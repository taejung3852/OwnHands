"""Snapshot-bound ELI5 Presentation generation and its separate SQLite cache.

The cache owns derived prose only. Review verdict, Claim status/count, freshness and
HumanDecision stay in the read-only sources and are read there on every request.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
import time

from ..lifecycle.model import canonical_json, fingerprint
from .generator import GeneratorError, OpenAICompatibleGenerator, ProviderConfig
from .read_model import DashboardReadModel, ReadModelError

NAMESPACE = "ownhands.dashboard.presentation"
SCHEMA_VERSION = 1
PROMPT_VERSION = "dashboard-eli5-v1"
OUTPUT_SCHEMA_VERSION = 1
GROUNDING_POLICY_VERSION = 1
LOCALE = "ko-KR"

LEASE_SECONDS = 45
TIMEOUT_SECONDS = 30
COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 2
INPUT_BYTES = 48 * 1024

VIEW_INTENTS = ("list_visible", "detail")
ICONS = ("✨", "🐛", "🔒", "⚡", "🛡️", "♻️", "🎨", "📋")
KINDS = ("intent", "observed", "gap", "inference")
SECTIONS = {"summary": (2, 3), "key_changes": (0, 4),
            "attention_items": (0, 3), "next_checks": (0, 3)}
# Authoritative values the generator may never own, at any depth of its output.
FORBIDDEN_KEYS = frozenset({
    "counts", "verdict", "total", "verified", "failed", "inconclusive", "unobserved",
    "required_complete", "freshness", "human_decision", "review_state", "status",
})
BANNED_PHRASES = ("완전히 안전", "모두 해결", "merge 가능", "현재도 최신",
                  "지금도 최신", "이후 새 근거 없음")
# The Dashboard computes every count itself; a generated sentence never states one.
AGGREGATE = re.compile(r"\d+\s*(개|건|%|/)")

_BODY = ("icon", "headline", "summary", "key_changes", "attention_items", "next_checks")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS presentation_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS presentations (
    cache_key TEXT PRIMARY KEY,
    presentation_id TEXT,
    snapshot_key TEXT NOT NULL,
    review_snapshot_id TEXT NOT NULL,
    snapshot_ref TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    recipe_hash TEXT NOT NULL,
    structured_input_hash TEXT,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    lease_owner TEXT,
    lease_expires_at TEXT,
    generated_at TEXT,
    generator_model TEXT,
    ready_sequence INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT,
    error_code TEXT,
    icon TEXT,
    headline TEXT,
    summary TEXT,
    key_changes TEXT,
    attention_items TEXT,
    next_checks TEXT
);
CREATE INDEX IF NOT EXISTS presentation_ready
ON presentations(recipe_hash, status, ready_sequence);
"""


class PresentationService:
    """`read_presentation` never writes or calls a provider; `ensure_presentation` may."""

    def __init__(self, catalog, lifecycle, project_id: str, *, cache_path,
                 config: ProviderConfig | None = None, generator=None, clock=None) -> None:
        self.read_model = DashboardReadModel(catalog, lifecycle, project_id)
        self.config = ProviderConfig.from_environment() if config is None else config
        self.cache_path = Path(cache_path).expanduser().resolve()
        for reserved in (Path(catalog.paths.catalog), Path(lifecycle.path)):
            if self.cache_path == reserved.expanduser().resolve():
                raise ValueError("presentation cache must not share a file with a source database")
        self._generator = generator
        self._clock = time.time if clock is None else clock
        self._connection = None
        self.recipe_hash = fingerprint({
            "prompt_version": PROMPT_VERSION,
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "grounding_policy_version": GROUNDING_POLICY_VERSION,
            "locale": LOCALE,
            **self.config.recipe(),
        })
        if self.cache_path.exists():
            self._connect()

    # --- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "PresentationService":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def timestamp(self, offset: float = 0.0) -> str:
        return datetime.fromtimestamp(self._clock() + offset, timezone.utc).isoformat()

    # --- read paths (no writes, no provider) -------------------------------

    def snapshot_key(self, snapshot_ref: dict) -> str:
        return self.read_model.snapshot_key(snapshot_ref)

    def read_detail(self, snapshot_key: str) -> dict:
        rows, bound = self._ready_rows()
        detail = self.read_model.read_detail(snapshot_key, presentations=rows, ready_sequence=bound)
        detail["presentation"] = self._present(detail)
        return detail

    def read_list(self, **query) -> dict:
        rows, bound = self._ready_rows()
        listing = self.read_model.read_list(presentations=rows, ready_sequence=bound, **query)
        for card in listing["items"]:
            card["presentation"] = self._present(card)
        return listing

    def read_presentation(self, snapshot_key: str) -> dict:
        return self.read_detail(snapshot_key)["presentation"]

    # --- ensure ------------------------------------------------------------

    def ensure_presentation(self, snapshot_key: str, *, view_intent: str,
                            recipe_hash: str | None = None) -> dict:
        if view_intent not in VIEW_INTENTS:
            raise ReadModelError("INVALID_QUERY", "Unsupported Dashboard view intent")
        if recipe_hash is not None and recipe_hash != self.recipe_hash:
            raise ReadModelError("RECIPE_CHANGED", "Dashboard presentation recipe changed")
        detail = self.read_detail(snapshot_key)
        if detail["presentation"]["status"] == "ready":
            return detail["presentation"]
        if detail["context"]["read_health"] != "complete":
            return self._fallback(detail, "unavailable", "source_partial")
        if not self.config.configured:
            return self._fallback(detail, "unavailable", "provider_not_configured")

        structured = self._structured_input(detail, self._facts(snapshot_key))
        cache_key = self._cache_key(detail)
        outcome, row = self._claim(cache_key, detail, fingerprint(structured))
        if outcome != "claimed":
            return self._from_row(detail, row)

        error_code = None
        output = None
        if len(canonical_json(structured).encode("utf-8")) > INPUT_BYTES:
            error_code = "input_too_large"
        else:
            try:
                output = self._provider().generate(
                    structured,
                    request_id=row["lease_owner"],
                    timeout_seconds=TIMEOUT_SECONDS,
                    idempotency_key=cache_key + ":" + str(row["attempt"]),
                )
            except GeneratorError as error:
                error_code = error.code
            if error_code is None:
                try:
                    output = self._validate(output, structured)
                except ValueError:
                    error_code = "invalid_output"
        return self._settle(cache_key, snapshot_key, detail, structured, row, output, error_code)

    # --- cache -------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._connection is not None:
            return self._connection
        fresh = not self.cache_path.exists()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.cache_path, isolation_level=None, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            if fresh:
                os.chmod(self.cache_path, 0o600)
            connection.executescript(_SCHEMA)
            for key, value in (("namespace", NAMESPACE), ("schema_version", str(SCHEMA_VERSION))):
                connection.execute(
                    "INSERT OR IGNORE INTO presentation_meta(key, value) VALUES (?, ?)", (key, value))
            stored = dict(connection.execute("SELECT key, value FROM presentation_meta").fetchall())
            if stored.get("namespace") != NAMESPACE or stored.get("schema_version") != str(SCHEMA_VERSION):
                raise ValueError("presentation cache schema is not supported")
        except BaseException:
            connection.close()
            raise
        self._connection = connection
        return connection

    def _rows(self) -> list[sqlite3.Row]:
        if self._connection is None and not self.cache_path.exists():
            return []
        return self._connect().execute(
            "SELECT * FROM presentations WHERE recipe_hash=?", (self.recipe_hash,)).fetchall()

    def _ready_rows(self) -> tuple[tuple[dict, ...], int]:
        rows = [row for row in self._rows() if row["status"] == "ready"]
        bound = max((row["ready_sequence"] for row in rows), default=0)
        return tuple(self._body(row) for row in rows), bound

    def _row(self, cache_key: str) -> sqlite3.Row | None:
        for row in self._rows():
            if row["cache_key"] == cache_key:
                return row
        return None

    @staticmethod
    def _body(row: sqlite3.Row) -> dict:
        value = {"snapshot_key": row["snapshot_key"], "status": row["status"],
                 "ready_sequence": row["ready_sequence"],
                 "presentation_id": row["presentation_id"], "recipe_hash": row["recipe_hash"],
                 "generated_at": row["generated_at"], "generator_model": row["generator_model"],
                 "icon": row["icon"]}
        for name in ("headline", "summary", "key_changes", "attention_items", "next_checks"):
            value[name] = json.loads(row[name]) if row[name] else None
        return value

    def _cache_key(self, detail: dict) -> str:
        return fingerprint({"namespace": NAMESPACE, "scope": detail["scope"],
                            "snapshot_ref": detail["snapshot_ref"],
                            "recipe_hash": self.recipe_hash})

    def _epoch(self, value) -> float:
        return datetime.fromisoformat(value).timestamp() if value else 0.0

    def _claim(self, cache_key: str, detail: dict, input_hash: str):
        """Short write transaction: decide, and take the lease. No provider call inside."""
        connection = self._connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            outcome, result = self._decide(connection, cache_key, detail, input_hash)
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        return outcome, result

    def _decide(self, connection, cache_key, detail, input_hash):
        row = connection.execute(
            "SELECT * FROM presentations WHERE cache_key=?", (cache_key,)).fetchone()
        now = self._clock()
        if row is not None:
            if row["status"] == "ready":
                return "ready", row
            if row["status"] == "pending" and self._epoch(row["lease_expires_at"]) > now:
                return "pending", row
            if row["attempt_count"] >= MAX_ATTEMPTS or self._epoch(row["next_retry_at"]) > now:
                if row["status"] == "pending":
                    # A worker died holding the last attempt: settle it instead of
                    # leaving the row pending with nothing left to resume it.
                    connection.execute(
                        """UPDATE presentations SET status='failed', lease_owner=NULL,
                           lease_expires_at=NULL,
                           error_code=COALESCE(error_code, 'lease_expired')
                           WHERE cache_key=?""", (cache_key,))
                    row = connection.execute(
                        "SELECT * FROM presentations WHERE cache_key=?", (cache_key,)).fetchone()
                return "failed", row
        owner = uuid.uuid4().hex
        attempt = (row["attempt_count"] if row is not None else 0) + 1
        snapshot_ref = detail["snapshot_ref"]
        connection.execute(
            """INSERT INTO presentations(
                 cache_key, snapshot_key, review_snapshot_id, snapshot_ref, fingerprint,
                 recipe_hash, structured_input_hash, status, attempt_count,
                 lease_owner, lease_expires_at)
               VALUES (?,?,?,?,?,?,?,'pending',?,?,?)
               ON CONFLICT(cache_key) DO UPDATE SET
                 status='pending', attempt_count=excluded.attempt_count,
                 lease_owner=excluded.lease_owner, lease_expires_at=excluded.lease_expires_at,
                 structured_input_hash=excluded.structured_input_hash,
                 next_retry_at=NULL, error_code=NULL""",
            (cache_key, detail["snapshot_key"], snapshot_ref["id"],
             canonical_json(snapshot_ref), snapshot_ref["hash"], self.recipe_hash,
             input_hash, attempt, owner, self.timestamp(LEASE_SECONDS)),
        )
        return "claimed", {"lease_owner": owner, "attempt": attempt}

    def _settle(self, cache_key, snapshot_key, detail, structured, lease, output, error_code):
        """Second short write transaction: only the lease owner may store a result."""
        connection = self._connect()
        if error_code is None:
            # A late response must not be stored against a snapshot or input it no longer matches.
            current = self.read_model.read_detail(snapshot_key)
            if (current["snapshot_ref"] != detail["snapshot_ref"]
                    or current["context"]["read_health"] != "complete"
                    or fingerprint(self._structured_input(
                        current, self._facts(snapshot_key))) != fingerprint(structured)):
                error_code = "input_changed"
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT * FROM presentations WHERE cache_key=?", (cache_key,)).fetchone()
            if row is None or row["lease_owner"] != lease["lease_owner"]:
                pass  # The lease moved on: this response is late and is discarded.
            elif error_code is not None:
                connection.execute(
                    """UPDATE presentations SET status='failed', error_code=?, next_retry_at=?,
                       lease_owner=NULL, lease_expires_at=NULL WHERE cache_key=?""",
                    (error_code, self.timestamp(COOLDOWN_SECONDS), cache_key))
            else:
                generated_at = self.timestamp()
                connection.execute(
                    """UPDATE presentations SET status='ready', error_code=NULL, next_retry_at=NULL,
                       lease_owner=NULL, lease_expires_at=NULL, generated_at=?, generator_model=?,
                       presentation_id=?, icon=?, headline=?, summary=?, key_changes=?,
                       attention_items=?, next_checks=?,
                       ready_sequence=(SELECT COALESCE(MAX(ready_sequence), 0) + 1
                                       FROM presentations)
                       WHERE cache_key=?""",
                    (generated_at, self.config.model_id,
                     fingerprint({"cache_key": cache_key, "generated_at": generated_at,
                                  "attempt": lease["attempt"]}),
                     output["icon"],
                     *[canonical_json(output[name]) for name in
                       ("headline", "summary", "key_changes", "attention_items", "next_checks")],
                     cache_key))
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        return self._from_row(detail, self._row(cache_key))

    # --- Presentation view model -------------------------------------------

    def _fallback(self, detail, status, reason, retry_after=None) -> dict:
        value = dict(detail["presentation"])
        value.update(status=status, reason_code=reason, fallback=True,
                     recipe_hash=self.recipe_hash, presentation_id=None,
                     generated_at=None, generator_model=None, retry_after=retry_after)
        return value

    def _present(self, detail) -> dict:
        """Overlay the cache state the browser needs to decide whether to ensure or poll."""
        if detail["presentation"]["status"] == "ready":
            return dict(detail["presentation"], recipe_hash=self.recipe_hash, retry_after=None)
        if detail["context"]["read_health"] != "complete":
            return self._fallback(detail, "unavailable", "source_partial")
        if not self.config.configured:
            return self._fallback(detail, "unavailable", "provider_not_configured")
        return self._from_row(detail, self._row(self._cache_key(detail)))

    def _from_row(self, detail, row) -> dict:
        if row is None:
            return self._fallback(detail, "absent", "presentation_absent")
        if row["status"] == "ready":
            ready = dict(detail["presentation"])
            ready.update(self._body(row))
            ready.pop("snapshot_key", None)
            ready.pop("ready_sequence", None)
            ready.update(status="ready", fallback=False, reason_code=None, retry_after=None)
            return ready
        if row["status"] == "pending":
            return self._fallback(detail, "pending", None)
        retry_after = None if row["attempt_count"] >= MAX_ATTEMPTS else row["next_retry_at"]
        return self._fallback(detail, "failed", row["error_code"], retry_after)

    # --- grounded input -----------------------------------------------------

    def _facts(self, snapshot_key: str) -> dict:
        return self.read_model.read_generation_facts(snapshot_key)

    def _structured_input(self, detail: dict, facts: dict) -> dict:
        """Allowlisted Snapshot facts only. No raw, no diff, no other Snapshot, no secret."""
        return {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "locale": LOCALE,
            "snapshot": {"snapshot_key": detail["snapshot_key"],
                         "created_at": detail["snapshot_created_at"]},
            "issue": {"title": detail["issue"]["title"],
                      "source": {"record_ref": detail["issue"]["ref"], "pointer": "/title"}},
            "spec": facts["spec"],
            "change": facts["change"],
            "review": {"review_state": detail["review_state"],
                       "state_reason": detail["state_reason"],
                       "required_complete": detail["required_complete"],
                       "counts": detail["counts"],
                       "source_contract_version": detail["source_contract_version"]},
            "claims": [{
                "id": claim["id"], "text": claim["text"], "required": claim["required"],
                "comparison": claim["comparison"], "status": claim["status"],
                "source": claim["source"],
                "checks": [{"id": check["id"], "statement": check["statement"],
                            "role": check["role"], "status": check["status"],
                            "reason_codes": check["reason_codes"],
                            "before": [self._observed(value) for value in check["before"]],
                            "after": [self._observed(value) for value in check["after"]],
                            "comparisons": [{name: value[name] for name in
                                             ("test_id", "comparable", "environment",
                                              "test_meaning", "expected_before")}
                                            for value in check["comparisons"]]}
                           for check in claim["checks"]],
            } for claim in detail["claims"]],
            "problems": [{"id": problem["id"], "kind": problem["kind"],
                          "required": problem["required"], "claim_id": problem["claim_id"],
                          "check_id": problem["check_id"], "reason_code": problem["reason_code"],
                          "description": problem["description"], "sources": problem["sources"]}
                         for problem in detail["problems"]],
        }

    @staticmethod
    def _observed(observation: dict) -> dict:
        """Execution meaning and result only: no refs, no evidence links, no raw."""
        return {name: observation[name] for name in
                ("phase", "result", "basis", "test_id", "test_meaning")}

    # --- output validation --------------------------------------------------

    def _validate(self, output, structured) -> dict:
        if not isinstance(output, dict) or set(output) != set(_BODY):
            raise ValueError("unexpected generation schema")
        if output["icon"] not in ICONS:
            raise ValueError("unexpected icon")
        self._reject_forbidden_keys(output)
        # `verified` backs an observed sentence; `gap` backs an unverified one. Everything
        # else (issue title, Spec document, change set) grounds intent and inference only.
        verified, gaps = set(), set()
        allowed = {canonical_json(structured["issue"]["source"]),
                   canonical_json(structured["spec"]["source"])}
        change = structured["change"]
        if change is not None:
            allowed.add(canonical_json(change["source"]))
            if change["baseline_source"] is not None:
                allowed.add(canonical_json(change["baseline_source"]))
        for claim in structured["claims"]:
            pointer = canonical_json(claim["source"])
            (verified if claim["status"] == "verified" else gaps).add(pointer)
        for problem in structured["problems"]:
            gaps.update(canonical_json(source) for source in problem["sources"])
        gaps -= verified
        allowed |= verified | gaps
        self._fact(output["headline"], allowed, verified, gaps, 60)
        for name, (low, high) in SECTIONS.items():
            items = output[name]
            if not isinstance(items, list) or not low <= len(items) <= high:
                raise ValueError("unexpected " + name + " length")
            for item in items:
                self._fact(item, allowed, verified, gaps, 120)
        return output

    @staticmethod
    def _reject_forbidden_keys(value) -> None:
        if isinstance(value, dict):
            if FORBIDDEN_KEYS & set(value):
                raise ValueError("generation may not carry an authoritative field")
            for child in value.values():
                PresentationService._reject_forbidden_keys(child)
        elif isinstance(value, list):
            for child in value:
                PresentationService._reject_forbidden_keys(child)

    @staticmethod
    def _fact(value, allowed, verified, gaps, limit) -> None:
        if not isinstance(value, dict) or set(value) != {"text", "kind", "sources"}:
            raise ValueError("unexpected TextFact schema")
        text, kind, sources = value["text"], value["kind"], value["sources"]
        if not isinstance(text, str) or not 0 < len(text) <= limit:
            raise ValueError("unexpected TextFact length")
        if kind not in KINDS:
            raise ValueError("unexpected TextFact kind")
        if AGGREGATE.search(text):
            raise ValueError("generation may not state a count")
        if any(phrase in text for phrase in BANNED_PHRASES):
            raise ValueError("generation may not overstate the observed scope")
        if not isinstance(sources, list) or not sources:
            raise ValueError("TextFact needs at least one SourcePointer")
        pointers = [canonical_json(source) for source in sources]
        for pointer in pointers:
            if pointer not in allowed:
                raise ValueError("SourcePointer is outside this Snapshot")
            if kind == "observed" and pointer not in verified:
                raise ValueError("only a verified Claim may be reported as observed")
        if kind == "gap" and not any(pointer in gaps for pointer in pointers):
            raise ValueError("a gap must cite a recorded gap, not only verified Claims")

    def _provider(self):
        if self._generator is None:
            self._generator = OpenAICompatibleGenerator(self.config)
        return self._generator

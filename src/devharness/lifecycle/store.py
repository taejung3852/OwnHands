from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ..catalog import Catalog
from ..evidence import EvidenceStore
from ..events import EventLog
from ..identity import IdentityRegistry
from .model import (
    BASES,
    CLAIM_STATES,
    KINDS,
    NAMESPACE,
    RESULTS,
    SCHEMA_VERSION,
    STAGE_SCOPE_KEYS,
    canonical_json,
    fingerprint,
    reference,
    references,
    require_sha256,
    require_text,
    validate_scope,
)


BLOCKER_REASONS = {
    "required_external_service_unavailable",
    "required_permission_unavailable",
    "required_input_unavailable",
    "verification_execution_failed",
    "invalid_required_evidence",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lifecycle_metadata(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lifecycle_records(
    sequence INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    logical_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    scope_json TEXT NOT NULL,
    data_json TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    UNIQUE(kind, logical_id, revision)
);
CREATE TABLE IF NOT EXISTS lifecycle_activations(
    sequence INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    slot TEXT NOT NULL,
    reference_json TEXT NOT NULL,
    approval_json TEXT,
    previous_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS lifecycle_record_identity
ON lifecycle_records(kind, logical_id, revision);
CREATE INDEX IF NOT EXISTS lifecycle_activation_slot
ON lifecycle_activations(kind, scope_json, slot, sequence);
CREATE TRIGGER IF NOT EXISTS lifecycle_records_no_update
BEFORE UPDATE ON lifecycle_records BEGIN SELECT RAISE(ABORT, 'lifecycle records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS lifecycle_records_no_delete
BEFORE DELETE ON lifecycle_records BEGIN SELECT RAISE(ABORT, 'lifecycle records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS lifecycle_activations_no_update
BEFORE UPDATE ON lifecycle_activations BEGIN SELECT RAISE(ABORT, 'lifecycle activations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS lifecycle_activations_no_delete
BEFORE DELETE ON lifecycle_activations BEGIN SELECT RAISE(ABORT, 'lifecycle activations are append-only'); END;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LifecycleStore:
    """Namespaced lifecycle v1 journal that only reads legacy Core records."""

    def __init__(self, catalog: Catalog, path: Path | str | None = None) -> None:
        self.catalog = catalog
        self.path = Path(path) if path is not None else catalog.paths.root / "lifecycle-v1.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(_SCHEMA)
        self.connection.execute(
            "INSERT OR IGNORE INTO lifecycle_metadata(key, value) VALUES ('namespace', ?)",
            (NAMESPACE,),
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO lifecycle_metadata(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        try:
            self._validate_metadata()
            self._verify_journal()
        except BaseException:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "LifecycleStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def _validate_metadata(self) -> None:
        values = dict(self.connection.execute("SELECT key, value FROM lifecycle_metadata"))
        if values != {"namespace": NAMESPACE, "schema_version": str(SCHEMA_VERSION)}:
            raise ValueError("unsupported lifecycle namespace or schema version")

    def append(self, kind: str, logical_id: str, scope: dict, data: dict) -> dict:
        if kind not in KINDS:
            raise ValueError(f"unsupported lifecycle artifact kind: {kind}")
        logical_id = require_text(logical_id, "logical_id")
        scope = validate_scope(scope)
        if not isinstance(data, dict):
            raise ValueError("artifact data must be an object")
        data = json.loads(canonical_json(data))

        with self._transaction() as connection:
            self._verify_journal()
            self._validate_owner(scope)
            scope_json = canonical_json(scope)
            data_json = canonical_json(data)
            latest = connection.execute(
                """SELECT * FROM lifecycle_records
                   WHERE kind=? AND logical_id=? ORDER BY revision DESC LIMIT 1""",
                (kind, logical_id),
            ).fetchone()
            if latest is not None and latest["scope_json"] != scope_json:
                raise ValueError("a lifecycle logical id cannot move to another scope")
            if latest is not None:
                stored_data = json.loads(latest["data_json"])
                comparable_data = dict(stored_data)
                if kind == "review":
                    comparable_data.pop("review_state", None)
                if (stored_data == data or comparable_data == data) and data.get("contract_version") != 2:
                    existing = reference(kind, logical_id, latest["revision"], latest["record_hash"])
                    self._get_with_closure(existing, set())
                    return existing
            self._validate_artifact(kind, logical_id, scope, data)
            data_json = canonical_json(data)
            if latest is not None and latest["data_json"] == data_json:
                return reference(kind, logical_id, latest["revision"], latest["record_hash"])
            revision = 1 if latest is None else latest["revision"] + 1
            head = connection.execute(
                "SELECT sequence, record_hash FROM lifecycle_records ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if head is None else head["sequence"] + 1
            previous_hash = "" if head is None else head["record_hash"]
            created_at = _now()
            document = {
                "namespace": NAMESPACE,
                "schema_version": SCHEMA_VERSION,
                "sequence": sequence,
                "kind": kind,
                "id": logical_id,
                "revision": revision,
                "scope": scope,
                "data": data,
                "previous_hash": previous_hash,
                "created_at": created_at,
            }
            record_hash = fingerprint(document)
            connection.execute(
                """INSERT INTO lifecycle_records(
                    sequence, kind, logical_id, revision, scope_json, data_json,
                    previous_hash, record_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sequence, kind, logical_id, revision, scope_json, data_json,
                 previous_hash, record_hash, created_at),
            )
            return reference(kind, logical_id, revision, record_hash)

    def get(self, artifact_ref: dict) -> dict:
        self._verify_journal()
        return self._get_with_closure(artifact_ref, set())

    def _get_with_closure(self, artifact_ref: dict, visited: set[str]) -> dict:
        row = self._row_for_reference(artifact_ref)
        record = self._record(row)
        if record["hash"] in visited:
            return record
        visited.add(record["hash"])
        if record["kind"] == "evidence_binding":
            self._validate_legacy_evidence(record["scope"], record["data"]["evidence_id"])
        for path, child_ref in references(record["data"]):
            child = self._record(self._row_for_reference(child_ref))
            if record["kind"] == "attempt" and path == ("previous",):
                if child["kind"] != "attempt" or child["scope"].get("issue_id") != record["scope"].get("issue_id"):
                    raise ValueError("previous attempt must belong to the same issue")
            else:
                self.assert_reference_scope(child_ref, record["scope"])
            self._get_with_closure(child_ref, visited)
        return record

    def activate(self, artifact_ref: dict, *, approval: dict | None = None, slot: str = "current") -> dict:
        record = self.get(artifact_ref)
        if record["kind"] not in {
            "attempt", "spec", "code_state", "environment", "baseline", "review", "snapshot"
        }:
            raise ValueError("artifact kind has no active selection")
        if record["kind"] not in {"attempt", "spec"}:
            self._require_attempt_scope(record["scope"])
        if record["kind"] == "baseline" and slot != record["data"]["baseline_kind"]:
            raise ValueError("baseline activation slot must match baseline_kind")
        if record["kind"] == "spec":
            if approval is None:
                raise ValueError("spec activation requires human approval")
            approval_record = self.get(approval)
            approval_data = approval_record["data"]
            if approval_record["kind"] != "spec_approval" or approval_data.get("spec") != artifact_ref:
                raise ValueError("spec approval does not bind the selected revision")
            if approval_data.get("actor", {}).get("kind") != "human" or approval_data.get("decision") != "approved":
                raise ValueError("spec activation requires an approved human decision")
            self.assert_reference_scope(approval, record["scope"])
        elif approval is not None:
            raise ValueError("only spec activation accepts spec approval")

        activation_scope = record["scope"]
        if record["kind"] in {"attempt", "spec"}:
            activation_scope = {
                key: record["scope"][key] for key in ("project_id", "issue_id")
            }

        with self._transaction() as connection:
            self._verify_journal()
            scope_json = canonical_json(activation_scope)
            latest = connection.execute(
                """SELECT * FROM lifecycle_activations
                   WHERE kind=? AND scope_json=? AND slot=? ORDER BY sequence DESC LIMIT 1""",
                (record["kind"], scope_json, slot),
            ).fetchone()
            reference_json = canonical_json(artifact_ref)
            approval_json = None if approval is None else canonical_json(approval)
            if latest is not None and latest["reference_json"] == reference_json and latest["approval_json"] == approval_json:
                return artifact_ref
            head = connection.execute(
                "SELECT sequence, record_hash FROM lifecycle_activations ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if head is None else head["sequence"] + 1
            previous_hash = "" if head is None else head["record_hash"]
            created_at = _now()
            body = {
                "namespace": NAMESPACE,
                "schema_version": SCHEMA_VERSION,
                "sequence": sequence,
                "kind": record["kind"],
                "scope": activation_scope,
                "slot": slot,
                "reference": artifact_ref,
                "approval": approval,
                "previous_hash": previous_hash,
                "created_at": created_at,
            }
            record_hash = fingerprint(body)
            connection.execute(
                """INSERT INTO lifecycle_activations(
                    sequence, kind, scope_json, slot, reference_json, approval_json,
                    previous_hash, record_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sequence, record["kind"], scope_json, slot, reference_json,
                 approval_json, previous_hash, record_hash, created_at),
            )
            return artifact_ref

    def current(self, kind: str, scope: dict, slot: str = "current") -> dict | None:
        activation = self.current_activation(kind, scope, slot)
        return None if activation is None else activation["reference"]

    def current_activation(self, kind: str, scope: dict, slot: str = "current") -> dict | None:
        scope_json = canonical_json(validate_scope(scope))
        self._verify_journal()
        row = self.connection.execute(
            """SELECT * FROM lifecycle_activations
               WHERE kind=? AND scope_json=? AND slot=? ORDER BY sequence DESC LIMIT 1""",
            (kind, scope_json, slot),
        ).fetchone()
        if row is None:
            return None
        return {
            "sequence": row["sequence"],
            "kind": row["kind"],
            "scope": json.loads(row["scope_json"]),
            "slot": row["slot"],
            "reference": json.loads(row["reference_json"]),
            "approval": None if row["approval_json"] is None else json.loads(row["approval_json"]),
            "hash": row["record_hash"],
            "created_at": row["created_at"],
        }

    def bind_evidence(self, logical_id: str, scope: dict, evidence_id: str) -> dict:
        scope = validate_scope(scope)
        self._validate_legacy_evidence(scope, evidence_id)
        return self.append("evidence_binding", logical_id, scope, {"evidence_id": evidence_id})

    def assert_reference_scope(self, artifact_ref: dict, scope: dict) -> None:
        record = self._record(self._row_for_reference(artifact_ref))
        target = validate_scope(scope)
        source = record["scope"]
        if source["project_id"] != target["project_id"]:
            raise ValueError("reference belongs to another project")
        if (record["kind"] == "work_issue" and "issue_id" in target
                and target["issue_id"] != record["id"]):
            raise ValueError("reference belongs to another issue")
        for key in ("issue_id", "task_id", "attempt_id"):
            if key in source and source.get(key) != target.get(key):
                raise ValueError(f"reference belongs to another {key.removesuffix('_id')}")

    def projection(self) -> dict:
        self._verify_journal()
        record_head = self.connection.execute(
            "SELECT sequence, record_hash FROM lifecycle_records ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        activation_head = self.connection.execute(
            "SELECT sequence, record_hash FROM lifecycle_activations ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        active: dict[str, dict] = {}
        for row in self.connection.execute("SELECT * FROM lifecycle_activations ORDER BY sequence"):
            key = canonical_json({"kind": row["kind"], "scope": json.loads(row["scope_json"]), "slot": row["slot"]})
            active[key] = {
                "reference": json.loads(row["reference_json"]),
                "approval": None if row["approval_json"] is None else json.loads(row["approval_json"]),
            }
        body = {
            "namespace": NAMESPACE,
            "schema_version": SCHEMA_VERSION,
            "record_head": 0 if record_head is None else record_head["sequence"],
            "record_hash": "" if record_head is None else record_head["record_hash"],
            "activation_head": 0 if activation_head is None else activation_head["sequence"],
            "activation_hash": "" if activation_head is None else activation_head["record_hash"],
            "active": active,
        }
        return {**body, "hash": fingerprint(body)}

    def projection_status(self, projected: dict) -> dict:
        current = self.projection()
        return {
            "needs_refresh": projected.get("record_head") != current["record_head"]
            or projected.get("activation_head") != current["activation_head"],
            "current": current,
        }

    def inspect_stage(self, stage: str, action: str, scope: dict, inputs: dict, request_context: dict) -> dict:
        from .readiness import inspect_stage

        self._validate_owner(validate_scope(scope))
        return inspect_stage(self, stage, action, scope, inputs, request_context)

    def evaluate_review(self, scope: dict, inputs: dict) -> dict:
        """Resolve a complete input set in one transaction; never run tests."""
        from .evaluation_store import compose_review
        with self._transaction():
            self._verify_journal()
            return compose_review(self, scope, json.loads(canonical_json(inputs)))

    def review_status(self, review_ref: dict) -> dict:
        """Report unreadable evidence or new records without rewriting a Snapshot."""
        from .evaluation_store import _collect
        with self._transaction():
            try:
                record = self.get(review_ref)
            except ValueError as error:
                return {"readable": False, "reason": str(error)}
            if record["kind"] != "review":
                raise ValueError("review_status requires a review")
            if record["data"].get("contract_version") != 2:
                return {"readable": True, "contract_version": 1}
            _, diagnostics, refs = _collect(self, record["scope"], record["data"]["evaluation_inputs"])
            return {"readable": True, "contract_version": 2,
                    "new_evidence_available": fingerprint(refs) != record["data"]["observation_set_hash"],
                    "diagnostics": diagnostics}

    def freshness(self, review_ref: dict, spec_ref: dict, code_ref: dict,
                  environment_ref: dict, test_meanings: dict[str, str]) -> dict:
        review = self.get(review_ref)
        if review["kind"] != "review":
            raise ValueError("freshness subject must be a review")
        data = review["data"]
        changed = []
        current_inputs = {
            "spec": self._require_kind(spec_ref, "spec", review["scope"]),
            "code_state": self._require_kind(code_ref, "code_state", review["scope"]),
            "environment": self._require_kind(environment_ref, "environment", review["scope"]),
        }
        if data.get("spec") != spec_ref:
            changed.append("spec")
        for name in ("code_state", "environment"):
            reviewed_input = self.get(data[name])
            if reviewed_input["data"].get("fingerprint") != current_inputs[name]["data"].get("fingerprint"):
                changed.append(name)
        unknown = []
        observation_refs = list(data.get("additional_observations", []))
        for claim in data.get("claims", []):
            observation_refs.extend(claim.get("observations", []))
        for observation_ref in observation_refs:
            observation = self.get(observation_ref)["data"]
            test_id = observation.get("test_id")
            if test_id not in test_meanings:
                unknown.append(test_id)
            elif test_meanings[test_id] != observation.get("test_meaning"):
                changed.append(f"test_meaning:{test_id}")
        state = "stale" if changed else "unknown" if unknown else "current"
        return {"state": state, "changed": sorted(set(changed)), "unknown": sorted(set(unknown))}

    def _validate_owner(self, scope: dict) -> None:
        task_id = scope.get("task_id")
        if task_id is None:
            return
        task = IdentityRegistry(self.catalog).get_task(task_id)
        if task.project_id != scope["project_id"]:
            raise ValueError("task belongs to another project")

    def _validate_artifact(self, kind: str, logical_id: str, scope: dict, data: dict) -> None:
        if kind in {"spec", "baseline", "observation", "review"}:
            version = data.get("contract_version", 1)
            if type(version) is not int or version not in {1, 2}:
                raise ValueError("unsupported artifact contract version")
            if version == 2:
                from .evaluation_store import validate_v2, validate_review
                if kind == "review":
                    validate_review(self, scope, data)
                    return
                validate_v2(self, kind, scope, data)
            elif kind != "spec":
                spec = self._require_kind(data.get("spec"), "spec", scope)
                if spec["data"].get("contract_version") == 2:
                    raise ValueError("v2 Spec cannot use legacy evaluation contract")
        if kind == "work_issue":
            if set(scope) != {"project_id"}:
                raise ValueError("work_issue must use project scope")
            require_text(data.get("title"), "work issue title")
        elif kind == "attempt":
            if scope.get("attempt_id") != logical_id:
                raise ValueError("attempt id must match its scope")
            self._require_kind(data.get("issue"), "work_issue", scope)
            previous = data.get("previous")
            if previous is not None:
                previous_record = self.get(previous)
                if previous_record["kind"] != "attempt" or previous_record["scope"].get("issue_id") != scope.get("issue_id"):
                    raise ValueError("previous attempt must belong to the same issue")
        elif kind == "spec":
            self._require_issue_scope(scope)
            self._require_kind(data.get("issue"), "work_issue", scope)
            document = data.get("document")
            if not isinstance(document, dict):
                raise ValueError("spec document must be an object")
            require_text(document.get("path"), "spec document path")
            require_text(document.get("text"), "spec document text")
            criteria = data.get("criteria")
            if not isinstance(criteria, list) or not criteria:
                raise ValueError("spec criteria must be a non-empty list")
            ids = []
            for criterion in criteria:
                if not isinstance(criterion, dict) or not isinstance(criterion.get("required"), bool):
                    raise ValueError("each criterion must define required as a boolean")
                ids.append(require_text(criterion.get("id"), "criterion id"))
                require_text(criterion.get("text"), "criterion text")
                if criterion.get("comparison") not in {"current", "preserve", "improve"}:
                    raise ValueError("criterion comparison must be current, preserve, or improve")
            if len(ids) != len(set(ids)):
                raise ValueError("criterion ids must be unique")
        elif kind == "spec_approval":
            self._require_issue_scope(scope)
            self._require_kind(data.get("spec"), "spec", scope)
            actor = data.get("actor")
            if not isinstance(actor, dict) or actor.get("kind") != "human":
                raise ValueError("spec approval must be made by a human")
            require_text(actor.get("id"), "spec approval actor id")
            if data.get("decision") not in {"approved", "rejected"}:
                raise ValueError("unsupported spec approval decision")
            require_text(data.get("reason"), "spec approval reason")
            require_text(data.get("source"), "spec approval source")
        elif kind == "code_state":
            self._require_attempt_scope(scope)
            if set(data) != {"code_state_version", "commit", "files", "coverage", "exclusions", "fingerprint"}:
                raise ValueError("code_state must contain the canonical v1 fields")
            if data.get("code_state_version") != 1:
                raise ValueError("unsupported code_state version")
            commit = require_text(data.get("commit"), "code_state commit")
            if len(commit) not in {40, 64} or any(character not in "0123456789abcdef" for character in commit):
                raise ValueError("code_state commit must be a Git object id")
            require_sha256(data.get("fingerprint"), "code_state fingerprint")
            if data.get("coverage") not in {"complete", "partial"}:
                raise ValueError("code_state coverage must be complete or partial")
            if not isinstance(data.get("exclusions"), list) or not isinstance(data.get("files"), list):
                raise ValueError("code_state exclusions and files must be lists")
            paths = []
            directory_paths = []
            for item in data["files"]:
                if not isinstance(item, dict) or set(item) != {"path", "origin", "kind", "mode", "hash"}:
                    raise ValueError("each code_state file must contain canonical fields")
                path = require_text(item.get("path"), "code_state file path")
                if path.startswith("/") or ".." in Path(path).parts:
                    raise ValueError("code_state file path must be repository-relative")
                paths.append(path)
                if item.get("origin") not in {"tracked", "untracked"}:
                    raise ValueError("code_state file origin must be tracked or untracked")
                file_kind = item.get("kind")
                if file_kind not in {"file", "symlink", "directory", "missing"}:
                    raise ValueError("unsupported code_state file kind")
                if file_kind in {"file", "symlink"}:
                    if not isinstance(item.get("mode"), int):
                        raise ValueError("captured code_state file mode must be an integer")
                    require_sha256(item.get("hash"), "code_state file hash")
                elif file_kind == "directory":
                    directory_paths.append(path)
                    if not isinstance(item.get("mode"), int) or item.get("hash") is not None:
                        raise ValueError("code_state directory must have a mode and null hash")
                elif item.get("mode") is not None or item.get("hash") is not None:
                    raise ValueError("missing code_state file must have null mode and hash")
            if len(paths) != len(set(paths)):
                raise ValueError("code_state file paths must be unique")
            exclusion_areas = []
            for item in data["exclusions"]:
                if not isinstance(item, dict) or set(item) != {"area", "reason"}:
                    raise ValueError("each code_state exclusion must contain area and reason")
                exclusion_areas.append(require_text(item.get("area"), "code_state exclusion area"))
                require_text(item.get("reason"), "code_state exclusion reason")
            if (data["coverage"] == "complete") == bool(data["exclusions"]):
                raise ValueError("code_state coverage must reflect whether exclusions exist")
            if not set(directory_paths) <= set(exclusion_areas):
                raise ValueError("code_state directories must be declared as exclusions")
            body = {key: data[key] for key in ("code_state_version", "commit", "files", "coverage", "exclusions")}
            if fingerprint(body) != data["fingerprint"]:
                raise ValueError("code_state fingerprint does not match its captured fields")
        elif kind == "environment":
            self._require_attempt_scope(scope)
            if set(data) != {"environment_version", "description", "details", "fingerprint"}:
                raise ValueError("environment must contain the canonical v1 fields")
            if data.get("environment_version") != 1 or not isinstance(data.get("details"), dict):
                raise ValueError("unsupported environment state")
            require_sha256(data.get("fingerprint"), "environment fingerprint")
            require_text(data.get("description"), "environment description")
            body = {key: data[key] for key in ("environment_version", "description", "details")}
            if fingerprint(body) != data["fingerprint"]:
                raise ValueError("environment fingerprint does not match its described fields")
        elif kind == "baseline":
            self._require_attempt_scope(scope)
            if data.get("baseline_kind") not in {"micro", "verification"}:
                raise ValueError("baseline_kind must be micro or verification")
            self._require_approved_spec(data, scope)
            self._require_kind(data.get("code_state"), "code_state", scope)
            self._require_kind(data.get("environment"), "environment", scope)
            observations = self._require_reference_list(data.get("observations"), "observation", scope)
            for observation in observations:
                observed = observation["data"]
                if observed.get("phase") != "before":
                    raise ValueError("baseline observations must use the before phase")
                for field in ("spec", "spec_approval", "code_state", "environment"):
                    if observed.get(field) != data[field]:
                        raise ValueError(f"baseline observation uses a different {field}")
            missing_reason = data.get("missing_reason", "")
            if not isinstance(missing_reason, str):
                raise ValueError("baseline missing_reason must be a string")
            if data["baseline_kind"] == "verification" and not observations and not missing_reason.strip():
                raise ValueError("verification baseline without observations requires a missing reason")
        elif kind == "evidence_binding":
            self._require_attempt_scope(scope)
            evidence_id = require_text(data.get("evidence_id"), "evidence id")
            self._validate_legacy_evidence(scope, evidence_id)
            # append() holds BEGIN IMMEDIATE here, so two writers cannot bind
            # the same legacy evidence to different attempts concurrently.
            for row in self.connection.execute(
                "SELECT scope_json, data_json FROM lifecycle_records WHERE kind='evidence_binding'"
            ):
                if json.loads(row["data_json"]).get("evidence_id") == evidence_id:
                    previous_scope = json.loads(row["scope_json"])
                    if previous_scope != scope:
                        raise ValueError("legacy evidence is already bound to another attempt")
        elif kind == "observation":
            self._require_attempt_scope(scope)
            self._require_approved_spec(data, scope)
            self._require_kind(data.get("code_state"), "code_state", scope)
            self._require_kind(data.get("environment"), "environment", scope)
            require_text(data.get("test_id"), "observation test_id")
            if data.get("phase") not in {"before", "after"}:
                raise ValueError("observation phase must be before or after")
            require_sha256(data.get("test_meaning"), "observation test_meaning")
            if data.get("result") not in RESULTS or data.get("basis") not in BASES:
                raise ValueError("unsupported observation result or basis")
            require_text(data.get("selection_reason"), "observation selection_reason")
            bindings = self._require_reference_list(data.get("evidence"), "evidence_binding", scope)
            if data["basis"] == "observed" and not bindings:
                raise ValueError("observed result requires bound evidence")
            for binding in bindings:
                evidence = self._validate_legacy_evidence(scope, binding["data"]["evidence_id"])
                if evidence.result != data["result"] or evidence.basis != data["basis"]:
                    raise ValueError("observation result/basis differs from bound evidence")
                expected_fields = {
                    "test_id": data["test_id"],
                    "criterion_id": data.get("criterion_id"),
                    "phase": data["phase"],
                    "spec_hash": data["spec"]["hash"],
                    "code_hash": data["code_state"]["hash"],
                    "environment_hash": data["environment"]["hash"],
                    "test_meaning": data["test_meaning"],
                }
                if any(evidence.fields.get(key) != value for key, value in expected_fields.items()):
                    raise ValueError("observation fields differ from bound evidence")
        elif kind == "review":
            self._validate_review(scope, data)
        elif kind == "snapshot":
            self._require_attempt_scope(scope)
            self._require_kind(data.get("review"), "review", scope)
        elif kind == "human_decision":
            self._require_attempt_scope(scope)
            self._require_kind(data.get("snapshot"), "snapshot", scope)
            actor = data.get("actor")
            if not isinstance(actor, dict) or actor.get("kind") != "human":
                raise ValueError("human decision must have a human actor")
            require_text(actor.get("id"), "human decision actor id")
            require_text(data.get("decision"), "human decision")
            require_text(data.get("reason"), "human decision reason")
            require_text(data.get("source"), "human decision source")
        elif kind == "outcome":
            stage = require_text(data.get("stage"), "outcome stage")
            expected_scope = STAGE_SCOPE_KEYS.get(stage)
            if expected_scope is None:
                raise ValueError("unsupported outcome stage")
            if set(scope) != expected_scope:
                raise ValueError(f"{stage} outcome has the wrong scope")
            if "attempt_id" in scope:
                self._require_attempt_scope(scope)
            elif "issue_id" in scope:
                self._require_issue_scope(scope)
            require_text(data.get("action"), "outcome action")
            if data.get("status") not in {"completed", "failed", "partial"}:
                raise ValueError("unsupported outcome status")
            for field in ("inputs", "outputs", "reused"):
                if not isinstance(data.get(field), list):
                    raise ValueError(f"outcome {field} must be a list")
                for artifact_ref in data[field]:
                    if not isinstance(artifact_ref, dict) or set(artifact_ref) != {"kind", "id", "revision", "hash"}:
                        raise ValueError(f"outcome {field} must contain lifecycle references")
                    self.get(artifact_ref)
                    self.assert_reference_scope(artifact_ref, scope)
            if not isinstance(data.get("gaps"), list):
                raise ValueError("outcome gaps must be a list")
            producer = data.get("producer")
            if producer is not None and not isinstance(producer, dict):
                raise ValueError("outcome producer must be an object or null")

        for path, artifact_ref in references(data):
            if kind == "attempt" and path == ("previous",):
                continue
            self.assert_reference_scope(artifact_ref, scope)

    def _validate_review(self, scope: dict, data: dict) -> None:
        self._require_attempt_scope(scope)
        spec = self._require_approved_spec(data, scope)
        code = self._require_kind(data.get("code_state"), "code_state", scope)
        environment = self._require_kind(data.get("environment"), "environment", scope)
        baseline = self._require_kind(data.get("baseline"), "baseline", scope)
        if baseline["data"]["spec"] != data["spec"]:
            raise ValueError("review and baseline use different spec revisions")
        if baseline["data"]["spec_approval"] != data["spec_approval"]:
            raise ValueError("review and baseline use different spec approvals")
        if baseline["data"]["environment"] != data["environment"]:
            raise ValueError("review and baseline use different environments")
        if baseline["data"]["baseline_kind"] != "verification":
            raise ValueError("review requires a verification baseline")
        criteria = {item["id"]: item for item in spec["data"]["criteria"]}
        claims = data.get("claims")
        if not isinstance(claims, list):
            raise ValueError("review claims must be a list")
        claim_ids = []
        review_state = "ready"
        before_records = [self.get(ref) for ref in baseline["data"].get("observations", [])]
        for claim in claims:
            if not isinstance(claim, dict):
                raise ValueError("each review claim must be an object")
            criterion_id = claim.get("criterion_id")
            if criterion_id not in criteria or criterion_id in claim_ids:
                raise ValueError("review claim has unknown or duplicate criterion")
            claim_ids.append(criterion_id)
            status = claim.get("status")
            if status not in CLAIM_STATES:
                raise ValueError("unsupported claim status")
            require_text(claim.get("reason"), "review claim reason")
            observations = self._require_reference_list(claim.get("observations"), "observation", scope)
            for observation in observations:
                self._require_review_observation_inputs(observation, data)
            if status != "verified":
                review_state = "needs-review"
                continue
            after_records = [item for item in observations if item["data"].get("phase") == "after"]
            if not after_records:
                raise ValueError("verified claim requires an after observation")
            for after in after_records:
                observed = after["data"]
                if observed.get("criterion_id") != criterion_id or observed.get("result") != "pass" or observed.get("basis") != "observed":
                    raise ValueError("verified claim requires observed passing evidence for its criterion")
                if (observed.get("spec") != data["spec"]
                        or observed.get("spec_approval") != data["spec_approval"]
                        or observed.get("code_state") != data["code_state"]
                        or observed.get("environment") != data["environment"]):
                    raise ValueError("verified observation is bound to different review inputs")
                comparison = criteria[criterion_id].get("comparison")
                if comparison in {"preserve", "improve"}:
                    comparable = [item for item in before_records
                                  if item["data"].get("criterion_id") == criterion_id
                                  and item["data"].get("test_id") == observed.get("test_id")
                                  and item["data"].get("phase") == "before"]
                    if not comparable:
                        raise ValueError("verified comparison claim requires Before evidence")
                    expected_before = "pass" if comparison == "preserve" else "fail"
                    if not any(item["data"].get("test_meaning") == observed.get("test_meaning")
                               and item["data"].get("environment") == data["environment"]
                               and item["data"].get("result") == expected_before
                               and item["data"].get("basis") == "observed" for item in comparable):
                        raise ValueError(f"{comparison} claim has no matching observed Before result")
        required = {item["id"] for item in criteria.values() if item["required"]}
        if not required <= set(claim_ids):
            review_state = "needs-review"
        additional = self._require_reference_list(data.get("additional_observations"), "observation", scope)
        for observation in additional:
            self._require_review_observation_inputs(observation, data)
        if any(item["data"].get("result") == "fail" for item in additional):
            review_state = "needs-review"
        blockers = data.get("blockers", [])
        if not isinstance(blockers, list):
            raise ValueError("review blockers must be a list")
        for blocker in blockers:
            if not isinstance(blocker, dict):
                raise ValueError("each review blocker must be an object")
            if blocker.get("reason") not in BLOCKER_REASONS:
                raise ValueError("unsupported review blocker reason")
            require_text(blocker.get("source"), "review blocker source")
        if blockers:
            review_state = "blocked"
        for field in ("uncertainties", "inferences"):
            if not isinstance(data.get(field), list):
                raise ValueError(f"review {field} must be a list")
        data["review_state"] = review_state

    @staticmethod
    def _require_review_observation_inputs(observation: dict, review_data: dict) -> None:
        observed = observation["data"]
        for field in ("spec", "spec_approval", "code_state", "environment"):
            if observed.get(field) != review_data.get(field):
                raise ValueError(f"review observation uses a different {field}")

    def _require_kind(self, artifact_ref: object, kind: str, scope: dict) -> dict:
        if not isinstance(artifact_ref, dict):
            raise ValueError(f"{kind} reference must be an object")
        record = self.get(artifact_ref)
        if record["kind"] != kind:
            raise ValueError(f"expected {kind} reference")
        self.assert_reference_scope(artifact_ref, scope)
        return record

    def _require_approved_spec(self, data: dict, scope: dict) -> dict:
        spec_ref = data.get("spec")
        spec = self._require_kind(spec_ref, "spec", scope)
        approval = self._require_kind(data.get("spec_approval"), "spec_approval", scope)
        approval_data = approval["data"]
        if approval_data.get("spec") != spec_ref:
            raise ValueError("spec approval does not bind the selected revision")
        if approval_data.get("actor", {}).get("kind") != "human" or approval_data.get("decision") != "approved":
            raise ValueError("artifact requires an approved human spec decision")
        issue_scope = {key: scope[key] for key in ("project_id", "issue_id")}
        activation = self.current_activation("spec", issue_scope)
        if activation is None or activation["reference"] != spec_ref or activation["approval"] != data.get("spec_approval"):
            raise ValueError("artifact requires the active spec and its activation approval")
        return spec

    def _require_reference_list(self, value: object, kind: str, scope: dict) -> list[dict]:
        if not isinstance(value, list):
            raise ValueError(f"{kind} references must be a list")
        return [self._require_kind(item, kind, scope) for item in value]

    @staticmethod
    def _require_issue_scope(scope: dict) -> None:
        if set(scope) != {"project_id", "issue_id"}:
            raise ValueError("artifact requires issue scope")

    def _require_attempt_scope(self, scope: dict) -> None:
        if set(scope) != {"project_id", "issue_id", "task_id", "attempt_id"}:
            raise ValueError("artifact requires attempt scope")
        row = self.connection.execute(
            """SELECT * FROM lifecycle_records
               WHERE kind='attempt' AND logical_id=? ORDER BY revision DESC LIMIT 1""",
            (scope["attempt_id"],),
        ).fetchone()
        if row is None or self._record(row)["scope"] != scope:
            raise ValueError("artifact scope does not identify an existing attempt")
        issue_scope = {key: scope[key] for key in ("project_id", "issue_id")}
        active = self.current("attempt", issue_scope)
        if active is None or self.get(active)["scope"] != scope:
            raise ValueError("artifact scope does not identify the active attempt")

    def _validate_legacy_evidence(self, scope: dict, evidence_id: str):
        evidence_store = EvidenceStore(self.catalog, EventLog(self.catalog))
        record = evidence_store.resolve(evidence_id)
        if record.task_id != scope.get("task_id"):
            raise ValueError("evidence belongs to another task")
        evidence_store.read_content(evidence_id)
        return record

    def _row_for_reference(self, artifact_ref: object) -> sqlite3.Row:
        if not isinstance(artifact_ref, dict) or set(artifact_ref) != {"kind", "id", "revision", "hash"}:
            raise ValueError("invalid lifecycle reference")
        if artifact_ref["kind"] not in KINDS:
            raise ValueError("invalid lifecycle reference kind")
        require_text(artifact_ref["id"], "lifecycle reference id")
        if not isinstance(artifact_ref["revision"], int) or isinstance(artifact_ref["revision"], bool) or artifact_ref["revision"] < 1:
            raise ValueError("lifecycle reference revision must be a positive integer")
        require_sha256(artifact_ref["hash"], "lifecycle reference hash")
        row = self.connection.execute(
            """SELECT * FROM lifecycle_records
               WHERE kind=? AND logical_id=? AND revision=?""",
            (artifact_ref["kind"], artifact_ref["id"], artifact_ref["revision"]),
        ).fetchone()
        if row is None or row["record_hash"] != artifact_ref["hash"]:
            raise ValueError("unknown or altered lifecycle reference")
        return row

    @staticmethod
    def _record(row: sqlite3.Row) -> dict:
        return {
            "namespace": NAMESPACE,
            "schema_version": SCHEMA_VERSION,
            "sequence": row["sequence"],
            "kind": row["kind"],
            "id": row["logical_id"],
            "revision": row["revision"],
            "hash": row["record_hash"],
            "scope": json.loads(row["scope_json"]),
            "data": json.loads(row["data_json"]),
            "created_at": row["created_at"],
        }

    def _verify_journal(self) -> None:
        previous = ""
        expected_sequence = 1
        for row in self.connection.execute("SELECT * FROM lifecycle_records ORDER BY sequence"):
            if row["sequence"] != expected_sequence or row["previous_hash"] != previous:
                raise ValueError("lifecycle record chain is incomplete")
            document = {
                "namespace": NAMESPACE,
                "schema_version": SCHEMA_VERSION,
                "sequence": row["sequence"],
                "kind": row["kind"],
                "id": row["logical_id"],
                "revision": row["revision"],
                "scope": json.loads(row["scope_json"]),
                "data": json.loads(row["data_json"]),
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            }
            if fingerprint(document) != row["record_hash"]:
                raise ValueError("lifecycle record fingerprint mismatch")
            previous = row["record_hash"]
            expected_sequence += 1

        previous = ""
        expected_sequence = 1
        for row in self.connection.execute("SELECT * FROM lifecycle_activations ORDER BY sequence"):
            if row["sequence"] != expected_sequence or row["previous_hash"] != previous:
                raise ValueError("lifecycle activation chain is incomplete")
            body = {
                "namespace": NAMESPACE,
                "schema_version": SCHEMA_VERSION,
                "sequence": row["sequence"],
                "kind": row["kind"],
                "scope": json.loads(row["scope_json"]),
                "slot": row["slot"],
                "reference": json.loads(row["reference_json"]),
                "approval": None if row["approval_json"] is None else json.loads(row["approval_json"]),
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            }
            if fingerprint(body) != row["record_hash"]:
                raise ValueError("lifecycle activation fingerprint mismatch")
            artifact_ref = body["reference"]
            artifact = self._record(self._row_for_reference(artifact_ref))
            if artifact["kind"] != row["kind"]:
                raise ValueError("lifecycle activation kind mismatch")
            expected_scope = artifact["scope"]
            if artifact["kind"] in {"attempt", "spec"}:
                expected_scope = {key: artifact["scope"][key] for key in ("project_id", "issue_id")}
            if expected_scope != body["scope"]:
                raise ValueError("lifecycle activation scope mismatch")
            if artifact["kind"] == "baseline" and body["slot"] != artifact["data"]["baseline_kind"]:
                raise ValueError("lifecycle baseline activation slot mismatch")
            if artifact["kind"] == "spec":
                approval_ref = body["approval"]
                approval = self._record(self._row_for_reference(approval_ref))
                if (approval["kind"] != "spec_approval"
                        or approval["scope"] != artifact["scope"]
                        or approval["data"].get("spec") != artifact_ref
                        or approval["data"].get("actor", {}).get("kind") != "human"
                        or approval["data"].get("decision") != "approved"):
                    raise ValueError("lifecycle spec activation approval mismatch")
            elif body["approval"] is not None:
                raise ValueError("non-spec lifecycle activation has an approval")
            previous = row["record_hash"]
            expected_sequence += 1

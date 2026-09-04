from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .catalog import Catalog
from .events import EventDraft, EventLog


RESULTS = {"pass", "fail", "not_run", "inconclusive"}
BASES = {"observed", "inferred", "unobserved"}
REDACTION_STATUSES = {"not_needed", "redacted", "reference_only"}
SENSITIVE_FIELD_FRAGMENTS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
}


class EvidenceConflict(ValueError):
    pass


@dataclass(frozen=True)
class RetentionPolicy:
    mode: str
    days: int | None


@dataclass(frozen=True)
class EvidenceDraft:
    evidence_id: str
    task_id: str
    requirement_id: str
    evidence_type: str
    subject_ref: str
    exact_scope: str
    result: str
    basis: str
    fields: dict
    content: bytes
    collection_method: str
    redaction_status: str


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    task_id: str
    requirement_id: str
    evidence_type: str
    subject_ref: str
    exact_scope: str
    result: str
    basis: str
    fields: dict
    content_hash: str
    object_path: Path
    content_size: int
    collection_method: str
    redaction_status: str
    created_at: str
    purged_at: str | None
    purge_reason: str | None
    fingerprint: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _identity_payload(payload: dict) -> dict:
    return payload


class EvidenceStore:
    def __init__(self, catalog: Catalog, events: EventLog) -> None:
        self.catalog = catalog
        self.events = events
        self.catalog.paths.objects.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.catalog.paths.objects, 0o700)

    def put(
        self,
        draft: EvidenceDraft,
        redactor: Callable[[bytes], bytes],
    ) -> EvidenceRecord:
        self._validate(draft)
        task_exists = self.catalog.query_value(
            "SELECT 1 FROM tasks WHERE task_id=?", (draft.task_id,)
        )
        if task_exists is None:
            raise ValueError(f"unknown task: {draft.task_id}")
        redacted = redactor(bytes(draft.content))
        if not isinstance(redacted, bytes):
            raise ValueError("redactor must return bytes")

        content_hash = hashlib.sha256(redacted).hexdigest()
        object_relpath = f"{content_hash[:2]}/{content_hash[2:]}"
        object_path = self.catalog.paths.objects / object_relpath
        self._write_object(object_path, redacted, content_hash)
        created_at = _now()
        fingerprint = self._fingerprint(draft, content_hash)

        with self.catalog.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM evidence WHERE evidence_id=?", (draft.evidence_id,)
            ).fetchone()
            if existing is not None:
                if existing["fingerprint"] != fingerprint:
                    raise EvidenceConflict(
                        f"evidence_id {draft.evidence_id!r} already has different content"
                    )
                return self._from_row(existing)

            connection.execute(
                """
                INSERT INTO evidence(
                    evidence_id, task_id, requirement_id, evidence_type,
                    subject_ref, exact_scope, result, basis, fields_json,
                    content_hash, object_relpath, content_size, collection_method,
                    redaction_status, fingerprint, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.evidence_id,
                    draft.task_id,
                    draft.requirement_id,
                    draft.evidence_type,
                    draft.subject_ref,
                    draft.exact_scope,
                    draft.result,
                    draft.basis,
                    self._canonical_json(draft.fields),
                    content_hash,
                    object_relpath,
                    len(redacted),
                    draft.collection_method,
                    draft.redaction_status,
                    fingerprint,
                    created_at,
                ),
            )
            self.events.append_in_transaction(
                EventDraft(
                    event_id=f"evidence-recorded:{draft.evidence_id}",
                    task_id=draft.task_id,
                    event_type="evidence.recorded",
                    event_version=1,
                    occurred_at=created_at,
                    payload={
                        "evidence_id": draft.evidence_id,
                        "requirement_id": draft.requirement_id,
                        "evidence_type": draft.evidence_type,
                        "content_hash": content_hash,
                    },
                    collection_method="evidence-store",
                    redaction_status="reference_only",
                ),
                _identity_payload,
                connection,
            )
            row = connection.execute(
                "SELECT * FROM evidence WHERE evidence_id=?", (draft.evidence_id,)
            ).fetchone()
            return self._from_row(row)

    def resolve(self, evidence_id: str) -> EvidenceRecord:
        row = self.catalog.connection.execute(
            "SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown evidence: {evidence_id}")
        if row["purged_at"] is not None:
            raise ValueError(f"evidence is purged: {evidence_id}")
        return self._from_row(row)

    def list_for_task(self, task_id: str) -> list[EvidenceRecord]:
        rows = self.catalog.connection.execute(
            """
            SELECT * FROM evidence
            WHERE task_id=? AND purged_at IS NULL
            ORDER BY created_at, evidence_id
            """,
            (task_id,),
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def read_content(self, evidence_id: str) -> bytes:
        record = self.resolve(evidence_id)
        content = record.object_path.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != record.content_hash:
            raise ValueError(
                f"evidence hash mismatch: expected {record.content_hash}, got {actual_hash}"
            )
        return content

    def retention(self) -> RetentionPolicy:
        row = self.catalog.connection.execute(
            "SELECT mode, days FROM retention_policy WHERE singleton=1"
        ).fetchone()
        return RetentionPolicy(mode=row["mode"], days=row["days"])

    def set_retention(self, policy: RetentionPolicy) -> None:
        if policy.mode == "keep_until_user_deletes":
            if policy.days is not None:
                raise ValueError("days must be null for keep_until_user_deletes")
        elif policy.mode == "days":
            if not isinstance(policy.days, int) or isinstance(policy.days, bool) or policy.days < 1:
                raise ValueError("days must be a positive integer")
        else:
            raise ValueError("retention mode is invalid")
        with self.catalog.transaction() as connection:
            connection.execute(
                "UPDATE retention_policy SET mode=?, days=? WHERE singleton=1",
                (policy.mode, policy.days),
            )

    def purge(self, evidence_id: str, reason: str) -> None:
        reason = _required_text(reason, "reason")
        purged_at = _now()
        with self.catalog.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"unknown evidence: {evidence_id}")
            if row["purged_at"] is not None:
                return
            connection.execute(
                "UPDATE evidence SET purged_at=?, purge_reason=? WHERE evidence_id=?",
                (purged_at, reason, evidence_id),
            )
            self.events.append_in_transaction(
                EventDraft(
                    event_id=f"evidence-purged:{evidence_id}",
                    task_id=row["task_id"],
                    event_type="evidence.purged",
                    event_version=1,
                    occurred_at=purged_at,
                    payload={
                        "evidence_id": evidence_id,
                        "content_hash": row["content_hash"],
                        "reason": reason,
                    },
                    collection_method="explicit-user-purge",
                    redaction_status="reference_only",
                ),
                _identity_payload,
                connection,
            )

        remaining_references = self.catalog.query_value(
            """
            SELECT COUNT(*) FROM evidence
            WHERE content_hash=? AND purged_at IS NULL
            """,
            (row["content_hash"],),
        )
        if remaining_references == 0:
            object_path = self.catalog.paths.objects / row["object_relpath"]
            if object_path.exists():
                object_path.unlink()

    @staticmethod
    def _validate(draft: EvidenceDraft) -> None:
        for name in (
            "evidence_id",
            "task_id",
            "requirement_id",
            "evidence_type",
            "subject_ref",
            "exact_scope",
            "collection_method",
        ):
            _required_text(getattr(draft, name), name)
        if draft.result not in RESULTS:
            raise ValueError("result is invalid")
        if draft.basis not in BASES:
            raise ValueError("basis is invalid")
        if draft.redaction_status not in REDACTION_STATUSES:
            raise ValueError("redaction_status is invalid")
        if not isinstance(draft.fields, dict) or not draft.fields:
            raise ValueError("fields must be a non-empty dictionary")
        for key in draft.fields:
            normalized = str(key).lower()
            if any(fragment in normalized for fragment in SENSITIVE_FIELD_FRAGMENTS):
                raise ValueError(f"sensitive field is not allowed in metadata: {key}")
        if not isinstance(draft.content, bytes):
            raise ValueError("content must be bytes")

    def _write_object(self, path: Path, content: bytes, expected_hash: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path.parent, 0o700)
        if path.exists():
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError("existing evidence object hash mismatch")
            return

        descriptor, temporary_name = tempfile.mkstemp(prefix=".incoming-", dir=path.parent)
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            os.chmod(path, 0o600)
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def _fingerprint(self, draft: EvidenceDraft, content_hash: str) -> str:
        document = asdict(draft)
        document.pop("content")
        document["content_hash"] = content_hash
        return hashlib.sha256(self._canonical_json(document).encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_json(value: object) -> str:
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"metadata must be JSON serializable: {error}") from error

    def _from_row(self, row: object) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=row["evidence_id"],
            task_id=row["task_id"],
            requirement_id=row["requirement_id"],
            evidence_type=row["evidence_type"],
            subject_ref=row["subject_ref"],
            exact_scope=row["exact_scope"],
            result=row["result"],
            basis=row["basis"],
            fields=json.loads(row["fields_json"]),
            content_hash=row["content_hash"],
            object_path=self.catalog.paths.objects / row["object_relpath"],
            content_size=row["content_size"],
            collection_method=row["collection_method"],
            redaction_status=row["redaction_status"],
            created_at=row["created_at"],
            purged_at=row["purged_at"],
            purge_reason=row["purge_reason"],
            fingerprint=row["fingerprint"],
        )

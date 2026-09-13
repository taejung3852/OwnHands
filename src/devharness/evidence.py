from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .catalog import Catalog
from .events import EventDraft, EventLog


RESULTS = {"pass", "fail", "not_run", "inconclusive"}
BASES = {"observed", "inferred", "unobserved"}
REDACTION_STATUSES = {"not_needed", "redacted", "reference_only"}
EVIDENCE_TYPES = {
    "active_configuration",
    "approval_lifecycle",
    "configuration_conflict",
    "direct_feature_probe",
    "event_projection_sequence",
    "feature_impact",
    "file_creation",
    "hook_execution",
    "instruction_loading",
    "mcp_capability",
    "regression_gate",
    "rule_probe",
    "sandbox_probe",
    "test_execution",
    "workspace_diff",
    "workspace_restore_point",
}
SENSITIVE_FIELD_FRAGMENTS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
}
SENSITIVE_FIELD_MARKERS = {
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "privatekey",
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
    inference_from: tuple[str, ...] = ()
    conflict_refs: tuple[str, ...] = ()


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
    inference_from: tuple[str, ...]
    conflict_refs: tuple[str, ...]
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
        if not catalog.readonly:
            self.catalog.paths.objects.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(self.catalog.paths.objects, 0o700)
            self.reconcile_objects()

    @classmethod
    def open_readonly(cls, catalog: Catalog) -> "EvidenceStore":
        if not catalog.readonly:
            raise ValueError('Evidence reader requires a read-only catalog')
        return cls(catalog, EventLog(catalog))

    def _require_writable(self) -> None:
        if self.catalog.readonly:
            raise PermissionError('Evidence store is read-only')

    def put(
        self,
        draft: EvidenceDraft,
        redactor: Callable[[bytes], bytes],
    ) -> EvidenceRecord:
        self._require_writable()
        self._validate(draft)
        task_exists = self.catalog.query_value(
            "SELECT 1 FROM tasks WHERE task_id=?", (draft.task_id,)
        )
        if task_exists is None:
            raise ValueError(f"unknown task: {draft.task_id}")
        redacted = redactor(bytes(draft.content))
        if not isinstance(redacted, bytes):
            raise ValueError("redactor must return bytes")
        if not redacted:
            raise ValueError("redacted content must not be empty")

        content_hash = hashlib.sha256(redacted).hexdigest()
        object_relpath = f"{content_hash[:2]}/{content_hash[2:]}"
        object_path = self.catalog.paths.objects / object_relpath
        created_at = _now()
        fingerprint = self._fingerprint(draft, content_hash)

        created_object = False
        try:
            with self.catalog.transaction() as connection:
                existing = connection.execute(
                    "SELECT * FROM evidence WHERE evidence_id=?", (draft.evidence_id,)
                ).fetchone()
                if existing is not None:
                    if existing["fingerprint"] != fingerprint:
                        raise EvidenceConflict(
                            f"evidence_id {draft.evidence_id!r} already has different content"
                        )
                    record = self._from_row(existing)
                    self._validate_object(record)
                    return record

                created_object = self._write_object(
                    object_path, redacted, content_hash
                )

                connection.execute(
                    """
                    INSERT INTO evidence(
                        evidence_id, task_id, requirement_id, evidence_type,
                        subject_ref, exact_scope, result, basis, fields_json,
                        content_hash, object_relpath, content_size, collection_method,
                        redaction_status, inference_from_json, conflict_refs_json,
                        fingerprint, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        self._canonical_json(list(draft.inference_from)),
                        self._canonical_json(list(draft.conflict_refs)),
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
        except BaseException:
            if created_object:
                references = self.catalog.query_value(
                    "SELECT COUNT(*) FROM evidence WHERE content_hash=?",
                    (content_hash,),
                )
                if references == 0 and object_path.exists():
                    object_path.unlink()
            raise

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
        return self._validate_object(record)

    @staticmethod
    def _validate_object(record: EvidenceRecord) -> bytes:
        content = record.object_path.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != record.content_hash:
            raise ValueError(
                f"evidence hash mismatch: expected {record.content_hash}, got {actual_hash}"
            )
        if len(content) != record.content_size:
            raise ValueError(
                f"evidence size mismatch: expected {record.content_size}, got {len(content)}"
            )
        return content

    def retention(self) -> RetentionPolicy:
        row = self.catalog.connection.execute(
            "SELECT mode, days FROM retention_policy WHERE singleton=1"
        ).fetchone()
        return RetentionPolicy(mode=row["mode"], days=row["days"])

    def set_retention(self, policy: RetentionPolicy) -> None:
        self._require_writable()
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
        self._require_writable()
        reason = _required_text(reason, "reason")
        purged_at = _now()
        trash_path: Path | None = None
        object_path: Path | None = None
        try:
            with self.catalog.transaction() as connection:
                row = connection.execute(
                    "SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,)
                ).fetchone()
                if row is None:
                    raise ValueError(f"unknown evidence: {evidence_id}")
                if row["purged_at"] is None:
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
                    connection.execute(
                        "UPDATE evidence SET purged_at=?, purge_reason=? WHERE evidence_id=?",
                        (purged_at, reason, evidence_id),
                    )
                remaining_references = connection.execute(
                    """
                    SELECT COUNT(*) FROM evidence
                    WHERE content_hash=? AND purged_at IS NULL
                    """,
                    (row["content_hash"],),
                ).fetchone()[0]
                object_path = self.catalog.paths.objects / row["object_relpath"]
                purge_key = hashlib.sha256(evidence_id.encode("utf-8")).hexdigest()
                trash_path = object_path.with_name(
                    f".{object_path.name}.purging.{purge_key}"
                )
                if remaining_references == 0:
                    if object_path.exists() and not trash_path.exists():
                        os.replace(object_path, trash_path)
        except BaseException:
            if (
                trash_path is not None
                and object_path is not None
                and trash_path.exists()
                and not object_path.exists()
            ):
                os.replace(trash_path, object_path)
                os.chmod(object_path, 0o600)
            raise

        if trash_path is not None and trash_path.exists():
            trash_path.unlink()

    def reconcile_objects(self, grace_period_seconds: int = 300) -> list[Path]:
        self._require_writable()
        if (
            not isinstance(grace_period_seconds, int)
            or isinstance(grace_period_seconds, bool)
            or grace_period_seconds < 0
        ):
            raise ValueError("grace_period_seconds must be a non-negative integer")
        cutoff = time.time() - grace_period_seconds
        removed: list[Path] = []
        with self.catalog.transaction() as connection:
            active_paths = {
                self.catalog.paths.objects / row["object_relpath"]
                for row in connection.execute(
                    "SELECT object_relpath FROM evidence WHERE purged_at IS NULL"
                ).fetchall()
            }
            for trash_path in sorted(self.catalog.paths.objects.rglob(".*.purging*")):
                marker = trash_path.name.find(".purging", 1)
                if marker < 0:
                    continue
                original_name = trash_path.name[1:marker]
                original_path = trash_path.with_name(original_name)
                if original_path in active_paths and not original_path.exists():
                    os.replace(trash_path, original_path)
                    os.chmod(original_path, 0o600)
                elif trash_path.stat().st_mtime <= cutoff:
                    trash_path.unlink()
                    removed.append(trash_path)
            for path in sorted(self.catalog.paths.objects.rglob("*")):
                if (
                    not path.is_file()
                    or path in active_paths
                    or ".purging" in path.name
                ):
                    continue
                if path.stat().st_mtime > cutoff:
                    continue
                path.unlink()
                removed.append(path)
        return removed

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
        if draft.evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"unknown evidence_type: {draft.evidence_type}")
        if draft.result not in RESULTS:
            raise ValueError("result is invalid")
        if draft.basis not in BASES:
            raise ValueError("basis is invalid")
        if draft.redaction_status not in REDACTION_STATUSES:
            raise ValueError("redaction_status is invalid")
        if (
            any(not isinstance(ref, str) or not ref.strip() for ref in draft.inference_from)
            or len(draft.inference_from) != len(set(draft.inference_from))
        ):
            raise ValueError("inference_from must be unique")
        if (
            any(not isinstance(ref, str) or not ref.strip() for ref in draft.conflict_refs)
            or len(draft.conflict_refs) != len(set(draft.conflict_refs))
        ):
            raise ValueError("conflict_refs must be unique")
        if draft.basis == "inferred" and not draft.inference_from:
            raise ValueError("inferred Evidence requires inference_from")
        if not isinstance(draft.fields, dict) or not draft.fields:
            raise ValueError("fields must be a non-empty dictionary")
        for key in EvidenceStore._field_names(draft.fields):
            normalized = key.lower()
            compact = "".join(
                character for character in normalized if character.isalnum()
            )
            if any(fragment in normalized for fragment in SENSITIVE_FIELD_FRAGMENTS) or any(
                marker in compact for marker in SENSITIVE_FIELD_MARKERS
            ):
                raise ValueError(f"sensitive field is not allowed in metadata: {key}")
        if not isinstance(draft.content, bytes):
            raise ValueError("content must be bytes")
        if not draft.content:
            raise ValueError("content must not be empty")

    @staticmethod
    def _field_names(value: object) -> list[str]:
        if isinstance(value, dict):
            return [str(key) for key in value] + [
                nested
                for item in value.values()
                for nested in EvidenceStore._field_names(item)
            ]
        if isinstance(value, (list, tuple)):
            return [
                nested for item in value for nested in EvidenceStore._field_names(item)
            ]
        return []

    def _write_object(self, path: Path, content: bytes, expected_hash: str) -> bool:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path.parent, 0o700)
        if path.exists():
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError("existing evidence object hash mismatch")
            os.chmod(path, 0o600)
            return False

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
        return True

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
        try:
            fields = json.loads(row["fields_json"])
            inference_from = tuple(json.loads(row["inference_from_json"]))
            conflict_refs = tuple(json.loads(row["conflict_refs_json"]))
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError("evidence metadata is not valid JSON") from error
        expected_fingerprint = self._fingerprint(
            EvidenceDraft(
                evidence_id=row["evidence_id"],
                task_id=row["task_id"],
                requirement_id=row["requirement_id"],
                evidence_type=row["evidence_type"],
                subject_ref=row["subject_ref"],
                exact_scope=row["exact_scope"],
                result=row["result"],
                basis=row["basis"],
                fields=fields,
                content=b"ignored-for-record-fingerprint",
                collection_method=row["collection_method"],
                redaction_status=row["redaction_status"],
                inference_from=inference_from,
                conflict_refs=conflict_refs,
            ),
            row["content_hash"],
        )
        if row["fingerprint"] != expected_fingerprint:
            raise ValueError("evidence metadata fingerprint mismatch")
        expected_relpath = f"{row['content_hash'][:2]}/{row['content_hash'][2:]}"
        if row["object_relpath"] != expected_relpath:
            raise ValueError("evidence object path does not match content hash")
        return EvidenceRecord(
            evidence_id=row["evidence_id"],
            task_id=row["task_id"],
            requirement_id=row["requirement_id"],
            evidence_type=row["evidence_type"],
            subject_ref=row["subject_ref"],
            exact_scope=row["exact_scope"],
            result=row["result"],
            basis=row["basis"],
            fields=fields,
            content_hash=row["content_hash"],
            object_path=self.catalog.paths.objects / row["object_relpath"],
            content_size=row["content_size"],
            collection_method=row["collection_method"],
            redaction_status=row["redaction_status"],
            inference_from=inference_from,
            conflict_refs=conflict_refs,
            created_at=row["created_at"],
            purged_at=row["purged_at"],
            purge_reason=row["purge_reason"],
            fingerprint=row["fingerprint"],
        )

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from .paths import DataPaths


SCHEMA_VERSION = 3


def projection_fingerprint(
    task_id: str,
    projected_sequence: int,
    state: str,
    projection_json: str,
) -> str:
    envelope = json.dumps(
        [task_id, projected_sequence, state, projection_json],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(envelope.encode("utf-8")).hexdigest()


def _evidence_fingerprint(row: sqlite3.Row, *, include_lineage: bool) -> str:
    try:
        document = {
            "evidence_id": row["evidence_id"],
            "task_id": row["task_id"],
            "requirement_id": row["requirement_id"],
            "evidence_type": row["evidence_type"],
            "subject_ref": row["subject_ref"],
            "exact_scope": row["exact_scope"],
            "result": row["result"],
            "basis": row["basis"],
            "fields": json.loads(row["fields_json"]),
            "collection_method": row["collection_method"],
            "redaction_status": row["redaction_status"],
            "content_hash": row["content_hash"],
        }
        if include_lineage:
            document["inference_from"] = json.loads(row["inference_from_json"])
            document["conflict_refs"] = json.loads(row["conflict_refs_json"])
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError("legacy Evidence metadata is invalid") from error
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event_fingerprint(row: sqlite3.Row, *, include_sequence: bool) -> str:
    try:
        payload = json.loads(row["payload_json"])
        if not isinstance(payload, dict):
            raise TypeError("Event payload is not an object")
        document = {
            "event_id": row["event_id"],
            "task_id": row["task_id"],
            "event_type": row["event_type"],
            "event_version": row["event_version"],
            "occurred_at": row["occurred_at"],
            "payload": payload,
            "collection_method": row["collection_method"],
            "redaction_status": row["redaction_status"],
        }
        if include_sequence:
            document["sequence"] = row["sequence"]
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError("legacy Event metadata is invalid") from error
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _legacy_events_for_v3_migration(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:
    rows = connection.execute(
        "SELECT * FROM events ORDER BY task_id, sequence"
    ).fetchall()
    sequences_by_task: dict[str, list[int]] = {}
    for row in rows:
        sequences_by_task.setdefault(row["task_id"], []).append(row["sequence"])
        if row["fingerprint"] != _event_fingerprint(row, include_sequence=False):
            raise RuntimeError("legacy Event fingerprint mismatch")
    if any(len(sequences) > 1 for sequences in sequences_by_task.values()):
        raise RuntimeError("legacy Event order is unverifiable")
    if any(
        sequences != list(range(1, len(sequences) + 1))
        for sequences in sequences_by_task.values()
    ):
        raise RuntimeError("legacy Event sequence integrity failure")
    return rows


class Catalog:
    def __init__(self, paths: DataPaths, connection: sqlite3.Connection) -> None:
        self.paths = paths
        self.path = paths.catalog
        self.connection = connection

    @classmethod
    def open(cls, paths: DataPaths | Path | str) -> "Catalog":
        if not isinstance(paths, DataPaths):
            paths = DataPaths.resolve(paths)
        paths.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(paths.root, 0o700)

        connection = sqlite3.connect(
            paths.catalog,
            timeout=5.0,
            autocommit=True,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")

        catalog = cls(paths, connection)
        catalog._initialize()
        if catalog.query_value("PRAGMA integrity_check") != "ok":
            connection.close()
            raise RuntimeError("SQLite catalog integrity check failed")
        os.chmod(paths.catalog, 0o600)
        return catalog

    def _initialize(self) -> None:
        has_schema_metadata = self.connection.execute(
            """
            SELECT 1 FROM sqlite_schema
            WHERE type='table' AND name='schema_metadata'
            """
        ).fetchone()
        if has_schema_metadata is not None:
            existing_version = self.query_value(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            )
            has_events = self.connection.execute(
                "SELECT 1 FROM sqlite_schema WHERE type='table' AND name='events'"
            ).fetchone()
            if existing_version == "1" and has_events is not None:
                with self.transaction() as connection:
                    locked_version = connection.execute(
                        """
                        SELECT value FROM schema_metadata
                        WHERE key='schema_version'
                        """
                    ).fetchone()[0]
                    if locked_version == "1":
                        _legacy_events_for_v3_migration(connection)

        self.connection.executescript(
            f"""
            BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) STRICT;
            INSERT INTO schema_metadata(key, value)
            VALUES ('schema_version', '{SCHEMA_VERSION}')
            ON CONFLICT(key) DO NOTHING;

            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                locator TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS worktrees (
                worktree_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(project_id),
                locator TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(project_id, locator)
            ) STRICT;

            CREATE TRIGGER IF NOT EXISTS projects_no_update
            BEFORE UPDATE ON projects
            BEGIN
                SELECT RAISE(ABORT, 'project identities are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS projects_no_delete
            BEFORE DELETE ON projects
            BEGIN
                SELECT RAISE(ABORT, 'project identities are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS worktrees_no_update
            BEFORE UPDATE ON worktrees
            BEGIN
                SELECT RAISE(ABORT, 'worktree identities are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS worktrees_no_delete
            BEFORE DELETE ON worktrees
            BEGIN
                SELECT RAISE(ABORT, 'worktree identities are immutable');
            END;

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(project_id),
                worktree_id TEXT NOT NULL REFERENCES worktrees(worktree_id),
                mode TEXT NOT NULL CHECK(mode IN ('managed', 'imported')),
                commit_hash TEXT NOT NULL,
                branch TEXT NOT NULL,
                cwd TEXT NOT NULL,
                environment_ref TEXT NOT NULL,
                created_at TEXT NOT NULL
            ) STRICT;

            CREATE TRIGGER IF NOT EXISTS tasks_no_update
            BEFORE UPDATE ON tasks
            BEGIN
                SELECT RAISE(ABORT, 'task snapshots are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS tasks_project_worktree_scope
            BEFORE INSERT ON tasks
            WHEN NOT EXISTS (
                SELECT 1 FROM worktrees
                WHERE worktree_id = NEW.worktree_id
                  AND project_id = NEW.project_id
            )
            BEGIN
                SELECT RAISE(ABORT, 'task project/worktree scope mismatch');
            END;

            CREATE TRIGGER IF NOT EXISTS tasks_no_delete
            BEFORE DELETE ON tasks
            BEGIN
                SELECT RAISE(ABORT, 'task snapshots are immutable');
            END;

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(task_id),
                sequence INTEGER NOT NULL CHECK(sequence > 0),
                event_type TEXT NOT NULL,
                event_version INTEGER NOT NULL CHECK(event_version > 0),
                occurred_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                collection_method TEXT NOT NULL,
                redaction_status TEXT NOT NULL CHECK(
                    redaction_status IN ('not_needed', 'redacted', 'reference_only')
                ),
                fingerprint TEXT NOT NULL,
                UNIQUE(task_id, sequence)
            ) STRICT;

            CREATE TRIGGER IF NOT EXISTS events_no_update
            BEFORE UPDATE ON events
            BEGIN
                SELECT RAISE(ABORT, 'events are append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS events_no_delete
            BEFORE DELETE ON events
            BEGIN
                SELECT RAISE(ABORT, 'events are append-only');
            END;

            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(task_id),
                requirement_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                subject_ref TEXT NOT NULL,
                exact_scope TEXT NOT NULL,
                result TEXT NOT NULL CHECK(
                    result IN ('pass', 'fail', 'not_run', 'inconclusive')
                ),
                basis TEXT NOT NULL CHECK(
                    basis IN ('observed', 'inferred', 'unobserved')
                ),
                fields_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                object_relpath TEXT NOT NULL,
                content_size INTEGER NOT NULL CHECK(content_size >= 0),
                collection_method TEXT NOT NULL,
                redaction_status TEXT NOT NULL CHECK(
                    redaction_status IN ('not_needed', 'redacted', 'reference_only')
                ),
                inference_from_json TEXT NOT NULL DEFAULT '[]',
                conflict_refs_json TEXT NOT NULL DEFAULT '[]',
                fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                purged_at TEXT,
                purge_reason TEXT
            ) STRICT;

            CREATE INDEX IF NOT EXISTS evidence_task_requirement
            ON evidence(task_id, requirement_id, evidence_type);

            CREATE TRIGGER IF NOT EXISTS evidence_canonical_fields_immutable
            BEFORE UPDATE ON evidence
            WHEN
                NEW.evidence_id != OLD.evidence_id OR
                NEW.task_id != OLD.task_id OR
                NEW.requirement_id != OLD.requirement_id OR
                NEW.evidence_type != OLD.evidence_type OR
                NEW.subject_ref != OLD.subject_ref OR
                NEW.exact_scope != OLD.exact_scope OR
                NEW.result != OLD.result OR
                NEW.basis != OLD.basis OR
                NEW.fields_json != OLD.fields_json OR
                NEW.content_hash != OLD.content_hash OR
                NEW.object_relpath != OLD.object_relpath OR
                NEW.content_size != OLD.content_size OR
                NEW.collection_method != OLD.collection_method OR
                NEW.redaction_status != OLD.redaction_status OR
                NEW.inference_from_json != OLD.inference_from_json OR
                NEW.conflict_refs_json != OLD.conflict_refs_json OR
                NEW.fingerprint != OLD.fingerprint OR
                NEW.created_at != OLD.created_at
            BEGIN
                SELECT RAISE(ABORT, 'canonical evidence fields are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS evidence_purge_is_monotonic
            BEFORE UPDATE ON evidence
            WHEN
                NOT (
                    NEW.purged_at IS OLD.purged_at AND
                    NEW.purge_reason IS OLD.purge_reason
                ) AND (
                    OLD.purged_at IS NOT NULL OR
                    NEW.purged_at IS NULL OR
                    NEW.purge_reason IS NULL OR
                    trim(NEW.purge_reason) = ''
                )
            BEGIN
                SELECT RAISE(ABORT, 'evidence purge transition is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS evidence_purge_requires_audit_event
            BEFORE UPDATE ON evidence
            WHEN OLD.purged_at IS NULL
              AND NEW.purged_at IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM events
                  WHERE event_id = 'evidence-purged:' || OLD.evidence_id
                    AND task_id = OLD.task_id
                    AND event_type = 'evidence.purged'
                    AND occurred_at = NEW.purged_at
                    AND collection_method = 'explicit-user-purge'
                    AND redaction_status = 'reference_only'
                    AND json_extract(payload_json, '$.evidence_id') = OLD.evidence_id
                    AND json_extract(payload_json, '$.content_hash') = OLD.content_hash
                    AND json_extract(payload_json, '$.reason') = NEW.purge_reason
              )
            BEGIN
                SELECT RAISE(ABORT, 'evidence purge requires matching audit event');
            END;

            CREATE TRIGGER IF NOT EXISTS evidence_no_delete
            BEFORE DELETE ON evidence
            BEGIN
                SELECT RAISE(ABORT, 'evidence rows are append-only; use purge');
            END;

            CREATE TABLE IF NOT EXISTS retention_policy (
                singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                mode TEXT NOT NULL CHECK(mode IN ('keep_until_user_deletes', 'days')),
                days INTEGER CHECK(days IS NULL OR days > 0)
            ) STRICT;
            INSERT INTO retention_policy(singleton, mode, days)
            VALUES (1, 'keep_until_user_deletes', NULL)
            ON CONFLICT(singleton) DO NOTHING;

            CREATE TABLE IF NOT EXISTS task_projections (
                task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
                projected_sequence INTEGER NOT NULL CHECK(projected_sequence >= 0),
                state TEXT NOT NULL CHECK(state IN ('ready', 'failed')),
                projection_json TEXT NOT NULL,
                projection_hash TEXT NOT NULL DEFAULT '',
                last_error TEXT,
                updated_at TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS control_validations (
                record_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(task_id),
                record_json TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL
            ) STRICT;

            CREATE TRIGGER IF NOT EXISTS control_validations_no_update
            BEFORE UPDATE ON control_validations
            BEGIN
                SELECT RAISE(ABORT, 'control validations are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS control_validations_no_delete
            BEFORE DELETE ON control_validations
            BEGIN
                SELECT RAISE(ABORT, 'control validations are immutable');
            END;

            CREATE INDEX IF NOT EXISTS control_validations_task
            ON control_validations(task_id);
            COMMIT;
            """
        )
        version = self.query_value(
            "SELECT value FROM schema_metadata WHERE key='schema_version'"
        )
        if version == "1":
            self._migrate_v1_to_v2()
            version = self.query_value(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            )
        if version == "2":
            self._migrate_v2_to_v3()
            version = self.query_value(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            )
        if version != str(SCHEMA_VERSION):
            raise RuntimeError(
                f"unsupported catalog schema version: {version!r}; expected {SCHEMA_VERSION}"
            )

    def _migrate_v1_to_v2(self) -> None:
        with self.transaction() as connection:
            version = connection.execute(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ).fetchone()[0]
            if version == "2":
                return
            if version != "1":
                raise RuntimeError(
                    f"unsupported catalog schema version during migration: {version!r}"
                )
            _legacy_events_for_v3_migration(connection)
            projection_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(task_projections)"
                ).fetchall()
            }
            if "projection_hash" not in projection_columns:
                connection.execute(
                    """
                    ALTER TABLE task_projections
                    ADD COLUMN projection_hash TEXT NOT NULL DEFAULT ''
                    """
                )
            connection.execute("DELETE FROM task_projections")

            evidence_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(evidence)").fetchall()
            }
            has_lineage_columns = {
                "inference_from_json",
                "conflict_refs_json",
            } <= evidence_columns
            connection.execute("DROP TRIGGER IF EXISTS evidence_canonical_fields_immutable")
            for column in ("inference_from_json", "conflict_refs_json"):
                if column not in evidence_columns:
                    connection.execute(
                        f"ALTER TABLE evidence ADD COLUMN {column} "
                        "TEXT NOT NULL DEFAULT '[]'"
                    )
            rows = connection.execute("SELECT * FROM evidence").fetchall()
            for row in rows:
                legacy_fingerprint = _evidence_fingerprint(
                    row, include_lineage=has_lineage_columns
                )
                if row["fingerprint"] != legacy_fingerprint:
                    raise RuntimeError("legacy Evidence fingerprint mismatch")
                connection.execute(
                    "UPDATE evidence SET fingerprint=? WHERE evidence_id=?",
                    (
                        _evidence_fingerprint(row, include_lineage=True),
                        row["evidence_id"],
                    ),
                )
            connection.execute(
                """
                CREATE TRIGGER evidence_canonical_fields_immutable
                BEFORE UPDATE ON evidence
                WHEN
                    NEW.evidence_id != OLD.evidence_id OR
                    NEW.task_id != OLD.task_id OR
                    NEW.requirement_id != OLD.requirement_id OR
                    NEW.evidence_type != OLD.evidence_type OR
                    NEW.subject_ref != OLD.subject_ref OR
                    NEW.exact_scope != OLD.exact_scope OR
                    NEW.result != OLD.result OR
                    NEW.basis != OLD.basis OR
                    NEW.fields_json != OLD.fields_json OR
                    NEW.content_hash != OLD.content_hash OR
                    NEW.object_relpath != OLD.object_relpath OR
                    NEW.content_size != OLD.content_size OR
                    NEW.collection_method != OLD.collection_method OR
                    NEW.redaction_status != OLD.redaction_status OR
                    NEW.inference_from_json != OLD.inference_from_json OR
                    NEW.conflict_refs_json != OLD.conflict_refs_json OR
                    NEW.fingerprint != OLD.fingerprint OR
                    NEW.created_at != OLD.created_at
                BEGIN
                    SELECT RAISE(ABORT, 'canonical evidence fields are immutable');
                END
                """
            )
            connection.execute(
                "UPDATE schema_metadata SET value='2' WHERE key='schema_version'"
            )

    def _migrate_v2_to_v3(self) -> None:
        with self.transaction() as connection:
            version = connection.execute(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ).fetchone()[0]
            if version == "3":
                return
            if version != "2":
                raise RuntimeError(
                    f"unsupported catalog schema version during migration: {version!r}"
                )
            rows = _legacy_events_for_v3_migration(connection)

            connection.execute("DROP TRIGGER IF EXISTS events_no_update")
            for row in rows:
                connection.execute(
                    "UPDATE events SET fingerprint=? WHERE event_id=?",
                    (
                        _event_fingerprint(row, include_sequence=True),
                        row["event_id"],
                    ),
                )
            connection.execute("DELETE FROM task_projections")
            connection.execute(
                """
                CREATE TRIGGER events_no_update
                BEFORE UPDATE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'events are append-only');
                END
                """
            )
            connection.execute(
                "UPDATE schema_metadata SET value='3' WHERE key='schema_version'"
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise
        else:
            self.connection.execute("COMMIT")

    def query_value(self, sql: str, parameters: Sequence[Any] = ()) -> Any:
        row = self.connection.execute(sql, parameters).fetchone()
        return None if row is None else row[0]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Catalog":
        return self

    def __exit__(self, *_error: object) -> None:
        self.close()

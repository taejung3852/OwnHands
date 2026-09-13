from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Iterator, Sequence

from .paths import DataPaths


SCHEMA_VERSION = 3

_V3_TABLE_COLUMNS = {
    "schema_metadata": {"key", "value"},
    "projects": {"project_id", "locator", "created_at"},
    "worktrees": {"worktree_id", "project_id", "locator", "created_at"},
    "tasks": {
        "task_id",
        "project_id",
        "worktree_id",
        "mode",
        "commit_hash",
        "branch",
        "cwd",
        "environment_ref",
        "created_at",
    },
    "events": {
        "event_id",
        "task_id",
        "sequence",
        "event_type",
        "event_version",
        "occurred_at",
        "payload_json",
        "collection_method",
        "redaction_status",
        "fingerprint",
    },
    "evidence": {
        "evidence_id",
        "task_id",
        "requirement_id",
        "evidence_type",
        "subject_ref",
        "exact_scope",
        "result",
        "basis",
        "fields_json",
        "content_hash",
        "object_relpath",
        "content_size",
        "collection_method",
        "redaction_status",
        "inference_from_json",
        "conflict_refs_json",
        "fingerprint",
        "created_at",
        "purged_at",
        "purge_reason",
    },
    "retention_policy": {"singleton", "mode", "days"},
    "task_projections": {
        "task_id",
        "projected_sequence",
        "state",
        "projection_json",
        "projection_hash",
        "last_error",
        "updated_at",
    },
    "control_validations": {
        "record_id",
        "task_id",
        "record_json",
        "fingerprint",
        "created_at",
    },
}

# Exact table-definition documents produced by the canonical v3 bootstrap and
# the two supported v1 upgrade layouts. The latter retain SQLite's ALTER TABLE
# rendering for the lineage/projection columns.
_V3_TABLE_DEFINITION_DIGESTS = {
    "e35de50ee40fd3d63db590d3f419c4dfbf1c46cc4a352fc47aec87766a2d1f91",
    "2ab933ed695214c5f3b8387e06a95ef9bac1cb049b0164d2a8d57598958b08a7",
    "6a7d5188427c65d7069ea371724c7b8f730699d6092af52d2dd568265d61f6c5",
}

_V3_INDEX_COLUMNS = {
    "evidence_task_requirement": (
        "evidence",
        ("task_id", "requirement_id", "evidence_type"),
    ),
    "control_validations_task": ("control_validations", ("task_id",)),
}

_V3_TRIGGER_TABLES = {
    "projects_no_update": "projects",
    "projects_no_delete": "projects",
    "worktrees_no_update": "worktrees",
    "worktrees_no_delete": "worktrees",
    "tasks_no_update": "tasks",
    "tasks_project_worktree_scope": "tasks",
    "tasks_no_delete": "tasks",
    "events_no_update": "events",
    "events_no_delete": "events",
    "evidence_canonical_fields_immutable": "evidence",
    "evidence_purge_is_monotonic": "evidence",
    "evidence_purge_requires_audit_event": "evidence",
    "evidence_no_delete": "evidence",
    "control_validations_no_update": "control_validations",
    "control_validations_no_delete": "control_validations",
}

_V3_INTEGER_COLUMNS = {
    ("events", "sequence"),
    ("events", "event_version"),
    ("evidence", "content_size"),
    ("retention_policy", "singleton"),
    ("retention_policy", "days"),
    ("task_projections", "projected_sequence"),
}

_V3_NULLABLE_COLUMNS = {
    ("evidence", "purged_at"),
    ("evidence", "purge_reason"),
    ("retention_policy", "singleton"),
    ("retention_policy", "days"),
    ("task_projections", "last_error"),
}

_V3_PRIMARY_KEYS = {
    ("schema_metadata", "key"),
    ("projects", "project_id"),
    ("worktrees", "worktree_id"),
    ("tasks", "task_id"),
    ("events", "event_id"),
    ("evidence", "evidence_id"),
    ("retention_policy", "singleton"),
    ("task_projections", "task_id"),
    ("control_validations", "record_id"),
}

_V3_COLUMN_DEFAULTS = {
    ("evidence", "inference_from_json"): "'[]'",
    ("evidence", "conflict_refs_json"): "'[]'",
    ("task_projections", "projection_hash"): "''",
}

_V3_INDEX_TRIGGER_DEFINITION_DIGEST = (
    "8a6b3d5671a31b43ec56132a4b6f42dfebfe7657667bac28aa4a31c8f86988d0"
)


def _normalize_schema_sql(sql: str) -> str:
    normalized: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(sql):
        character = sql[index]
        if quote is not None:
            normalized.append(character)
            if character == quote:
                if (
                    quote != "]"
                    and index + 1 < len(sql)
                    and sql[index + 1] == quote
                ):
                    index += 1
                    normalized.append(sql[index])
                else:
                    quote = None
        elif character in ("'", '"', "`"):
            quote = character
            normalized.append(character)
        elif character == "[":
            quote = "]"
            normalized.append(character)
        elif not character.isspace():
            normalized.append(character.upper())
        index += 1
    return "".join(normalized)


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
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, TypeError) as error:
            raise RuntimeError("legacy Event metadata is invalid") from error
        task = connection.execute(
            "SELECT mode FROM tasks WHERE task_id=?", (row["task_id"],)
        ).fetchone()
        if (
            row["event_type"] != "task.created"
            or row["event_version"] != 1
            or row["sequence"] != 1
            or task is None
            or payload.get("mode") != task["mode"]
        ):
            raise RuntimeError("legacy Event lifecycle mismatch")
    return rows


class Catalog:
    def __init__(self, paths: DataPaths, connection: sqlite3.Connection, *, readonly: bool = False) -> None:
        self.paths = paths
        self.path = paths.catalog
        self.connection = connection
        self.readonly = readonly

    @classmethod
    def open_readonly(cls, paths: DataPaths | Path | str) -> "Catalog":
        """Open an existing current-schema catalog without initialization or repair."""
        if not isinstance(paths, DataPaths):
            paths = DataPaths.resolve(paths)
        connection = sqlite3.connect(paths.catalog.resolve().as_uri() + '?mode=ro',
                                     uri=True, autocommit=True)
        connection.row_factory = sqlite3.Row
        catalog = cls(paths, connection, readonly=True)
        try:
            connection.execute('PRAGMA query_only=ON')
            connection.execute('PRAGMA foreign_keys=ON')
            if catalog.query_value("SELECT value FROM schema_metadata WHERE key='schema_version'") != str(SCHEMA_VERSION):
                raise RuntimeError('unsupported read-only catalog schema version')
            cls._validate_v3_schema_contract(connection)
            if catalog.query_value('PRAGMA integrity_check') != 'ok':
                raise RuntimeError('SQLite catalog integrity check failed')
        except BaseException:
            connection.close()
            raise
        return catalog

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
        existing_object_count = self.connection.execute(
            "SELECT COUNT(*) FROM sqlite_schema"
        ).fetchone()[0]
        has_schema_metadata = self.connection.execute(
            """
            SELECT 1 FROM sqlite_schema
            WHERE type='table' AND name='schema_metadata'
            """
        ).fetchone()
        if existing_object_count:
            if has_schema_metadata is None:
                raise RuntimeError("missing catalog schema metadata")
            existing_version = self.query_value(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            )
            if existing_version is None:
                raise RuntimeError("missing catalog schema version")
            if existing_version not in {"1", "2", str(SCHEMA_VERSION)}:
                raise RuntimeError(
                    "unsupported catalog schema version: "
                    f"{existing_version!r}; expected one of '1', '2', "
                    f"{str(SCHEMA_VERSION)!r}"
                )
            if existing_version == str(SCHEMA_VERSION):
                self._validate_v3_schema_contract(self.connection)
                return

        with self.transaction() as connection:
            connection.executescript(
                f"""
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
                    f"unsupported catalog schema version: {version!r}; "
                    f"expected {SCHEMA_VERSION}"
                )
            self._validate_v3_schema_contract(connection)

    @staticmethod
    def _validate_v3_schema_contract(connection: sqlite3.Connection) -> None:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_schema
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }
        if tables != set(_V3_TABLE_COLUMNS):
            raise RuntimeError("schema v3 contract mismatch: tables")
        table_definitions = connection.execute(
            """
            SELECT name, sql FROM sqlite_schema
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        table_definition_document = "\n".join(
            f"{row['name']}:{_normalize_schema_sql(row['sql'])}"
            for row in table_definitions
        )
        table_definition_digest = hashlib.sha256(
            table_definition_document.encode("utf-8")
        ).hexdigest()
        if table_definition_digest not in _V3_TABLE_DEFINITION_DIGESTS:
            raise RuntimeError("schema v3 contract mismatch: table definitions")
        for table, expected_columns in _V3_TABLE_COLUMNS.items():
            actual_columns = {
                row["name"]: (
                    row["type"].upper(),
                    bool(row["notnull"]),
                    row["dflt_value"],
                    bool(row["pk"]),
                )
                for row in connection.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }
            expected_signatures = {
                column: (
                    "INTEGER" if (table, column) in _V3_INTEGER_COLUMNS else "TEXT",
                    (table, column) not in _V3_NULLABLE_COLUMNS,
                    _V3_COLUMN_DEFAULTS.get((table, column)),
                    (table, column) in _V3_PRIMARY_KEYS,
                )
                for column in expected_columns
            }
            if actual_columns != expected_signatures:
                raise RuntimeError(
                    f"schema v3 contract mismatch: columns for {table}"
                )

        indexes = {
            row["name"]: row["tbl_name"]
            for row in connection.execute(
                """
                SELECT name, tbl_name FROM sqlite_schema
                WHERE type='index' AND name NOT LIKE 'sqlite_autoindex_%'
                """
            ).fetchall()
        }
        if indexes != {
            name: contract[0] for name, contract in _V3_INDEX_COLUMNS.items()
        }:
            raise RuntimeError("schema v3 contract mismatch: indexes")
        for name, (_table, expected_columns) in _V3_INDEX_COLUMNS.items():
            actual_columns = tuple(
                row["name"]
                for row in connection.execute(f"PRAGMA index_info({name})").fetchall()
            )
            if actual_columns != expected_columns:
                raise RuntimeError(
                    f"schema v3 contract mismatch: index columns for {name}"
                )

        triggers = {
            row["name"]: row["tbl_name"]
            for row in connection.execute(
                "SELECT name, tbl_name FROM sqlite_schema WHERE type='trigger'"
            ).fetchall()
        }
        if triggers != _V3_TRIGGER_TABLES:
            raise RuntimeError("schema v3 contract mismatch: triggers")
        definitions = connection.execute(
            """
            SELECT name, sql FROM sqlite_schema
            WHERE type IN ('index', 'trigger') AND sql IS NOT NULL
            ORDER BY name
            """
        ).fetchall()
        definition_document = "\n".join(
            f"{row['name']}:{' '.join(row['sql'].split())}" for row in definitions
        )
        actual_digest = hashlib.sha256(
            definition_document.encode("utf-8")
        ).hexdigest()
        if actual_digest != _V3_INDEX_TRIGGER_DEFINITION_DIGEST:
            raise RuntimeError(
                "schema v3 contract mismatch: index or trigger definition"
            )

    def _migrate_v1_to_v2(self) -> None:
        transaction = (
            nullcontext(self.connection)
            if self.connection.in_transaction
            else self.transaction()
        )
        with transaction as connection:
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
        transaction = (
            nullcontext(self.connection)
            if self.connection.in_transaction
            else self.transaction()
        )
        with transaction as connection:
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
        if self.readonly:
            raise PermissionError('catalog is read-only')
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

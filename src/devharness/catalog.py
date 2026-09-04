from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from .paths import DataPaths


SCHEMA_VERSION = 1


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
        os.chmod(paths.catalog, 0o600)
        return catalog

    def _initialize(self) -> None:
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
            COMMIT;
            """
        )
        version = self.query_value(
            "SELECT value FROM schema_metadata WHERE key='schema_version'"
        )
        if version != str(SCHEMA_VERSION):
            raise RuntimeError(
                f"unsupported catalog schema version: {version!r}; expected {SCHEMA_VERSION}"
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

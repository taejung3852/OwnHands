from __future__ import annotations

import hashlib
import json
import stat
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from devharness.catalog import Catalog
from devharness.evidence import EvidenceStore
from devharness.events import EventDraft, EventLog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths
from devharness.projections import ProjectionEngine


class IdentityRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "application-support"
        self.paths = DataPaths.resolve(self.root)
        self.catalog = Catalog.open(self.paths)
        self.registry = IdentityRegistry(self.catalog)

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def _create_v2_event_catalog(
        self, name: str, *, tampered_payload: str | None = None
    ) -> tuple[DataPaths, str, str, str]:
        paths = DataPaths.resolve(Path(self.temporary_directory.name) / name)
        with Catalog.open(paths) as catalog:
            registry = IdentityRegistry(catalog)
            project = registry.register_project(f"file:///{name}")
            worktree = registry.register_worktree(
                project.project_id, f"file:///{name}/main"
            )
            task = registry.create_task(
                worktree.worktree_id,
                mode="managed",
                commit="abc123",
                branch="main",
                cwd=f"/{name}",
                environment_ref="legacy-runtime",
            )
            EventLog(catalog).append(
                EventDraft(
                    event_id="legacy-event",
                    task_id=task.task_id,
                    event_type="task.created",
                    event_version=1,
                    occurred_at="2026-09-04T00:00:00+00:00",
                    payload={"mode": "managed"},
                    collection_method="legacy-fixture",
                    redaction_status="not_needed",
                ),
                lambda payload: payload,
            )
            ProjectionEngine(catalog, EventLog(catalog)).project(task.task_id)
            legacy_document = {
                "event_id": "legacy-event",
                "task_id": task.task_id,
                "event_type": "task.created",
                "event_version": 1,
                "occurred_at": "2026-09-04T00:00:00+00:00",
                "payload": {"mode": "managed"},
                "collection_method": "legacy-fixture",
                "redaction_status": "not_needed",
            }

            def canonical(document: dict) -> str:
                return json.dumps(
                    document,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )

            legacy_fingerprint = hashlib.sha256(
                canonical(legacy_document).encode("utf-8")
            ).hexdigest()
            expected_fingerprint = hashlib.sha256(
                canonical({**legacy_document, "sequence": 1}).encode("utf-8")
            ).hexdigest()
            catalog.connection.execute("DROP TRIGGER events_no_update")
            catalog.connection.execute(
                "UPDATE events SET fingerprint=? WHERE event_id='legacy-event'",
                (legacy_fingerprint,),
            )
            if tampered_payload is not None:
                catalog.connection.execute(
                    "UPDATE events SET payload_json=? WHERE event_id='legacy-event'",
                    (tampered_payload,),
                )
            catalog.connection.execute(
                "UPDATE schema_metadata SET value='2' WHERE key='schema_version'"
            )
        return paths, task.task_id, legacy_fingerprint, expected_fingerprint

    def _insert_second_legacy_v2_event(
        self,
        paths: DataPaths,
        task_id: str,
        *,
        swap_sequences: bool,
    ) -> None:
        document = {
            "event_id": "legacy-event-2",
            "task_id": task_id,
            "event_type": "task.created",
            "event_version": 1,
            "occurred_at": "2026-09-04T00:00:01+00:00",
            "payload": {"mode": "imported"},
            "collection_method": "legacy-fixture",
            "redaction_status": "not_needed",
        }
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        legacy_fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        connection = sqlite3.connect(paths.catalog)
        connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "legacy-event-2",
                task_id,
                2,
                "task.created",
                1,
                "2026-09-04T00:00:01+00:00",
                '{"mode":"imported"}',
                "legacy-fixture",
                "not_needed",
                legacy_fingerprint,
            ),
        )
        if swap_sequences:
            connection.execute(
                "UPDATE events SET sequence=99 WHERE event_id='legacy-event'"
            )
            connection.execute(
                "UPDATE events SET sequence=1 WHERE event_id='legacy-event-2'"
            )
            connection.execute(
                "UPDATE events SET sequence=2 WHERE event_id='legacy-event'"
            )
        connection.commit()
        connection.close()

    @staticmethod
    def _legacy_catalog_snapshot(paths: DataPaths) -> tuple[str, list[tuple], list[tuple]]:
        connection = sqlite3.connect(paths.catalog)
        version = connection.execute(
            "SELECT value FROM schema_metadata WHERE key='schema_version'"
        ).fetchone()[0]
        events = connection.execute(
            "SELECT * FROM events ORDER BY event_id"
        ).fetchall()
        projections = connection.execute(
            "SELECT * FROM task_projections ORDER BY task_id"
        ).fetchall()
        connection.close()
        return version, events, projections

    def _create_full_v1_catalog(
        self, name: str, *, include_second_event: bool = False
    ) -> tuple[DataPaths, str]:
        root = Path(self.temporary_directory.name) / name
        root.mkdir()
        paths = DataPaths.resolve(root)
        content_hash = "8f6682fa8a90b77ca07b61bd7ba6637aea607f5d6cf8bfe73c17ebff965d4a1b"
        evidence_fingerprint = (
            "b6cc3272f93efec6f200e7a2b26544fb129d4c0e35da90db6e22c9edb368a14c"
        )
        expected_v2_fingerprint = (
            "94c1e8cf4caf62ec642ac9171ddbea2acfec59d363c691994c158c5b12a8fad8"
        )
        projection_json = (
            '{"event_counts":{},"evidence":{"active_ids":["legacy-evidence"],'
            '"purged_ids":[]},"guarantee":{"report_ids":[]},'
            '"task":{"mode":"managed"}}'
        )
        connection = sqlite3.connect(paths.catalog)
        connection.executescript(
            """
            CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT;
            INSERT INTO schema_metadata VALUES ('schema_version', '1');
            CREATE TABLE projects (
                project_id TEXT PRIMARY KEY, locator TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            ) STRICT;
            CREATE TABLE worktrees (
                worktree_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(project_id),
                locator TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(project_id, locator)
            ) STRICT;
            CREATE TABLE tasks (
                task_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(project_id),
                worktree_id TEXT NOT NULL REFERENCES worktrees(worktree_id),
                mode TEXT NOT NULL CHECK(mode IN ('managed', 'imported')),
                commit_hash TEXT NOT NULL, branch TEXT NOT NULL, cwd TEXT NOT NULL,
                environment_ref TEXT NOT NULL, created_at TEXT NOT NULL
            ) STRICT;
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(task_id),
                sequence INTEGER NOT NULL CHECK(sequence > 0),
                event_type TEXT NOT NULL,
                event_version INTEGER NOT NULL CHECK(event_version > 0),
                occurred_at TEXT NOT NULL, payload_json TEXT NOT NULL,
                collection_method TEXT NOT NULL, redaction_status TEXT NOT NULL,
                fingerprint TEXT NOT NULL, UNIQUE(task_id, sequence)
            ) STRICT;
            CREATE TABLE evidence (
                evidence_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(task_id),
                requirement_id TEXT NOT NULL, evidence_type TEXT NOT NULL,
                subject_ref TEXT NOT NULL, exact_scope TEXT NOT NULL,
                result TEXT NOT NULL, basis TEXT NOT NULL, fields_json TEXT NOT NULL,
                content_hash TEXT NOT NULL, object_relpath TEXT NOT NULL,
                content_size INTEGER NOT NULL, collection_method TEXT NOT NULL,
                redaction_status TEXT NOT NULL, fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL, purged_at TEXT, purge_reason TEXT
            ) STRICT;
            CREATE TABLE task_projections (
                task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
                projected_sequence INTEGER NOT NULL, state TEXT NOT NULL,
                projection_json TEXT NOT NULL, last_error TEXT,
                updated_at TEXT NOT NULL
            ) STRICT;
            CREATE TABLE retention_policy (
                singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                mode TEXT NOT NULL, days INTEGER
            ) STRICT;
            INSERT INTO retention_policy VALUES (1, 'keep_until_user_deletes', NULL);
            CREATE TABLE control_validations (
                record_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(task_id),
                record_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL
            ) STRICT;
            """
        )
        connection.execute(
            "INSERT INTO projects VALUES (?, ?, ?)",
            ("legacy-project", "file:///legacy", "2026-09-04T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO worktrees VALUES (?, ?, ?, ?)",
            (
                "legacy-worktree",
                "legacy-project",
                "file:///legacy/main",
                "2026-09-04T00:00:00+00:00",
            ),
        )
        connection.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "legacy-task",
                "legacy-project",
                "legacy-worktree",
                "managed",
                "abc123",
                "main",
                "/legacy",
                "legacy-runtime",
                "2026-09-04T00:00:00+00:00",
            ),
        )
        connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "legacy-event",
                "legacy-task",
                1,
                "task.created",
                1,
                "2026-09-04T00:00:00+00:00",
                '{"mode":"managed"}',
                "legacy-fixture",
                "not_needed",
                "6410e02785760e9ca1e58b76abdc35b80549efdb3b0599c3b0fb9334e092f3f7",
            ),
        )
        if include_second_event:
            connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "legacy-event-2",
                    "legacy-task",
                    2,
                    "task.created",
                    1,
                    "2026-09-04T00:00:01+00:00",
                    '{"mode":"imported"}',
                    "legacy-fixture",
                    "not_needed",
                    "e200d96285e4e0ea7c5b5bd1cad4ee51715b7d93a9e307be7b301893c239c411",
                ),
            )
        connection.execute(
            """
            INSERT INTO evidence VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "legacy-evidence",
                "legacy-task",
                "legacy-requirement",
                "test_execution",
                "test:legacy",
                "tests/test_legacy.py",
                "pass",
                "observed",
                '{"result":"pass"}',
                content_hash,
                f"{content_hash[:2]}/{content_hash[2:]}",
                23,
                "legacy-fixture",
                "not_needed",
                evidence_fingerprint,
                "2026-09-04T00:00:00+00:00",
                None,
                None,
            ),
        )
        connection.execute(
            "INSERT INTO task_projections VALUES (?, 0, 'ready', ?, NULL, ?)",
            ("legacy-task", projection_json, "2026-09-04T00:00:00+00:00"),
        )
        connection.commit()
        connection.close()
        object_path = paths.objects / f"{content_hash[:2]}/{content_hash[2:]}"
        object_path.parent.mkdir(parents=True)
        object_path.write_bytes(b"legacy evidence content")
        return paths, expected_v2_fingerprint

    @staticmethod
    def _v1_migration_snapshot(paths: DataPaths) -> dict[str, object]:
        connection = sqlite3.connect(paths.catalog)
        snapshot = {
            "sqlite_schema": connection.execute(
                """
                SELECT type, name, tbl_name, sql
                FROM sqlite_schema
                ORDER BY type, name
                """
            ).fetchall(),
            "version": connection.execute(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ).fetchone()[0],
            "event_columns": connection.execute(
                "PRAGMA table_info(events)"
            ).fetchall(),
            "events": connection.execute(
                "SELECT * FROM events ORDER BY event_id"
            ).fetchall(),
            "evidence_columns": connection.execute(
                "PRAGMA table_info(evidence)"
            ).fetchall(),
            "evidence": connection.execute(
                "SELECT * FROM evidence ORDER BY evidence_id"
            ).fetchall(),
            "projection_columns": connection.execute(
                "PRAGMA table_info(task_projections)"
            ).fetchall(),
            "projections": connection.execute(
                "SELECT * FROM task_projections ORDER BY task_id"
            ).fetchall(),
        }
        connection.close()
        return snapshot

    def test_same_locator_is_idempotent_and_other_locator_is_distinct(self) -> None:
        project = self.registry.register_project("file:///repo")

        self.assertEqual(project, self.registry.register_project("file:///repo"))
        self.assertNotEqual(
            project.project_id,
            self.registry.register_project("file:///other").project_id,
        )

    def test_worktree_is_stable_and_scoped_to_its_project(self) -> None:
        project = self.registry.register_project("file:///repo")
        worktree = self.registry.register_worktree(
            project.project_id, "file:///repo/worktrees/main"
        )

        self.assertEqual(
            worktree,
            self.registry.register_worktree(
                project.project_id, "file:///repo/worktrees/main"
            ),
        )
        self.assertEqual(project.project_id, worktree.project_id)

        with self.assertRaisesRegex(ValueError, "unknown project"):
            self.registry.register_worktree("missing-project", "file:///repo/other")

    def test_project_and_worktree_identities_cannot_be_deleted_and_recreated(self) -> None:
        project = self.registry.register_project("file:///stable")
        worktree = self.registry.register_worktree(
            project.project_id, "file:///stable/main"
        )

        with self.assertRaisesRegex(sqlite3.DatabaseError, "immutable"):
            self.catalog.connection.execute(
                "DELETE FROM worktrees WHERE worktree_id=?", (worktree.worktree_id,)
            )
        with self.assertRaisesRegex(sqlite3.DatabaseError, "immutable"):
            self.catalog.connection.execute(
                "DELETE FROM projects WHERE project_id=?", (project.project_id,)
            )

        self.assertEqual(
            project,
            self.registry.register_project("file:///stable"),
        )
        self.assertEqual(
            worktree,
            self.registry.register_worktree(
                project.project_id, "file:///stable/main"
            ),
        )

    def test_task_snapshot_captures_mode_and_git_context(self) -> None:
        project = self.registry.register_project("file:///repo")
        worktree = self.registry.register_worktree(project.project_id, "file:///repo/main")

        task = self.registry.create_task(
            worktree.worktree_id,
            mode="managed",
            commit="abc123",
            branch="feature/identity",
            cwd="/repo/main",
            environment_ref="local-macos",
        )

        self.assertEqual(project.project_id, task.project_id)
        self.assertEqual(worktree.worktree_id, task.worktree_id)
        self.assertEqual("managed", task.mode)
        self.assertEqual("abc123", task.commit)
        self.assertEqual("feature/identity", task.branch)
        self.assertEqual("/repo/main", task.cwd)
        self.assertEqual("local-macos", task.environment_ref)
        self.assertEqual(task, self.registry.get_task(task.task_id))

    def test_invalid_task_mode_and_unknown_worktree_are_rejected(self) -> None:
        project = self.registry.register_project("file:///repo")
        worktree = self.registry.register_worktree(project.project_id, "file:///repo/main")

        with self.assertRaisesRegex(ValueError, "mode"):
            self.registry.create_task(
                worktree.worktree_id,
                mode="other",
                commit="abc123",
                branch="main",
                cwd="/repo/main",
                environment_ref="local",
            )

        with self.assertRaisesRegex(ValueError, "unknown worktree"):
            self.registry.create_task(
                "missing-worktree",
                mode="imported",
                commit="abc123",
                branch="main",
                cwd="/repo/main",
                environment_ref="local",
            )

    def test_catalog_uses_required_sqlite_mode_and_private_permissions(self) -> None:
        directory_mode = stat.S_IMODE(self.root.stat().st_mode)
        database_mode = stat.S_IMODE(self.catalog.path.stat().st_mode)

        self.assertEqual(0o700, directory_mode)
        self.assertEqual(0o600, database_mode)
        self.assertEqual("delete", self.catalog.query_value("PRAGMA journal_mode"))
        self.assertEqual(2, self.catalog.query_value("PRAGMA synchronous"))
        self.assertEqual(1, self.catalog.query_value("PRAGMA foreign_keys"))

    def test_explicit_data_root_inside_git_worktree_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory) / "repo"
            repository.mkdir()
            (repository / ".git").mkdir()

            with self.assertRaisesRegex(ValueError, "Git worktree"):
                DataPaths.resolve(repository / "raw-evidence")

    def test_concurrent_same_locator_registration_is_idempotent(self) -> None:
        root = Path(self.temporary_directory.name) / "concurrent-data"

        def register() -> str:
            with Catalog.open(DataPaths.resolve(root)) as catalog:
                return IdentityRegistry(catalog).register_project(
                    "file:///same-repository"
                ).project_id

        with ThreadPoolExecutor(max_workers=2) as executor:
            project_ids = list(executor.map(lambda _index: register(), range(2)))

        self.assertEqual(1, len(set(project_ids)))

    def test_concurrent_same_worktree_registration_is_idempotent(self) -> None:
        root = Path(self.temporary_directory.name) / "concurrent-worktree-data"
        with Catalog.open(DataPaths.resolve(root)) as catalog:
            project_id = IdentityRegistry(catalog).register_project(
                "file:///same-repository"
            ).project_id

        def register() -> str:
            with Catalog.open(DataPaths.resolve(root)) as catalog:
                return IdentityRegistry(catalog).register_worktree(
                    project_id, "file:///same-repository/main"
                ).worktree_id

        with ThreadPoolExecutor(max_workers=2) as executor:
            worktree_ids = list(executor.map(lambda _index: register(), range(2)))

        self.assertEqual(1, len(set(worktree_ids)))

    def test_task_snapshot_is_immutable(self) -> None:
        project = self.registry.register_project("file:///immutable")
        worktree = self.registry.register_worktree(
            project.project_id, "file:///immutable/main"
        )
        task = self.registry.create_task(
            worktree.worktree_id,
            mode="managed",
            commit="abc123",
            branch="main",
            cwd="/repo/main",
            environment_ref="local",
        )

        with self.assertRaisesRegex(sqlite3.DatabaseError, "immutable"):
            self.catalog.connection.execute(
                "UPDATE tasks SET commit_hash='tampered' WHERE task_id=?",
                (task.task_id,),
            )

    def test_database_rejects_cross_project_task_scope(self) -> None:
        first_project = self.registry.register_project("file:///first")
        second_project = self.registry.register_project("file:///second")
        second_worktree = self.registry.register_worktree(
            second_project.project_id, "file:///second/main"
        )

        with self.assertRaisesRegex(sqlite3.DatabaseError, "project/worktree"):
            self.catalog.connection.execute(
                """
                INSERT INTO tasks(
                    task_id, project_id, worktree_id, mode, commit_hash, branch,
                    cwd, environment_ref, created_at
                ) VALUES (?, ?, ?, 'managed', 'abc', 'main', '/repo', 'local', ?)
                """,
                (
                    "cross-project-task",
                    first_project.project_id,
                    second_worktree.worktree_id,
                    "2026-09-04T00:00:00+00:00",
                ),
            )

    def test_v1_projection_catalog_is_discarded_until_canonical_replay(self) -> None:
        root = Path(self.temporary_directory.name) / "legacy-v1"
        root.mkdir()
        database = root / "catalog.sqlite3"
        projection_json = (
            '{"event_counts":{},"evidence":{"active_ids":[],"purged_ids":[]},'
            '"guarantee":{"report_ids":[]},"task":{}}'
        )
        connection = sqlite3.connect(database)
        connection.executescript(
            """
            CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT;
            INSERT INTO schema_metadata(key, value) VALUES ('schema_version', '1');
            CREATE TABLE task_projections (
                task_id TEXT PRIMARY KEY,
                projected_sequence INTEGER NOT NULL,
                state TEXT NOT NULL,
                projection_json TEXT NOT NULL,
                last_error TEXT,
                updated_at TEXT NOT NULL
            ) STRICT;
            """
        )
        connection.execute(
            """
            INSERT INTO task_projections(
                task_id, projected_sequence, state, projection_json, last_error, updated_at
            ) VALUES (?, 0, 'ready', ?, NULL, '2026-09-04T00:00:00+00:00')
            """,
            ("legacy-task", projection_json),
        )
        connection.commit()
        connection.close()

        with Catalog.open(DataPaths.resolve(root)) as catalog:
            row = catalog.connection.execute(
                "SELECT * FROM task_projections WHERE task_id='legacy-task'"
            ).fetchone()
            self.assertEqual("3", catalog.query_value(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ))
            self.assertIsNone(row)

    def test_v2_catalog_migrates_verified_legacy_event_fingerprint(self) -> None:
        paths, task_id, _legacy_fingerprint, expected_fingerprint = (
            self._create_v2_event_catalog("legacy-v2-event")
        )

        with Catalog.open(paths) as catalog:
            row = catalog.connection.execute(
                "SELECT fingerprint FROM events WHERE event_id='legacy-event'"
            ).fetchone()

            self.assertEqual(
                "3",
                catalog.query_value(
                    "SELECT value FROM schema_metadata WHERE key='schema_version'"
                ),
            )
            self.assertEqual(expected_fingerprint, row["fingerprint"])
            self.assertEqual(
                0,
                catalog.query_value("SELECT COUNT(*) FROM task_projections"),
            )
            records = EventLog(catalog).list_for_task(task_id)
            self.assertEqual([1], [record.sequence for record in records])

    def test_legacy_single_event_lifecycle_mismatch_is_refused_atomically(self) -> None:
        cases = (
            ("non-created", "tool.completed", {}),
            ("mode-mismatch", "task.created", {"mode": "imported"}),
        )
        for schema_version in (1, 2):
            for case, event_type, payload in cases:
                with self.subTest(schema_version=schema_version, case=case):
                    name = f"legacy-v{schema_version}-{case}"
                    if schema_version == 1:
                        paths, _expected = self._create_full_v1_catalog(name)
                        task_id = "legacy-task"
                    else:
                        paths, task_id, _legacy, _expected = (
                            self._create_v2_event_catalog(name)
                        )
                    document = {
                        "event_id": "legacy-event",
                        "task_id": task_id,
                        "event_type": event_type,
                        "event_version": 1,
                        "occurred_at": "2026-09-04T00:00:00+00:00",
                        "payload": payload,
                        "collection_method": "legacy-fixture",
                        "redaction_status": "not_needed",
                    }
                    fingerprint = hashlib.sha256(
                        json.dumps(
                            document,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        ).encode("utf-8")
                    ).hexdigest()
                    connection = sqlite3.connect(paths.catalog)
                    connection.execute("DROP TRIGGER IF EXISTS events_no_update")
                    connection.execute(
                        """
                        UPDATE events
                        SET event_type=?, payload_json=?, fingerprint=?
                        WHERE event_id='legacy-event'
                        """,
                        (
                            event_type,
                            json.dumps(
                                payload,
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            fingerprint,
                        ),
                    )
                    connection.commit()
                    connection.close()
                    before_connection = sqlite3.connect(paths.catalog)
                    before = tuple(before_connection.iterdump())
                    before_connection.close()

                    with self.assertRaisesRegex(
                        RuntimeError, "legacy Event lifecycle"
                    ):
                        Catalog.open(paths)

                    after_connection = sqlite3.connect(paths.catalog)
                    after = tuple(after_connection.iterdump())
                    after_connection.close()
                    self.assertEqual(before, after)

    def test_schema_v3_missing_events_is_rejected_without_repair(self) -> None:
        paths = DataPaths.resolve(
            Path(self.temporary_directory.name) / "schema-v3-missing-events"
        )
        with Catalog.open(paths) as catalog:
            registry = IdentityRegistry(catalog)
            project = registry.register_project("file:///schema-v3-missing-events")
            worktree = registry.register_worktree(
                project.project_id, "file:///schema-v3-missing-events/main"
            )
            task = registry.create_task(
                worktree.worktree_id,
                mode="managed",
                commit="abc123",
                branch="main",
                cwd="/schema-v3-missing-events",
                environment_ref="local-test",
            )
            EventLog(catalog).append(
                EventDraft(
                    event_id="schema-contract-event",
                    task_id=task.task_id,
                    event_type="task.created",
                    event_version=1,
                    occurred_at="2026-09-04T00:00:00+00:00",
                    payload={"mode": "managed"},
                    collection_method="schema-contract-test",
                    redaction_status="not_needed",
                ),
                lambda payload: payload,
            )

        connection = sqlite3.connect(paths.catalog)
        connection.execute("DROP TABLE events")
        connection.commit()
        before = tuple(connection.iterdump())
        connection.close()

        try:
            reopened = Catalog.open(paths)
        except RuntimeError as error:
            self.assertRegex(str(error), "schema v3 contract")
        else:
            with reopened:
                laundered = ProjectionEngine(
                    reopened, EventLog(reopened)
                ).project(task.task_id)
                freshness = ProjectionEngine(
                    reopened, EventLog(reopened)
                ).freshness(task.task_id)
            self.fail(
                "damaged schema v3 reopened and laundered deleted Events as "
                f"{laundered.state} sequence {laundered.projected_sequence}, "
                f"fresh={freshness.is_fresh}"
            )

        after_connection = sqlite3.connect(paths.catalog)
        after = tuple(after_connection.iterdump())
        after_connection.close()
        self.assertEqual(before, after)

    def test_schema_v3_changed_core_contract_is_rejected_before_ddl(self) -> None:
        mutations = {
            "missing-trigger": "DROP TRIGGER events_no_update",
            "missing-index": "DROP INDEX evidence_task_requirement",
            "extra-column": "ALTER TABLE events ADD COLUMN injected TEXT",
            "changed-column-type": None,
            "changed-trigger-definition": None,
        }
        for case, mutation in mutations.items():
            with self.subTest(case=case):
                paths = DataPaths.resolve(
                    Path(self.temporary_directory.name) / f"schema-v3-{case}"
                )
                with Catalog.open(paths):
                    pass
                connection = sqlite3.connect(paths.catalog)
                if case == "changed-column-type":
                    connection.execute("PRAGMA writable_schema=ON")
                    connection.execute(
                        """
                        UPDATE sqlite_schema
                        SET sql=replace(sql, 'sequence INTEGER', 'sequence TEXT')
                        WHERE type='table' AND name='events'
                        """
                    )
                    schema_version = connection.execute(
                        "PRAGMA schema_version"
                    ).fetchone()[0]
                    connection.execute(f"PRAGMA schema_version={schema_version + 1}")
                    connection.execute("PRAGMA writable_schema=OFF")
                elif case == "changed-trigger-definition":
                    connection.execute("PRAGMA writable_schema=ON")
                    connection.execute(
                        """
                        UPDATE sqlite_schema
                        SET sql=replace(
                            sql,
                            'SELECT RAISE(ABORT, ''events are append-only'');',
                            'SELECT 1;'
                        )
                        WHERE type='trigger' AND name='events_no_update'
                        """
                    )
                    schema_version = connection.execute(
                        "PRAGMA schema_version"
                    ).fetchone()[0]
                    connection.execute(f"PRAGMA schema_version={schema_version + 1}")
                    connection.execute("PRAGMA writable_schema=OFF")
                else:
                    connection.execute(mutation)
                connection.commit()
                before = tuple(connection.iterdump())
                connection.close()

                with self.assertRaisesRegex(RuntimeError, "schema v3 contract"):
                    Catalog.open(paths)

                after_connection = sqlite3.connect(paths.catalog)
                after = tuple(after_connection.iterdump())
                after_connection.close()
                self.assertEqual(before, after)

    def test_v2_catalog_without_events_migrates_to_sequence_bound_schema(self) -> None:
        paths = DataPaths.resolve(
            Path(self.temporary_directory.name) / "empty-legacy-v2-event"
        )
        with Catalog.open(paths) as catalog:
            registry = IdentityRegistry(catalog)
            project = registry.register_project("file:///empty-legacy-v2-event")
            worktree = registry.register_worktree(
                project.project_id, "file:///empty-legacy-v2-event/main"
            )
            task = registry.create_task(
                worktree.worktree_id,
                mode="managed",
                commit="abc123",
                branch="main",
                cwd="/empty-legacy-v2-event",
                environment_ref="legacy-runtime",
            )
            ProjectionEngine(catalog, EventLog(catalog)).project(task.task_id)
            catalog.connection.execute(
                "UPDATE schema_metadata SET value='2' WHERE key='schema_version'"
            )

        with Catalog.open(paths) as catalog:
            self.assertEqual(
                "3",
                catalog.query_value(
                    "SELECT value FROM schema_metadata WHERE key='schema_version'"
                ),
            )
            self.assertEqual(0, catalog.query_value("SELECT COUNT(*) FROM events"))
            self.assertEqual(
                0, catalog.query_value("SELECT COUNT(*) FROM task_projections")
            )

    def test_v2_catalog_refuses_to_resign_swapped_multiple_legacy_events(self) -> None:
        paths, task_id, _legacy_fingerprint, _expected_fingerprint = (
            self._create_v2_event_catalog("swapped-multiple-legacy-v2-events")
        )
        self._insert_second_legacy_v2_event(
            paths, task_id, swap_sequences=True
        )
        before = self._legacy_catalog_snapshot(paths)

        with self.assertRaisesRegex(
            RuntimeError, "legacy Event order is unverifiable"
        ):
            Catalog.open(paths)

        after = self._legacy_catalog_snapshot(paths)
        self.assertEqual("2", before[0])
        self.assertEqual(before, after)

    def test_v2_catalog_refuses_to_resign_ordered_multiple_legacy_events(self) -> None:
        paths, task_id, _legacy_fingerprint, _expected_fingerprint = (
            self._create_v2_event_catalog("ordered-multiple-legacy-v2-events")
        )
        self._insert_second_legacy_v2_event(
            paths, task_id, swap_sequences=False
        )
        before = self._legacy_catalog_snapshot(paths)

        with self.assertRaisesRegex(
            RuntimeError, "legacy Event order is unverifiable"
        ):
            Catalog.open(paths)

        after = self._legacy_catalog_snapshot(paths)
        self.assertEqual("2", before[0])
        self.assertEqual(before, after)

    def test_v2_catalog_refuses_to_resign_unverified_legacy_event(self) -> None:
        paths, _task_id, legacy_fingerprint, _expected_fingerprint = (
            self._create_v2_event_catalog(
                "tampered-v2-event", tampered_payload='{"mode":"imported"}'
            )
        )

        with self.assertRaisesRegex(RuntimeError, "legacy Event fingerprint"):
            Catalog.open(paths)

        connection = sqlite3.connect(paths.catalog)
        version = connection.execute(
            "SELECT value FROM schema_metadata WHERE key='schema_version'"
        ).fetchone()[0]
        fingerprint = connection.execute(
            "SELECT fingerprint FROM events WHERE event_id='legacy-event'"
        ).fetchone()[0]
        projection_count = connection.execute(
            "SELECT COUNT(*) FROM task_projections"
        ).fetchone()[0]
        connection.close()
        self.assertEqual("2", version)
        self.assertEqual(legacy_fingerprint, fingerprint)
        self.assertEqual(1, projection_count)

    def test_v1_multiple_event_refusal_rolls_back_the_entire_migration(self) -> None:
        paths, _expected_v2_fingerprint = self._create_full_v1_catalog(
            "atomic-multiple-event-v1", include_second_event=True
        )
        before = self._v1_migration_snapshot(paths)

        with self.assertRaisesRegex(
            RuntimeError, "legacy Event order is unverifiable"
        ):
            Catalog.open(paths)

        after = self._v1_migration_snapshot(paths)
        self.assertEqual("1", before["version"])
        self.assertEqual(2, len(before["events"]))
        self.assertEqual(1, len(before["evidence"]))
        self.assertEqual(1, len(before["projections"]))
        self.assertNotIn(
            "inference_from_json", [column[1] for column in before["evidence_columns"]]
        )
        self.assertNotIn(
            "projection_hash", [column[1] for column in before["projection_columns"]]
        )
        self.assertEqual(before, after)

    def test_v1_bad_evidence_fingerprint_refusal_preserves_entire_catalog(self) -> None:
        paths, _expected_v2_fingerprint = self._create_full_v1_catalog(
            "atomic-bad-evidence-v1"
        )
        connection = sqlite3.connect(paths.catalog)
        connection.execute(
            "UPDATE evidence SET fingerprint=? WHERE evidence_id='legacy-evidence'",
            ("0" * 64,),
        )
        connection.commit()
        connection.close()
        before = self._v1_migration_snapshot(paths)

        with self.assertRaisesRegex(RuntimeError, "legacy Evidence fingerprint"):
            Catalog.open(paths)

        after = self._v1_migration_snapshot(paths)
        self.assertEqual("1", before["version"])
        self.assertEqual(1, len(before["events"]))
        self.assertEqual(before, after)

    def test_v1_bad_event_fingerprint_refusal_preserves_entire_catalog(self) -> None:
        paths, _expected_v2_fingerprint = self._create_full_v1_catalog(
            "atomic-bad-event-v1"
        )
        connection = sqlite3.connect(paths.catalog)
        connection.execute(
            "UPDATE events SET fingerprint=? WHERE event_id='legacy-event'",
            ("0" * 64,),
        )
        connection.commit()
        connection.close()
        before = self._v1_migration_snapshot(paths)

        with self.assertRaisesRegex(RuntimeError, "legacy Event fingerprint"):
            Catalog.open(paths)

        after = self._v1_migration_snapshot(paths)
        self.assertEqual(before, after)

    def test_v1_malformed_evidence_json_refusal_preserves_entire_catalog(self) -> None:
        for case in ("fields", "lineage"):
            with self.subTest(case=case):
                paths, _expected_v2_fingerprint = self._create_full_v1_catalog(
                    f"atomic-malformed-{case}-v1"
                )
                connection = sqlite3.connect(paths.catalog)
                if case == "fields":
                    connection.execute(
                        """
                        UPDATE evidence SET fields_json='not-json'
                        WHERE evidence_id='legacy-evidence'
                        """
                    )
                else:
                    connection.execute(
                        """
                        ALTER TABLE evidence ADD COLUMN inference_from_json
                        TEXT NOT NULL DEFAULT '[]'
                        """
                    )
                    connection.execute(
                        """
                        ALTER TABLE evidence ADD COLUMN conflict_refs_json
                        TEXT NOT NULL DEFAULT '[]'
                        """
                    )
                    connection.execute(
                        """
                        UPDATE evidence SET inference_from_json='not-json'
                        WHERE evidence_id='legacy-evidence'
                        """
                    )
                connection.commit()
                connection.close()
                before = self._v1_migration_snapshot(paths)

                with self.assertRaisesRegex(
                    RuntimeError, "legacy Evidence metadata is invalid"
                ):
                    Catalog.open(paths)

                after = self._v1_migration_snapshot(paths)
                self.assertEqual(before, after)

    def test_unknown_schema_version_is_rejected_before_bootstrap(self) -> None:
        root = Path(self.temporary_directory.name) / "unknown-schema-version"
        root.mkdir()
        paths = DataPaths.resolve(root)
        connection = sqlite3.connect(paths.catalog)
        connection.executescript(
            """
            CREATE TABLE schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) STRICT;
            INSERT INTO schema_metadata VALUES ('schema_version', '999');
            CREATE TABLE future_only (
                future_id TEXT PRIMARY KEY,
                future_value TEXT NOT NULL
            ) STRICT;
            INSERT INTO future_only VALUES ('future-row', 'preserve-me');
            """
        )
        before_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
        ).fetchall()
        before_rows = {
            "schema_metadata": connection.execute(
                "SELECT * FROM schema_metadata ORDER BY key"
            ).fetchall(),
            "future_only": connection.execute(
                "SELECT * FROM future_only ORDER BY future_id"
            ).fetchall(),
        }
        connection.close()
        self.assertEqual(4, len(before_schema))

        with self.assertRaisesRegex(RuntimeError, "unsupported catalog schema version"):
            Catalog.open(paths)

        connection = sqlite3.connect(paths.catalog)
        after_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
        ).fetchall()
        after_rows = {
            "schema_metadata": connection.execute(
                "SELECT * FROM schema_metadata ORDER BY key"
            ).fetchall(),
            "future_only": connection.execute(
                "SELECT * FROM future_only ORDER BY future_id"
            ).fetchall(),
        }
        connection.close()
        self.assertEqual(before_schema, after_schema)
        self.assertEqual(before_rows, after_rows)

    def test_existing_database_without_version_row_is_not_fresh_bootstrapped(self) -> None:
        root = Path(self.temporary_directory.name) / "missing-schema-version"
        root.mkdir()
        paths = DataPaths.resolve(root)
        connection = sqlite3.connect(paths.catalog)
        connection.executescript(
            """
            CREATE TABLE schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) STRICT;
            CREATE TABLE existing_data (
                item_id TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) STRICT;
            INSERT INTO existing_data VALUES ('existing-row', 'preserve-me');
            """
        )
        before_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
        ).fetchall()
        before_rows = connection.execute(
            "SELECT * FROM existing_data ORDER BY item_id"
        ).fetchall()
        connection.close()

        with self.assertRaisesRegex(RuntimeError, "missing catalog schema version"):
            Catalog.open(paths)

        connection = sqlite3.connect(paths.catalog)
        after_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
        ).fetchall()
        after_rows = connection.execute(
            "SELECT * FROM existing_data ORDER BY item_id"
        ).fetchall()
        version_count = connection.execute(
            "SELECT COUNT(*) FROM schema_metadata WHERE key='schema_version'"
        ).fetchone()[0]
        connection.close()
        self.assertEqual(before_schema, after_schema)
        self.assertEqual(before_rows, after_rows)
        self.assertEqual(0, version_count)

    def test_nonempty_database_without_schema_metadata_is_not_fresh_bootstrapped(self) -> None:
        root = Path(self.temporary_directory.name) / "missing-schema-metadata"
        root.mkdir()
        paths = DataPaths.resolve(root)
        connection = sqlite3.connect(paths.catalog)
        connection.executescript(
            """
            CREATE TABLE existing_data (
                item_id TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) STRICT;
            INSERT INTO existing_data VALUES ('existing-row', 'preserve-me');
            """
        )
        before_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
        ).fetchall()
        before_rows = connection.execute(
            "SELECT * FROM existing_data ORDER BY item_id"
        ).fetchall()
        connection.close()

        with self.assertRaisesRegex(RuntimeError, "missing catalog schema metadata"):
            Catalog.open(paths)

        connection = sqlite3.connect(paths.catalog)
        after_schema = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
        ).fetchall()
        after_rows = connection.execute(
            "SELECT * FROM existing_data ORDER BY item_id"
        ).fetchall()
        connection.close()
        self.assertEqual(before_schema, after_schema)
        self.assertEqual(before_rows, after_rows)

    def test_full_v1_catalog_migrates_legacy_evidence_and_discards_projection(self) -> None:
        paths, expected_v2_fingerprint = self._create_full_v1_catalog(
            "full-legacy-v1"
        )

        with Catalog.open(paths) as catalog:
            columns = {
                row["name"]
                for row in catalog.connection.execute("PRAGMA table_info(evidence)")
            }
            row = catalog.connection.execute(
                "SELECT * FROM evidence WHERE evidence_id='legacy-evidence'"
            ).fetchone()
            record = EvidenceStore(catalog, EventLog(catalog)).resolve(
                "legacy-evidence"
            )
            event = EventLog(catalog).list_for_task("legacy-task")[0]
            freshness = ProjectionEngine(catalog, EventLog(catalog)).freshness(
                "legacy-task"
            )

            self.assertTrue({"inference_from_json", "conflict_refs_json"} <= columns)
            self.assertEqual(
                ("[]", "[]"),
                (row["inference_from_json"], row["conflict_refs_json"]),
            )
            self.assertEqual(expected_v2_fingerprint, record.fingerprint)
            self.assertEqual(
                "50f77ce390bf6914c2129f13faf9a310a10674bfff9f9db2fd01b813903e5706",
                event.fingerprint,
            )
            self.assertEqual(1, event.sequence)
            self.assertEqual(
                "3",
                catalog.query_value(
                    "SELECT value FROM schema_metadata WHERE key='schema_version'"
                ),
            )
            self.assertEqual("missing", freshness.projection_state)
            self.assertFalse(freshness.is_fresh)

    def test_concurrent_v1_catalog_open_migrates_once(self) -> None:
        root = Path(self.temporary_directory.name) / "concurrent-legacy-v1"
        root.mkdir()
        database = root / "catalog.sqlite3"
        connection = sqlite3.connect(database)
        connection.executescript(
            """
            CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT;
            INSERT INTO schema_metadata(key, value) VALUES ('schema_version', '1');
            CREATE TABLE task_projections (
                task_id TEXT PRIMARY KEY,
                projected_sequence INTEGER NOT NULL,
                state TEXT NOT NULL,
                projection_json TEXT NOT NULL,
                last_error TEXT,
                updated_at TEXT NOT NULL
            ) STRICT;
            """
        )
        connection.commit()
        connection.close()

        barrier = threading.Barrier(2)
        original_transaction = Catalog.transaction

        @contextmanager
        def synchronized_transaction(catalog):
            barrier.wait(timeout=5)
            with original_transaction(catalog) as connection:
                yield connection

        def open_catalog(_index: int) -> str:
            try:
                with Catalog.open(DataPaths.resolve(root)):
                    return "ok"
            except sqlite3.DatabaseError as error:
                return str(error)

        with mock.patch.object(Catalog, "transaction", synchronized_transaction):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(open_catalog, range(2)))

        self.assertEqual(["ok", "ok"], sorted(results))


if __name__ == "__main__":
    unittest.main()

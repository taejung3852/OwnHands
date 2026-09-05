from __future__ import annotations

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
from devharness.events import EventLog
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
            self.assertEqual("2", catalog.query_value(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ))
            self.assertIsNone(row)

    def test_full_v1_catalog_migrates_legacy_evidence_and_discards_projection(self) -> None:
        root = Path(self.temporary_directory.name) / "full-legacy-v1"
        root.mkdir()
        paths = DataPaths.resolve(root)
        content_hash = "8f6682fa8a90b77ca07b61bd7ba6637aea607f5d6cf8bfe73c17ebff965d4a1b"
        legacy_fingerprint = "b6cc3272f93efec6f200e7a2b26544fb129d4c0e35da90db6e22c9edb368a14c"
        expected_v2_fingerprint = "94c1e8cf4caf62ec642ac9171ddbea2acfec59d363c691994c158c5b12a8fad8"
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
                "legacy-worktree", "legacy-project", "file:///legacy/main",
                "2026-09-04T00:00:00+00:00",
            ),
        )
        connection.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "legacy-task", "legacy-project", "legacy-worktree", "managed",
                "abc123", "main", "/legacy", "legacy-runtime",
                "2026-09-04T00:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO evidence VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "legacy-evidence", "legacy-task", "legacy-requirement",
                "test_execution", "test:legacy", "tests/test_legacy.py", "pass",
                "observed", '{"result":"pass"}', content_hash,
                f"{content_hash[:2]}/{content_hash[2:]}", 23, "legacy-fixture",
                "not_needed", legacy_fingerprint, "2026-09-04T00:00:00+00:00",
                None, None,
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
            freshness = ProjectionEngine(catalog, EventLog(catalog)).freshness(
                "legacy-task"
            )

            self.assertTrue({"inference_from_json", "conflict_refs_json"} <= columns)
            self.assertEqual(
                ("[]", "[]"),
                (row["inference_from_json"], row["conflict_refs_json"]),
            )
            self.assertEqual(expected_v2_fingerprint, record.fingerprint)
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

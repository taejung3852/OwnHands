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

from devharness.catalog import Catalog, projection_fingerprint
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths


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

    def test_v1_projection_catalog_migrates_with_integrity_hash(self) -> None:
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
                "SELECT projection_hash FROM task_projections WHERE task_id='legacy-task'"
            ).fetchone()
            self.assertEqual("2", catalog.query_value(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ))
            self.assertEqual(
                projection_fingerprint(
                    "legacy-task", 0, "ready", projection_json
                ),
                row["projection_hash"],
            )

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

from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from devharness.catalog import Catalog
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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .catalog import Catalog


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class ProjectIdentity:
    project_id: str
    locator: str
    created_at: str


@dataclass(frozen=True)
class WorktreeIdentity:
    worktree_id: str
    project_id: str
    locator: str
    created_at: str


@dataclass(frozen=True)
class TaskIdentity:
    task_id: str
    project_id: str
    worktree_id: str
    mode: str
    commit: str
    branch: str
    cwd: str
    environment_ref: str
    created_at: str


class IdentityRegistry:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def register_project(self, locator: str) -> ProjectIdentity:
        locator = _required(locator, "locator")
        with self.catalog.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE locator=?", (locator,)
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO projects(project_id, locator, created_at) VALUES (?, ?, ?)",
                    (str(uuid4()), locator, _now()),
                )
                row = connection.execute(
                    "SELECT * FROM projects WHERE locator=?", (locator,)
                ).fetchone()
        return ProjectIdentity(**dict(row))

    def register_worktree(self, project_id: str, locator: str) -> WorktreeIdentity:
        project_id = _required(project_id, "project_id")
        locator = _required(locator, "locator")
        with self.catalog.transaction() as connection:
            project_exists = connection.execute(
                "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
            ).fetchone()
            if project_exists is None:
                raise ValueError(f"unknown project: {project_id}")
            row = connection.execute(
                "SELECT * FROM worktrees WHERE project_id=? AND locator=?",
                (project_id, locator),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO worktrees(worktree_id, project_id, locator, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (str(uuid4()), project_id, locator, _now()),
                )
                row = connection.execute(
                    "SELECT * FROM worktrees WHERE project_id=? AND locator=?",
                    (project_id, locator),
                ).fetchone()
        return WorktreeIdentity(**dict(row))

    def create_task(
        self,
        worktree_id: str,
        mode: str,
        commit: str,
        branch: str,
        cwd: str,
        environment_ref: str,
    ) -> TaskIdentity:
        worktree_id = _required(worktree_id, "worktree_id")
        if mode not in {"managed", "imported"}:
            raise ValueError("mode must be managed or imported")
        commit = _required(commit, "commit")
        branch = _required(branch, "branch")
        cwd = _required(cwd, "cwd")
        environment_ref = _required(environment_ref, "environment_ref")

        worktree = self.catalog.connection.execute(
            "SELECT project_id FROM worktrees WHERE worktree_id=?", (worktree_id,)
        ).fetchone()
        if worktree is None:
            raise ValueError(f"unknown worktree: {worktree_id}")

        task_id = str(uuid4())
        created_at = _now()
        with self.catalog.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, project_id, worktree_id, mode, commit_hash, branch,
                    cwd, environment_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    worktree["project_id"],
                    worktree_id,
                    mode,
                    commit,
                    branch,
                    cwd,
                    environment_ref,
                    created_at,
                ),
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> TaskIdentity:
        row = self.catalog.connection.execute(
            "SELECT * FROM tasks WHERE task_id=?", (task_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown task: {task_id}")
        values = dict(row)
        values["commit"] = values.pop("commit_hash")
        return TaskIdentity(**values)

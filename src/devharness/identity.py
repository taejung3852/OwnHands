from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .catalog import Catalog
from .events import EventDraft, EventLog


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

    def create_task_lifecycle(
        self,
        project_locator: str,
        worktree_locator: str,
        mode: str,
        commit: str,
        branch: str,
        cwd: str,
        environment_ref: str,
        *,
        task_id: str | None = None,
    ) -> TaskIdentity:
        project_locator = _required(project_locator, "project_locator")
        worktree_locator = _required(worktree_locator, "worktree_locator")
        if mode not in {"managed", "imported"}:
            raise ValueError("mode must be managed or imported")
        commit = _required(commit, "commit")
        branch = _required(branch, "branch")
        cwd = _required(cwd, "cwd")
        environment_ref = _required(environment_ref, "environment_ref")

        actual_task_id = str(uuid4()) if task_id is None else _required(task_id, "task_id")
        created_at = _now()

        with self.catalog.transaction() as connection:
            # 1. Ensure project exists
            project_row = connection.execute(
                "SELECT project_id FROM projects WHERE locator=?", (project_locator,)
            ).fetchone()
            if project_row is None:
                p_id = str(uuid4())
                connection.execute(
                    "INSERT INTO projects(project_id, locator, created_at) VALUES (?, ?, ?)",
                    (p_id, project_locator, created_at),
                )
            else:
                p_id = project_row["project_id"]

            # 2. Ensure worktree exists
            worktree_row = connection.execute(
                "SELECT worktree_id FROM worktrees WHERE project_id=? AND locator=?",
                (p_id, worktree_locator),
            ).fetchone()
            if worktree_row is None:
                w_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO worktrees(worktree_id, project_id, locator, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (w_id, p_id, worktree_locator, created_at),
                )
            else:
                w_id = worktree_row["worktree_id"]

            # 3. Insert task
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, project_id, worktree_id, mode, commit_hash, branch,
                    cwd, environment_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    actual_task_id,
                    p_id,
                    w_id,
                    mode,
                    commit,
                    branch,
                    cwd,
                    environment_ref,
                    created_at,
                ),
            )

            # 4. Canonical task.created event at sequence 1
            event_log = EventLog(self.catalog)
            event_draft = EventDraft(
                event_id=f"task-created:{actual_task_id}",
                task_id=actual_task_id,
                event_type="task.created",
                event_version=1,
                occurred_at=created_at,
                payload={"mode": mode, "task_id": actual_task_id},
                collection_method="identity:lifecycle",
                redaction_status="not_needed",
            )
            event_log.append_in_transaction(event_draft, lambda p: p, connection)

        return self.get_task(actual_task_id)

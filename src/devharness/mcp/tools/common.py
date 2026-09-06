from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devharness.catalog import Catalog
from devharness.events import EventDraft, EventLog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths


def ensure_task_exists(catalog: Catalog, task_id: str) -> None:
    task_row = catalog.query_value("SELECT 1 FROM tasks WHERE task_id=?", (task_id,))
    if task_row is not None:
        return
    registry = IdentityRegistry(catalog)
    project = registry.register_project("mcp:auto-project")
    worktree = registry.register_worktree(project.project_id, "mcp:auto-worktree")
    created_at = datetime.now(timezone.utc).isoformat()
    with catalog.transaction() as connection:
        connection.execute(
            """
            INSERT INTO tasks(
                task_id, project_id, worktree_id, mode, commit_hash, branch,
                cwd, environment_ref, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                project.project_id,
                worktree.worktree_id,
                "managed",
                "HEAD",
                "main",
                "/",
                "mcp-env",
                created_at,
            ),
        )
    events = EventLog(catalog)
    events.append(
        EventDraft(
            event_id=f"task-created:{task_id}",
            task_id=task_id,
            event_type="task.created",
            event_version=1,
            occurred_at=created_at,
            payload={"mode": "managed", "task_id": task_id},
            collection_method="mcp:auto-init",
            redaction_status="not_needed",
        ),
        lambda p: p,
    )


def record_tool_evidence(
    data_paths: DataPaths | None,
    task_id: str,
    requirement_id: str,
    evidence_type: str,
    subject_ref: str,
    scope: str,
    result_decision: str | None,
    payload: dict[str, Any],
) -> str | None:
    paths = data_paths or DataPaths.resolve()
    with Catalog.open(paths) as catalog:
        ensure_task_exists(catalog, task_id)
        payload_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        content_hash = hashlib.sha256(payload_bytes).hexdigest()
        draft = EvidenceDraft(
            evidence_id=f"sha256:{content_hash}",
            task_id=task_id,
            requirement_id=requirement_id,
            evidence_type=evidence_type,
            subject_ref=subject_ref,
            exact_scope=scope,
            result="pass" if result_decision == "pass" else "fail",
            basis="observed",
            fields={"decision": result_decision},
            content=payload_bytes,
            collection_method=f"mcp:{subject_ref}",
            redaction_status="not_needed",
        )
        store = EvidenceStore(catalog, EventLog(catalog))
        record = store.put(draft, lambda b: b)
        return record.evidence_id

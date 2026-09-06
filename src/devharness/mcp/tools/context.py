from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devharness.catalog import Catalog
from devharness.context_architecture import ContextArchitectureError, lint_context
from devharness.events import EventDraft, EventLog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths

CONTEXT_LINT_TOOL = {
    "name": "context.lint",
    "description": "Deterministic static lint of instruction sources against instruction hygiene rules.",
    "inputSchema": {
        "type": "object",
        "required": ["root", "sources"],
        "properties": {
            "root": {"type": "string", "description": "Absolute path to project root"},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["source_id", "path", "source_type"],
                    "properties": {
                        "source_id": {"type": "string"},
                        "path": {"type": "string"},
                        "source_type": {
                            "enum": [
                                "agents_instruction",
                                "instruction_overlay",
                                "project_context",
                                "reference",
                                "skill",
                                "task_instruction",
                            ]
                        },
                    },
                },
            },
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}


def _ensure_task_exists(catalog: Catalog, task_id: str) -> None:
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


def handle_context_lint(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    if not isinstance(root_str, str) or not root_str.strip():
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": "InvalidArgument", "message": "root must be a non-empty string"},
        }

    sources = arguments.get("sources")
    if not isinstance(sources, list):
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": "InvalidArgument", "message": "sources must be a list"},
        }

    root_path = Path(root_str).resolve()
    try:
        raw_result = lint_context(root_path, sources)
    except (ContextArchitectureError, OSError) as error:
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": type(error).__name__, "message": str(error)},
        }

    findings = raw_result.get("findings", [])
    if not findings:
        decision = "pass"
    elif any(f.get("rule_id") == "missing_source" for f in findings):
        decision = "hard_block"
    else:
        decision = "soft_block"

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        paths = data_paths or DataPaths.resolve()
        with Catalog.open(paths) as catalog:
            _ensure_task_exists(catalog, task_id)
            payload_bytes = json.dumps(raw_result, sort_keys=True, ensure_ascii=False).encode("utf-8")
            content_hash = hashlib.sha256(payload_bytes).hexdigest()
            draft = EvidenceDraft(
                evidence_id=f"sha256:{content_hash}",
                task_id=task_id,
                requirement_id="M1.5-LINT",
                evidence_type="instruction_loading",
                subject_ref="context.lint",
                exact_scope=str(root_path),
                result=("pass" if decision == "pass" else "fail"),
                basis="observed",
                fields={"decision": decision, "findings_count": len(findings)},
                content=payload_bytes,
                collection_method="mcp:context.lint",
                redaction_status="not_needed",
            )
            store = EvidenceStore(catalog, EventLog(catalog))
            record = store.put(draft, lambda b: b)
            evidence_id = record.evidence_id

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devharness.catalog import Catalog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.events import EventLog
from devharness.paths import DataPaths


class TaskNotFoundError(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"task not found: {task_id}")
        self.task_id = task_id


def validate_task_exists(catalog: Catalog, task_id: str) -> None:
    task_row = catalog.query_value("SELECT 1 FROM tasks WHERE task_id=?", (task_id,))
    if task_row is None:
        raise TaskNotFoundError(task_id)


def task_not_found_response(task_id: str) -> dict[str, Any]:
    return {
        "status": "error",
        "decision": "hard_block",
        "evidence_id": None,
        "data": {},
        "error": {
            "code": "TaskNotFound",
            "message": f"task not found: {task_id}",
        },
    }


def make_error_envelope(
    code: str,
    message: str,
    decision: str | None = "hard_block",
) -> dict[str, Any]:
    return {
        "status": "error",
        "decision": decision,
        "evidence_id": None,
        "data": {},
        "error": {"code": code, "message": message},
    }


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
        validate_task_exists(catalog, task_id)
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

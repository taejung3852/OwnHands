from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devharness.control_profile import ControlProfileError, profile_project
from devharness.paths import DataPaths

HARNESS_PROFILE_TOOL = {
    "name": "harness.profile",
    "description": "Scans repository project structure, configuration layers, rules, and sensitive paths.",
    "inputSchema": {
        "type": "object",
        "required": ["root"],
        "properties": {
            "root": {"type": "string", "description": "Absolute path to project root"},
            "project_id": {"type": "string", "default": "default-project"},
            "worktree_id": {"type": "string", "default": "main"},
            "environment_ref": {"type": "string", "default": "local-env"},
        },
    },
}


def handle_harness_profile(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    if not isinstance(root_str, str) or not root_str.strip():
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": "InvalidArgument", "message": "root must be a non-empty string"},
        }

    root_path = Path(root_str).resolve()
    identity = {
        "project_id": arguments.get("project_id", "default-project"),
        "worktree_id": arguments.get("worktree_id", "main"),
        "environment_ref": arguments.get("environment_ref", "local-env"),
    }
    now = datetime.now(timezone.utc).isoformat()

    try:
        raw_result = profile_project(root_path, identity, observed_at=now)
    except (ControlProfileError, OSError) as error:
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": type(error).__name__, "message": str(error)},
        }

    return {
        "status": "ok",
        "decision": None,
        "evidence_id": None,
        "data": raw_result,
        "error": None,
    }

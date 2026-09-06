from __future__ import annotations

from pathlib import Path
from typing import Any

from devharness.context_architecture import ContextArchitectureError, lint_context
from devharness.mcp.tools.common import record_tool_evidence
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
        evidence_id = record_tool_evidence(
            data_paths=data_paths,
            task_id=task_id,
            requirement_id="M1.5-LINT",
            evidence_type="instruction_loading",
            subject_ref="context.lint",
            scope=str(root_path),
            result_decision=decision,
            payload=raw_result,
        )

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }

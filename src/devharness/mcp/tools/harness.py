from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devharness.control_profile import (
    ControlProfileError,
    assess_baseline_freshness,
    build_baseline,
    build_execution_contract,
    compile_control_profile,
    profile_project,
    render_control_preview,
    run_interview,
)
from devharness.mcp.tools.common import (
    TaskNotFoundError,
    make_error_envelope,
    record_tool_evidence,
    task_not_found_response,
)
from devharness.paths import DataPaths

# -----------------------------------------------------------------------------
# Tool Definitions (Canonical Schemas)
# -----------------------------------------------------------------------------

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

HARNESS_CONTRACT_VALIDATE_TOOL = {
    "name": "harness.contract_validate",
    "description": "Validates the semantic integrity, boundary isolation, and permission approvals by compiling baseline profile and task overlay into an execution contract.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "baseline": {"type": "object", "description": "Baseline control profile (when compiling from overlay)"},
            "overlay": {"type": "object", "description": "Task overlay (when compiling from baseline)"},
            "approvals": {"type": "array", "description": "List of explicit approval records", "default": []},
            "profile": {"type": "object", "description": "Project profile (when building baseline)"},
            "interview_responses": {"type": "array", "description": "Interview answer list"},
            "version": {"type": "integer", "default": 1, "description": "Baseline version"},
            "predecessor_ref": {"type": ["string", "null"], "description": "Predecessor baseline reference"},
            "event_refs": {"type": "array", "items": {"type": "string"}, "description": "Event references", "default": []},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "description": "Evidence references", "default": []},
            "trigger": {"type": "string", "description": "Optional freshness check trigger"},
            "available_refs": {"type": "array", "items": {"type": "string"}, "description": "Available evidence refs for freshness check"},
            "task_id": {"type": "string", "description": "Optional task ID to bind and record evidence"},
        },
    },
}

HARNESS_COMPILE_PREVIEW_TOOL = {
    "name": "harness.compile_preview",
    "description": "Compiles validated execution contract into concrete workspace artifacts and generates user preview.",
    "inputSchema": {
        "type": "object",
        "required": ["contract"],
        "properties": {
            "contract": {"type": "object", "description": "Task Execution Contract"},
            "existing": {"type": "object", "description": "Existing workspace file contents mapping", "default": {}},
            "evidence_index": {"type": "object", "description": "Evidence index mapping", "default": {}},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

# -----------------------------------------------------------------------------
# Tool Handlers
# -----------------------------------------------------------------------------

def handle_harness_profile(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    if not isinstance(root_str, str) or not root_str.strip():
        return make_error_envelope("InvalidArgument", "root must be a non-empty string")

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
        return make_error_envelope(type(error).__name__, str(error))

    # Compatibility anchor: decision=null
    return {
        "status": "ok",
        "decision": None,
        "evidence_id": None,
        "data": raw_result,
        "error": None,
    }


def handle_harness_contract_validate(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    contract = arguments.get("contract")
    baseline = arguments.get("baseline")
    overlay = arguments.get("overlay")
    profile = arguments.get("profile")
    interview_responses = arguments.get("interview_responses")
    approvals = arguments.get("approvals", [])
    now = datetime.now(timezone.utc).isoformat()

    decision = "pass"
    result_data: dict[str, Any] = {}

    if isinstance(profile, dict) and interview_responses is not None:
        if not isinstance(interview_responses, list):
            return make_error_envelope("InvalidArgument", "interview_responses must be a list")
        version = arguments.get("version", 1)
        predecessor_ref = arguments.get("predecessor_ref")
        event_refs = arguments.get("event_refs") or []
        evidence_refs = arguments.get("evidence_refs") or []
        try:
            interview = run_interview(profile, interview_responses)
            built_baseline = build_baseline(
                profile,
                interview,
                version=version,
                predecessor_ref=predecessor_ref,
                event_refs=event_refs,
                evidence_refs=evidence_refs,
            )
            result_data["interview"] = interview
            result_data["baseline"] = built_baseline
            if interview.get("unresolved_decisions"):
                decision = "soft_block"
            else:
                decision = "pass"
            trigger = arguments.get("trigger")
            if isinstance(trigger, str) and trigger.strip():
                available_refs = set(arguments.get("available_refs") or [])
                freshness = assess_baseline_freshness(built_baseline, profile, trigger, available_refs)
                result_data["freshness"] = freshness
                if freshness.get("status") != "fresh":
                    decision = "soft_block"
        except (ControlProfileError, ValueError) as error:
            decision = "hard_block"
            result_data = {"validation_error": str(error), "error_type": type(error).__name__}
    elif isinstance(baseline, dict) and isinstance(overlay, dict):
        try:
            built = build_execution_contract(baseline=baseline, overlay=overlay, approvals=approvals, now=now)
            result_data = built
            perms = built.get("permissions", [])
            gate_status = built.get("gate_status")
            if gate_status == "hard_block" or any(p.get("active") is False for p in perms):
                decision = "hard_block"
            else:
                decision = "pass"
        except (ControlProfileError, ValueError) as error:
            decision = "hard_block"
            result_data = {
                "validation_error": str(error),
                "error_type": type(error).__name__,
            }
    else:
        return make_error_envelope(
            "InvalidArgument",
            "direct contract validation is unsupported; provide 'baseline' and 'overlay' or 'profile' and 'interview_responses'",
        )

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M2-CONTRACT",
                evidence_type="active_configuration",
                subject_ref="harness.contract_validate",
                scope=task_id,
                result_decision=decision,
                payload=result_data,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": result_data,
        "error": None,
    }


def handle_harness_compile_preview(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    contract = arguments.get("contract")
    if not isinstance(contract, dict):
        return make_error_envelope("InvalidArgument", "contract must be an object")

    existing = arguments.get("existing", {})
    evidence_index = arguments.get("evidence_index", {})

    try:
        compiled = compile_control_profile(contract, existing)
        preview_markdown = render_control_preview(contract, compiled, evidence_index)
        data = {
            "contract_id": contract.get("contract_id"),
            "compiled": compiled,
            "preview_markdown": preview_markdown,
        }
        has_hard_findings = any(f.get("severity") == "hard" for f in compiled.get("findings", []))
        if not compiled.get("apply_ready") or has_hard_findings:
            decision = "hard_block"
        else:
            decision = "pass"
    except (ControlProfileError, KeyError, IndexError, TypeError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M2-PREVIEW",
                evidence_type="active_configuration",
                subject_ref="harness.compile_preview",
                scope=str(contract.get("contract_id", "")),
                result_decision=decision,
                payload=data,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": data,
        "error": None,
    }

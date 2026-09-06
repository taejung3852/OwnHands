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
    "description": "Validates the semantic integrity, boundary isolation, and permission approvals of a Task Execution Contract or Baseline Profile.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "contract": {"type": "object", "description": "Compiled or declared Task Execution Contract"},
            "baseline": {"type": "object", "description": "Baseline control profile (when compiling from overlay)"},
            "overlay": {"type": "object", "description": "Task overlay (when compiling from baseline)"},
            "profile": {"type": "object", "description": "Project profile (when building baseline)"},
            "interview_responses": {"type": "array", "description": "Interview answer list"},
            "version": {"type": "integer", "default": 1, "description": "Baseline version"},
            "predecessor_ref": {"type": ["string", "null"], "description": "Predecessor baseline reference"},
            "event_refs": {"type": "array", "items": {"type": "string"}, "description": "Event references", "default": []},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "description": "Evidence references", "default": []},
            "trigger": {"type": "string", "description": "Optional freshness check trigger"},
            "available_refs": {"type": "array", "items": {"type": "string"}, "description": "Available evidence refs for freshness check"},
            "approvals": {"type": "array", "description": "List of explicit approval records", "default": []},
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
    elif isinstance(contract, dict):
        task = contract.get("task")
        if not isinstance(task, dict) or "task_id" not in task:
            decision = "hard_block"
            findings = ["contract.task is missing or invalid"]
        else:
            findings = []
            writable = contract.get("writable_paths", [])
            protected = contract.get("protected_targets", [])
            for w in writable:
                for p in protected:
                    if w == p or str(w).startswith(str(p) + "/") or str(p).startswith(str(w) + "/"):
                        findings.append(f"writable path '{w}' overlaps protected target '{p}'")
                        decision = "hard_block"

            active_perms = contract.get("permissions") or contract.get("active_permissions", [])
            for perm in active_perms:
                if perm.get("active") is False:
                    findings.append(f"permission '{perm.get('permission')}' is unapproved")
                    decision = "hard_block"
            if contract.get("gate_status") == "hard_block":
                findings.append("contract gate_status is hard_block")
                decision = "hard_block"

        result_data = {
            "contract": contract,
            "validation_findings": findings,
        }
    else:
        return make_error_envelope(
            "InvalidArgument",
            "either 'contract', 'baseline' with 'overlay', or 'profile' with 'interview_responses' must be provided",
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

    c = dict(contract)
    c.setdefault("contract_id", c.get("task", {}).get("task_id", "default-contract"))
    c.setdefault("permissions", c.get("active_permissions", []))
    c.setdefault("writable_paths", [])
    c.setdefault("protected_targets", ["AGENTS.md"])
    c.setdefault("approval_triggers", [])
    c.setdefault("validation_criteria", ["pytest"])
    c.setdefault("gate_status", "ready_for_preview")
    c.setdefault("unobserved", [])
    if isinstance(c.get("task"), dict):
        c["task"] = dict(c["task"])
        c["task"].setdefault("goal", "task execution")
    else:
        c["task"] = {"goal": "task execution"}
    if "fingerprint" not in c:
        import hashlib
        import json
        c["fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()

    try:
        compiled = compile_control_profile(c, existing)
        preview_markdown = render_control_preview(c, compiled, evidence_index)
        data = {
            "contract_id": c.get("contract_id"),
            "compiled": compiled,
            "preview_markdown": preview_markdown,
        }
        decision = "pass"
    except (ControlProfileError, ValueError) as error:
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
                scope=str(c.get("contract_id", "")),
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

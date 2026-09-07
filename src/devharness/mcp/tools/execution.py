from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devharness.assurance import AssuranceError, capture_restore_point, verify_restore_point
from devharness.catalog import Catalog
from devharness.codex_app_server import AppServerRecord, AppServerRun
from devharness.control_profile import ControlProfileError, apply_candidate, rollback_candidate
from devharness.control_runtime import evaluate_runtime_controls
from devharness.identity import IdentityRegistry
from devharness.imported_tasks import ImportedTaskError, import_task
from devharness.managed_tasks import ManagedTaskError, prepare_managed_task, record_managed_run
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

SANDBOX_INSPECT_TOOL = {
    "name": "sandbox.inspect",
    "description": "Inspects workspace isolation, worktree boundaries, sensitive files, and command safety.",
    "inputSchema": {
        "type": "object",
        "required": ["root"],
        "properties": {
            "root": {"type": "string", "description": "Absolute path to workspace root"},
            "command": {"type": "string", "description": "Optional shell command string to evaluate before execution"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

GIT_RESTORE_CAPTURE_TOOL = {
    "name": "git.restore_capture",
    "description": "Captures a Git restore snapshot and internal reconstruction verification prior to mutating changes.",
    "inputSchema": {
        "type": "object",
        "required": ["root"],
        "properties": {
            "root": {"type": "string", "description": "Absolute path to git repository root"},
            "task_id": {"type": "string", "description": "Optional task ID to bind and record evidence"},
            "project_id": {"type": "string", "default": "default-project"},
            "worktree_id": {"type": "string", "default": "main"},
            "environment_ref": {"type": "string", "default": "local-env"},
        },
    },
}

RUNTIME_CONTROLS_CHECK_TOOL = {
    "name": "runtime.controls_check",
    "description": "Evaluates observed App Server runtime controls against prepared task contract.",
    "inputSchema": {
        "type": "object",
        "required": ["prepared", "run"],
        "properties": {
            "prepared": {"type": "object", "description": "Prepared managed task document"},
            "run": {"type": "object", "description": "App Server run document"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

TASK_PREPARE_TOOL = {
    "name": "task.prepare",
    "description": "Prepares a managed task execution environment, verifying baseline freshness, contract, and git restore point.",
    "inputSchema": {
        "type": "object",
        "required": [
            "repository",
            "baseline",
            "contract",
            "task",
            "freshness",
            "approval",
            "available_event_refs",
            "available_evidence_refs",
            "sandbox_mode",
            "approval_policy",
            "start_commit",
            "patch_hash",
            "branch",
        ],
        "properties": {
            "repository": {"type": "string"},
            "baseline": {"type": "object"},
            "contract": {"type": "object"},
            "task": {"type": "object"},
            "freshness": {"type": "object"},
            "approval": {"type": "object"},
            "available_event_refs": {"type": "array", "items": {"type": "string"}},
            "available_evidence_refs": {"type": "array", "items": {"type": "string"}},
            "sandbox_mode": {"type": "string"},
            "approval_policy": {"type": "string"},
            "start_commit": {"type": "string"},
            "patch_hash": {"type": "string", "description": "Strictly non-nullable SHA-256 fingerprint"},
            "branch": {"type": "string"},
            "runtime_observations": {"type": "object"},
            "task_id": {"type": "string"},
        },
    },
}

TASK_CREATE_TOOL = {
    "name": "task.create",
    "description": "Explicit atomic creation of Project, Worktree, Task identity, and canonical task.created event.",
    "inputSchema": {
        "type": "object",
        "required": ["project_locator", "worktree_locator", "mode", "commit", "branch", "cwd", "environment_ref"],
        "properties": {
            "project_locator": {"type": "string"},
            "worktree_locator": {"type": "string"},
            "mode": {"enum": ["managed", "imported"]},
            "commit": {"type": "string"},
            "branch": {"type": "string"},
            "cwd": {"type": "string"},
            "environment_ref": {"type": "string"},
            "task_id": {"type": "string"},
        },
    },
}

TASK_RECORD_RUN_TOOL = {
    "name": "task.record_run",
    "description": "Records execution observations and lifecycle terminal events for a managed task run.",
    "inputSchema": {
        "type": "object",
        "required": ["prepared", "run"],
        "properties": {
            "prepared": {"type": "object"},
            "run": {"type": "object"},
            "task_id": {"type": "string"},
        },
    },
}

TASK_IMPORT_TOOL = {
    "name": "task.import",
    "description": "Imports an external task from an authoritative fixture capturing current snapshot, diff, and test run.",
    "inputSchema": {
        "type": "object",
        "required": ["fixture"],
        "properties": {
            "fixture": {"type": "object", "description": "Authoritative import fixture document"},
        },
    },
}

HARNESS_CANDIDATE_APPLY_TOOL = {
    "name": "harness.candidate_apply",
    "description": "Applies compiled candidate configuration artifacts to workspace under explicit approval.",
    "inputSchema": {
        "type": "object",
        "required": ["compiled", "root", "approval"],
        "properties": {
            "compiled": {"type": "object"},
            "root": {"type": "string"},
            "approval": {"type": "object"},
            "task_id": {"type": "string"},
        },
    },
}

HARNESS_CANDIDATE_ROLLBACK_TOOL = {
    "name": "harness.candidate_rollback",
    "description": "Rolls back applied candidate configuration changes using journal recording.",
    "inputSchema": {
        "type": "object",
        "required": ["root", "journal_path"],
        "properties": {
            "root": {"type": "string"},
            "journal_path": {"type": "string"},
            "task_id": {"type": "string"},
        },
    },
}

SENSITIVE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r"^id_rsa.*$", re.IGNORECASE),
    re.compile(r"^credentials(\.json)?$", re.IGNORECASE),
]

DANGEROUS_PATTERNS = [
    (re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\s+([/~]|\$HOME|\.\.)"), "Destructive deletion targeting root, home, or parent directory", "hard_block"),
    (re.compile(r"(curl|wget)\s+.*\|\s*(bash|sh|zsh)"), "Piping remote script directly to shell interpreter", "hard_block"),
    (re.compile(r"\bsudo\s+"), "Elevated privileges (sudo) execution in sandbox", "soft_block"),
    (re.compile(r"\b(pip|npm|yarn|pnpm)\s+(install|add)"), "External package installation modifying runtime dependencies", "soft_block"),
]

# -----------------------------------------------------------------------------
# Tool Handlers
# -----------------------------------------------------------------------------

def handle_sandbox_inspect(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    if not isinstance(root_str, str) or not root_str.strip():
        return make_error_envelope("InvalidArgument", "root must be a non-empty string")

    root_path = Path(root_str).resolve()
    if not root_path.is_dir():
        return make_error_envelope("DirectoryNotFound", f"workspace root does not exist: {root_path}")

    is_git_repo = (root_path / ".git").exists()
    git_branch = None
    if is_git_repo:
        try:
            branch_proc = subprocess.run(
                ["git", "-C", str(root_path), "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            git_branch = branch_proc.stdout.strip() or "HEAD (detached)"
        except OSError:
            git_branch = "unobserved"

    sensitive_files: list[str] = []
    try:
        for entry in root_path.iterdir():
            if any(pattern.match(entry.name) for pattern in SENSITIVE_PATTERNS):
                sensitive_files.append(entry.name)
    except OSError:
        pass

    command = arguments.get("command")
    command_risk: dict[str, Any] | None = None
    decision = "pass"

    if command is not None:
        if not isinstance(command, str):
            return make_error_envelope("InvalidArgument", "command must be a string")
        matched_threat = None
        for pat, desc, threat_decision in DANGEROUS_PATTERNS:
            if pat.search(command):
                matched_threat = {"pattern": pat.pattern, "description": desc, "decision": threat_decision}
                if threat_decision == "hard_block":
                    decision = "hard_block"
                    break
                elif threat_decision == "soft_block" and decision != "hard_block":
                    decision = "soft_block"
        command_risk = {
            "command": command,
            "threat_detected": matched_threat is not None,
            "threat_details": matched_threat,
        }
    else:
        if sensitive_files:
            decision = "soft_block"

    data = {
        "workspace_root": str(root_path),
        "is_git_repository": is_git_repo,
        "current_branch": git_branch,
        "sensitive_files_detected": sensitive_files,
        "command_assessment": command_risk,
    }

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M2-SANDBOX",
                evidence_type="sandbox_probe",
                subject_ref="sandbox.inspect",
                scope=str(root_path),
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


def handle_git_restore_capture(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    if not isinstance(root_str, str) or not root_str.strip():
        return make_error_envelope("InvalidArgument", "root must be a non-empty string")

    root_path = Path(root_str).resolve()
    task_id = arguments.get("task_id") or "default-task"
    identity = {
        "project_id": arguments.get("project_id", "default-project"),
        "worktree_id": arguments.get("worktree_id", "main"),
        "environment_ref": arguments.get("environment_ref", "local-env"),
        "task_id": task_id,
    }
    now = datetime.now(timezone.utc).isoformat()

    try:
        raw_result = capture_restore_point(root_path, identity, observed_at=now)
        verification = verify_restore_point(root_path, raw_result)
    except (AssuranceError, OSError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    # Strip internal binary bytes
    public_restore_point = {k: v for k, v in raw_result.items() if not k.startswith("_")}
    public_verification = {k: v for k, v in verification.items() if not k.startswith("_")}
    data = {
        **public_restore_point,
        "verification": public_verification,
    }

    evidence_id = None
    if isinstance(arguments.get("task_id"), str) and arguments["task_id"].strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=arguments["task_id"],
                requirement_id="M4-RESTORE",
                evidence_type="workspace_restore_point",
                subject_ref="git.restore_capture",
                scope=str(root_path),
                result_decision="pass",
                payload=data,
            )
        except TaskNotFoundError:
            return task_not_found_response(arguments["task_id"])

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": evidence_id,
        "data": data,
        "error": None,
    }


def handle_runtime_controls_check(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    prepared = arguments.get("prepared")
    run_dict = arguments.get("run")
    if not isinstance(prepared, dict) or not isinstance(run_dict, dict):
        return make_error_envelope("InvalidArgument", "prepared and run must be objects")

    try:
        records = [AppServerRecord(**r) for r in run_dict.get("records", [])]
        run_obj = AppServerRun(
            records=records,
            thread_id=run_dict.get("thread_id", ""),
            turn_id=run_dict.get("turn_id", ""),
            terminal_status=run_dict.get("terminal_status", "completed"),
            instruction_sources=run_dict.get("instruction_sources", []),
            codex_version=run_dict.get("codex_version", "0.48.0"),
            protocol_fingerprint=run_dict.get("protocol_fingerprint", ""),
        )
        packet = evaluate_runtime_controls(prepared, run_obj)
    except Exception as error:
        return make_error_envelope(type(error).__name__, str(error))

    all_checks = [
        chk
        for ctrl in packet.values()
        for chk in (ctrl.get("configured"), ctrl.get("loaded"), ctrl.get("enforced"))
        if isinstance(chk, dict)
    ]

    if any(c.get("result") == "fail" for c in all_checks):
        decision = "hard_block"
    else:
        configured_meta = prepared.get("configured", {})
        required_controls = [
            name
            for name, meta in configured_meta.items()
            if isinstance(meta, dict) and meta.get("observed") is True
        ]
        if not required_controls:
            required_controls = ["sandbox", "approval", "agents"]

        REQUIRED_CHECKS_MAP = {
            "sandbox": ("configured", "enforced"),
            "approval": ("configured", "enforced"),
            "agents": ("configured", "loaded"),
            "config": ("configured",),
            "rules": ("configured",),
            "hooks": ("configured",),
        }

        all_required_pass = True
        for name in required_controls:
            ctrl = packet.get(name)
            if not ctrl:
                all_required_pass = False
                break
            needed_checks = REQUIRED_CHECKS_MAP.get(name, ("configured",))
            for chk_name in needed_checks:
                chk = ctrl.get(chk_name, {})
                if chk.get("result") != "pass" or chk.get("basis") != "observed":
                    all_required_pass = False
                    break
            if not all_required_pass:
                break

        decision = "pass" if all_required_pass else "unobserved"

    evidence_id = None
    task_id = arguments.get("task_id") or prepared.get("task", {}).get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M3-RUNTIME-CONTROLS",
                evidence_type="active_configuration",
                subject_ref="runtime.controls_check",
                scope=task_id,
                result_decision=decision,
                payload=packet,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": packet,
        "error": None,
    }


def handle_task_prepare(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    patch_hash = arguments.get("patch_hash")
    if not isinstance(patch_hash, str) or not patch_hash.startswith("sha256:") or len(patch_hash) != 71:
        return make_error_envelope("InvalidArgument", "patch_hash must be a valid sha256 fingerprint string")

    now = datetime.now(timezone.utc).isoformat()
    try:
        prepared = prepare_managed_task(arguments, now=now)
    except (ManagedTaskError, ValueError, OSError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    evidence_id = None
    task_id = arguments.get("task_id") or prepared.get("task", {}).get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M3-TASK-PREPARE",
                evidence_type="active_configuration",
                subject_ref="task.prepare",
                scope=task_id,
                result_decision="pass",
                payload=prepared,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": evidence_id,
        "data": prepared,
        "error": None,
    }


def handle_task_create(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    paths = data_paths or DataPaths.resolve()
    for field in ("project_locator", "worktree_locator", "mode", "commit", "branch", "cwd", "environment_ref"):
        if not isinstance(arguments.get(field), str) or not arguments[field].strip():
            return make_error_envelope("InvalidArgument", f"{field} must be a non-empty string")

    try:
        with Catalog.open(paths) as catalog:
            registry = IdentityRegistry(catalog)
            created = registry.create_task_lifecycle(
                project_locator=arguments["project_locator"],
                worktree_locator=arguments["worktree_locator"],
                mode=arguments["mode"],
                commit=arguments["commit"],
                branch=arguments["branch"],
                cwd=arguments["cwd"],
                environment_ref=arguments["environment_ref"],
                task_id=arguments.get("task_id"),
            )
            data = {
                "task_id": created.task_id,
                "project_id": created.project_id,
                "worktree_id": created.worktree_id,
                "mode": created.mode,
                "commit": created.commit,
                "branch": created.branch,
                "cwd": created.cwd,
                "environment_ref": created.environment_ref,
                "created_at": created.created_at,
            }
    except Exception as error:
        return make_error_envelope(type(error).__name__, str(error))

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": None,
        "data": data,
        "error": None,
    }


def handle_task_record_run(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    prepared = arguments.get("prepared")
    run_dict = arguments.get("run")
    if not isinstance(prepared, dict) or not isinstance(run_dict, dict):
        return make_error_envelope("InvalidArgument", "prepared and run must be objects")

    paths = data_paths or DataPaths.resolve()
    try:
        records = [AppServerRecord(**r) for r in run_dict.get("records", [])]
        run_obj = AppServerRun(
            records=records,
            thread_id=run_dict.get("thread_id", ""),
            turn_id=run_dict.get("turn_id", ""),
            terminal_status=run_dict.get("terminal_status", "completed"),
            instruction_sources=run_dict.get("instruction_sources", []),
            codex_version=run_dict.get("codex_version", "0.48.0"),
            protocol_fingerprint=run_dict.get("protocol_fingerprint", ""),
        )
        with Catalog.open(paths) as catalog:
            result = record_managed_run(catalog, prepared, run_obj)
    except Exception as error:
        return make_error_envelope(type(error).__name__, str(error))

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": None,
        "data": result,
        "error": None,
    }


def handle_task_import(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    fixture = arguments.get("fixture")
    if not isinstance(fixture, dict):
        return make_error_envelope("InvalidArgument", "fixture must be an object")

    paths = data_paths or DataPaths.resolve()
    try:
        with Catalog.open(paths) as catalog:
            imported = import_task(fixture, catalog)
    except (ImportedTaskError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": None,
        "data": imported,
        "error": None,
    }


def handle_harness_candidate_apply(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    compiled = arguments.get("compiled")
    root_str = arguments.get("root")
    approval = arguments.get("approval")
    if not isinstance(compiled, dict) or not isinstance(root_str, str) or not isinstance(approval, dict):
        return make_error_envelope("InvalidArgument", "compiled (dict), root (str), and approval (dict) are required")

    root_path = Path(root_str).resolve()
    try:
        raw_result = apply_candidate(compiled, root_path, approval)
    except (ControlProfileError, ValueError, OSError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M2-CANDIDATE-APPLY",
                evidence_type="active_configuration",
                subject_ref="harness.candidate_apply",
                scope=str(root_path),
                result_decision="pass",
                payload=raw_result,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }


def handle_harness_candidate_rollback(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    journal_path = arguments.get("journal_path")
    if not isinstance(root_str, str) or not isinstance(journal_path, (str, Path)):
        return make_error_envelope("InvalidArgument", "root (str) and journal_path (str) are required")

    root_path = Path(root_str).resolve()
    try:
        raw_result = rollback_candidate(root_path, journal_path)
    except (ControlProfileError, ValueError, OSError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M2-CANDIDATE-ROLLBACK",
                evidence_type="workspace_restore_point",
                subject_ref="harness.candidate_rollback",
                scope=str(root_path),
                result_decision="pass",
                payload=raw_result,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }

from __future__ import annotations

from pathlib import Path
from typing import Any

from devharness.catalog import Catalog
from devharness.context_architecture import (
    ApplicabilityGate,
    ContextArchitectureError,
    build_comparison_plan,
    evaluate_comparison,
    evaluate_context_guarantees,
    lint_context,
    validate_manifest,
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

CONTEXT_INSPECT_TOOL = {
    "name": "context.inspect",
    "description": "Validates a context manifest against authoritative event and evidence reference closures.",
    "inputSchema": {
        "type": "object",
        "required": ["manifest"],
        "properties": {
            "manifest": {"type": "object", "description": "Context manifest dictionary"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}, "description": "Authoritative evidence IDs"},
            "event_ids": {"type": "array", "items": {"type": "string"}, "description": "Authoritative event IDs"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

CONTEXT_GATE_EVALUATE_TOOL = {
    "name": "context.gate_evaluate",
    "description": "Evaluates applicability gate across candidate instruction and control sources.",
    "inputSchema": {
        "type": "object",
        "required": ["gate_input"],
        "properties": {
            "gate_input": {"type": "object", "description": "Applicability gate input payload"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

CONTEXT_BENCHMARK_PLAN_TOOL = {
    "name": "context.benchmark_plan",
    "description": "Generates a 9-run balanced crossover comparison plan for an evaluation package.",
    "inputSchema": {
        "type": "object",
        "required": ["package", "target_commit"],
        "properties": {
            "package": {"type": "object", "description": "Comparison package configuration"},
            "target_commit": {"type": "string", "description": "Target commit hash"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

CONTEXT_BENCHMARK_EVALUATE_TOOL = {
    "name": "context.benchmark_evaluate",
    "description": "Evaluates observed 9-run comparison results against baseline conditions.",
    "inputSchema": {
        "type": "object",
        "required": ["package", "runs"],
        "properties": {
            "package": {"type": "object", "description": "Comparison package configuration"},
            "runs": {"type": "array", "items": {"type": "object"}, "description": "List of 9 execution runs"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

CONTEXT_GUARANTEE_EVALUATE_TOOL = {
    "name": "context.guarantee_evaluate",
    "description": "Evaluates context claims against authoritative evidence records, preserving Core result categories and verdicts.",
    "inputSchema": {
        "type": "object",
        "required": ["matrix", "manifest", "evidence_records"],
        "properties": {
            "matrix": {"type": "object", "description": "Context guarantee matrix"},
            "manifest": {"type": "object", "description": "Context manifest"},
            "evidence_records": {"type": "array", "items": {"type": "object"}, "description": "Evidence records"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

# -----------------------------------------------------------------------------
# Tool Handlers
# -----------------------------------------------------------------------------

def handle_context_lint(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    if not isinstance(root_str, str) or not root_str.strip():
        return make_error_envelope("InvalidArgument", "root must be a non-empty string")

    sources = arguments.get("sources")
    if not isinstance(sources, list):
        return make_error_envelope("InvalidArgument", "sources must be a list")

    root_path = Path(root_str).resolve()
    try:
        raw_result = lint_context(root_path, sources)
    except (ContextArchitectureError, OSError) as error:
        return make_error_envelope(type(error).__name__, str(error))

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
        try:
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
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }


def handle_context_inspect(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    manifest = arguments.get("manifest")
    if not isinstance(manifest, dict):
        return make_error_envelope("InvalidArgument", "manifest must be an object")

    evidence_ids = arguments.get("evidence_ids")
    event_ids = arguments.get("event_ids")

    # Authoritative resolution from catalog if not provided
    if (evidence_ids is None or event_ids is None) and data_paths is not None:
        try:
            with Catalog.open(data_paths) as catalog:
                manifest_task = manifest.get("task", {})
                t_id = manifest_task.get("task_id") if isinstance(manifest_task, dict) else None
                if evidence_ids is None:
                    if t_id:
                        rows = catalog.connection.execute("SELECT evidence_id FROM evidence WHERE task_id=?", (t_id,)).fetchall()
                    else:
                        rows = catalog.connection.execute("SELECT evidence_id FROM evidence").fetchall()
                    evidence_ids = [r["evidence_id"] for r in rows]
                if event_ids is None:
                    if t_id:
                        rows = catalog.connection.execute("SELECT event_id FROM events WHERE task_id=?", (t_id,)).fetchall()
                    else:
                        rows = catalog.connection.execute("SELECT event_id FROM events").fetchall()
                    event_ids = [r["event_id"] for r in rows]
        except Exception:
            evidence_ids = evidence_ids or []
            event_ids = event_ids or []
    else:
        evidence_ids = evidence_ids or []
        event_ids = event_ids or []

    try:
        validate_manifest(manifest, set(evidence_ids), set(event_ids))
        decision = "pass"
        data = {"manifest_id": manifest.get("manifest_id"), "valid": True, "error": None}
    except (ContextArchitectureError, ValueError) as error:
        decision = "hard_block"
        data = {"manifest_id": manifest.get("manifest_id"), "valid": False, "validation_error": str(error)}

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M1.5-INSPECT",
                evidence_type="instruction_loading",
                subject_ref="context.inspect",
                scope=str(manifest.get("manifest_id")),
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


def handle_context_gate_evaluate(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    gate_input = arguments.get("gate_input")
    if not isinstance(gate_input, dict):
        return make_error_envelope("InvalidArgument", "gate_input must be an object")

    try:
        raw_result = ApplicabilityGate().evaluate(gate_input)
    except (ContextArchitectureError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    all_overlays = raw_result.get("instruction_overlay", []) + raw_result.get("control_overlay", [])
    decisions = {item.get("decision") for item in all_overlays}
    if "forbidden" in decisions:
        decision = "hard_block"
    elif any(d in {"unobserved", "replace_with_specific"} for d in decisions):
        decision = "soft_block"
    else:
        decision = "pass"

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M1.5-GATE",
                evidence_type="active_configuration",
                subject_ref="context.gate_evaluate",
                scope=gate_input.get("trigger", "unknown"),
                result_decision=decision,
                payload=raw_result,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }


def handle_context_benchmark_plan(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    package = arguments.get("package")
    target_commit = arguments.get("target_commit")
    if not isinstance(package, dict) or not isinstance(target_commit, str) or not target_commit.strip():
        return make_error_envelope("InvalidArgument", "package (dict) and target_commit (str) are required")

    try:
        plan = build_comparison_plan(package, target_commit)
    except (ContextArchitectureError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    data = {"package_id": package.get("package_id"), "target_commit": target_commit, "plan": plan}
    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M1.5-BENCH-PLAN",
                evidence_type="direct_feature_probe",
                subject_ref="context.benchmark_plan",
                scope=package.get("package_id", ""),
                result_decision="pass",
                payload=data,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": "pass",
        "evidence_id": evidence_id,
        "data": data,
        "error": None,
    }


def handle_context_benchmark_evaluate(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    package = arguments.get("package")
    runs = arguments.get("runs")
    if not isinstance(package, dict) or not isinstance(runs, list):
        return make_error_envelope("InvalidArgument", "package (dict) and runs (list) are required")

    try:
        raw_result = evaluate_comparison(package, runs)
    except (ContextArchitectureError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    verdict = raw_result.get("improvement_verdict")
    if verdict == "recommended":
        decision = "pass"
    elif verdict == "no_improvement":
        decision = "soft_block"
    elif verdict == "not_evaluated":
        decision = "unobserved"
    else:
        decision = "unobserved"

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M1.5-BENCH-EVAL",
                evidence_type="direct_feature_probe",
                subject_ref="context.benchmark_evaluate",
                scope=package.get("package_id", ""),
                result_decision=decision,
                payload=raw_result,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }


def handle_context_guarantee_evaluate(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    matrix = arguments.get("matrix")
    manifest = arguments.get("manifest")
    evidence_records = arguments.get("evidence_records")
    if not isinstance(matrix, dict) or not isinstance(manifest, dict) or not isinstance(evidence_records, list):
        return make_error_envelope("InvalidArgument", "matrix (dict), manifest (dict), and evidence_records (list) are required")

    try:
        raw_results = evaluate_context_guarantees(matrix, manifest, evidence_records)
    except (ContextArchitectureError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    verdicts = {r.get("verdict") for r in raw_results}
    if "contradicted" in verdicts:
        decision = "hard_block"
    elif all(v == "supported" for v in verdicts) and raw_results:
        decision = "pass"
    else:
        decision = "soft_block"

    data = {"manifest_id": manifest.get("manifest_id"), "results": raw_results}
    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M1.5-GUARANTEE",
                evidence_type="instruction_loading",
                subject_ref="context.guarantee_evaluate",
                scope=manifest.get("manifest_id", ""),
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

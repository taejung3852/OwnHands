from __future__ import annotations

from typing import Any

from devharness.assurance import AssuranceError, compare_test_runs, evaluate_regression_gate
from devharness.mcp.tools.common import record_tool_evidence
from devharness.paths import DataPaths

TESTS_COMPARE_RUNS_TOOL = {
    "name": "tests.compare_runs",
    "description": "Compares pre-change baseline test receipts against post-change test receipts.",
    "inputSchema": {
        "type": "object",
        "required": ["before", "after"],
        "properties": {
            "before": {"type": "object", "description": "Pre-change test run object with receipts"},
            "after": {"type": "object", "description": "Post-change test run object with receipts"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

ASSURANCE_GATE_EVALUATE_TOOL = {
    "name": "assurance.gate_evaluate",
    "description": "Authoritative evaluation of the regression gate combining contract, impact, design, comparisons, and gaps.",
    "inputSchema": {
        "type": "object",
        "required": ["contract", "impact", "design", "comparison", "gaps"],
        "properties": {
            "contract": {"type": "object", "description": "Task Execution Contract"},
            "impact": {"type": "object", "description": "Actual diff impact analysis"},
            "design": {"type": "object", "description": "Test Design Memo"},
            "comparison": {"type": "object", "description": "Test comparison results"},
            "gaps": {"type": "object", "description": "Test gap detection results"},
            "override": {"type": ["object", "null"], "description": "Optional human override"},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}


def handle_tests_compare_runs(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    before = arguments.get("before")
    after = arguments.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": "InvalidArgument", "message": "before and after must be objects"},
        }

    try:
        raw_result = compare_test_runs(before, after)
    except (AssuranceError, ValueError) as error:
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": type(error).__name__, "message": str(error)},
        }

    comparisons = raw_result.get("comparisons", [])
    statuses = {c.get("status") for c in comparisons}
    if "regression" in statuses:
        decision = "hard_block"
    elif any(s in {"stale", "incomparable", "missing_after", "contradicted"} for s in statuses):
        decision = "soft_block"
    else:
        decision = "pass"

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        evidence_id = record_tool_evidence(
            data_paths=data_paths,
            task_id=task_id,
            requirement_id="M4-COMPARE",
            evidence_type="test_execution",
            subject_ref="tests.compare_runs",
            scope="test_comparison",
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


def handle_assurance_gate_evaluate(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    for field in ("contract", "impact", "design", "comparison", "gaps"):
        if not isinstance(arguments.get(field), dict):
            return {
                "status": "error",
                "decision": None,
                "evidence_id": None,
                "data": {},
                "error": {"type": "InvalidArgument", "message": f"{field} must be an object"},
            }

    contract = arguments["contract"]
    impact = arguments["impact"]
    design = arguments["design"]
    comparison = arguments["comparison"]
    gaps = arguments["gaps"]
    override = arguments.get("override")

    try:
        raw_result = evaluate_regression_gate(
            contract=contract,
            impact=impact,
            design=design,
            comparison=comparison,
            gaps=gaps,
            override=override,
        )
    except (AssuranceError, ValueError) as error:
        return {
            "status": "error",
            "decision": None,
            "evidence_id": None,
            "data": {},
            "error": {"type": type(error).__name__, "message": str(error)},
        }

    decision = raw_result.get("decision", "hard_block")
    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        evidence_id = record_tool_evidence(
            data_paths=data_paths,
            task_id=task_id,
            requirement_id="M4-GATE",
            evidence_type="regression_gate",
            subject_ref="assurance.gate_evaluate",
            scope="regression_gate",
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

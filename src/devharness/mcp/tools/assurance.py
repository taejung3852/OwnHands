from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devharness.assurance import (
    AssuranceError,
    analyze_impact,
    build_assurance_packet,
    build_test_design,
    compare_test_runs,
    detect_test_gaps,
    evaluate_regression_gate,
    record_test_baseline,
    validate_assurance_packet,
)
from devharness.catalog import Catalog
from devharness.events import EventLog
from devharness.evidence import EvidenceStore
from devharness.guarantees import GuaranteeEvaluator, GuaranteeValidationError
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

TESTS_BASELINE_RECORD_TOOL = {
    "name": "tests.baseline_record",
    "description": "Records pre-change baseline test run receipts. Failing baseline tests (TDD RED) are strictly preserved and validated.",
    "inputSchema": {
        "type": "object",
        "required": ["contract", "selection", "receipts", "observed_at"],
        "properties": {
            "contract": {"type": "object"},
            "selection": {"type": "array", "items": {"type": "object"}},
            "receipts": {"type": "array", "items": {"type": "object"}},
            "observed_at": {"type": "string"},
            "task_id": {"type": "string"},
        },
    },
}

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

TESTS_GAP_DETECT_TOOL = {
    "name": "tests.gap_detect",
    "description": "Detects test coverage gaps across required criteria, impact hypotheses, and test comparisons.",
    "inputSchema": {
        "type": "object",
        "required": ["contract", "impact", "design", "comparison"],
        "properties": {
            "contract": {"type": "object"},
            "impact": {"type": "object"},
            "design": {"type": "object"},
            "comparison": {"type": "object"},
            "task_id": {"type": "string"},
        },
    },
}

TESTS_DESIGN_MEMO_TOOL = {
    "name": "tests.design_memo",
    "description": "Builds test design memo mapping changed impact relations to test criteria and requirements.",
    "inputSchema": {
        "type": "object",
        "required": ["contract", "impact", "requirement_catalog"],
        "properties": {
            "contract": {"type": "object"},
            "impact": {"type": "object"},
            "requirement_catalog": {"type": "array", "items": {"type": "object"}},
            "task_id": {"type": "string"},
        },
    },
}

GIT_DIFF_IMPACT_TOOL = {
    "name": "git.diff_impact",
    "description": "Analyzes Git tracked changes against declared relations (feature, test, dependency, contract) to compute impact scope.",
    "inputSchema": {
        "type": "object",
        "required": ["root", "contract", "restore_point", "relation_catalog"],
        "properties": {
            "root": {"type": "string", "description": "Absolute path to repository root"},
            "contract": {"type": "object", "description": "Task Execution Contract"},
            "restore_point": {"type": "object", "description": "Git restore point"},
            "relation_catalog": {"type": "object", "description": "Relation catalog mapping changes to targets"},
            "task_id": {"type": "string", "description": "Optional task ID to bind and record evidence"},
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
            "restore_point": {"type": "object"},
            "restore_verification": {"type": "object"},
            "before": {"type": "object"},
            "after": {"type": "object"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "task_id": {"type": "string", "description": "Optional task ID to record evidence"},
        },
    },
}

GUARANTEE_EVALUATE_TOOL = {
    "name": "guarantee.evaluate",
    "description": "Authoritative evaluation of product guarantee claims for a task across catalog and evidence stores.",
    "inputSchema": {
        "type": "object",
        "required": ["task_id"],
        "properties": {
            "task_id": {"type": "string"},
            "claim_ids": {"type": "array", "items": {"type": "string"}},
            "matrix_path": {"type": "string"},
        },
    },
}

# -----------------------------------------------------------------------------
# Tool Handlers
# -----------------------------------------------------------------------------

def handle_tests_baseline_record(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    contract = arguments.get("contract")
    selection = arguments.get("selection")
    receipts = arguments.get("receipts")
    observed_at = arguments.get("observed_at")
    if not isinstance(contract, dict) or not isinstance(selection, list) or not isinstance(receipts, list) or not isinstance(observed_at, str):
        return make_error_envelope("InvalidArgument", "contract (dict), selection (list), receipts (list), observed_at (str) are required")

    try:
        run_record = record_test_baseline(contract, selection, receipts, observed_at)
    except (AssuranceError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    # TDD baseline recording itself succeeds (pass), even if some tests in baseline failed!
    decision = "pass"
    evidence_id = None
    task_id = arguments.get("task_id") or contract.get("task", {}).get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M4-BASELINE-RECORD",
                evidence_type="test_execution",
                subject_ref="tests.baseline_record",
                scope=task_id,
                result_decision=decision,
                payload=run_record,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": run_record,
        "error": None,
    }


def handle_tests_compare_runs(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    before = arguments.get("before")
    after = arguments.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return make_error_envelope("InvalidArgument", "before and after must be objects")

    try:
        raw_result = compare_test_runs(before, after)
    except (AssuranceError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    comparisons = raw_result.get("comparisons", [])
    statuses = {c.get("status") for c in comparisons}

    # 11 Comparison statuses mapping with strict precedence: hard > soft > unobserved > pass
    if "regression" in statuses or "contradicted" in statuses:
        decision = "hard_block"
    elif any(s in {"stale", "incomparable", "missing_after", "unchanged_failure", "inconclusive"} for s in statuses):
        decision = "soft_block"
    elif any(s in {"missing_before", "not_run"} for s in statuses) or not comparisons:
        decision = "unobserved"
    elif all(s in {"comparable_pass", "fixed_failure"} for s in statuses):
        decision = "pass"
    else:
        decision = "unobserved"

    evidence_id = None
    task_id = arguments.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
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
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": raw_result,
        "error": None,
    }


def handle_tests_gap_detect(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    contract = arguments.get("contract")
    impact = arguments.get("impact")
    design = arguments.get("design")
    comparison = arguments.get("comparison")
    if not all(isinstance(arguments.get(k), dict) for k in ("contract", "impact", "design", "comparison")):
        return make_error_envelope("InvalidArgument", "contract, impact, design, and comparison must be objects")

    try:
        gaps_result = detect_test_gaps(contract, impact, design, comparison)
    except (AssuranceError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    gaps = gaps_result.get("gaps", [])
    if any(g.get("required") for g in gaps):
        decision = "hard_block"
    elif gaps:
        decision = "soft_block"
    else:
        decision = "pass"

    evidence_id = None
    task_id = arguments.get("task_id") or contract.get("task", {}).get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M4-GAPS",
                evidence_type="regression_gate",
                subject_ref="tests.gap_detect",
                scope=task_id,
                result_decision=decision,
                payload=gaps_result,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": gaps_result,
        "error": None,
    }


def handle_tests_design_memo(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    contract = arguments.get("contract")
    impact = arguments.get("impact")
    catalog = arguments.get("requirement_catalog")
    if not isinstance(contract, dict) or not isinstance(impact, dict) or not isinstance(catalog, list):
        return make_error_envelope("InvalidArgument", "contract (dict), impact (dict), and requirement_catalog (list) are required")

    try:
        design = build_test_design(contract, impact, catalog)
    except (AssuranceError, ValueError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    mappings = design.get("mappings", [])
    has_omitted = any(bool(m.get("omitted_viewpoints")) for m in mappings if isinstance(m, dict))
    decision = "soft_block" if has_omitted else "pass"

    evidence_id = None
    task_id = arguments.get("task_id") or contract.get("task", {}).get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M4-DESIGN",
                evidence_type="feature_impact",
                subject_ref="tests.design_memo",
                scope=task_id,
                result_decision=decision,
                payload=design,
            )
        except TaskNotFoundError:
            return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": design,
        "error": None,
    }


def handle_git_diff_impact(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    root_str = arguments.get("root")
    if not isinstance(root_str, str) or not root_str.strip():
        return make_error_envelope("InvalidArgument", "root must be a non-empty string")

    root_path = Path(root_str).resolve()
    contract = arguments.get("contract")
    restore_point = arguments.get("restore_point")
    relation_catalog = arguments.get("relation_catalog")
    now = datetime.now(timezone.utc).isoformat()

    if not (isinstance(contract, dict) and isinstance(restore_point, dict) and isinstance(relation_catalog, dict)):
        return make_error_envelope(
            "InvalidArgument",
            "contract, restore_point, and relation_catalog are required objects",
        )

    try:
        raw_result = analyze_impact(
            repository=root_path,
            restore_point=restore_point,
            contract=contract,
            relation_catalog=relation_catalog,
            observed_at=now,
        )
    except (AssuranceError, ValueError, OSError) as error:
        return make_error_envelope(type(error).__name__, str(error))

    if raw_result.get("protected_target_changes"):
        decision = "hard_block"
    elif raw_result.get("unobserved"):
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
                requirement_id="M4-IMPACT",
                evidence_type="feature_impact",
                subject_ref="git.diff_impact",
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


def handle_assurance_gate_evaluate(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    for field in ("contract", "impact", "design", "comparison", "gaps"):
        if not isinstance(arguments.get(field), dict):
            return make_error_envelope("InvalidArgument", f"{field} must be an object")

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
        return make_error_envelope(type(error).__name__, str(error))

    # Optional 12-argument packet assembly if provided
    restore_point = arguments.get("restore_point")
    restore_verification = arguments.get("restore_verification")
    before = arguments.get("before")
    after = arguments.get("after")
    evidence_refs = arguments.get("evidence_refs")

    packet = None
    if all(x is not None for x in (restore_point, restore_verification, before, after, evidence_refs)):
        try:
            packet = build_assurance_packet(
                contract=contract,
                restore_point=restore_point,
                restore_verification=restore_verification,
                impact=impact,
                test_design=design,
                before=before,
                after=after,
                comparison=comparison,
                gaps=gaps,
                gate=raw_result,
                evidence_refs=evidence_refs,
                observed_at=datetime.now(timezone.utc).isoformat(),
            )
            validate_assurance_packet(packet)
        except (AssuranceError, ValueError) as error:
            return make_error_envelope(type(error).__name__, f"packet validation failed: {error}")

    data = {**raw_result}
    if packet is not None:
        data["assurance_packet"] = packet

    decision = raw_result.get("decision", "hard_block")
    evidence_id = None
    task_id = arguments.get("task_id") or contract.get("task", {}).get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        try:
            evidence_id = record_tool_evidence(
                data_paths=data_paths,
                task_id=task_id,
                requirement_id="M4-GATE",
                evidence_type="regression_gate",
                subject_ref="assurance.gate_evaluate",
                scope="regression_gate",
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


def handle_guarantee_evaluate(arguments: dict[str, Any], data_paths: DataPaths | None = None) -> dict:
    task_id = arguments.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        return make_error_envelope("InvalidArgument", "task_id must be a non-empty string")

    paths = data_paths or DataPaths.resolve()
    matrix_path_str = arguments.get("matrix_path")
    if matrix_path_str:
        matrix_path = Path(matrix_path_str)
    else:
        # Default to canonical guarantee matrix
        matrix_path = Path(__file__).resolve().parents[4] / "docs" / "product" / "guarantee-matrix.v1.json"

    claim_ids = arguments.get("claim_ids")
    try:
        with Catalog.open(paths) as catalog:
            evidence_store = EvidenceStore(catalog, EventLog(catalog))
            evaluator = GuaranteeEvaluator(catalog, evidence_store, matrix_path)
            report = evaluator.evaluate(task_id, claim_ids)
    except TaskNotFoundError:
        return task_not_found_response(task_id)
    except (GuaranteeValidationError, ValueError, OSError) as error:
        if "unknown task" in str(error):
            return task_not_found_response(task_id)
        return make_error_envelope(type(error).__name__, str(error))

    claim_results = report.get("claim_results", [])
    verdicts = {c.get("verdict") for c in claim_results}
    if "contradicted" in verdicts:
        decision = "hard_block"
    elif "not_evaluated" in verdicts or not verdicts:
        decision = "unobserved"
    elif all(v == "supported" for v in verdicts):
        decision = "pass"
    else:
        decision = "unobserved"

    evidence_id = None
    try:
        evidence_id = record_tool_evidence(
            data_paths=data_paths,
            task_id=task_id,
            requirement_id="M0-GUARANTEE",
            evidence_type="active_configuration",
            subject_ref="guarantee.evaluate",
            scope=task_id,
            result_decision=decision,
            payload=report,
        )
    except TaskNotFoundError:
        return task_not_found_response(task_id)

    return {
        "status": "ok",
        "decision": decision,
        "evidence_id": evidence_id,
        "data": report,
        "error": None,
    }

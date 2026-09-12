"""Explicit M4.5 compatibility tools; never imported by the default server."""

from devharness.mcp.tools.context import (
    CONTEXT_BENCHMARK_EVALUATE_TOOL,
    CONTEXT_BENCHMARK_PLAN_TOOL,
    CONTEXT_GATE_EVALUATE_TOOL,
    CONTEXT_GUARANTEE_EVALUATE_TOOL,
    CONTEXT_INSPECT_TOOL,
    CONTEXT_LINT_TOOL,
    handle_context_benchmark_evaluate,
    handle_context_benchmark_plan,
    handle_context_gate_evaluate,
    handle_context_guarantee_evaluate,
    handle_context_inspect,
    handle_context_lint,
)
from devharness.mcp.tools.harness import (
    HARNESS_COMPILE_PREVIEW_TOOL,
    HARNESS_CONTRACT_VALIDATE_TOOL,
    HARNESS_PROFILE_TOOL,
    handle_harness_compile_preview,
    handle_harness_contract_validate,
    handle_harness_profile,
)
from devharness.mcp.tools.execution import (
    HARNESS_CANDIDATE_APPLY_TOOL,
    HARNESS_CANDIDATE_ROLLBACK_TOOL,
    RUNTIME_CONTROLS_CHECK_TOOL,
    SANDBOX_INSPECT_TOOL,
    TASK_PREPARE_TOOL,
    TASK_RECORD_RUN_TOOL,
    handle_harness_candidate_apply,
    handle_harness_candidate_rollback,
    handle_runtime_controls_check,
    handle_sandbox_inspect,
    handle_task_prepare,
    handle_task_record_run,
)


def register_legacy_tools(server):
    tools = {
        "context.lint": (CONTEXT_LINT_TOOL, handle_context_lint),
        "context.inspect": (CONTEXT_INSPECT_TOOL, handle_context_inspect),
        "context.gate_evaluate": (CONTEXT_GATE_EVALUATE_TOOL, handle_context_gate_evaluate),
        "context.benchmark_plan": (CONTEXT_BENCHMARK_PLAN_TOOL, handle_context_benchmark_plan),
        "context.benchmark_evaluate": (CONTEXT_BENCHMARK_EVALUATE_TOOL, handle_context_benchmark_evaluate),
        "context.guarantee_evaluate": (CONTEXT_GUARANTEE_EVALUATE_TOOL, handle_context_guarantee_evaluate),
        "harness.profile": (HARNESS_PROFILE_TOOL, handle_harness_profile),
        "harness.contract_validate": (HARNESS_CONTRACT_VALIDATE_TOOL, handle_harness_contract_validate),
        "harness.compile_preview": (HARNESS_COMPILE_PREVIEW_TOOL, handle_harness_compile_preview),
        "sandbox.inspect": (SANDBOX_INSPECT_TOOL, handle_sandbox_inspect),
        "runtime.controls_check": (RUNTIME_CONTROLS_CHECK_TOOL, handle_runtime_controls_check),
        "task.prepare": (TASK_PREPARE_TOOL, handle_task_prepare),
        "task.record_run": (TASK_RECORD_RUN_TOOL, handle_task_record_run),
        "harness.candidate_apply": (HARNESS_CANDIDATE_APPLY_TOOL, handle_harness_candidate_apply),
        "harness.candidate_rollback": (HARNESS_CANDIDATE_ROLLBACK_TOOL, handle_harness_candidate_rollback),
    }
    for schema, handler in tools.values():
        server.register_tool(schema, handler)

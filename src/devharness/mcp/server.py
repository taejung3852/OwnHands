from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

from devharness.mcp.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    error_response,
    success_response,
)
from devharness.mcp.tools.assurance import (
    ASSURANCE_GATE_EVALUATE_TOOL,
    GIT_DIFF_IMPACT_TOOL,
    GUARANTEE_EVALUATE_TOOL,
    TESTS_BASELINE_RECORD_TOOL,
    TESTS_COMPARE_RUNS_TOOL,
    TESTS_DESIGN_MEMO_TOOL,
    TESTS_GAP_DETECT_TOOL,
    handle_assurance_gate_evaluate,
    handle_git_diff_impact,
    handle_guarantee_evaluate,
    handle_tests_baseline_record,
    handle_tests_compare_runs,
    handle_tests_design_memo,
    handle_tests_gap_detect,
)
from devharness.mcp.tools.execution import (
    GIT_RESTORE_CAPTURE_TOOL,
    TASK_CREATE_TOOL,
    TASK_IMPORT_TOOL,
    handle_git_restore_capture,
    handle_task_create,
    handle_task_import,
)
from devharness.paths import DataPaths


class McpServer:
    def __init__(self, data_root: Path | str | None = None, *, legacy_tools: bool = False) -> None:
        self.data_paths = DataPaths.resolve(data_root) if data_root else None
        self.tools: dict[str, tuple[dict, Callable[[dict, DataPaths | None], dict]]] = {
            "git.restore_capture": (GIT_RESTORE_CAPTURE_TOOL, handle_git_restore_capture),
            "task.create": (TASK_CREATE_TOOL, handle_task_create),
            "task.import": (TASK_IMPORT_TOOL, handle_task_import),
            # assurance domain (7)
            "tests.baseline_record": (TESTS_BASELINE_RECORD_TOOL, handle_tests_baseline_record),
            "tests.compare_runs": (TESTS_COMPARE_RUNS_TOOL, handle_tests_compare_runs),
            "tests.gap_detect": (TESTS_GAP_DETECT_TOOL, handle_tests_gap_detect),
            "tests.design_memo": (TESTS_DESIGN_MEMO_TOOL, handle_tests_design_memo),
            "git.diff_impact": (GIT_DIFF_IMPACT_TOOL, handle_git_diff_impact),
            "assurance.gate_evaluate": (ASSURANCE_GATE_EVALUATE_TOOL, handle_assurance_gate_evaluate),
            "guarantee.evaluate": (GUARANTEE_EVALUATE_TOOL, handle_guarantee_evaluate),
        }

        if legacy_tools:
            from devharness.mcp.legacy import register_legacy_tools
            register_legacy_tools(self)

    def register_tool(
        self,
        schema: dict,
        handler: Callable[[dict, DataPaths | None], dict],
    ) -> None:
        self.tools[schema["name"]] = (schema, handler)

    def handle_request(self, request: dict[str, Any]) -> dict | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return error_response(None, INVALID_REQUEST, "invalid jsonrpc request")

        req_id = request.get("id")
        method = request.get("method")

        if method == "notifications/initialized":
            return None

        if method == "initialize":
            return success_response(
                req_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "ownhands-mcp-server",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "tools": {},
                    },
                },
            )

        if method == "tools/list":
            tools_list = [tool_def for tool_def, _ in self.tools.values()]
            return success_response(req_id, {"tools": tools_list})

        if method == "tools/call":
            params = request.get("params")
            if not isinstance(params, dict):
                return error_response(req_id, INVALID_PARAMS, "params must be an object")

            tool_name = params.get("name")
            tool_entry = None
            if isinstance(tool_name, str):
                tool_entry = self.tools.get(tool_name)
            if not tool_entry:
                return error_response(req_id, METHOD_NOT_FOUND, f"tool not found: {tool_name}")

            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                return error_response(req_id, INVALID_PARAMS, "arguments must be an object")

            _, handler = tool_entry
            try:
                result_payload = handler(arguments, self.data_paths)
                return success_response(
                    req_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result_payload, ensure_ascii=False),
                            }
                        ]
                    },
                )
            except Exception as error:
                return error_response(req_id, INTERNAL_ERROR, f"tool execution error: {error}")

        return error_response(req_id, METHOD_NOT_FOUND, f"method not found: {method}")

    def run_stdio(self, in_stream: TextIO = sys.stdin, out_stream: TextIO = sys.stdout) -> None:
        for line in in_stream:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as error:
                response = error_response(None, -32700, f"parse error: {error}")
                out_stream.write(json.dumps(response) + "\n")
                out_stream.flush()
                continue

            response = self.handle_request(request)
            if response is not None:
                out_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
                out_stream.flush()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="OwnHands verification MCP server")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--legacy-tools", action="store_true", help="enable the historical M4.5 25-tool contract")
    arguments = parser.parse_args()
    McpServer(arguments.data_root, legacy_tools=arguments.legacy_tools).run_stdio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

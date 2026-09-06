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
from devharness.mcp.tools.context import CONTEXT_LINT_TOOL, handle_context_lint
from devharness.paths import DataPaths


class McpServer:
    def __init__(self, data_root: Path | str | None = None) -> None:
        self.data_paths = DataPaths.resolve(data_root) if data_root else None
        self.tools: dict[str, tuple[dict, Callable[[dict, DataPaths | None], dict]]] = {
            "context.lint": (CONTEXT_LINT_TOOL, handle_context_lint),
        }

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
            if tool_name not in self.tools:
                return error_response(req_id, METHOD_NOT_FOUND, f"tool not found: {tool_name}")

            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                return error_response(req_id, INVALID_PARAMS, "arguments must be an object")

            _, handler = self.tools[tool_name]
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

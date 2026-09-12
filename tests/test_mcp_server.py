"""Historical M4.5 compatibility contract; active registry lives in test_control_boundary."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from devharness.mcp.server import McpServer


class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "AGENTS.md").write_text("# Project Agents\nFollow the rules.\n", encoding="utf-8")
        data_root = self.root / "data"
        self.server = McpServer(data_root=data_root, legacy_tools=True)
        from devharness.catalog import Catalog
        from devharness.identity import IdentityRegistry
        from devharness.paths import DataPaths
        with Catalog.open(DataPaths.resolve(data_root)) as catalog:
            registry = IdentityRegistry(catalog)
            registry.create_task_lifecycle(
                project_locator="file:///test-project",
                worktree_locator="file:///test-project/main",
                mode="managed",
                commit="0" * 40,
                branch="main",
                cwd=str(self.root),
                environment_ref="test-env",
                task_id="task-test-01",
            )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initialize(self) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        }
        response = self.server.handle_request(request)
        self.assertEqual(response["id"], 1)
        self.assertIn("serverInfo", response["result"])
        self.assertEqual(response["result"]["serverInfo"]["name"], "ownhands-mcp-server")

    def test_tools_list(self) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        response = self.server.handle_request(request)
        self.assertEqual(response["id"], 2)
        tool_names = [t["name"] for t in response["result"]["tools"]]
        self.assertIn("context.lint", tool_names)

    def test_tools_call_context_lint_pass_no_task_id(self) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "context.lint",
                "arguments": {
                    "root": str(self.root),
                    "sources": [
                        {
                            "source_id": "src:agents",
                            "path": "AGENTS.md",
                            "source_type": "agents_instruction",
                        }
                    ],
                },
            },
        }
        response = self.server.handle_request(request)
        self.assertEqual(response["id"], 3)
        content = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(content["status"], "ok")
        self.assertEqual(content["decision"], "pass")
        self.assertIsNone(content["evidence_id"])
        self.assertEqual(content["data"]["findings"], [])

    def test_tools_call_context_lint_soft_block_with_task_id(self) -> None:
        # Universal wording like "always" triggers broad_universal_wording
        (self.root / "AGENTS.md").write_text("Always follow every rule on all tasks.\n", encoding="utf-8")
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "context.lint",
                "arguments": {
                    "root": str(self.root),
                    "sources": [
                        {
                            "source_id": "src:agents",
                            "path": "AGENTS.md",
                            "source_type": "agents_instruction",
                        }
                    ],
                    "task_id": "task-test-01",
                },
            },
        }
        response = self.server.handle_request(request)
        self.assertEqual(response["id"], 4)
        content = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(content["status"], "ok")
        self.assertEqual(content["decision"], "soft_block")
        self.assertTrue(len(content["data"]["findings"]) > 0)
        self.assertIsNotNone(content["evidence_id"])
        self.assertTrue(content["evidence_id"].startswith("sha256:"))

    def test_tools_call_unknown_tool(self) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "non_existent.tool",
                "arguments": {},
            },
        }
        response = self.server.handle_request(request)
        self.assertEqual(response["id"], 5)
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)

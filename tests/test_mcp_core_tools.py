from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from devharness.mcp.server import McpServer


class McpCoreToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "pyproject.toml").write_text("[project]\nname = \"test\"\n", encoding="utf-8")
        data_root = self.root / "data"
        self.server = McpServer(data_root=data_root)
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
                task_id="task-compare-01",
            )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_tools_list_contains_all_four_tools(self) -> None:
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        resp = self.server.handle_request(req)
        tool_names = [t["name"] for t in resp["result"]["tools"]]
        self.assertIn("context.lint", tool_names)
        self.assertIn("harness.profile", tool_names)
        self.assertIn("tests.compare_runs", tool_names)
        self.assertIn("assurance.gate_evaluate", tool_names)

    def test_harness_profile_returns_envelope(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "harness.profile",
                "arguments": {
                    "root": str(self.root),
                },
            },
        }
        resp = self.server.handle_request(req)
        envelope = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(envelope["status"], "ok")
        self.assertIsNone(envelope["decision"])
        self.assertIn("pyproject.toml", envelope["data"]["structure"])

    def test_tests_compare_runs_pass_and_regression(self) -> None:
        # Base receipt
        receipt_base = {
            "test_id": "test_1",
            "subject_ref": "src.main",
            "criterion_id": "crit_1",
            "classification": "regression",
            "validation_command": "pytest",
            "command_fingerprint": "sha256:" + "1" * 64,
            "selection_scope": "tests",
            "environment_fingerprint": "sha256:" + "2" * 64,
            "contract_fingerprint": "sha256:" + "3" * 64,
            "start_patch_hash": "sha256:" + "4" * 64,
            "target_patch_hash": "sha256:" + "5" * 64,
            "code_refs": ["src/main.py"],
            "result": "pass",
            "basis": "observed",
            "evidence_refs": ["ev_1"],
            "conflict_refs": [],
        }

        # Case 1: Pass
        before_pass = {"receipts": [dict(receipt_base)]}
        after_pass = {"receipts": [dict(receipt_base)]}
        req_pass = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "tests.compare_runs",
                "arguments": {"before": before_pass, "after": after_pass, "task_id": "task-compare-01"},
            },
        }
        resp_pass = self.server.handle_request(req_pass)
        envelope_pass = json.loads(resp_pass["result"]["content"][0]["text"])
        self.assertEqual(envelope_pass["status"], "ok")
        self.assertEqual(envelope_pass["decision"], "pass")
        self.assertIsNotNone(envelope_pass["evidence_id"])

        # Case 2: Regression (after fails)
        receipt_fail = dict(receipt_base, result="fail")
        after_fail = {"receipts": [receipt_fail]}
        req_fail = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "tests.compare_runs",
                "arguments": {"before": before_pass, "after": after_fail},
            },
        }
        resp_fail = self.server.handle_request(req_fail)
        envelope_fail = json.loads(resp_fail["result"]["content"][0]["text"])
        self.assertEqual(envelope_fail["status"], "ok")
        self.assertEqual(envelope_fail["decision"], "hard_block")

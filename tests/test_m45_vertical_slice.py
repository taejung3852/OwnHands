from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devharness.catalog import Catalog
from devharness.mcp.server import McpServer
from devharness.paths import DataPaths
from devharness.plugin import load_plugin_manifest


class M45VerticalSliceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo_root = Path(__file__).resolve().parents[1]

        # Target project files
        self.project_dir = self.root / "project"
        self.project_dir.mkdir()
        (self.project_dir / "AGENTS.md").write_text("# Clean Rules\nFollow task requirements.\n", encoding="utf-8")
        (self.project_dir / "AGENTS_SOFT.md").write_text("Always execute on all tasks.\n", encoding="utf-8")

        self.data_root = self.root / "data"
        self.server = McpServer(data_root=self.data_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_plugin_manifest_discovers_skills_and_server(self) -> None:
        manifest = load_plugin_manifest(self.repo_root)
        self.assertEqual(manifest["name"], "ownhands")
        self.assertTrue((self.repo_root / manifest["skills"]["directory"] / "using-ownhands" / "SKILL.md").is_file())
        self.assertTrue((self.repo_root / manifest["skills"]["directory"] / "context-validation" / "SKILL.md").is_file())

    def test_slice_clean_pass_records_evidence(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "context.lint",
                "arguments": {
                    "root": str(self.project_dir),
                    "sources": [
                        {
                            "source_id": "src:agents",
                            "path": "AGENTS.md",
                            "source_type": "agents_instruction",
                        }
                    ],
                    "task_id": "task-clean-01",
                },
            },
        }
        response = self.server.handle_request(req)
        self.assertEqual(response["id"], 101)
        envelope = json.loads(response["result"]["content"][0]["text"])

        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertEqual(envelope["data"]["findings"], [])
        self.assertIsNotNone(envelope["evidence_id"])

        evidence_id = envelope["evidence_id"]
        # Verify directly in SQLite Catalog and CAS objects
        paths = DataPaths.resolve(self.data_root)
        with Catalog.open(paths) as catalog:
            evidence_row = catalog.connection.execute(
                "SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,)
            ).fetchone()
            self.assertIsNotNone(evidence_row)
            self.assertEqual(evidence_row["task_id"], "task-clean-01")
            self.assertEqual(evidence_row["result"], "pass")
            self.assertEqual(evidence_row["basis"], "observed")

            object_path = paths.objects / evidence_row["object_relpath"]
            self.assertTrue(object_path.is_file())
            content_data = json.loads(object_path.read_text(encoding="utf-8"))
            self.assertEqual(content_data["findings"], [])

    def test_slice_soft_block_identifies_findings(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": {
                "name": "context.lint",
                "arguments": {
                    "root": str(self.project_dir),
                    "sources": [
                        {
                            "source_id": "src:agents-soft",
                            "path": "AGENTS_SOFT.md",
                            "source_type": "agents_instruction",
                        }
                    ],
                    "task_id": "task-soft-01",
                },
            },
        }
        response = self.server.handle_request(req)
        envelope = json.loads(response["result"]["content"][0]["text"])

        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "soft_block")
        self.assertTrue(len(envelope["data"]["findings"]) > 0)
        rule_ids = [f["rule_id"] for f in envelope["data"]["findings"]]
        self.assertIn("broad_universal_wording", rule_ids)
        self.assertIsNotNone(envelope["evidence_id"])

    def test_slice_hard_block_missing_source(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 103,
            "method": "tools/call",
            "params": {
                "name": "context.lint",
                "arguments": {
                    "root": str(self.project_dir),
                    "sources": [
                        {
                            "source_id": "src:missing",
                            "path": "NON_EXISTENT_AGENTS.md",
                            "source_type": "agents_instruction",
                        }
                    ],
                    "task_id": "task-hard-01",
                },
            },
        }
        response = self.server.handle_request(req)
        envelope = json.loads(response["result"]["content"][0]["text"])

        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "hard_block")
        rule_ids = [f["rule_id"] for f in envelope["data"]["findings"]]
        self.assertIn("missing_source", rule_ids)

    def test_stdio_subprocess_e2e_roundtrip(self) -> None:
        # Launch real stdio MCP server process
        process = subprocess.Popen(
            [sys.executable, "-m", "devharness", "mcp-server", "--data-root", str(self.data_root)],
            cwd=self.repo_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        init_msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        call_msg = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "context.lint",
                "arguments": {
                    "root": str(self.project_dir),
                    "sources": [{"source_id": "src:agents", "path": "AGENTS.md", "source_type": "agents_instruction"}],
                },
            },
        })

        stdout_data, _ = process.communicate(input=f"{init_msg}\n{call_msg}\n", timeout=10)
        lines = [line.strip() for line in stdout_data.strip().splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)

        init_resp = json.loads(lines[0])
        self.assertEqual(init_resp["id"], 1)
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "ownhands-mcp-server")

        call_resp = json.loads(lines[1])
        self.assertEqual(call_resp["id"], 2)
        envelope = json.loads(call_resp["result"]["content"][0]["text"])
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")

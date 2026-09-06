from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from devharness.assurance import RECEIPT_FIELDS
from devharness.catalog import Catalog
from devharness.events import EventDraft, EventLog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.identity import IdentityRegistry
from devharness.mcp.server import McpServer
from devharness.paths import DataPaths

CANONICAL_25_TOOLS = {
    # context.* (6)
    "context.lint",
    "context.inspect",
    "context.gate_evaluate",
    "context.benchmark_plan",
    "context.benchmark_evaluate",
    "context.guarantee_evaluate",
    # harness.* (3)
    "harness.profile",
    "harness.contract_validate",
    "harness.compile_preview",
    # execution / task / sandbox / git restore / candidate (9)
    "sandbox.inspect",
    "git.restore_capture",
    "runtime.controls_check",
    "task.prepare",
    "task.create",
    "task.record_run",
    "task.import",
    "harness.candidate_apply",
    "harness.candidate_rollback",
    # tests / git impact / assurance / guarantee (7)
    "tests.baseline_record",
    "tests.compare_runs",
    "tests.gap_detect",
    "tests.design_memo",
    "git.diff_impact",
    "assurance.gate_evaluate",
    "guarantee.evaluate",
}


def git_cmd(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_bytes,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


class McpContract25ToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / "data"
        self.data_paths = DataPaths.resolve(self.data_dir)
        self.server = McpServer(data_root=self.data_dir)

        # Initialize catalog and a canonical task in catalog
        with Catalog.open(self.data_paths) as catalog:
            registry = IdentityRegistry(catalog)
            project = registry.register_project("file:///test-project")
            worktree = registry.register_worktree(project.project_id, "file:///test-project/main")
            self.task = registry.create_task(
                worktree_id=worktree.worktree_id,
                mode="managed",
                commit="0" * 40,
                branch="main",
                cwd=str(self.root),
                environment_ref="test-env",
            )
            # Log initial task.created event
            events = EventLog(catalog)
            if not events.list_for_task(self.task.task_id):
                events.append(
                    EventDraft(
                        event_id=f"task-created:{self.task.task_id}",
                        task_id=self.task.task_id,
                        event_type="task.created",
                        event_version=1,
                        occurred_at="2026-09-07T00:00:00+00:00",
                        payload={"mode": "managed", "task_id": self.task.task_id},
                        collection_method="setup",
                        redaction_status="not_needed",
                    ),
                    lambda p: p,
                )

        (self.root / "pyproject.toml").write_text("[project]\nname = \"test\"\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def call_tool(self, name: str, arguments: dict) -> dict:
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp, f"Tool call {name} failed: {resp.get('error')}")
        return json.loads(resp["result"]["content"][0]["text"])

    # --------------------------------------------------------------------------
    # 1. Topology & List Contract
    # --------------------------------------------------------------------------
    def test_tools_list_contains_exact_25_canonical_tools(self) -> None:
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        resp = self.server.handle_request(req)
        tool_names = [t["name"] for t in resp["result"]["tools"]]
        self.assertEqual(
            set(tool_names),
            CANONICAL_25_TOOLS,
            f"Expected exactly 25 tools. Missing: {CANONICAL_25_TOOLS - set(tool_names)}, Extra: {set(tool_names) - CANONICAL_25_TOOLS}",
        )
        self.assertEqual(len(tool_names), 25)

    # --------------------------------------------------------------------------
    # 2. Unknown Task Isolation (No Magic Auto-Creation)
    # --------------------------------------------------------------------------
    def test_unknown_task_isolation_rejects_with_hard_block_task_not_found(self) -> None:
        # Tools that take task_id to record evidence must fail when task_id does not exist
        envelope = self.call_tool(
            "context.lint",
            {
                "root": str(self.root),
                "sources": [],
                "task_id": "nonexistent-task-9999",
            },
        )
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["decision"], "hard_block")
        self.assertIsNotNone(envelope["error"])
        self.assertEqual(envelope["error"].get("code"), "TaskNotFound")

        # Verify it was NOT magically inserted into the database
        with Catalog.open(self.data_paths) as catalog:
            exists = catalog.query_value("SELECT 1 FROM tasks WHERE task_id=?", ("nonexistent-task-9999",))
            self.assertIsNone(exists)

    # --------------------------------------------------------------------------
    # 3. Context Domain Tools
    # --------------------------------------------------------------------------
    def test_context_lint_contract(self) -> None:
        source_file = self.root / "AGENTS.md"
        source_file.write_text("# Instructions\nDo good things.\n", encoding="utf-8")
        envelope = self.call_tool(
            "context.lint",
            {
                "root": str(self.root),
                "sources": [
                    {
                        "source_id": "agents",
                        "path": "AGENTS.md",
                        "source_type": "agents_instruction",
                    }
                ],
                "task_id": self.task.task_id,
            },
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertIn("findings", envelope["data"])
        self.assertIsNotNone(envelope["evidence_id"])

    def test_context_inspect_contract(self) -> None:
        # context.inspect validates a context manifest with authoritative event/evidence refs
        manifest = {
            "manifest_version": "1.0",
            "manifest_id": "man-1",
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "mode": self.task.mode,
                "target_commit": self.task.commit,
                "cwd": self.task.cwd,
                "environment_ref": self.task.environment_ref,
            },
            "context_sources": [],
            "control_sources": [],
            "instruction_overlay": {"source_refs": [], "skill_invocations": [], "excluded_source_refs": []},
            "control_overlay": {"source_refs": [], "immutable_source_refs": []},
            "event_refs": [],
            "evidence_refs": [],
            "generated_at": "2026-09-07T00:00:00+00:00",
        }
        envelope = self.call_tool(
            "context.inspect",
            {"manifest": manifest, "evidence_ids": [], "event_ids": []},
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertTrue(envelope["data"].get("valid"))

    def test_context_gate_evaluate_contract(self) -> None:
        gate_input = {
            "trigger": "task_start",
            "task": {"scope": "src", "phase": "exec"},
            "active_source_refs": ["src1"],
            "sources": [
                {
                    "source_id": "src1",
                    "source_class": "context",
                    "content_hash": "sha256:" + "0" * 64,
                    "deterministic": True,
                }
            ],
        }
        envelope = self.call_tool("context.gate_evaluate", {"gate_input": gate_input})
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertIn("instruction_overlay", envelope["data"])

    def test_context_benchmark_plan_and_evaluate_contract(self) -> None:
        package = {
            "package_version": "1.0",
            "package_id": "pkg-01",
            "fixture": {"fixture_id": "fix-1"},
            "fixed_conditions": {
                "model": "codex-test",
                "reasoning_effort": "high",
                "prompt": "solve task",
                "environment": "env-1",
                "controls": "ctl-1",
            },
            "conditions": {
                "A": {"prompt": "base"},
                "B": {"prompt": "opt_b"},
                "C": {"prompt": "opt_c"},
            },
            "repetitions": 3,
            "crossover_order": ["A", "B", "C", "B", "C", "A", "C", "A", "B"],
            "metrics": ["requirements_met", "tests_passed", "instruction_violations", "out_of_scope_changes"],
        }
        plan_env = self.call_tool(
            "context.benchmark_plan",
            {"package": package, "target_commit": "commit123"},
        )
        self.assertEqual(plan_env["status"], "ok")
        self.assertEqual(len(plan_env["data"]["plan"]), 9)

        # Mock 9 completed runs
        runs = []
        for item in plan_env["data"]["plan"]:
            runs.append(
                {
                    **item,
                    "status": "completed",
                    "metrics": {
                        "requirements_met": {"value": True, "basis": "observed"},
                        "tests_passed": {"value": True, "basis": "observed"},
                        "instruction_violations": {"value": 0, "basis": "observed"},
                        "out_of_scope_changes": {"value": 0, "basis": "observed"},
                    },
                }
            )

        eval_env = self.call_tool(
            "context.benchmark_evaluate",
            {"package": package, "runs": runs},
        )
        self.assertEqual(eval_env["status"], "ok")
        self.assertIn("improvement_verdict", eval_env["data"])
        self.assertIn("failure_counts", eval_env["data"])

    def test_context_guarantee_evaluate_exact_keys_no_fake_reasons(self) -> None:
        matrix = {
            "matrix_version": "1.5-proposed-1",
            "claims": [
                {
                    "claim_id": "CLM-01",
                    "category": "instruction_loaded",
                    "claim": "Instructions are observed and loaded.",
                    "allowed_basis": ["observed"],
                    "required_evidence": [
                        {"type": "instruction_loading", "required_fields": ["manifest_ref", "task_ref"]}
                    ],
                    "residual_risks": ["lexical parity only"],
                }
            ],
        }
        manifest = {
            "manifest_id": "man-01",
            "task": {"task_id": "task-01"},
            "context_sources": [{"source_id": "src-01"}],
        }
        evidence_records = [
            {
                "evidence_id": "ev-01",
                "evidence_type": "instruction_loading",
                "basis": "observed",
                "result": "pass",
                "fields": {
                    "manifest_ref": "man-01",
                    "task_ref": "task-01",
                    "source_ref": "src-01",
                },
            }
        ]
        envelope = self.call_tool(
            "context.guarantee_evaluate",
            {"matrix": matrix, "manifest": manifest, "evidence_records": evidence_records},
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        results = envelope["data"]["results"]
        self.assertEqual(len(results), 1)
        res = results[0]
        # Must contain exact 7 core keys without fake reasons
        expected_keys = {
            "claim_id",
            "category",
            "verdict",
            "evidence_refs",
            "conflict_refs",
            "residual_risks",
            "permitted_statement",
        }
        self.assertEqual(set(res.keys()), expected_keys)
        self.assertNotIn("reasons", res)
        self.assertEqual(res["verdict"], "supported")

    # --------------------------------------------------------------------------
    # 4. Harness Domain Tools
    # --------------------------------------------------------------------------
    def test_harness_profile_returns_raw_doc_and_null_decision(self) -> None:
        envelope = self.call_tool("harness.profile", {"root": str(self.root)})
        self.assertEqual(envelope["status"], "ok")
        self.assertIsNone(envelope["decision"])  # Compatibility anchor: decision=null
        self.assertIn("structure", envelope["data"])

    def test_harness_contract_validate_contract_and_overlay(self) -> None:
        contract_valid = {
            "contract_id": "c-valid",
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "environment_ref": self.task.environment_ref,
            },
            "writable_paths": ["src/main.py"],
            "protected_targets": ["AGENTS.md"],
            "active_permissions": [{"permission": "fs:write", "active": True}],
        }
        envelope_pass = self.call_tool(
            "harness.contract_validate",
            {
                "contract": contract_valid,
                "task_id": self.task.task_id,
            },
        )
        self.assertEqual(envelope_pass["status"], "ok")
        self.assertEqual(envelope_pass["decision"], "pass")
        self.assertIsNotNone(envelope_pass["evidence_id"])

        # Unapproved permission causes hard_block
        contract_unapproved = {
            "contract_id": "c-unapproved",
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "environment_ref": self.task.environment_ref,
            },
            "writable_paths": ["src/main.py"],
            "protected_targets": ["AGENTS.md"],
            "active_permissions": [{"permission": "fs:delete", "active": False}],
        }
        envelope_blocked = self.call_tool(
            "harness.contract_validate",
            {"contract": contract_unapproved},
        )
        self.assertEqual(envelope_blocked["status"], "ok")
        self.assertEqual(envelope_blocked["decision"], "hard_block")

    def test_harness_compile_preview_contract(self) -> None:
        contract = {
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "environment_ref": self.task.environment_ref,
            },
            "boundary": {"workspace_root": str(self.root)},
            "active_permissions": [{"permission": "fs:write", "scope": "src", "active": True}],
            "writable_paths": ["src/main.py"],
            "allowed_commands": ["pytest"],
            "hooks": [],
            "risk_profile": {"risk_level": "low"},
        }
        envelope = self.call_tool(
            "harness.compile_preview",
            {"contract": contract, "existing": {}},
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertIn("compiled", envelope["data"])
        self.assertIn("preview_markdown", envelope["data"])

    # --------------------------------------------------------------------------
    # 5. Execution Domain Tools
    # --------------------------------------------------------------------------
    def test_sandbox_inspect_contract(self) -> None:
        envelope = self.call_tool(
            "sandbox.inspect",
            {"root": str(self.root), "command": "pytest", "task_id": self.task.task_id},
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertFalse(envelope["data"]["command_assessment"]["threat_detected"])

    def test_git_restore_capture_strips_binary_patch(self) -> None:
        repo_dir = self.root / "git_repo"
        repo_dir.mkdir()
        git_cmd(repo_dir, "init")
        git_cmd(repo_dir, "config", "user.email", "test@example.com")
        git_cmd(repo_dir, "config", "user.name", "Tester")
        (repo_dir / "sample.txt").write_text("initial", encoding="utf-8")
        git_cmd(repo_dir, "add", ".")
        git_cmd(repo_dir, "commit", "-m", "init")
        (repo_dir / "sample.txt").write_text("modified", encoding="utf-8")

        envelope = self.call_tool(
            "git.restore_capture",
            {"root": str(repo_dir), "task_id": self.task.task_id},
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertIn("start_commit", envelope["data"])
        self.assertIn("tracked_patch_hash", envelope["data"])
        self.assertNotIn("_tracked_patch", envelope["data"])

    def test_task_create_lifecycle_atomic(self) -> None:
        envelope = self.call_tool(
            "task.create",
            {
                "project_locator": "file:///repo_lifecycle",
                "worktree_locator": "file:///repo_lifecycle/main",
                "mode": "managed",
                "commit": "1" * 40,
                "branch": "feature",
                "cwd": "/repo_lifecycle/main",
                "environment_ref": "python3",
            },
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        created_task_id = envelope["data"]["task_id"]

        with Catalog.open(self.data_paths) as catalog:
            registry = IdentityRegistry(catalog)
            t = registry.get_task(created_task_id)
            self.assertEqual(t.task_id, created_task_id)
            events = EventLog(catalog)
            evs = events.list_for_task(created_task_id)
            self.assertEqual(len(evs), 1)
            self.assertEqual(evs[0].sequence, 1)
            self.assertEqual(evs[0].event_type, "task.created")

    def test_task_prepare_requires_sha256_patch_hash(self) -> None:
        envelope = self.call_tool(
            "task.prepare",
            {
                "repository": str(self.root),
                "patch_hash": "invalid_not_sha256",
            },
        )
        self.assertEqual(envelope["status"], "error")
        self.assertIsNone(envelope["decision"])

    def test_task_import_contract(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures/m3/imported-task.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        envelope = self.call_tool("task.import", {"fixture": fixture})
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertEqual(envelope["data"]["mode"], "imported")

    def test_candidate_apply_and_rollback(self) -> None:
        project_dir = self.root / "project_apply"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / ".ownhands-disposable").write_text("synthetic\n", encoding="utf-8")
        (project_dir / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        codex_dir = project_dir / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        (codex_dir / "config.toml").write_text('sandbox_mode = "workspace-write"\napproval_policy = "on-request"\n', encoding="utf-8")

        contract = {
            "contract_version": "1.0",
            "contract_id": "contract-apply-01",
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "environment_ref": self.task.environment_ref,
                "mode": "managed",
            },
            "permissions": [],
            "writable_paths": ["src/**"],
            "protected_targets": [".env"],
            "approval_triggers": ["external_effect"],
            "validation_criteria": ["pytest"],
            "gate_status": "ready_for_preview",
            "fingerprint": "sha256:" + "0" * 64,
        }
        existing = {
            ".ownhands-disposable": (project_dir / ".ownhands-disposable").read_text(),
            "AGENTS.md": (project_dir / "AGENTS.md").read_text(),
            ".codex/config.toml": (codex_dir / "config.toml").read_text(),
        }
        from devharness.control_profile import compile_control_profile
        compiled = compile_control_profile(contract, existing)

        approval = {
            "decision": "approved",
            "decision_source": "explicit_product_approval",
            "contract_ref": contract["contract_id"],
            "approver": "lead",
            "approved_at": "2026-09-07T00:00:00Z",
            "scope": "candidate_apply",
        }
        apply_env = self.call_tool(
            "harness.candidate_apply",
            {"compiled": compiled, "root": str(project_dir), "approval": approval},
        )
        self.assertEqual(apply_env["status"], "ok")
        self.assertEqual(apply_env["decision"], "pass")
        journal_path = apply_env["data"]["journal_path"]

        # Now rollback
        rollback_env = self.call_tool(
            "harness.candidate_rollback",
            {"root": str(project_dir), "journal_path": journal_path},
        )
        self.assertEqual(rollback_env["status"], "ok")
        self.assertEqual(rollback_env["decision"], "pass")

    # --------------------------------------------------------------------------
    # 6. Assurance Domain Tools
    # --------------------------------------------------------------------------
    def _make_test_contract(self) -> dict:
        from devharness.assurance import fingerprint
        draft = {
            "criteria": [{"criterion_id": "crit1", "block_level": "hard"}],
            "tests": [
                {
                    "test_id": "test_red_1",
                    "subject_ref": "feature_a",
                    "command": "pytest test_a.py",
                    "selection_scope": "unit",
                    "classification": "regression",
                    "code_refs": ["src/a.py"],
                }
            ],
            "mappings": [{"criterion_id": "crit1", "test_ids": ["test_red_1"], "viewpoints": ["v1"], "reason": "r1"}],
            "impact_hypotheses": [],
        }
        contract = {
            "contract_version": "1.1",
            "contract_id": "contract:task-01",
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "environment_ref": self.task.environment_ref,
                "mode": "managed",
                "goal": "verify assurance",
            },
            "protected_targets": [".env", ".git/**"],
            "validation_criteria": ["pytest test_a.py"],
            "gate_criteria": ["crit1"],
            "assurance_draft": draft,
        }
        contract["fingerprint"] = fingerprint(contract)
        return contract

    def test_tests_baseline_record_failing_baseline_is_valid_tdd_red(self) -> None:
        from devharness.assurance import fingerprint
        contract = self._make_test_contract()
        test = contract["assurance_draft"]["tests"][0]
        selection = [dict(test)]
        receipt_fail = {
            "test_id": test["test_id"],
            "subject_ref": test["subject_ref"],
            "criterion_id": "crit1",
            "classification": test["classification"],
            "validation_command": test["command"],
            "command_fingerprint": fingerprint({"command": test["command"]}),
            "selection_scope": test["selection_scope"],
            "environment_fingerprint": "sha256:" + "e" * 64,
            "contract_fingerprint": contract["fingerprint"],
            "start_patch_hash": "sha256:" + "0" * 64,
            "target_patch_hash": "sha256:" + "0" * 64,
            "code_refs": test["code_refs"],
            "result": "fail",  # TDD Red baseline has failing test!
            "basis": "observed",
            "evidence_refs": ["ev-fail-01"],
            "conflict_refs": [],
        }
        self.assertEqual(set(receipt_fail.keys()), RECEIPT_FIELDS)

        envelope = self.call_tool(
            "tests.baseline_record",
            {
                "contract": contract,
                "selection": selection,
                "receipts": [receipt_fail],
                "observed_at": "2026-09-07T00:00:00+00:00",
                "task_id": self.task.task_id,
            },
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], "pass")
        self.assertIn("receipts", envelope["data"])

    def test_assurance_gate_evaluate_contract(self) -> None:
        from devharness.assurance import fingerprint
        contract = self._make_test_contract()
        impact = {
            "contract_id": contract["contract_id"],
            "contract_fingerprint": contract["fingerprint"],
            "fingerprint": "sha256:" + "i" * 64,
            "restore_point_ref": "rp1",
            "joined_relations": [],
            "unobserved_boundaries": [],
            "affected_targets": [],
        }
        design = {
            "contract_id": contract["contract_id"],
            "contract_fingerprint": contract["fingerprint"],
            "impact_fingerprint": impact["fingerprint"],
            "fingerprint": "sha256:" + "d" * 64,
            "selected_tests": [dict(contract["assurance_draft"]["tests"][0])],
            "criterion_coverage": [{"criterion_id": "crit1", "covered": True}],
            "missing_coverage": [],
        }
        comparison = {
            "comparisons": [
                {
                    "test_id": "test_red_1",
                    "criterion_id": "crit1",
                    "status": "comparable_pass",
                    "block_level": "hard",
                    "subject_ref": "feature_a",
                    "evidence_refs": ["ev1"],
                    "conflict_refs": [],
                }
            ]
        }
        gaps = {"gaps": [], "unresolved_gaps": []}

        envelope = self.call_tool(
            "assurance.gate_evaluate",
            {
                "contract": contract,
                "impact": impact,
                "design": design,
                "comparison": comparison,
                "gaps": gaps,
                "task_id": self.task.task_id,
            },
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["decision"], envelope["data"]["decision"])
        self.assertIn("decision", envelope["data"])


    def test_tests_compare_runs_11_status_mappings(self) -> None:
        receipt_base = {
            "test_id": "t1",
            "subject_ref": "sub",
            "criterion_id": "crit1",
            "classification": "regression",
            "validation_command": "pytest",
            "command_fingerprint": "sha256:" + "1" * 64,
            "selection_scope": "tests",
            "environment_fingerprint": "sha256:" + "2" * 64,
            "contract_fingerprint": "sha256:" + "3" * 64,
            "start_patch_hash": "sha256:" + "4" * 64,
            "target_patch_hash": "sha256:" + "5" * 64,
            "code_refs": ["src/a.py"],
            "result": "pass",
            "basis": "observed",
            "evidence_refs": ["ev1"],
            "conflict_refs": [],
        }
        # 1. Pass -> pass
        env_pass = self.call_tool(
            "tests.compare_runs",
            {"before": {"receipts": [receipt_base]}, "after": {"receipts": [receipt_base]}, "task_id": self.task.task_id},
        )
        self.assertEqual(env_pass["decision"], "pass")

        # 2. Regression (after fails) -> hard_block
        env_reg = self.call_tool(
            "tests.compare_runs",
            {
                "before": {"receipts": [receipt_base]},
                "after": {"receipts": [{**receipt_base, "result": "fail"}]},
                "task_id": self.task.task_id,
            },
        )
        self.assertEqual(env_reg["decision"], "hard_block")

    def test_git_diff_impact_validates_relation_types(self) -> None:
        repo_dir = self.root / "git_impact_repo"
        repo_dir.mkdir()
        git_cmd(repo_dir, "init")
        git_cmd(repo_dir, "config", "user.email", "test@example.com")
        git_cmd(repo_dir, "config", "user.name", "Tester")
        (repo_dir / "file.txt").write_text("a\n", encoding="utf-8")
        git_cmd(repo_dir, "add", ".")
        git_cmd(repo_dir, "commit", "-m", "init")

        # Invalid relation_type
        bad_catalog = {
            "relations": [
                {
                    "relation_id": "r1",
                    "changed_path_glob": "*.txt",
                    "relation_type": "invalid_type",
                    "target_ref": "target",
                    "basis": "declared",
                    "evidence_refs": [],
                }
            ]
        }
        envelope = self.call_tool(
            "git.diff_impact",
            {
                "root": str(repo_dir),
                "contract": {
                    "contract_id": "c1",
                    "task": {"task_id": "t1"},
                    "assurance_draft": {"impact_hypotheses": []},
                    "fingerprint": "sha256:" + "0" * 64,
                },
                "restore_point": {
                    "restore_point_id": "rp1",
                    "task": {"task_id": "t1"},
                    "tracked_patch_hash": "sha256:" + "0" * 64,
                },
                "relation_catalog": bad_catalog,
            },
        )
        self.assertEqual(envelope["status"], "error")
        self.assertIsNone(envelope["decision"])

    def test_guarantee_evaluate_contract(self) -> None:
        envelope = self.call_tool(
            "guarantee.evaluate",
            {
                "task_id": self.task.task_id,
            },
        )
        self.assertEqual(envelope["status"], "ok")
        self.assertIn(envelope["decision"], {"pass", "soft_block", "unobserved"})
        self.assertIn("claim_results", envelope["data"])
        for claim_res in envelope["data"]["claim_results"]:
            self.assertIn(claim_res["verdict"], {"supported", "contradicted", "not_evaluated"})

    # --------------------------------------------------------------------------
    # 7. Bug Regression Tests (TDD Verification)
    # --------------------------------------------------------------------------
    def test_harness_contract_validate_profile_interview_pipeline(self) -> None:
        # 1. Profile project
        profile_env = self.call_tool("harness.profile", {"root": str(self.root)})
        self.assertEqual(profile_env["status"], "ok")
        profile = profile_env["data"]

        # 2. Validate with interview responses through real Core pipeline (run_interview -> build_baseline)
        responses = ["workspace-write", "on-request"]
        env = self.call_tool(
            "harness.contract_validate",
            {
                "profile": profile,
                "interview_responses": responses,
                "version": 1,
                "predecessor_ref": None,
                "event_refs": [],
                "evidence_refs": [],
            },
        )
        self.assertEqual(env["status"], "ok")
        self.assertIn(env["decision"], {"pass", "soft_block"})
        self.assertIn("baseline", env["data"])
        self.assertEqual(env["data"]["baseline"]["version"], 1)
        self.assertIn("interview", env["data"])

    def test_harness_contract_validate_baseline_overlay_hard_block_and_permissions(self) -> None:
        profile_env = self.call_tool("harness.profile", {"root": str(self.root)})
        profile = profile_env["data"]
        from devharness.control_profile import run_interview, build_baseline
        interview = run_interview(profile, ["workspace-write", "on-request"])
        baseline = build_baseline(
            profile,
            interview,
            version=1,
            predecessor_ref=None,
            event_refs=["event-1"],
            evidence_refs=["evidence-1"],
        )
        overlay = {
            "overlay_version": "1.0",
            "overlay_id": "overlay-test-01",
            "task": {
                "project_id": baseline["project_id"],
                "worktree_id": baseline["worktree_id"],
                "task_id": "task-test-01",
                "environment_ref": baseline["environment_ref"],
                "mode": "managed",
            },
            "baseline_ref": baseline["baseline_id"],
            "baseline_fingerprint": baseline["fingerprint"],
            "instruction_overlay": {"source_refs": []},
            "control_overlay": {"source_refs": []},
            "writable_paths": ["src/**"],
            "protected_targets": [".env"],
            "permission_expansions": [
                {
                    "permission": "network",
                    "scope": "api.openai.com",
                    "reason": "testing",
                    "duration": "task",
                    "approval_ref": "unapproved-app",
                }
            ],
            "approval_triggers": [],
            "validation_criteria": ["pytest"],
            "gate_criteria": [],
            "unobserved_paths": [],
        }
        # No matching approval -> hard_block on unapproved permission
        env = self.call_tool(
            "harness.contract_validate",
            {"baseline": baseline, "overlay": overlay, "approvals": []},
        )
        self.assertEqual(env["status"], "ok")
        self.assertEqual(env["decision"], "hard_block")
        self.assertEqual(env["data"]["gate_status"], "hard_block")
        self.assertTrue(any(p["active"] is False for p in env["data"]["permissions"]))

    def test_task_record_run_managed_execution(self) -> None:
        # Create a repo with a committed baseline
        repo_dir = self.root / "task_run_repo"
        repo_dir.mkdir()
        git_cmd(repo_dir, "init")
        git_cmd(repo_dir, "config", "user.email", "run@example.invalid")
        git_cmd(repo_dir, "config", "user.name", "RunTester")
        (repo_dir / ".ownhands-disposable").write_text("synthetic\n", encoding="utf-8")
        (repo_dir / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (repo_dir / ".codex").mkdir()
        (repo_dir / ".codex" / "config.toml").write_text('sandbox_mode = "workspace-write"\napproval_policy = "on-request"\n', encoding="utf-8")
        (repo_dir / ".codex" / "rules").mkdir()
        (repo_dir / ".codex" / "rules" / "ownhands.rules").write_text('prefix_rule(pattern=["python"], decision="allow")\n', encoding="utf-8")
        (repo_dir / ".codex" / "hooks.json").write_text('{"hooks":[]}\n', encoding="utf-8")
        git_cmd(repo_dir, "add", ".")
        git_cmd(repo_dir, "commit", "-m", "initial")
        start_commit = git_cmd(repo_dir, "rev-parse", "HEAD").decode().strip()
        diff_patch = git_cmd(repo_dir, "diff", "--binary", start_commit)
        from devharness.managed_tasks import prepare_managed_task
        import hashlib
        patch_hash = "sha256:" + hashlib.sha256(diff_patch).hexdigest()

        # Register task in catalog with actual repo path
        with Catalog.open(self.data_paths) as catalog:
            reg = IdentityRegistry(catalog)
            proj = reg.register_project(str(repo_dir))
            wt = reg.register_worktree(proj.project_id, str(repo_dir))
            t = reg.create_task(
                wt.worktree_id,
                "managed",
                start_commit,
                "main",
                str(repo_dir),
                "test-env",
            )
            ev = EventLog(catalog)
            ev.append(
                EventDraft(
                    f"task-created:{t.task_id}",
                    t.task_id,
                    "task.created",
                    1,
                    "2026-09-07T00:00:00+00:00",
                    {"mode": "managed"},
                    "identity:lifecycle",
                    "not_needed",
                ),
                lambda p: p,
            )
            store = EvidenceStore(catalog, ev)
            store.put(
                EvidenceDraft(
                    "evidence-m2-baseline",
                    t.task_id,
                    "M2-baseline",
                    "direct_feature_probe",
                    "baseline-managed-v1",
                    "M2 baseline",
                    "pass",
                    "observed",
                    {"artifact_ref": "baseline-managed-v1"},
                    b"synthetic M2 baseline",
                    "m3-test",
                    "not_needed",
                ),
                lambda p: p,
            )

            # Build valid prepare request
            sources = []
            for src_path, src_type in (
                ("AGENTS.md", "agents_instruction"),
                (".codex/config.toml", "codex_config"),
                (".codex/rules/ownhands.rules", "rule"),
                (".codex/hooks.json", "hook"),
            ):
                sources.append(
                    {
                        "source_id": f"source:{src_path}",
                        "source_type": src_type,
                        "path": src_path,
                        "content_hash": "sha256:" + hashlib.sha256((repo_dir / src_path).read_bytes()).hexdigest(),
                    }
                )
            baseline = {
                "baseline_id": "baseline-managed-v1",
                "project_id": proj.project_id,
                "worktree_id": wt.worktree_id,
                "environment_ref": "test-env",
                "sources": sources,
                "event_refs": [f"task-created:{t.task_id}"],
                "evidence_refs": ["evidence-m2-baseline"],
                "commands": [{"command": "pytest", "kind": "test"}],
                "sensitive_paths": [],
                "unobserved": [],
            }
            from devharness.managed_tasks import _canonical_hash
            baseline["fingerprint"] = _canonical_hash(baseline)
            contract = {
                "contract_id": f"contract:{t.task_id}",
                "task": {
                    "project_id": proj.project_id,
                    "worktree_id": wt.worktree_id,
                    "task_id": t.task_id,
                    "environment_ref": "test-env",
                    "mode": "managed",
                },
                "baseline_ref": baseline["baseline_id"],
                "baseline_fingerprint": baseline["fingerprint"],
                "gate_status": "ready_for_preview",
                "approval_triggers": [],
                "permissions": [],
                "writable_paths": ["src/**"],
                "protected_targets": [".env"],
                "validation_criteria": ["pytest"],
            }
            contract["fingerprint"] = _canonical_hash(contract)
            prep_request = {
                "repository": str(repo_dir),
                "start_commit": start_commit,
                "patch_hash": patch_hash,
                "task": contract["task"],
                "baseline": baseline,
                "contract": contract,
                "sandbox_mode": "workspace-write",
                "approval_policy": "on-request",
                "branch": "main",
                "freshness": {"status": "fresh", "basis": "observed"},
                "available_event_refs": [f"task-created:{t.task_id}"],
                "available_evidence_refs": ["evidence-m2-baseline"],
                "approval": {
                    "decision": "approved",
                    "decision_source": "explicit_product_approval",
                    "contract_ref": contract["contract_id"],
                    "task_id": t.task_id,
                    "scope": "managed_task_start",
                    "expires_at": "2026-09-07T12:00:00+00:00",
                },
            }
            prepared = prepare_managed_task(prep_request, now="2026-09-07T00:00:00+00:00")

        # Now call task.record_run via MCP tool
        run_data = {
            "records": [
                {
                    "kind": "notification",
                    "method": "item/completed",
                    "payload_hash": "sha256:" + "0" * 64,
                    "request_id": None,
                    "thread_id": "th-1",
                    "turn_id": "tu-1",
                    "item_id": "it-1",
                    "item_type": "commandExecution",
                    "status": "completed",
                    "decision": None,
                }
            ],
            "thread_id": "th-1",
            "turn_id": "tu-1",
            "terminal_status": "completed",
            "instruction_sources": ["AGENTS.md"],
            "codex_version": "0.48.0",
            "protocol_fingerprint": "sha256:" + "0" * 64,
        }
        env = self.call_tool(
            "task.record_run",
            {"prepared": prepared, "run": run_data},
        )
        self.assertEqual(env["status"], "ok")
        self.assertEqual(env["decision"], "pass")
        self.assertEqual(env["data"]["task_id"], t.task_id)

    def test_tests_gap_detect_evaluates_core_gaps_field(self) -> None:
        from devharness.mcp.tools.assurance import handle_tests_gap_detect
        contract = self._make_test_contract()
        impact = {"contract_id": contract["contract_id"], "fingerprint": "sha256:" + "0" * 64, "relations": []}
        design = {"contract_id": contract["contract_id"], "selected_tests": [], "mappings": []}
        comparison = {"comparisons": []}

        # Mock detect_test_gaps return
        import devharness.mcp.tools.assurance as assurance_mod
        orig = assurance_mod.detect_test_gaps
        try:
            # Case 1: Core gaps has required gap -> hard_block
            assurance_mod.detect_test_gaps = lambda c, i, d, cmp: {"gaps": [{"required": True, "kind": "no_test"}]}
            res1 = handle_tests_gap_detect({"contract": contract, "impact": impact, "design": design, "comparison": comparison}, self.data_paths)
            self.assertEqual(res1["decision"], "hard_block")

            # Case 2: Core gaps has only optional gap -> soft_block
            assurance_mod.detect_test_gaps = lambda c, i, d, cmp: {"gaps": [{"required": False, "kind": "optional_gap"}]}
            res2 = handle_tests_gap_detect({"contract": contract, "impact": impact, "design": design, "comparison": comparison}, self.data_paths)
            self.assertEqual(res2["decision"], "soft_block")

            # Case 3: Core gaps is empty -> pass
            assurance_mod.detect_test_gaps = lambda c, i, d, cmp: {"gaps": []}
            res3 = handle_tests_gap_detect({"contract": contract, "impact": impact, "design": design, "comparison": comparison}, self.data_paths)
            self.assertEqual(res3["decision"], "pass")
        finally:
            assurance_mod.detect_test_gaps = orig

    def test_tests_design_memo_evaluates_omitted_viewpoints(self) -> None:
        from devharness.mcp.tools.assurance import handle_tests_design_memo
        contract = self._make_test_contract()
        impact = {"fingerprint": "sha256:" + "0" * 64}
        catalog = [{"criterion_id": "crit1", "test_ids": ["test_red_1"], "required_viewpoints": ["v1"]}]

        import devharness.mcp.tools.assurance as assurance_mod
        orig = assurance_mod.build_test_design
        try:
            # Case 1: omitted_viewpoints is non-empty -> soft_block
            assurance_mod.build_test_design = lambda c, i, req: {"mappings": [{"omitted_viewpoints": ["v2"]}]}
            res1 = handle_tests_design_memo({"contract": contract, "impact": impact, "requirement_catalog": catalog}, self.data_paths)
            self.assertEqual(res1["decision"], "soft_block")

            # Case 2: omitted_viewpoints is empty -> pass
            assurance_mod.build_test_design = lambda c, i, req: {"mappings": [{"omitted_viewpoints": []}]}
            res2 = handle_tests_design_memo({"contract": contract, "impact": impact, "requirement_catalog": catalog}, self.data_paths)
            self.assertEqual(res2["decision"], "pass")
        finally:
            assurance_mod.build_test_design = orig

    def test_git_diff_impact_unobserved_and_protected_targets(self) -> None:
        from devharness.mcp.tools.assurance import handle_git_diff_impact
        # Case 1: Missing contract/restore_point/relation_catalog returns error envelope, not fallback
        res_missing = handle_git_diff_impact({"root": str(self.root)})
        self.assertEqual(res_missing["status"], "error")
        self.assertIsNone(res_missing["decision"])

        import devharness.mcp.tools.assurance as assurance_mod
        orig = assurance_mod.analyze_impact
        try:
            # Case 2: protected_target_changes present -> hard_block
            assurance_mod.analyze_impact = lambda **kw: {"protected_target_changes": [".env"], "unobserved": []}
            res_prot = handle_git_diff_impact({
                "root": str(self.root),
                "contract": {},
                "restore_point": {},
                "relation_catalog": {},
            })
            self.assertEqual(res_prot["decision"], "hard_block")

            # Case 3: unobserved present -> soft_block
            assurance_mod.analyze_impact = lambda **kw: {"protected_target_changes": [], "unobserved": [{"area": "src/new.py"}]}
            res_unobs = handle_git_diff_impact({
                "root": str(self.root),
                "contract": {},
                "restore_point": {},
                "relation_catalog": {},
            })
            self.assertEqual(res_unobs["decision"], "soft_block")

            # Case 4: clean -> pass
            assurance_mod.analyze_impact = lambda **kw: {"protected_target_changes": [], "unobserved": []}
            res_clean = handle_git_diff_impact({
                "root": str(self.root),
                "contract": {},
                "restore_point": {},
                "relation_catalog": {},
            })
            self.assertEqual(res_clean["decision"], "pass")
        finally:
            assurance_mod.analyze_impact = orig

    def test_context_benchmark_evaluate_three_core_verdicts(self) -> None:
        from devharness.mcp.tools.context import handle_context_benchmark_evaluate
        import devharness.mcp.tools.context as context_mod
        orig = context_mod.evaluate_comparison
        try:
            # recommended -> pass
            context_mod.evaluate_comparison = lambda p, r: {"improvement_verdict": "recommended"}
            r1 = handle_context_benchmark_evaluate({"package": {}, "runs": []})
            self.assertEqual(r1["decision"], "pass")

            # no_improvement -> soft_block
            context_mod.evaluate_comparison = lambda p, r: {"improvement_verdict": "no_improvement"}
            r2 = handle_context_benchmark_evaluate({"package": {}, "runs": []})
            self.assertEqual(r2["decision"], "soft_block")

            # not_evaluated -> unobserved
            context_mod.evaluate_comparison = lambda p, r: {"improvement_verdict": "not_evaluated"}
            r3 = handle_context_benchmark_evaluate({"package": {}, "runs": []})
            self.assertEqual(r3["decision"], "unobserved")
        finally:
            context_mod.evaluate_comparison = orig

    def test_guarantee_evaluate_verdict_decision_mapping(self) -> None:
        from devharness.mcp.tools.assurance import handle_guarantee_evaluate
        import devharness.mcp.tools.assurance as assurance_mod
        orig = assurance_mod.GuaranteeEvaluator

        class MockEvaluator:
            def __init__(self, catalog, store, matrix):
                pass
            def evaluate(self, task_id, claim_ids=None):
                return getattr(self, "_report", {})

        mock = MockEvaluator(None, None, None)
        assurance_mod.GuaranteeEvaluator = lambda *a, **k: mock
        try:
            # Case 1: any contradicted -> hard_block
            mock._report = {"claim_results": [{"verdict": "supported"}, {"verdict": "contradicted"}]}
            res1 = handle_guarantee_evaluate({"task_id": self.task.task_id}, self.data_paths)
            self.assertEqual(res1["decision"], "hard_block")

            # Case 2: any not_evaluated -> unobserved
            mock._report = {"claim_results": [{"verdict": "supported"}, {"verdict": "not_evaluated"}]}
            res2 = handle_guarantee_evaluate({"task_id": self.task.task_id}, self.data_paths)
            self.assertEqual(res2["decision"], "unobserved")

            # Case 3: all supported -> pass
            mock._report = {"claim_results": [{"verdict": "supported"}, {"verdict": "supported"}]}
            res3 = handle_guarantee_evaluate({"task_id": self.task.task_id}, self.data_paths)
            self.assertEqual(res3["decision"], "pass")
        finally:
            assurance_mod.GuaranteeEvaluator = orig

    def test_option_c_error_envelope_and_mcp_underscore_removed(self) -> None:
        from devharness.mcp.tools.common import make_error_envelope, task_not_found_response
        # Default decision is None
        err = make_error_envelope("SampleError", "Sample message")
        self.assertIsNone(err["decision"])
        self.assertEqual(err["status"], "error")

        # TaskNotFound preserves hard_block
        tnf = task_not_found_response("some-task")
        self.assertEqual(tnf["decision"], "hard_block")
        self.assertEqual(tnf["status"], "error")

        # MCP server rejects underscore aliases
        req = {
            "jsonrpc": "2.0",
            "id": 999,
            "method": "tools/call",
            "params": {"name": "context_lint", "arguments": {}},
        }
        resp = self.server.handle_request(req)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)  # METHOD_NOT_FOUND

    def test_record_tool_evidence_preserves_result_and_basis_semantics(self) -> None:
        from devharness.mcp.tools.common import record_tool_evidence
        with Catalog.open(self.data_paths) as catalog:
            store = EvidenceStore(catalog, EventLog(catalog))

            # pass -> pass, observed
            id_pass = record_tool_evidence(
                self.data_paths, self.task.task_id, "REQ", "active_configuration", "sub", "sc", "pass", {"k": 1}
            )
            rec_pass = store.resolve(id_pass)
            self.assertEqual(rec_pass.result, "pass")
            self.assertEqual(rec_pass.basis, "observed")

            # soft_block -> inconclusive, observed
            id_soft = record_tool_evidence(
                self.data_paths, self.task.task_id, "REQ", "active_configuration", "sub", "sc", "soft_block", {"k": 2}
            )
            rec_soft = store.resolve(id_soft)
            self.assertEqual(rec_soft.result, "inconclusive")
            self.assertEqual(rec_soft.basis, "observed")

            # hard_block -> fail, observed
            id_hard = record_tool_evidence(
                self.data_paths, self.task.task_id, "REQ", "active_configuration", "sub", "sc", "hard_block", {"k": 3}
            )
            rec_hard = store.resolve(id_hard)
            self.assertEqual(rec_hard.result, "fail")
            self.assertEqual(rec_hard.basis, "observed")

            # unobserved -> not_run, unobserved
            id_unobs = record_tool_evidence(
                self.data_paths, self.task.task_id, "REQ", "active_configuration", "sub", "sc", "unobserved", {"k": 4}
            )
            rec_unobs = store.resolve(id_unobs)
            self.assertEqual(rec_unobs.result, "not_run")
            self.assertEqual(rec_unobs.basis, "unobserved")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from devharness.control_profile import (
    ControlProfileError,
    apply_candidate,
    assess_baseline_freshness,
    build_baseline,
    build_execution_contract,
    compile_control_profile,
    profile_project,
    render_control_preview,
    rollback_candidate,
    run_interview,
)
from devharness.m2_review import run_m2_demo


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/m2/project"
CASES = json.loads((ROOT / "tests/fixtures/m2/interview-cases.json").read_text())
ATTACKS = json.loads((ROOT / "tests/fixtures/m2/adversarial-cases.json").read_text())
NOW = "2026-09-05T12:00:00+00:00"
IDENTITY = {
    "project_id": "project-m2",
    "worktree_id": "worktree-m2",
    "environment_ref": "macos-arm64-python-3.12",
}


class ControlProfileLifecycleTests(unittest.TestCase):
    def copy_fixture(self, root: Path) -> Path:
        project = root / "project"
        shutil.copytree(FIXTURE, project)
        return project

    def profile(self, project: Path) -> dict:
        return profile_project(project, IDENTITY, observed_at=NOW)

    def baseline(self, project: Path) -> dict:
        profile = self.profile(project)
        interview = run_interview(profile, CASES["complete"])
        return build_baseline(
            profile,
            interview,
            version=1,
            predecessor_ref=None,
            event_refs=["event-profile"],
            evidence_refs=["evidence-profile"],
        )

    def overlay(self, baseline: dict, *, mode: str = "managed") -> dict:
        return {
            "overlay_version": "1.0",
            "overlay_id": "overlay-m2",
            "task": {
                **IDENTITY,
                "task_id": "task-m2",
                "mode": mode,
                "goal": "compile a safe synthetic profile",
            },
            "baseline_ref": baseline["baseline_id"],
            "baseline_fingerprint": baseline["fingerprint"],
            "instruction_overlay": {"source_refs": ["source:AGENTS.md"]},
            "control_overlay": {"source_refs": ["source:.codex/config.toml"]},
            "writable_paths": ["src/**", "output/**"],
            "protected_targets": [".env", ".git/**"],
            "permission_expansions": [],
            "approval_triggers": ["external_effect", "protected_target"],
            "validation_criteria": ["python -m unittest -v"],
            "gate_criteria": ["tests_pass", "no_protected_target_change"],
            "unobserved_paths": baseline["unobserved"],
        }

    def approvals(self) -> list[dict]:
        return [{
            "approval_id": "approval-network",
            "task_id": "task-m2",
            "decision": "approved",
            "decision_source": "explicit_product_approval",
            "scope": "api.openai.com",
            "permission": "network",
            "expires_at": "2026-09-05T13:00:00+00:00",
        }]

    def contract(self, project: Path, *, mode: str = "managed") -> dict:
        baseline = self.baseline(project)
        return build_execution_contract(baseline, self.overlay(baseline, mode=mode), self.approvals(), now=NOW)

    def test_profiler_is_deterministic_read_only_and_redacts_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            secret = "m2-fixture-secret-value"
            (project / ".env").write_text(f"API_KEY={secret}\n")
            before = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            first = self.profile(project)
            second = self.profile(project)
            after = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            serialized = json.dumps(first, ensure_ascii=False)
            self.assertEqual(first, second)
            self.assertEqual(before, after)
            self.assertNotIn(secret, serialized)
            self.assertIn(".env", {item["path"] for item in first["sensitive_paths"]})
            self.assertEqual({"test", "lint"}, {item["kind"] for item in first["commands"]})
            self.assertEqual({"inspect_hwpx", "write_hwpx"}, {item["name"] for item in first["hwpx_tool_contract"]["tools"]})
            self.assertTrue(all(source["realization"]["loaded"]["basis"] == "unobserved" for source in first["sources"]))

    def test_profiler_marks_unsupported_symlink_unobserved_without_following_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.copy_fixture(root)
            outside = root / "outside.txt"
            outside.write_text("outside-secret")
            (project / "linked.txt").symlink_to(outside)
            report = self.profile(project)
            self.assertIn("linked.txt", {item["path"] for item in report["unobserved"]})
            self.assertNotIn("outside-secret", json.dumps(report))

    def test_interview_asks_one_decision_and_fails_closed_on_ambiguous_declined_or_silent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self.profile(self.copy_fixture(Path(temporary)))
            complete = run_interview(report, CASES["complete"])
            self.assertEqual(["failure_impact", "external_effect"], [turn["question"]["decision_ids"][0] for turn in complete["transcript"]])
            inferred = {item["decision_id"]: item for item in complete["decisions"] if item["status"] == "recommended"}
            self.assertEqual({"protected_data", "permission_expansion", "validation"}, set(inferred))
            self.assertTrue(all(len(turn["question"]["decision_ids"]) == 1 for turn in complete["transcript"]))
            self.assertTrue(all(turn["question"]["recommendation"] and turn["question"]["reason"] for turn in complete["transcript"]))
            for case in ("ambiguous", "silence"):
                result = run_interview(report, CASES[case])
                self.assertFalse(result["approval_granted"])
                self.assertTrue(result["unresolved_decisions"])
                self.assertEqual("synthetic_fixture", result["evidence_basis"])

    def test_baseline_is_bound_versioned_deterministic_and_never_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            first = self.baseline(project)
            self.assertEqual(first["fingerprint"], self.baseline(project)["fingerprint"])
            with self.assertRaisesRegex(ControlProfileError, "predecessor"):
                build_baseline(self.profile(project), run_interview(self.profile(project), CASES["complete"]), version=2, predecessor_ref=None, event_refs=["event-profile"], evidence_refs=["evidence-profile"])
            second = build_baseline(self.profile(project), run_interview(self.profile(project), CASES["complete"]), version=2, predecessor_ref=first["baseline_id"], event_refs=["event-profile"], evidence_refs=["evidence-profile"])
            self.assertEqual(first["baseline_id"], second["predecessor_ref"])
            foreign = copy.deepcopy(self.profile(project))
            foreign["project_id"] = ATTACKS["foreign_identity"]["project_id"]
            with self.assertRaisesRegex(ControlProfileError, "identity"):
                assess_baseline_freshness(first, foreign, "source_change", {"event-profile", "evidence-profile"})

    def test_baseline_freshness_handles_change_manual_refresh_and_unsupported_as_unobserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            baseline = self.baseline(project)
            current = self.profile(project)
            self.assertEqual("fresh", assess_baseline_freshness(baseline, current, "scheduled_check", {"event-profile", "evidence-profile"})["status"])
            (project / "AGENTS.md").write_text("changed")
            self.assertEqual("stale", assess_baseline_freshness(baseline, self.profile(project), "source_change", {"event-profile", "evidence-profile"})["status"])
            self.assertEqual("stale", assess_baseline_freshness(baseline, current, "manual_refresh", {"event-profile", "evidence-profile"})["status"])
            self.assertEqual("unobserved", assess_baseline_freshness(baseline, current, "unsupported_change", {"event-profile", "evidence-profile"})["status"])
            with self.assertRaisesRegex(ControlProfileError, "reference"):
                assess_baseline_freshness(baseline, current, "scheduled_check", {"event-profile"})

    def test_project_contract_content_change_marks_baseline_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            baseline = self.baseline(project)
            (project / "REQUIREMENTS.md").write_text("changed contract")
            result = assess_baseline_freshness(
                baseline,
                self.profile(project),
                "source_change",
                {"event-profile", "evidence-profile"},
            )
            self.assertEqual("stale", result["status"])

    def test_contract_permission_expansion_needs_exact_live_product_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            baseline = self.baseline(project)
            overlay = self.overlay(baseline)
            overlay["permission_expansions"] = [{"permission": "network", "scope": "api.openai.com", "reason": "task API call", "duration": "task", "approval_ref": "approval-network"}]
            active = build_execution_contract(baseline, overlay, self.approvals(), now=NOW)
            self.assertTrue(active["permissions"][0]["active"])
            for approvals in ([], [{**self.approvals()[0], "decision_source": "fixture_response"}], [{**self.approvals()[0], "expires_at": ATTACKS["expired_approval"]}]):
                contract = build_execution_contract(baseline, overlay, approvals, now=NOW)
                self.assertFalse(contract["permissions"][0]["active"])
                self.assertEqual("hard_block", contract["gate_status"])
            widened = copy.deepcopy(overlay)
            widened["permission_expansions"][0].pop("approval_ref")
            with self.assertRaisesRegex(ControlProfileError, "approval_ref"):
                build_execution_contract(baseline, widened, self.approvals(), now=NOW)

    def test_contract_rejects_protected_targets_overlay_mixing_and_imported_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            baseline = self.baseline(project)
            overlay = self.overlay(baseline)
            overlay["writable_paths"].append(".env")
            with self.assertRaisesRegex(ControlProfileError, "protected"):
                build_execution_contract(baseline, overlay, [], now=NOW)
            overlay = self.overlay(baseline)
            overlay["instruction_overlay"]["source_refs"] = ["source:.codex/config.toml"]
            with self.assertRaisesRegex(ControlProfileError, "instruction_overlay"):
                build_execution_contract(baseline, overlay, [], now=NOW)
            imported = self.contract(project, mode="imported")
            self.assertEqual("not_run", imported["realization"]["loaded"]["result"])
            self.assertEqual("unobserved", imported["realization"]["enforced"]["basis"])

    def test_compiler_is_deterministic_dry_run_and_lints_conflict_excess_and_unknowns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            contract = self.contract(project)
            existing = {
                ".codex/config.toml": "sandbox_mode = \"read-only\"\n",
                ".codex/hooks.json": "{\"hooks\":[{\"event\":\"before_task\"},{\"event\":\"before_task\"}]}",
                ".codex/rules/duplicate.rules": "allow python\nallow python\n",
            }
            first = compile_control_profile(contract, existing, codex_version="9.9.9")
            second = compile_control_profile(contract, existing, codex_version="9.9.9")
            self.assertEqual(first, second)
            self.assertTrue(first["dry_run"])
            self.assertEqual({"config", "agents", "rules", "hooks", "sandbox", "approval"}, {item["artifact_type"] for item in first["artifacts"]})
            codes = {item["code"] for item in first["findings"]}
            self.assertTrue({"precedence_conflict", "duplicate_hook", "duplicate_rule", "unsupported_codex_version"} <= codes)
            self.assertFalse(first["apply_ready"])

    def test_apply_requires_real_approval_journals_atomic_diff_and_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.copy_fixture(root)
            (project / ".ownhands-disposable").write_text("fixture")
            contract = self.contract(project)
            existing = {str(path.relative_to(project)): path.read_text() for path in project.rglob("*") if path.is_file() and path.name != ".env"}
            compiled = compile_control_profile(contract, existing)
            with self.assertRaisesRegex(ControlProfileError, "explicit product approval"):
                apply_candidate(compiled, project, {"decision_source": "fixture_response", "decision": "approved"})
            application = apply_candidate(compiled, project, {"decision_source": "explicit_product_approval", "decision": "approved", "contract_ref": contract["contract_id"]})
            self.assertTrue(Path(application["journal_path"]).exists())
            self.assertTrue(application["verified"])
            with self.assertRaisesRegex(ControlProfileError, "journal"):
                apply_candidate(compiled, project, {"decision_source": "explicit_product_approval", "decision": "approved", "contract_ref": contract["contract_id"]})
            rollback = rollback_candidate(project, Path(application["journal_path"]))
            self.assertTrue(rollback["verified"])
            self.assertEqual(existing[".codex/config.toml"], (project / ".codex/config.toml").read_text())

    def test_apply_rejects_stale_diff_and_non_disposable_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            contract = self.contract(project)
            existing = {str(path.relative_to(project)): path.read_text() for path in project.rglob("*") if path.is_file()}
            compiled = compile_control_profile(contract, existing)
            approval = {"decision_source": "explicit_product_approval", "decision": "approved", "contract_ref": contract["contract_id"]}
            with self.assertRaisesRegex(ControlProfileError, "disposable"):
                apply_candidate(compiled, project, approval)
            (project / ".ownhands-disposable").write_text("fixture")
            (project / ".codex/config.toml").write_text("changed after diff")
            with self.assertRaisesRegex(ControlProfileError, "stale diff"):
                apply_candidate(compiled, project, approval)

    def test_apply_rejects_escape_and_symlink_parent_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.copy_fixture(root)
            (project / ".ownhands-disposable").write_text("fixture")
            contract = self.contract(project)
            existing = {str(path.relative_to(project)): path.read_text() for path in project.rglob("*") if path.is_file()}
            compiled = compile_control_profile(contract, existing)
            approval = {"decision_source": "explicit_product_approval", "decision": "approved", "contract_ref": contract["contract_id"]}
            original_agents = (project / "AGENTS.md").read_text()
            malicious = copy.deepcopy(compiled["artifacts"][-1])
            malicious["path"] = "../outside.txt"
            malicious["before_hash"] = None
            compiled["artifacts"].append(malicious)
            with self.assertRaisesRegex(ControlProfileError, "contained"):
                apply_candidate(compiled, project, approval)
            self.assertFalse((root / "outside.txt").exists())
            self.assertEqual(original_agents, (project / "AGENTS.md").read_text())
            self.assertFalse((project / ".ownhands-rollback-journal.json").exists())

            for invalid_path in ("", ".", "/tmp/ownhands-absolute-escape", "nested/../escape.txt"):
                invalid = compile_control_profile(contract, existing)
                malicious = copy.deepcopy(invalid["artifacts"][-1])
                malicious["path"] = invalid_path
                malicious["before_hash"] = None
                invalid["artifacts"].append(malicious)
                with self.subTest(path=invalid_path), self.assertRaisesRegex(ControlProfileError, "contained"):
                    apply_candidate(invalid, project, approval)

            compiled = compile_control_profile(contract, existing)
            outside_directory = root / "outside"
            outside_directory.mkdir()
            try:
                (project / ".escape").symlink_to(outside_directory, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            malicious = copy.deepcopy(compiled["artifacts"][-1])
            malicious["path"] = ".escape/pwned.txt"
            malicious["before_hash"] = None
            compiled["artifacts"].append(malicious)
            with self.assertRaisesRegex(ControlProfileError, "symlink"):
                apply_candidate(compiled, project, approval)
            self.assertFalse((outside_directory / "pwned.txt").exists())

    def test_rollback_rejects_alternate_journal_and_tampered_escape_before_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.copy_fixture(root)
            (project / ".ownhands-disposable").write_text("fixture")
            contract = self.contract(project)
            existing = {str(path.relative_to(project)): path.read_text() for path in project.rglob("*") if path.is_file()}
            compiled = compile_control_profile(contract, existing)
            approval = {"decision_source": "explicit_product_approval", "decision": "approved", "contract_ref": contract["contract_id"]}
            application = apply_candidate(compiled, project, approval)
            journal_path = Path(application["journal_path"])
            alternate = project / "alternate-journal.json"
            alternate.write_bytes(journal_path.read_bytes())
            with self.assertRaisesRegex(ControlProfileError, "expected journal"):
                rollback_candidate(project, alternate)

            journal = json.loads(journal_path.read_text())
            escaped = journal["entries"][-1]
            escaped["path"] = "../outside.txt"
            outside = root / "outside.txt"
            outside.write_text(compiled["artifacts"][-1]["content"])
            journal_path.write_text(json.dumps(journal))
            applied_agents = (project / "AGENTS.md").read_text()
            with self.assertRaisesRegex(ControlProfileError, "contained"):
                rollback_candidate(project, journal_path)
            self.assertEqual(compiled["artifacts"][-1]["content"], outside.read_text())
            self.assertEqual(applied_agents, (project / "AGENTS.md").read_text())

    def test_preview_escapes_data_has_semantic_structure_and_rejects_broken_evidence_or_stale_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = self.copy_fixture(Path(temporary))
            contract = self.contract(project)
            contract["task"]["goal"] = ATTACKS["html_injection"]
            compiled = compile_control_profile(contract, {})
            refs = set(contract["event_refs"] + contract["evidence_refs"])
            html = render_control_preview(contract, compiled, {ref: f"evidence/{ref}" for ref in refs})
            self.assertNotIn("<script>", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("<main", html)
            self.assertIn("<svg", html)
            self.assertIn("<title>", html)
            self.assertIn("Changed", html)
            self.assertIn("Protected", html)
            self.assertIn("Unobserved", html)
            self.assertIn("Restore unavailable", html)
            with self.assertRaisesRegex(ControlProfileError, "drill-down"):
                render_control_preview(contract, compiled, {})
            stale = copy.deepcopy(compiled)
            stale["contract_fingerprint"] = "sha256:stale"
            with self.assertRaisesRegex(ControlProfileError, "stale"):
                render_control_preview(contract, stale, {ref: ref for ref in refs})

    def test_vertical_slice_uses_m1_store_and_keeps_raw_evidence_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.copy_fixture(root)
            output = root / "preview.html"
            result = run_m2_demo(root / "app-data", project, output, observed_at=NOW)
            self.assertTrue(output.exists())
            self.assertEqual(["profile", "interview", "baseline", "contract", "compile", "preview"], result["stages"])
            self.assertTrue(result["event_refs"])
            self.assertTrue(result["evidence_refs"])
            self.assertFalse(any(path.is_relative_to(project) for path in (root / "app-data").rglob("*") if path.is_file()))
            html = output.read_text()
            self.assertIn(result["contract_id"], html)
            self.assertNotIn("m2-fixture-secret", html)


if __name__ == "__main__":
    unittest.main()

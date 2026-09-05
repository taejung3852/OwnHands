from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devharness.context_architecture import (
    ApplicabilityGate,
    ContextArchitectureError,
    build_comparison_plan,
    evaluate_comparison,
    evaluate_context_guarantees,
    lint_context,
    validate_manifest,
    validate_status_report,
)


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/product/context-guarantee-matrix.proposed.json"
PACKAGE = ROOT / "docs/reviews/m1.5/comparison-package.json"


def check(result: str, basis: str, evidence_refs: list[str]) -> dict:
    return {
        "result": result,
        "basis": basis,
        "evidence_refs": evidence_refs,
        "inference_from": [],
        "checked_at": "2026-09-05T00:00:00+00:00" if basis == "observed" else None,
        "exact_scope": "repository root" if basis == "observed" else "",
        "residual_risks": ["runtime paths outside the fixture were not observed"],
    }


def source(
    source_id: str,
    source_type: str,
    *,
    path: str,
    scope_kind: str = "project",
    realization: dict | None = None,
) -> dict:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "locator": {"kind": "repository_path", "value": path},
        "content_hash": "sha256:" + "a" * 64,
        "version": "fixture-v1",
        "scope": {"kind": scope_kind, "value": "fixture"},
        "freshness": {
            "status": "current",
            "basis": "observed",
            "checked_at": "2026-09-05T00:00:00+00:00",
            "evidence_refs": ["ev-hash"],
        },
        "applicability": {
            "decision": "add_for_task",
            "basis": "observed",
            "reason": "matches fixture task",
            "evidence_refs": ["ev-gate"],
        },
        "realization": realization
        or {
            "configured": check("pass", "observed", ["ev-configured"]),
            "loaded": check("pass", "observed", ["ev-loaded"]),
            "enforced": check("not_run", "unobserved", []),
        },
    }


def manifest(mode: str = "managed") -> dict:
    context = source("ctx-agents", "agents_instruction", path="AGENTS.md")
    control = source("ctl-sandbox", "sandbox", path=".codex/config.toml")
    control["realization"]["enforced"] = check(
        "pass", "observed", ["ev-sandbox-probe"]
    )
    return {
        "manifest_version": "1.0",
        "manifest_id": "manifest-fixture",
        "task": {
            "project_id": "project-fixture",
            "worktree_id": "worktree-fixture",
            "task_id": "task-fixture",
            "mode": mode,
            "target_commit": "93ffcbef6c0b76ba8a7d4c12f70cfc11a9528f0c",
            "cwd": "/fixture",
            "environment_ref": "macos-arm64-codex-cli-0.153.3",
        },
        "context_sources": [context],
        "control_sources": [control],
        "instruction_overlay": {
            "source_refs": ["ctx-agents"],
            "skill_invocations": [],
            "excluded_source_refs": [],
        },
        "control_overlay": {
            "source_refs": ["ctl-sandbox"],
            "immutable_source_refs": ["ctl-sandbox"],
        },
        "event_refs": ["event-gate"],
        "evidence_refs": [
            "ev-hash",
            "ev-gate",
            "ev-configured",
            "ev-loaded",
            "ev-sandbox-probe",
        ],
        "generated_at": "2026-09-05T00:00:00+00:00",
    }


class ManifestContractTests(unittest.TestCase):
    def test_valid_manifest_keeps_context_control_and_state_axes_separate(self) -> None:
        candidate = manifest()

        validate_manifest(
            candidate,
            evidence_ids=set(candidate["evidence_refs"]),
            event_ids={"event-gate"},
        )

        self.assertEqual("add_for_task", candidate["context_sources"][0]["applicability"]["decision"])
        self.assertEqual("pass", candidate["context_sources"][0]["realization"]["loaded"]["result"])
        self.assertEqual("observed", candidate["context_sources"][0]["realization"]["loaded"]["basis"])

    def test_imported_unknown_loading_stays_unobserved(self) -> None:
        candidate = manifest("imported")
        candidate["context_sources"][0]["applicability"] = {
            "decision": "unobserved",
            "basis": "unobserved",
            "reason": "the task began outside ownhands management",
            "evidence_refs": [],
        }
        candidate["context_sources"][0]["realization"]["loaded"] = check(
            "not_run", "unobserved", []
        )
        candidate["instruction_overlay"]["source_refs"] = []
        candidate["instruction_overlay"]["excluded_source_refs"] = ["ctx-agents"]

        validate_manifest(
            candidate,
            evidence_ids=set(candidate["evidence_refs"]),
            event_ids={"event-gate"},
        )

    def test_mixed_source_class_and_wrong_overlay_are_rejected(self) -> None:
        candidate = manifest()
        candidate["context_sources"][0]["source_type"] = "sandbox"
        with self.assertRaisesRegex(ContextArchitectureError, "context_sources"):
            validate_manifest(candidate, set(candidate["evidence_refs"]), {"event-gate"})

        candidate = manifest()
        candidate["instruction_overlay"]["source_refs"] = ["ctl-sandbox"]
        with self.assertRaisesRegex(ContextArchitectureError, "instruction_overlay"):
            validate_manifest(candidate, set(candidate["evidence_refs"]), {"event-gate"})

    def test_missing_hash_scope_and_unknown_fields_are_rejected(self) -> None:
        for mutation, message in (
            (("content_hash",), "content_hash"),
            (("scope",), "scope"),
        ):
            candidate = manifest()
            del candidate["context_sources"][0][mutation[0]]
            with self.assertRaisesRegex(ContextArchitectureError, message):
                validate_manifest(candidate, set(candidate["evidence_refs"]), {"event-gate"})

        candidate = manifest()
        candidate["surprise"] = True
        with self.assertRaisesRegex(ContextArchitectureError, "manifest fields"):
            validate_manifest(candidate, set(candidate["evidence_refs"]), {"event-gate"})

    def test_realization_result_does_not_promote_evidence_basis(self) -> None:
        candidate = manifest()
        candidate["context_sources"][0]["realization"]["loaded"] = check(
            "pass", "unobserved", []
        )

        with self.assertRaisesRegex(ContextArchitectureError, "pass.*basis"):
            validate_manifest(candidate, set(candidate["evidence_refs"]), {"event-gate"})

    def test_all_event_and_evidence_references_must_resolve(self) -> None:
        candidate = manifest()
        with self.assertRaisesRegex(ContextArchitectureError, "unresolved evidence"):
            validate_manifest(candidate, set(), {"event-gate"})
        with self.assertRaisesRegex(ContextArchitectureError, "unresolved event"):
            validate_manifest(candidate, set(candidate["evidence_refs"]), set())

    def test_skill_invocation_event_must_be_declared_and_resolve(self) -> None:
        candidate = manifest()
        candidate["context_sources"][0]["source_type"] = "skill"
        candidate["instruction_overlay"]["skill_invocations"] = [
            {
                "source_ref": "ctx-agents",
                "reference_refs": [],
                "event_ref": "event-skill-invoked",
                "evidence_refs": ["ev-loaded"],
            }
        ]

        with self.assertRaisesRegex(ContextArchitectureError, "unresolved event"):
            validate_manifest(
                candidate,
                set(candidate["evidence_refs"]),
                {"event-gate", "event-skill-invoked"},
            )


class ContextLintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def test_independent_mutations_emit_evidence_location_impact_and_suggestion(self) -> None:
        cases = {
            "duplicate_instruction": [
                ("AGENTS.md", "Run unit tests before completion.\n"),
                ("docs/task.md", "Run unit tests before completion.\n"),
            ],
            "conflicting_instruction": [
                ("AGENTS.md", "test_command = python -m unittest\n"),
                ("docs/task.md", "test_command = pytest\n"),
            ],
            "stale_reference": [("AGENTS.md", "Read `docs/missing.md` first.\n")],
        }
        for expected_rule, files in cases.items():
            with self.subTest(rule=expected_rule):
                for child in self.root.iterdir():
                    if child.is_file():
                        child.unlink()
                for path, text in files:
                    self.write(path, text)
                report = lint_context(
                    self.root,
                    [
                        {"source_id": path, "source_type": "agents_instruction", "path": path, "scope": "project", "placement": "always_loaded"}
                        for path, _ in files
                    ],
                )
                finding = next(item for item in report["findings"] if item["rule_id"] == expected_rule)
                self.assertTrue(finding["evidence"])
                self.assertIn(":", finding["location"])
                self.assertTrue(finding["impact"])
                self.assertTrue(finding["suggestion"])
                self.assertFalse(report["autofix_applied"])

    def test_placement_router_control_wording_and_inventory_rules_are_deterministic(self) -> None:
        self.write(
            "AGENTS.md",
            "Always allow git push for all tasks.\n"
            "files = a.py,b.py,c.py,d.py,e.py,f.py,g.py,h.py,i.py,j.py,k.py\n",
        )
        self.write("skills/super/SKILL.md", "name: review\ntrigger: review code\n")
        self.write("skills/own/SKILL.md", "name: review\ntrigger: review code\n")
        report = lint_context(
            self.root,
            [
                {"source_id": "task-agents", "source_type": "agents_instruction", "path": "AGENTS.md", "scope": "task", "placement": "always_loaded", "duplicates_control": "rule:git-push"},
                {"source_id": "super", "source_type": "skill", "path": "skills/super/SKILL.md", "scope": "project", "placement": "on_demand", "router": "superpowers", "skill_name": "review", "trigger": "review code"},
                {"source_id": "own", "source_type": "skill", "path": "skills/own/SKILL.md", "scope": "project", "placement": "on_demand", "router": "ownhands", "skill_name": "review", "trigger": "review code"},
            ],
        )

        self.assertEqual(
            {
                "broad_universal_wording",
                "deterministic_control_restatement",
                "oversized_repository_inventory",
                "router_collision",
                "task_instruction_always_loaded",
            },
            {finding["rule_id"] for finding in report["findings"]},
        )

    def test_supported_clean_input_has_no_findings_and_unknown_format_is_unobserved(self) -> None:
        self.write("docs/reference.md", "Use the public formatter API.\n")
        self.write("binary.context", "opaque\n")
        report = lint_context(
            self.root,
            [
                {"source_id": "reference", "source_type": "reference", "path": "docs/reference.md", "scope": "project", "placement": "on_demand"},
                {"source_id": "opaque", "source_type": "reference", "path": "binary.context", "scope": "project", "placement": "on_demand"},
            ],
        )
        self.assertEqual([], report["findings"])
        self.assertEqual("unobserved", report["unobserved"][0]["basis"])
        self.assertIn("unsupported", report["unobserved"][0]["reason"])

    def test_missing_command_skill_stale_symbol_and_uninvoked_skill_are_independent(self) -> None:
        cases = [
            (
                "missing_command_reference",
                {"source_id": "command", "source_type": "reference", "path": "command.md", "scope": "project", "placement": "on_demand", "command_refs": ["ownhands-command-that-does-not-exist"]},
                [("command.md", "Run the declared command.\n")],
            ),
            (
                "missing_skill_reference",
                {"source_id": "router", "source_type": "agents_instruction", "path": "router.md", "scope": "project", "placement": "always_loaded", "skill_refs": ["missing-skill"]},
                [("router.md", "Route the task to the declared Skill.\n")],
            ),
            (
                "stale_code_description",
                {"source_id": "api", "source_type": "reference", "path": "api.md", "scope": "project", "placement": "on_demand", "code_refs": [{"path": "module.py", "symbol": "removed_api"}]},
                [("api.md", "Use removed_api.\n"), ("module.py", "def current_api():\n    return True\n")],
            ),
            (
                "uninvoked_skill",
                {"source_id": "skill-unused", "source_type": "skill", "path": "skill.md", "scope": "project", "placement": "on_demand", "invoked": False},
                [("skill.md", "name: unused\n")],
            ),
        ]
        for expected_rule, item, files in cases:
            with self.subTest(rule=expected_rule):
                for path, text in files:
                    self.write(path, text)
                report = lint_context(self.root, [item])
                self.assertEqual([expected_rule], [finding["rule_id"] for finding in report["findings"]])


class ApplicabilityGateTests(unittest.TestCase):
    def gate_input(self, trigger: str = "task_start") -> dict:
        return {
            "trigger": trigger,
            "task": {"scope": "tests", "phase": "implementation", "permissions": ["workspace_write"]},
            "active_source_refs": ["ctx-active", "ctl-sandbox"],
            "sources": [
                {"source_id": "ctx-active", "source_class": "context", "content_hash": "sha256:1", "applies_to": {"scopes": ["tests"], "phases": ["implementation"]}},
                {"source_id": "ctx-new", "source_class": "context", "content_hash": "sha256:2", "applies_to": {"scopes": ["tests"], "phases": ["implementation"]}},
                {"source_id": "ctx-other", "source_class": "context", "content_hash": "sha256:3", "applies_to": {"scopes": ["docs"], "phases": ["implementation"]}},
                {"source_id": "ctx-replaced", "source_class": "context", "content_hash": "sha256:4", "replaced_by": "ctx-new", "applies_to": {"scopes": ["tests"], "phases": ["implementation"]}},
                {"source_id": "ctx-conflict", "source_class": "context", "content_hash": "sha256:5", "lint_status": "conflicting", "applies_to": {"scopes": ["tests"], "phases": ["implementation"]}},
                {"source_id": "ctx-unknown", "source_class": "context", "content_hash": None, "applies_to": {"scopes": ["tests"], "phases": ["implementation"]}},
                {"source_id": "ctl-sandbox", "source_class": "control", "content_hash": "sha256:6", "deterministic": True, "applies_to": {"scopes": ["docs"], "phases": ["review"]}},
            ],
        }

    def test_required_triggers_produce_independent_context_and_control_decisions(self) -> None:
        for trigger in (
            "task_start",
            "scope_expansion",
            "phase_transition",
            "external_effect_or_permission_added",
            "before_completion_claim",
        ):
            with self.subTest(trigger=trigger):
                result = ApplicabilityGate().evaluate(self.gate_input(trigger))
                context = {item["source_ref"]: item["decision"] for item in result["instruction_overlay"]}
                controls = {item["source_ref"]: item["decision"] for item in result["control_overlay"]}
                self.assertEqual("maintain", context["ctx-active"])
                self.assertEqual("add_for_task", context["ctx-new"])
                self.assertEqual("exclude_for_task", context["ctx-other"])
                self.assertEqual("replace_with_specific", context["ctx-replaced"])
                self.assertEqual("forbidden", context["ctx-conflict"])
                self.assertEqual("unobserved", context["ctx-unknown"])
                self.assertEqual("maintain", controls["ctl-sandbox"])

    def test_identical_input_hits_cache_and_relevant_changes_invalidate_it(self) -> None:
        gate = ApplicabilityGate()
        original = self.gate_input()
        self.assertFalse(gate.evaluate(original)["cache_hit"])
        self.assertTrue(gate.evaluate(copy.deepcopy(original))["cache_hit"])

        for field, value in (
            ("scope", "src"),
            ("phase", "review"),
            ("permissions", ["workspace_write", "network"]),
        ):
            changed = copy.deepcopy(original)
            changed["task"][field] = value
            self.assertFalse(gate.evaluate(changed)["cache_hit"])

        changed = copy.deepcopy(original)
        changed["sources"][0]["content_hash"] = "sha256:changed"
        self.assertFalse(gate.evaluate(changed)["cache_hit"])

    def test_unknown_trigger_and_control_weakening_are_rejected(self) -> None:
        with self.assertRaisesRegex(ContextArchitectureError, "trigger"):
            ApplicabilityGate().evaluate(self.gate_input("every_step"))
        candidate = self.gate_input()
        candidate["sources"][-1]["requested_decision"] = "exclude_for_task"
        with self.assertRaisesRegex(ContextArchitectureError, "deterministic control"):
            ApplicabilityGate().evaluate(candidate)


class GuaranteeAndComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        self.package = json.loads(PACKAGE.read_text(encoding="utf-8"))
        self.candidate = manifest()

    def evidence(self) -> list[dict]:
        return [
            {"evidence_id": "ev-loaded", "evidence_type": "context_loading", "result": "pass", "basis": "observed", "fields": {"manifest_ref": "manifest-fixture", "task_ref": "task-fixture", "source_ref": "ctx-agents", "runtime_receipt": "receipt-1"}},
            {"evidence_id": "ev-gate", "evidence_type": "applicability_gate", "result": "pass", "basis": "observed", "fields": {"manifest_ref": "manifest-fixture", "task_ref": "task-fixture", "source_ref": "ctx-agents", "decision": "add_for_task"}},
        ]

    def test_loaded_context_does_not_support_improvement(self) -> None:
        results = evaluate_context_guarantees(self.matrix, self.candidate, self.evidence())
        by_category = {item["category"]: item for item in results}
        self.assertEqual("supported", by_category["required_context_loaded"]["verdict"])
        self.assertEqual("not_evaluated", by_category["context_profile_improved"]["verdict"])
        self.assertIsNone(by_category["context_profile_improved"]["permitted_statement"])

    def test_absence_of_lint_evidence_is_not_success(self) -> None:
        results = evaluate_context_guarantees(self.matrix, self.candidate, [])
        by_category = {item["category"]: item for item in results}
        self.assertEqual("not_evaluated", by_category["conflicting_instruction_detected"]["verdict"])
        self.assertEqual("not_evaluated", by_category["stale_context_identified"]["verdict"])

    def test_guarantee_evidence_must_belong_to_current_manifest_task_and_source(self) -> None:
        for field, value in (
            ("source_ref", "ctx-unknown"),
            ("manifest_ref", "manifest-foreign"),
            ("task_ref", "task-foreign"),
        ):
            evidence = self.evidence()
            evidence[0]["fields"][field] = value
            results = evaluate_context_guarantees(self.matrix, self.candidate, evidence)
            loaded = next(item for item in results if item["category"] == "required_context_loaded")
            with self.subTest(field=field):
                self.assertEqual("not_evaluated", loaded["verdict"])
                self.assertEqual([], loaded["evidence_refs"])

    def test_status_report_rejects_mixed_sections_and_non_authoritative_success(self) -> None:
        evidence = self.evidence()
        results = evaluate_context_guarantees(self.matrix, self.candidate, evidence)
        report = {
            "report_version": "1.0",
            "matrix_version": self.matrix["matrix_version"],
            "manifest_ref": self.candidate["manifest_id"],
            "active_context": [{"source_ref": "ctx-agents", "evidence_refs": ["ev-loaded"]}],
            "active_controls": [{"source_ref": "ctl-sandbox", "evidence_refs": ["ev-sandbox-probe"]}],
            "excluded_context": [],
            "applicability_results": [{"source_ref": "ctx-agents", "decision": "add_for_task", "evidence_refs": ["ev-gate"]}],
            "lint_findings": [],
            "claim_results": results,
        }
        complete_evidence = evidence + [{"evidence_id": "ev-sandbox-probe", "evidence_type": "sandbox_probe", "result": "pass", "basis": "observed", "fields": {}}]
        validate_status_report(report, self.candidate, self.matrix, complete_evidence)

        mixed = copy.deepcopy(report)
        mixed["active_context"][0]["source_ref"] = "ctl-sandbox"
        with self.assertRaisesRegex(ContextArchitectureError, "active_context"):
            validate_status_report(mixed, self.candidate, self.matrix, complete_evidence)

        invented = copy.deepcopy(report)
        improvement = next(item for item in invented["claim_results"] if item["category"] == "context_profile_improved")
        improvement["verdict"] = "supported"
        improvement["permitted_statement"] = "관찰된 비교 범위에서 Context Profile이 기준 조건보다 개선됐다"
        with self.assertRaisesRegex(ContextArchitectureError, "authoritative"):
            validate_status_report(invented, self.candidate, self.matrix, complete_evidence)

        unresolved = copy.deepcopy(report)
        unresolved["applicability_results"][0]["evidence_refs"] = ["missing-evidence"]
        with self.assertRaisesRegex(ContextArchitectureError, "applicability_results"):
            validate_status_report(unresolved, self.candidate, self.matrix, complete_evidence)

        no_drilldown = copy.deepcopy(report)
        no_drilldown["active_context"][0]["evidence_refs"] = []
        with self.assertRaisesRegex(ContextArchitectureError, "active_context.*evidence"):
            validate_status_report(no_drilldown, self.candidate, self.matrix, complete_evidence)

    def test_comparison_plan_is_one_fixture_three_conditions_three_runs(self) -> None:
        plan = build_comparison_plan(self.package, "commit-under-review")
        self.assertEqual(9, len(plan))
        self.assertEqual({"A", "B", "C"}, {run["condition"] for run in plan})
        self.assertEqual({1, 2, 3}, {run["repetition"] for run in plan})
        self.assertEqual({"commit-under-review"}, {run["target_commit"] for run in plan})
        fixed = {
            (
                run["model"],
                run["reasoning_effort"],
                run["prompt_hash"],
                run["environment_fingerprint"],
                run["control_fingerprint"],
            )
            for run in plan
        }
        self.assertEqual(1, len(fixed))

    def test_comparison_rejects_missing_runs_changed_controls_and_invented_metrics(self) -> None:
        plan = build_comparison_plan(self.package, "commit-under-review")
        runs = []
        for specification in plan:
            runs.append(
                {
                    **specification,
                    "status": "not_run",
                    "metrics": {
                        "requirements_met": {"basis": "unobserved", "value": None},
                        "tests_passed": {"basis": "unobserved", "value": None},
                        "instruction_violations": {"basis": "unobserved", "value": None},
                        "out_of_scope_changes": {"basis": "unobserved", "value": None},
                        "tool_calls": {"basis": "unobserved", "value": None},
                        "elapsed_seconds": {"basis": "unobserved", "value": None},
                        "input_tokens": {"basis": "unobserved", "value": None},
                        "output_tokens": {"basis": "unobserved", "value": None},
                        "human_understanding": {"basis": "unobserved", "value": None},
                        "human_review_seconds": {"basis": "unobserved", "value": None},
                    },
                }
            )
        result = evaluate_comparison(self.package, runs)
        self.assertEqual("not_evaluated", result["improvement_verdict"])

        with self.assertRaisesRegex(ContextArchitectureError, "exactly 9"):
            evaluate_comparison(self.package, runs[:-1])

        changed = copy.deepcopy(runs)
        changed[0]["control_fingerprint"] = "sha256:different"
        with self.assertRaisesRegex(ContextArchitectureError, "control"):
            evaluate_comparison(self.package, changed)

        changed = copy.deepcopy(runs)
        changed[0]["context_fingerprint"] = changed[2]["context_fingerprint"]
        with self.assertRaisesRegex(ContextArchitectureError, "context fingerprint"):
            evaluate_comparison(self.package, changed)

        invented = copy.deepcopy(runs)
        invented[0]["metrics"]["input_tokens"] = {"basis": "unobserved", "value": 123}
        with self.assertRaisesRegex(ContextArchitectureError, "unobserved"):
            evaluate_comparison(self.package, invented)

        invented = copy.deepcopy(runs)
        invented[0]["metrics"]["human_review_seconds"] = {"basis": "observed", "value": 0}
        with self.assertRaisesRegex(ContextArchitectureError, "human review"):
            evaluate_comparison(self.package, invented)

    def completed_runs(self, overrides: dict[str, list[tuple[bool, bool, int, int]]] | None = None) -> list[dict]:
        values = overrides or {
            condition: [(True, True, 0, 0)] * 3 for condition in "ABC"
        }
        runs = []
        for specification in build_comparison_plan(self.package, "commit-under-review"):
            requirements, tests, violations, out_of_scope = values[specification["condition"]][specification["repetition"] - 1]
            observed = lambda value: {"basis": "observed", "value": value, "receipt_ref": "run-receipt"}
            runs.append({
                **specification,
                "status": "completed",
                "metrics": {
                    "requirements_met": observed(requirements),
                    "tests_passed": observed(tests),
                    "instruction_violations": observed(violations),
                    "out_of_scope_changes": observed(out_of_scope),
                    "tool_calls": {"basis": "unobserved", "value": None},
                    "elapsed_seconds": observed(1.0),
                    "input_tokens": {"basis": "unobserved", "value": None},
                    "output_tokens": {"basis": "unobserved", "value": None},
                    "human_understanding": {"basis": "unobserved", "value": None},
                    "human_review_seconds": {"basis": "unobserved", "value": None},
                },
            })
        return runs

    def test_observed_machine_metrics_produce_no_improvement_result(self) -> None:
        result = evaluate_comparison(self.package, self.completed_runs())
        self.assertEqual("no_improvement", result["improvement_verdict"])
        self.assertEqual([], result["recommended_conditions"])
        self.assertIn("human", " ".join(result["residual_risks"]))

    def test_non_regressing_machine_improvement_can_recommend_b_without_human_metrics(self) -> None:
        result = evaluate_comparison(
            self.package,
            self.completed_runs({
                "A": [(False, False, 1, 1), (True, True, 0, 0), (True, True, 0, 0)],
                "B": [(True, True, 0, 0)] * 3,
                "C": [(True, True, 2, 0)] * 3,
            }),
        )
        self.assertEqual("recommended", result["improvement_verdict"])
        self.assertEqual(["B"], result["recommended_conditions"])
        self.assertEqual("unobserved", result["human_metrics_basis"])

    def test_failed_terminal_run_counts_in_fixed_sample_without_retry(self) -> None:
        runs = self.completed_runs()
        failed = next(run for run in runs if run["condition"] == "B")
        failed["status"] = "failed"
        failed["metrics"]["requirements_met"]["value"] = False
        failed["metrics"]["tests_passed"]["value"] = False
        failed["metrics"]["instruction_violations"]["value"] = 1
        result = evaluate_comparison(self.package, runs)
        self.assertEqual("no_improvement", result["improvement_verdict"])
        self.assertEqual(9, result["terminal_run_count"])
        self.assertEqual(1, result["failure_counts"]["failed"])

    def test_comparison_rejects_crossover_order_swap_with_balanced_pairs(self) -> None:
        runs = self.completed_runs()
        first, second = runs[0], runs[1]
        first["condition"], second["condition"] = second["condition"], first["condition"]
        first["context_fingerprint"], second["context_fingerprint"] = (
            second["context_fingerprint"],
            first["context_fingerprint"],
        )
        with self.assertRaisesRegex(ContextArchitectureError, "fixed comparison plan"):
            evaluate_comparison(self.package, runs)


class ContextArchitectureCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "devharness", *arguments],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_comparison_plan_command_emits_nine_fixed_runs(self) -> None:
        result = self.run_cli(
            "m15-comparison-plan",
            "--package",
            str(PACKAGE),
            "--target-commit",
            "commit-under-review",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(9, len(plan))
        self.assertEqual({"gpt-5.6-sol"}, {item["model"] for item in plan})
        self.assertEqual({"medium"}, {item["reasoning_effort"] for item in plan})

    def test_lint_command_emits_json_and_never_changes_the_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents = root / "AGENTS.md"
            original = "Read `missing.md` before work.\n"
            agents.write_text(original, encoding="utf-8")
            sources = root / "sources.json"
            sources.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "agents",
                            "source_type": "agents_instruction",
                            "path": "AGENTS.md",
                            "scope": "project",
                            "placement": "always_loaded",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_cli(
                "m15-context-lint", "--root", str(root), "--sources", str(sources)
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("stale_reference", json.loads(result.stdout)["findings"][0]["rule_id"])
            self.assertEqual(original, agents.read_text(encoding="utf-8"))

    def test_invalid_comparison_input_returns_nonzero(self) -> None:
        result = self.run_cli(
            "m15-comparison-plan", "--package", str(PACKAGE), "--target-commit", ""
        )
        self.assertNotEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main()

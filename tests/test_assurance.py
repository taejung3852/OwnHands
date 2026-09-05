from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from devharness.assurance import (
    AssuranceError,
    analyze_impact,
    build_assurance_packet,
    build_test_design,
    canonical_json,
    capture_restore_point,
    compare_test_runs,
    detect_test_gaps,
    evaluate_regression_gate,
    fingerprint,
    record_test_baseline,
    verify_restore_point,
)
from devharness.control_profile import build_execution_contract


NOW = "2026-09-06T12:00:00+00:00"
HASH_A = "sha256:" + "a" * 64
FIXTURES = Path(__file__).parent / "fixtures" / "m4"
RELATIONS = json.loads((FIXTURES / "relation-catalog.json").read_text(encoding="utf-8"))
ATTACKS = json.loads((FIXTURES / "adversarial-cases.json").read_text(encoding="utf-8"))


def git(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        input=input_bytes,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def disposable_repository(root: Path) -> Path:
    repository = root / "repository"
    repository.mkdir()
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "fixture@example.invalid")
    git(repository, "config", "user.name", "M4 Fixture")
    sources = {
        "REQUIREMENTS.md": "# Widget\n\nNormalize a widget and preserve schema errors.\n",
        "src/widget.py": "def normalize(value):\n    return value.strip()\n",
        "schema/widget.schema.json": '{"type":"string"}\n',
        "tests/test_widget.py": "def test_widget():\n    assert True\n",
    }
    for relative, content in sources.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "fixture start")
    (repository / "src/widget.py").write_text(
        "def normalize(value):\n    if not isinstance(value, str):\n        raise TypeError('value')\n    return value.strip().lower()\n",
        encoding="utf-8",
    )
    (repository / "schema/widget.schema.json").write_text(
        '{"type":"string","minLength":1}\n', encoding="utf-8"
    )
    (repository / "tests/test_widget.py").write_text(
        "def test_widget():\n    assert True\n\ndef test_error():\n    assert True\n",
        encoding="utf-8",
    )
    (repository / "REQUIREMENTS.md").write_text(
        "# Widget\n\nNormalize case and preserve schema errors.\n", encoding="utf-8"
    )
    (repository / "untracked-secret.txt").write_text("must stay outside restore\n")
    return repository


def contract() -> dict:
    draft = {
        "impact_hypotheses": [
            {
                "hypothesis_id": "impact:widget",
                "path_globs": ["src/widget.py", "schema/*.json"],
                "relation_refs": [
                    "relation:widget-regression-test",
                    "relation:schema-error-test",
                ],
                "basis": "declared",
            }
        ],
        "tests": [
            {
                "test_id": "test:widget-regression",
                "subject_ref": "subject:widget-runtime",
                "command": "python -m unittest tests.test_widget",
                "selection_scope": "tests.test_widget",
                "classification": "regression",
                "code_refs": ["tests/test_widget.py"],
            },
            {
                "test_id": "test:schema-errors",
                "subject_ref": "subject:widget-schema",
                "command": "python -m unittest tests.test_schema",
                "selection_scope": "tests.test_schema",
                "classification": "new_feature",
                "code_refs": ["tests/test_schema.py"],
            },
        ],
        "mappings": [
            {
                "criterion_id": "tests_pass",
                "test_ids": ["test:widget-regression"],
                "viewpoints": ["regression", "recovery"],
                "reason": "existing behavior can regress",
            },
            {
                "criterion_id": "schema_compatible",
                "test_ids": ["test:schema-errors"],
                "viewpoints": ["error"],
                "reason": "schema errors define the new boundary",
            },
        ],
        "criteria": [
            {"criterion_id": "tests_pass", "block_level": "hard"},
            {"criterion_id": "schema_compatible", "block_level": "hard"},
        ],
    }
    result = {
        "contract_version": "1.1",
        "contract_id": "contract:task-m4",
        "task": {
            "project_id": "project-ownhands",
            "worktree_id": "worktree-m4",
            "environment_ref": "macos-arm64-python-3.12",
            "task_id": "task-m4",
            "mode": "managed",
            "goal": "verify the assurance pipeline",
        },
        "protected_targets": [".env", ".git/**"],
        "validation_criteria": [
            "python -m unittest tests.test_widget",
            "python -m unittest tests.test_schema",
        ],
        "gate_criteria": ["tests_pass", "schema_compatible"],
        "assurance_draft": draft,
    }
    result["fingerprint"] = fingerprint(result)
    return result


def receipt(
    test_id: str,
    *,
    criterion_id: str,
    classification: str,
    result: str = "pass",
    command_fingerprint: str | None = None,
    environment_fingerprint: str = "sha256:" + "b" * 64,
    contract_fingerprint: str | None = None,
    start_patch_hash: str = "sha256:" + "c" * 64,
    target_patch_hash: str = "sha256:" + "d" * 64,
) -> dict:
    if test_id == "test:widget-regression":
        command = "python -m unittest tests.test_widget"
        selection_scope = "tests.test_widget"
        code_refs = ["tests/test_widget.py"]
        subject_ref = "subject:widget-runtime"
    else:
        command = "python -m unittest tests.test_schema"
        selection_scope = "tests.test_schema"
        code_refs = ["tests/test_schema.py"]
        subject_ref = "subject:widget-schema"
    return {
        "test_id": test_id,
        "subject_ref": subject_ref,
        "criterion_id": criterion_id,
        "classification": classification,
        "validation_command": command,
        "command_fingerprint": command_fingerprint or fingerprint({"command": command}),
        "selection_scope": selection_scope,
        "environment_fingerprint": environment_fingerprint,
        "contract_fingerprint": contract_fingerprint or contract()["fingerprint"],
        "start_patch_hash": start_patch_hash,
        "target_patch_hash": target_patch_hash,
        "code_refs": code_refs,
        "result": result,
        "basis": "observed" if result not in {"missing", "not_run"} else "unobserved",
        "evidence_refs": [] if result in {"missing", "not_run"} else [f"evidence:{test_id}:run"],
        "conflict_refs": [],
    }


def requirement_catalog() -> list[dict]:
    return [
        {
            "criterion_id": "tests_pass",
            "required_viewpoints": ["regression", "recovery"],
            "test_ids": ["test:widget-regression"],
        },
        {
            "criterion_id": "schema_compatible",
            "required_viewpoints": ["error"],
            "test_ids": ["test:schema-errors"],
        },
    ]


class AssuranceTests(unittest.TestCase):
    def test_canonical_identity_and_unique_lists_fail_closed(self) -> None:
        self.assertEqual('{"a":1,"b":2}', canonical_json({"b": 2, "a": 1}))
        duplicate = contract()
        duplicate["gate_criteria"] = ["tests_pass", "tests_pass"]
        with self.assertRaisesRegex(AssuranceError, "duplicate"):
            build_test_design(duplicate, {"relations": []}, requirement_catalog())
        unknown = contract()
        unknown["gate_criteria"] = ["tests_pass", "unknown"]
        unknown["fingerprint"] = fingerprint({key: value for key, value in unknown.items() if key != "fingerprint"})
        with self.assertRaisesRegex(AssuranceError, "unknown"):
            build_test_design(unknown, {"relations": []}, requirement_catalog())

    def test_restore_capture_reconstructs_tracked_patch_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = disposable_repository(Path(temporary))
            status_before = git(repository, "status", "--porcelain=v1", "-z")
            restore = capture_restore_point(repository, contract()["task"], NOW)
            verification = verify_restore_point(repository, restore)
            status_after = git(repository, "status", "--porcelain=v1", "-z")
            self.assertEqual("pass", verification["result"])
            self.assertEqual("observed", verification["basis"])
            self.assertEqual(restore["tracked_patch_hash"], verification["reconstructed_patch_hash"])
            self.assertEqual(status_before, status_after)
            self.assertEqual(
                {"untracked_content", "submodules", "symbolic_links"},
                {item["area"] for item in restore["exclusions"]},
            )
            self.assertNotIn("untracked-secret", canonical_json(verification))

    def test_restore_reconstructs_intent_to_add_files_in_captured_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = disposable_repository(Path(temporary))
            added = repository / "src/new_widget.py"
            added.write_text("VALUE = 'new'\n", encoding="utf-8")
            git(repository, "add", "-N", "src/new_widget.py")
            restore = capture_restore_point(repository, contract()["task"], NOW)
            verification = verify_restore_point(repository, restore)
            self.assertEqual("pass", verification["result"])
            self.assertEqual(restore["tracked_patch_hash"], verification["reconstructed_patch_hash"])

    def test_restore_reconstructs_from_a_detached_head_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = disposable_repository(Path(temporary))
            git(repository, "checkout", "--detach", "--quiet", "HEAD")
            restore = capture_restore_point(repository, contract()["task"], NOW)
            verification = verify_restore_point(repository, restore)
            self.assertEqual("pass", verification["result"])
            self.assertEqual(restore["tracked_patch_hash"], verification["reconstructed_patch_hash"])

    def test_actual_diff_joins_only_declared_relations_and_records_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = disposable_repository(Path(temporary))
            restore = capture_restore_point(repository, contract()["task"], NOW)
            impact = analyze_impact(repository, restore, contract(), RELATIONS, NOW)
            self.assertEqual(
                {"REQUIREMENTS.md", "schema/widget.schema.json", "src/widget.py", "tests/test_widget.py"},
                {item["path"] for item in impact["changed_paths"]},
            )
            self.assertEqual(
                {item["relation_id"] for item in RELATIONS["relations"]},
                {item["relation_id"] for item in impact["relations"]},
            )
            self.assertIn("python_dynamic_imports", {item["area"] for item in impact["unobserved"]})
            self.assertTrue({"untracked_content", "external_services"} <= {item["area"] for item in impact["exclusions"]})
            self.assertFalse(impact["claims_complete_dependency_analysis"])

    def test_test_design_uses_contract_draft_classification_and_viewpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = disposable_repository(Path(temporary))
            restore = capture_restore_point(repository, contract()["task"], NOW)
            impact = analyze_impact(repository, restore, contract(), RELATIONS, NOW)
            design = build_test_design(contract(), impact, requirement_catalog())
            mapped = {item["criterion_id"]: item for item in design["mappings"]}
            self.assertEqual("regression", mapped["tests_pass"]["tests"][0]["classification"])
            self.assertEqual("new_feature", mapped["schema_compatible"]["tests"][0]["classification"])
            self.assertEqual(["regression", "recovery"], mapped["tests_pass"]["selected_viewpoints"])
            self.assertEqual([], mapped["tests_pass"]["omitted_viewpoints"])

    def test_execution_contract_binds_minimum_assurance_draft_into_fingerprint(self) -> None:
        baseline = {
            "baseline_id": "baseline:p:v1", "fingerprint": HASH_A,
            "project_id": "p", "worktree_id": "w", "environment_ref": "e",
            "sources": [], "event_refs": [], "evidence_refs": [],
        }
        overlay = {
            "overlay_id": "overlay", "baseline_ref": "baseline:p:v1", "baseline_fingerprint": HASH_A,
            "task": {"project_id": "p", "worktree_id": "w", "environment_ref": "e", "task_id": "t", "mode": "managed", "goal": "g"},
            "instruction_overlay": {"source_refs": []}, "control_overlay": {"source_refs": []},
            "writable_paths": ["src/**"], "protected_targets": [".git/**"],
            "permission_expansions": [], "approval_triggers": [],
            "validation_criteria": ["python -m unittest"], "gate_criteria": ["tests_pass"],
            "unobserved_paths": [],
            "assurance_draft": {
                "impact_hypotheses": [],
                "tests": [{"test_id": "test:all", "subject_ref": "subject:all", "command": "python -m unittest", "selection_scope": "tests", "classification": "regression", "code_refs": ["tests/"]}],
                "mappings": [{"criterion_id": "tests_pass", "test_ids": ["test:all"], "viewpoints": ["regression"], "reason": "existing suite"}],
                "criteria": [{"criterion_id": "tests_pass", "block_level": "hard"}],
            },
        }
        first = build_execution_contract(baseline, overlay, [], now=NOW)
        changed = copy.deepcopy(overlay)
        changed["assurance_draft"]["criteria"][0]["block_level"] = "soft"
        second = build_execution_contract(baseline, changed, [], now=NOW)
        self.assertIn("assurance_draft", first)
        self.assertEqual("1.1", first["contract_version"])
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])

    def test_legacy_v10_contract_is_read_compatible_but_cannot_enter_m4(self) -> None:
        legacy = contract()
        legacy["contract_version"] = "1.0"
        legacy.pop("assurance_draft")
        legacy["fingerprint"] = fingerprint({key: value for key, value in legacy.items() if key != "fingerprint"})
        with self.assertRaisesRegex(AssuranceError, "v1.0.*M4"):
            build_test_design(legacy, {"relations": []}, requirement_catalog())

    def test_receipts_require_exact_selection_and_observed_evidence(self) -> None:
        selected = contract()["assurance_draft"]["tests"]
        receipts = [
            receipt("test:widget-regression", criterion_id="tests_pass", classification="regression"),
            receipt("test:schema-errors", criterion_id="schema_compatible", classification="new_feature"),
        ]
        run = record_test_baseline(contract(), selected, receipts, NOW)
        self.assertEqual({"test:widget-regression", "test:schema-errors"}, {item["test_id"] for item in run["receipts"]})
        with self.assertRaisesRegex(AssuranceError, "exact test selection"):
            record_test_baseline(contract(), selected, receipts[:1], NOW)
        forged = copy.deepcopy(receipts)
        forged[0]["evidence_refs"] = []
        with self.assertRaisesRegex(AssuranceError, "observed.*Evidence"):
            record_test_baseline(contract(), selected, forged, NOW)

    def test_receipts_bind_exact_contract_assignment_and_reject_raw_fields(self) -> None:
        selected = contract()["assurance_draft"]["tests"]
        swapped = [
            receipt("test:widget-regression", criterion_id="schema_compatible", classification="regression"),
            receipt("test:schema-errors", criterion_id="tests_pass", classification="new_feature"),
        ]
        with self.assertRaisesRegex(AssuranceError, "criterion_id.*mapping"):
            record_test_baseline(contract(), selected, swapped, NOW)
        leaked = [
            receipt("test:widget-regression", criterion_id="tests_pass", classification="regression"),
            receipt("test:schema-errors", criterion_id="schema_compatible", classification="new_feature"),
        ]
        leaked[0]["raw_output"] = "SECRET_RAW_SENTINEL"
        with self.assertRaisesRegex(AssuranceError, "unexpected.*raw_output"):
            record_test_baseline(contract(), selected, leaked, NOW)

    def test_before_after_comparison_binds_meaning_environment_contract_and_patch_hashes(self) -> None:
        selected = contract()["assurance_draft"]["tests"]
        before_receipts = [
            receipt("test:widget-regression", criterion_id="tests_pass", classification="regression"),
            receipt("test:schema-errors", criterion_id="schema_compatible", classification="new_feature"),
        ]
        before = record_test_baseline(contract(), selected, before_receipts, NOW)
        after = record_test_baseline(contract(), selected, copy.deepcopy(before_receipts), NOW)
        self.assertTrue(all(item["status"] == "comparable_pass" for item in compare_test_runs(before, after)["comparisons"]))
        mutations = {
            "command_fingerprint": "incomparable",
            "selection_scope": "stale",
            "environment_fingerprint": "incomparable",
            "contract_fingerprint": "stale",
            "start_patch_hash": "stale",
            "target_patch_hash": "stale",
        }
        for key, expected in mutations.items():
            with self.subTest(key=key):
                changed = copy.deepcopy(after)
                target = next(item for item in changed["receipts"] if item["test_id"] == "test:widget-regression")
                target[key] = "sha256:" + "e" * 64 if key.endswith("fingerprint") or key.endswith("hash") else "different"
                comparison = compare_test_runs(before, changed)
                indexed = {item["test_id"]: item for item in comparison["comparisons"]}
                self.assertEqual(expected, indexed["test:widget-regression"]["status"])

    def test_comparison_never_turns_missing_failure_or_conflict_into_pass(self) -> None:
        selected = contract()["assurance_draft"]["tests"]
        good = [
            receipt("test:widget-regression", criterion_id="tests_pass", classification="regression"),
            receipt("test:schema-errors", criterion_id="schema_compatible", classification="new_feature"),
        ]
        before = record_test_baseline(contract(), selected, good, NOW)
        cases = {"missing": "missing_after", "not_run": "not_run", "inconclusive": "inconclusive", "fail": "regression"}
        for result, expected in cases.items():
            with self.subTest(result=result):
                after_receipts = copy.deepcopy(good)
                after_receipts[0] = receipt("test:widget-regression", criterion_id="tests_pass", classification="regression", result=result)
                after = record_test_baseline(contract(), selected, after_receipts, NOW)
                indexed = {item["test_id"]: item for item in compare_test_runs(before, after)["comparisons"]}
                self.assertEqual(expected, indexed["test:widget-regression"]["status"])
        conflicted = copy.deepcopy(good)
        conflicted[0]["conflict_refs"] = ["evidence:conflict"]
        after = record_test_baseline(contract(), selected, conflicted, NOW)
        indexed = {item["test_id"]: item for item in compare_test_runs(before, after)["comparisons"]}
        self.assertEqual("contradicted", indexed["test:widget-regression"]["status"])

    def test_comparison_classifies_all_observed_pass_fail_transitions(self) -> None:
        selected = contract()["assurance_draft"]["tests"]
        expected = {
            ("pass", "pass"): "comparable_pass",
            ("fail", "pass"): "fixed_failure",
            ("fail", "fail"): "unchanged_failure",
            ("pass", "fail"): "regression",
        }
        for transition, status in expected.items():
            with self.subTest(transition=transition):
                before_receipts = [
                    receipt("test:widget-regression", criterion_id="tests_pass", classification="regression", result=transition[0]),
                    receipt("test:schema-errors", criterion_id="schema_compatible", classification="new_feature"),
                ]
                after_receipts = copy.deepcopy(before_receipts)
                after_receipts[0] = receipt("test:widget-regression", criterion_id="tests_pass", classification="regression", result=transition[1])
                before = record_test_baseline(contract(), selected, before_receipts, NOW)
                after = record_test_baseline(contract(), selected, after_receipts, NOW)
                indexed = {item["test_id"]: item for item in compare_test_runs(before, after)["comparisons"]}
                self.assertEqual(status, indexed["test:widget-regression"]["status"])

    def test_gap_detection_reports_no_adequate_test_and_wrong_classification(self) -> None:
        impact = {
            "relations": [
                {"relation_id": "relation:required-regression", "relation_type": "test", "target_ref": "test:widget-regression", "required_classification": "regression", "basis": "declared", "evidence_refs": []},
                {"relation_id": "relation:missing-test", "relation_type": "test", "target_ref": "test:not-selected", "required_classification": "regression", "basis": "declared", "evidence_refs": []},
            ],
            "unobserved": [], "protected_target_changes": [],
        }
        design = build_test_design(contract(), impact, requirement_catalog())
        wrong = copy.deepcopy(design)
        wrong["selected_tests"][0]["classification"] = "new_feature"
        comparison = {"comparisons": []}
        gaps = detect_test_gaps(contract(), impact, wrong, comparison)
        kinds = {item["kind"] for item in gaps["gaps"]}
        self.assertIn("wrong_test_classification", kinds)
        self.assertIn("no_adequate_test", kinds)

    def test_gate_hard_blocks_required_gap_and_rejects_any_override(self) -> None:
        impact = {"unobserved": [], "protected_target_changes": []}
        design = {"mappings": [], "selected_tests": []}
        comparison = {"comparisons": []}
        gaps = {"gaps": [{"gap_id": "gap:1", "kind": "no_adequate_test", "required": True, "criterion_id": "tests_pass", "reason": "none"}]}
        gate = evaluate_regression_gate(contract(), impact, design, comparison, gaps, ATTACKS["user_delegation_override"])
        self.assertEqual("hard_block", gate["decision"])
        self.assertEqual("rejected", gate["override"]["status"])

    def test_gate_independently_blocks_omitted_or_swapped_contract_criteria(self) -> None:
        impact = {"unobserved": [], "protected_target_changes": []}
        design = build_test_design(contract(), {"relations": [], "unobserved": []}, requirement_catalog())
        only_one = {
            "comparisons": [
                {"test_id": "test:widget-regression", "criterion_id": "tests_pass", "classification": "regression", "status": "comparable_pass", "evidence_refs": []}
            ]
        }
        omitted = evaluate_regression_gate(contract(), impact, design, only_one, {"gaps": []})
        self.assertEqual("hard_block", omitted["decision"])
        self.assertTrue(any("schema_compatible" in reason for reason in omitted["hard_reasons"]))
        swapped = copy.deepcopy(only_one)
        swapped["comparisons"][0]["criterion_id"] = "schema_compatible"
        result = evaluate_regression_gate(contract(), impact, design, swapped, {"gaps": []})
        self.assertEqual("hard_block", result["decision"])

    def test_public_gate_hard_blocks_coordinated_contract_mapping_swap_and_rejects_override(self) -> None:
        current = contract()
        impact = {"unobserved": [], "protected_target_changes": []}
        design = build_test_design(current, {"relations": [], "unobserved": []}, requirement_catalog())
        design["mappings"][0]["tests"], design["mappings"][1]["tests"] = (
            design["mappings"][1]["tests"],
            design["mappings"][0]["tests"],
        )
        design["fingerprint"] = fingerprint({key: value for key, value in design.items() if key != "fingerprint"})
        comparison = {
            "comparisons": [
                {"test_id": "test:widget-regression", "criterion_id": "schema_compatible", "classification": "regression", "status": "comparable_pass", "evidence_refs": []},
                {"test_id": "test:schema-errors", "criterion_id": "tests_pass", "classification": "new_feature", "status": "comparable_pass", "evidence_refs": []},
            ]
        }
        approval = copy.deepcopy(ATTACKS["wrong_scope_override"])
        approval["decision_scope"] = {
            "contract_id": current["contract_id"],
            "contract_fingerprint": current["fingerprint"],
            "decision": "soft_block_override",
        }
        gate = evaluate_regression_gate(current, impact, design, comparison, {"gaps": []}, approval)
        self.assertEqual("hard_block", gate["decision"])
        self.assertEqual("rejected", gate["override"]["status"])

    def test_fixed_failure_is_adequate_only_for_new_feature_classification(self) -> None:
        for classification, expected_gap, expected_gate in (
            ("regression", True, "hard_block"),
            ("new_feature", False, "pass"),
        ):
            with self.subTest(classification=classification):
                current = contract()
                test = copy.deepcopy(current["assurance_draft"]["tests"][0])
                test["classification"] = classification
                current["assurance_draft"]["tests"] = [test]
                current["assurance_draft"]["mappings"] = [{
                    "criterion_id": "tests_pass", "test_ids": [test["test_id"]],
                    "viewpoints": [classification], "reason": "single exact transition",
                }]
                current["assurance_draft"]["criteria"] = [{"criterion_id": "tests_pass", "block_level": "hard"}]
                current["gate_criteria"] = ["tests_pass"]
                current["validation_criteria"] = [test["command"]]
                current["fingerprint"] = fingerprint({key: value for key, value in current.items() if key != "fingerprint"})
                before_receipt = receipt(
                    test["test_id"], criterion_id="tests_pass", classification=classification,
                    result="fail", contract_fingerprint=current["fingerprint"],
                )
                after_receipt = receipt(
                    test["test_id"], criterion_id="tests_pass", classification=classification,
                    result="pass", contract_fingerprint=current["fingerprint"],
                )
                before = record_test_baseline(current, [test], [before_receipt], NOW)
                after = record_test_baseline(current, [test], [after_receipt], NOW)
                comparison = compare_test_runs(before, after)
                self.assertEqual("fixed_failure", comparison["comparisons"][0]["status"])
                impact = {"relations": [], "unobserved": [], "protected_target_changes": []}
                design = build_test_design(
                    current,
                    impact,
                    [{"criterion_id": "tests_pass", "required_viewpoints": [classification], "test_ids": [test["test_id"]]}],
                )
                gaps = detect_test_gaps(current, impact, design, comparison)
                self.assertEqual(expected_gap, any(item["kind"] == "no_adequate_test" for item in gaps["gaps"]))
                self.assertEqual(expected_gate, evaluate_regression_gate(current, impact, design, comparison, gaps)["decision"])

    def test_soft_block_override_requires_exact_product_authority_and_audit_fields(self) -> None:
        impact = {"unobserved": [{"area": "dynamic_runtime_relationships", "reason": "bounded v1"}], "protected_target_changes": []}
        design = build_test_design(contract(), {"relations": [], "unobserved": []}, requirement_catalog())
        comparisons = {
            "comparisons": [
                {"test_id": "test:widget-regression", "criterion_id": "tests_pass", "classification": "regression", "status": "comparable_pass", "evidence_refs": ["evidence:test:widget-regression:run"]},
                {"test_id": "test:schema-errors", "criterion_id": "schema_compatible", "classification": "new_feature", "status": "comparable_pass", "evidence_refs": ["evidence:test:schema-errors:run"]},
            ]
        }
        gaps = {"gaps": []}
        rejected = evaluate_regression_gate(contract(), impact, design, comparisons, gaps, ATTACKS["user_delegation_override"])
        self.assertEqual("soft_block", rejected["decision"])
        self.assertEqual("rejected", rejected["override"]["status"])
        rejected_scope = evaluate_regression_gate(contract(), impact, design, comparisons, gaps, ATTACKS["wrong_scope_override"])
        self.assertEqual("soft_block", rejected_scope["decision"])
        approval = copy.deepcopy(ATTACKS["wrong_scope_override"])
        approval["decision_scope"] = {
            "contract_id": contract()["contract_id"],
            "contract_fingerprint": contract()["fingerprint"],
            "decision": "soft_block_override",
        }
        accepted = evaluate_regression_gate(contract(), impact, design, comparisons, gaps, approval)
        self.assertEqual("pass", accepted["decision"])
        self.assertEqual("accepted", accepted["override"]["status"])
        self.assertEqual("explicit_product_approval", accepted["override"]["decision_source"])

    def test_execution_contract_keeps_missing_draft_as_legacy_v10_and_explicit_draft_as_v11(self) -> None:
        baseline = {
            "baseline_id": "baseline:p:v1", "fingerprint": HASH_A,
            "project_id": "p", "worktree_id": "w", "environment_ref": "e",
            "sources": [], "event_refs": [], "evidence_refs": [],
        }
        overlay = {
            "overlay_id": "overlay", "baseline_ref": "baseline:p:v1", "baseline_fingerprint": HASH_A,
            "task": {"project_id": "p", "worktree_id": "w", "environment_ref": "e", "task_id": "t", "mode": "managed", "goal": "g"},
            "instruction_overlay": {"source_refs": []}, "control_overlay": {"source_refs": []},
            "writable_paths": ["src/**"], "protected_targets": [".git/**"],
            "permission_expansions": [], "approval_triggers": [],
            "validation_criteria": ["python -m unittest"], "gate_criteria": ["tests_pass"],
            "unobserved_paths": [],
        }
        legacy = build_execution_contract(baseline, overlay, [], now=NOW)
        self.assertEqual("1.0", legacy["contract_version"])
        self.assertNotIn("assurance_draft", legacy)
        with self.assertRaisesRegex(AssuranceError, "v1.0.*M4"):
            build_test_design(legacy, {"relations": []}, [])
        explicit = copy.deepcopy(overlay)
        explicit["assurance_draft"] = {
            "impact_hypotheses": [],
            "tests": [{"test_id": "test:all", "subject_ref": "subject:all", "command": "python -m unittest", "selection_scope": "tests", "classification": "regression", "code_refs": ["tests/"]}],
            "mappings": [{"criterion_id": "tests_pass", "test_ids": ["test:all"], "viewpoints": ["regression"], "reason": "explicit suite"}],
            "criteria": [{"criterion_id": "tests_pass", "block_level": "hard"}],
        }
        current = build_execution_contract(baseline, explicit, [], now=NOW)
        self.assertEqual("1.1", current["contract_version"])
        self.assertIn("assurance_draft", current)

    def test_packet_reference_closure_and_deterministic_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = disposable_repository(Path(temporary))
            c = contract()
            restore = capture_restore_point(repository, c["task"], NOW)
            verification = verify_restore_point(repository, restore)
            impact = analyze_impact(repository, restore, c, RELATIONS, NOW)
            design = build_test_design(c, impact, requirement_catalog())
            selected = c["assurance_draft"]["tests"]
            receipts = [
                receipt("test:widget-regression", criterion_id="tests_pass", classification="regression", start_patch_hash=restore["start_patch_hash"], target_patch_hash=restore["tracked_patch_hash"]),
                receipt("test:schema-errors", criterion_id="schema_compatible", classification="new_feature", start_patch_hash=restore["start_patch_hash"], target_patch_hash=restore["tracked_patch_hash"]),
            ]
            before = record_test_baseline(c, selected, receipts, NOW)
            after = record_test_baseline(c, selected, copy.deepcopy(receipts), NOW)
            comparison = compare_test_runs(before, after)
            gaps = detect_test_gaps(c, impact, design, comparison)
            gate = evaluate_regression_gate(c, impact, design, comparison, gaps)
            evidence_refs = sorted({ref for item in receipts for ref in item["evidence_refs"]} | {ref for item in impact["relations"] for ref in item["evidence_refs"]})
            arguments = dict(
                contract=c, restore_point=restore, restore_verification=verification,
                impact=impact, test_design=design, before=before, after=after,
                comparison=comparison, gaps=gaps, gate=gate,
                evidence_refs=evidence_refs, observed_at=NOW,
            )
            first = build_assurance_packet(**arguments)
            second = build_assurance_packet(**arguments)
            self.assertEqual(first, second)
            self.assertEqual("1.0", first["packet_version"])
            self.assertNotIn("_tracked_patch", canonical_json(first))
            broken = copy.deepcopy(arguments)
            broken["evidence_refs"] = []
            with self.assertRaisesRegex(AssuranceError, "reference closure"):
                build_assurance_packet(**broken)
            dangling = copy.deepcopy(arguments)
            dangling["evidence_refs"] = evidence_refs + ["evidence:unused"]
            with self.assertRaisesRegex(AssuranceError, "reference closure"):
                build_assurance_packet(**dangling)
            failed_restore = copy.deepcopy(arguments)
            failed_restore["restore_verification"]["result"] = "fail"
            with self.assertRaisesRegex(AssuranceError, "Restore verification"):
                build_assurance_packet(**failed_restore)
            stale_after = copy.deepcopy(arguments)
            stale_after["after"]["receipts"][0]["result"] = "fail"
            with self.assertRaisesRegex(AssuranceError, "after.*fingerprint"):
                build_assurance_packet(**stale_after)
            wrong_after_ref = copy.deepcopy(arguments)
            wrong_after_ref["comparison"]["after_ref"] = HASH_A
            wrong_after_ref["comparison"]["fingerprint"] = fingerprint({key: value for key, value in wrong_after_ref["comparison"].items() if key != "fingerprint"})
            with self.assertRaisesRegex(AssuranceError, "comparison"):
                build_assurance_packet(**wrong_after_ref)
            forged_gate = copy.deepcopy(arguments)
            forged_gate["gate"]["decision"] = "pass"
            forged_gate["gate"]["initial_decision"] = "pass"
            forged_gate["gate"]["soft_reasons"] = []
            forged_gate["gate"]["basis"] = "observed"
            forged_gate["gate"]["fingerprint"] = fingerprint({key: value for key, value in forged_gate["gate"].items() if key != "fingerprint"})
            with self.assertRaisesRegex(AssuranceError, "Gate.*authoritative"):
                build_assurance_packet(**forged_gate)


if __name__ == "__main__":
    unittest.main()

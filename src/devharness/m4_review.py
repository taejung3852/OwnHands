from __future__ import annotations

import copy
import html
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .assurance import (
    analyze_impact,
    build_assurance_packet,
    build_test_design,
    capture_restore_point,
    compare_test_runs,
    detect_test_gaps,
    evaluate_regression_gate,
    fingerprint,
    record_test_baseline,
    validate_assurance_packet,
    verify_restore_point,
)
from .dashboard_security import private_atomic_write


class M4ReviewError(ValueError):
    pass


PACKET_FIELDS = {
    "packet_version",
    "packet_id",
    "contract_id",
    "contract_fingerprint",
    "contract_snapshot",
    "task",
    "observed_at",
    "input_fingerprint",
    "restore_point",
    "restore_verification",
    "impact",
    "test_design",
    "before",
    "after",
    "comparison",
    "gaps",
    "gate",
    "evidence_refs",
    "fingerprint",
}


def _is_hash(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _evidence_refs(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_refs":
                if not isinstance(item, list) or any(not isinstance(ref, str) or not ref for ref in item):
                    raise M4ReviewError("Evidence reference list is invalid")
                refs.update(item)
            else:
                refs.update(_evidence_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_evidence_refs(item))
    return refs


def validate_packet_document(packet: object) -> dict:
    try:
        return validate_assurance_packet(packet)
    except ValueError as error:
        raise M4ReviewError(str(error)) from error


def _write(path: Path, content: str) -> None:
    private_atomic_write(path, content)


def _run_git(repository: Path, *arguments: str) -> None:
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-09-06T12:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-09-06T12:00:00+00:00",
        }
    )
    subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )


def _fixture_repository(root: Path) -> Path:
    repository = root / "repository"
    repository.mkdir()
    _run_git(repository, "init", "-q")
    _run_git(repository, "config", "user.email", "fixture@example.invalid")
    _run_git(repository, "config", "user.name", "M4 Fixture")
    _write(repository / "REQUIREMENTS.md", "# Widget\n\nNormalize strings while preserving observed behavior.\n")
    _write(repository / "widget.py", "def normalize(value):\n    return value.strip().lower()\n")
    _write(
        repository / "tests/test_widget.py",
        "import unittest\n\nfrom widget import normalize\n\n"
        "class WidgetTests(unittest.TestCase):\n"
        "    def test_normalizes_a_string(self):\n"
        "        self.assertEqual('hello', normalize(' Hello '))\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n",
    )
    _run_git(repository, "add", ".")
    _run_git(repository, "commit", "-qm", "fixture start")
    return repository


def _contract() -> dict:
    command = "python -m unittest discover -s tests -v"
    contract = {
        "contract_version": "1.1",
        "contract_id": "contract:m4-synthetic-review",
        "task": {
            "project_id": "project:ownhands-fixture",
            "worktree_id": "worktree:m4-fixture",
            "environment_ref": "python-3.12-local-fixture",
            "task_id": "task:m4-fixture",
            "mode": "managed",
            "goal": "Exercise the local M4 assurance review slice",
        },
        "protected_targets": [".git/**"],
        "validation_criteria": [command],
        "gate_criteria": ["tests_pass"],
        "assurance_draft": {
            "impact_hypotheses": [
                {
                    "hypothesis_id": "impact:widget",
                    "path_globs": ["widget.py"],
                    "relation_refs": ["relation:widget-test"],
                    "basis": "declared",
                }
            ],
            "tests": [
                {
                    "test_id": "test:widget-regression",
                    "subject_ref": "subject:widget-runtime",
                    "command": command,
                    "selection_scope": "tests/test_widget.py",
                    "classification": "regression",
                    "code_refs": ["tests/test_widget.py"],
                }
            ],
            "mappings": [
                {
                    "criterion_id": "tests_pass",
                    "test_ids": ["test:widget-regression"],
                    "viewpoints": ["regression", "recovery"],
                    "reason": "the existing normalization behavior must remain stable",
                }
            ],
            "criteria": [{"criterion_id": "tests_pass", "block_level": "hard"}],
        },
    }
    contract["fingerprint"] = fingerprint(contract)
    return contract


def _run_test(repository: Path) -> tuple[str, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return ("pass" if completed.returncode == 0 else "fail"), completed.stdout


def _receipt(
    contract: dict,
    result: str,
    evidence_ref: str,
    environment_fingerprint: str,
    start_patch_hash: str,
    target_patch_hash: str,
) -> dict:
    test = contract["assurance_draft"]["tests"][0]
    return {
        "test_id": test["test_id"],
        "subject_ref": test["subject_ref"],
        "criterion_id": "tests_pass",
        "classification": test["classification"],
        "validation_command": test["command"],
        "command_fingerprint": fingerprint({"command": test["command"]}),
        "selection_scope": test["selection_scope"],
        "environment_fingerprint": environment_fingerprint,
        "contract_fingerprint": contract["fingerprint"],
        "start_patch_hash": start_patch_hash,
        "target_patch_hash": target_patch_hash,
        "code_refs": test["code_refs"],
        "result": result,
        "basis": "observed",
        "evidence_refs": [evidence_ref],
        "conflict_refs": [],
    }


def render_review(packet: dict) -> str:
    validate_packet_document(packet)
    task = packet["task"]
    impact = packet["impact"]
    design = packet["test_design"]
    gaps = packet["gaps"]["gaps"]
    gate = packet["gate"]
    changed = "".join(
        f"<li><code>{html.escape(item['path'])}</code> — {html.escape(item['status'])}</li>"
        for item in impact["changed_paths"]
    ) or "<li>No tracked changes</li>"
    tests = "".join(
        f"<tr><td>{html.escape(item['test_id'])}</td><td>{html.escape(item['classification'])}</td><td>{html.escape(item['selection_scope'])}</td></tr>"
        for item in design["selected_tests"]
    )
    gap_items = "".join(
        f"<li>{html.escape(item['kind'])}: {html.escape(item['reason'])}</li>" for item in gaps
    ) or "<li>No required test gaps</li>"
    evidence = "".join(
        f'<li id="{html.escape(ref, quote=True)}"><a href="#{html.escape(ref, quote=True)}">{html.escape(ref)}</a></li>'
        for ref in packet["evidence_refs"]
    )
    hard_reasons = "".join(f"<li>{html.escape(reason)}</li>" for reason in gate["hard_reasons"]) or "<li>None</li>"
    soft_reasons = "".join(f"<li>{html.escape(reason)}</li>" for reason in gate["soft_reasons"]) or "<li>None</li>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ownhands M4 Assurance Review</title>
<style>body{{max-width:72rem;margin:2rem auto;padding:0 1rem;font:16px/1.5 system-ui}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid;padding:.5rem;text-align:left}}code{{overflow-wrap:anywhere}}.decision{{border-left:.35rem solid;padding:.75rem}}</style></head>
<body><a href="#main">Skip to review</a><main id="main" tabindex="-1">
<h1>ownhands M4 Assurance Review</h1><p>This is a local M4 review artifact, not the M5 production UI.</p>
<h2>Summary</h2><p><strong>Task:</strong> {html.escape(task['task_id'])}</p><p><strong>Goal:</strong> {html.escape(task['goal'])}</p><p><strong>Restore:</strong> {html.escape(packet['restore_verification']['result'])} in a disposable clone</p>
<h2>Impact</h2><ul>{changed}</ul><p>Bounded declared relations: {len(impact['relations'])}; completeness is not claimed.</p>
<h2>Tests</h2><table><thead><tr><th>Test</th><th>Class</th><th>Scope</th></tr></thead><tbody>{tests}</tbody></table>
<h2>Gaps</h2><ul>{gap_items}</ul>
<h2>Gate</h2><p class="decision"><strong>{html.escape(gate['decision'])}</strong> ({html.escape(gate['basis'])})</p><h3>Hard reasons</h3><ul>{hard_reasons}</ul><h3>Soft reasons</h3><ul>{soft_reasons}</ul>
<h2>Evidence</h2><ul>{evidence}</ul><p>Raw test output is retained only in the supplied local data root.</p>
</main></body></html>"""


def run_m4_fixture(
    data_root: Path | str,
    packet_output: Path | str,
    review_output: Path | str,
    *,
    observed_at: str,
) -> dict:
    data_root = Path(data_root).resolve()
    packet_output = Path(packet_output).resolve()
    review_output = Path(review_output).resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    contract = _contract()
    with tempfile.TemporaryDirectory(prefix="ownhands-m4-fixture-") as temporary:
        repository = _fixture_repository(Path(temporary))
        before_result, before_output = _run_test(repository)
        _write(data_root / "before-test-output.txt", before_output)
        _write(
            repository / "widget.py",
            "def normalize(value):\n"
            "    if not isinstance(value, str):\n"
            "        raise TypeError('value must be a string')\n"
            "    return value.strip().lower()\n",
        )
        restore = capture_restore_point(repository, contract["task"], observed_at)
        verification = verify_restore_point(repository, restore)
        relation_catalog = {
            "relations": [
                {
                    "relation_id": "relation:widget-feature",
                    "changed_path_glob": "widget.py",
                    "relation_type": "feature",
                    "target_ref": "feature:string-validation",
                    "basis": "declared",
                    "evidence_refs": ["evidence:m4:requirements"],
                },
                {
                    "relation_id": "relation:widget-test",
                    "changed_path_glob": "widget.py",
                    "relation_type": "test",
                    "target_ref": "test:widget-regression",
                    "required_classification": "regression",
                    "basis": "declared",
                    "evidence_refs": ["evidence:m4:test-map"],
                },
            ],
            "excluded": [
                {"area": "external_services", "reason": "the fixture invokes no external service"},
                {"area": "dynamic_runtime_relationships", "reason": "v1 joins declared relations only"},
            ],
            "unobserved": [
                {"area": "dynamic_runtime_relationships", "reason": "the fixture does not claim complete dependency discovery"}
            ],
        }
        impact = analyze_impact(repository, restore, contract, relation_catalog, observed_at)
        design = build_test_design(
            contract,
            impact,
            [{"criterion_id": "tests_pass", "required_viewpoints": ["regression", "recovery"], "test_ids": ["test:widget-regression"]}],
        )
        after_result, after_output = _run_test(repository)
        _write(data_root / "after-test-output.txt", after_output)
        environment_fingerprint = fingerprint(
            {"implementation": sys.implementation.name, "version": list(sys.version_info[:3])}
        )
        before_receipt = _receipt(
            contract,
            before_result,
            "evidence:m4:before-test",
            environment_fingerprint,
            restore["start_patch_hash"],
            restore["tracked_patch_hash"],
        )
        after_receipt = _receipt(
            contract,
            after_result,
            "evidence:m4:after-test",
            environment_fingerprint,
            restore["start_patch_hash"],
            restore["tracked_patch_hash"],
        )
        selection = contract["assurance_draft"]["tests"]
        before = record_test_baseline(contract, selection, [before_receipt], observed_at)
        after = record_test_baseline(contract, selection, [after_receipt], observed_at)
        comparison = compare_test_runs(before, after)
        gaps = detect_test_gaps(contract, impact, design, comparison)
        gate = evaluate_regression_gate(contract, impact, design, comparison, gaps)
        evidence_refs = sorted(
            {"evidence:m4:before-test", "evidence:m4:after-test", "evidence:m4:requirements", "evidence:m4:test-map"}
        )
        packet = build_assurance_packet(
            contract=contract,
            restore_point=restore,
            restore_verification=verification,
            impact=impact,
            test_design=design,
            before=before,
            after=after,
            comparison=comparison,
            gaps=gaps,
            gate=gate,
            evidence_refs=evidence_refs,
            observed_at=observed_at,
        )
    validate_packet_document(packet)
    _write(packet_output, json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _write(review_output, render_review(packet))
    return {
        "packet_path": str(packet_output),
        "review_path": str(review_output),
        "data_root": str(data_root),
        "packet_fingerprint": packet["fingerprint"],
        "gate_decision": packet["gate"]["decision"],
    }

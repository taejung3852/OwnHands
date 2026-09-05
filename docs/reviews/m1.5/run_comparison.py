from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from devharness.context_architecture import build_comparison_plan, evaluate_comparison


def metric(value=None, *, basis="unobserved", **provenance):
    return {"basis": basis, "value": value, **provenance}


def tokens_from(events, field, receipt):
    values = []
    for event in events:
        usage = event.get("usage")
        if isinstance(usage, dict) and isinstance(usage.get(field), int):
            values.append(usage[field])
    return metric(values[-1], basis="observed", receipt_ref=receipt) if values else metric()


def changed_paths(before: dict[str, bytes], workspace: Path) -> list[str]:
    after = {
        str(path.relative_to(workspace)): path.read_bytes()
        for path in workspace.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fixed ownhands M1.5 A/B/C comparison")
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--target-commit", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="required acknowledgement that this consumes Codex quota")
    arguments = parser.parse_args()
    if not arguments.execute:
        parser.error("--execute is required; without it no Codex run is started")
    if arguments.output_root.exists():
        parser.error("output-root must not already exist")

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=arguments.repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if head.returncode != 0 or head.stdout.strip() != arguments.target_commit:
        parser.error("target-commit must equal the current repository HEAD")
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=arguments.repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        parser.error("repository must be clean before the nine-run comparison")

    package = json.loads(arguments.package.read_text(encoding="utf-8"))
    fixture = arguments.repo_root / package["fixture"]["path"]
    context_root = arguments.package.parent / "fixtures"
    required_paths = [
        fixture,
        context_root / "condition-b" / "AGENTS.md",
        context_root / "condition-c" / "AGENTS.md",
        context_root / "condition-c" / "task-reference.md",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        parser.error(f"required comparison path is missing: {missing[0]}")
    plan = build_comparison_plan(package, arguments.target_commit)
    arguments.output_root.mkdir(parents=True)
    (arguments.output_root / "run-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    records = []
    for specification in plan:
        run_root = arguments.output_root / specification["run_id"]
        workspace = run_root / "workspace"
        shutil.copytree(fixture, workspace)
        condition = specification["condition"]
        if condition in {"B", "C"}:
            source = context_root / f"condition-{condition.lower()}"
            for path in source.iterdir():
                shutil.copy2(path, workspace / path.name)
        before = {
            str(path.relative_to(workspace)): path.read_bytes()
            for path in workspace.rglob("*")
            if path.is_file()
        }
        event_path = run_root / "codex-events.jsonl"
        last_message = run_root / "last-message.txt"
        command = [
            "codex", "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--skip-git-repo-check", "--json", "--color", "never",
            "--model", specification["model"],
            "--config", f'model_reasoning_effort="{specification["reasoning_effort"]}"',
            "--config", 'approval_policy="never"',
            "--config", "sandbox_workspace_write.network_access=false",
            "--sandbox", "workspace-write", "--cd", str(workspace),
            "--output-last-message", str(last_message), package["fixed_conditions"]["prompt"],
        ]
        started = time.monotonic()
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        elapsed = time.monotonic() - started
        event_path.write_text(completed.stdout, encoding="utf-8")
        events = []
        for line in completed.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
        tests = subprocess.run(
            [sys.executable, "-m", "unittest", "-v"], cwd=workspace, text=True, capture_output=True, check=False
        )
        (run_root / "fixture-tests.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
        changes = changed_paths(before, workspace)
        out_of_scope = [path for path in changes if path != "harness.py"]
        receipt = str(event_path.relative_to(arguments.output_root))
        test_receipt = str((run_root / "fixture-tests.txt").relative_to(arguments.output_root))
        instruction_receipt = f"{test_receipt} + workspace diff"
        instruction_violations = int(tests.returncode != 0) + len(out_of_scope)
        record = {
            **specification,
            "status": "completed" if completed.returncode == 0 else "failed",
            "metrics": {
                "requirements_met": metric(tests.returncode == 0 and not out_of_scope, basis="observed", receipt_ref=test_receipt),
                "tests_passed": metric(tests.returncode == 0, basis="observed", receipt_ref=test_receipt),
                "instruction_violations": metric(instruction_violations, basis="observed", receipt_ref=instruction_receipt, exact_scope="fixture tests and change-only-harness requirement"),
                "out_of_scope_changes": metric(len(out_of_scope), basis="observed", receipt_ref="workspace diff"),
                "tool_calls": metric(),
                "elapsed_seconds": metric(round(elapsed, 6), basis="observed", receipt_ref=receipt),
                "input_tokens": tokens_from(events, "input_tokens", receipt),
                "output_tokens": tokens_from(events, "output_tokens", receipt),
                "human_understanding": metric(),
                "human_review_seconds": metric(),
            },
            "changed_paths": changes,
            "codex_exit_code": completed.returncode,
        }
        (run_root / "run-record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        records.append(record)
    (arguments.output_root / "run-records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    evaluation = evaluate_comparison(package, records)
    (arguments.output_root / "comparison-evaluation.json").write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

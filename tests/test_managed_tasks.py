from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from devharness.catalog import Catalog
from devharness.codex_app_server import AppServerRecord, AppServerRun
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.events import EventDraft, EventLog
from devharness.guarantees import GuaranteeEvaluator
from devharness.identity import IdentityRegistry
from devharness.managed_tasks import (
    ManagedTaskError,
    prepare_managed_task,
    record_managed_run,
    verify_start_restore,
)
from devharness.paths import DataPaths
from devharness.projections import ProjectionEngine


NOW = "2026-09-05T12:00:00+00:00"
MATRIX = Path(__file__).resolve().parents[1] / "docs/product/guarantee-matrix.v1.json"
HASH = "1" * 64


def canonical_hash(value: dict) -> str:
    document = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(document.encode()).hexdigest()


def content_hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def create_repository(root: Path) -> tuple[Path, str, str]:
    repository = root / "repository"
    repository.mkdir()
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "fixture@example.invalid")
    git(repository, "config", "user.name", "Fixture")
    files = {
        ".ownhands-disposable": b"synthetic fixture\n",
        "AGENTS.md": b"Synthetic managed instructions.\n",
        ".codex/config.toml": b'sandbox_mode = "workspace-write"\napproval_policy = "on-request"\n',
        ".codex/rules/ownhands.rules": b'prefix_rule(pattern=["python"], decision="allow")\n',
        ".codex/hooks.json": b'{"hooks":[]}\n',
    }
    for relative, payload in files.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "fixture")
    start_commit = git(repository, "rev-parse", "HEAD")
    patch = subprocess.run(
        ["git", "diff", "--binary", start_commit],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return repository, start_commit, content_hash(patch)


def make_request(
    repository: Path,
    start_commit: str,
    patch_hash: str,
    *,
    project_id: str = "project-managed",
    worktree_id: str = "worktree-managed",
    task_id: str = "task-managed",
    environment_ref: str = "environment-managed",
) -> dict:
    sources = []
    for path, source_type in (
        ("AGENTS.md", "agents_instruction"),
        (".codex/config.toml", "codex_config"),
        (".codex/rules/ownhands.rules", "rule"),
        (".codex/hooks.json", "hook"),
    ):
        sources.append(
            {
                "source_id": f"source:{path}",
                "source_type": source_type,
                "path": path,
                "content_hash": content_hash((repository / path).read_bytes()),
            }
        )
    baseline = {
        "baseline_id": "baseline-managed-v1",
        "project_id": project_id,
        "worktree_id": worktree_id,
        "environment_ref": environment_ref,
        "sources": sources,
        "event_refs": [f"task-created:{task_id}"],
        "evidence_refs": ["evidence-m2-baseline"],
    }
    baseline["fingerprint"] = canonical_hash(baseline)
    task = {
        "project_id": project_id,
        "worktree_id": worktree_id,
        "task_id": task_id,
        "environment_ref": environment_ref,
        "mode": "managed",
        "goal": "synthetic managed run",
    }
    contract = {
        "contract_id": f"contract:{task_id}",
        "task": task,
        "baseline_ref": baseline["baseline_id"],
        "baseline_fingerprint": baseline["fingerprint"],
        "gate_status": "ready_for_preview",
        "event_refs": list(baseline["event_refs"]),
        "evidence_refs": list(baseline["evidence_refs"]),
        "approval_triggers": ["protected_target"],
    }
    contract["fingerprint"] = canonical_hash(contract)
    return {
        "repository": str(repository),
        "task": copy.deepcopy(task),
        "baseline": baseline,
        "freshness": {"status": "fresh", "basis": "observed"},
        "contract": contract,
        "approval": {
            "approval_id": "approval-managed-start",
            "decision": "approved",
            "decision_source": "explicit_product_approval",
            "contract_ref": contract["contract_id"],
            "task_id": task_id,
            "scope": "managed_task_start",
            "expires_at": "2026-09-05T13:00:00+00:00",
        },
        "start_commit": start_commit,
        "patch_hash": patch_hash,
        "branch": "fixture-main",
        "available_event_refs": list(baseline["event_refs"]),
        "available_evidence_refs": list(baseline["evidence_refs"]),
        "sandbox_mode": "workspace-write",
        "approval_policy": "on-request",
        "runtime_observations": {
            "sandbox": {
                "item_id": "item-sandbox",
                "exact_scope": "outside-worktree-write",
                "probe": "write synthetic marker outside writable roots",
                "attempted": True,
                "terminal_payload_hash": HASH,
            },
            "approval": {
                "item_id": "item-approval",
                "exact_scope": "safe-command-decline",
                "exact_action": "decline synthetic safe command",
                "request_payload_hash": HASH,
            },
            "hook": {
                "item_id": "hook-fixture",
                "exact_scope": "PreToolUse synthetic command",
                "event_type": "PreToolUse",
                "started_payload_hash": HASH,
                "completed_payload_hash": HASH,
            },
        },
    }


def app_server_run() -> AppServerRun:
    def item(
        kind: str,
        method: str,
        item_id: str,
        *,
        status: str | None = None,
        decision: str | None = None,
        request_id: str | None = None,
    ) -> AppServerRecord:
        return AppServerRecord(
            kind=kind,
            method=method,
            payload_hash=HASH,
            request_id=request_id,
            thread_id="thread-managed",
            turn_id="turn-managed",
            item_id=item_id,
            item_type="commandExecution",
            status=status,
            decision=decision,
        )

    return AppServerRun(
        records=[
            item("notification", "hook/started", "hook-fixture", status="started"),
            item("notification", "hook/completed", "hook-fixture", status="completed"),
            item("notification", "item/completed", "item-sandbox", status="failed"),
            item("approval_request", "item/commandExecution/requestApproval", "item-approval", request_id="approval-runtime"),
            item("approval_decision", "item/commandExecution/requestApproval", "item-approval", decision="decline", request_id="approval-runtime"),
            item("notification", "serverRequest/resolved", "item-approval", status="resolved", decision="decline", request_id="approval-runtime"),
            item("notification", "item/completed", "item-approval", status="declined"),
        ],
        thread_id="thread-managed",
        turn_id="turn-managed",
        terminal_status="completed",
        instruction_sources=["AGENTS.md"],
        codex_version="0.153.3",
        protocol_fingerprint="sha256:protocol-fixture",
    )


class ManagedTaskTests(unittest.TestCase):
    def test_managed_start_requires_fresh_bound_approved_contract_and_restore_basis(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository, start_commit, patch_hash = create_repository(Path(temporary))
            valid = make_request(repository, start_commit, patch_hash)
            mutations = []

            stale = copy.deepcopy(valid)
            stale["freshness"]["status"] = "stale"
            mutations.append(("freshness", stale))
            for key in ("project_id", "worktree_id", "task_id", "environment_ref"):
                foreign = copy.deepcopy(valid)
                foreign["task"][key] = f"foreign-{key}"
                mutations.append((key, foreign))
            expired = copy.deepcopy(valid)
            expired["approval"]["expires_at"] = "2026-09-05T11:59:59+00:00"
            mutations.append(("expired approval", expired))
            wrong_scope = copy.deepcopy(valid)
            wrong_scope["approval"]["scope"] = "other_task"
            mutations.append(("approval scope", wrong_scope))
            for key, value in (
                ("decision", "declined"),
                ("decision_source", "fixture_response"),
                ("contract_ref", "contract:foreign"),
            ):
                invalid_approval = copy.deepcopy(valid)
                invalid_approval["approval"][key] = value
                mutations.append((f"approval {key}", invalid_approval))
            blocked_gate = copy.deepcopy(valid)
            blocked_gate["contract"]["gate_status"] = "hard_block"
            blocked_gate["contract"]["fingerprint"] = canonical_hash(
                {key: value for key, value in blocked_gate["contract"].items() if key != "fingerprint"}
            )
            mutations.append(("contract gate", blocked_gate))
            missing_commit = copy.deepcopy(valid)
            missing_commit["start_commit"] = ""
            mutations.append(("start commit", missing_commit))
            missing_patch = copy.deepcopy(valid)
            missing_patch["patch_hash"] = ""
            mutations.append(("patch hash", missing_patch))
            stale_contract = copy.deepcopy(valid)
            stale_contract["contract"]["fingerprint"] = "sha256:" + "f" * 64
            mutations.append(("contract fingerprint", stale_contract))
            unresolved = copy.deepcopy(valid)
            unresolved["available_evidence_refs"] = []
            mutations.append(("reference closure", unresolved))

            for name, request in mutations:
                with self.subTest(mutation=name), self.assertRaises(ManagedTaskError):
                    prepare_managed_task(request, now=NOW)

    def test_managed_start_rejects_unmarked_and_non_git_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, start_commit, patch_hash = create_repository(root)
            request = make_request(repository, start_commit, patch_hash)
            (repository / ".ownhands-disposable").unlink()
            with self.assertRaisesRegex(ManagedTaskError, "disposable"):
                prepare_managed_task(request, now=NOW)

            ordinary = root / "ordinary"
            ordinary.mkdir()
            (ordinary / ".ownhands-disposable").write_text("fixture")
            non_git = copy.deepcopy(request)
            non_git["repository"] = str(ordinary)
            with self.assertRaisesRegex(ManagedTaskError, "Git"):
                prepare_managed_task(non_git, now=NOW)

    def test_dirty_start_without_patch_fingerprint_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository, start_commit, patch_hash = create_repository(Path(temporary))
            (repository / "AGENTS.md").write_text("changed synthetic instructions\n")
            request = make_request(repository, start_commit, patch_hash)
            request["patch_hash"] = ""

            with self.assertRaisesRegex(ManagedTaskError, "patch"):
                prepare_managed_task(request, now=NOW)

    def test_restore_receipt_checks_commit_and_patch_without_changing_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository, start_commit, patch_hash = create_repository(Path(temporary))
            before = git(repository, "status", "--porcelain=v1")

            receipt = verify_start_restore(repository, start_commit, patch_hash)

            self.assertEqual("pass", receipt["result"])
            self.assertEqual("observed", receipt["basis"])
            self.assertEqual(start_commit, receipt["commit_patch_or_reference"])
            self.assertEqual(patch_hash, receipt["patch_hash"])
            self.assertEqual("start commit resolves and current binary patch matches", receipt["restore_probe"])
            self.assertEqual(before, git(repository, "status", "--porcelain=v1"))
            with self.assertRaisesRegex(ManagedTaskError, "patch"):
                verify_start_restore(repository, start_commit, "sha256:" + "0" * 64)

    def test_recorded_run_uses_real_stores_and_supports_exact_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, start_commit, patch_hash = create_repository(root)
            paths = DataPaths.resolve(root / "app-data")
            with Catalog.open(paths) as catalog:
                identities = IdentityRegistry(catalog)
                project = identities.register_project(str(repository))
                worktree = identities.register_worktree(project.project_id, str(repository))
                task = identities.create_task(
                    worktree.worktree_id,
                    "managed",
                    start_commit,
                    "fixture-main",
                    str(repository),
                    "environment-managed",
                )
                events = EventLog(catalog)
                events.append(
                    EventDraft(
                        f"task-created:{task.task_id}",
                        task.task_id,
                        "task.created",
                        1,
                        NOW,
                        {"mode": "managed"},
                        "m3-test",
                        "not_needed",
                    ),
                    lambda value: value,
                )
                store = EvidenceStore(catalog, events)
                store.put(
                    EvidenceDraft(
                        "evidence-m2-baseline",
                        task.task_id,
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
                    lambda value: value,
                )
                request = make_request(
                    repository,
                    start_commit,
                    patch_hash,
                    project_id=project.project_id,
                    worktree_id=worktree.worktree_id,
                    task_id=task.task_id,
                )
                prepared = prepare_managed_task(request, now=NOW)

                packet = record_managed_run(catalog, prepared, app_server_run())

                self.assertEqual(task.task_id, packet["task_id"])
                self.assertEqual("thread-managed", packet["thread_id"])
                self.assertEqual("turn-managed", packet["turn_id"])
                self.assertEqual("completed", packet["terminal_status"])
                self.assertEqual("pass", packet["restore"]["result"])
                self.assertEqual(6, len(packet["control_records"]))
                self.assertEqual(11, len(packet["evidence_refs"]))
                self.assertEqual(
                    list(range(1, len(events.list_for_task(task.task_id)) + 1)),
                    [event.sequence for event in events.list_for_task(task.task_id)],
                )
                for evidence_id in packet["evidence_refs"]:
                    evidence = store.resolve(evidence_id)
                    self.assertFalse(evidence.object_path.is_relative_to(repository))
                    self.assertEqual(0o600, os.stat(evidence.object_path).st_mode & 0o777)
                projection = ProjectionEngine(catalog, events).project(task.task_id)
                freshness = ProjectionEngine(catalog, events).freshness(task.task_id)
                self.assertEqual("ready", projection.state)
                self.assertTrue(freshness.is_fresh)
                evaluator = GuaranteeEvaluator(catalog, store, MATRIX)
                results = {
                    result["claim_id"]: result["verdict"]
                    for result in evaluator.evaluate(
                        task.task_id, ["GM-003", "GM-005", "GM-006", "GM-007", "GM-010"]
                    )["claim_results"]
                }
                self.assertEqual(
                    {
                        "GM-003": "supported",
                        "GM-005": "supported",
                        "GM-006": "supported",
                        "GM-007": "supported",
                        "GM-010": "supported",
                    },
                    results,
                )

    def test_recorded_run_rejects_unresolved_m2_catalog_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, start_commit, patch_hash = create_repository(root)
            with Catalog.open(DataPaths.resolve(root / "app-data")) as catalog:
                identities = IdentityRegistry(catalog)
                project = identities.register_project(str(repository))
                worktree = identities.register_worktree(project.project_id, str(repository))
                task = identities.create_task(worktree.worktree_id, "managed", start_commit, "fixture-main", str(repository), "environment-managed")
                EventLog(catalog).append(
                    EventDraft(f"task-created:{task.task_id}", task.task_id, "task.created", 1, NOW, {"mode": "managed"}, "m3-test", "not_needed"),
                    lambda value: value,
                )
                request = make_request(repository, start_commit, patch_hash, project_id=project.project_id, worktree_id=worktree.worktree_id, task_id=task.task_id)
                prepared = prepare_managed_task(request, now=NOW)

                with self.assertRaisesRegex(ManagedTaskError, "Evidence reference"):
                    record_managed_run(catalog, prepared, app_server_run())


if __name__ == "__main__":
    unittest.main()

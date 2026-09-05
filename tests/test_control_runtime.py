from __future__ import annotations

import copy
import unittest

from devharness.codex_app_server import AppServerRecord, AppServerRun
from devharness.control_runtime import evaluate_runtime_controls


HASH = "0" * 64
NOW = "2026-09-05T12:00:00+00:00"


def record(
    kind: str,
    method: str,
    *,
    item_id: str | None = None,
    status: str | None = None,
    decision: str | None = None,
    request_id: str | None = None,
) -> AppServerRecord:
    return AppServerRecord(
        kind=kind,
        method=method,
        payload_hash=HASH,
        request_id=request_id,
        thread_id="thread-runtime",
        turn_id="turn-runtime",
        item_id=item_id,
        item_type="commandExecution" if item_id else None,
        status=status,
        decision=decision,
    )


def run(records: list[AppServerRecord], sources: list[str] | None = None) -> AppServerRun:
    return AppServerRun(
        records=records,
        thread_id="thread-runtime",
        turn_id="turn-runtime",
        terminal_status="completed",
        instruction_sources=sources or [],
        codex_version="0.153.3",
        protocol_fingerprint="sha256:protocol-fixture",
    )


def prepared() -> dict:
    return {
        "task": {
            "project_id": "project-runtime",
            "worktree_id": "worktree-runtime",
            "task_id": "task-runtime",
            "environment_ref": "environment-runtime",
        },
        "checked_at": NOW,
        "configured": {
            "config": {"observed": True, "exact_scope": ".codex/config.toml"},
            "agents": {"observed": True, "exact_scope": "AGENTS.md"},
            "rules": {"observed": True, "exact_scope": ".codex/rules/ownhands.rules"},
            "hooks": {"observed": True, "exact_scope": ".codex/hooks.json"},
            "sandbox": {"observed": True, "exact_scope": "workspace-write"},
            "approval": {"observed": True, "exact_scope": "on-request"},
        },
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


class RuntimeControlTests(unittest.TestCase):
    def test_configured_record_does_not_promote_to_loaded_or_enforced(self) -> None:
        packet = evaluate_runtime_controls(prepared(), run([]))

        self.assertEqual("pass", packet["config"]["configured"]["result"])
        self.assertEqual("observed", packet["config"]["configured"]["basis"])
        self.assertEqual("not_run", packet["config"]["loaded"]["result"])
        self.assertEqual("unobserved", packet["config"]["loaded"]["basis"])
        self.assertEqual("not_run", packet["config"]["enforced"]["result"])
        self.assertEqual("unobserved", packet["config"]["enforced"]["basis"])

    def test_instruction_source_is_loaded_only_for_an_exact_run_source(self) -> None:
        exact = evaluate_runtime_controls(prepared(), run([], ["AGENTS.md"]))
        foreign = evaluate_runtime_controls(prepared(), run([], ["nested/AGENTS.md"]))

        self.assertEqual("pass", exact["agents"]["loaded"]["result"])
        self.assertEqual("observed", exact["agents"]["loaded"]["basis"])
        self.assertEqual("instruction-source", exact["agents"]["control_id"])
        self.assertEqual("AGENTS.md", exact["agents"]["loaded"]["exact_scope"])
        self.assertEqual("not_run", foreign["agents"]["loaded"]["result"])
        self.assertEqual([], foreign["agents"]["loaded"]["evidence_refs"])

    def test_sandbox_enforcement_needs_the_exact_failed_probe_item(self) -> None:
        exact = evaluate_runtime_controls(
            prepared(),
            run([record("notification", "item/completed", item_id="item-sandbox", status="failed")]),
        )
        wrong_item = evaluate_runtime_controls(
            prepared(),
            run([record("notification", "item/completed", item_id="item-other", status="failed")]),
        )
        successful_write = evaluate_runtime_controls(
            prepared(),
            run([record("notification", "item/completed", item_id="item-sandbox", status="completed")]),
        )
        wrong_hash_prepared = prepared()
        wrong_hash_prepared["runtime_observations"]["sandbox"]["terminal_payload_hash"] = "f" * 64
        wrong_hash = evaluate_runtime_controls(
            wrong_hash_prepared,
            run([record("notification", "item/completed", item_id="item-sandbox", status="failed")]),
        )

        self.assertEqual("pass", exact["sandbox"]["enforced"]["result"])
        self.assertEqual("observed", exact["sandbox"]["enforced"]["basis"])
        self.assertEqual("outside-worktree-write", exact["sandbox"]["enforced"]["exact_scope"])
        self.assertEqual("not_run", wrong_item["sandbox"]["enforced"]["result"])
        self.assertEqual("fail", successful_write["sandbox"]["enforced"]["result"])
        self.assertEqual("observed", successful_write["sandbox"]["enforced"]["basis"])
        self.assertEqual("fail", wrong_hash["sandbox"]["enforced"]["result"])

    def test_model_independent_sandbox_denial_is_observed_without_an_app_server_item(self) -> None:
        probe = copy.deepcopy(prepared())
        probe["runtime_observations"]["sandbox"] = {
            "item_id": "sandbox:" + "a" * 64,
            "exact_scope": "one sibling-path write outside the disposable worktree",
            "probe": "deterministic_cli_sandbox",
            "attempted": True,
            "denied": True,
            "exit_code": 1,
            "terminal_payload_hash": "b" * 64,
        }

        packet = evaluate_runtime_controls(probe, run([]))

        self.assertEqual("pass", packet["sandbox"]["enforced"]["result"])
        self.assertEqual("observed", packet["sandbox"]["enforced"]["basis"])

    def test_approval_enforcement_needs_request_decision_resolution_and_terminal_item(self) -> None:
        complete_records = [
            record("approval_request", "item/commandExecution/requestApproval", item_id="item-approval", request_id="approval-1"),
            record("approval_decision", "item/commandExecution/requestApproval", item_id="item-approval", decision="decline", request_id="approval-1"),
            record("notification", "serverRequest/resolved", item_id="item-approval", status="resolved", decision="decline", request_id="approval-1"),
            record("notification", "item/completed", item_id="item-approval", status="declined"),
        ]
        complete = evaluate_runtime_controls(prepared(), run(complete_records))
        incomplete = evaluate_runtime_controls(prepared(), run(complete_records[:-1]))
        wrong_hash_prepared = prepared()
        wrong_hash_prepared["runtime_observations"]["approval"]["request_payload_hash"] = "f" * 64
        wrong_hash = evaluate_runtime_controls(wrong_hash_prepared, run(complete_records))

        self.assertEqual("pass", complete["approval"]["enforced"]["result"])
        self.assertEqual("observed", complete["approval"]["enforced"]["basis"])
        self.assertEqual("approval-transaction", complete["approval"]["control_id"])
        self.assertEqual("safe-command-decline", complete["approval"]["enforced"]["exact_scope"])
        self.assertEqual("fail", incomplete["approval"]["enforced"]["result"])
        self.assertEqual("observed", incomplete["approval"]["enforced"]["basis"])
        self.assertEqual("fail", wrong_hash["approval"]["enforced"]["result"])

    def test_hook_failure_is_observed_failure_and_never_enforcement(self) -> None:
        packet = evaluate_runtime_controls(
            prepared(),
            run(
                [
                    record("notification", "hook/started", item_id="hook-fixture", status="started"),
                    record("notification", "hook/completed", item_id="hook-fixture", status="failed"),
                ]
            ),
        )

        self.assertEqual("fail", packet["hooks"]["loaded"]["result"])
        self.assertEqual("observed", packet["hooks"]["loaded"]["basis"])
        self.assertEqual("not_run", packet["hooks"]["enforced"]["result"])
        self.assertEqual("unobserved", packet["hooks"]["enforced"]["basis"])


if __name__ == "__main__":
    unittest.main()

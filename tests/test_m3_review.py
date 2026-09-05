from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from devharness.m3_review import (
    M3ReviewError,
    build_review_packet,
    claim_live_attempt,
    render_review,
    validate_live_preflight,
)


HASH = "sha256:" + "a" * 64
PROTOCOL = "sha256:" + "b" * 64


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def repository(root: Path) -> Path:
    path = root / "disposable"
    path.mkdir()
    git(path, "init", "-q")
    (path / ".ownhands-disposable").write_text("fixture\n")
    return path


def managed_packet() -> dict:
    def check(result: str, basis: str, ref: str | None = None) -> dict:
        return {
            "result": result,
            "basis": basis,
            "evidence_refs": [] if ref is None else [ref],
        }

    controls = {
        name: {
            "configured": check("pass", "observed", f"evidence:configured:{name}"),
            "loaded": check("not_run", "unobserved"),
            "enforced": check("not_run", "unobserved"),
        }
        for name in ("config", "agents", "rules", "hooks", "sandbox", "approval")
    }
    controls["agents"]["loaded"] = check("pass", "observed", "evidence:agents:loaded")
    controls["hooks"]["loaded"] = check("fail", "observed", "evidence:hooks:failed")
    controls["sandbox"]["enforced"] = check("pass", "observed", "evidence:sandbox:denied")
    controls["approval"]["enforced"] = check("pass", "observed", "evidence:approval:declined")
    evidence = sorted(
        {ref for control in controls.values() for value in control.values() for ref in value["evidence_refs"]}
        | {"evidence:restore"}
    )
    control_types = {
        "config": "active_config",
        "agents": "agents_instruction",
        "rules": "rule",
        "hooks": "control_profile",
        "sandbox": "sandbox",
        "approval": "approval_policy",
    }
    return {
        "task_id": "task-managed-fixture",
        "thread_id": "thread-private-92f3",
        "turn_id": "turn-private-18ab",
        "terminal_status": "completed",
        "control_records": [
            {"control_type": control_types[name], "checks": checks} for name, checks in controls.items()
        ],
        "event_refs": [f"evidence-recorded:{ref}" for ref in evidence],
        "evidence_refs": evidence,
        "restore": {
            "result": "pass",
            "basis": "observed",
            "commit_patch_or_reference": "1" * 40,
            "patch_hash": HASH,
            "scope": "/private/Users/alice/secret-repository",
        },
    }


def imported_packet() -> dict:
    not_run = {
        "result": "not_run",
        "basis": "unobserved",
        "evidence_refs": [],
    }
    return {
        "task_id": "task-imported-fixture",
        "mode": "imported",
        "controls": {
            name: {stage: dict(not_run) for stage in ("configured", "loaded", "enforced")}
            for name in ("config", "agents", "rules", "hooks", "sandbox", "approval")
        },
        "evidence_refs": ["evidence:imported:snapshot", "evidence:imported:diff", "evidence:imported:test"],
    }


def raw_receipt(managed: dict, *, probe_kind: str = "fixture") -> dict:
    return {
        "probe_kind": probe_kind,
        "codex_version": "0.153.3",
        "protocol_fingerprint": PROTOCOL,
        "model": "gpt-5.6-luna",
        "reasoning_effort": "low",
        "terminal_status": managed["terminal_status"],
        "thread_id": managed["thread_id"],
        "task_id": managed["task_id"],
        "event_refs": managed["event_refs"],
        "evidence_refs": managed["evidence_refs"],
        "restore": managed["restore"],
        "sandbox": {"attempted": True, "denied": True, "item_ref": "item-sandbox"},
        "approval": {
            "requested": True,
            "decision": "decline",
            "resolved": True,
            "terminal": True,
            "item_ref": "item-approval",
        },
    }


class M3ReviewTests(unittest.TestCase):
    def test_fake_packet_is_sanitized_and_cannot_satisfy_live_gate(self) -> None:
        managed = managed_packet()
        packet = build_review_packet(
            managed,
            imported_packet(),
            raw_receipt(managed),
            generated_at="2026-09-05T12:00:00+00:00",
        )
        rendered = json.dumps(packet, ensure_ascii=False, sort_keys=True)

        self.assertEqual("blocked", packet["runtime_gate"]["result"])
        self.assertEqual("unobserved", packet["runtime_gate"]["basis"])
        self.assertEqual("pass", packet["managed"]["controls"]["sandbox"]["enforced"]["result"])
        self.assertEqual("observed", packet["managed"]["controls"]["sandbox"]["enforced"]["basis"])
        self.assertEqual(
            ["evidence:sandbox:denied"],
            packet["managed"]["controls"]["sandbox"]["enforced"]["evidence_refs"],
        )
        self.assertTrue(packet["managed"]["thread_ref"].startswith("sha256:"))
        for forbidden in (
            "thread-private-92f3",
            "turn-private-18ab",
            "/private/Users/alice/secret-repository",
            "raw prompt containing API_TOKEN=secret",
            "command output: private",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertIn("issues/38", packet["human_friction"]["issue"])
        self.assertEqual("unobserved", packet["human_friction"]["basis"])
        self.assertIn("Configured", render_review(packet))
        self.assertIn("Enforced / Observed", render_review(packet))

    def test_live_gate_recomputes_closure_and_fails_tampering(self) -> None:
        managed = managed_packet()
        receipt = raw_receipt(managed, probe_kind="live")
        packet = build_review_packet(
            managed,
            imported_packet(),
            receipt,
            generated_at="2026-09-05T12:00:00+00:00",
        )
        self.assertEqual("pass", packet["runtime_gate"]["result"])
        self.assertTrue(all(check["result"] == "pass" for check in packet["runtime_gate"]["checks"].values()))

        tampered = raw_receipt(managed, probe_kind="live")
        tampered["evidence_refs"] = tampered["evidence_refs"][:-1]
        with self.assertRaisesRegex(M3ReviewError, "Evidence reference closure"):
            build_review_packet(managed, imported_packet(), tampered, generated_at="2026-09-05T12:00:00+00:00")

        incomplete = raw_receipt(managed, probe_kind="live")
        incomplete["approval"]["terminal"] = False
        packet = build_review_packet(managed, imported_packet(), incomplete, generated_at="2026-09-05T12:00:00+00:00")
        self.assertEqual("blocked", packet["runtime_gate"]["result"])
        self.assertEqual("fail", packet["runtime_gate"]["checks"]["approval_chain"]["result"])

    def test_live_preflight_is_explicit_exact_and_raw_data_is_outside_git(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = repository(root)
            data_root = root / "raw"
            output = root / "packet.json"

            with self.assertRaisesRegex(M3ReviewError, "--live"):
                validate_live_preflight(repo, data_root, output, "codex", "gpt-5.6-luna", 30, live=False)
            with self.assertRaisesRegex(M3ReviewError, "outside Git"):
                validate_live_preflight(repo, repo / "raw", output, "codex", "gpt-5.6-luna", 30, live=True)
            nested = repo / "nested"
            nested.mkdir()
            (nested / ".ownhands-disposable").write_text("fixture\n")
            with self.assertRaisesRegex(M3ReviewError, "exact Git repository root"):
                validate_live_preflight(nested, data_root, output, "codex", "gpt-5.6-luna", 30, live=True)
            (repo / ".ownhands-disposable").unlink()
            with self.assertRaisesRegex(M3ReviewError, "disposable"):
                validate_live_preflight(repo, data_root, output, "codex", "gpt-5.6-luna", 30, live=True)

    def test_live_attempt_is_claimed_before_execution_and_never_retried(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            repo = repository(root)
            data_root = root / "raw-one"
            first = claim_live_attempt(data_root, {"repository_fingerprint": HASH, "model": "gpt-5.6-luna"}, repository=repo)
            self.assertTrue(first.is_file())
            with self.assertRaisesRegex(M3ReviewError, "already been attempted"):
                claim_live_attempt(root / "raw-two", {"repository_fingerprint": HASH, "model": "gpt-5.6-luna"}, repository=repo)

    def test_live_preflight_accepts_only_absolute_executable_and_tmp_raw_root(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            repo = repository(root)
            accepted = validate_live_preflight(
                repo,
                root / "raw",
                root / "packet.json",
                "/usr/bin/true",
                "gpt-5.6-luna",
                30,
                live=True,
            )
            self.assertEqual(Path("/usr/bin/true"), Path(accepted["codex_bin"]))
            with self.assertRaisesRegex(M3ReviewError, "absolute executable"):
                validate_live_preflight(repo, root / "other-raw", root / "packet.json", "codex", "gpt-5.6-luna", 30, live=True)


if __name__ == "__main__":
    unittest.main()

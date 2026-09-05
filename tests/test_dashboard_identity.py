from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from devharness.identity import TaskIdentity
from devharness.m3_review import build_review_packet
from devharness.m4_review import run_m4_fixture
from devharness.dashboard_sources import (
    m3_task_ref,
    validate_m3_packet,
    validate_m3_source,
    validate_m4_source,
)
from tests.test_m3_review import imported_packet, managed_packet, raw_receipt


NOW = "2026-09-06T12:00:00+00:00"


def m3_packet() -> dict:
    managed = managed_packet()
    return build_review_packet(
        managed,
        imported_packet(),
        raw_receipt(managed, probe_kind="live"),
        generated_at=NOW,
    )


def task_for_m3(packet: dict, *, task_id: str = "task-managed-fixture") -> TaskIdentity:
    return TaskIdentity(
        task_id=task_id,
        project_id="project-ownhands",
        worktree_id="worktree-ownhands",
        mode="managed",
        commit="abc123",
        branch="main",
        cwd="/repo",
        environment_ref="local-test",
        created_at=NOW,
    )


class DashboardIdentityTests(unittest.TestCase):
    def test_m3_packet_fingerprint_controls_and_reference_closure_validate(self) -> None:
        packet = m3_packet()

        validated = validate_m3_packet(packet)

        self.assertEqual(packet, validated)
        self.assertEqual(packet["managed"]["task_ref"], m3_task_ref("task-managed-fixture"))
        changed = copy.deepcopy(packet)
        changed["managed"]["controls"]["sandbox"]["enforced"]["evidence_refs"] = []
        with self.assertRaises(ValueError):
            validate_m3_packet(changed)

    def test_other_task_m3_stays_project_scope_and_never_becomes_task_control(self) -> None:
        packet = m3_packet()

        closure = validate_m3_source(task=task_for_m3(packet, task_id="another-task"), packet=packet)

        self.assertEqual("project", closure.scope)
        self.assertEqual("mismatch", closure.status)
        self.assertFalse(closure.task_applicable)
        self.assertIn("task_ref mismatch", closure.reasons)

    def test_m4_requires_all_canonical_task_and_start_commit_fields(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            run_m4_fixture(root / "raw", root / "packet.json", root / "review.html", observed_at=NOW)
            packet = json.loads((root / "packet.json").read_text(encoding="utf-8"))
        identity = packet["task"]
        task = TaskIdentity(
            task_id=identity["task_id"],
            project_id=identity["project_id"],
            worktree_id=identity["worktree_id"],
            mode=identity["mode"],
            commit=packet["restore_point"]["start_commit"],
            branch="main",
            cwd="/repo",
            environment_ref=identity["environment_ref"],
            created_at=NOW,
        )

        self.assertEqual("closed", validate_m4_source(task=task, packet=packet).status)
        for field in ("project_id", "worktree_id", "task_id", "environment_ref", "mode"):
            with self.subTest(field=field):
                changed_task = TaskIdentity(
                    **{**task.__dict__, field: "different"}
                )
                closure = validate_m4_source(task=changed_task, packet=packet)
                self.assertEqual("mismatch", closure.status)
                self.assertFalse(closure.task_applicable)
                self.assertIn(f"{field} mismatch", closure.reasons)
        changed_commit = TaskIdentity(**{**task.__dict__, "commit": "different"})
        self.assertIn(
            "start commit mismatch",
            validate_m4_source(task=changed_commit, packet=packet).reasons,
        )

    def test_tampered_m4_packet_is_invalid_not_partially_accepted(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            run_m4_fixture(root / "raw", root / "packet.json", root / "review.html", observed_at=NOW)
            packet = json.loads((root / "packet.json").read_text(encoding="utf-8"))
        identity = packet["task"]
        task = TaskIdentity(
            task_id=identity["task_id"], project_id=identity["project_id"],
            worktree_id=identity["worktree_id"], mode=identity["mode"],
            commit=packet["restore_point"]["start_commit"], branch="main", cwd="/repo",
            environment_ref=identity["environment_ref"], created_at=NOW,
        )
        packet["gate"]["decision"] = "pass"

        closure = validate_m4_source(task=task, packet=packet)

        self.assertEqual("invalid", closure.status)
        self.assertFalse(closure.task_applicable)


if __name__ == "__main__":
    unittest.main()

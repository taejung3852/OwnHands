from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from devharness.__main__ import _dashboard_services
from devharness.dashboard_export import export_masked_history
from tests.test_dashboard_render import review_view


NOW = "2026-09-06T12:00:00+00:00"


class DashboardExportTests(unittest.TestCase):
    def test_export_contains_only_requested_allowlisted_sections_and_safe_task_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            private_root = Path(temporary)
            view = review_view()
            view.summary["private_path"] = str(private_root / "packet.json")
            payload = json.loads(
                export_masked_history(
                    view=view,
                    sections=("summary", "history", "summary"),
                    private_roots=(private_root,),
                    exported_at=NOW,
                )
            )

        self.assertEqual({"task", "summary", "history", "exported_at"}, set(payload))
        self.assertEqual(
            {"task_id", "project_id", "worktree_id", "mode", "commit", "branch", "environment_ref"},
            set(payload["task"]),
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(str(private_root), serialized)
        self.assertNotIn("private_path", serialized)

    def test_export_omits_prompt_transcript_commands_secrets_raw_fields_and_absolute_paths(self) -> None:
        view = review_view()
        view.summary.update(
            {
                "prompt": "system prompt",
                "transcript": "private transcript",
                "command_output": "secret command output",
                "api_key": "secret-value",
                "raw_payload": {"html": "<script>"},
                "object_path": "/private/object/path",
            }
        )
        view.history[0]["references"].update(
            {"secret_token": "abc", "raw": "bytes", "note": "read /etc/shadow"}
        )

        payload = json.loads(
            export_masked_history(
                view=view,
                sections=("summary", "history"),
                private_roots=(),
                exported_at=NOW,
            )
        )
        serialized = json.dumps(payload, ensure_ascii=False).casefold()

        for forbidden in (
            "prompt",
            "transcript",
            "command_output",
            "api_key",
            "raw_payload",
            "object_path",
            "secret_token",
            '"raw"',
            "/etc/shadow",
            "/private/object/path",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_export_rejects_unknown_sections_and_accepts_only_the_five_public_sections(self) -> None:
        view = review_view()
        for section in ("summary", "verification", "guarantees", "history", "decision"):
            with self.subTest(section=section):
                payload = json.loads(
                    export_masked_history(
                        view=view,
                        sections=(section,),
                        private_roots=(),
                        exported_at=NOW,
                    )
                )
                self.assertIn(section, payload)
        with self.assertRaisesRegex(ValueError, "unknown export sections"):
            export_masked_history(
                view=view,
                sections=("harness",),
                private_roots=(),
                exported_at=NOW,
            )

    def test_default_dashboard_service_uses_the_same_allowlisted_masked_export(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            services, catalog = _dashboard_services(root / "data")
            try:
                view = review_view()
                view.summary["raw_payload"] = "must not leave service boundary"
                exported = services.export_history(view, ("summary", "history"))
            finally:
                catalog.close()

        payload = json.loads(exported)
        self.assertEqual({"task", "summary", "history", "exported_at"}, set(payload))
        self.assertNotIn("raw_payload", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()

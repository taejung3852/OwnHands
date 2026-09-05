from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from devharness.review import run_m1_demo


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = Path(__file__).parent / "fixtures/hwpx_package_inspection.json"
MATRIX_PATH = REPOSITORY_ROOT / "docs/product/guarantee-matrix.v1.json"


class M1VerticalPocTests(unittest.TestCase):
    def test_fixture_flows_from_event_to_report_and_html_without_raw_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output = root / "review.html"

            result = run_m1_demo(root / "data", output, FIXTURE_PATH, MATRIX_PATH)
            html = output.read_text(encoding="utf-8")
            report = json.loads(result.report_path.read_text(encoding="utf-8"))

            self.assertEqual("supported", result.report["claim_results"][0]["verdict"])
            self.assertEqual(result.report, report)
            self.assertIn("관련 테스트를 실행했다", html)
            self.assertIn(result.evidence_id, html)
            self.assertIn("수집 완전성: Unobserved", html)
            self.assertIn("Task mode: imported", html)
            self.assertIn("Imported Task", html)
            self.assertIn("Event head 3 / Projection 3", html)
            self.assertNotIn("raw package bytes", html)
            self.assertNotIn("m1-demo-secret", html)
            self.assertNotIn("[REDACTED]", html)

    def test_html_escapes_fixture_derived_text(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        fixture["evidence"]["exact_scope"] = "<script>alert('scope')</script>"

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            fixture_path = root / "fixture.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            output = root / "review.html"

            run_m1_demo(root / "data", output, fixture_path, MATRIX_PATH)
            html = output.read_text(encoding="utf-8")

            self.assertNotIn("<script>", html)
            self.assertIn("&lt;script&gt;", html)

    def test_fixture_is_non_sensitive_and_raw_storage_stays_outside_repository(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        serialized = json.dumps(fixture, ensure_ascii=False).lower()

        self.assertNotIn("authorization", serialized)
        self.assertNotIn("password", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertFalse(str(REPOSITORY_ROOT) in fixture["task"]["cwd"])


if __name__ == "__main__":
    unittest.main()

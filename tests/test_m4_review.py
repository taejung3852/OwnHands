from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from devharness.assurance import fingerprint
from devharness.m4_review import (
    M4ReviewError,
    render_review,
    run_m4_fixture,
    validate_packet_document,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/product/assurance-packet.schema.json"
EXAMPLE = ROOT / "docs/product/assurance-packet.example.json"
NOW = "2026-09-06T12:00:00+00:00"


class M4ReviewTests(unittest.TestCase):
    def test_fixture_packet_has_strict_schema_shape_and_reference_closure(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            result = run_m4_fixture(
                root / "raw-evidence",
                root / "assurance-packet.json",
                root / "review.html",
                observed_at=NOW,
            )
            packet = json.loads((root / "assurance-packet.json").read_text(encoding="utf-8"))
            schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
            self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(set(schema["required"]), set(packet))
            validate_packet_document(packet)
            self.assertEqual(packet["fingerprint"], result["packet_fingerprint"])
            self.assertEqual("soft_block", packet["gate"]["decision"])
            self.assertTrue(set(packet["evidence_refs"]) >= set(packet["gate"]["evidence_refs"]))
            changed = copy.deepcopy(packet)
            changed["unexpected"] = True
            with self.assertRaisesRegex(M4ReviewError, "unexpected"):
                validate_packet_document(changed)

    def test_example_is_a_valid_synthetic_packet(self) -> None:
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        validate_packet_document(example)
        self.assertEqual("managed", example["task"]["mode"])
        self.assertNotIn("/Users/", json.dumps(example))

    def test_review_escapes_values_orders_sections_and_omits_raw_output(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            run_m4_fixture(root / "raw", root / "packet.json", root / "review.html", observed_at=NOW)
            packet = json.loads((root / "packet.json").read_text(encoding="utf-8"))
            packet["task"]["goal"] = '<script>alert("m4")</script>'
            packet["fingerprint"] = fingerprint({key: value for key, value in packet.items() if key != "fingerprint"})
            review = render_review(packet)
            self.assertNotIn("<script>", review)
            self.assertIn("&lt;script&gt;", review)
            headings = ["Summary", "Impact", "Tests", "Gaps", "Gate", "Evidence"]
            positions = [review.index(f">{heading}<") for heading in headings]
            self.assertEqual(sorted(positions), positions)
            raw_output = (root / "raw" / "before-test-output.txt").read_text(encoding="utf-8")
            self.assertIn("Ran 1 test", raw_output)
            for rendered in (review, (root / "packet.json").read_text(encoding="utf-8")):
                self.assertNotIn("Ran 1 test", rendered)
                self.assertNotIn("raw_output", rendered)

    def test_review_rejects_unresolved_evidence_reference(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            run_m4_fixture(root / "raw", root / "packet.json", root / "review.html", observed_at=NOW)
            packet = json.loads((root / "packet.json").read_text(encoding="utf-8"))
            packet["gate"]["evidence_refs"].append("evidence:missing")
            with self.assertRaisesRegex(M4ReviewError, "reference closure"):
                render_review(packet)


if __name__ == "__main__":
    unittest.main()

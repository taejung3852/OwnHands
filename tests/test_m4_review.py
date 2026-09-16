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
SCHEMA = ROOT / "docs/legacy/product/assurance-packet.schema.json"
EXAMPLE = ROOT / "docs/legacy/product/assurance-packet.example.json"
NOW = "2026-09-06T12:00:00+00:00"


class M4ReviewTests(unittest.TestCase):
    def packet_fixture(self, root: Path) -> dict:
        run_m4_fixture(root / "raw", root / "packet.json", root / "review.html", observed_at=NOW)
        return json.loads((root / "packet.json").read_text(encoding="utf-8"))

    @staticmethod
    def resign_packet(packet: dict) -> None:
        section_names = (
            "contract_snapshot", "restore_point", "restore_verification", "impact", "test_design",
            "before", "after", "comparison", "gaps", "gate",
        )
        sections = {name: packet[name] for name in section_names}
        packet["input_fingerprint"] = fingerprint(
            {
                "contract_id": packet["contract_id"],
                "contract_fingerprint": packet["contract_fingerprint"],
                "sections": sections,
                "evidence_refs": packet["evidence_refs"],
            }
        )
        packet["packet_id"] = "assurance:" + packet["input_fingerprint"].removeprefix("sha256:")
        packet["fingerprint"] = fingerprint({key: value for key, value in packet.items() if key != "fingerprint"})

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
            review = render_review(packet)
            self.assertNotIn("<script>", review)
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
            packet["gate"]["fingerprint"] = fingerprint({key: value for key, value in packet["gate"].items() if key != "fingerprint"})
            self.resign_packet(packet)
            with self.assertRaisesRegex(M4ReviewError, "reference closure|Gate.*authoritative"):
                render_review(packet)

    def test_runtime_validation_rejects_nested_fingerprint_reference_and_patch_attacks(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            original = self.packet_fixture(root)
            attacks = []
            stale_result = copy.deepcopy(original)
            stale_result["after"]["receipts"][0]["result"] = "fail"
            attacks.append(stale_result)
            wrong_ref = copy.deepcopy(original)
            wrong_ref["comparison"]["after_ref"] = "sha256:" + "a" * 64
            wrong_ref["comparison"]["fingerprint"] = fingerprint({key: value for key, value in wrong_ref["comparison"].items() if key != "fingerprint"})
            self.resign_packet(wrong_ref)
            attacks.append(wrong_ref)
            wrong_patch = copy.deepcopy(original)
            wrong_patch["after"]["receipts"][0]["target_patch_hash"] = "sha256:" + "b" * 64
            wrong_patch["after"]["fingerprint"] = fingerprint({key: value for key, value in wrong_patch["after"].items() if key != "fingerprint"})
            self.resign_packet(wrong_patch)
            attacks.append(wrong_patch)
            caller_pass = copy.deepcopy(original)
            caller_pass["gate"].update({"initial_decision": "pass", "decision": "pass", "basis": "observed", "soft_reasons": []})
            caller_pass["gate"]["fingerprint"] = fingerprint({key: value for key, value in caller_pass["gate"].items() if key != "fingerprint"})
            self.resign_packet(caller_pass)
            attacks.append(caller_pass)
            for index, attacked in enumerate(attacks):
                with self.subTest(attack=index), self.assertRaisesRegex(M4ReviewError, "fingerprint|reference|patch|authoritative|Gate"):
                    render_review(attacked)

    def test_runtime_validation_rejects_gap_gate_inconsistency_even_when_resigned(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            packet = self.packet_fixture(root)
            packet["gaps"]["gaps"] = [
                {
                    "gap_id": "gap:forged",
                    "kind": "no_adequate_test",
                    "required": True,
                    "criterion_id": "tests_pass",
                    "reason": "forged gap",
                }
            ]
            packet["gaps"]["fingerprint"] = fingerprint({key: value for key, value in packet["gaps"].items() if key != "fingerprint"})
            self.resign_packet(packet)
            with self.assertRaisesRegex(M4ReviewError, "gap.*authoritative"):
                validate_packet_document(packet)


if __name__ == "__main__":
    unittest.main()

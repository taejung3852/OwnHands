import unittest

from harness import summarize_harness


class HarnessSummaryTests(unittest.TestCase):
    def test_context_and_controls_are_separate(self):
        self.assertEqual(
            {"active_context": ["AGENTS.md"], "active_controls": ["sandbox"]},
            summarize_harness(["AGENTS.md"], ["sandbox"]),
        )

    def test_mixed_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "both"):
            summarize_harness(["shared"], ["shared"])


if __name__ == "__main__":
    unittest.main()

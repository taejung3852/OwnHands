from __future__ import annotations

import unittest
from pathlib import Path

from devharness.context_architecture import lint_context


class SkillDefinitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.skills_dir = self.repo_root / "skills"

    def test_using_ownhands_skill_exists_and_is_clean(self) -> None:
        skill_path = self.skills_dir / "using-ownhands" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: using-ownhands", content)
        self.assertIn("description:", content)

        # Run lint_context on the skill file
        sources = [
            {
                "source_id": "skill:using-ownhands",
                "path": "skills/using-ownhands/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_context_validation_skill_exists_and_is_clean(self) -> None:
        skill_path = self.skills_dir / "context-validation" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: context-validation", content)
        self.assertIn("context.lint", content)

        # Run lint_context on the skill file
        sources = [
            {
                "source_id": "skill:context-validation",
                "path": "skills/context-validation/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_harness_profiler_skill_exists_and_is_clean(self) -> None:
        skill_path = self.skills_dir / "harness-profiler" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: harness-profiler", content)
        self.assertIn("harness.profile", content)

        sources = [
            {
                "source_id": "skill:harness-profiler",
                "path": "skills/harness-profiler/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_execution_control_skill_exists_and_is_clean(self) -> None:
        skill_path = self.skills_dir / "execution-control" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: execution-control", content)

        sources = [
            {
                "source_id": "skill:execution-control",
                "path": "skills/execution-control/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_test_assurance_skill_exists_and_is_clean(self) -> None:
        skill_path = self.skills_dir / "test-assurance" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: test-assurance", content)

        sources = [
            {
                "source_id": "skill:test-assurance",
                "path": "skills/test-assurance/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_platform_tool_references_exist_and_are_clean(self) -> None:
        references = [
            ("ref:antigravity", "skills/using-ownhands/references/antigravity-tools.md"),
            ("ref:codex", "skills/using-ownhands/references/codex-tools.md"),
            ("ref:claude-code", "skills/using-ownhands/references/claude-code-tools.md"),
            ("ref:grok", "skills/using-ownhands/references/grok-tools.md"),
        ]
        for source_id, rel_path in references:
            ref_path = self.repo_root / rel_path
            self.assertTrue(ref_path.is_file(), f"{rel_path} does not exist")
            result = lint_context(
                self.repo_root,
                [{"source_id": source_id, "path": rel_path, "source_type": "reference"}],
            )
            self.assertEqual(
                result["findings"],
                [],
                f"Findings detected in {rel_path}: {result['findings']}",
            )

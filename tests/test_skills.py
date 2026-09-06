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

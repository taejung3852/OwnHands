from __future__ import annotations

import re
import unittest
from pathlib import Path

from devharness.context_architecture import lint_context
from devharness.plugin import discover_skills


def parse_frontmatter(content: str) -> dict[str, str]:
    """Lightweight stdlib-only frontmatter parser extracting YAML key-value pairs."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, val = line.split(":", 1)
            metadata[key.strip()] = val.strip().strip('"').strip("'")
    return metadata


class SkillDefinitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.skills_dir = self.repo_root / "skills"
        self.legacy_skills_dir = self.repo_root / "legacy" / "skills"

    # --- Section 1: New Lifecycle Skills (Pure stdlib-based validation) ---

    def test_using_ownhands_router_skill_definition(self) -> None:
        skill_path = self.skills_dir / "using-ownhands" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        self.assertEqual(meta.get("name"), "using-ownhands")
        self.assertIn("STAY DORMANT", meta.get("description", ""))
        self.assertIn("work-map", content)
        self.assertIn("verification-spec", content)
        self.assertIn("baseline", content)
        self.assertIn("review", content)
        self.assertIn("dashboard", content)

    def test_work_map_skill_definition(self) -> None:
        skill_path = self.skills_dir / "work-map" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        self.assertEqual(meta.get("name"), "work-map")
        self.assertIn("STAY DORMANT", meta.get("description", ""))
        self.assertIn("decomposed into concrete work items", meta.get("description", ""))

    def test_verification_spec_skill_definition_and_references(self) -> None:
        skill_path = self.skills_dir / "verification-spec" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        self.assertEqual(meta.get("name"), "verification-spec")
        self.assertIn("STAY DORMANT", meta.get("description", ""))
        self.assertIn("for a defined work item", meta.get("description", ""))

        # Verify all 3 required references exist
        ref_dir = self.skills_dir / "verification-spec" / "references"
        self.assertTrue((ref_dir / "spec-template.md").is_file())
        self.assertTrue((ref_dir / "criteria-guide.md").is_file())
        self.assertTrue((ref_dir / "tdd-mapping.md").is_file())

    def test_baseline_skill_definition_and_references(self) -> None:
        skill_path = self.skills_dir / "baseline" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        self.assertEqual(meta.get("name"), "baseline")
        self.assertIn("STAY DORMANT", meta.get("description", ""))

        ref_dir = self.skills_dir / "baseline" / "references"
        self.assertTrue((ref_dir / "worktree-guide.md").is_file())

    def test_review_skill_definition_and_references(self) -> None:
        skill_path = self.skills_dir / "review" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        self.assertEqual(meta.get("name"), "review")
        self.assertIn("STAY DORMANT", meta.get("description", ""))
        self.assertIn("Requires an approved spec for formal review", meta.get("description", ""))

        ref_dir = self.skills_dir / "review" / "references"
        self.assertTrue((ref_dir / "observation-report-template.md").is_file())

    def test_dashboard_skill_definition(self) -> None:
        skill_path = self.skills_dir / "dashboard" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        self.assertEqual(meta.get("name"), "dashboard")
        self.assertIn("STAY DORMANT", meta.get("description", ""))
        self.assertIn("for a stored review", meta.get("description", ""))

    def test_active_skills_exact_contents_and_discovery(self) -> None:
        expected_active_skills = {
            "baseline",
            "dashboard",
            "review",
            "using-ownhands",
            "verification-spec",
            "work-map",
        }
        actual_active_dirs = {
            p.name for p in self.skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
        }
        self.assertEqual(actual_active_dirs, expected_active_skills)

        discovered = discover_skills(self.repo_root)
        discovered_names = {item["name"] for item in discovered}
        self.assertEqual(discovered_names, expected_active_skills)

        legacy_names = {"context-validation", "execution-control", "harness-profiler", "test-assurance"}
        self.assertTrue(expected_active_skills.isdisjoint(legacy_names))
        for legacy_name in legacy_names:
            self.assertFalse((self.skills_dir / legacy_name).exists(), f"{legacy_name} should not exist in active skills")

    # --- Section 2: Legacy Skills Discovery Isolation ---

    def test_legacy_skills_isolated_in_legacy_directory(self) -> None:
        legacy_skills = [
            "context-validation",
            "execution-control",
            "harness-profiler",
            "test-assurance",
        ]
        self.assertTrue(self.legacy_skills_dir.is_dir())
        for skill_name in legacy_skills:
            skill_path = self.legacy_skills_dir / skill_name / "SKILL.md"
            self.assertTrue(skill_path.is_file(), f"Legacy skill {skill_name} must exist under legacy/skills")
            content = skill_path.read_text(encoding="utf-8")
            meta = parse_frontmatter(content)
            self.assertEqual(meta.get("name"), skill_name)
            desc = meta.get("description", "")
            self.assertTrue(
                desc.startswith("[Legacy / Compat Only]"),
                f"Legacy skill {skill_name} must begin with '[Legacy / Compat Only]', got: {desc}",
            )
            self.assertIn("Do not invoke for new lifecycle workflows.", desc)

    def test_active_skills_do_not_reference_legacy_skills(self) -> None:
        legacy_skill_names = ["context-validation", "execution-control", "harness-profiler", "test-assurance"]
        for md_file in self.skills_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            for legacy_name in legacy_skill_names:
                self.assertNotIn(
                    f"skills/{legacy_name}",
                    content,
                    f"Active skill file {md_file.relative_to(self.repo_root)} must not reference legacy skill path {legacy_name}",
                )

    # --- Section 3: Legacy Compatibility Regression Checks ---

    def test_using_ownhands_skill_is_clean_with_context_linter(self) -> None:
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
        skill_path = self.legacy_skills_dir / "context-validation" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: context-validation", content)
        self.assertIn("context.lint", content)

        sources = [
            {
                "source_id": "skill:context-validation",
                "path": "legacy/skills/context-validation/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_harness_profiler_skill_exists_and_is_clean(self) -> None:
        skill_path = self.legacy_skills_dir / "harness-profiler" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: harness-profiler", content)
        self.assertIn("harness.profile", content)

        sources = [
            {
                "source_id": "skill:harness-profiler",
                "path": "legacy/skills/harness-profiler/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_execution_control_skill_exists_and_is_clean(self) -> None:
        skill_path = self.legacy_skills_dir / "execution-control" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: execution-control", content)

        sources = [
            {
                "source_id": "skill:execution-control",
                "path": "legacy/skills/execution-control/SKILL.md",
                "source_type": "skill",
            }
        ]
        result = lint_context(self.repo_root, sources)
        self.assertEqual(result["findings"], [])

    def test_test_assurance_skill_exists_and_is_clean(self) -> None:
        skill_path = self.legacy_skills_dir / "test-assurance" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: test-assurance", content)

        sources = [
            {
                "source_id": "skill:test-assurance",
                "path": "legacy/skills/test-assurance/SKILL.md",
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


if __name__ == "__main__":
    unittest.main()

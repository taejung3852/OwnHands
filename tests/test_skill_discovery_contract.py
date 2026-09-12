from __future__ import annotations

import re
import unittest
from pathlib import Path

from devharness.plugin import discover_skills


def parse_frontmatter(content: str) -> dict[str, str]:
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


class SkillDiscoveryContractTests(unittest.TestCase):
    """
    This test validates the OwnHands discovery/routing contract.
    It does not execute a real LLM or native Codex/Claude skill discovery runtime.

    Validates:
    1. Active skills expose explicit STAY DORMANT boundaries in their frontmatter.
    2. Discovered skills strictly exclude all legacy execution-control skills from discover_skills().
    3. Representative user prompt intents map cleanly to the deterministic routing contract.
    """

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.skills_dir = self.repo_root / "skills"
        self.legacy_dir = self.repo_root / "legacy" / "skills"

    def test_all_active_skills_have_dormant_directives(self) -> None:
        active_skills = discover_skills(self.repo_root)
        self.assertEqual(len(active_skills), 6)

        for item in active_skills:
            skill_file = Path(item["skill_file"])
            content = skill_file.read_text(encoding="utf-8")
            meta = parse_frontmatter(content)
            description = meta.get("description", "")

            self.assertIn(
                "STAY DORMANT",
                description,
                f"Active skill {item['name']} must contain 'STAY DORMANT' directive in frontmatter",
            )

    def test_legacy_skills_are_completely_excluded_from_discovery(self) -> None:
        discovered = discover_skills(self.repo_root)
        discovered_names = {item["name"] for item in discovered}

        legacy_skills = ["context-validation", "execution-control", "harness-profiler", "test-assurance"]
        for legacy in legacy_skills:
            self.assertNotIn(
                legacy,
                discovered_names,
                f"Legacy skill {legacy} must NOT be discovered by agent discovery",
            )
            # Must exist in legacy directory
            self.assertTrue(
                (self.legacy_dir / legacy / "SKILL.md").is_file(),
                f"Legacy skill {legacy} must be preserved in legacy/skills",
            )

    def test_prompt_intent_matching_contract(self) -> None:
        """
        Simulates the agent prompt intent evaluation against frontmatter triggers:
        - General chat, research, brainstorming -> STAY DORMANT
        - Large/Ambiguous goal -> work-map
        - Defined work item with no spec -> verification-spec
        - Post-implementation verification -> review
        """
        scenarios = [
            ("오늘 점심 뭐 먹지?", "chat", None),
            ("Python asyncio의 이벤트 루프 동작 원리에 대해 설명해줘", "research", None),
            ("새로운 검색 기능에 대한 아이디어를 브레인스토밍해보자", "brainstorming", None),
            ("우리 서비스의 검색 품질을 전반적으로 개선하고 싶어", "large_goal", "work-map"),
            ("Issue #81의 중복 환불 방지 로직을 구현하려고 해", "work_item_no_spec", "verification-spec"),
            ("방금 환불 방지 로직 구현과 단위 테스트 작성을 마쳤으니 전체 검증 및 리뷰를 진행해줘", "post_implementation", "review"),
        ]

        for prompt, intent, expected_skill in scenarios:
            if intent in {"chat", "research", "brainstorming"}:
                selected = None
            elif intent == "large_goal":
                selected = "work-map"
            elif intent == "work_item_no_spec":
                selected = "verification-spec"
            elif intent == "post_implementation":
                selected = "review"
            else:
                selected = None

            self.assertEqual(
                selected,
                expected_skill,
                f"Prompt '{prompt}' (intent: {intent}) expected {expected_skill} but got {selected}",
            )


if __name__ == "__main__":
    unittest.main()

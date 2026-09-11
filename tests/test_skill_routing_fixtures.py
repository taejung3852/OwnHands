from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class LifecycleRoutingContext:
    intent: str
    phase: Literal["exploration", "planning", "pre_implementation", "in_progress", "post_implementation"]
    work_item_defined: bool = False
    work_item_oversized: bool = False
    spec_state: Literal["none", "draft", "approved", "stale"] = "none"
    baseline_state: Literal["none", "valid", "stale"] = "none"
    has_before_observation: bool = False
    implementation_complete: bool = False
    review_state: Literal["none", "current", "stale"] = "none"
    dashboard_presentation: Literal["none", "current", "stale"] = "none"
    wants_visualization: bool = False
    spec_approval_matches: bool = True
    code_state_matches: bool = True
    environment_matches: bool = True
    test_meaning_matches: bool = True


def route_lifecycle_contract(context: LifecycleRoutingContext) -> str | None:
    """
    Authoritative deterministic routing contract policy for OwnHands (#81).
    Evaluates: Explicit user intent > Persisted lifecycle state > Repository facts.
    Returns: The single next skill name, or None (Dormant).
    """
    # 1. Dormant Conditions
    if context.intent in {
        "conversation/general",
        "concept_question",
        "research",
        "brainstorming_only",
    }:
        return None

    if context.phase == "in_progress" or (
        context.phase != "post_implementation" and context.intent == "implementation_in_progress"
    ):
        return None

    # 2. Freshness & Invalidation overrides
    if context.spec_state == "stale":
        return "verification-spec"

    if context.phase == "pre_implementation" and context.baseline_state == "stale":
        return "baseline"

    if context.phase == "post_implementation" and context.review_state == "stale":
        return "review"

    # 3. Dashboard presentation on-demand
    if context.wants_visualization and context.review_state in {"current", "stale"}:
        if context.dashboard_presentation in {"none", "stale"}:
            return "dashboard"
        return None  # Cache hit: current presentation is read statically without skill invocation

    # 4. Post-implementation review & verification
    if context.phase == "post_implementation" or context.intent == "implementation_completed":
        if context.spec_state != "approved":
            # Formal review strictly disallows missing spec; routes to spec
            return "verification-spec"
        # If valid before baseline is missing, review orchestrates with missing_before / gap
        return "review"

    # 5. Work breakdown vs Specification
    if context.work_item_oversized or (context.intent == "large_goal" and not context.work_item_defined):
        return "work-map"

    if context.work_item_defined:
        if context.spec_state in {"none", "draft"}:
            return "verification-spec"

        if context.spec_state == "approved":
            if context.phase == "pre_implementation":
                can_reuse_baseline = (
                    context.baseline_state == "valid"
                    and context.spec_approval_matches
                    and context.code_state_matches
                    and context.environment_matches
                    and context.test_meaning_matches
                )
                if not can_reuse_baseline:
                    return "baseline"
                return None  # Baseline ready, move to coding (dormant)

    return None


class SkillRoutingFixtureTests(unittest.TestCase):
    """
    Validates that the deterministic routing policy contract adheres strictly
    to the 16 scenarios, freshness transitions, and edge cases specified in Issue #81.
    """

    # --- Group 1: Dormant Scenarios ---

    def test_dormant_on_general_conversation(self) -> None:
        ctx = LifecycleRoutingContext(intent="conversation/general", phase="exploration")
        self.assertIsNone(route_lifecycle_contract(ctx))

    def test_dormant_on_concept_question(self) -> None:
        ctx = LifecycleRoutingContext(intent="concept_question", phase="exploration")
        self.assertIsNone(route_lifecycle_contract(ctx))

    def test_dormant_on_general_research(self) -> None:
        ctx = LifecycleRoutingContext(intent="research", phase="exploration")
        self.assertIsNone(route_lifecycle_contract(ctx))

    def test_dormant_on_brainstorming_only(self) -> None:
        ctx = LifecycleRoutingContext(intent="brainstorming_only", phase="exploration")
        self.assertIsNone(route_lifecycle_contract(ctx))

    def test_dormant_during_active_implementation(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="implementation_in_progress",
            phase="in_progress",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="valid",
        )
        self.assertIsNone(route_lifecycle_contract(ctx))

    # --- Group 2: Active Lifecycle Transitions ---

    def test_routes_to_work_map_when_goal_is_ambiguous_or_oversized(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="large_goal",
            phase="planning",
            work_item_defined=False,
            work_item_oversized=True,
        )
        self.assertEqual(route_lifecycle_contract(ctx), "work-map")

    def test_routes_to_verification_spec_when_work_item_defined_without_spec(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="start_work_item",
            phase="planning",
            work_item_defined=True,
            work_item_oversized=False,
            spec_state="none",
        )
        self.assertEqual(route_lifecycle_contract(ctx), "verification-spec")

    def test_routes_to_verification_spec_when_spec_is_draft_unapproved(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="review_spec",
            phase="planning",
            work_item_defined=True,
            spec_state="draft",
        )
        self.assertEqual(route_lifecycle_contract(ctx), "verification-spec")

    def test_routes_to_baseline_when_spec_approved_prior_to_implementation(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="prepare_code",
            phase="pre_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="none",
        )
        self.assertEqual(route_lifecycle_contract(ctx), "baseline")

    def test_routes_to_review_when_implementation_complete_with_approved_spec(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="implementation_completed",
            phase="post_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="valid",
            has_before_observation=True,
            implementation_complete=True,
        )
        self.assertEqual(route_lifecycle_contract(ctx), "review")

    def test_routes_to_dashboard_when_visualization_requested_and_presentation_needed(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="view_dashboard",
            phase="post_implementation",
            work_item_defined=True,
            spec_state="approved",
            review_state="current",
            dashboard_presentation="none",
            wants_visualization=True,
        )
        self.assertEqual(route_lifecycle_contract(ctx), "dashboard")

    # --- Group 3: Freshness & Edge Cases ---

    def test_dashboard_cache_hit_returns_dormant(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="view_dashboard",
            phase="post_implementation",
            work_item_defined=True,
            spec_state="approved",
            review_state="current",
            dashboard_presentation="current",  # Current presentation exists
            wants_visualization=True,
        )
        # Static read-only UI; skill is NOT invoked
        self.assertIsNone(route_lifecycle_contract(ctx))

    def test_stale_spec_routes_to_verification_spec(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="continue_work",
            phase="planning",
            work_item_defined=True,
            spec_state="stale",
        )
        self.assertEqual(route_lifecycle_contract(ctx), "verification-spec")

    def test_code_change_after_review_marks_review_stale_and_routes_to_review(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="reverify",
            phase="post_implementation",
            work_item_defined=True,
            spec_state="approved",
            review_state="stale",
            implementation_complete=True,
        )
        self.assertEqual(route_lifecycle_contract(ctx), "review")

    def test_pre_implementation_environment_change_routes_to_baseline(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="prepare_code",
            phase="pre_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="stale",
        )
        self.assertEqual(route_lifecycle_contract(ctx), "baseline")

    def test_post_implementation_without_before_observation_does_not_fake_baseline(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="implementation_completed",
            phase="post_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="none",  # No baseline was captured before edits
            has_before_observation=False,
            implementation_complete=True,
        )
        # Time travel is forbidden: routes to review to record missing_before / gap, not baseline
        self.assertEqual(route_lifecycle_contract(ctx), "review")

    def test_formal_review_disallowed_without_approved_spec(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="implementation_completed",
            phase="post_implementation",
            work_item_defined=True,
            spec_state="none",  # No approved spec
            implementation_complete=True,
        )
        # Formal review blocked: must route to verification-spec first
        self.assertEqual(route_lifecycle_contract(ctx), "verification-spec")

    def test_baseline_reuse_requires_all_four_factors(self) -> None:
        # 1. All 4 factors match: baseline is reused, router stays dormant for coding
        ctx_match = LifecycleRoutingContext(
            intent="prepare_code",
            phase="pre_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="valid",
            spec_approval_matches=True,
            code_state_matches=True,
            environment_matches=True,
            test_meaning_matches=True,
        )
        self.assertIsNone(route_lifecycle_contract(ctx_match))

        # 2. Environment differs: baseline cannot be reused, re-captures baseline
        ctx_env_mismatch = LifecycleRoutingContext(
            intent="prepare_code",
            phase="pre_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="valid",
            spec_approval_matches=True,
            code_state_matches=True,
            environment_matches=False,  # Environment changed!
            test_meaning_matches=True,
        )
        self.assertEqual(route_lifecycle_contract(ctx_env_mismatch), "baseline")

        # 3. Test meaning differs: baseline cannot be reused, re-captures baseline
        ctx_test_mismatch = LifecycleRoutingContext(
            intent="prepare_code",
            phase="pre_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="valid",
            spec_approval_matches=True,
            code_state_matches=True,
            environment_matches=True,
            test_meaning_matches=False,  # Test command/params changed!
        )
        self.assertEqual(route_lifecycle_contract(ctx_test_mismatch), "baseline")

    def test_router_never_returns_chained_skills(self) -> None:
        """Every permutation returns either a single known skill string or None."""
        known_skills = {"work-map", "verification-spec", "baseline", "review", "dashboard"}
        test_contexts = [
            LifecycleRoutingContext(intent="conversation/general", phase="exploration"),
            LifecycleRoutingContext(intent="large_goal", phase="planning", work_item_oversized=True),
            LifecycleRoutingContext(intent="start", phase="planning", work_item_defined=True, spec_state="none"),
            LifecycleRoutingContext(intent="code", phase="pre_implementation", work_item_defined=True, spec_state="approved"),
            LifecycleRoutingContext(intent="verify", phase="post_implementation", work_item_defined=True, spec_state="approved", implementation_complete=True),
            LifecycleRoutingContext(intent="dash", phase="post_implementation", work_item_defined=True, review_state="current", wants_visualization=True),
        ]
        for ctx in test_contexts:
            result = route_lifecycle_contract(ctx)
            if result is not None:
                self.assertIn(result, known_skills)
                self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()

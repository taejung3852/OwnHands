import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from devharness.catalog import Catalog
from devharness.events import EventLog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.identity import IdentityRegistry
from devharness.lifecycle.model import fingerprint
from devharness.lifecycle.store import LifecycleStore
from devharness.paths import DataPaths


@dataclass(frozen=True)
class LifecycleRoutingContext:
    intent: str
    phase: Literal["exploration", "planning", "pre_implementation", "in_progress", "post_implementation"]
    work_item_defined: bool = False
    work_item_oversized: bool = False
    spec_state: Literal["none", "draft", "approved", "stale"] = "none"
    baseline_state: Literal["none", "valid", "missing_before", "stale"] = "none"
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
        # Time travel is forbidden: routes to review to prepare missing-Before baseline, not baseline
        self.assertEqual(route_lifecycle_contract(ctx), "review")

    def test_post_implementation_with_missing_before_baseline_routes_to_review(self) -> None:
        ctx = LifecycleRoutingContext(
            intent="implementation_completed",
            phase="post_implementation",
            work_item_defined=True,
            spec_state="approved",
            baseline_state="missing_before",  # Baseline exists with observations=[] + missing_reason
            has_before_observation=False,
            implementation_complete=True,
        )
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


class LifecycleBaselineAndReviewContractTests(unittest.TestCase):
    """
    Directly verifies the #80 machine contract integration for baseline and review:
    1. Formal review strictly requires a VerificationBaseline artifact reference.
    2. Verification baseline with observations=[] requires a non-empty missing_reason.
    3. Under a baseline with observations=[], preserve/improve claims cannot be verified.
    4. Under a baseline with observations=[], current claims can be verified with After evidence alone.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.paths = DataPaths.resolve(Path(self.temp_dir.name) / "data")
        self.catalog = Catalog.open(self.paths)
        self.task = IdentityRegistry(self.catalog).create_task_lifecycle(
            "project", "worktree", "imported", "a" * 40, "main", "/fixture", "env"
        )
        self.store = LifecycleStore(self.catalog)
        self.project_scope = {"project_id": self.task.project_id}
        self.issue = self.store.append(
            "work_issue", "issue:1", self.project_scope,
            {"title": "Test Issue", "source": "test", "content": "Test", "request_refs": []}
        )
        self.issue_scope = {**self.project_scope, "issue_id": "issue:1"}
        self.scope = {**self.issue_scope, "task_id": self.task.task_id, "attempt_id": "attempt:1"}
        self.attempt = self.store.append("attempt", "attempt:1", self.scope, {"issue": self.issue, "previous": None})
        self.store.activate(self.attempt)

        # Code state and environment
        code_body = {
            "code_state_version": 1, "commit": "a" * 40,
            "files": [{"path": "main.py", "origin": "tracked", "kind": "file", "mode": 0o644, "hash": fingerprint("code")}],
            "coverage": "complete", "exclusions": []
        }
        self.code = self.store.append("code_state", "code:1", self.scope, {**code_body, "fingerprint": fingerprint(code_body)})
        pre_code_body = {
            **code_body, "commit": "b" * 40,
            "files": [{"path": "main.py", "origin": "tracked", "kind": "file", "mode": 0o644, "hash": fingerprint("code-pre")}],
        }
        self.code_pre = self.store.append(
            "code_state", "code:pre", self.scope,
            {**pre_code_body, "fingerprint": fingerprint(pre_code_body)},
        )
        # The fixture's environment is known to be unchanged across the edit.
        env_body = {"environment_version": 1, "description": "test-env", "details": {}}
        self.env = self.store.append("environment", "env:1", self.scope, {**env_body, "fingerprint": fingerprint(env_body)})

        # Spec with preserve, improve, and current criteria
        self.spec_data = {
            "issue": self.issue,
            "document": {"path": "docs/spec.md", "text": "# Spec"},
            "criteria": [
                {"id": "crit_preserve", "text": "Preserve existing behavior", "required": False, "comparison": "preserve"},
                {"id": "crit_improve", "text": "Improve latency", "required": False, "comparison": "improve"},
                {"id": "crit_current", "text": "Add new capability", "required": True, "comparison": "current"},
            ]
        }
        self.spec = self.store.append("spec", "spec:1", self.issue_scope, self.spec_data)
        self.approval = self.store.append(
            "spec_approval", "appr:1", self.issue_scope,
            {"spec": self.spec, "actor": {"kind": "human", "id": "user"}, "decision": "approved", "reason": "ok", "source": "test"}
        )
        self.store.activate(self.spec, approval=self.approval)
        self.counter = 0

    def tearDown(self) -> None:
        self.catalog.close()
        self.temp_dir.cleanup()

    def _create_observation(self, criterion_id: str, phase: str, result: str) -> dict:
        self.counter += 1
        evidence_id = f"ev:{self.counter}"
        test_meaning_hash = fingerprint("meaning_fixture")
        fields = {
            "test_id": "test_fn", "criterion_id": criterion_id, "phase": phase,
            "spec_hash": self.spec["hash"], "code_hash": self.code["hash"],
            "environment_hash": self.env["hash"], "test_meaning": test_meaning_hash
        }
        EvidenceStore(self.catalog, EventLog(self.catalog)).put(
            EvidenceDraft(
                evidence_id, self.scope["task_id"], criterion_id, "test_execution",
                "test_fn", "function", result, "observed", fields, b"stdout log",
                "runner", "not_needed"
            ),
            lambda b: b
        )
        binding = self.store.bind_evidence(f"binding:{self.counter}", self.scope, evidence_id)
        return self.store.append(
            "observation", f"obs:{self.counter}", self.scope,
            {
                "spec": self.spec,
                "spec_approval": self.approval,
                "code_state": self.code,
                "environment": self.env,
                "test_id": "test_fn",
                "criterion_id": criterion_id,
                "phase": phase,
                "test_meaning": test_meaning_hash,
                "result": result,
                "basis": "observed",
                "selection_reason": "test execution",
                "evidence": [binding],
            }
        )

    def test_formal_review_requires_verification_baseline_artifact(self) -> None:
        # Attempting to store a review without a valid baseline artifact reference raises ValueError
        with self.assertRaises(ValueError):
            self.store.append(
                "review", "review:no-base", self.scope,
                {
                    "spec": self.spec,
                    "spec_approval": self.approval,
                    "code_state": self.code,
                    "environment": self.env,
                    "baseline": {"kind": "baseline", "id": "nonexistent", "revision": 1, "hash": "0" * 64},
                    "claims": [],
                    "additional_observations": [],
                    "uncertainties": [],
                    "inferences": [],
                }
            )

    def test_verification_baseline_empty_observations_requires_missing_reason(self) -> None:
        # Empty observations without missing_reason -> fails
        with self.assertRaises(ValueError) as ctx:
            self.store.append(
                "baseline", "base:empty-fail", self.scope,
                {
                    "spec": self.spec,
                    "spec_approval": self.approval,
                    "code_state": self.code_pre,
                    "environment": self.env,
                    "baseline_kind": "verification",
                    "observations": [],
                    "missing_reason": "",
                }
            )
        self.assertIn("missing reason", str(ctx.exception))

        # Empty observations with non-empty missing_reason -> succeeds!
        baseline_ref = self.store.append(
            "baseline", "base:empty-ok", self.scope,
            {
                "spec": self.spec,
                "spec_approval": self.approval,
                "code_state": self.code_pre,
                "environment": self.env,
                "baseline_kind": "verification",
                "observations": [],
                "missing_reason": "Before observation unavailable (implementation completed prior to baseline capture)",
            }
        )
        self.assertEqual(baseline_ref["kind"], "baseline")

    def test_unknown_pre_change_state_is_not_supported_by_v1(self) -> None:
        # missing_reason cannot replace the required pre-change reference.
        # This checks schema rejection, not automatic provenance detection:
        # the skill must never substitute self.code (the After state).
        with self.assertRaises(ValueError):
            self.store.append(
                "baseline", "base:no-reason", self.scope,
                {
                    "spec": self.spec,
                    "spec_approval": self.approval,
                    "code_state": None,
                    "environment": self.env,
                    "baseline_kind": "verification",
                    "observations": [],
                    "missing_reason": "Pre-change CodeState provenance is unavailable",
                }
            )
        with self.assertRaises(ValueError):
            self.store.append(
                "review", "review:unknown-pre-state", self.scope,
                {
                    "spec": self.spec, "spec_approval": self.approval,
                    "code_state": self.code, "environment": self.env,
                    "baseline": None, "claims": [],
                    "additional_observations": [], "uncertainties": [], "inferences": [],
                },
            )

    def test_pre_change_code_state_provenance_allowed_when_available(self) -> None:
        # If genuine pre-change CodeState exists (e.g. pre-edit commit 'b'*40), linking it is supported
        baseline_ref = self.store.append(
            "baseline", "base:with-pre-code", self.scope,
            {
                "spec": self.spec,
                "spec_approval": self.approval,
                "code_state": self.code_pre,  # Genuine pre-change code state linked
                "environment": self.env,
                "baseline_kind": "verification",
                "observations": [],
                "missing_reason": "Pre-change CodeState captured from pre-edit commit, but Before observations were not executed",
            }
        )
        stored_baseline = self.store.get(baseline_ref)
        self.assertEqual(stored_baseline["data"]["code_state"]["id"], "code:pre")
        self.assertEqual(stored_baseline["data"]["observations"], [])

        # Even with pre-change CodeState provenance, lack of Before observations forbids verified comparison claim
        after_obs = self._create_observation("crit_preserve", "after", "pass")
        with self.assertRaises(ValueError) as ctx:
            self.store.append(
                "review", "review:fail-even-with-pre-code", self.scope,
                {
                    "spec": self.spec,
                    "spec_approval": self.approval,
                    "code_state": self.code,
                    "environment": self.env,
                    "baseline": baseline_ref,
                    "claims": [
                        {
                            "criterion_id": "crit_preserve",
                            "status": "verified",
                            "reason": "Attempting verification without Before observations",
                            "observations": [after_obs],
                        }
                    ],
                    "additional_observations": [],
                    "uncertainties": [],
                    "inferences": [],
                }
            )
        self.assertIn("verified comparison claim requires Before evidence", str(ctx.exception))

    def test_missing_before_forbids_preserve_and_improve_verification(self) -> None:
        baseline_ref = self.store.append(
            "baseline", "base:no-before", self.scope,
            {
                "spec": self.spec,
                "spec_approval": self.approval,
                "code_state": self.code_pre,
                "environment": self.env,
                "baseline_kind": "verification",
                "observations": [],
                "missing_reason": "Before observation unavailable",
            }
        )
        after_preserve = self._create_observation("crit_preserve", "after", "pass")
        after_improve = self._create_observation("crit_improve", "after", "pass")

        # 1. Attempting status="verified" for preserve criterion MUST fail
        with self.assertRaises(ValueError) as ctx:
            self.store.append(
                "review", "review:fail-preserve", self.scope,
                {
                    "spec": self.spec,
                    "spec_approval": self.approval,
                    "code_state": self.code,
                    "environment": self.env,
                    "baseline": baseline_ref,
                    "claims": [
                        {"criterion_id": "crit_preserve", "status": "verified", "reason": "Passing after", "observations": [after_preserve]}
                    ],
                    "additional_observations": [], "uncertainties": [], "inferences": [],
                }
            )
        self.assertIn("verified comparison claim requires Before evidence", str(ctx.exception))

        # 2. Attempting status="verified" for improve criterion MUST also fail
        with self.assertRaises(ValueError) as ctx:
            self.store.append(
                "review", "review:fail-improve", self.scope,
                {
                    "spec": self.spec,
                    "spec_approval": self.approval,
                    "code_state": self.code,
                    "environment": self.env,
                    "baseline": baseline_ref,
                    "claims": [
                        {"criterion_id": "crit_improve", "status": "verified", "reason": "Passing after", "observations": [after_improve]}
                    ],
                    "additional_observations": [], "uncertainties": [], "inferences": [],
                }
            )
        self.assertIn("verified comparison claim requires Before evidence", str(ctx.exception))

        # 3. Recording as status="inconclusive" or "unobserved" succeeds and yields review_state="needs-review"
        review_ref = self.store.append(
            "review", "review:ok-inconclusive", self.scope,
            {
                "spec": self.spec,
                "spec_approval": self.approval,
                "code_state": self.code,
                "environment": self.env,
                "baseline": baseline_ref,
                "claims": [
                    {
                        "criterion_id": "crit_preserve",
                        "status": "inconclusive",
                        "reason": "Before observation unavailable; cannot verify preservation",
                        "observations": [after_preserve],
                    },
                    {
                        "criterion_id": "crit_improve",
                        "status": "unobserved",
                        "reason": "Before baseline observation missing",
                        "observations": [],
                    }
                ],
                "additional_observations": [], "uncertainties": [], "inferences": [],
            }
        )
        review_record = self.store.get(review_ref)
        self.assertEqual(review_record["data"]["review_state"], "needs-review")

    def test_current_criterion_can_be_verified_with_after_evidence_alone(self) -> None:
        baseline_ref = self.store.append(
            "baseline", "base:no-before-2", self.scope,
            {
                "spec": self.spec,
                "spec_approval": self.approval,
                "code_state": self.code_pre,
                "environment": self.env,
                "baseline_kind": "verification",
                "observations": [],
                "missing_reason": "Before observation unavailable",
            }
        )
        after_obs = self._create_observation("crit_current", "after", "pass")
        baseline_data = self.store.get(baseline_ref)["data"]
        after_data = self.store.get(after_obs)["data"]
        self.assertEqual(baseline_data["code_state"], self.code_pre)
        self.assertNotEqual(baseline_data["code_state"], after_data["code_state"])

        # For comparison="current", status="verified" succeeds even with no Before observations
        review_ref = self.store.append(
            "review", "review:current-verified", self.scope,
            {
                "spec": self.spec,
                "spec_approval": self.approval,
                "code_state": self.code,
                "environment": self.env,
                "baseline": baseline_ref,
                "claims": [
                    {
                        "criterion_id": "crit_current",
                        "status": "verified",
                        "reason": "New feature passing in After observation",
                        "observations": [after_obs],
                    }
                ],
                "additional_observations": [],
                "uncertainties": [],
                "inferences": [],
            }
        )
        review_record = self.store.get(review_ref)
        self.assertEqual(review_record["data"]["review_state"], "ready")


if __name__ == "__main__":
    unittest.main()

"""F01-F09 acceptance fixtures for the Dashboard WI-02 read model."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from devharness.catalog import Catalog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.events import EventLog
from devharness.identity import IdentityRegistry
from devharness import lifecycle
from devharness.lifecycle.model import fingerprint
from devharness.lifecycle.store import LifecycleStore
import tests.test_claim_evaluation as claim_fixtures

try:
    from devharness.dashboard.read_model import DashboardReadModel, ReadModelError
except ImportError:  # RED must be an assertion failure, not a fixture import error.
    DashboardReadModel = ReadModelError = None


GOLDEN = Path(__file__).parent / "fixtures" / "dashboard" / "view-model-golden.json"


class DashboardReadModelTests(unittest.TestCase):
    """Composition keeps WI-02 fixtures independent of ClaimEvaluationTests inheritance."""

    def setUp(self):
        self.fixture = claim_fixtures.ClaimEvaluationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.readers = []

    def open_reader(self):
        self.assertIsNotNone(DashboardReadModel, "Dashboard read model is not implemented")
        catalog = Catalog.open_readonly(self.fixture.paths)
        store = LifecycleStore.open_readonly(catalog)
        self.readers.extend((store, catalog))
        self.addCleanup(store.close)
        self.addCleanup(catalog.close)
        return DashboardReadModel(catalog, store, self.fixture.task.project_id)

    def inventory(self):
        root = self.fixture.paths.root
        return {
            str(path.relative_to(root)): (
                path.stat().st_mode,
                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
            )
            for path in [root, *root.rglob("*")]
        }

    def append_snapshot(self, review, logical_id):
        return self.fixture.store.append("snapshot", logical_id, self.fixture.scope, {"review": review})

    def counts_snapshot(self):
        f = self.fixture
        spec = copy.deepcopy(f.spec_data)
        spec["contract_version"] = 2
        spec["document"]["text"] += "\nDashboard F02"
        statuses = {
            "required-verified-1": (True, "pass"),
            "required-verified-2": (True, "pass"),
            "required-failed": (True, "fail"),
            "required-inconclusive": (True, "inconclusive"),
            "required-unobserved": (True, None),
            "optional-verified": (False, "pass"),
            "optional-excluded": (False, None),
        }
        spec["criteria"] = [
            {
                "id": criterion_id,
                "text": criterion_id.replace("-", " "),
                "required": required,
                "comparison": "current",
                "checks": [{
                    "check_id": "normal",
                    "statement": "Observe " + criterion_id,
                    "role": "success_condition",
                }],
            }
            for criterion_id, (required, _) in statuses.items()
        ]
        f.spec = f.store.append("spec", "spec:dashboard-counts", f.issue_scope, spec)
        f.approval = f.approve(f.spec)
        for criterion_id, (_, result) in statuses.items():
            if result is None:
                continue
            f.observe(
                result,
                criterion=criterion_id,
                execution_status="error" if result == "inconclusive" else "completed",
                failure_kind="execution_error" if result == "inconclusive" else None,
                test_id="test:" + criterion_id,
            )
        inputs = f.inputs(blockers=[{
            "criterion_id": "required-unobserved",
            "check_id": "normal",
            "reason": "required_external_service_unavailable",
            "source": "fixture:service",
        }])
        inputs["test_plan"] = [
            {
                "criterion_id": criterion_id,
                "check_id": "normal",
                "test_id": "test:" + criterion_id,
                "test_meaning": "d" * 64,
            }
            for criterion_id in statuses
        ]
        inputs["exclusions"] = [{
            "criterion_id": "optional-excluded",
            "reason": "Not selected for this change",
        }]
        inputs["findings"] = [{
            "reason": "A verified run still has a review finding",
            "observations": [next(ref for ref in f.store.evaluate_review(f.scope, inputs)["claims"][0]["observations"])],
        }]
        data = f.store.evaluate_review(f.scope, inputs)
        review = f.store.append("review", "review:dashboard-counts", f.scope, data)
        snapshot = self.append_snapshot(review, "snapshot:dashboard-counts")
        return snapshot, review, data

    def simple_snapshot(self, suffix, *, title, status="unobserved", blocked=False,
                        activate_inputs=False, previous=None):
        f = self.fixture
        project_scope = f.project_scope
        issue_id = "issue:" + suffix
        issue = f.store.append("work_issue", issue_id, project_scope, {
            "title": title,
            "source": "https://example.invalid/issues/" + suffix,
            "content": title,
            "request_refs": [],
        })
        issue_scope = {**project_scope, "issue_id": issue_id}
        attempt_id = "attempt:" + suffix
        scope = {**issue_scope, "task_id": f.task.task_id, "attempt_id": attempt_id}
        attempt = f.store.append("attempt", attempt_id, scope, {"issue": issue, "previous": previous})
        f.store.activate(attempt)
        spec = f.store.append("spec", "spec:" + suffix, issue_scope, {
            "issue": issue,
            "document": {"path": "docs/" + suffix + ".md", "text": title},
            "criteria": [{"id": "c1", "text": title, "required": True, "comparison": "current"}],
        })
        approval = f.store.append("spec_approval", "approval:" + suffix, issue_scope, {
            "spec": spec,
            "actor": {"kind": "human", "id": "owner"},
            "decision": "approved",
            "reason": "Fixture approval",
            "source": "fixture",
        })
        f.store.activate(spec, approval=approval)
        code = f.store.append("code_state", "code:" + suffix, scope, f.code_state_data(suffix))
        environment = f.store.append(
            "environment", "env:" + suffix, scope, lifecycle.environment_state("fixture " + suffix)
        )
        if activate_inputs:
            f.store.activate(code)
            f.store.activate(environment)
        observations = []
        if status == "verified":
            f.counter += 1
            evidence_id = "simple-evidence:" + str(f.counter)
            fields = {
                "test_id": "test:" + suffix,
                "criterion_id": "c1",
                "phase": "after",
                "spec_hash": spec["hash"],
                "code_hash": code["hash"],
                "environment_hash": environment["hash"],
                "test_meaning": "d" * 64,
            }
            EvidenceStore(f.catalog, EventLog(f.catalog)).put(EvidenceDraft(
                evidence_id, f.task.task_id, "c1", "test_execution", "test:" + suffix,
                "fixture", "pass", "observed", fields, b"pass", "fixture", "not_needed"
            ), lambda value: value)
            binding = f.store.bind_evidence("simple-binding:" + str(f.counter), scope, evidence_id)
            observations.append(f.store.append("observation", "simple-observation:" + str(f.counter), scope, {
                "spec": spec,
                "spec_approval": approval,
                "code_state": code,
                "environment": environment,
                "test_id": "test:" + suffix,
                "criterion_id": "c1",
                "phase": "after",
                "test_meaning": "d" * 64,
                "result": "pass",
                "basis": "observed",
                "selection_reason": "Fixture",
                "evidence": [binding],
            }))
        baseline = f.store.append("baseline", "baseline:" + suffix, scope, {
            "spec": spec,
            "spec_approval": approval,
            "code_state": code,
            "environment": environment,
            "baseline_kind": "verification",
            "observations": [],
            "missing_reason": "Before not required",
        })
        review = f.store.append("review", "review:" + suffix, scope, {
            "spec": spec,
            "spec_approval": approval,
            "code_state": code,
            "environment": environment,
            "baseline": baseline,
            "claims": [{"criterion_id": "c1", "status": status,
                        "observations": observations, "reason": "Stored fixture result"}],
            "additional_observations": [],
            "blockers": ([{"criterion_id": "c1", "reason": "required_input_unavailable",
                            "source": "fixture:input"}] if blocked else []),
            "uncertainties": [],
            "inferences": [],
        })
        snapshot = f.store.append("snapshot", "snapshot:" + suffix, scope, {"review": review})
        return {"issue": issue, "attempt": attempt, "scope": scope, "spec": spec,
                "code": code, "environment": environment, "review": review, "snapshot": snapshot}

    def test_f01_f02_snapshot_is_frozen_and_claim_counts_match_manual_golden(self):
        snapshot, review, stored = self.counts_snapshot()
        original_issue = self.fixture.issue
        self.fixture.store.append("work_issue", original_issue["id"], self.fixture.project_scope, {
            "title": "A later title must not leak",
            "source": "https://example.invalid/issues/changed",
            "content": "changed",
            "request_refs": [],
        })
        reader = self.open_reader()
        vm = reader.read_detail(reader.snapshot_key(snapshot))
        golden = json.loads(GOLDEN.read_text())
        self.assertEqual({name: vm[name] for name in golden}, golden)
        self.assertEqual(vm["issue"]["ref"], original_issue)
        self.assertEqual(vm["issue"]["title"], "Widget")
        self.assertEqual(vm["review_state"], stored["review_state"])
        self.assertEqual(vm["review_ref"], review)
        self.assertEqual(len(vm["claims"]), 7)

    def test_f03_problem_index_keeps_stored_causes_and_priority(self):
        snapshot, _, _ = self.counts_snapshot()
        reader = self.open_reader()
        vm = reader.read_detail(reader.snapshot_key(snapshot))
        kinds = [problem["kind"] for problem in vm["problems"]]
        self.assertEqual(kinds[0], "blocker")
        self.assertIn("failure", kinds)
        self.assertIn("inconclusive", kinds)
        self.assertIn("unobserved", kinds)
        self.assertIn("finding", kinds)
        self.assertIn("excluded", kinds)
        self.assertEqual(vm["remaining_problem_count"], max(0, len(vm["problems"]) - 3))
        self.assertEqual(len({(p["kind"], json.dumps(p["sources"], sort_keys=True))
                              for p in vm["problems"]}), len(vm["problems"]))

    def test_f02_required_zero_and_legacy_review_do_not_invent_completion_or_checks(self):
        f = self.fixture
        f.configure(optional=True)
        inputs = f.inputs()
        inputs["exclusions"] = [{"criterion_id": "c1", "reason": "Outside this change"}]
        review = f.store.append("review", "review:required-zero", f.scope,
                                f.store.evaluate_review(f.scope, inputs))
        snapshot = self.append_snapshot(review, "snapshot:required-zero")
        legacy = self.simple_snapshot("legacy", title="Legacy review", status="verified")
        reader = self.open_reader()
        zero = reader.read_detail(reader.snapshot_key(snapshot))
        old = reader.read_detail(reader.snapshot_key(legacy["snapshot"]))
        self.assertEqual(zero["counts"]["required"]["total"], 0)
        self.assertTrue(zero["required_complete"])
        self.assertEqual(zero["counts"]["excluded_optional_count"], 1)
        self.assertEqual(old["source_contract_version"], 1)
        self.assertEqual(old["claims"][0]["checks"], [])
        self.assertEqual(len(old["claims"][0]["observations"]), 1)
        legacy_key = old["claims"][0]["observations"][0]["evidence_links"][0]["evidence_key"]
        self.assertEqual(reader.read_evidence(old["snapshot_key"], legacy_key)["availability"], "available")

    def test_f04_comparisons_keep_missing_before_conflicts_and_every_run(self):
        f = self.fixture
        f.configure("preserve", checks=("normal", "retry"))
        f.observe("pass", phase="before", check="normal", execution_id="same-before")
        f.observe("fail", phase="before", check="normal", execution_id="same-before")
        f.observe("pass", check="normal")
        f.observe("pass", check="retry")
        data = f.evaluate(before=[])
        review = f.store.append("review", "review:f04", f.scope, data)
        snapshot = self.append_snapshot(review, "snapshot:f04")
        reader = self.open_reader()
        vm = reader.read_detail(reader.snapshot_key(snapshot))
        claim = vm["claims"][0]
        self.assertEqual(claim["status"], data["claims"][0]["status"])
        self.assertEqual(sum(len(check["after"]) for check in claim["checks"]), 2)
        self.assertEqual(sum(len(check["before"]) for check in claim["checks"]), 2)
        self.assertTrue(claim["checks"][0]["conflicts"])
        self.assertFalse(claim["checks"][1]["comparisons"][0]["comparable"])

    def test_f04_additional_observation_remains_drillable_without_a_claim(self):
        f = self.fixture
        f.configure("current")
        f.observe()
        extra = f.observe("fail", check="outside", criterion=None)
        review = f.store.append("review", "review:f04-additional", f.scope, f.evaluate())
        snapshot = self.append_snapshot(review, "snapshot:f04-additional")
        reader = self.open_reader()
        vm = reader.read_detail(reader.snapshot_key(snapshot))
        self.assertEqual([item["ref"] for item in vm["additional_observations"]], [extra])
        evidence_key = vm["additional_observations"][0]["evidence_links"][0]["evidence_key"]
        evidence = reader.read_evidence(vm["snapshot_key"], evidence_key)
        self.assertIsNone(evidence["claim_id"])
        self.assertEqual(evidence["check_id"], "outside")

    def test_f05_context_uses_registered_current_inputs_without_rewriting_snapshot(self):
        f = self.fixture
        f.configure("current")
        f.observe()
        review = f.store.append("review", "review:f05", f.scope, f.evaluate())
        snapshot = self.append_snapshot(review, "snapshot:f05")
        reader = self.open_reader()
        key = reader.snapshot_key(snapshot)
        unknown = reader.read_context(key)
        self.assertEqual(unknown["freshness"], "unknown")
        f.store.activate(f.code)
        f.store.activate(f.env)
        recaptured_code = f.store.append("code_state", "code:recaptured", f.scope, f.code_state_data())
        recaptured_env = f.store.append(
            "environment", "env:recaptured", f.scope, lifecycle.environment_state("fixture")
        )
        f.store.activate(recaptured_code)
        f.store.activate(recaptured_env)
        self.assertEqual(reader.read_context(key)["freshness"], "current")
        before = reader.read_detail(key)["counts"]
        f.observe()
        newer = self.append_snapshot(review, "snapshot:f05-newer")
        after = reader.read_detail(key)
        self.assertEqual(after["counts"], before)
        self.assertTrue(after["context"]["new_evidence_available"])
        self.assertEqual(after["context"]["newer_snapshot_key"], reader.snapshot_key(newer))
        next_attempt = f.store.append("attempt", "attempt:f05-next", {
            **f.issue_scope, "task_id": f.task.task_id, "attempt_id": "attempt:f05-next"
        }, {"issue": f.issue, "previous": f.attempt})
        f.store.activate(next_attempt)
        changed = reader.read_context(key)
        self.assertEqual(changed["freshness"], "unknown")
        self.assertEqual(changed["reasons"], ["attempt_changed"])
        self.assertTrue(changed["superseded_attempt"])

    def test_f05_conflicting_current_test_meaning_is_unknown_not_self_copied(self):
        f = self.fixture
        f.configure("current")
        f.observe()
        review = f.store.append("review", "review:f05-meaning", f.scope, f.evaluate())
        snapshot = self.append_snapshot(review, "snapshot:f05-meaning")
        f.store.activate(f.code)
        f.store.activate(f.env)
        f.observe(meaning="e" * 64)
        reader = self.open_reader()
        context = reader.read_context(reader.snapshot_key(snapshot))
        self.assertEqual(context["freshness"], "unknown")
        self.assertIn("test_meaning_unknown:test:normal", context["reasons"])

    def test_f05_known_change_stays_stale_when_another_current_input_is_missing(self):
        f = self.fixture
        f.configure("current")
        f.observe()
        review = f.store.append("review", "review:f05-partial-inputs", f.scope, f.evaluate())
        snapshot = self.append_snapshot(review, "snapshot:f05-partial-inputs")
        changed_code = f.store.append(
            "code_state", "code:f05-changed", f.scope, f.code_state_data("changed")
        )
        f.store.activate(changed_code)
        reader = self.open_reader()
        context = reader.read_context(reader.snapshot_key(snapshot))
        self.assertEqual(context["freshness"], "stale")
        self.assertIn("code_state_changed", context["reasons"])
        self.assertIn("environment_missing", context["reasons"])

    def test_f06_evidence_keys_are_snapshot_scoped_and_partial_is_not_ready(self):
        f = self.fixture
        f.configure(checks=("normal", "retry"))
        left_observation = f.observe()
        left_review = f.store.append("review", "review:f06-left", f.scope, f.evaluate())
        left_snapshot = self.append_snapshot(left_review, "snapshot:f06-left")
        f.observe(check="retry")
        right_review = f.store.append("review", "review:f06-right", f.scope, f.evaluate())
        right_snapshot = self.append_snapshot(right_review, "snapshot:f06-right")
        reader = self.open_reader()
        left_key = reader.snapshot_key(left_snapshot)
        right_key = reader.snapshot_key(right_snapshot)
        right_vm = reader.read_detail(right_key)
        right_only = right_vm["claims"][0]["checks"][1]["after"][0]["evidence_links"][0]["evidence_key"]
        with self.assertRaises(ReadModelError) as caught:
            reader.read_evidence(left_key, right_only)
        self.assertEqual(caught.exception.code, "NOT_FOUND")
        self.assertEqual(str(caught.exception), "Dashboard resource was not found")
        raw = EvidenceStore(f.catalog, EventLog(f.catalog)).resolve("evidence:1")
        raw.object_path.write_bytes(b"corrupt")
        before = self.inventory()
        partial = reader.read_detail(left_key)
        self.assertEqual(partial["context"]["read_health"], "partial")
        self.assertTrue(partial["presentation"]["fallback"])
        evidence_key = partial["claims"][0]["checks"][0]["after"][0]["evidence_links"][0]["evidence_key"]
        evidence = reader.read_evidence(left_key, evidence_key)
        self.assertEqual(evidence["availability"], "corrupt")
        self.assertEqual(evidence["command"]["availability"], "not_collected")
        self.assertIsNone(evidence["raw"]["text"])
        self.assertEqual(before, self.inventory())
        self.assertEqual(left_observation["id"], partial["claims"][0]["checks"][0]["after"][0]["ref"]["id"])

    def test_f06_missing_and_purged_evidence_remain_distinct(self):
        f = self.fixture
        f.configure(checks=("normal", "retry"))
        f.observe(content=b"shared evidence")
        f.observe(check="retry", content=b"shared evidence")
        review = f.store.append("review", "review:f06-availability", f.scope, f.evaluate())
        snapshot = self.append_snapshot(review, "snapshot:f06-availability")
        evidence = EvidenceStore(f.catalog, EventLog(f.catalog))
        evidence.resolve("evidence:1").object_path.unlink()
        evidence.purge("evidence:2", "Fixture purge")
        reader = self.open_reader()
        detail = reader.read_detail(reader.snapshot_key(snapshot))
        links = [check["after"][0]["evidence_links"][0]
                 for check in detail["claims"][0]["checks"]]
        self.assertEqual({link["availability"] for link in links}, {"missing", "purged"})
        self.assertEqual(detail["context"]["read_health"], "partial")

    def test_f06_evidence_count_uses_unique_evidence_ids_not_binding_count(self):
        f = self.fixture
        f.configure("current")
        observation = f.observe()
        second_binding = f.store.bind_evidence("binding:duplicate", f.scope, "evidence:1")
        duplicated = f.store.get(observation)["data"]
        duplicated["evidence"].append(second_binding)
        f.store.append("observation", "obs:duplicate-binding", f.scope, duplicated)
        review = f.store.append("review", "review:f06-unique-count", f.scope, f.evaluate())
        snapshot = self.append_snapshot(review, "snapshot:f06-unique-count")
        reader = self.open_reader()
        check = reader.read_detail(reader.snapshot_key(snapshot))["claims"][0]["checks"][0]
        self.assertEqual(check["evidence_count"], 1)

    def test_f06_foreign_project_snapshot_is_the_same_not_found(self):
        f = self.fixture
        task = IdentityRegistry(f.catalog).create_task_lifecycle(
            "foreign-project", "foreign-worktree", "imported", "b" * 40,
            "main", "/foreign", "foreign-env",
        )
        project_scope = {"project_id": task.project_id}
        issue = f.store.append("work_issue", "foreign-issue", project_scope, {"title": "Foreign"})
        issue_scope = {**project_scope, "issue_id": "foreign-issue"}
        scope = {**issue_scope, "task_id": task.task_id, "attempt_id": "foreign-attempt"}
        attempt = f.store.append("attempt", "foreign-attempt", scope, {"issue": issue, "previous": None})
        f.store.activate(attempt)
        spec = f.store.append("spec", "foreign-spec", issue_scope, {
            "issue": issue,
            "document": {"path": "docs/foreign.md", "text": "Foreign"},
            "criteria": [{"id": "c1", "text": "Foreign", "required": True,
                          "comparison": "current"}],
        })
        approval = f.store.append("spec_approval", "foreign-approval", issue_scope, {
            "spec": spec, "actor": {"kind": "human", "id": "owner"},
            "decision": "approved", "reason": "Fixture", "source": "fixture",
        })
        f.store.activate(spec, approval=approval)
        code = f.store.append("code_state", "foreign-code", scope, f.code_state_data("foreign"))
        environment = f.store.append(
            "environment", "foreign-environment", scope, lifecycle.environment_state("foreign")
        )
        baseline = f.store.append("baseline", "foreign-baseline", scope, {
            "spec": spec, "spec_approval": approval, "code_state": code,
            "environment": environment, "baseline_kind": "verification",
            "observations": [], "missing_reason": "Before absent",
        })
        review = f.store.append("review", "foreign-review", scope, {
            "spec": spec, "spec_approval": approval, "code_state": code,
            "environment": environment, "baseline": baseline,
            "claims": [{"criterion_id": "c1", "status": "unobserved",
                        "observations": [], "reason": "Not run"}],
            "additional_observations": [], "blockers": [], "uncertainties": [], "inferences": [],
        })
        snapshot = f.store.append("snapshot", "foreign-snapshot", scope, {"review": review})
        foreign_key = fingerprint({"namespace": "ownhands.lifecycle", "scope": scope,
                                   "snapshot_ref": snapshot})
        reader = self.open_reader()
        with self.assertRaises(ReadModelError) as foreign:
            reader.read_detail(foreign_key)
        with self.assertRaises(ReadModelError) as absent:
            reader.read_detail("f" * 64)
        self.assertEqual((foreign.exception.code, str(foreign.exception)),
                         (absent.exception.code, str(absent.exception)))

    def test_f07_list_selection_unicode_search_order_and_cursor_stability(self):
        need = self.simple_snapshot("need", title="Needs review", status="unobserved")
        blocked = self.simple_snapshot("blocked", title="Blocked", status="unobserved", blocked=True)
        stale = self.simple_snapshot("stale", title="Stale ready", status="verified", activate_inputs=True)
        changed_code = self.fixture.store.append(
            "code_state", "code:stale-changed", stale["scope"], self.fixture.code_state_data("changed")
        )
        self.fixture.store.activate(changed_code)
        unknown = self.simple_snapshot("unknown", title="ＡＢＣ 카페", status="verified")
        current = self.simple_snapshot("current", title="Current ready", status="verified", activate_inputs=True)
        older = self.fixture.store.append("snapshot", "snapshot:need-old", need["scope"], {"review": need["review"]})
        newer = self.fixture.store.append("snapshot", "snapshot:need-new", need["scope"], {"review": need["review"]})
        reader = self.open_reader()
        page = reader.read_list(limit=10)
        keys = [item["snapshot_key"] for item in page["items"]]
        self.assertNotIn(reader.snapshot_key(older), keys)
        self.assertIn(reader.snapshot_key(newer), keys)
        states = [(item["review_state"], item["context"]["freshness"]) for item in page["items"]]
        self.assertEqual(states[:4], [
            ("needs-review", "unknown"), ("blocked", "unknown"),
            ("ready", "stale"), ("ready", "unknown"),
        ])
        search = reader.read_list(q="abc 카페", ready_sequence=5)
        self.assertEqual([item["snapshot_key"] for item in search["items"]], [reader.snapshot_key(unknown["snapshot"])])
        self.assertEqual(search["summary_search"], "cached_only")
        cached = (
            {"snapshot_key": reader.snapshot_key(current["snapshot"]), "status": "ready",
             "ready_sequence": 5, "headline": {"text": "저장 요약"}, "summary": []},
            {"snapshot_key": reader.snapshot_key(unknown["snapshot"]), "status": "ready",
             "ready_sequence": 4, "headline": {"text": "저장 요약 둘"}, "summary": []},
        )
        first = reader.read_list(q="저장", limit=1, presentations=cached, ready_sequence=5)
        self.assertEqual(len(first["items"]), 1)
        later_cache = cached + ({
            "snapshot_key": reader.snapshot_key(stale["snapshot"]), "status": "ready",
            "ready_sequence": 6, "headline": {"text": "저장 요약 셋"}, "summary": [],
        },)
        second = reader.read_list(q="저장", cursor=first["next_cursor"], limit=1,
                                  presentations=later_cache, ready_sequence=6)
        self.assertEqual(len(second["items"]), 1)
        self.assertNotEqual(second["items"][0]["snapshot_key"], reader.snapshot_key(stale["snapshot"]))
        self.fixture.store.append("work_issue", "issue:cursor-change", self.fixture.project_scope, {
            "title": "Cursor change", "source": "fixture", "content": "change", "request_refs": []
        })
        with self.assertRaises(ReadModelError) as caught:
            reader.read_list(q="저장", cursor=first["next_cursor"], limit=1,
                             presentations=cached, ready_sequence=5)
        self.assertEqual(caught.exception.code, "LIST_CHANGED")
        with self.assertRaises(ReadModelError) as invalid:
            reader.read_list(cursor="not-a-cursor")
        self.assertEqual(invalid.exception.code, "INVALID_QUERY")

        with self.assertRaises(ReadModelError) as wrong_shape:
            reader.read_list(cursor=reader._encode_cursor([]))
        self.assertEqual(wrong_shape.exception.code, "INVALID_QUERY")

        cursor_data = reader._decode_cursor(first["next_cursor"])
        cursor_data["last"] = ["bad"]
        with self.assertRaises(ReadModelError) as invalid_last:
            reader.read_list(q="저장", cursor=reader._encode_cursor(cursor_data), limit=1,
                             presentations=cached, ready_sequence=5)
        self.assertEqual(invalid_last.exception.code, "INVALID_QUERY")

    def test_f08_one_source_change_retries_but_continuous_change_fails(self):
        item = self.simple_snapshot("change", title="Changing source", status="unobserved")
        reader = self.open_reader()
        key = reader.snapshot_key(item["snapshot"])
        original = reader._build_state
        calls = 0

        def change_once(snapshot_key, presentations=(), ready_sequence=0):
            nonlocal calls
            result = original(snapshot_key, presentations, ready_sequence)
            calls += 1
            if calls == 1:
                self.fixture.store.append("work_issue", "issue:change-once", self.fixture.project_scope, {
                    "title": "one", "source": "fixture", "content": "one", "request_refs": []
                })
            return result

        with patch.object(reader, "_build_state", side_effect=change_once):
            self.assertEqual(reader.read_detail(key)["snapshot_ref"], item["snapshot"])
        self.assertEqual(calls, 2)

        def change_always(snapshot_key, presentations=(), ready_sequence=0):
            nonlocal calls
            result = original(snapshot_key, presentations, ready_sequence)
            calls += 1
            self.fixture.store.append("work_issue", "issue:change-always", self.fixture.project_scope, {
                "title": str(calls), "source": "fixture", "content": str(calls), "request_refs": []
            })
            return result

        with patch.object(reader, "_build_state", side_effect=change_always):
            with self.assertRaises(ReadModelError) as caught:
                reader.read_detail(key)
        self.assertEqual(caught.exception.code, "SOURCE_CHANGED")

    def test_f08_cursor_rejects_raw_health_change_that_reorders_the_list(self):
        self.simple_snapshot("cursor-first", title="Needs review", status="unobserved")
        self.simple_snapshot(
            "cursor-second", title="Ready", status="verified", activate_inputs=True
        )
        reader = self.open_reader()
        first = reader.read_list(limit=1)
        self.assertIsNotNone(first["next_cursor"])
        raw = self.fixture.catalog.connection.execute(
            "SELECT evidence_id FROM evidence ORDER BY created_at, evidence_id DESC LIMIT 1"
        ).fetchone()[0]
        EvidenceStore(self.fixture.catalog, EventLog(self.fixture.catalog)).resolve(raw).object_path.unlink()
        with self.assertRaises(ReadModelError) as caught:
            reader.read_list(cursor=first["next_cursor"], limit=1)
        self.assertEqual(caught.exception.code, "LIST_CHANGED")

    def test_f08_empty_list_differs_from_direct_not_found_and_integrity_error(self):
        reader = self.open_reader()
        self.assertEqual(reader.read_list()["items"], [])
        with self.assertRaises(ReadModelError) as missing:
            reader.read_detail("f" * 64)
        self.assertEqual(missing.exception.code, "NOT_FOUND")
        self.fixture.store.connection.execute("DROP TRIGGER lifecycle_records_no_update")
        self.fixture.store.connection.execute("UPDATE lifecycle_records SET data_json='{}' WHERE kind='work_issue'")
        with self.assertRaises(ReadModelError) as corrupt:
            reader.read_list()
        self.assertEqual(corrupt.exception.code, "SOURCE_INTEGRITY_ERROR")

    def test_f09_all_reads_are_side_effect_free_and_never_evaluate_or_generate(self):
        f = self.fixture
        f.configure("current")
        f.observe()
        f.store.activate(f.code)
        f.store.activate(f.env)
        review = f.store.append("review", "review:f09", f.scope, f.evaluate())
        snapshot = self.append_snapshot(review, "snapshot:f09")
        reader = self.open_reader()
        key = reader.snapshot_key(snapshot)
        detail = reader.read_detail(key)
        evidence_key = detail["claims"][0]["checks"][0]["after"][0]["evidence_links"][0]["evidence_key"]
        before = self.inventory()
        forbidden = [
            patch.object(LifecycleStore, "evaluate_review", side_effect=AssertionError("evaluate")),
            patch.object(LifecycleStore, "append", side_effect=AssertionError("append")),
            patch.object(LifecycleStore, "activate", side_effect=AssertionError("activate")),
            patch.object(EvidenceStore, "put", side_effect=AssertionError("put")),
            patch.object(EvidenceStore, "purge", side_effect=AssertionError("purge")),
            patch.object(EvidenceStore, "reconcile_objects", side_effect=AssertionError("reconcile")),
        ]
        with forbidden[0], forbidden[1], forbidden[2], forbidden[3], forbidden[4], forbidden[5]:
            reader.read_list()
            reader.read_detail(key)
            reader.read_claim(key, "c1")
            reader.read_evidence(key, evidence_key)
            reader.read_context(key)
        self.assertEqual(before, self.inventory())


if __name__ == "__main__":
    unittest.main()

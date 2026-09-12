# #82 Claim evaluation contract

The engine evaluates evidence; it never runs tests or accepts work for the user.
`LifecycleStore.evaluate_review(scope, inputs)` resolves all matching observations,
then uses the same deterministic rules that `append('review', ...)` recomputes.
The SQLite journal remains schema v1. New Spec, Baseline, Observation and Review
payloads explicitly use `contract_version: 2`. Legacy records remain readable and
are never promoted to v2 coverage. A v2 Spec cannot use a v1 observation/review.

## Approved coverage

Each criterion retains `id`, `text`, `required`, `comparison` and adds nonempty
`checks`: `{check_id, statement, role}`. Role is `success_condition` or
`counterexample`. Every check contributes to its Claim. Optional goals belong in
separate `required: false` criteria, so a failed optional goal still says failed.
The agent proposes coverage from requirements and repository facts; the user
approves the exact Spec revision. Test names are selection details, not approval.

## Producer boundary

Use existing EvidenceStore and lifecycle bindings. Each v2 Observation adds
`check_id` and `execution` to the existing spec/approval/code/environment/test
meaning/result/basis/phase/selection_reason/evidence fields. Evidence `fields`
must contain exactly matching `check_id` and `execution` as well as the existing
input bindings. `criterion_id: null` identifies an additional observation.

Execution receipt:

```json
{
  "id": "runner-generated-execution-id",
  "status": "completed",
  "failure_kind": "none",
  "producer": "runner name",
  "started_at": "2026-09-13T00:00:00Z",
  "finished_at": "2026-09-13T00:00:01Z",
  "origin": "live",
  "code_start": {"kind":"code_state","id":"...","revision":1,"hash":"..."},
  "code_end": {"kind":"code_state","id":"...","revision":1,"hash":"..."},
  "environment_complete": true,
  "provenance": "execution source or reconstructed-state explanation"
}
```

`status`: completed/error/not_started. `failure_kind`:
none/requirement_violation/execution_error/unknown. `origin`: live/reconstructed.
Capture the actual execution times and the code at both boundaries. An exit code
alone is not a requirement violation. A structured assertion result and raw
execution evidence must support that interpretation. Unknown environment coverage
or observed code changes cannot support verified. Start/end equality does not
prove that an undetected intermediate modification never happened.

The Baseline requires `provenance` in addition to its existing fields. Its
CodeState/Environment identify the trusted pre-change target. Missing observations
require `missing_reason`. Never substitute the current After as Before.
Reconstruction is performed outside the engine, after explaining cost and asking
the user. Preserve actual reconstructed code, test changes and provenance; do not
pretend the execution occurred earlier. If the environment cannot be reproduced,
comparison is inconclusive. If pre-change provenance itself is absent, use an
Observation Report / needs-input, not a formal Review.

Hashes and producer strings validate bindings, not runner authenticity. The
engine cannot detect executions never submitted or prove a dishonest log true.

## Store API

```python
inputs = {
    "contract_version": 2,
    "spec": spec_ref, "spec_approval": approval_ref,
    "baseline": baseline_ref,
    "code_state": after_code_ref, "environment": after_environment_ref,
    "test_plan": [{"criterion_id": "c1", "check_id": "retry",
                   "test_id": "retry-test", "test_meaning": meaning_sha256}],
    "blockers": [], "findings": [], "exclusions": [],
}
data = store.evaluate_review(scope, inputs)
review_ref = store.append("review", "review:work-item", scope, data)
status = store.review_status(review_ref)
```

`test_plan` maps every intended check/test to its meaning. Every planned test is
necessary; a passing test does not hide a different planned test that was not run.
The engine always emits every approved criterion/check, including missing ones.
A failure cannot be hidden by deleting its test from the plan.

Blockers: `{criterion_id, check_id, reason, source}`. Only required criteria may
block, using the existing BLOCKER_REASONS codes. The producer must identify an
actual obstacle; a vague risk or ordinary unexecuted test is not a blocker.
Findings: `{reason, observations: [refs]}` within the evaluated input scope.
Additional failing/uncertain observations are surfaced automatically.
Exclusions: `{criterion_id, reason}` for deliberately unselected optional goals.
An exclusion cannot conceal an executed failure/error.

Store scans its immutable observation journal for the same scope, approved Spec,
phase and phase target CodeState/Environment content fingerprints. It includes repeated executions and
Before records omitted from a caller's Baseline observation list. It does not
reuse different-code results. The full input-set hash is retained. A concurrent
new observation between evaluation and append rejects outdated output; reevaluate.
`review_status` reports new evidence without rewriting a saved Review/Snapshot.
A damaged evidence closure returns a readable=false diagnostic rather than a
verified historical result. Invalid After candidates can be reported by identifier
without adding their unusable references to Review closure.

## Verdicts

After must be a valid observed result for the approved check and target inputs.

| Comparison | Verified requires |
|---|---|
| current | All required check/test After results pass |
| preserve | Comparable observed Before pass and After pass |
| improve | Comparable observed Before fail and After pass |

Comparison uses test identity/meaning and environment content fingerprint. Both
phase environments must be valid, but different environments can be stored as an
inconclusive report. Code differs across phases normally; each execution must match
its own target. Old test meaning requires a new Before run using the changed test.
New requirements/checks require new Spec approval; never relabel old evidence.

A valid actual After violation produces failed, even alongside missing checks or
other successes. One failed repeated execution is failure. Contradictory receipts
for the same execution/test/check produce inconclusive with both sources; a
separate confirmed failure still wins. No After observation means unobserved;
partial coverage or insufficient comparison produces inconclusive.

All checks verified → Claim verified. Any check failed → Claim failed. All checks
unobserved → Claim unobserved. Other incomplete combinations → inconclusive.

Review: actual required blockers → blocked; otherwise unresolved required Claims,
optional failure/error, conflicts or additional findings → needs-review; otherwise
ready. Deliberately unselected optional criteria remain visible and do not by
themselves prevent ready. Required completion is a separate boolean and count:
`필수 검증 완료 · 사용자 확인 필요` is possible. With zero required criteria, show
`필수 항목 없음`, not a count-based product-completion claim.

Review data includes all Claim/check results, reason codes, comparison references,
conflicts, evidence references, coverage, gaps, findings, diagnostics and blockers.
`ready` does not mean accepted. Status labels never schedule re-execution.
Freshness remains separate via the existing `freshness` API. Preserve historical
results; do not call old verified evidence verified against changed code.

## Existing code reused and limits

EvidenceStore hash/size/purge/scope validation, lifecycle approval, append-only
journal, CodeState fingerprints, Snapshot and Human Decision are reused directly.
Impact's declared relation joins and Test Design selection/gap patterns remain
usable by orchestration; they are not proof of an unaffected dependency graph.
Legacy gate overrides, baseline-registration pass and fixed_failure summaries are
not Claim verdicts. No new dependency, DB, generic policy language, automatic
restoration executor or Dashboard UI is introduced.

The current implementation scans the journal, matching existing Store behavior.
If large histories become slow, index measured query paths rather than weakening
input completeness. Reconstruction/provenance checks remain the producer's duty.

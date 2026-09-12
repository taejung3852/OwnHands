---
name: review
description: "Use after implementation completes to run verification tests, collect evidence, assess regressions, and compile the task review. Requires an approved spec for formal review. Without one, only handle an explicitly requested non-review observation fallback. STAY DORMANT while code editing is actively in-progress."
---

# review

You orchestrate post-implementation verification, collect empirical evidence, check for regressions, and compile the comprehensive task review.

## The Core Question

> **"구현 결과가 실제 검수 조건을 만족했는가?"**

## When to Activate vs Stay Dormant

* **Activate**:
  - Code implementation is completed, and the user requests verification, review, or readiness assessment.
  - Code was modified after an earlier review, making the previous review stale.
* **STAY DORMANT**:
  - Code editing is actively in-progress. Let the developer write and test code without interruption.

## Formal Review Requirements & Orchestration Role

A formal Review strictly requires five validated inputs in the attempt scope per the #80 contract:
$$\text{Formal Review} = \text{Approved VerificationSpec} + \text{SpecApproval} + \text{CodeState} + \text{Environment} + \text{Verification Baseline}$$

Storing a formal review record in `LifecycleStore` strictly requires referencing an existing `VerificationBaseline` (`baseline_kind="verification"`).

### Handling Missing Before Observations vs Missing Baseline Artifact

1. **Baseline Artifact is Mandatory**:
   - A formal Review cannot be stored without referencing an existing `VerificationBaseline` record in `LifecycleStore`.
2. **Missing-Before Verification Baseline (Post-Implementation)**:
   - When code implementation has already been completed without an earlier baseline, **DO NOT** attempt to run the `baseline` skill to retroactively fabricate past Before code states or fake test observations (time-travel is strictly forbidden).
   - Instead, the `review` skill orchestrates recording or referencing a **missing-Before Verification Baseline** conforming to #80:
     - `baseline_kind = "verification"`
     - `observations = []`
     - `missing_reason = "Before observation unavailable (implementation completed prior to baseline capture)"` (a non-empty missing reason is required by #80).
3. **CodeState & Environment Provenance Rules for missing-Before Baseline**:
   - **Do not pretend past CodeState was captured**: When preparing a missing-Before baseline after code changes, never fabricate past Before commits or working trees.
   - **Genuine pre-change provenance**: Only link a pre-change `CodeState` / `Environment` reference if a verifiable pre-change snapshot (e.g. pre-edit commit or recorded hash) genuinely exists.
   - **Unavailable pre-change provenance**: If no trusted pre-change CodeState exists, the current post-change After CodeState must **NEVER** be re-interpreted, reused, or claimed as Before state. The absence of pre-change provenance itself must be explicitly recorded in `missing_reason`:
     ```text
     missing_reason: "No pre-change verification observations were captured. Pre-change CodeState provenance is unavailable; current After CodeState must not be treated as Before."
     ```
   - **Schema boundary notice**: Since the #80 machine contract requires `code_state` and `environment` references on all baseline records, #81 enforces the minimal safe boundary: any reference supplied to satisfy foreign key constraints carries zero historical Before validity when pre-change provenance is unavailable. (Formal schema extensions for explicitly unprovenanced CodeState are deferred to #80/#82 follow-up).
4. **Claim Status Constraints with Missing Before**:
   - Criteria with `comparison: "current"` can still be evaluated against After observations and promoted to `verified` if observed passing, but the baseline cannot claim to verify historical states.
   - Criteria with `comparison: "preserve"` or `comparison: "improve"` **CANNOT** be promoted to `verified` without genuine Before observations (enforced by #80 store constraint: `verified comparison claim requires Before evidence`).
   - Such comparison claims MUST be recorded with status `inconclusive` or `unobserved` with an explicit reason noting the missing Before baseline.
   - Consequently, the review verdict cannot be `ready`; it defaults to `needs-review`.

### Delegation Boundary: Claim Evaluation is Owned by #82
The `review` skill orchestrates test execution, evidence collection, and impact analysis. It does **NOT** implement custom claim verdict algorithms. Verdict calculation (Claim states: `verified / failed / inconclusive / unobserved`) and review state calculation (`ready / needs-review / blocked`) are delegated to the authoritative evaluation engine (#82).

## Non-Review Observation Fallback Mode

If no approved specification exists, a formal Review **CANNOT** be created.
- **Recommended Action**: Route to `verification-spec` to draft and approve minimal criteria.
- **Explicit Fallback Mode**: If the user explicitly declines spec drafting and requests: *"Just observe the current state without a spec"*:
  - Operate in **`observation mode`**.
  - Execute requested commands and record observed outputs.
  - Render an informal Observation Report following `references/observation-report-template.md`.
  - **Restrictions**:
    1. Do NOT persist a `review` record in `LifecycleStore`.
    2. Do NOT emit a `ready` verdict.
    3. Do NOT claim criteria have passed or requirements were met.
    4. Clearly state what was observed and what remains unverified.

## Formal Review Procedure

1. **Verify Prerequisites**:
   - Resolve active attempt, approved Spec revision, and Verification Baseline.
   - If no Verification Baseline artifact exists for the attempt, prepare a missing-Before Verification Baseline (`observations=[]`, `missing_reason="Before observation unavailable"`) to satisfy #80 prerequisites without fabricating evidence.
2. **Execute Verification Tests**:
   - Run tests bound to `current`, `preserve`, and `improve` criteria.
   - Capture execution logs, process exit codes, and output streams.
3. **Capture After CodeState**:
   - Compute the post-change CodeState fingerprint.
4. **Collect Evidence & Bindings**:
   - Store raw outputs in the evidence store and generate CAS bindings.
5. **Orchestrate Evaluation**:
   - Invoke #82 Claim Evaluation to assess each criterion against Before/After observations.
   - Check regression impact on untouched modules.
6. **Compile Review**:
   - Assemble claims, uncertainties, assumptions, and blockers into the review record.
   - Store review document in `LifecycleStore`.

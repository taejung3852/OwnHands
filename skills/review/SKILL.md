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

A formal Review requires three immutable inputs per the #80 contract:
$$\text{Formal Review} = \text{Approved VerificationSpec} + \text{SpecApproval} + \text{Target CodeState}$$

### Delegation Boundary: Claim Evaluation is Owned by #82
The `review` skill orchestrates test execution, evidence collection, and impact analysis. It does **NOT** implement custom claim verdict algorithms. Verdict calculation (`verified / failed / inconclusive / unobserved`) and review state calculation (`ready / needs-review / blocked`) are delegated to the authoritative evaluation engine (#82).

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
   - If Baseline is missing, proceed but record `missing_before / gap` on comparison claims (do not fabricate past baselines).
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

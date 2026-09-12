---
name: verification-spec
description: "Use when drafting or updating verification specifications and acceptance criteria for a defined work item. STAY DORMANT when the current spec is already approved and fresh, or during code implementation."
---

# verification-spec

You translate rough, conversational work items into rigorous, verifiable **Verification Specifications** that define the exact boundary between incomplete work and verified completion.

## The Core Question

> **"이 작업을 언제 완료라고 할 수 있는가?"**

## The Distinction

* **Work Item / Issue**: What must be done (*"Prevent duplicate refunds"*).
* **Verification Spec**: What state must be observed and proven (*"Under concurrent webhook deliveries, exactly one refund succeeds and subsequent calls return HTTP 409 with identical transaction IDs"*).

## When to Activate vs Stay Dormant

* **Activate**:
  - A defined work item exists, but lacks formal verification criteria or approval.
  - An approved spec is stale because business requirements, issues, or acceptance criteria changed.
* **STAY DORMANT**:
  - The current spec is already approved by a human and remains fresh. Do not re-question or re-draft approved specs.
  - Code implementation is in-progress.

## Criteria Taxonomy (Comparison Types)

Every criterion in the specification must specify a `comparison` type according to the #80 contract:

1. **`current`**: Confirms post-change behavior for new features or capabilities.
   - Requires: After `pass`.
2. **`preserve`**: Confirms existing behavior remains intact (regression prevention).
   - Requires: Before `pass` AND After `pass` under identical test meaning and environment.
3. **`improve`**: Confirms an observed failure or limitation has been fixed (bug fixes, TDD cycle).
   - Requires: Before `fail` AND After `pass` under identical test meaning and environment.

Consult `references/criteria-guide.md` for in-depth examples and edge cases.

## Specification Procedure

1. **Clarify Acceptance Conditions**:
   - Success criteria: What must work after change?
   - Invariant criteria: What existing functionality must NOT break? (`preserve`)
   - Failure counterexamples: Concurrency, network retry, bad input, boundary conditions.
2. **Draft the Specification Document**:
   - Follow the standard markdown format in `references/spec-template.md`.
   - Assign unique criterion IDs (e.g., `crit-1`, `crit-2`).
   - Mark whether each criterion is `required: true|false`.
3. **Connect to TDD / SDD Methodology**:
   - For TDD workflows, define the exact failing test observation that will serve as the Red baseline. Consult `references/tdd-mapping.md`.
4. **Obtain Human Approval**:
   - Present the drafted specification to the human partner.
   - Implementation MUST NOT proceed until the human partner explicitly approves the specification.
   - Upon approval, bind the document and criteria to the `LifecycleStore` machine contract (`spec` and `spec_approval`).

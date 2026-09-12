---
name: baseline
description: "Use immediately before writing code to observe and capture pre-change code fingerprints, environment state, and Before observations. STAY DORMANT while code editing is in-progress or after baseline is already captured."
---

# baseline

You observe, measure, and record the exact pre-change baseline state of the repository and test suite immediately before code modifications begin.

## The Core Question

> **"바꾸기 전의 기준 상태는 무엇인가?"**

## When to Activate vs Stay Dormant

* **Activate**:
  - A formal Verification Specification is approved by the human partner, and code implementation has not yet started.
  - Pre-implementation environment or test parameters changed, requiring a fresh Before observation.
* **STAY DORMANT**:
  - Code editing is actively in-progress. Do not interrupt the developer while typing.
  - A valid baseline is already captured with matching Spec, CodeState, Environment, and Test meaning.
  - Implementation is already finished: **DO NOT** invoke `baseline` to travel back in time or fake past Before observations. The `baseline` skill is strictly for pre-implementation Before observations. After implementation, `review` may prepare a missing-Before Verification Baseline (`observations=[]`, non-empty `missing_reason`) only with trusted pre-change CodeState and Environment references. Without that provenance, it produces an Observation Report / `needs-input` and creates neither a baseline nor a formal Review.

## Worktree Policy: Observation First, Isolation Optional

OwnHands does **NOT** force the creation of a new Git worktree. Its core mandate is to observe and faithfully record the reality of the developer's current environment:
- Active branch
- Worktree location
- Git commit hash
- Working tree dirty status and code fingerprint
- Environment fingerprint
- Before test observations

If the current working tree is clean, observe in-place. If the tree contains uncommitted experimental edits, or if the user explicitly prefers an isolated branch, guide them to optional Git Worktree creation. Consult `references/worktree-guide.md`.

## Baseline Procedure

1. **Verify Approved Spec**:
   - Ensure the current issue has an active, human-approved `spec` and `spec_approval`.
2. **Capture Code State & Environment**:
   - Compute the repository CodeState fingerprint (HEAD commit + tracked/untracked content hashes).
   - Compute the Environment fingerprint (runtime version, OS, configuration).
3. **Execute Before Observations**:
   - Run tests corresponding to `preserve` criteria ➔ Verify they pass.
   - Run tests corresponding to `improve` criteria (TDD Red) ➔ Verify they fail as expected.
4. **Persist Baseline Record**:
   - Store the baseline artifact in `LifecycleStore` linked to the active attempt scope.
   - Use `contract_version: 2`, preserve pre-change `provenance` and record v2 execution receipts per `../../docs/m5-r/claim-evaluation-contract.md`.
   - If an existing defect is observed, show evidence and ask the user whether to include it, create a separate issue, or defer. Do not automatically expand scope or create an issue. Work confirmed independent may continue; dependent or uncertain work waits.
   - Hand off to implementation.

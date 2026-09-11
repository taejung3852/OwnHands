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
  - Implementation is already finished: **DO NOT** attempt to travel back in time to capture a baseline after edits have been made. Such cases must proceed directly to `review` with `missing_before / gap` recorded.

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
   - Hand off to implementation.

# Verification Specification Template

## Target Work Item
- **Title**: [Title of the Work Item]
- **Scope**: [Project / Subsystem]
- **Date**: [YYYY-MM-DD]

## 1. Goal and Problem Statement
Briefly describe the user requirement, background context, and what the change accomplishes.

## 2. Invariant Rules (What Must NOT Change)
Describe existing behaviors, performance baselines, or interfaces that must remain completely intact.

## 3. Acceptance Criteria Table

| ID | Statement | Comparison | Required | Verification Method |
|---|---|---|---|---|
| `crit-1` | [Description of expected post-change behavior] | `current` | `true` | Automated test `tests/test_foo.py:test_bar` |
| `crit-2` | [Description of existing behavior that must not break] | `preserve` | `true` | Existing test suite regression run |
| `crit-3` | [Description of bug/defect that must be resolved] | `improve` | `true` | Before failing test turning pass |

## 4. Edge Cases & Counterexamples
- **Edge Case 1**: Concurrency / Race conditions
- **Edge Case 2**: Invalid or malicious input handling
- **Edge Case 3**: Partial failure and rollback recovery

## 5. Required Evidence
- Test output logs and execution receipts.
- Git code fingerprint of the implementation commit.
- Environment fingerprint (Python version, dependencies, OS).

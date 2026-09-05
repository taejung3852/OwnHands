# Task 2 Report: trusted Dashboard sources and TaskReviewView

## Status

Implemented the Task 2 source validators, Evidence resolver, and deterministic
non-persistent `TaskReviewView` assembler. The implementation keeps M3
project provenance separate from current-Task controls, requires exact M4 Task
and patch identity, distinguishes M1 Store objects from M4 logical references,
and evaluates freshness separately from source collection completeness.

## TDD evidence

- Initial RED: all four Dashboard test modules failed because
  `devharness.dashboard_sources` and `devharness.dashboard_view` did not exist.
- Completeness RED: removing the Project Baseline incorrectly left the view
  `complete`; the assembler now requires M2 baseline, context status, and a
  fingerprint-closed execution contract.
- Decision RED: a fresh projection without a matching canonical
  `assurance.evaluated` reference incorrectly allowed submission; eligibility
  now requires the latest packet, Gate fingerprint, and Gate decision closure.
- Integrity RED: tampered direct human Evidence incorrectly closed collection
  completeness; content integrity is now checked before that observation is
  used.
- Contract RED: a modified or non-serializable Contract goal entered Summary;
  the Contract/snapshot fingerprint and M4 Contract reference now fail closed.

## Verification

- Focused Dashboard tests: 16 tests passed.
- Brief regression set (Dashboard, Evidence, Assurance, Projections): 76 tests
  passed before duplicate test-import cleanup; all behaviors remained covered.
- Full repository discovery after implementation: 276 tests passed.
- `git diff --check`: passed.

## Review notes

- `assemble_task_review` performs no Catalog mutation and creates no file; the
  repeated-assembly test compares both SQLite total changes and data-root files.
- M3 mismatch exposes project provenance but replaces current-Task controls
  with independent `not_run`/`unobserved` stage rows.
- Unregistered M4 refs stay `reference_only`; registered refs require current
  Task binding, packet fingerprint, non-purged content, hash/size integrity,
  and a non-symlink Store object before disclosure.
- Missing or mismatched TGR remains `not_evaluated`; missing or corrupted human
  feature observation remains `unobserved`.

## Environment note

Sandboxed `uv` and system-Python bytecode-cache initialization could not write
their user cache directories. The authorized Python 3.12 `uv run` path was used
for all actual test evidence; no test or product failure was hidden by this
environment limitation.

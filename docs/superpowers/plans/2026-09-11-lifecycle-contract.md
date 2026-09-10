# Lifecycle v1 Implementation Plan

> **For agentic workers:** Use executing-plans to implement task-by-task; independent reviews may be delegated.

**Goal:** Deliver #80's versioned, scoped lifecycle with immutable history, shared readiness and evidence references.
**Architecture:** New `devharness.lifecycle` package uses a separate append-only SQLite journal under the existing private data root. It reads legacy Identity/Evidence; it never extends Catalog v3 or appends unsupported legacy events. Router/Skill/Dashboard consume the same Python API; #81 exposes routing and #82 supplies Claim evaluation.
**Tech Stack:** Python >=3.12, standard library, sqlite3, unittest.
**Spec:** ../specs/2026-09-11-lifecycle-contract-design.md

## Global constraints
- Human owns required criteria and approval; optional methods never become gates.
- Keep legacy Contract/Gate/approval and exact 25 tools unchanged.
- Explicit Issue/Task/attempt scope; immutable references use kind/id/revision/hash.
- Preserve missing/incomparable Before; decision append does not stale its basis.
- No UI, routing engine, live test runner, or automatic Claim evaluator in #80.

## Task 1: Scoped immutable artifacts and journal
Files: `src/devharness/lifecycle/{__init__,model,store}.py`, `tests/test_lifecycle.py`.
Interfaces: `LifecycleStore(catalog)`, `append(kind, id, scope, data) -> reference`, `get(reference)`, `activate(reference)`, `current(kind, scope, slot)`, `projection()`.
- [x] Write real SQLite tests for scoped graph, revisions, approval, immutable snapshot and activation conflict, unsupported schema, replay corruption, rollback and legacy reopen.
- [x] Run `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_lifecycle.py -v`; confirm missing API fails.
- [x] Implement strict record validation and reference closure; transactional hash-linked journal with append-only triggers and replayed active selection. Use `BEGIN IMMEDIATE` for sequence/revision allocation. Hashes detect accidental corruption, not administrator forgery.
- [x] Run the same tests and inspect failures before moving on.

## Task 2: Evidence, code state and review invariants
Files: `src/devharness/lifecycle/{code_state,model,store}.py`, `tests/test_lifecycle.py`.
Interfaces: `capture_code_state(path)`, `bind_evidence(id, scope, legacy_id)`, `freshness(review, spec, code, environment, test_meanings)`.
- [x] Add real Git tracked/untracked/mode/symlink cases and real EvidenceStore corruption/scope/purge cases.
- [x] Add Before absent, meaning/environment mismatch, inferred pass, unrelated proof, additional failure, mandatory missing cases. Verify RED before implementation.
- [x] Capture hashes without exporting file contents; mark ignored/submodule/unsupported observations explicitly. Bind and revalidate raw Evidence, preserve legacy types. Validate necessary conditions for submitted Claim results without implementing #82's evaluator.
- [x] Verify targeted tests. Keep Review status, semantic freshness, journal projection lag and human decision independent.

## Task 3: Shared readiness and producer-neutral outcome
Files: `src/devharness/lifecycle/readiness.py`, `tests/fixtures/lifecycle/freshness.json`, `tests/test_lifecycle.py`.
Interfaces: `inspect_stage(stage, action, scope, inputs, request_context)`, performed `outcome` records carry input/output references.
- [x] Add readiness tests for goal/Issue/Spec/Baseline/Review, no Skill/direct execution, existing artifacts, stale inputs and unchanged decision/display fixtures; verify RED.
- [x] Implement deterministic checks with reason codes and sources; separate report readiness from completion readiness. Never select named methods or grant execution permission.
- [x] Verify every fixture and cross-consumer equality.

## Task 4: Documentation and verification
Files: `docs/m5-r/lifecycle-contract.md`, `docs/m5-r/lifecycle-verification.md`, README link.
- [x] Document exact payload fields, scopes, active slots, approval trust boundary, lifecycle interfaces, compatibility and limitations with runnable example.
- [x] Run `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q`, `git diff --check`; obtain independent code review and fix concrete findings with regression tests.
- [x] Map each #80 acceptance condition to executed tests. Record actual results and remaining limitations. Deliver local branch and reviewable diff; no automatic merge or issue closure.

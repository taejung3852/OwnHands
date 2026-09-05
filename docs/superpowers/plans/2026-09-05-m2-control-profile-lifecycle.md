# M2 Control Profile Lifecycle Implementation Plan

> **For agentic workers:** Execute inline with test-driven development. Do not delegate this plan.

**Goal:** Build the stdlib-only M2 preflight lifecycle from read-only project profiling through a locally reviewable compiler preview, without starting or controlling a Codex task.

**Architecture:** `devharness.control_profile` owns six deterministic stages and one disposable-tree apply/rollback boundary. Each stage accepts and returns JSON-shaped dictionaries, preserves Project/Worktree/Task/Environment identity, uses canonical SHA-256 fingerprints, and fails closed on unresolved authority or provenance. `devharness.m2_review` connects the stages to the existing M1 Identity, Event, and Evidence stores and renders an escaped local HTML artifact.

**Tech Stack:** Python 3.12 standard library, JSON Schema draft 2020-12 documents, `unittest`, existing SQLite Event/Evidence store.

**Spec:** `docs/product/Control_layer.md` sections 3–7, `docs/product/향후계획.md` M2, ADR-0001/0002/0004/0006/0009, GitHub issues #25–#30.

## Global Constraints

- Product name is `ownhands`; Python import namespace remains `devharness`.
- No external dependencies, runtime Codex integration, user/global config write, M4 Assurance, M5 production UI, deployment, or publishing.
- Profiler is read-only and never returns secret values; unsupported or unreadable paths are `unobserved` with a reason.
- Fixed interview fixtures are synthetic evidence, never user approval or user testing.
- Configured does not imply Loaded or Enforced; the latter two remain `not_run / unobserved` in M2.
- Apply is opt-in, requires an explicit product approval record, and is restricted to a caller-declared disposable tree with an atomic write journal and verified rollback.

---

### Task 1: Behavioral and adversarial contract

**Files:**
- Create: `tests/test_control_profile.py`
- Create: `tests/fixtures/m2/interview-cases.json`
- Create: `tests/fixtures/m2/adversarial-cases.json`
- Create: `tests/fixtures/m2/project/`

**Interfaces:**
- Exercise `profile_project`, `run_interview`, `build_baseline`, `baseline_freshness`, `build_execution_contract`, `compile_control_profile`, `apply_candidate`, `rollback_candidate`, and `render_control_preview` against real temporary trees.
- Assert deterministic fingerprints, identity/reference closure, fail-closed approval behavior, no mutation/secret leakage, exact diff/journal/rollback, and escaped accessible HTML with resolvable evidence links.

- [ ] Write literal, behavior-based tests for issues #25–#30 and the full vertical slice.
- [ ] Run `python -m unittest tests.test_control_profile -v` and capture the missing-module RED.

### Task 2: Minimal lifecycle core

**Files:**
- Create: `src/devharness/control_profile.py`

**Interfaces:**
- Consume only paths, JSON-shaped contracts, fixed timestamps, and explicit approval records.
- Produce canonical profile, interview, baseline, execution contract, compiler result, diff, journal, and rollback verification records.

- [ ] Implement read-only supported-file discovery, hashes, scopes, and explicit Unobserved records.
- [ ] Implement the one-question interview transition table with ambiguous/declined/silent fail-closed outcomes.
- [ ] Implement versioned Baseline identity/fingerprint/predecessor and freshness decisions.
- [ ] Implement overlay validation and permission-expansion authorization/expiry rules, including Imported restrictions.
- [ ] Implement deterministic candidate artifacts and lint; keep dry-run as the default.
- [ ] Implement atomic disposable-tree apply and hash-verified rollback with no overwrite outside the journal.
- [ ] Run focused tests to GREEN.

### Task 3: M1-backed vertical slice and preview

**Files:**
- Create: `src/devharness/m2_review.py`
- Create: `docs/reviews/m2/README.md`
- Create: `docs/reviews/m2/run_fixture.py`
- Create: `docs/product/control-profile-lifecycle.schema.json`
- Create: `docs/product/control-profile-lifecycle.example.json`

**Interfaces:**
- Register one synthetic Managed Task with existing `IdentityRegistry`, append stage Events with `EventLog`, store redacted stage receipts with `EvidenceStore` outside the repository, and pass only Event/Evidence references into the final packet.
- Render a local semantic HTML/SVG preview from the validated Contract and compiler diff; reject stale diff or unresolved drill-down references.

- [ ] Add the end-to-end failing test before implementing orchestration/rendering.
- [ ] Implement the smallest M1-store connection and local renderer.
- [ ] Validate the example with the strict schema and run the review script in a temporary output root.

### Task 4: Final verification

**Files:**
- Modify: `docs/product/Requirements_Traceability.md`
- Modify: `docs/reviews/m2/README.md`

- [ ] Record actual RED and GREEN evidence without claiming user testing, Loaded, or Enforced.
- [ ] Run focused tests, the full repository suite, strict schema validation, compileall with an external bytecode cache, and `git diff --check`.
- [ ] Confirm no user/global config path or raw Evidence object was written inside the repository.

# M4 Assurance Pipeline Implementation Plan

> Execution rule: standard-library only, tests first, no user workspace mutation, no raw Evidence commit.

## Acceptance boundary

Implement issues #44–#49 and only the M4 technical Gates in the approved design. The final review is limited to one explicit acceptance/blocker review, one batch blocker fix, and one affected revalidation. Non-blocking findings become follow-up issues.

## Task 1 — Contract fixtures and RED tests

Files:

- Create `tests/test_assurance.py`
- Create `tests/fixtures/m4/relation-catalog.json`
- Create `tests/fixtures/m4/adversarial-cases.json`

Steps:

1. Build a disposable Git repository helper with a start commit, tracked patch, requirements, source, schema, and existing tests.
2. Write failing tests for restore capture/reconstruction, actual diff impact, test design classification, before/after comparison, gap detection, Gate decisions, override rules, and deterministic reuse.
3. Run only `tests.test_assurance` and confirm failure because `devharness.assurance` does not exist.

## Task 2 — Minimal Assurance core

Files:

- Create `src/devharness/assurance.py`
- Modify `src/devharness/evidence.py` only if a missing M4 Evidence type is required.

Steps:

1. Implement canonical JSON/hash and strict identity/list validation.
2. Implement safe Git helpers, Restore Point capture, and disposable-clone verification.
3. Implement bounded actual-diff Impact Analysis with declared relation joining and explicit exclusions.
4. Implement Test Design Memo, baseline receipt validation, comparison, and gap detection.
5. Implement contract-driven Gate evaluation and scoped Soft Block override; reject Hard Block override.
6. Implement packet assembly and deterministic input fingerprint.
7. Run focused tests until GREEN without expanding scope.

## Task 3 — Packet schema and review slice

Files:

- Create `docs/product/assurance-packet.schema.json`
- Create `docs/product/assurance-packet.example.json`
- Create `src/devharness/m4_review.py`
- Create `docs/reviews/m4/run_fixture.py`
- Create `docs/reviews/m4/README.md`
- Modify `src/devharness/__main__.py` only to expose a local `m4-demo` command if the review runner needs it.
- Modify `docs/product/Requirements_Traceability.md`
- Modify `docs/product/향후계획.md` only for issue/evidence links and current M4 status.

Steps:

1. Write RED tests for schema-shaped packet/reference closure and escaped review rendering.
2. Add the strict Draft 2020-12 schema and synthetic example.
3. Build a local review runner using a disposable fixture and no external services.
4. Render Summary → Impact → Tests → Gaps → Gate → Evidence; keep raw output out of HTML/JSON.
5. Run the fixture and validate its generated packet against the schema.

## Task 4 — Actual M4 Evidence and regression checks

Files:

- Create `docs/reviews/m4/observed-gate-summary.json`
- Update `docs/reviews/m4/README.md`

Steps:

1. Capture the M4 branch Restore Point and analyze its actual diff.
2. Record the pre-change main test baseline and post-change result with matching test/environment fingerprints.
3. Generate the actual Assurance packet locally under `/tmp`; commit only the allowlisted gate summary.
4. Run focused M4 tests, full repository tests, compile, strict schema/example validation, and `git diff --check`.
5. Confirm `docs/diagrams/` and raw Evidence are absent from the diff.

## Task 5 — Limited final Gate review and delivery

1. Run one independent review restricted to issues #44–#49 and the approved adversarial cases.
2. If blockers exist, batch-fix once and rerun only affected mandatory checks plus the full required suite once.
3. Record non-blocking findings as GitHub follow-up issues instead of expanding the PR.
4. Commit, push, create one M4 PR, inspect its exact file list and lack of automatic GitHub checks, and merge only when all M4 Gates pass.
5. Link Evidence and close #44–#49 only after merge. Keep external-effect restoration, complete dependency analysis, and human evaluation outside M4.

## Model and retry budget

- Implementation and normal verification: GPT-5.6 Sol.
- Escalate the same mandatory verification to GPT-6 Astra only after two Sol failures.
- If the same mandatory verification fails twice under Astra, stop retrying and diagnose whether the root cause is the test design, environment, product contract, or implementation architecture before further changes.
- Sandbox/tool-launch failures before product execution do not count as product verification failures; they are recorded separately.


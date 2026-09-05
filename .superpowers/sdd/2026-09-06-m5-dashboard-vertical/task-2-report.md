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

---

## Independent review fix round 1

### Status

Closed all six Important and both Minor findings from `task-2-review.md`.
The assembler now validates a TGR by recomputing it through the caller-supplied
authoritative `GuaranteeEvaluator` bound to the same Catalog and EvidenceStore;
rejects incomplete or unsafe M5-06 HWPX human Evidence; validates canonical M2
Baseline/Context shapes; requires Contract/Baseline/Hypothesis/M4 relation
closure for an observed Diagram; exposes bounded `impact.unobserved` rows as
recommended; and requires Event head plus both projected sequences to agree.

### Public API change

`assemble_task_review` gained one backward-compatible optional keyword:

```text
guarantee_evaluator: GuaranteeEvaluator | None = None
```

The added input is necessary because a detached TGR dictionary cannot be
validated authoritatively from the original assembler inputs. If it is absent,
bound to a different Catalog/Store, or rejects the report, every supplied claim
is rendered `not_evaluated` and Task collection completeness remains
`unobserved`. A valid TGR whose authoritative result is itself
`not_evaluated` remains a valid collected report; claim status and source
collection are intentionally independent.

### RED evidence

- Fabricated TGR: the new test first failed with an unexpected-keyword
  `TypeError`, demonstrating that authoritative evaluator validation was not
  available through the API. Forged permitted statements/verdicts, malformed
  envelopes, and stale target commits are now explicit attacks.
- Direct human Evidence: a generic observed probe with only
  `human_observation=True` was returned instead of `None`.
- M5-06 contract alignment: a real `M5-06` HWPX record with material
  input/expected/actual/environment/generated-files/human-observation fields
  initially left completeness `unobserved` because the old predicate expected
  a noncanonical ad-hoc contract.
- Evidence integrity: a same-bytes object symlinked outside the Store is
  explicitly rejected through the shared resolver path; the existing resolver
  attacks continue to cover purge, hash, size, cross-Task, and path failures.
- Diagram closure: the M4 fixture without a closing Baseline/Contract was
  incorrectly `observed` rather than `unobserved`.
- Bounded unobserved relations: `impact.unobserved` initially produced no
  recommended relation row.
- Freshness: inconsistent `ProjectionStatus.projected_sequence` and
  `Freshness.projected_sequence` were incorrectly labeled `fresh`.
- Canonical M2 artifacts: a shallow forged artifact initially counted as
  present; after the first shape fix, a re-fingerprinted malformed nested HWPX
  contract and an internally contradictory Context claim still produced
  `complete`, giving a second focused RED before nested schema validation.

The first attempt at the new valid relationless packet test exposed two test
fixture issues rather than product failures: its hypotheses still referenced
removed relations, then its receipts retained the pre-change Contract
fingerprint. Both fixture bindings were corrected. Importing a TestCase alias
also caused duplicate discovery; the fixture module is now imported without
placing another TestCase class in the test module namespace.

### GREEN evidence

- Focused Dashboard Evidence/View/Freshness suite: 14 tests passed.
- M5-06 direct Evidence plus completeness checks: 2 tests passed.
- Nested Baseline/Context and TGR attack test: 1 test passed.
- Brief regression set: 73 tests passed.
- Full repository discovery: 273 unique tests passed. The prior 276 count
  included three duplicate DashboardView tests collected through a TestCase
  alias; removing that alias explains the count change.
- Python 3.12 compile check for all six Task 2 implementation/test files:
  passed.
- `git diff --check`: passed.

### Self-review

- No Catalog row or workspace file is written by assembly; the pre-existing
  deterministic non-persistence test remains green.
- Invalid TGR content never becomes observed, and a Gate is never substituted
  for a TGR claim.
- Direct feature closure requires requirement `M5-06`, a namespaced HWPX
  subject and adapter, current Task/environment/commit bindings when present,
  material required observation fields, a generated output/files or tool
  error, material human observation, and resolver-backed object integrity.
- M3 project-level provenance and M4 task-level Assurance remain separate;
  relationless or non-closing sources remain `unobserved`.
- Freshness and collection completeness remain independent.

### Integration note

Task 3's registered HWPX adapter must emit the M5-06 Evidence contract consumed
here: HWPX adapter/subject, input, expected, actual, exact environment,
generated files/output or tool error, and a material human observation. This
round does not modify Task 3, raw packets, diagrams, GitHub state, or product
documentation.

---

## Astra bounded correction after diagnosis

### Result and contract

The remaining M2 provenance/Evidence closure, exact public signature, and
relationless proof findings are corrected. This section supersedes the prior
round's claim that adding `guarantee_evaluator` was necessary. The assembler
again exposes exactly the brief's original keyword parameters and constructs
`GuaranteeEvaluator` internally using the supplied Store/Catalog and the
repository-owned `docs/product/guarantee-matrix.v1.json`, following the existing
managed/imported Task composition.

M2 now requires a current-Task registration in the existing EvidenceStore:
`active_configuration`, requirement `M5-05`, collection method
`m2-validated-artifact`, observed/pass, subject equal to the Baseline ID or
Context manifest reference. Fields bind `artifact_kind`
(`project_baseline|context_status`), `artifact_ref`, `artifact_fingerprint`,
`environment`, and `target_commit`. The artifact fingerprint and stored content
hash must identify the entire exact canonical JSON document, including the
Baseline's own fingerprint. Producers validate M2 semantics before registration;
assembly does not create registrations or infer a Manifest from a reference.
This contract was recorded in the Task 2 brief before the correction; the brief
and diagnosis remain local ledger material rather than new tracked files.

The read path resolves explicit Evidence/Event references, including nested
source realization and Context conflict references. Supporting objects use the
existing resolver's Task, purge, record/object integrity, redaction, and symlink
checks. Context support also closes manifest, Task, and explicit source scope;
supplied environment/commit bindings must match. The Baseline closes to the
original execution Contract's ID/fingerprint references. The same M2 closure
result feeds completeness, Harness references, and the Diagram prerequisite.

### RED and proof evidence

- **R3:** a real authoritative report supplied with only the original public
  arguments was incorrectly listed as missing TGR. After internal composition,
  the behavioral check and exact-signature assertion pass.
- **R1:** a schema-valid changed and re-fingerprinted Baseline was accepted as
  collected with no missing-source entry. The regression also verifies that
  removing its registration makes completeness and the Diagram unobserved.
- **R2:** purged Context support still counted as complete. Additional isolated
  cases showed the same failure for missing support, another Task's support,
  mismatched manifest/source bindings, and tampered object bytes. All now fail
  closed. Exact registered artifact bytes, explicit Event refs, and nested
  conflict refs have additional boundary coverage.
- **Relationless proof:** the new positive control has a registered bound
  Baseline, original execution Contract, and valid M4 packet and produces an
  observed graph. Its relationless variant preserves all those bindings and
  a nonempty declared hypothesis, and produces no nodes/edges with unobserved
  state. No correct production branch was changed to manufacture RED evidence.

One initial test-helper error omitted relation Evidence from the packet's
reference set; it was corrected before recording the R1/R2 REDs. The first M2
GREEN attempt revealed that M4's intentionally reduced Contract snapshot omits
Baseline references. Supplying the actual original execution Contract from
the fixture builder resolved that positive-control failure. The subsequent
M2/TGR suite passed; no repeated unresolved required-check failure occurred.

### Validation

Executed with the worktree's existing Python **3.12.14** environment and
`PYTHONPATH=src`:

- Dashboard Identity/Evidence/View/Freshness: **26 tests passed**.
- Dashboard plus affected Evidence, Assurance, Projections, Guarantees,
  Context Architecture, and Control Profile regression set: **149 passed**.
- Full repository discovery: **281 tests passed**. The emitted M3 live-fixture
  drift refusal is expected negative-case output; the suite exited successfully.
- Python compilation of all six Task 2 implementation/test files: passed.
  `py_compile` could not write an existing bytecode-cache location in the
  sandbox; compiling the same six sources in memory succeeded without writes.
- `git diff --check`: passed.
- Complete registered-source assembly repeated twice: identical views,
  unchanged SQLite change count, and byte-identical data-root files. The
  original missing-source non-persistence test also passed.

### Scoped self-review and limits

Only `dashboard_view.py` and the two view/freshness test modules changed in
production/test code. Existing M1/M2 schemas, Evidence types, source resolver,
Guarantee semantics, runtime dependencies, and public parameters were not added
or changed. Registration writes exist only in test/source preparation; the
assembler reads. No Task 3, GitHub, actual-packet, raw-output or diagram artifact
work was performed.

This closes the bounded code/proof issues; independent re-review is still
required. Actual vertical-slice producers must create the specified validated
M2 registrations, or the Dashboard will correctly remain unobserved. The read
path verifies registered provenance and current supporting objects; it does not
independently rerun the M2 interview or reconstruct a missing Context Manifest.

# M4 Assurance Pipeline Design

## Status and scope

This design implements issues #44–#49 on top of the merged M3 runtime contract. It is limited to local Git workspace restoration, bounded impact relations, contract-driven test design, before/after test receipts, regression gating, test-gap detection, and a reviewable Assurance packet.

It does not promise complete dependency analysis, arbitrary command execution, external-effect rollback, every language, every regression, or human comprehension. M5 consumes the packet without redefining its semantics.

## Design choice

Use one standard-library module, `devharness.assurance`, plus one packet schema and one review runner. The evaluator receives explicit documents and Git references; it does not hide model inference or silently execute commands. This is preferred over a plugin graph or general workflow engine because M4 needs deterministic, auditable decisions more than extensibility.

The public operations are:

1. `capture_restore_point(repository, task, observed_at)` records the start commit, binary tracked patch fingerprint, repository/task identity, and explicit exclusions.
2. `verify_restore_point(repository, restore_point)` clones the repository into a temporary disposable directory, reconstructs the recorded commit plus tracked patch, and compares the resulting patch fingerprint. The source workspace is never reset or cleaned.
3. `analyze_impact(repository, restore_point, contract, relation_catalog, observed_at)` reads the actual Git diff and joins it to caller-declared feature, contract, dependency, and test relations. It records relation basis, analysis scope, exclusions, and Unobserved areas. Unknown dynamic relationships remain Unobserved.
4. `build_test_design(contract, impact, requirement_catalog)` maps each Contract criterion to selected test viewpoints, new-feature or regression classification, reasons, and omitted viewpoints.
5. `record_test_baseline(contract, selection, receipts, observed_at)` validates exact test IDs, code references, command/environment fingerprints, results, and Evidence references. Missing results remain `missing`; they are never synthesized.
6. `compare_test_runs(before, after)` requires matching test meaning, command fingerprint, and environment fingerprint. It distinguishes comparable, missing, stale, failed, not-run, inconclusive, and contradictory results.
7. `detect_test_gaps(contract, impact, design, comparison)` reports unmapped Contract criteria, impacted relations without tests, wrong test classification, and missing error/recovery coverage.
8. `evaluate_regression_gate(contract, impact, design, comparison, gaps, override=None)` produces `pass`, `soft_block`, or `hard_block`. Contract criteria without adequate observed evidence hard-block. Non-required residual risk may soft-block. A Soft Block override requires a product authority record, reason, and residual risk; a Hard Block cannot be overridden.
9. `build_assurance_packet(...)` validates identity/reference closure and creates a canonical fingerprint. Repeated evaluation with unchanged input fingerprints returns the same semantic packet and does not run tests again.

## Contract binding

The current Task Execution Contract is authoritative:

- `contract_id`, `fingerprint`, Task identity, `validation_criteria`, `gate_criteria`, protected targets, and external-effect declarations are copied by reference and checked.
- Every `gate_criteria` item must have a design mapping and adequate Evidence. Unknown or duplicate criteria fail closed.
- Test receipts identify which Contract criterion and validation command they cover. A new-feature test cannot satisfy a required regression relation.
- The user's delegation to develop OwnHands is not a product override record. Only `decision_source: explicit_product_approval` scoped to the exact Contract and `soft_block_override` is accepted.

## Evidence states

Test result and evidence basis remain separate axes:

- Result: `pass`, `fail`, `not_run`, `inconclusive`, `missing`.
- Basis: `observed`, `inferred`, `unobserved`.
- Comparison: `comparable_pass`, `regression`, `missing_before`, `missing_after`, `stale`, `incomparable`, `not_run`, `inconclusive`, `contradicted`.

Only observed, comparable results can establish regression success. Absence, uncertainty, staleness, conflict, and unsupported paths never collapse into pass.

## Restore boundary

Restore Point covers only the local tracked Git workspace represented by the start commit and binary patch. Untracked files, databases, external APIs, deployments, messages, payments, and shared infrastructure are explicit exclusions. Verification operates on a disposable clone and cannot mutate the user's source worktree.

## Impact boundary

Impact v1 uses actual changed paths first and joins only declared or statically observed relationships. Each relation carries `basis` and `evidence_refs`. The packet lists unsupported languages, dynamic runtime relationships, external service effects, and untracked content as excluded or Unobserved. It never claims completeness.

## Gate decision table

| Condition | Decision |
|---|---|
| Contract identity/reference mismatch, duplicate/unknown criterion, protected-target change, observed failure, regression, missing required before/after result, incomparable required environment, required test gap | Hard Block |
| Contract criteria pass but a non-required residual risk or bounded Unobserved relation remains | Soft Block |
| All Contract criteria have adequate observed comparable Evidence and no required gap | Pass |
| Soft Block plus exact product override record | Pass with audited override |
| Hard Block plus any ordinary override | Hard Block and rejected override |

## Test strategy

Tests are written first and must fail because `devharness.assurance` is absent. Fixtures cover:

- actual disposable Git restore reconstruction and source-worktree preservation;
- changed paths, declared relations, exclusions, and Unobserved relations;
- new-feature versus regression classification;
- missing/stale/incomparable before Evidence;
- same-test and same-environment comparison;
- unknown, duplicate, omitted, or swapped Contract criteria;
- fail/not-run/inconclusive/contradictory Evidence resisting pass;
- Soft Block override scope/authority/audit fields;
- Hard Block override rejection;
- repeated completion evaluation remaining deterministic without executing commands.

## Review artifact

`docs/reviews/m4/run_fixture.py` creates an Assurance packet from a disposable local Git fixture and renders a compact HTML review. Raw test output stays under the supplied local data root; committed examples contain only synthetic allowlisted data and hashes. This artifact is not the M5 production UI.


# ownhands M1.5 Context Architecture Review Package

## Review state

M1.5 issues #16–#21의 정책, Proposed ADR, strict contracts, deterministic probes와 고정 비교 harness를 검토할 수 있다. Production Compiler, Codex runtime adapter, 전역 config 변경, Production UI와 plugin vendoring은 포함하지 않았다. ADR-0009는 실제 9-run Gate와 독립 검토 전까지 `Proposed`다.

## Issue coverage

| Issue | Review artifact | Executable evidence |
|---|---|---|
| #16 Placement Policy | `docs/product/Context_Placement_Policy.md` | lint placement/router fixtures |
| #17 Task Harness Manifest | manifest schema + managed/imported examples | `validate_manifest` attacks and strict Ajv validation |
| #18 Context Lint | rule/limitation fixtures | `m15-context-lint`, no autofix |
| #19 Applicability Gate | ADR trigger/cache contract | transition, cache and safety-control tests |
| #20 A/B/C comparison | `comparison-package.json`, fixture and runner | exactly nine fixed run specs; actual runs pending |
| #21 Guarantee/Status | proposed Matrix + Status schema/example | Loaded≠improvement, absence≠success and class-mixing attacks |

## Tested contracts

- `context_sources` and `control_sources` use separate allowed taxonomies and cannot share a source ID.
- `instruction_overlay` can reference only Context; `control_overlay` can reference only Control and records immutable safety controls.
- Applicability, configured/loaded/enforced realization, and observed/inferred/unobserved basis remain separate.
- All nested Evidence references must appear in the Manifest envelope and resolve in the caller-provided M1 Evidence registry; Event references also must resolve.
- Gate triggers are limited to Task start, scope expansion, phase transition, external effect/permission addition, and before a completion claim. Scope, phase, permissions or source hash invalidate the canonical-input cache.
- Lint findings include evidence, location, impact and suggestion. Unsupported formats and semantic/dynamic paths remain Unobserved. No file is modified.
- Context Guarantee claims require claim-specific observed Evidence. A Context loading receipt cannot support the improvement claim, and lack of a lint finding cannot support a “no conflict” claim.
- Status summaries keep Active Context and Active Controls separate and require Evidence drill-down.

## RED evidence

First feature RED:

```text
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_context_architecture -v
ModuleNotFoundError: No module named 'devharness.context_architecture'
Ran 1 test in 0.000s
FAILED (errors=1)
```

The earlier plain `uv run` attempt could not initialize the user cache and is an environment error, not RED evidence.

CLI RED before the entrypoint change:

```text
Ran 3 tests in 0.137s
FAILED (failures=2)
invalid choice: 'm15-comparison-plan'
invalid choice: 'm15-context-lint'
```

Acceptance follow-up RED before evidence binding and comparison evaluation:

```text
Ran 8 tests in 0.003s
FAILED (failures=5)
foreign source/Manifest/task evidence was accepted; completed machine-observed comparisons remained not_evaluated
```

The terminal-sample follow-up also failed once because a failed run was incorrectly treated as missing rather than consuming one of the fixed nine slots.

## Local verification commands

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_context_architecture -v
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ownhands-m15-pycache PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m compileall -q src tests docs/reviews/m1.5/run_comparison.py
```

2026-09-05 final local run: focused M1.5 tests 26/26 passed in 0.154s; full repository tests 133/133 passed in 0.639s; redirected compile check and `git diff --check` exited 0. The first compile attempt tried to write repository `__pycache__` directories and was denied by the worktree sandbox, so it is not counted as successful compile evidence.

Strict draft 2020-12 schema checks use the repository's pinned temporary validator pattern and add no dependency:

```bash
npm_config_cache=/tmp/ownhands-m15-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/task-harness-manifest.schema.json -d docs/product/task-harness-manifest.managed.example.json -d docs/product/task-harness-manifest.imported.example.json
npm_config_cache=/tmp/ownhands-m15-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/context-guarantee-matrix.schema.json -d docs/product/context-guarantee-matrix.proposed.json
npm_config_cache=/tmp/ownhands-m15-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/context-status-report.schema.json -d docs/product/context-status-report.example.json
npm_config_cache=/tmp/ownhands-m15-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/context-comparison-package.schema.json -d docs/reviews/m1.5/comparison-package.json
```

Final strict validation accepted both Manifest examples, the proposed Context Guarantee Matrix, the Context Status example and the comparison package with no strict-type/tuple warning. Four isolated Manifest mutations—mixed source class, missing scope, Loaded/pass with Unobserved basis, and unknown source type—were rejected. The no-quota plan probe emitted 9 runs, A/B/C each 3 times, with one model, effort, target commit and Control fingerprint.

Generate the fixed plan without spending Codex quota:

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m devharness m15-comparison-plan --package docs/reviews/m1.5/comparison-package.json --target-commit "$(git rev-parse HEAD)"
```

## Pending exact nine-run command

Run only after the M1.5 review commit is checked out cleanly. This is the one remaining quota-consuming command; it creates one isolated workspace per planned run and invokes `codex exec` exactly nine times:

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python docs/reviews/m1.5/run_comparison.py --package docs/reviews/m1.5/comparison-package.json --repo-root . --target-commit "$(git rev-parse HEAD)" --output-root /tmp/ownhands-m15-context-comparison --execute
```

Fixed conditions are `gpt-5.6-sol`, `medium`, one literal prompt, one captured commit, macOS arm64 / Codex CLI 0.153.3 / Python 3.12, workspace-write sandbox, no approvals, network disabled, rules ignored and user config/hooks disabled. A/B/C use one fixture and cross-over order `A B C C A B B C A`, each exactly three times.

The runner preserves raw Codex JSONL and fixture test receipts. Token values become Observed only when the JSONL contains a numeric usage receipt; otherwise they remain `null / Unobserved`. It records instruction violations only for the fixture's machine-checkable tests and change-only-`harness.py` boundary. After nine terminal records, it writes an individual-results comparison and either an evidence-bounded non-regression recommendation or a no-improvement result. Failed or aborted executions remain in their assigned condition, consume their fixed slot, and are never retried. `human_understanding` and `human_review_seconds` remain `null / Unobserved`; the machine result does not claim a human benefit.

## Known limits and blockers

- Actual A/B/C outcomes are not observed because the nine Codex runs were intentionally not invoked.
- The lexical lint prototype cannot establish semantic equivalence, generated prompt content, dynamic paths, binary formats, or runtime load. Those paths are explicitly Unobserved.
- JSON Schema cannot enforce cross-array source identity or Event/Evidence reference closure; `validate_manifest` provides that semantic gate.
- The comparison runner is a disposable evaluation probe, not the M2 Production Compiler or a runtime integration.
- ADR acceptance remains blocked on the 9-run result and independent review. If the gate later passes, the approval record must identify `사용자 사전 위임에 따른 에이전트 결정`.

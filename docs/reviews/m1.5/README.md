# ownhands M1.5 Context Architecture Review Package

## Review state

M1.5 issues #16–#21의 정책, Accepted ADR, strict contracts, deterministic probes와 고정 비교 harness를 검토할 수 있다. Production Compiler, Codex runtime adapter, 전역 config 변경, Production UI와 plugin vendoring은 포함하지 않았다. ADR-0009의 승인 방식은 `사용자 사전 위임에 따른 에이전트 결정`이며 사용자가 직접 검토했다고 주장하지 않는다.

## Issue coverage

| Issue | Review artifact | Executable evidence |
|---|---|---|
| #16 Placement Policy | `docs/product/Context_Placement_Policy.md` | lint placement/router fixtures |
| #17 Task Harness Manifest | manifest schema + managed/imported examples | `validate_manifest` attacks and strict Ajv validation |
| #18 Context Lint | rule/limitation fixtures | `m15-context-lint`, no autofix |
| #19 Applicability Gate | ADR trigger/cache contract | transition, cache and safety-control tests |
| #20 A/B/C comparison | `comparison-package.json`, fixture and runner | 9/9 terminal records; C machine-only recommendation |
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

Post-review crossover RED: the focused adversarial test failed because swapping the first two conditions and their Context fingerprints preserved the balanced set and was incorrectly accepted. Exact sequence/condition/repetition/run ID validation then made the test GREEN.

## Local verification commands

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_context_architecture -v
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ownhands-m15-pycache PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m compileall -q src tests docs/reviews/m1.5/run_comparison.py
```

2026-09-05 final post-review run: affected Guarantee/Comparison tests 10/10 passed in 0.002s; full repository tests 134/134 passed in 0.594s; redirected compile check and `git diff --check` exited 0. The first compile attempt tried to write repository `__pycache__` directories and was denied by the worktree sandbox, so it is not counted as successful compile evidence.

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

## Exact nine-run command

This command has already been run for the reviewed records and must not be retried. It is retained only for audit reproducibility:

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python docs/reviews/m1.5/run_comparison.py --package docs/reviews/m1.5/comparison-package.json --repo-root . --target-commit 71f6a8220c4e929ece39e76fadbdcdd15af9c7d7 --output-root /tmp/ownhands-m15-context-comparison --execute
```

Fixed conditions are `gpt-5.6-sol`, `medium`, one literal prompt, one captured commit, macOS arm64 / Codex CLI 0.153.3 / Python 3.12, workspace-write sandbox, no approvals, network disabled, rules ignored and user config/hooks disabled. A/B/C use one fixture and cross-over order `A B C C A B B C A`, each exactly three times.

The runner preserves raw Codex JSONL and fixture test receipts. Token values become Observed only when the JSONL contains a numeric usage receipt; otherwise they remain `null / Unobserved`. It records instruction violations only for the fixture's machine-checkable tests and change-only-`harness.py` boundary. After nine terminal records, it writes an individual-results comparison and either an evidence-bounded non-regression recommendation or a no-improvement result. Failed or aborted executions remain in their assigned condition, consume their fixed slot, and are never retried. `human_understanding` and `human_review_seconds` remain `null / Unobserved`; the machine result does not claim a human benefit.

## Observed nine-run summary

Raw JSONL과 실행별 workspace는 `/tmp/ownhands-m15-context-comparison`에만 보관하며 Git에 포함하지 않는다. 아래 값은 synthetic Fixture의 공유 가능한 요약이다.

| Run | 조건 | 요구·테스트 | 지침 위반 | 범위 밖 변경 | 시간(초) | Input / Output token |
|---|---|---|---:|---:|---:|---:|
| 01 | A | pass | 0 | 0 | 83.720 | 265,592 / 2,039 |
| 02 | B | fail | 1 | 0 | 25.052 | 60,910 / 852 |
| 03 | C | pass | 0 | 0 | 55.130 | 168,565 / 1,584 |
| 04 | C | pass | 0 | 0 | 54.092 | 173,138 / 1,581 |
| 05 | A | fail | 1 | 0 | 44.138 | 141,291 / 1,345 |
| 06 | B | pass | 0 | 0 | 57.689 | 169,758 / 1,724 |
| 07 | B | pass | 0 | 0 | 68.539 | 201,055 / 2,104 |
| 08 | C | pass | 0 | 0 | 61.820 | 175,600 / 1,915 |
| 09 | A | pass | 0 | 0 | 75.526 | 243,502 / 2,151 |

조건별 결과는 A 2/3, B 2/3, C 3/3이며 모든 조건의 범위 밖 변경은 0건이다. 실행 프로세스 실패·중단은 0건이다. 관찰된 이 Fixture의 기계 지표에서는 C가 A보다 비퇴행 개선됐으므로 C를 M2 기본 Context 조합으로 추천한다. 사람 이해도와 사람 검토 시간은 `Unobserved`다.

## Known limits

- The unchanged nine records were re-evaluated after exact crossover validation: 9 terminal, 0 failed, 0 aborted; machine evidence recommends C over A for this fixture only. Human understanding and review time remain Unobserved.
- The lexical lint prototype cannot establish semantic equivalence, generated prompt content, dynamic paths, binary formats, or runtime load. Those paths are explicitly Unobserved.
- JSON Schema cannot enforce cross-array source identity or Event/Evidence reference closure; `validate_manifest` provides that semantic gate.
- The comparison runner is a disposable evaluation probe, not the M2 Production Compiler or a runtime integration.
- 제한 Gate Review에서 발견한 crossover-order fail-open은 한 번의 수정·재검증으로 닫혔다. 추가 광범위 감사나 새 결함 탐색 라운드는 수행하지 않았다.

# ownhands M2 Control Profile Lifecycle Review Package

## Scope

This package exercises issues #25–#30 as one synthetic, local-only preflight slice:

```text
read-only Profiler → adaptive Interview → versioned Baseline
→ Task Overlay / Execution Contract → dry-run Compile/Lint → local Preview
```

It does not start a Codex task, apply user/global configuration, claim runtime loading or enforcement, perform M4 assurance, or provide the M5 production UI. The only write/apply behavior is tested against a temporary tree containing the explicit `.ownhands-disposable` marker and a real product-approval-shaped record; synthetic interview responses never authorize it.

## TDD evidence

Initial RED:

```text
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_control_profile -v
ModuleNotFoundError: No module named 'devharness.control_profile'
Ran 1 test in 0.000s
FAILED (errors=1)
```

Adaptive-interview RED:

```text
Expected only failure_impact and external_effect questions.
The pre-fix implementation asked all five decisions, including three safely inferable values.
Ran 1 test; FAILED (failures=1).
```

Project-contract freshness RED:

```text
Changing REQUIREMENTS.md returned fresh instead of stale.
Ran 1 test; FAILED (failures=1).
```

Bounded #29 path-containment RED:

```text
Ran 2 tests in 0.012s
FAILED (failures=2)
apply accepted ../outside.txt and rollback accepted an alternate/tampered journal path
```

The fix validates every artifact and journal entry before the first write, rejects absolute/empty/dot/parent paths and symlink components, and accepts only the exact in-root rollback journal.

## Contracts and adversarial coverage

- Profiler output is deterministic and read-only; it records source hashes, scope and freshness while sensitive files expose names only. Symlinks and unsupported formats are Unobserved.
- Interview questions contain one decision, recommendation and reason. Ambiguous, declined and silent responses remain unresolved and never become approval. Fixed responses are synthetic fixture evidence, not user testing.
- Baselines bind Project, Worktree and Environment; later versions require a predecessor. Structure, dependency, contract and Control-source hashes contribute to staleness. Foreign identity and unresolved M1 references fail closed.
- Permission expansion requires exact scope, reason, Task duration and a non-expired explicit product approval. Missing, fixture-derived, declined or expired authority is inactive and hard-blocked. Imported runtime history remains Unobserved.
- Compiler candidates cover config, AGENTS, Rules, Hooks, Sandbox and Approval. Precedence conflicts, duplicate Hooks, excessive permission, missing protected targets and unsupported versions block apply or remain Unobserved.
- Apply requires a marked disposable tree, current before-hashes, no existing journal and exact contract approval. Atomic writes are hash-checked; rollback refuses changed targets and verifies restoration.
- Preview uses headings, tables, text labels, SVG title/description, keyboard skip structure, escaped values and resolvable Evidence links. Stale diff and broken drill-down fail closed; a missing journal is shown as `Restore unavailable` rather than apply-ready UI.

## Local fixture command

This writes raw Evidence only under `/tmp` and generates a local review artifact:

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python docs/reviews/m2/run_fixture.py --data-root /tmp/ownhands-m2-evidence --output /tmp/ownhands-m2-preview.html
```

## Verification commands

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_control_profile -v
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ownhands-m2-pycache PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m compileall -q src tests docs/reviews/m2/run_fixture.py
npm_config_cache=/tmp/ownhands-m2-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/project-baseline.schema.json -d docs/product/project-baseline.example.json
npm_config_cache=/tmp/ownhands-m2-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/task-execution-contract.schema.json -d docs/product/task-execution-contract.example.json
npm_config_cache=/tmp/ownhands-m2-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/control-profile-compiler.schema.json -d docs/product/control-profile-compiler.example.json
git diff --check
```

2026-09-05 final local verification: focused M2 tests 13/13 passed in 0.078s; the full repository suite 147/147 passed in 0.729s; compile and `git diff --check` exited 0. Strict draft 2020-12 validation accepted the Baseline, Execution Contract and Compiler examples, and all stored fingerprints/diff hashes matched their canonical contents.

## Evidence boundaries

- Project files and declared config are `Configured` candidates only where directly observed.
- Candidate compiler artifacts remain `not_run / unobserved` until disposable apply; M2 never labels them Loaded or Enforced.
- Runtime Codex configuration, trusted-project activation, Hook execution, Rules behavior, Sandbox behavior and approval enforcement remain `Unobserved` for M3.
- Profiler hashes, fixture test/diff receipts, journal writes and rollback hashes are `Observed` within their exact synthetic scope.
- Semantic completeness, unsupported dynamic paths and actual human understanding remain `Unobserved`.

# ownhands M4 Assurance Pipeline Review Package

## Scope

This package exercises issues #44–#49 as one local-only slice:

```text
Task Execution Contract assurance_draft
→ tracked Git Restore Point
→ disposable-clone reconstruction
→ actual-diff declared relation join
→ Test Design Memo
→ before/after receipts
→ gap detection
→ regression Gate
→ Assurance packet and compact review
```

It does not implement the M5 production UI, execute caller-supplied commands, claim complete dependency analysis, restore external effects, or treat development delegation as product approval.

## TDD evidence

Initial Assurance RED:

```text
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_assurance -v
ModuleNotFoundError: No module named 'devharness.assurance'
Ran 1 test in 0.000s
FAILED (errors=1)
```

Review RED:

```text
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_m4_review -v
ModuleNotFoundError: No module named 'devharness.m4_review'
Ran 1 test in 0.000s
FAILED (errors=1)
```

The next schema/example RED had two expected `FileNotFoundError` results after the renderer security tests were already green.

## Local fixture command

Raw output remains under the supplied repository-external data root. The packet and review are local outputs, not committed runtime Evidence.

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python docs/reviews/m4/run_fixture.py --data-root /tmp/ownhands-m4-evidence --packet /tmp/ownhands-m4-assurance-packet.json --output /tmp/ownhands-m4-review.html
```

## Verification commands

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_assurance tests.test_m4_review -v
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ownhands-m4-pycache PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m compileall -q src tests docs/reviews/m4/run_fixture.py
npm_config_cache=/tmp/ownhands-m4-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/task-execution-contract.schema.json -d docs/product/task-execution-contract.example.json
npm_config_cache=/tmp/ownhands-m4-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/assurance-packet.schema.json -d docs/product/assurance-packet.example.json
git diff --check
```

## Evidence boundaries

- Restore covers only the start commit plus the captured tracked binary patch. Untracked content, submodule working trees, symlink targets, databases, APIs, deployments and shared infrastructure are excluded or Unobserved.
- Impact v1 starts from the actual tracked diff and joins only declared or statically observed relations. Dynamic runtime paths and unsupported relations stay Unobserved.
- Only observed receipts with matching test meaning, command, selection scope, environment, Contract fingerprint and start/target patch hashes can become `comparable_pass`.
- `no_adequate_test`, wrong classification, required error/recovery omissions, missing/stale/incomparable/contradictory Evidence, protected changes and observed failures cannot collapse into pass.
- A Soft Block accepts only exact `explicit_product_approval` scoped to `soft_block_override` for the Contract fingerprint. A Hard Block remains blocked.
- GM-013 remains the existing evidence claim that related tests ran; M4 comparison success and test-gap semantics live in the Assurance packet and do not redefine `GuaranteeEvaluator`.

## Actual branch observation

`observed-gate-summary.json` records the allowlisted result for base `f2a1dd3` through target `5ce66a9`. Restore reconstruction passed without changing the source worktree; 18 tracked paths were analyzed, all five before/after meanings were comparable after the change, and no required test Gap remained. The resulting Gate is `soft_block / unobserved`, not Pass: declared path relations do not establish complete dynamic runtime dependency coverage, and no exact product override was supplied.

The full actual packet is local at `/tmp/ownhands-m4-actual-packet-5ce66a9.json`; its raw before/after command output is local under `/tmp/ownhands-m4-actual-raw-5ce66a9/`. Those paths are intentionally not committed.

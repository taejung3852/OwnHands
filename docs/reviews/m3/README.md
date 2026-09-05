# ownhands M3 Managed Runtime Review Package

## Current status

The M3 runtime Gate is **blocked**. Seven separately authorized, one-shot attempt claims on 2026-09-05 produced no terminal Managed Task. The first three App Server runs respectively exposed a legacy JSON-RPC envelope assumption, an exact upstream user-agent assumption, and an interleaved `thread/started` notification that was treated as the direct `thread/start` response. The fourth claim failed closed before App Server launch because the disposable fixture omitted required synthetic config, rule, and hook sources. The fifth claim passed fixture preparation and reached actual task execution after the interleaving fix, but timed out. During that fifth run a zero-byte sibling marker was created, proving that locating the disposable repository under the OS temporary root made the intended sibling-write sandbox denial invalid. The sixth claim used a repository outside the OS temporary root and persisted bounded failure progress, which showed no approval request before timeout. The seventh claim used the boundary-driven trigger from commit `ed9465a`: it observed one command approval request, the predetermined decline, `serverRequest/resolved`, and the declined terminal command item in one run, but the global 180-second deadline expired before `turn/completed`. The sibling marker remained absent, but the bounded failure record does not preserve the exact command result needed to prove the separate sandbox-denial requirement. All raw attempt ledgers remain local under separate `/tmp` roots with status `failed`; no runtime transcript packet was produced or committed.

Commits `19f8224` and `7d309a5` corrected the first two defects, commit `154ac1a` adds bounded routing for interleaved notifications, and commit `2f42a0b` services interleaved approval requests while persisting bounded failure progress. Commit `ed9465a` removes the ineffective project-rule plus harmless-`printf` trigger: under `workspace-write / on-request`, that action does not naturally require approval, and project-local Rules load only for a trusted project. The replacement asks for a default-sandbox sibling write followed by exactly one elevated retry of the same action. Local RED/GREEN coverage, the 199-test suite, compile, schema validation, and diff checks passed before the seventh claim. That live result proves the command approval transaction path can complete, but it does not prove terminal-turn closure or the separate sandbox denial. The seventh authorization is consumed and must not be silently retried. Any next change must first address the active-run deadline and record enough allowlisted command outcome to establish the sandbox result; a further one-shot live claim requires explicit authorization. Issues #32–#36 still lack their complete required real runtime Evidence, while #37's fixture-only Imported boundary remains independently testable. The committed example remains `blocked / unobserved` and M4 must not start.

## Safety boundary

- The target must be the exact root of a fresh Git repository outside the OS temporary root, contain a regular `.ownhands-disposable` marker and all required synthetic source files, and be validated before the attempt is claimed. Before any version/schema/runtime command, the CLI exclusively creates `.ownhands-m3-live-attempt`; that repository can never be used for a second attempt, even with a different data root.
- `--repository`, `--data-root`, `--output`, `--codex-bin`, `--model`, and `--timeout` are mandatory, and execution additionally requires explicit `--live`.
- Raw Catalog, Evidence objects, generated protocol schema, normalized runtime receipts, and the immutable attempt ledger stay under the supplied `/tmp` data root. The data root must not be inside any Git worktree.
- The adapter launches only its own `codex app-server` child. It does not read, resume, steer, or approve a Desktop task and does not enumerate or change user/global configuration.
- The approval decision is the predetermined `decline`. Missing identity, terminal, sandbox-denial, approval-resolution, Evidence, Event, protocol, or restore linkage blocks the Gate.
- The committed JSON contains hashes and allowlisted states, never prompts, command output, secret-like configuration, external private paths, raw thread/turn IDs, or transcripts.

## Historical one-shot operator command

The following shape documents the consumed attempt; it is not authorization to rerun it. Codex CLI 0.153.3 and model `gpt-5.6-luna` were used with a fresh disposable repository and a new `/tmp` data root:

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python docs/reviews/m3/run_live_probe.py \
  --repository /Users/parktaejung/Documents/ChatGPT/DevHarness-worktrees/ownhands-m3-live-disposable \
  --data-root /tmp/ownhands-m3-live-evidence \
  --output /tmp/ownhands-m3-runtime.json \
  --codex-bin /absolute/path/to/codex \
  --model gpt-5.6-luna \
  --timeout 180 \
  --live
```

Do not remove an attempt ledger, create a replacement repository, or rerun. The seventh one-shot claim is consumed. A new live attempt requires an explicit policy/authorization change; until then the recorded non-zero result keeps M3 blocked.

## Verification

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_m3_review -v
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ownhands-m3-pycache PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m compileall -q src tests docs/reviews/m3
npm_config_cache=/tmp/ownhands-m3-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/managed-task-runtime.schema.json -d docs/product/managed-task-runtime.example.json
git diff --check
```

## Evidence boundary

`Configured`, `Loaded`, and `Enforced` are control stages. `Observed`, `Inferred`, and `Unobserved` are evidence bases. The packet never promotes one axis into the other. Imported history remains `not_run / unobserved`; current imported snapshot, diff, and directly executed test receipt do not recreate prior Managed control history. Human Desktop workflow friction remains `not_run / unobserved` and is tracked by issue #38.

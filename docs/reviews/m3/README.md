# ownhands M3 Managed Runtime Review Package

## Current status

The M3 runtime Gate remains **blocked** after the authorized final-closure run on 2026-09-06. The sandbox check is now a model-independent `codex sandbox` sibling-write probe, and it produced an observed non-zero denial while the outside marker remained absent. The separate App Server run observed the approval request, predetermined decline, `serverRequest/resolved`, declined terminal item, and `turn/completed`. Event/Evidence closure, protocol, identity, sandbox denial, approval chain, restore, and terminal-turn checks all passed.

The only failing required check is `instruction_loaded`. Even with a non-persistent, process-local trust override scoped to the disposable repository, the installed App Server returned no matching `AGENTS.md` entry in `thread/start.instructionSources`. The source is therefore only Configured; it is not promoted to Loaded. This blocks issue #34 and M3. The result is recorded in the local sanitized packet at `/tmp/ownhands-m3-runtime-final-closure-20260906.json`; raw Evidence remains local under `/tmp/ownhands-m3-live-evidence-final-closure-20260906` and is not committed. No further live attempt is authorized or implied by this record, and M4 must not start.

Local RED/GREEN coverage includes buffered stdio delivery, optional terminal item summaries, deterministic sandbox denial, and process-local disposable-project trust. The full 215-test suite, compile check, and diff check passed before this final run. GitHub has no automatic checks configured, so these are local verification results only.

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

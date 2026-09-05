# ownhands M3 Managed Runtime Review Package

## Current status

The M3 runtime Gate is **blocked**. The initial live App Server attempt on 2026-09-05 failed during the handshake because the adapter required a legacy JSON-RPC envelope member. After explicit user authorization, one fresh attempt used the corrected adapter and failed at the next initialize check because the returned upstream user-agent string did not exactly equal the adapter's assumed literal. Both raw attempt ledgers remain local under separate `/tmp` roots with status `failed`; no runtime transcript packet was produced or committed.

The generated Codex CLI 0.153.3 schema showed that current wire messages omit the legacy `jsonrpc` member. Commit `19f8224` corrected that defect. The official initialize contract describes `userAgent` as the upstream service identity, not a stable exact mirror of the local CLI version; the adapter's exact literal check is therefore a separate compatibility defect. The authorized fresh attempt has been consumed and must not be silently retried. Issues #32–#36 still lack their required real runtime Evidence, while #37's fixture-only Imported boundary remains independently testable. The committed example remains `blocked / unobserved` and M4 must not start.

## Safety boundary

- The target must be the exact root of a fresh Git repository containing a regular `.ownhands-disposable` marker. Before any version/schema/runtime command, the CLI exclusively creates `.ownhands-m3-live-attempt`; that repository can never be used for a second attempt, even with a different data root.
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

Do not remove the attempt ledger, create a replacement repository, or rerun. A new live attempt requires an explicit policy/authorization change; until then the recorded non-zero result keeps M3 blocked.

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

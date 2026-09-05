# M3 Managed Task Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect a fresh M2 contract to a standalone App-Server-managed Codex task and store truthful runtime Control Evidence for Managed and Imported task modes.

**Architecture:** A stdlib JSON-RPC process adapter validates App Server messages and feeds normalized records into a runtime-control evaluator. A managed-task coordinator binds those records to the existing M1 identity/event/evidence stores; a separate importer preserves the narrower Imported Task guarantee boundary. One disposable live probe supplies the required runtime Evidence.

**Tech Stack:** Python 3.12 standard library, installed `codex-cli 0.153.3`, App Server stdio JSON-RPC v2, SQLite-backed M1 stores, `unittest`, JSON Schema draft 2020-12.

**Spec:** `docs/superpowers/specs/2026-09-05-m3-managed-task-integration-design.md`

## Global Constraints

- Product name is `ownhands`; keep `devharness` as the Python import namespace.
- Use only a new non-sensitive disposable Git repository for live probes.
- Never list, read, resume, steer, inject into, or mutate existing Desktop tasks.
- Never write user/global Codex configuration or store its arbitrary values.
- Raw App Server messages and Evidence stay outside Git; committed receipts are allowlisted and redacted.
- `Configured`, `Loaded`, and `Enforced` are independent checks; unavailable data is `not_run/unobserved`.
- Rules are experimental and cannot be a required core guarantee.
- Fake transports prove parser behavior only; they cannot satisfy the live runtime Gate.
- Do not implement M4, M5, deployment, publication, external API effects, payments, or secret transmission.
- Human workflow friction remains Unobserved and is tracked by issue #38.

---

### Task 1: App Server stdio adapter

**Files:**
- Create: `src/devharness/codex_app_server.py`
- Create: `tests/test_codex_app_server.py`
- Create: `tests/fixtures/m3/app-server-success.jsonl`
- Create: `tests/fixtures/m3/app-server-attacks.json`

**Interfaces:**
- Produces `AppServerConfig`, `AppServerRecord`, `AppServerRun`, `AppServerError`, `run_app_server(config, transport_factory, sink, approval_handler)`.
- `AppServerRun` contains only normalized allowlisted messages, the active thread/turn IDs, terminal status, instruction sources, and version/schema identity.

- [ ] **Step 1: Write literal protocol tests before production code.**

```python
def test_handshake_thread_turn_and_terminal_chain_is_scope_checked():
    run = run_app_server(CONFIG, fake_transport(SUCCESS_JSONL), records.append, decline)
    self.assertEqual("completed", run.terminal_status)
    self.assertEqual("thread-fixture", run.thread_id)
    self.assertEqual(["AGENTS.md"], run.instruction_sources)

def test_cross_thread_approval_cannot_be_answered_or_recorded_as_enforced():
    with self.assertRaisesRegex(AppServerError, "approval scope"):
        run_app_server(CONFIG, fake_transport(CROSS_THREAD_JSONL), records.append, decline)
```

Cover malformed JSON, duplicate response ID, response error, premature exit, timeout, unknown terminal state, cross-thread/turn/item approval, missing `serverRequest/resolved`, and terminal item mismatch. Expectations must be hand-written literals, not produced by adapter helpers.

- [ ] **Step 2: Run the focused tests and capture RED.**

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_codex_app_server -v
```

Expected: import failure because `devharness.codex_app_server` does not exist.

- [ ] **Step 3: Implement the minimal adapter.**

```python
@dataclass(frozen=True)
class AppServerConfig:
    executable: str
    cwd: Path
    model: str
    sandbox: str
    approval_policy: str
    prompt: str
    timeout_seconds: float
    codex_version: str
    protocol_fingerprint: str

def run_app_server(
    config: AppServerConfig,
    transport_factory: Callable[[AppServerConfig], JsonRpcTransport],
    sink: Callable[[AppServerRecord], None],
    approval_handler: Callable[[AppServerRecord], str],
) -> AppServerRun: ...
```

Use monotonically allocated request IDs, exact response matching, a single active thread/turn, and a deadline. Allowlist record fields and hash non-allowlisted payloads. The production transport starts only `codex app-server --listen stdio://`; its terminate/kill methods may target only its own child process.

- [ ] **Step 4: Run Task 1 tests to GREEN and run a mutation check.**

Delete or invert each scope check mentally and confirm a named test would fail. Run the focused command again.

- [ ] **Step 5: Commit Task 1.**

```bash
git add src/devharness/codex_app_server.py tests/test_codex_app_server.py tests/fixtures/m3
git commit -m "M3: add App Server protocol adapter"
```

### Task 2: Managed Task start and runtime controls

**Files:**
- Create: `src/devharness/managed_tasks.py`
- Create: `src/devharness/control_runtime.py`
- Create: `tests/test_managed_tasks.py`
- Create: `tests/test_control_runtime.py`

**Interfaces:**
- Consumes M2 Baseline, Execution Contract, explicit approval record, start commit/patch fingerprint, marked disposable repository, and `AppServerRun`.
- Produces `ManagedTaskPacket`, `ControlValidationPacket`, M1 Event/Evidence references, and a minimal restore receipt.

- [ ] **Step 1: Write failing tests for the M2 handoff and identity chain.**

```python
def test_managed_start_requires_fresh_bound_approved_contract_and_restore_basis():
    for mutation in (stale_baseline, foreign_task, expired_approval, missing_start_commit):
        with self.subTest(mutation=mutation.__name__), self.assertRaises(ManagedTaskError):
            prepare_managed_task(mutation(valid_request()))

def test_runtime_record_does_not_promote_configured_to_loaded_or_enforced():
    packet = evaluate_runtime_controls(configured_only_run())
    self.assertEqual("pass", packet["config"]["configured"]["result"])
    self.assertEqual("not_run", packet["config"]["loaded"]["result"])
    self.assertEqual("not_run", packet["config"]["enforced"]["result"])
```

Also cover wrong Project/Worktree/Task/Environment, unresolved Evidence references, unmarked/non-Git target, dirty start state without patch fingerprint, and Contract fingerprint mismatch.

- [ ] **Step 2: Run focused tests and capture RED.**

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_managed_tasks tests.test_control_runtime -v
```

- [ ] **Step 3: Implement the coordinator and independent control evaluator.**

```python
def prepare_managed_task(request: dict, *, now: str) -> dict: ...
def record_managed_run(catalog: Catalog, prepared: dict, run: AppServerRun) -> dict: ...
def evaluate_runtime_controls(prepared: dict, run: AppServerRun) -> dict: ...
def verify_start_restore(repository: Path, start_commit: str, patch_hash: str) -> dict: ...
```

For Config, AGENTS, Rules, Hooks, Sandbox, and Approval, emit the ADR-0002 shape with independent checks. A Sandbox check may be `enforced=pass/observed` only when a matching command item attempted the scoped harmless write and completed denied/failed under the recorded sandbox. Approval is `enforced=pass/observed` only when request, host decision, resolution, and terminal item result share thread/turn/item identity. A hook error remains Hook failure/unavailable and never proves enforcement.

- [ ] **Step 4: Connect to real M1 stores in temporary roots and reach GREEN.**

Assert Event sequence, Evidence redaction, Project/Worktree/Task/Environment closure, private file permissions, projection freshness, and Guarantee evaluation from the resulting canonical records.

- [ ] **Step 5: Commit Task 2.**

```bash
git add src/devharness/managed_tasks.py src/devharness/control_runtime.py tests/test_managed_tasks.py tests/test_control_runtime.py
git commit -m "M3: bind managed runtime control evidence"
```

### Task 3: Imported Task guarantee boundary

**Files:**
- Create: `src/devharness/imported_tasks.py`
- Create: `tests/test_imported_tasks.py`
- Create: `tests/fixtures/m3/imported-task.json`

**Interfaces:**
- Consumes an explicitly supplied synthetic repository snapshot, current diff, and directly executed current-test receipt.
- Produces an Imported Task packet and Task Guarantee Report without opening any Desktop task.

- [ ] **Step 1: Write failing behavior tests.**

```python
def test_imported_task_observes_only_current_diff_and_current_test():
    packet = import_task(FIXTURE, catalog)
    self.assertEqual("observed", packet["current_diff"]["basis"])
    self.assertEqual("not_run", packet["controls"]["sandbox"]["enforced"]["result"])

def test_imported_task_managed_only_claim_is_not_evaluated():
    report = import_task(FIXTURE, catalog)["guarantee_report"]
    self.assertEqual("not_evaluated", verdict(report, "managed-control-enforcement"))
```

Reject unspecified Desktop thread IDs, foreign identity, stale test commit, fabricated past approval/control evidence, duplicate references, and raw secret fields.

- [ ] **Step 2: Run the focused test and capture RED.**

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_imported_tasks -v
```

- [ ] **Step 3: Implement the minimal importer and reach GREEN.**

Do not invoke `codex`, App Server, task-management tools, or Desktop APIs from this path. Bind only the supplied current observations and mark all historical Managed-only control checks `not_run/unobserved`.

- [ ] **Step 4: Commit Task 3.**

```bash
git add src/devharness/imported_tasks.py tests/test_imported_tasks.py tests/fixtures/m3/imported-task.json
git commit -m "M3: preserve imported task guarantee limits"
```

### Task 4: Live runtime probe and review packet

**Files:**
- Create: `src/devharness/m3_review.py`
- Create: `tests/test_m3_review.py`
- Create: `docs/reviews/m3/run_live_probe.py`
- Create: `docs/reviews/m3/README.md`
- Create: `docs/product/managed-task-runtime.schema.json`
- Create: `docs/product/managed-task-runtime.example.json`
- Modify: `docs/product/Requirements_Traceability.md`
- Modify: `docs/adr/0001-codex-desktop-integration.md`
- Modify: `docs/adr/0002-control-validation-evidence-model.md`
- Modify: `docs/product/향후계획.md`

**Interfaces:**
- Consumes the Task 1–3 APIs and one disposable repository.
- Produces a strict sanitized review packet, local HTML summary, raw local Evidence directory, and exact runtime Gate result.

- [ ] **Step 1: Write a failing end-to-end fixture test.**

The fake transport version must prove orchestration and sanitization only. Assert that no raw prompt, command output, secret-like config value, external private path, or unmasked thread ID enters the committed packet. Assert exact Evidence links and state labels.

- [ ] **Step 2: Run the end-to-end test and capture RED.**

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest tests.test_m3_review -v
```

- [ ] **Step 3: Implement review orchestration and strict schema.**

The CLI requires explicit `--repository`, `--data-root`, `--output`, `--codex-bin`, `--model`, and `--timeout`. It refuses a repository without `.ownhands-disposable`, refuses a data root inside Git, and defaults to no live execution unless `--live` is explicitly present.

- [ ] **Step 4: Run one real App Server probe.**

Use `codex-cli 0.153.3`, the generated stable v2 protocol fingerprint, model `gpt-5.6-luna`, low reasoning effort, a fresh disposable Git fixture, and raw output under `/tmp`. The bounded probe must produce:

- one terminal Managed Task;
- a loaded instruction source receipt;
- one harmless command Hook lifecycle result or explicit unavailable/failure classification;
- one sandbox-denied write with matching command item;
- one approval request with predetermined decline, resolution, and terminal result, or a hard Gate failure when the stable route cannot produce it.

Never retry for a favorable outcome. A failed or interrupted run counts as the one live execution and is reported truthfully.

- [ ] **Step 5: Validate the sanitized packet against raw local Evidence.**

Recompute Event/Evidence references, protocol/version fingerprint, identity closure, sandbox attempt/result, approval chain, and restore receipt. The required runtime Gate fails if any chain is incomplete. Record human friction as Unobserved and link issue #38.

- [ ] **Step 6: Run milestone verification.**

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ownhands-m3-pycache PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m compileall -q src tests docs/reviews/m3
npm_config_cache=/tmp/ownhands-m3-npm-cache npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/managed-task-runtime.schema.json -d docs/product/managed-task-runtime.example.json
git diff --check
```

- [ ] **Step 7: Record exact evidence and commit.**

```bash
git add src/devharness/m3_review.py tests/test_m3_review.py docs/reviews/m3 docs/product/managed-task-runtime.schema.json docs/product/managed-task-runtime.example.json docs/product/Requirements_Traceability.md docs/adr/0001-codex-desktop-integration.md docs/adr/0002-control-validation-evidence-model.md docs/product/향후계획.md
git commit -m "M3: verify managed Codex runtime integration"
```

### Task 5: Bounded final Gate and integration

**Files:**
- Modify only files required by the single blocker-fix wave, if any.

- [ ] **Step 1: Run one final review limited to #32–#37 acceptance criteria and merge blockers.**

The reviewer must classify human friction as Unobserved/M6 #38, not as an M3 blocker. It may run targeted reproductions for concrete suspicions but no broad audit.

- [ ] **Step 2: If blockers exist, send all blockers to the same implementer in one fix wave.**

Create RED regressions, apply the minimal fix, and do not add scope.

- [ ] **Step 3: Run exactly one revalidation of fixed paths and affected required checks.**

If a required blocker remains, keep #32–#37 and the PR open, record M3 Blocked, and do not start M4.

- [ ] **Step 4: If the Gate passes, push, create one M3 PR, verify GitHub state/checks, merge, add Evidence to #32–#37, close them and the M3 Milestone, and update #7.**

Keep GitHub automatic checks separate from local verification. Do not claim automatic checks passed when none exist.

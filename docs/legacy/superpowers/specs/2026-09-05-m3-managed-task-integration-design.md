# M3 Codex Managed Task Integration Design

- **Status:** Approved for implementation by prior user delegation
- **Approval mechanism:** 사용자 사전 위임에 따른 에이전트 결정
- **Human review:** Not performed; human workflow friction remains Unobserved and is tracked by GitHub issue #38
- **Scope issues:** #32–#37

## Goal

Connect an M2 Task Execution Contract to a new, disposable Codex-managed task, capture stable App Server events and control evidence, and preserve the narrower guarantees of an Imported Task. The implementation must produce at least one observed `Enforced` control record from a real runtime probe without reading, resuming, steering, or mutating an existing Desktop task.

## Fixed boundaries

- Product name is **ownhands**. The existing Python import namespace `devharness` remains for compatibility.
- Only a newly created non-sensitive disposable Git repository may be used for runtime probes.
- Existing Desktop tasks, user projects, daemon sessions, private transcripts, and user/global configuration are not probe targets.
- Raw App Server messages and Evidence objects remain outside the repository. Shared receipts contain allowlisted fields, hashes, and redacted summaries only.
- Runtime `Loaded` and `Enforced` states are never inferred from file presence or generated configuration.
- Rules remain experimental and cannot be a required core guarantee.
- M3 preserves only a start commit, patch hash, and references plus a minimal restore check. Full restore belongs to M4.
- No M4 Assurance, M5 Dashboard, deployment, package publication, external API side effect, payment, or secret transmission is included.

## Integration decision

### Chosen: App Server over stdio JSON-RPC v2

Launch the installed `codex app-server --listen stdio://` as a child process for each ownhands-managed probe. Perform the `initialize`/`initialized` handshake, start a fresh thread, start one bounded turn, answer any server approval request with a predeclared fixture decision, and consume notifications until a terminal turn result or timeout.

This is the chosen path because ADR-0001 requires App Server for managed client events and approvals. The current official OpenAI documentation describes stdio as newline-delimited JSON, `thread/start` as creating and subscribing to a fresh thread, `instructionSources` as the loaded instruction paths, and approval requests as server-initiated JSON-RPC requests scoped by thread, turn, and item.

### Rejected: Codex SDK

The stable Python SDK is suitable for ownhands-owned automation and uses App Server internally, but its high-level run interface is not the smallest boundary for preserving raw approval and lifecycle event identity. Adding it would also add a production dependency that M3 does not need.

### Rejected: `codex exec --json`

Non-interactive JSONL is an official automation path and useful for CI, but it does not expose the same bidirectional approval client contract required by ADR-0001. It remains a possible future adapter, not the M3 managed-client path.

## Components

### `codex_app_server.py`

Owns process lifecycle and protocol validation. It accepts an explicit executable, supported version range, cwd, model, sandbox, approval policy, fixed prompt, timeout, and approval handler. It emits normalized response, notification, approval, and process-exit records. It rejects malformed JSON, duplicate response IDs, unknown required terminal states, cross-thread/turn/item approval messages, timeouts, and premature process exit.

The adapter never persists raw messages itself. A caller-provided sink receives redacted normalized records. All outbound request IDs are generated locally and all inbound identifiers are checked against the active run.

### `managed_tasks.py`

Validates the M2 handoff and starts a managed task only when:

- Baseline freshness is `fresh`;
- the Contract fingerprint and identity match the Task;
- the Contract gate is ready and its approval record is explicit, scoped, and unexpired;
- a start commit and patch fingerprint exist;
- the target is a marked disposable repository.

It registers Project, Worktree, and Task identities in the M1 store, maps App Server thread/turn/item identities into canonical Events, stores redacted Evidence, and emits a Control Validation packet. A minimal restore check proves only that the disposable worktree can return to its start commit and patch state.

### `control_runtime.py`

Produces independent `configured`, `loaded`, and `enforced` checks for:

- Config and trust: allowlisted resolved values plus config layer/origin metadata;
- AGENTS instructions: `thread/start.instructionSources`, exact scope, and source hashes;
- Rules: experimental match/decision/result, or explicit Unobserved when the stable path is unavailable;
- Hooks: synchronous `hook/started` and `hook/completed` outcomes, including failure, timeout, and unavailable;
- Sandbox: active sandbox plus a harmless denied filesystem write;
- Approval: request, host decision, resolution, and terminal item result with exact identity.

Unknown or unavailable data becomes `not_run/unobserved`; it never becomes a pass. Allowlisted configuration excludes credentials, tokens, MCP environment values, and arbitrary user/global values.

### Imported Task path

Imported input is an explicit synthetic snapshot containing current repository identity, current diff, and a directly executed test receipt. The importer does not open a Desktop task. Current observations may be recorded, but historical Config, AGENTS, Rules, Hooks, Sandbox, Approval, and pre-change tests remain `not_run/unobserved`. Managed-only Guarantee claims therefore evaluate to `not_evaluated`.

### M3 review packet

A deterministic JSON packet and local HTML summary show:

- Task mode and exact identities;
- App Server/Codex version and protocol schema fingerprint;
- Event and Evidence reference closure;
- configured/loaded/enforced checks and basis;
- runtime probe scope and terminal outcome;
- missing, failed, timeout, unavailable, and Unobserved paths;
- Imported limitations;
- the minimal start restore receipt.

The committed packet contains no raw transcript, secret value, private path outside the disposable fixture, or fabricated success. The actual raw runtime evidence remains in a temporary data root.

## Runtime probe design

Use one fresh disposable Git repository containing only synthetic files. Launch a standalone App Server process using installed Codex CLI `0.153.3`, stdio transport, a low-cost supported model, and explicit per-thread sandbox/approval parameters.

The managed turn performs bounded harmless actions:

1. Read a synthetic marker and report the current instruction scope.
2. Execute a harmless command so synchronous Hook lifecycle can be observed when supported.
3. Attempt one write that the selected sandbox must deny, producing the required Sandbox `Enforced/Observed` evidence.
4. Trigger one safe approval request and apply the predetermined decline decision. The decision proves transaction handling, not human approval or user testing.

If authentication, protocol support, Hook trust, model availability, or approval routing prevents valid runtime evidence, the probe records the exact failure and M3 remains blocked. Mock or fixture transport results cannot satisfy the runtime Gate.

## Failure semantics

- Missing event, timeout, malformed payload, unsupported version, identity mismatch, or incomplete terminal chain is a hard failure for the affected required path.
- A declined approval is a valid observed transaction only when request, exact host decision, server resolution, and terminal item outcome all link correctly.
- Hook failure or unavailability is an observed failure/unavailable state, not proof that the guarded action was blocked.
- A Sandbox control is `Enforced` only when the actual command attempted the scoped operation and the runtime denied it under the recorded sandbox.
- The adapter terminates only the child process it started and never restarts or controls the Desktop daemon.

## Test strategy

1. Protocol unit tests use a deterministic fake child transport and literal message fixtures. Each test names the malformed, reordered, cross-scope, timeout, or fail-open behavior it catches.
2. Store integration tests use the real M1 Catalog, EventLog, EvidenceStore, Projection, and Guarantee evaluator in a temporary data root.
3. Disposable repository tests use real Git commands only inside a temporary repository.
4. One live App Server probe supplies the required runtime Evidence. Its results are validated independently against the normalized packet and raw local receipt.
5. Full repository tests, strict schemas, compile checks, and diff checks run before the single bounded final Gate Review.

## Acceptance mapping

| Issue | Proving artifact |
|---|---|
| #32 Adapter | protocol tests, version/schema receipt, live App Server event chain |
| #33 Managed start | M2 handoff validation, Task/thread mapping, start restore receipt |
| #34 Config/AGENTS | config layer allowlist and `instructionSources` validation |
| #35 Rules/Hooks | safe rule state plus hook lifecycle/failure classification |
| #36 Sandbox/Approval | live Sandbox denial and linked approval transaction |
| #37 Imported | current diff/test receipt and Managed-only `not_evaluated` report |

## Remaining risk

- App Server and Hooks can evolve with the installed Codex version; the protocol fingerprint and support policy limit claims to the observed version.
- A single disposable task proves only the exact tested control paths, not every command, tool, network path, or user environment.
- Human Desktop workflow friction is Unobserved and moved to M6 issue #38.

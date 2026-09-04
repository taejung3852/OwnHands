# M0-02 — Codex Desktop integration paths

- Status: research spike; no production implementation decision is encoded here.
- Checked: 2026-09-04 (Asia/Seoul)
- Local evidence: Codex CLI `0.153.0`, bundled with ChatGPT Desktop, via read-only `--help` commands.
- Scope: official OpenAI documentation and the installed CLI's help only. No existing Desktop task, user/global config, private session transcript, or remote-control pairing was accessed.

## Decision-ready summary

Use **App Server as the only candidate managed-task adapter**. Its documented `thread/read`/`thread/list` route permits a non-subscribing, non-resuming **snapshot observer** of an existing stored thread; use polling and idempotent reconciliation for Imported Task review. A narrow, disposable, user-authorized proof is still required before claiming it works against a Desktop-created task on this host or before any live-event design. Use **Hooks plus project-local configuration/AGENTS.md** for lifecycle policy and local evidence only after their own M0-03 probes. Use **SDK only for separate, automation-owned tasks**, not as an attachment mechanism. Treat Rules as experimental and never make M0/M1 guarantees depend on them.

The decisive boundary is clear: the public protocol documents `thread/read` as reading a stored thread **without resuming or subscribing**, so it is a documented read-only snapshot mechanism. It does **not** document a passive, live event subscription/attachment to a task already actively operated in Codex Desktop. Therefore an existing Desktop task can be treated as an **Imported Task with snapshot/status evidence** when user-authorized, but live turn/approval capture and past policy enforcement remain Unobserved until a safe probe proves non-disruptive coexistence on the exact Desktop + CLI version. Do not replace the Desktop UX, issue a turn, steer, approve, interrupt, or resume a user task merely to test this.

## Evidence vocabulary used here

| Label | Meaning |
|---|---|
| Documented | Directly stated in an official OpenAI document or installed CLI help. |
| Locally observed | Direct output from the installed CLI on this machine; not a claim about an active Desktop task. |
| Unobserved | No permitted probe was run, or the source does not establish the behaviour. |

This preserves the product baseline distinction: configuration presence is not loading, loading is not enforcement, and observation is not control.

## Comparison of integration paths

| Path | What is documented | M0-02 value | Stability / limitation |
|---|---|---|---|
| App Server | JSON-RPC custom-client protocol for threads, approvals, streamed agent events, diffs, status, and instruction sources. `thread/read` reads without resuming or subscribing; `thread/resume` reopens an existing thread. | Best managed-task adapter; only documented route for approval request/result protocol events; snapshot observer for Imported Task review. | Core protocol has a stable surface; many thread-history and process operations require `experimentalApi`. Passive **live** attachment to an active Desktop task is **Unobserved**. |
| Codex SDK | Programmatically starts a thread then runs a prompt; OpenAI positions it for automation/CI. | Suitable for DevHarness-owned, non-Desktop automation or fixtures. | Not documented as a client for Desktop-owned threads, approvals, or a passive event tap. Do not use it for Desktop integration. |
| Hooks | Configured lifecycle handlers can observe/intercept supported local tool paths; `PreToolUse` can deny supported calls and `PermissionRequest` can decide an approval request. | Candidate for per-session tool evidence and narrow enforcement probes. | Coverage is explicitly incomplete (hosted tools and specialised paths can bypass). Hook errors/unsupported output can continue the tool call. Not a complete audit stream. |
| Config, AGENTS.md, Rules | Layered config precedence; `thread/start`/`resume` return instruction sources; AGENTS discovery hierarchy is documented; Rules restrict commands outside the sandbox. | Compile and validate baseline/overlay, instruction source, and guardrail configuration. | Project config is trusted-project only. AGENTS loading is session-start scoped. Rules are explicitly experimental and outside-sandbox only. |
| Logs / event observation | App Server emits turn, item, diff, status, approval, and resolution notifications to its connected client. AGENTS docs describe optional local TUI/session logs for instruction audit. | App Server is the structured event source; hooks' own durable handler output can supplement it. | Existing Desktop task event observation without resume is unproved. Transcript format is explicitly not stable for hooks. Log parsing must not be the canonical adapter. |

## Official findings

### 1. App Server

[App Server](https://developers.openai.com/codex/app-server) describes the custom-client protocol as responsible for authentication, conversation history, approvals, and streamed agent events. Its stable overview documents `thread/start`, `thread/resume`, `thread/read`, and `thread/list`; it also documents `turn/started`, `turn/completed`, `turn/diff/updated`, `thread/status/changed`, command/file-change approval requests, their decisions, and final item status.

Important boundary:

- `thread/read` reads stored data **without resuming or subscribing**.
- `thread/resume` reopens the thread; later turns append to it and its response contains loaded `instructionSources`.
- The document does not say that a second client can subscribe read-only to a thread that another client (Desktop) has already loaded and is actively using.

So the protocol supports historical/snapshot inspection of a known stored thread without subscribing (Documented) and a client-owned resumed thread (Documented). Snapshot inspection is the only documented non-invasive observation route; coexistence of a **live event subscriber** with the Desktop UX is Unobserved. Resuming might preserve the stored thread identity, but it is an interaction/lifecycle operation—not evidence of a non-invasive observer attachment.

The documentation explicitly gates some fields/methods behind `capabilities.experimentalApi`; relevant examples include `thread/turns/list`, `thread/items/list`, historical thread filters, background-terminal operations, process sessions, and dynamic tools. Keep M0/M1 on the stable method subset. Generate a protocol schema per installed CLI version only into a disposable directory during future probes; generated schemas match that exact version, but the generation command itself is marked experimental in CLI help.

### 2. SDK

[Codex SDK](https://developers.openai.com/codex/codex-sdk) shows `new Codex()`, `startThread()`, and `thread.run(prompt)`. It says to use the SDK to automate coding tasks including CI, while directing custom clients that need authentication, conversation history, approvals, and streamed agent events to App Server. This is direct evidence that SDK is the automation route, not the Desktop-task observation route.

Recommendation: SDK tasks are DevHarness-created tasks with separate task identity. They can produce useful fixture/evidence flows, but must not be represented as continuation, attachment, or comprehensive capture of a Desktop task.

### 3. Hooks

[Hooks](https://developers.openai.com/codex/hooks) documents `PreToolUse`, `PostToolUse`, `PermissionRequest`, Session lifecycle and other events. For supported local tool calls, `PreToolUse` can deny or rewrite before execution; `PostToolUse` runs after the result and cannot undo side effects. `PermissionRequest` can allow, deny, or leave the ordinary approval prompt in place; any matching deny wins.

The same document limits the claim: hosted tools do not use the local function-tool hook path, specialised paths may opt out, and it calls tool hooks a useful guardrail rather than a complete enforcement boundary. It also says the transcript path is a convenience only and its format is not stable. A hook failure is not automatically a fail-closed control: unsupported fields are reported as hook failure while Codex continues the tool call in documented cases.

Recommendation: record hook handler invocation/result in DevHarness-owned evidence; mark coverage outside supported tool paths `Unobserved`. Do not derive "all actions observed" or "all risky actions controlled" from hooks.

### 4. Config, Rules, and AGENTS.md

[Config basics](https://developers.openai.com/codex/config-basic) documents precedence: CLI/config overrides, trusted project `.codex/config.toml` layers from project root to CWD (closest wins), profile, user, system, defaults. This makes the resolved effective config a necessary M0-03 evidence target, not merely a file diff.

[AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md) documents global and root-to-CWD instruction discovery, with `AGENTS.override.md` taking precedence per directory. It also provides two documented audit routes: a plaintext TUI log enabled with `codex -c log_dir=...`, or a session JSONL only if session logging was enabled. App Server `thread/start` and `thread/resume` return `instructionSources`. These are documented ways to establish instruction loading for a DevHarness-managed start/resume; they do not prove an arbitrary pre-existing Desktop session's active instruction chain.

[Rules](https://developers.openai.com/codex/rules) says Rules control commands Codex can run **outside the sandbox** and explicitly labels the feature experimental and subject to change. Rules may be an optional defence-in-depth experiment, never the sole enforcement proof or a stable contract dependency.

### 5. Approval, sandbox, and event observation

[Agent approvals & security](https://developers.openai.com/codex/agent-approvals-security) is the policy reference. The App Server protocol supplies the observable transaction boundary for command/file-change approvals: request, client decision, `serverRequest/resolved`, and a completed/failed/declined item. This is strong evidence only for a task whose App Server client actually receives those notifications.

For an existing Desktop task, neither the docs nor the local read-only probes performed here establish that an external client receives its live approval events or can observe the decision/result without becoming the controlling client. Mark each of approval request, decision, and result **Unobserved** for that scenario.

## Explicit answers to the six M0-02 questions

| Question | Answer | Evidence state and boundary |
|---|---|---|
| 1. Can Desktop thread/turn events be accessed? | App Server `thread/read` can read stored thread/turn snapshot data without subscribing; streamed events are documented for threads the client starts/resumes. | **Documented** snapshot/history observer (when a known stored task is explicitly in scope); **Unobserved** for passive live event observation of an already-running Desktop task. |
| 2. Can approval request and result be observed? | App Server documents request → decision → resolution → terminal item sequence. | **Documented** where the App Server client owns/receives the stream; **Unobserved** for an external observer of a Desktop-owned task. |
| 3. Can Hook started/completed be confirmed? | Hooks can receive lifecycle/tool events and a DevHarness-owned handler can record its own start/end/result. | **Documented** hook execution interface; **Observed only after a local handler log or supported event evidence**. No documented universal App Server `hook.started/completed` notification was found; passive Desktop confirmation is **Unobserved**. |
| 4. Can active config source be confirmed? | Config precedence is documented. App Server start/resume returns `instructionSources`; AGENTS docs offer optional local logs. | **Documented** for managed start/resume instruction sources; resolved active config source and pre-existing Desktop task config are **Unobserved** until M0-03 probe evidence. |
| 5. Can existing Desktop UX be retained? | `thread/read` is explicitly non-subscribing/non-resuming, so it is the documented snapshot route least likely to affect UX; no official source promises passive **live** attachment while Desktop remains active. | **Documented for non-subscribing snapshot reads; Unobserved / blocker for live Managed Desktop integration.** Do not claim live compatibility or attempt it on a live user task. |
| 6. Which scope relies on experimental features? | Rules are experimental. App Server experimental API includes turn/item pagination and other methods; CLI labels `app-server`, remote control, and schema generation experimental. | Stable baseline: ordinary App Server start/resume/read/list/events and Hooks/config/AGENTS as documented. Experimental features may be isolated behind capability/version checks and cannot be required for core guarantees. |

## Local read-only probe results

| Probe | Result | Classification |
|---|---|---|
| `codex --version` | `codex-cli 0.153.0` from `/Applications/ChatGPT.app/Contents/Resources/codex`. | Locally observed. |
| `codex --help` | CLI exposes `app-server [experimental]`, `remote-control [experimental]`, and `agents` for shared local app-server daemon sessions. | Locally observed; command availability is not attach capability. |
| `codex app-server --help` | Supports an App Server process/proxy/schema tools. | Locally observed. |
| `codex app-server daemon --help` | Starting/stopping, bootstrap, and enabling remote control are mutating options; none were run. | Locally observed availability only. |
| `codex agents --help` | Described as browsing agent sessions on a shared local daemon; it was not run because that could expose private existing tasks. | Locally observed help; no session data accessed. |

No live thread, approval, hook, config, or log probe was run. This is intentional: doing so without a dedicated disposable task could alter UX or inspect private task data.

## Required minimal probe plan (before implementation / ADR)

Run these only in a disposable repository and a newly created, explicitly consented Desktop task. Keep raw output in an ignored local evidence location, not Git.

1. Record Desktop build/CLI version, project trust state, CWD, effective config candidate files, and a harmless task marker.
2. With a **second App Server client**, call only the documented `thread/read`/list/status methods against the disposable task. Do not resume, start a turn, steer, interrupt, approve, archive, or modify metadata. Compare Desktop UX/state before and after. Success criterion: documented, non-subscribing snapshot reads expose the target and do not change the task UX. This is only historical/status observation, not a subscription proof.
3. If the protocol exposes no documented subscription method, stop. Record `Unobserved`; do not try an undocumented socket, session-file tail, remote-control pairing, or reverse-engineered Desktop endpoint.
4. In a separately created App-Server-managed task, capture stable `turn/*`, `item/*`, diff, status, and approval request/result events. This validates the adapter's managed path, not Desktop attachment.
5. In a second disposable task with project-local config, use harmless hooks to append a marker to an ignored temporary evidence file. Verify `PreToolUse`/`PostToolUse` ordering and a safe denied no-op. Test failure/timeout behaviour independently, then label all unsupported/hosted paths Unobserved.
6. Validate AGENTS instruction loading using a fresh managed start/resume and returned `instructionSources`; validate config resolution only where an official observable output or a safe, version-pinned local method exists. File presence alone stays Configured.

### Explicitly prohibited probes

- Attaching to, reading, resuming, steering, approving, interrupting, archiving, or changing metadata for an existing personal/work Desktop task.
- Enabling remote control, pairing, starting/restarting the user daemon, or editing user/global Codex configuration.
- Testing a block by performing destructive, networked, secret-bearing, paid, or externally visible work.
- Treating session JSONL/transcripts or internal Desktop files as a stable integration API.

## Alternatives and recommendation

| Alternative | Benefits | Rejection / constraint |
|---|---|---|
| App Server managed task from DevHarness | Official structured event and approval protocol; instruction sources; preserves core evidence model. | Requires a new DevHarness-managed task and an M0 proof of how it coexists with Desktop. |
| SDK-owned task | Small automation API, useful for CI/fixture runs. | Separate task lifecycle; no documented Desktop attachment, streaming approval handling, or UX preservation. |
| Hooks + project config only | Native policy/lifecycle integration; no client takeover needed. | Partial tool coverage and no complete turn/approval/dashboard event stream. Complement only. |
| Parse logs/transcripts/files | May support post-hoc local forensics. | Formats and completeness are not stable; cannot be canonical or enforcement evidence. Use only optional Imported Task evidence with explicit provenance. |
| Passive snapshot observer of an active Desktop task | `thread/read` is documented as non-subscribing/non-resuming; supports Imported Task history/status snapshots. | Requires explicit user scope and safe compatibility probe; no live stream, approval capture, or past-control evidence. |
| Passive live external attachment to active Desktop task | Would preserve the familiar UX while capturing events. | No official documented capability found. Not an implementation choice until a safe proof exists. |

**Recommendation:** Implement two explicit modes: (1) an App-Server-managed task started after DevHarness preflight, which records structured events into the local canonical event log; and (2) an Imported Desktop Task observer that uses only authorized App Server snapshot/status reads and marks live events, approvals, and historical policy enforcement Unobserved. Retain Desktop-first managed intent only if a future approved probe demonstrates non-disruptive live coexistence. Hooks/config/AGENTS are complementary validation sources. Rules remain optional experimental defence-in-depth.

## Remaining risks and gates

1. **Desktop attach risk (Hard evidence gate):** No passive attach proof exists. M3 must not claim "Desktop Managed Task" until it does.
2. **Client ownership / approvals:** An App Server client receiving an approval request may be expected to decide it; this can change the user interaction path. Test only in a disposable task.
3. **Version drift:** App Server protocol schemas and feature maturity can change. Persist exact CLI/Desktop versions and capability set with every probe/result.
4. **Coverage gap:** Hooks omit hosted tools and some specialised paths; represent these as Unobserved rather than success.
5. **Trust / precedence:** Project-local config is trusted-project-only and closest-CWD configuration wins. Resolve source-by-source, do not overwrite existing config.
6. **Privacy:** Thread histories, transcript paths, and logs can contain user content/secrets. Keep raw data local and ignored; store only redacted derived evidence when justified.
7. **Experimental dependency:** Rules and experimental App Server methods must have a capability check, a stable fallback, and wording that never upgrades them to a broad guarantee.

## Source register

- [Codex App Server — official OpenAI documentation](https://developers.openai.com/codex/app-server) (thread lifecycle, notification stream, approvals, instruction sources, experimental capability).
- [Codex SDK — official OpenAI documentation](https://developers.openai.com/codex/codex-sdk) (automation/CI positioning and API shape).
- [Codex Hooks — official OpenAI documentation](https://developers.openai.com/codex/hooks) (events, enforcement, coverage, limitations, transcript stability).
- [Codex config basics — official OpenAI documentation](https://developers.openai.com/codex/config-basic) (configuration precedence and trusted project layers).
- [AGENTS.md — official OpenAI documentation](https://developers.openai.com/codex/agent-configuration/agents-md) (discovery order and documented audit routes).
- [Codex Rules — official OpenAI documentation](https://developers.openai.com/codex/rules) (outside-sandbox scope and experimental status).
- [Agent approvals & security — official OpenAI documentation](https://developers.openai.com/codex/agent-approvals-security) (approval/security policy reference).
- Installed Codex CLI `0.153.0`: `codex --help`, `codex app-server --help`, `codex app-server daemon --help`, `codex agents --help`, `codex remote-control --help`, `codex app-server generate-json-schema --help`; read-only local probe output, 2026-09-04.

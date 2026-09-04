# M0-03 — Control Validation Coverage

**Status:** ADR evidence, not a claim that every control is active here.

**Observed:** 2026-09-04 · macOS · Codex CLI `0.153.0` · DevHarness repository.

**Evidence hygiene:** raw logs, resolved private configuration, tokens, and hook output stay outside Git.

## Decision framing

DevHarness must answer two independent questions:

1. **Control realization:** was the control configured, loaded into this run, and demonstrated to enforce its boundary?
2. **Evidence basis:** is that conclusion directly observed, inferred from another result, or unobserved on this integration path?

Do not use one `control_state` enum. It would make `Enforced` and `Inferred` mutually exclusive even though they describe different dimensions. Config precedence also makes this distinction material: CLI overrides outrank trusted project layers, profiles, user config, system config, and defaults; untrusted projects skip project-local config, hooks, and rules ([Config basics](https://learn.chatgpt.com/docs/config-file/config-basic)).

## Schema alternatives for ADR review

| Option | Shape | Benefit | Cost / risk |
|---|---|---|---|
| A. Independent axes | `realization: { configured, loaded, enforced }`; `basis: observed \| inferred \| unobserved`; evidence references per check | Directly represents the product model; no false promotion | More fields and UI rules |
| B. Evidence records only | Append records with assertion, outcome, basis, scope, and evidence | Strongest audit trail | Requires projection/aggregation rules |
| C. Claim checklist + basis | Three nullable/tri-state checks plus one basis field per claim | Straightforward Guarantee Matrix rendering | Less reusable where one probe supports many claims |
| D. Single enum | One value chosen from all six words | Small | Collapses two dimensions; reject |

**Recommendation:** adopt A as the report/read model, backed by B as the append-only source model. Each realization check should be `pass | fail | not_run | not_applicable`; it must not be implicitly promoted. `basis` describes how a conclusion was obtained, not a degree of success. `Unobserved` must be explicit rather than a default success.

```json
{
  "control": "rules.command-prefix",
  "realization": {"configured": "pass", "loaded": "pass", "enforced": "pass"},
  "basis": "observed",
  "evidence_refs": ["ev_01", "ev_02"],
  "scope": {"command_pattern": ["tool", "safe-subcommand"]},
  "residual_risk": ["non-matching and bypass paths"]
}
```

This is an illustrative record, not a final schema.

최종 M0 schema는 여기에 instance `control_id`와 별도로 Matrix selector용 `control_type`을 두고, `project_id`·`worktree_id`·`task_id`·`environment_ref`를 필수 scope로 둔다. Guarantee gate는 같은 selector와 scope의 canonical record 전체를 평가하므로 Report가 다른 Task의 pass를 가져오거나 관련 failed record를 생략할 수 없다. Canonical store 조회 구현 자체는 M1 이후 runtime Gate이며 현재 **Unobserved**다.

## Coverage and validation plan

`Configured` means parseable compiled intent. `Loaded` requires a run-specific source/value/instruction/tool record. `Enforced` requires a harmless behavior with the predicted allow/prompt/deny outcome. `Observed` fits visible execution that imposed no boundary; `Inferred` must name its supporting observation; `Unobserved` means no safe available collection path.

| Control | Configured | Loaded | Enforced / observed probe | Fail-open or limit |
|---|---|---|---|---|
| Config loading | TOML parse, hash, intended source | Fresh-run active source + resolved value | Loading is not a boundary; `Enforced` N/A | Project trust can skip a layer; value ≠ behavior |
| AGENTS source | Non-empty file and scope inventory | Instruction-chain/log or disposable `codex debug prompt-input` | Observe supply only; never claim model compliance | Global override and nearer files can change chain |
| Rules | Parse `.rules`; validate match/not-match fixtures | Active source in trusted project | Synthetic harmless `forbidden` prefix is blocked; test `prompt` only with no side effect | Experimental exact-prefix controls do not cover alternatives |
| Hooks | Parse source and handler reference | Active source + trust review state | App Server `hook/started`/`hook/completed` receipt for synchronous hooks plus handler result; bounded synthetic timeout/non-zero separately | Async hooks have no matching completion notification; concurrency and non-hook tool paths remain outside the claim |
| Sandbox filesystem | Mode and writable roots | Run sandbox metadata | Benign outside-root deny plus inside-root allowed operation | Additional roots/full access and non-command tools |
| Sandbox network | Network/proxy/destination policy | Run policy metadata | Denied non-production endpoint, or allowlisted controlled endpoint only | Network-on/proxy-off is unrestricted outbound |
| Approval policy | Effective policy and app/MCP modes | Client/App Server metadata | Harmless request → decline/allow → terminal result | `never` has no request; absence proves nothing |
| Precedence and trust | Inventory candidate values/layers | Resolved value/source and trust state | Disposable nested project/profile/CLI conflict | Managed or hidden sources can remain unknown |
| MCP / plugin discovery | Entry/manifest parse | `codex mcp list`, plugin list, session inventory | list-tools/health/read-only harmless call | Configured does not imply connected, authenticated, or correct |
| Skill discovery | `SKILL.md` syntax/path | Model-visible list and selected-skill load evidence | Observe selection/full load only | Initial list can be shortened or incomplete |
| Test command | Declared command/cwd/inputs/side-effect boundary | Launch metadata and environment fingerprint | Project-owned fixture/local test; exit/result summary | Pass proves the declared selection only |
| Unobserved paths | Capability map | Adapter/version inventory | Record missing path or unsafe probe as negative evidence | External, hosted, historical, and plugin-internal paths remain possible |

The official behavior supports these constraints. Codex builds AGENTS guidance from global and root-to-CWD sources, with later (nearer) text overriding earlier text; it documents a TUI/session-log audit route ([AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)). Rules offer `allow`, `prompt`, and `forbidden`, selecting the most restrictive match, but are experimental ([Rules](https://learn.chatgpt.com/docs/agent-configuration/rules)).

Hooks run scripts or MCP tools in the lifecycle; matching command hooks run concurrently, non-managed hooks need trust review, hosted tools do not use the local hook path, and specialized paths can opt out ([Hooks](https://learn.chatgpt.com/docs/hooks)). App Server documents `hook/started` and `hook/completed` for synchronous lifecycle hooks only ([App Server](https://developers.openai.com/codex/app-server)). An MCP hook blocks only when it receives a blocking decision; error, missing-server, and unavailable-tool cases do not block. Hook timeouts are seconds and usually default to 600 seconds ([Hooks execution](https://learn.chatgpt.com/docs/hooks)).

Sandboxing supplies the technical filesystem/network boundary while approval determines when Codex pauses ([Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security)). In workspace-write mode, `.git`, `.agents`, and `.codex` remain protected. Network is normally off; if it is enabled without `network_proxy`, outbound traffic is direct and unrestricted, while the proxy constrains traffic only when enabled ([network controls](https://learn.chatgpt.com/docs/agent-approvals-security)).

For Managed Tasks, App Server is the preferred observation source: it streams thread/turn/item/request-resolution events and documents request → decision → final approval outcomes, including `declined` ([App Server events](https://learn.chatgpt.com/docs/app-server), [App Server approvals](https://learn.chatgpt.com/docs/app-server)). CLI output is a fallback, not proof of Desktop-wide observation.

## Safe and forbidden probe matrix

| Area | Safe for M0 | Forbidden |
|---|---|---|
| Files/config | Read repository files; parse copied/disposable config; create only task-owned disposable files outside Git | Change global/user/system config, overwrite project controls, inspect protected private data |
| Rules/approvals | Synthetic marker command or declined reversible permission request | Test blocks by performing destructive, deploy, money, messaging, credential, or data action |
| Hooks | Handler writes only to OS temp; bounded synthetic error/timeout | Attach global hooks, execute downloaded scripts, or rely on failure to protect real data |
| Sandbox/network | Temp/non-sensitive path and controlled non-production endpoint | Contact production/private/credentialed services or bypass sandbox/approvals |
| MCP/plugins | Read-only discovery and known harmless health/list capability | Install/update/remove, OAuth login, add/remove server, or invoke write/destructive tool |
| Tests | Declared project test against fixtures/isolated state | Migration, deployment, live integration, cleanup, or opaque side-effecting command |

Record: Codex/App Server version, OS, execution surface, project trust, worktree/commit, config-source paths (redacted if needed), probe scope, expected/actual result, timestamp, basis, raw-evidence location outside Git, and residual risk.

## Fail-open and fail-closed findings

| Situation | Finding |
|---|---|
| Untrusted project | Project-local config, hooks, and rules are skipped; fail-open relative to a project-local contract unless the Managed Task launcher refuses to start. |
| Matching `forbidden` rule | Fail-closed only for the exact matched prefix. |
| Rule miss or disabled Rules | Unobserved for alternative paths; never generalize a successful probe. |
| MCP hook error/missing/unavailable tool | Explicit fail-open; emit degraded-control evidence and Gate consequence. |
| Command-hook timeout/non-zero | Version-specific probe required; configuration alone cannot label it fail-closed. |
| PostToolUse block | Prevention is too late because the original tool may have run. |
| Declined approval | Fail-closed for the observed request; capture final `declined` item. |
| `approval_policy = "never"` | Intentionally open approval path; sandbox may still constrain execution. |
| Network enabled, proxy off | Fail-open relative to a domain-restriction claim. |
| Auto-review parse/prompt/review failure | Officially does not run; reviewer timeouts surface separately ([Agent approvals](https://learn.chatgpt.com/docs/agent-approvals-security)). |

## Version and environment notes

- Official local binary: `/Applications/ChatGPT.app/Contents/Resources/codex`; observed version `codex-cli 0.153.0`. Its help exposes `mcp list`, `plugin list`, `features list`, `debug prompt-input`, `sandbox`, and experimental `app-server`.
- The [M0-02/03 capability probe](probes/m0-02-03-codex-capability-probe.sh) completed a disposable stdio `initialize` handshake and generated the installed CLI's default protocol schema in a temporary directory. It found `thread/read`, approval request/resolution, `instructionSources`, `hook/started`, and `hook/completed`. This observes App Server availability and schema shape only; the generator is experimental and no handler, control, or live-task behavior was invoked.
- This build's `codex sandbox --help` accepts a command directly and supports supplied sandbox-state JSON, readable roots, and network-disable. Current public docs show platform subcommands in examples. Treat this as a version/interface compatibility check and preserve exact help only in local raw evidence.
- `codex mcp list` lists configured servers, not connected or behaviorally verified servers ([MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)).
- Skills are progressively disclosed: the initial list can abbreviate or omit entries, then Codex reads a selected `SKILL.md` in full ([Build skills](https://learn.chatgpt.com/docs/build-skills)).
- No DevHarness enforcement probe was performed during this research-only spike. All current repository-specific enforcement results remain `Unobserved`; command and schema availability are Observed but are not enforcement.

## ADR conditions

Proceed with the independent-axis approach only with:

1. Per-check evidence references, scope, version/environment, and timestamp.
2. Distinct `not_run`, `failed`, `not_applicable`, and `unobserved` values.
3. A Managed-Task refusal when trust or active-source observation is absent for a project-local claim.
4. A degraded-control event plus Gate rule for unavailable/erroring MCP hooks.
5. Claims bounded to an exact command, path, event, tool, and network destination.
6. Imported Tasks defaulting historical config, hook, approval, sandbox, and pre-change-test claims to `Unobserved`.

## Unobserved items to carry forward

1. A supported stable Desktop route for active config source and full instruction-chain capture.
2. Command-hook timeout/non-zero behavior for each lifecycle event in this installed version.
3. Receipt of documented synchronous hook start/completion notifications from a DevHarness-managed task, and any Desktop-owned task observation path; async hook completion remains outside that notification contract.
4. Hosted and specialized tool paths that bypass local PreToolUse/PostToolUse hooks.
5. Enumeration of all managed/admin configuration layers without reading protected configuration.
6. Sandbox coverage for GUI, MCP, plugin, or external-process side effects.
7. DNS/proxy edge behavior in the installed Desktop runtime; DNS classification is documented as best effort.
8. Third-party plugin dependency readiness, remote MCP auth freshness, schemas, and result correctness.
9. Historical behavior before a task becomes Managed: approvals, hooks, policy, external effects, and pre-change tests.
10. A safe, deterministic project test command suitable for later M3/M4 control validation.

DevHarness may therefore say, for example, “this exact trusted-session rule denied this synthetic prefix” or “this App Server approval was declined.” It must not say that all commands, all tools, all instructions, or the entire system are controlled.

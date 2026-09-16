# Research: `using-superpowers` Root Routing Architecture & Its Application to OwnHands

**Document Path:** `docs/research/using-superpowers-routing-pattern.md`  
**Author:** DevHarness Research Subagent  
**Date:** 2026-09-06  
**Status:** Approved for Architectural Implementation (M4.5 / Issue #63)

---

## 1. Executive Summary

Autonomous coding agents (such as Claude Code, OpenAI Codex, Antigravity, Gemini CLI, Hermes, and Pi) possess an intrinsic behavioral bias toward immediate action: when presented with a request, models reflexively attempt to answer questions, explore files ad-hoc, or modify code directly without planning or systematic verification.

The **Superpowers** plugin solves this fundamental failure mode not by adding another domain tool, but by introducing a **Root Router Pattern** centered on `using-superpowers`. This skill acts as a cognitive choke-point that intercepts conversation initiation, breaks rationalization loops, establishes strict priority rules (process before implementation), and routes intent into specialized, gate-controlled sub-skills (`brainstorming`, `systematic-debugging`, `test-driven-development`, and `verification-before-completion`).

For **DevHarness / OwnHands**, adopting this pattern is vital. Under **ADR-0010**, DevHarness enforces a strict **4-tier separation** (Router Skill → Sub-Skills → MCP Gateway → Core Engine) and an **Option C Hybrid Contract** (`domain.action`, 4-state decisions: `pass`, `soft_block`, `hard_block`, `unobserved`, and conditional CAS evidence persistence). By structuring `using-ownhands` as the root router and deploying specialized sub-skills (`context-validation`, `harness-profiler`, `execution-control`, `test-assurance`), OwnHands can eliminate un-linted context, un-profiled sandboxes, destructive shell executions, and unverified regression claims.

---

## 2. Core Mechanisms of `using-superpowers`

### 2.1 Multi-Harness Bootstrap & Discovery Ecosystem

A core revelation from inspecting `/Users/parktaejung/.gemini/config/plugins/superpowers/` is that **skills do not rely purely on LLM memory or passive tool catalogs**. As stated in `AGENTS.md`:

> *"A real integration loads the `using-superpowers` bootstrap at session start. The bootstrap is what causes skills to auto-trigger at the right moments. Without it, the skills are dead weight — present on disk but never invoked."*

Superpowers implements active bootstrapping across six runtime environments:

```text
                  ┌─────────────────────────────────────────────────────────┐
                  │                 Harness Initializers                    │
                  └─────────────────────────────────────────────────────────┘
                   /            |             |              |            \
                  /             |             |              |             \
          Claude Code         Cursor      Gemini CLI       Hermes          Pi
         (hooks.json)   (hooks-cursor.json) (GEMINI.md)  (__init__.py)  (superpowers.ts)
               │                │             │              │             │
        SessionStart      sessionStart   @include       pre_llm_call    context event
         run-hook.cmd     run-hook.cmd    import       first_turn hook  message inject
               \                |             |              |             /
                \               |             |              |            /
                 ▼              ▼             ▼              ▼           ▼
        ┌───────────────────────────────────────────────────────────────────┐
        │  Bootstrap Context Injection (<EXTREMELY_IMPORTANT> Wrapper)     │
        │  - Injects raw SKILL.md of `using-superpowers`                    │
        │  - Appends harness-specific tool mapping (e.g. references/*)      │
        └───────────────────────────────────────────────────────────────────┘
```

1. **Claude Code (`hooks.json` & `hooks/session-start`):**
   - Configures a `SessionStart` hook matching `startup|clear|compact`.
   - Executes `hooks/session-start`, which reads `skills/using-superpowers/SKILL.md`, escapes it, wraps it inside `<EXTREMELY_IMPORTANT> You have superpowers ... </EXTREMELY_IMPORTANT>`, and emits JSON via `hookSpecificOutput.additionalContext`.
2. **Cursor (`hooks/hooks-cursor.json`):**
   - Runs `hooks/run-hook.cmd session-start` on `sessionStart`, outputting snake_case `additional_context`.
3. **Gemini CLI (`gemini-extension.json` & `GEMINI.md`):**
   - `gemini-extension.json` designates `contextFileName: "GEMINI.md"`.
   - `GEMINI.md` uses native inclusion directives:
     ```markdown
     @./skills/using-superpowers/SKILL.md
     @./skills/using-superpowers/references/gemini-tools.md
     ```
4. **Hermes Agent (`.hermes-plugin/__init__.py`):**
   - Registers every skill with `ctx.register_skill(name, Path(skill_md))`.
   - Binds to `pre_llm_call`: when `is_first_turn` is true, dynamically returns `{"context": bootstrap}` to prepend the router into the prompt.
5. **Pi Coding Agent (`.pi/extensions/superpowers.ts`):**
   - Intercepts `context` events, verifies absence of `BOOTSTRAP_MARKER`, and inserts the bootstrap user message after any compaction summary.
6. **Antigravity CLI (`agy`):**
   - Injects the available skill catalog into the system instructions with description-based routing prompts.

### 2.2 Activation Triggers & Description Engineering

The YAML frontmatter of `using-superpowers` is engineered specifically to trigger semantic routing whenever a user opens a conversation:

```yaml
---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
---
```

Key features:
- **"Use when starting any conversation"**: Matches the initial intent state of turn 0.
- **"before ANY response including clarifying questions"**: Disables the agent's reflex to immediately ask clarifying questions or read random files before loading procedural guidelines.
- **Acceptance Test**: Verified via the standard test prompt: `Let's make a react todo list`. A functioning installation will invoke `brainstorming` before generating code.

### 2.3 Hard Guardrails

`using-superpowers` deploys two explicit XML semantic barriers:

#### A. `<SUBAGENT-STOP>` (Preventing Recursive Loops)
```markdown
<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>
```
*Why this is critical:* When a primary controller spawns a worker agent (e.g. for testing, code review, or research), the subagent receives task instructions in its prompt. Without `<SUBAGENT-STOP>`, the subagent would evaluate `using-superpowers`, attempt to re-brainstorm or establish plan modes, and freeze or thrash instead of completing its assigned leaf-node task.

#### B. `<EXTREMELY-IMPORTANT>` (Cognitive Override)
```markdown
<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>
```
*Why this is critical:* LLMs suffer from "sycophancy" and "action-bias," frequently judging their own capabilities as sufficient to solve a problem without structured procedures. The 1% threshold mathematically lowers the decision boundary to force invocation.

### 2.4 The Rule & Priority Taxonomy (Process vs. Implementation)

`using-superpowers` establishes an unambiguous priority hierarchy:
1. **The Rule:** Invoke relevant skills **BEFORE** any response or action (exploring code, checking files, asking questions). Announce `"Using [skill] to [purpose]"` and follow it sequentially.
2. **Process Skills Over Implementation Skills:**
   - **Process Skills** (`brainstorming`, `systematic-debugging`, `writing-plans`) establish *how* to approach the problem, frame scope, and guard boundaries.
   - **Implementation Skills** (`frontend-design`, `test-driven-development`, `mcp-builder`) carry out specific technical actions within an approved plan.
   - *Example:* "Let's build X" → Invoke `brainstorming` first. Never jump directly to `frontend-design` or code synthesis.
   - *Example:* "Fix this bug" → Invoke `systematic-debugging` first. Never jump directly to editing files.

### 2.5 Cognitive Anti-Rationalization: The Red Flags Engine

Superpowers identifies that agents rationalize process evasion using predictable inner monologue patterns. The Red Flags table functions as a cognitive pattern-matching interceptor:

| Rationalization Thought | Operational Reality |
|---|---|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

### 2.6 Inter-Skill Lifecycle Routing State Machine

Sub-skills in Superpowers do not operate as isolated silos; they form a tightly coupled, closed-loop state machine where exit conditions hand off strictly to subsequent skills:

- **Handoff from `brainstorming`:**
  - *Spike Path:* Concludes with a reported recommendation (throwaway code).
  - *Bounded Path:* In-chat design → Explicit human approval → Direct transition to normal workflow (`test-driven-development`).
  - *Architectural Path:* Design doc (`docs/superpowers/specs/YYYY-MM-DD-*.md`) → Self-review → Human review gate → **Exclusive handoff to `writing-plans`**.
- **Handoff from `systematic-debugging`:**
  - In Phase 4, mandates calling `test-driven-development` to write a failing reproduction test before fixing code.
  - Mandates calling `verification-before-completion` before claiming the bug is resolved.
  - **Circuit Breaker:** If 3+ fix attempts fail, systematic debugging halts and forces an architectural rethink with the human partner.
- **Handoff to `verification-before-completion`:**
  - Iron Law: *"No completion claims without fresh verification evidence."*
  - Prohibits claiming tests pass or features work based on previous runs or assumptions.

### 2.7 Host Platform Adaptation Layer

Superpowers decouples procedural intent from vendor-specific tool calls through reference files (`references/<harness>-tools.md`):

| Abstract Action | Antigravity CLI (`agy`) | Codex | Gemini CLI | Hermes Agent | Pi |
|---|---|---|---|---|---|
| **Dispatch Subagent** | `invoke_subagent` (`TypeName: "self" \| "research"`) | `spawn_agent {fork_turns: "none"}` | `invoke_agent(agent_name="generalist")` | `delegate_task(role="leaf")` | `subagent` (from `pi-subagents`) or inline |
| **Track Tasks / Todo** | Task Artifact (`write_to_file` + `IsArtifact: true`, `ArtifactType: "task"`) | Plan file / markdown checklists | `write_todos` | `todo` tool | Markdown plan / `TODO.md` |
| **Run Shell** | Native execution tool | Shell container / sandbox | `run_shell_command` | `terminal` | `bash` |
| **Inspect Files** | `view_file` | `read_file` | `read_file` / `read_many_files` | `read_file` | `read` |

---

## 3. Mapping Superpowers Patterns to OwnHands

### 3.1 Alignment with ADR-0010: The 4-Tier Separation

Superpowers operates primarily across 2 tiers: skills provide procedural text, and the agent translates text into host shell/editor calls.

In contrast, **DevHarness / OwnHands** enforces a strict **4-tier architecture (ADR-0010)** to guarantee determinism, auditability, and safety:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Router Skill (`using-ownhands`)                                │
│ - Intent classification, cognitive anti-rationalization, phase gating │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ delegates
┌───────────────────────────────────▼────────────────────────────────────┐
│ Tier 2: Sub-Skills                                                     │
│ - `context-validation`, `harness-profiler`,                            │
│   `execution-control`, `test-assurance`                                │
│ - Heuristics, methodology (ISTQB), evaluation of Option C envelopes   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ invokes stdio JSON-RPC
┌───────────────────────────────────▼────────────────────────────────────┐
│ Tier 3: MCP Tools Gateway (`ownhands-mcp-server`)                      │
│ - Option C Contract: domain.action                                     │
│ - Envelopes: status, decision, evidence_id, data, error               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ executes core logic
┌───────────────────────────────────▼────────────────────────────────────┐
│ Tier 4: Core Engine (`devharness` stdlib-only)                         │
│ - SQLite Catalog Schema v3, Append-only Event Log, CAS Evidence Store  │
│ - Sandboxing, Git restore capture, Regression Gate algorithms          │
│ - Core 0-Mutation Invariant (242+ green tests preserved)               │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Structuring `using-ownhands` as the Root Router

The current implementation of `skills/using-ownhands/SKILL.md` (37 lines) is a passive decision tree. To achieve the robustness of Superpowers, it must be upgraded with:
1. **Frontmatter & Description:** Triggering on workspace entry, task changes, and instruction updates.
2. **Hard XML Guardrails:**
   - `<SUBAGENT-STOP>`: Ensures subagents dispatched by DevHarness do not recursively invoke the router.
   - `<EXTREMELY-IMPORTANT>`: Imposes the non-negotiable rule that no code modification or shell command execution is permitted before context validation and harness profiling.
3. **Iron Law of OwnHands:**
   ```text
   NO CODE MUTATION WITHOUT CONTEXT VALIDATION AND PROFILE BASELINE FIRST
   NO TASK COMPLETION CLAIMS WITHOUT DETERMINISTIC REGRESSION GATE PASS
   ```
4. **Priority Rule:**
   - Governance & Safety Skills (`context-validation`, `harness-profiler`) ALWAYS precede Execution Skills (`execution-control`, `test-assurance`).

### 3.3 The OwnHands Sub-Skill Topology

OwnHands organizes agent activities into four specialized sub-skills, each backed by Option C MCP tools:

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│                              using-ownhands                                   │
└──────────────┬───────────────────┬───────────────────┬─────────────────┬──────┘
               │                   │                   │                 │
               ▼                   ▼                   ▼                 ▼
     ┌──────────────────┐ ┌──────────────────┐ ┌───────────────┐ ┌───────────────┐
     │context-validation│ │ harness-profiler │ │execution-ctrl │ │test-assurance │
     └─────────┬────────┘ └────────┬─────────┘ └───────┬───────┘ └───────┬───────┘
               │                   │                   │                 │
               ▼                   ▼                   ▼                 ▼
        `context.lint`      `harness.profile`   `sandbox.inspect` `git.diff_impact`
        `context.inspect`   `harness.contract_  `approval.inspect` `tests.compare_runs`
                             validate`          `git.restore_     `assurance.gate_
                                                 capture`          evaluate`
```

#### 1. `context-validation` (M4.5-01 Vertical Slice)
- **Role:** Enforces instruction hygiene across `AGENTS.md`, `.codex/rules/*.rules`, and task overlays.
- **MCP Tools:** `context.lint`, `context.inspect`.
- **Decisions Handled:**
  - `pass`: Clean instructions. Proceed to profiling or task planning.
  - `soft_block`: Advisory warnings (broad universal wording, shadow rules). Report to user; proceed only with recorded rationale.
  - `hard_block`: Critical defects (missing files, stale references). Halts execution.

#### 2. `harness-profiler`
- **Role:** Discovers workspace structure, test commands (`pyproject.toml`, etc.), sensitive credential paths, and compiles task execution contracts.
- **MCP Tools:** `harness.profile`, `harness.contract_validate`, `harness.compile_preview`.
- **Decisions Handled:** Establishes task boundaries and baseline parameters.

#### 3. `execution-control`
- **Role:** Evaluates sandbox permissions, side effects, approval requirements, and takes Git restore snapshots before risky actions.
- **MCP Tools:** `sandbox.inspect`, `approval.inspect`, `runtime.controls_check`, `git.restore_capture`.
- **Decisions Handled:** Blocks unauthorized external network access or writes outside declared worktrees.

#### 4. `test-assurance`
- **Role:** ISTQB-aligned test design memos, Git diff impact analysis, pre/post test run comparisons, and authoritative regression gate evaluations.
- **MCP Tools:** `git.diff_impact`, `tests.design_memo`, `tests.compare_runs`, `tests.gap_detect`, `assurance.gate_evaluate`, `guarantee.evaluate`.
- **Decisions Handled:**
  - `pass`: All tests comparable pass or fixed failure.
  - `soft_block`: Gaps in coverage or unobserved side effects.
  - `hard_block`: Regression detected (`has_regression: true`). Any override is strictly rejected.

### 3.4 OwnHands Anti-Rationalization & Red Flags Engine

Coding agents in automated harnesses exhibit specific evasions when interacting with safety frameworks. `using-ownhands` must explicitly counter these thoughts:

| Agent Rationalization Thought | OwnHands Reality & Directive |
|---|---|
| "I can edit code directly without running context linting" | **STOP.** Stale rules and instruction conflicts corrupt task execution. Run `context.lint` first. |
| "I don't need to profile the repo; I can see the directory tree" | **STOP.** Skimming directory listings misses sensitive credential paths and declared test commands. Run `harness.profile`. |
| "I'll skip the baseline test run and just run pytest at the end" | **STOP.** Without a pre-change baseline receipt, you cannot prove whether failures were pre-existing or regressions. Capture baseline. |
| "I only changed one line; diff impact analysis is overkill" | **STOP.** Single-line changes can breach undeclared interfaces or unobserved side-effects. Run `git.diff_impact`. |
| "The tool returned `soft_block`, but it's just a warning, so I'll ignore it" | **STOP.** Soft blocks require an explicit human override actor, recorded rationale, and contract fingerprint. |
| "The tool returned `hard_block`, but I know how to patch around it" | **STOP.** Hard blocks represent fatal regressions or missing sources. Never bypass a hard block. |
| "I'll run bash commands directly without checking sandbox controls" | **STOP.** Destructive shell execution without pre-inspection risks unrecoverable workspace corruption. Run `sandbox.inspect`. |
| "I don't need to pass `task_id` since this is a quick check" | **STOP.** Omitting `task_id` disables CAS evidence persistence, leaving no verifiable audit trail. Always supply `task_id`. |
| "Tests pass, so I can declare the task complete" | **STOP.** Passing tests is not verification. You must invoke `assurance.gate_evaluate` and generate the Task Guarantee Report. |

### 3.5 Situation-to-Skill Routing Matrix (Option C Dispatch Matrix)

| Operational Phase | User Intent / Trigger | Delegated Sub-Skill | Target MCP Tool (`domain.action`) | Expected Decision & Gate Rule |
|---|---|---|---|---|
| **Phase 0: Workspace Entry** | Starting work, onboarding repo, exploring configuration | `harness-profiler` | `harness.profile` | `decision: null` (profile recorded) |
| **Phase 1: Instruction Alignment** | Modifying `AGENTS.md`, rules, task overlays | `context-validation` | `context.lint`, `context.inspect` | Must achieve `pass` or approved `soft_block` |
| **Phase 2: Task Contract Synthesis** | Scoping files to touch, defining permissions | `harness-profiler` | `harness.contract_validate` | Must achieve `pass` (`hard_block` halts) |
| **Phase 3: Execution Safety** | Running external commands, package installations | `execution-control` | `sandbox.inspect`, `git.restore_capture` | Pre-execution snapshot captured |
| **Phase 4: Test Design** | Formulating test strategy before code modifications | `test-assurance` | `tests.design_memo` | Test strategy aligned with ISTQB CTFL |
| **Phase 5: Pre-Change Baseline** | Capturing clean test baseline prior to edit | `test-assurance` | `tests.compare_runs` (baseline phase) | Evidence stored with `task_id` |
| **Phase 6: Post-Change Assurance** | After code edits, verifying diff and regressions | `test-assurance` | `git.diff_impact`, `tests.compare_runs` | `hard_block` if regression detected |
| **Phase 7: Task Completion** | Declaring task done, submitting PR / report | `test-assurance` | `assurance.gate_evaluate`, `guarantee.evaluate` | Must produce verified `evidence_id` and `pass` |

### 3.6 Cross-Harness Adaptation for OwnHands

OwnHands must operate across diverse client environments while invoking the same underlying MCP tools:

1. **Antigravity CLI (`agy`):**
   - Dispatches validation and research tasks via `invoke_subagent(TypeName: "research" | "self")`.
   - Tracks governance milestones via task artifacts (`write_to_file` with `IsArtifact: true`, `ArtifactType: "task"`).
   - Connects to `ownhands-mcp-server` over stdio.
2. **Codex CLI:**
   - Multi-agent isolation via `spawn_agent {fork_turns: "none"}` with explicit `model` and `reasoning_effort`.
   - Event-driven monitoring via `wait_agent` (5-10 minute bounded intervals).
   - Git worktree / sandbox detection using standard read-only commands.
3. **Claude Code / Cursor / Gemini CLI:**
   - Automatic session bootstrap context injection via hooks or extension manifests.
   - MCP tool exposure via standard MCP configuration (`mcpServers`).

---

## 4. Upgraded Specification for `skills/using-ownhands/SKILL.md`

```markdown
---
name: using-ownhands
description: Top-level OwnHands Skill Router. Use when starting any task, modifying workspace instructions, running commands with side effects, or verifying task completion. Enforces 4-tier harness safety and routes to specialized sub-skills.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance an OwnHands governance rule or safety boundary applies, you ABSOLUTELY MUST invoke the relevant sub-skill.

NO CODE MODIFICATION WITHOUT CONTEXT VALIDATION AND HARNESS PROFILING.
NO TASK COMPLETION CLAIMS WITHOUT DETERMINISTIC REGRESSION GATE PASS.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

# using-ownhands (Root Router)

You are the OwnHands Root Skill Router. You enforce harness boundaries and route requests to specialized sub-skills backed by deterministic Option C MCP tools (`domain.action`).

Do not perform direct rule lints, contract validations, or test comparisons inside this router. Delegate execution to dedicated sub-skills.

## Skill Priority

1. **Governance & Baseline First:** Before editing code or creating task plans, run `context-validation` and `harness-profiler`.
2. **Execution Safety Second:** Before running shell commands with potential side-effects, invoke `execution-control`.
3. **Test Assurance Third:** Before claiming fixes or declaring task completion, invoke `test-assurance`.

## Red Flags - STOP and Route

| Thought | Reality |
|---|---|
| "I can edit code directly without context linting" | Stale context corrupts tasks. Delegate to `context-validation`. |
| "I don't need to profile the repo" | Skimming misses credential paths and test commands. Delegate to `harness-profiler`. |
| "I'll skip the baseline test run" | You cannot prove regressions without a baseline. Delegate to `test-assurance`. |
| "I only changed one line; impact check is overkill" | Small changes cause unobserved breaks. Run `git.diff_impact`. |
| "The tool returned soft_block, I'll ignore it" | Soft blocks require explicit override rationale. |
| "The tool returned hard_block, I'll work around it" | Hard blocks are absolute stops. Fix the root cause. |
| "Tests pass, so the task is complete" | Completion requires `assurance.gate_evaluate` and evidence verification. |

## Routing Matrix

- **Starting work or modifying instructions (`AGENTS.md`, rules, overlays):**
  → Delegate to `context-validation` (invokes `context.lint`, `context.inspect`).
- **Inspecting project commands, boundaries, or contracts:**
  → Delegate to `harness-profiler` (invokes `harness.profile`, `harness.contract_validate`).
- **Evaluating side-effects, permissions, or capturing restore points:**
  → Delegate to `execution-control` (invokes `sandbox.inspect`, `git.restore_capture`).
- **Designing tests, comparing test runs, or evaluating the regression gate:**
  → Delegate to `test-assurance` (invokes `tests.compare_runs`, `assurance.gate_evaluate`).

## Platform Adaptation

Consult the tool mapping reference for your current harness:
- Antigravity: `references/antigravity-tools.md`
- Codex: `references/codex-tools.md`
- Claude Code / Gemini / Other: Native MCP tool calls via `ownhands-mcp-server`.
```

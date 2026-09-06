# Research: Adapting OwnHands to Claude Code and Grok (xAI)

**Document Path:** docs/research/claude-code-and-grok-adaptation.md  
**Author:** DevHarness Research Subagent  
**Date:** 2026-09-06  
**Status:** Approved for Harness Extension (M4.5+ Platform Adaptation)  
**Target Environments:** Anthropic Claude Code CLI, xAI Grok Build CLI, xAI API / Custom Agent Harness

---

## 1. Executive Summary

OwnHands operates on a strict **4-tier architecture** (Router Skill $\rightarrow$ Sub-Skills $\rightarrow$ MCP Gateway $\rightarrow$ Core Engine) governed by **ADR-0010** and the **Option C Hybrid Contract** (`domain.action`, 4-state decisions: `pass`, `soft_block`, `hard_block`, `unobserved`, and CAS evidence persistence).

To ensure deterministic quality assurance, context hygiene, and regression prevention across multiple agent environments, OwnHands provides platform-specific tool adaptation layers. While initial support focused on **Antigravity CLI (`agy`)** and **OpenAI Codex**, modern developer agent ecosystems increasingly center on **Claude Code** (Anthropic official terminal coding agent) and **Grok** (xAI Grok Build CLI and xAI API with first-party Remote MCP support).

This research investigates the native tools, subagent invocation models, MCP discovery mechanisms, instruction rule hierarchies, and task-tracking primitives of both platforms, establishing concrete mapping references and architectural recommendations for OwnHands integration.

---

## 2. Claude Code Architectural Investigation

### 2.1 Native Tool Catalog & Execution Semantics
Claude Code provides a specialized built-in tool suite optimized for local terminal software engineering:

1. **`Read`:** Reads file content into context with 1-indexed line slicing. Includes diff-based reading and suppresses duplicate reads of files already present in context. Supports multimodal inspection of images and PDF documents.
2. **`Edit`:** Executes precise, atomic string replacement (`file_path`, `old_string`, `new_string`). Does not generate full-file rewrites, minimizing context drift and unintended code edits.
3. **`Write`:** Creates new files or overwrites existing files entirely (`file_path`, `content`).
4. **`Bash`:** Executes shell commands within a persistent, stateful bash session. Supports timeout controls, environment configuration, and explicit permission management.
5. **`Glob` & `Grep`:** Dedicated filesystem exploration primitives. Claude Code instructions instruct the model to prefer `Glob` and `Grep` over raw `find` or `grep` shell commands to avoid unnecessary permission prompts and token overhead.
6. **`Agent` (Subagent Primitive):** Spawns isolated subagents to execute bounded subtasks (such as test exploration, code review, or research) in separate context windows.
7. **Task / Todo Tracking:**
   - **Checklist Tracking:** Multi-step tasks are tracked via `TodoWrite` (Agent SDK) or interactive task lists (`Ctrl+T`, `/todos`), where items progress through `pending`, `in_progress`, and `completed`. On recent models, this is explicitly enabled via `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`.
   - **Background Processes:** Tracked separately via `/tasks`, providing process lifecycle control over background shells and subagents.

### 2.2 Subagent Lifecycle & Isolation
- **Definition:** Subagents are declared as Markdown files with YAML frontmatter in:
  - User-level: `~/.claude/agents/*.md`
  - Project-level: `.claude/agents/*.md`
- **Frontmatter Schema:** Includes `name`, `description`, `tools` (allowlist), `disallowedTools` (denylist), `model`, and `permissionMode`.
- **Transcript Storage:** Subagent runs persist independently in `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`, remaining immune to main session compaction.
- **Loop Prevention:** To prevent subagents from recursively loading the top-level router skill, subagent prompts must include the `<SUBAGENT-STOP>` guardrail.

### 2.3 MCP Discovery & Namespacing Model
- **Configuration Sources:**
  - Project level: `.mcp.json` (committed to source control for team consistency).
  - Global user level: `~/.claude.json` (managed by Claude Code).
  - Interactive CLI: `claude mcp add` / `claude mcp add-json`.
- **Namespacing Convention:** All MCP tools are exposed to the model using the canonical pattern:
  `mcp__<server-name>__<tool-name>`
- **Identifier Pattern:** Tool names conform to `^[a-zA-Z0-9_-]{1,64}$`. While Claude Code parses dots in server outputs, aliasing dot notation (`context.lint` $\rightarrow$ `context_lint`) ensures full interoperability across permission rules and client filters.

### 2.4 Instruction Rules & Lifecycle Hooks
- **`CLAUDE.md`:** Global project instructions read at the beginning of each session.
- **`.claude/rules/*.md`:** Path-scoped rule files with `paths:` glob arrays in frontmatter. Loaded dynamically only when Claude accesses files matching the patterns.
- **Lifecycle Hooks (`hooks.json`):**
  - `SessionStart`: Injects the `using-ownhands` router bootstrap into context.
  - `PreToolUse`: Intercepts `Edit`, `Write`, or `Bash` calls to ensure prerequisite OwnHands sub-skills have executed.
  - `PostToolUse`: Records audit receipts into the CAS evidence store.

---

## 3. Grok (xAI) Architectural Investigation

### 3.1 Dual Execution Environments
Grok agentic workflows execute in two distinct modalities:
1. **Grok Build CLI (`grok`):** Official interactive and headless terminal coding agent.
2. **xAI API / Custom Agent Harness (`https://api.x.ai/v1`):** OpenAI-compatible API for custom agent harnesses.

### 3.2 Grok Build CLI Architecture
- **Configuration Hierarchy:**
  - `~/.grok/config.toml` (user defaults)
  - `.grok/config.toml` (project overrides)
  - `/etc/grok/managed_config.toml` (enterprise managed policies)
  - Active configurations can be verified via `grok inspect`.
- **Native Tools:**
  - `bash`: Local shell execution within sandbox.
  - `edit` / `write`: Local file modification, controllable via `GROK_WRITE_FILE=0` for read-only modes.
  - `read`: Local file inspection.
  - Built-in Server Tools: `web_search`, `x_search`, `code_execution` (remote sandboxed Python), `collections_search`.
- **Subagent & Task Delegation:**
  - Enabled via `GROK_SUBAGENTS=1`.
  - The agent screen manages multi-step checklists via Agent Todos (`Ctrl+T`).
  - Background processes (builds, dev servers) run as monitored background tasks.
- **Instruction Discovery:** Traverses directory hierarchy from current working directory to repository root searching for `AGENTS.md` (or `AGENT.md`), with backward compatibility for `.claude/rules/`.

### 3.3 xAI API & Function Calling Model
- **Endpoint:** `https://api.x.ai/v1/chat/completions` (OpenAI SDK compatible).
- **Client-Side Function Calling:**
  - Tools declared under `tools: [{"type": "function", "function": {...}}]`.
  - Supports `tool_choice: "auto" | "none" | "required" | {"type": "function", ...}`.
  - Model emits `tool_calls` containing `id` and `function.arguments`.
  - Client harness executes the local tool and responds with `role: "tool"`, `tool_call_id`.
- **First-Party Remote MCP Support:**
  - xAI API supports Remote MCP servers directly inside the `tools` array:
    ```json
    {
      "type": "mcp",
      "server_url": "https://<endpoint>/sse",
      "server_label": "ownhands",
      "server_description": "OwnHands Deterministic QA Gateway",
      "allowed_tools": ["context_lint", "harness_profile", "tests_compare_runs", "assurance_gate_evaluate"]
    }
    ```
  - Transports supported: Streaming HTTP and SSE (Server-Sent Events).
  - Enables cloud-hosted Grok agents to connect directly to centralized OwnHands evidence gates without client-side function forwarding.

---

## 4. OwnHands 4-Tier Mapping Matrix

| OwnHands Tier | Action / Purpose | Claude Code CLI Mapping | Grok Build CLI Mapping | Grok API / Harness Mapping |
|---|---|---|---|---|
| **Tier 1: Router** | Intercept intent, enforce safety sequencing | `CLAUDE.md` + `hooks/session-start` | `AGENTS.md` + `--rules` | System prompt injection |
| **Tier 2: Sub-Skill** | `context-validation` (Instruction hygiene) | Evaluates `CLAUDE.md`, `.claude/rules/` | Evaluates `AGENTS.md`, `.grok/` | Evaluates prompt & task contracts |
| **Tier 2: Sub-Skill** | `harness-profiler` (Repo & baseline profiling) | `Glob`, `Grep`, `Read` | `read`, local git inspect | Local file exploration tools |
| **Tier 2: Sub-Skill** | `execution-control` (Safe execution & snapshot) | Intercepts `Bash`; runs `git.restore_capture` | Intercepts `bash`; aligns with `sandbox.toml` | Pre-command git snapshot |
| **Tier 2: Sub-Skill** | `test-assurance` (Regression prevention) | `mcp__ownhands__tests_compare_runs` | `ownhands:tests.compare_runs` | Function call / Remote MCP |
| **Tier 3: MCP Gateway** | Stdio JSON-RPC Option C Envelopes | `.mcp.json` stdio runner | `.grok/config.toml` stdio runner | Client stdio runner or SSE bridge |
| **Tier 4: Core Engine** | CAS Evidence Store & Gate Evaluation | SQLite v3 + CAS at `.ownhands/data` | SQLite v3 + CAS at `.ownhands/data` | Central or local CAS evidence root |

---

## 5. Architectural Recommendations for Implementation

1. **Dual MCP Tool Name Aliasing:**
   - In `src/devharness/mcp/server.py`, register both dot-notated and underscore-aliased tool names (`context.lint` and `context_lint`, `harness.profile` and `harness_profile`, etc.) to support Claude Code's `mcp__ownhands__<tool>` validator and Grok's schema parser seamlessly.
2. **Platform Reference Files:**
   - Place `skills/using-ownhands/references/claude-code-tools.md` and `skills/using-ownhands/references/grok-tools.md` directly alongside existing `antigravity-tools.md` and `codex-tools.md`.
3. **Subagent Router Shielding:**
   - Subagent templates and dispatch instructions must mandate `<SUBAGENT-STOP>` to guarantee subagents focus strictly on leaf tasks.
4. **Instruction File Coexistence:**
   - Maintain `AGENTS.md` at the project root for Grok, Antigravity, and Codex, with a companion `CLAUDE.md` referencing the same core rules for Claude Code.

---

## 6. Primary Sources & Citations

- **Anthropic Claude Code Official Documentation:**
  - Architecture & Tools: `https://docs.anthropic.com/en/docs/agents-and-tools/claude-code`
  - Subagents & Permissions: `https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/subagents`
  - MCP Integration: `https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/mcp`
  - Memory & Rules: `https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/rules`
- **xAI Grok Official Documentation:**
  - Grok Build CLI & Settings: `https://docs.x.ai/api/build/config`
  - Tools & Function Calling: `https://docs.x.ai/api/tools`
  - Remote MCP Tools: `https://docs.x.ai/api/tools/remote-mcp`
  - Agentic Workflows & Subagents: `https://docs.x.ai/api/build/agents`
- **OwnHands Project Repositories & Specifications:**
  - ADR-0010: Skill / MCP / Plugin Architecture (`docs/adr/0010-skill-mcp-plugin-architecture.md`)
  - Milestone 11 Contract Specification (`docs/product/m4.5-contracts.md`)

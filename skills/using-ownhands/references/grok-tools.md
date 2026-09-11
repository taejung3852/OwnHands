# Grok (xAI) Tool Mapping for OwnHands

When executing OwnHands skills in the xAI Grok ecosystem (Grok Build CLI or Grok API custom harness), actions map to the following native primitives:

| Action in OwnHands Skills | Grok Build CLI (`grok`) | Grok API / Custom Harness | Notes |
|---|---|---|---|
| **Dispatch Subagent** | Subagent / Task tool (`GROK_SUBAGENTS=1`) | Client-side subagent loop or orchestrator | Must inject `<SUBAGENT-STOP>` to prevent recursive router invocations. |
| **Track Governance Milestones** | Agent Todos (`Ctrl+T`) & background tasks | In-context markdown checklist / plan object | Separate multi-step todo tracking from background OS process monitoring. |
| **Invoke OwnHands MCP Tools** | mcp_servers.ownhands configuration | Function calling (`tools`) or Remote MCP (`type: "mcp"`) | Transports Option C JSON-RPC envelopes. |
| **Inspect Source & Rule Files** | `read` / local file tools | Tool call to local reader / inspector | Traverses and validates AGENTS instructions and rules. |
| **File Modification** | `edit` or `write` (governed by `GROK_WRITE_FILE`) | Tool call to local file editor | Permitted during implementation after spec approval and baseline capture. |
| **Shell & Command Execution** | `bash` (governed by sandbox policy) | Tool call to local shell runner | Used for baseline test capture and post-implementation review verification. |

---

## Grok Build CLI Configuration

In the project root, configure Grok MCP settings to connect OwnHands tools:

```toml
[mcp_servers.ownhands]
command = "uv"
args = [
    "run",
    "--no-project",
    "--python",
    "3.12",
    "-m",
    "devharness.mcp.server",
    "--data-root",
    ".ownhands/data"
]

[rules]
auto_approve = [
    "ownhands:context.lint",
    "ownhands:harness.profile"
]
```

### Enabling Subagents & Permissions in Grok Build
Environment variables configuration:
```bash
export GROK_SUBAGENTS=1            # Enables subagent delegation and task tools
export GROK_SANDBOX_AUTO_ALLOW_BASH=0  # Requires permission verification before shell runs
```

---

## Grok API & Remote MCP Integration Model

When building a custom harness using the Grok API, OwnHands supports two execution models:

### Model A: Client-Side Stdio MCP Gateway (Local Codebases)
1. The harness defines OwnHands functions in the `tools` payload (`context_lint`, `harness_profile`, `tests_compare_runs`, `assurance_gate_evaluate`).
2. Grok returns `tool_calls` with tool arguments.
3. The harness routes calls to the devharness MCP server via stdio JSON-RPC.
4. Tool outputs are appended as `role: "tool"` messages with `tool_call_id`.

### Model B: Remote MCP Tool (Cloud / Remote Environments)
For distributed or CI/CD runners, Grok natively accepts Remote MCP server definitions directly in the `tools` array:

```json
{
  "messages": [
    {"role": "system", "content": "You are guided by OwnHands governance. Validate context and baselines before editing code."},
    {"role": "user", "content": "Run regression test comparison for current PR"}
  ],
  "tools": [
    {
      "type": "mcp",
      "server_url": "https://mcp.your-domain.com/sse",
      "server_label": "ownhands",
      "server_description": "OwnHands Quality Assurance Gateway",
      "allowed_tools": [
        "context_lint",
        "harness_profile",
        "tests_compare_runs",
        "assurance_gate_evaluate"
      ]
    }
  ]
}
```

---

## Subagent Isolation Guardrail

When spawning subagents via Grok subagent delegation, wrap task prompts with:

```markdown
<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore using-ownhands.
</SUBAGENT-STOP>
```

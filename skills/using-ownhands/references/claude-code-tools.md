# Claude Code CLI Tool Mapping for OwnHands

When executing OwnHands skills in the Claude Code (Anthropic CLI) environment, actions map to the following native primitives:

| Action in OwnHands Skills | Claude Code CLI Equivalent | Notes |
|---|---|---|
| **Dispatch Subagent** | `Agent` tool (`subagent_type`, `prompt`, `description`) | Defined under claude agents directory. Provide `<SUBAGENT-STOP>` in prompt to prevent re-routing loops. |
| **Track Governance Milestones** | Task list (`TodoWrite`, Ctrl+T, or tasks) | States transition across `pending`, `in_progress`, and `completed`. Use tasks for background subagents. |
| **Invoke OwnHands MCP Tools** | `mcp__ownhands__<tool>` via stdio JSON-RPC | Configured in project MCP configuration or user config. Aliased as `mcp__ownhands__context_lint`, `mcp__ownhands__harness_profile`. |
| **Inspect Source & Rule Files** | `Read`, `Glob`, `Grep` | `Read` handles line slicing and multimodal files; `Glob` and `Grep` provide repository indexing. |
| **File Modification** | `Edit` (string replacement) or `Write` (full file) | Permitted during implementation after spec approval and baseline capture. |
| **Shell & Command Execution** | `Bash` (`command`, `timeout`) | Used for baseline test capture and post-implementation review verification. |

---

## MCP Server Configuration for Claude Code

Configure the OwnHands MCP server in project MCP configuration:

```json
{
  "mcpServers": {
    "ownhands": {
      "command": "uv",
      "args": [
        "run",
        "--no-project",
        "--python",
        "3.12",
        "-m",
        "devharness.mcp.server",
        "--data-root",
        ".ownhands/data"
      ]
    }
  }
}
```

Interactive registration command:
```bash
claude mcp add ownhands -- uv run --no-project --python 3.12 -m devharness.mcp.server --data-root .ownhands/data
```

### Tool Identifier Convention
Claude Code prefixes exposed MCP tools with the pattern:
`mcp__<server-name>__<tool-name>`

Identifier mapping:
- context.lint -> `mcp__ownhands__context_lint`
- harness.profile -> `mcp__ownhands__harness_profile`
- tests.compare_runs -> `mcp__ownhands__tests_compare_runs`
- assurance.gate_evaluate -> `mcp__ownhands__assurance_gate_evaluate`

---

## Subagent Isolation Guardrail

When spawning subagents via Claude Code `Agent` tool, wrap task prompts with:

```markdown
<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore using-ownhands.
</SUBAGENT-STOP>
```

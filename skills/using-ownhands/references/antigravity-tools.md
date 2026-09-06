# Antigravity CLI (`agy`) Tool Mapping for OwnHands

When executing OwnHands skills in the Antigravity CLI environment, actions map to the following native primitives:

| Action in OwnHands Skills | Antigravity CLI Equivalent | Notes |
|---|---|---|
| **Dispatch Subagent** | `invoke_subagent` with `TypeName: "self"` (full write) or `"research"` (read-only) | Ensure subagents have `<SUBAGENT-STOP>` active to prevent re-routing loops. |
| **Track Governance Milestones** | Task Artifact (`write_to_file` with `IsArtifact: true`, Task artifact type) | Do NOT use `manage_task`, which is exclusively for background OS process lifecycle. |
| **Invoke OwnHands MCP Tools** | `run_command` invoking Python MCP runner or native MCP stdio connection | Calls devharness MCP server with Option C JSON-RPC envelopes. |
| **Inspect Source & Rule Files** | `view_file` | Read rules, AGENTS instructions, and task overlays. |
| **File Modification** | `replace_file_content` or `write_to_file` | Permitted only after `context-validation` pass. |

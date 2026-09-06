# OpenAI Codex Tool Mapping for OwnHands

When executing OwnHands skills in the OpenAI Codex environment, actions map to the following native primitives:

| Action in OwnHands Skills | Codex CLI / App Equivalent | Notes |
|---|---|---|
| **Dispatch Subagent** | `spawn_agent {fork_turns: "none"}` | Provide clean context isolation. Explicitly specify `model` and `reasoning_effort`. |
| **Wait for Subagent Completion** | `wait_agent` with bounded timeout (300000-600000 ms) | Treat as event subscription, not short-polling. |
| **Resume Subagent** | `followup_task` | Use to deliver fix rounds or review requests. |
| **Track Tasks & Checklists** | Plan file or markdown checklist in session context | Maintained across task phases. |
| **Invoke OwnHands MCP Tools** | Native MCP client configured in Codex config or mcpServers | Transports Option C domain:action requests. |
| **Inspect Sandbox & Worktrees** | Read-only git commands (`git rev-parse --git-dir`, `git branch --show-current`) | Determine worktree isolation before modifying files. |

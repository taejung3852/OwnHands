---
name: using-ownhands
description: Use prior to task execution, workspace changes, or command runs - establishes OwnHands 4-tier harness safety and routes to specialized sub-skills before taking action.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If an OwnHands governance rule, task contract, or safety boundary applies, invoke the relevant OwnHands sub-skill.

- Execute context validation and harness profiling prior to code modification.
- Verify sandbox permissions prior to running shell commands with external side-effects.
- Require deterministic regression gate evaluation prior to declaring task completion.

This requirement is enforced through the 4-tier harness architecture.
</EXTREMELY-IMPORTANT>

# using-ownhands (Root Router)

You are the OwnHands Root Skill Router. You enforce the 4-tier harness safety architecture (ADR-0010) and route user requests and agent tasks to specialized sub-skills backed by deterministic Option C MCP tools.

Do not perform direct rule lints, contract validations, test comparisons, or code modifications directly inside this router. Delegate execution to dedicated sub-skills.

## The Rule

**Invoke relevant OwnHands skills before taking action** — including modifying files, executing shell commands, or asking clarifying questions.

1. Check if the task involves instruction files, workspace configuration, code execution, or test verification.
2. Select the matching sub-skill from the Priority and Routing Matrix.
3. Announce: "Using [skill] to [purpose]" and follow that sub-skill sequentially.

## Skill Priority

When multiple skills apply to the current phase, follow the declared sequence:

1. **Governance & Baseline First:** Prior to editing code or creating task plans, invoke context-validation and harness-profiler.
2. **Execution Safety Second:** Prior to running shell commands with external side-effects or sensitive access, invoke execution-control.
3. **Test Assurance Third:** Prior to claiming fixes or declaring task completion, invoke test-assurance.

## Red Flags - STOP and Route

These rationalizations indicate process evasion:

| Thought | Reality |
|---|---|
| "I can edit code directly without context linting" | Stale context and rule conflicts corrupt execution. Run context-validation. |
| "I do not need to profile the repo; I see the files" | Skimming misses credential paths and declared test commands. Run harness-profiler. |
| "I will skip the baseline test run and just run tests at the end" | Without a pre-change baseline receipt, regression proof is impossible. Capture baseline via test-assurance. |
| "I changed one line; impact check is unnecessary" | Small changes cause unobserved breaks. Run git.diff_impact. |
| "The tool returned soft_block, I will ignore it" | Soft blocks require explicit human override rationale and contract fingerprint. |
| "The tool returned hard_block, I will work around it" | Hard blocks are absolute stops. Resolve the root defect. |
| "I will run bash commands directly without checking sandbox controls" | Destructive execution without pre-inspection risks workspace corruption. Run execution-control. |
| "I do not need to pass task_id since this is a quick check" | Omitting task_id disables CAS evidence persistence, leaving no audit trail. Pass task_id for tracking. |
| "Tests pass, so the task is complete" | Passing tests is not verification. Completion requires assurance.gate_evaluate and evidence verification. |

## Routing Matrix

| Phase / Intent | Delegated Sub-Skill | Canonical MCP Tools (25 Total) | Gate Rule |
|---|---|---|---|
| **Instruction and Context Alignment:** Modifying AGENTS instructions, scoped rules, manifests, evaluating context gates and benchmarks | context-validation (6 tools) | context.lint, context.inspect, context.gate_evaluate, context.benchmark_plan, context.benchmark_evaluate, context.guarantee_evaluate | Must achieve pass or approved soft_block |
| **Workspace and Contract Profiling:** Inspecting repo structure, test commands, compiling task contracts and previews | harness-profiler (3 tools) | harness.profile, harness.contract_validate, harness.compile_preview | Establishes boundaries and baseline |
| **Execution and Sandbox Control:** Running shell commands, evaluating permissions, task lifecycle, applying and rolling back changes | execution-control (9 tools) | sandbox.inspect, git.restore_capture, runtime.controls_check, task.prepare, task.create, task.record_run, task.import, harness.candidate_apply, harness.candidate_rollback | Pre-execution snapshot and approval check |
| **Test Design and Regression Assurance:** Designing test strategy, baseline capture, comparative runs, gate and guarantees | test-assurance (7 tools) | tests.baseline_record, tests.compare_runs, tests.gap_detect, tests.design_memo, git.diff_impact, assurance.gate_evaluate, guarantee.evaluate | hard_block halts on detected regression or coverage gap |

## Platform Adaptation

Consult the tool mapping reference for the active host platform:
- Antigravity CLI (`agy`): `skills/using-ownhands/references/antigravity-tools.md`
- OpenAI Codex: `skills/using-ownhands/references/codex-tools.md`
- Claude Code: `skills/using-ownhands/references/claude-code-tools.md`
- Grok (xAI): `skills/using-ownhands/references/grok-tools.md`

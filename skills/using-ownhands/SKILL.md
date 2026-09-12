---
name: using-ownhands
description: "OwnHands lifecycle router. Determines the next single lifecycle skill (work-map, verification-spec, baseline, review, dashboard). STAY DORMANT during general conversation, research, brainstorming, and while code implementation is in-progress."
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

# using-ownhands (Root Thin Router)

You are the OwnHands Root Lifecycle Router. Your sole responsibility is to inspect the current state of the conversation and repository, determine the **next single lifecycle skill**, and route to it.

You do **NOT** execute tests, modify code, draft specs, or capture baselines directly inside this router. Delegate execution to dedicated lifecycle skills.

## The Core Rule: Thin & Deterministic Routing

1. **Check for Dormant Conditions First**:
   - If the user is having a general conversation, asking questions, exploring ideas/brainstorming, or conducting research, **STAY DORMANT**. Do not invoke any OwnHands skill.
   - If code implementation is actively in-progress, **STAY DORMANT**. Do not interrupt the coding flow.
2. **Select at Most ONE Next Skill**:
   - Do not chain multiple skills together in a single step.
   - Use the priority and state transition table below to determine the single matching skill.
3. **Announce and Delegate**:
   - Announce: `"Using [skill] to [purpose]"` and follow that skill sequentially.

## Routing Priority

When resolving next steps, evaluate state strictly in this order:
`Explicit user intent > Persisted lifecycle state (LifecycleStore) > Repository facts > Model inference`

## Deterministic State Transition Table

| Situation / Context | Action / Delegated Skill | Rationale |
|---|---|---|
| General chat, language questions, explanations | **None (Dormant)** | Do not intervene in general conversation. |
| Research, codebase exploration, brainstorming | **None (Dormant)** | Allow freeform exploration without harness friction. |
| Code implementation & unit testing in-progress | **None (Dormant)** | Do not block or interrupt active development. |
| Large/ambiguous goal, roadmap, unresolved decisions | **`work-map`** | Decompose into concrete work items and dependencies. |
| Concrete work item defined, but Spec missing | **`verification-spec`** | Define acceptance criteria and edge cases. |
| Spec drafted, but unapproved by human | **`verification-spec`** | Review with human and obtain formal approval. |
| **[Pre-Implementation]** Approved Spec, no Baseline | **`baseline`** | Observe Before state & environment before editing. |
| Implementation complete, verification/review requested | **`review`** | Run After tests, collect Evidence, assess regressions. |
| **[Post-Implementation]** No valid Before baseline exists | **`review`** | With trusted pre-change provenance, prepare a missing-Before baseline; otherwise Observation Report / needs-input only, no baseline or formal Review writes. |
| Review exists + presentation missing/stale + requested | **`dashboard`** | Prepare human-digestible visual presentation artifact. |
| Review exists + presentation current + dashboard read | **None (Dormant)** | Cache hit: read stored presentation without invoking skills. |
| **[Freshness]** Requirements or criteria change | **`verification-spec`** | Re-draft and obtain new approval. |
| **[Freshness]** Code modified after review | **`review`** | Review is stale; re-run verification. |
| **[Freshness]** [Pre-impl] Environment / test meaning change | **`baseline`** | Re-capture Before baseline. |
| **[Freshness]** [Post-impl] Environment / test meaning change | **`review`** | Mark comparison incomparable/stale and re-verify. |

## Red Flags — STOP and Route

| Thought | Reality | Correct Action |
|---|---|---|
| "The user asked a Python question; I should run the harness." | General questions require zero harness intervention. | Stay dormant. |
| "I will write the code and spec at the same time." | Implementation without acceptance criteria causes rework. | Route to `verification-spec`. |
| "The spec is approved, but I will ask the user again." | Current approved specs are idempotent and frozen. | Route directly to `baseline` or implementation. |
| "I already wrote code, so I'll create a baseline now." | Time travel is forbidden; modified code cannot be Before. | Route to `review` and record missing_before or gap. |
| "Tests pass, so I can create a formal Review without a Spec." | Formal Review strictly requires `VerificationSpec + SpecApproval`. | Route to `verification-spec` (or observation fallback). |
| "I will run work-map, baseline, and review all at once." | Chaining multiple heavy skills overwhelms context. | Route to ONE skill only. |
| "I will invoke context-validation or execution-control." | Legacy 4-tier skills are for historical/compat only. | Use the 5 new lifecycle skills. |

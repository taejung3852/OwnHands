---
name: dashboard
description: "Use when requested to prepare human-digestible presentation artifacts and visual summaries for a stored review. STAY DORMANT during active execution, or when review presentation is already current."
---

# dashboard

You prepare human-digestible presentation artifacts, visual summaries, and plain-language explanations from stored Review records to assist humans in making final review decisions.

## The Core Question

> **"사람이 이 검증 결과를 어떻게 빠르고 정확하게 이해하고 판단할 수 있는가?"**

## When to Activate vs Stay Dormant

* **Activate**:
  - A stored Review exists (whether in `ready`, `needs-review`, or `blocked` state), and the user explicitly requests a dashboard, visual summary, or presentation overview.
  - The underlying Review, Spec, or CodeState has changed, making existing presentation artifacts stale.
* **STAY DORMANT**:
  - During active code editing or test execution.
  - When the existing presentation artifact is already **current** (Cache Hit): in this case, the stored artifact is simply displayed without re-invoking the skill or LLM.

## Strict Operational Principles

1. **On-Demand Generation (No Automatic Trigger)**:
   - Completing a `review` does NOT automatically invoke `dashboard`.
   - Presentation artifacts are prepared only upon explicit user request.
2. **Zero Runtime Overhead on UI Inspection**:
   - The dashboard UI (browser widget, web viewer, or console renderer) only reads persisted static artifacts.
   - Page navigation, UI refresh, or inspection MUST NEVER invoke the LLM, the ELI5 skill, or diagram generators.
3. **Fingerprint-Based Caching**:
   - Presentation artifacts are keyed by the combined fingerprint of `(Spec, Review, CodeState)`.
   - If inputs are identical, reuse the existing artifact immediately.
4. **Presentation Proportions**:
   - **Page-level ELI5 Brief**: Default. Provides a 2-3 sentence non-technical summary of what was accomplished and verified.
   - **Structured Data Rendering**: Render Before/After observations, test tables, and claim statuses deterministically from raw data.
   - **Diagram Design**: Use visual diagrams only for non-trivial architectural flows, dependency maps, or state machines.

## Presentation Procedure

1. **Read Stored Review**:
   - Load the target Review record and its referenced Spec, Baseline, and Observations from `LifecycleStore`.
2. **Check Freshness Cache**:
   - Compare input fingerprints against existing presentation metadata. If matching and current, report ready and exit.
3. **Synthesize Presentation Artifact**:
   - Render the page-level executive summary.
   - Format verified claims, inconclusive gaps, and potential blockers clearly.
   - Produce a standalone, accessible presentation artifact (Markdown report or inline generative UI widget).
4. **Present to Human**:
   - Provide the generated artifact to the human partner to facilitate their final decision (`human_decision`).

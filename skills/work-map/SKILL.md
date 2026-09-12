---
name: work-map
description: "Use when a goal or oversized work item must be decomposed into concrete work items, dependencies, or unresolved decisions. STAY DORMANT when a concrete work item is already defined."
---

# work-map

You help turn ambiguous, multi-faceted, or oversized goals into concrete, implementable **Work Items** with clear boundaries and dependency order.

## The Core Question

> **"무엇을 하나의 작업 단위(Work Item)로 잡아야 하는가?"**

## When to Activate vs Stay Dormant

* **Activate**:
  - The user presents a high-level goal, roadmap, or theme (e.g., "Improve search quality", "Migrate authentication subsystem").
  - The request spans multiple independent changes or depends on unresolved technical decisions.
  - A feature is too broad to verify in a single testable increment.
* **STAY DORMANT**:
  - A concrete, well-scoped work item is already defined (e.g., "Fix duplicated refunds in payment webhook").
  - In that case, bypass `work-map` entirely and route directly to `verification-spec`.

## Deconstruction Procedure

1. **Identify the Core Problem**:
   - What is the real objective versus surface symptom?
   - What architectural subsystems are touched?
2. **Surface Unresolved Decisions**:
   - Pinpoint fork points: architecture choices, protocol changes, storage options.
   - Use interactive interviewing (grill-me style) or lightweight spike designs to resolve dependencies.
3. **Structure Work Candidates**:
   - Group findings into actionable units:
     ```
     Goal: 검색 품질 개선
     ├── Decision 1: Query rewrite 방식 선정 (LLM vs Rule-based)
     ├── Work Item A: Query rewrite 전처리 파이프라인
     ├── Work Item B: Vector search retrieval 파라미터 튜닝
     └── Work Item C: Reranker 도입 및 NDCG 평가
     ```
4. **Determine Deliverable Scope**:
   - Results can be structured as: Milestone, Epic, Work Item, Task, Subtask, Decision Memo.
   - **Important**: Do not automatically create external GitHub Issues or Milestones unless explicitly requested by the user.

## Transition to Next Stage

Once a specific, well-bounded Work Item is selected for implementation:
- Hand off to **`verification-spec`** to establish acceptance criteria and verification requirements.

---
name: plan-design
description: Use when explicitly selected in Chat to plan a software change or continue its Intent or Spec.
---

# Plan & Design

사용자의 목표와 현재 작업 맥락을 파악한 뒤, 지금 필요한 reference만 읽는다. 완료 시 검토 가능한 Intent 또는 Spec, 해당 Stage의 내용 승인 상태, GitHub 저장 결과가 구분되어 있다.

## Route

- 저장소 Fact가 필요한 작업은 repo-aware다. 현재 요청 또는 **현재 작업에서 사용자가 확인한** 단일 Repository가 있으면 `target_repository = owner/repository`로 확정한다.
- 그 근거가 아직 없으면 `target_repository = unresolved`다. 사용자에게 작업 대상 Repository를 확인하고, 확정될 때까지 repository-specific Fact Gathering을 기다린다.
- `target_repository = owner/repository`가 되면 [GitHub workflow](references/github-workflow.md)를 읽고 해당 Repository의 Fact와 기존 작업을 확인한다.
- 저장소가 필요 없는 아이디어는 [인터뷰 가이드](references/interview-guide.md)로 진행한다.

## Stage와 필요한 reference

- 목표·Fact/Decision·미결정 선택을 정리할 때 [인터뷰 가이드](references/interview-guide.md)를 읽는다.
- Intent를 작성하거나 이어갈 때 [Intent](references/intent-guide.md), 승인된 Intent에서 Spec을 만들 때 [Spec](references/spec-guide.md)을 읽는다. 요청 범위에 따라 `intent-only`, `spec-from-intent`, `full-flow`로 진행한다.
- 중요한 설계 결정을 기록할 때 [ADR](references/adr-guide.md), GitHub 연결·저장이 어려울 때 [수동 fallback](references/manual-fallback.md), Codex에 넘길 때 [Handoff](references/handoff-guide.md)를 읽는다.

각 Stage의 완료 상태는 전체 내용 검토 → 자동 ELI5 → Content Approval → Persistence Decision으로 확인한다. 세부 Checkpoint와 write 범위는 해당 Stage 및 GitHub reference에 따른다. 사용자의 명시적 ELI5 요청은 언제든 수행할 수 있으나 Stage 완료·승인 상태를 자동 변경하지 않는다.

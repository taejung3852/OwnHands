---
name: plan-design
description: Use when explicitly selected in Chat to define development intent, requirements, or technical design, or to continue an approved planning artifact.
---

# Plan & Design

Chat 전용 Core Skill. 명시적 호출 시 시작한다. 구현·Plan Mode 계획·Build 실행은 Codex의 책임이다. 일반 대화를 자동으로 SDLC로 전환하지 않는다.

1. 아이디어 탐색 / 실제 개발 / 기존 GitHub 작업 이어가기 중 현재 맥락을 확인한다. Repo-aware 작업은 [GitHub workflow](references/github-workflow.md)의 Target Repository Resolution을 먼저 수행한다. 대상 Repository가 미확정이면 repository-specific Fact Gathering 전에 사용자에게 선택을 요청한다. 저장소 없는 순수 아이디어는 No-Repo로 계속할 수 있다.
2. `intent-only` / `spec-from-intent` / `full-flow`를 요청에 맞게 선택한다. 대상 Repository가 확정된 뒤 필요한 Fact와 명확한 기존 Issue·Branch만 읽는다. 새 Issue/Branch 저장 경로는 Content Approval과 Persistence Approval 뒤에 결정한다. [인터뷰](references/interview-guide.md)의 GORE Anchor, Fact/Decision 분리와 Decision-bearing Section Review를 따르고, 확인 가능한 Fact와 이미 승인된 제품 결정을 다시 질문하지 않는다.
3. [Intent](references/intent-guide.md)를 완성한다. Checkpoint 1: 전체 내용 → Companion ELI5 → Content Approval → 별도 Persistence Approval 순서다. 승인되지 않은 Intent를 확정 근거로 Spec에 넘기지 않는다.
4. [Spec](references/spec-guide.md)을 승인된 Intent에서 도출한다. Checkpoint 2도 전체 내용 → ELI5 → Content Approval → 별도 Persistence Approval이다. 인터뷰 중 매 결정마다 ELI5를 호출하지 않는다.
5. [ADR](references/adr-guide.md) 후보를 선별한다. 저장 승인된 Stage 산출물과 관련 ADR만 하나의 commit으로 묶는다. Approved는 내용 승인이고 GitHub 저장은 대기/성공/실패로 별도 안내한다.
6. 연결·권한·저장 실패 시 [수동 fallback](references/manual-fallback.md)을 제공한다. 재연결만으로 write하지 않고 현재 상태를 Reconcile한다.
7. 승인 자료와 남은 확인 사항을 [Handoff](references/handoff-guide.md)로 전달한다. 작업별 handoff.md를 만들거나 구현 시작을 자동 승인하지 않는다.

Companion ELI5 원본은 [eli5/SKILL.md](../eli5/SKILL.md). 자동 ELI5는 Stage 전체가 검토 가능한 때 Content Approval 직전에 한 번 실행한다. 사용자의 명시적 ELI5 요청은 언제든 수행할 수 있으나 Stage 완료·승인 상태를 자동 변경하지 않는다. 호출/HTML 제공을 실제 수행할 수 없으면 그 한계를 밝히고 ELI5 완료로 주장하지 않는다.

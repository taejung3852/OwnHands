# Intent: Chat Plan & Design — GitHub-centered SDLC

- **작성자**: 박태정 (@taejung3852) & ChatGPT
- **일자**: 2026-09-22
- **상태**: Approved — 사용자 승인 (Checkpoint 1)
- **관련 Issue**: [#154](https://github.com/taejung3852/OwnHands/issues/154)
- **Source of Truth**: [ADR-0011](../../adr/0011-chat-codex-ownership-and-handoff.md), [ADR-0012](../../adr/0012-authoring-skills-via-ownhands-mcp.md), [ADR-0017](../../adr/0017-guided-planning-and-visual-approval.md), [ADR-0019](../../adr/0019-github-centered-sdlc-and-stage-commits.md)

---

## 1. 문제 및 배경 (Why)

### 현재 상황과 고통

OwnHands의 첫 실제 E2E에서 기획·설계 대화와 구현·검증이 같은 Codex 흐름에 섞이면서 단계 경계가 흐려졌다. 사용자는 러프한 요구를 충분히 논의하는 작업과 실제 코드를 실행하는 작업을 분리하고 싶어 한다.

ChatGPT는 사용자와 목표·비목표·성공 기준·기술 선택을 대화로 좁히는 공간으로 사용하고, Codex는 승인된 설계를 실제 구현·검증하는 실행 환경으로 사용한다. 이 선택은 사용자의 작업 방식에 대한 결정이며 특정 모델의 우열이나 정량적인 비용 절감 효과를 이미 검증했다는 뜻은 아니다.

또한 세션 자체가 기억의 중심이 되면 Chat과 Codex 사이 인계가 대화 복사에 의존하게 된다. 작업의 상태와 승인 결과는 GitHub에 남아야 이후 세션과 도구가 같은 기준을 읽을 수 있다.

### 대상 사용자

- OwnHands를 이용해 AI 코딩 에이전트와 실제 소프트웨어 개발을 수행하는 사용자
- 우선 dogfooding 대상은 OwnHands의 소유자인 박태정이다.

---

## 2. 목표 결과 및 가치 (What)

### 최상위 Goal

**Chat에서 충분히 기획·설계한 승인 상태를 GitHub에 영속화하고, Codex가 그 상태를 이어받아 재인터뷰 없이 Plan → Build → Verify를 수행할 수 있는 GitHub 중심 SDLC를 만든다.**

### 목표 사용자 흐름

```text
아이디어 / 요청
  ↓
실제 개발하기로 결정
  ↓
기존 Issue 사용 / 없으면 Issue 생성
  ↓
단일 작업 Branch
  ↓
ChatGPT
  Intent 논의 → 사용자 승인
  ↓
GitHub
  intent.md + Intent 과정에서 생긴 관련 ADR을 일괄 Commit
  ↓
ChatGPT
  Spec 논의 → 사용자 승인
  ↓
GitHub
  spec.md + Design 과정에서 생긴 관련 ADR을 일괄 Commit
  ↓
간결한 Handoff
  ↓
Codex
  Implementation Plan 논의 → 사용자 승인 → plan.md 저장
  → Build → Verify
  ↓
PR → Human Gate → Merge
```

### GitHub의 역할

GitHub를 SDLC의 중심 Source of Truth로 사용한다.

- **Issue**: 작업의 존재와 진행 연결점
- **Intent**: 왜 만들고 무엇을 달성하며 어디까지가 경계인지
- **Spec**: 구현자가 따라야 할 기술 계약과 Acceptance Criteria
- **ADR**: 중요한 선택의 맥락·대안·이유
- **plan.md**: 승인된 구현 순서·변경 범위·검증 방법
- **Commit**: 승인된 상태와 실제 변경의 버전 이력
- **PR**: 실제 변경 결과·검증 Evidence·Human Gate의 협업 지점

ChatGPT와 Codex는 Source of Truth 자체가 아니라 GitHub의 SDLC 상태를 앞뒤에서 다루는 작업 인터페이스다.

### 성공 기준

첫 Thin Slice E2E에서 다음 흐름을 한 작업으로 관통한다.

1. 실제 개발로 확정된 작업이 GitHub Issue를 가진다.
2. Issue부터 PR까지 하나의 작업 Branch를 사용한다.
3. Chat에서 Intent와 Spec을 각각 충분히 논의하고 승인한다.
4. Draft 결정마다 커밋하지 않고, 각 Stage 승인 시 관련 산출물을 묶어 GitHub에 저장한다.
5. Codex가 승인된 Intent·Spec·관련 결정의 의미를 이해하고 중요한 제품 결정을 다시 질문하지 않은 채 구현 계획을 준비할 수 있다.
6. 승인된 구현 계획을 `plan.md`로 보존한 뒤 Build → Verify까지 수행한다.
7. 결과를 PR로 연결하여 Human Gate까지 도달한다.

---

## 3. 비목표 (Non-goals & Boundaries)

- ChatGPT에서 기획하는 방식이 Codex보다 우월한지 다시 비교 실험하지 않는다.
- 특정 ChatGPT 요금제의 한도, 실제 토큰 절감량, 비용 절감률을 제품 보장으로 주장하지 않는다.
- 모든 대화 Draft와 중간 Decision을 Git commit으로 보존하지 않는다.
- Decision 하나마다 ADR 하나를 강제하지 않는다. 장기적으로 다시 봐야 할 중요한 선택만 ADR로 남긴다.
- Handoff를 지금 단계에서 고정 필드가 많은 Manifest 스키마로 강제하지 않는다.
- GitHub API를 OwnHands MCP 안에 다시 구현하지 않는다.
- 이번 Intent 승인만으로 MCP/Plugin 전달 방식, 인증, 원격 접속, 충돌 처리 구현이 완료됐다고 보지 않는다.
- trivial change까지 항상 Intent/Spec/Plan heavy flow를 강제하는 기준은 이번 단계에서 확정하지 않는다.

---

## 4. 핵심 제약 조건 (Constraints)

### 책임 분리

- **ChatGPT**: GORE 기반 Plan(기획)과 Design(설계), 사용자 승인 UX
- **OwnHands MCP/Plugin**: ChatGPT가 사용할 Intent·Spec·ADR 작성 Skill 및 가이드 제공
- **GitHub 연결 도구**: Issue/Branch/파일/Commit/PR 등 저장소 상태 읽기·쓰기
- **Codex**: 승인된 설계를 바탕으로 Implementation Plan, Build, Verify 수행

### Work Item과 Branch

- 단순 아이디어 탐색 단계에서는 Issue 생성을 강제하지 않는다.
- 사용자가 실제 개발 작업으로 진행하기로 확정하면 GitHub Issue를 Work Item으로 사용한다.
- 기존 Issue가 없다면 Chat 흐름에서 Issue를 생성하는 것을 기본 경로로 한다.
- Issue부터 PR까지 하나의 작업 Branch를 이어서 사용한다.

### Stage 승인과 Commit 경계

- **Commit Boundary = Stage Approval Boundary**를 기본 원칙으로 한다.
- Intent 논의 중 Draft는 Chat에서 다루고, Intent 승인 시 `intent.md`와 그 과정에서 생성·수정된 관련 ADR을 한 번에 저장한다.
- Spec 승인 시 `spec.md`와 Design 과정에서 생성·수정된 관련 ADR을 한 번에 저장한다.
- Codex의 구현 계획은 사용자 승인 후 `plan.md`로 보존한다.
- 중간 결정마다 Git history를 쪼개는 것을 기본 동작으로 하지 않는다.

### Handoff

- Chat 전체 대화를 Codex에 다시 전달하는 것을 기본 방식으로 삼지 않는다.
- Handoff는 Codex가 **어떤 작업인지, 어디를 봐야 하는지, 무엇이 이미 승인됐는지, 다음에 무엇을 해야 하는지** 이해할 수 있을 만큼의 안내를 제공한다.
- 정확한 Handoff 문장 템플릿과 필드 강도는 Spec에서 결정한다.
- 향후 OwnHands Plugin/Skill의 reference에 `handoff-guide.md` 같은 작성 가이드를 두는 것을 구현 후보로 유지한다.

### 정직한 Evidence

- GitHub에 문서가 저장됐다는 것과 MCP/Plugin 런타임 연결이 실제 작동한다는 것은 구분한다.
- 첫 E2E에서 Chat → GitHub → Codex → Build → Verify → PR을 실제 관측하기 전 전체 흐름을 완료로 주장하지 않는다.

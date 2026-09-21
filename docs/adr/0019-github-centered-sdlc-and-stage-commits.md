# ADR-0019: GitHub를 SDLC의 중심 Source of Truth로 사용하고 Stage 승인 시 일괄 Commit한다

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-22
- **관련 Issue:** [#154](https://github.com/taejung3852/OwnHands/issues/154)
- **선행 결정:** [ADR-0011](0011-chat-codex-ownership-and-handoff.md), [ADR-0017](0017-guided-planning-and-visual-approval.md)
- **관련 Intent:** [Chat Plan & Design](../specs/chat-plan-design-flow/intent.md)

---

## 1. Context

ADR-0011은 ChatGPT가 기획·설계를, Codex가 구현·검증을 담당하는 방향을 확정했지만 둘 사이의 지속 가능한 기준점과 승인 산출물 저장 경계는 남아 있었다.

사용자는 Chat이나 Codex 세션 자체보다 GitHub를 중심으로 SDLC가 돌아가는 구조를 선호한다. 동시에 Decision 하나가 생길 때마다 파일을 저장·커밋하면 Git history가 대화 로그처럼 잘게 쪼개지고, 어떤 커밋이 실제 승인된 Stage를 의미하는지 흐려질 수 있다.

또한 요청만 있는 탐색 단계와 실제 개발 Work Item을 구분하지 않으면 모든 아이디어가 불필요한 Issue와 Branch를 만들 수 있다.

---

## 2. Decision

### 2.1 GitHub 중심 SDLC

GitHub를 작업의 durable Source of Truth로 사용한다.

- Issue: Work Item과 진행 연결점
- Intent: 목적·결과·경계
- Spec: 기술 계약·Acceptance Criteria
- ADR: 중요한 선택의 이유와 대안
- plan.md: 승인된 구현·검증 실행 계획
- Commit: 승인 상태와 변경 이력
- PR: 결과·Evidence·Human Gate

ChatGPT와 Codex는 각각 기획·설계와 구현·검증을 수행하는 인터페이스이며, 장기 상태의 기준은 GitHub에 저장된 산출물이다.

### 2.2 Work Item 승격 규칙

- 단순 아이디어 탐색은 Issue 없이 Chat에서 진행할 수 있다.
- 사용자가 실제 개발하기로 결정한 순간부터 GitHub Issue를 Work Item으로 사용한다.
- 이미 관련 Issue가 있으면 재사용한다.
- 없다면 Chat 흐름에서 얇은 Issue를 생성하는 것을 기본 경로로 한다.
- Issue 본문은 Intent/Spec의 복제본이 아니라 작업의 존재·목표·현재 결정 지점을 보여주는 협업 표면이다.

### 2.3 단일 작업 Branch

Issue에 연결된 하나의 작업 Branch를 Intent부터 PR까지 이어서 사용한다.

기획 전용 Branch와 구현 Branch를 기본적으로 분리하지 않는다. Branch naming 세부 규칙은 후속 Spec에서 정한다.

### 2.4 Stage 승인 = Commit 경계

개별 Decision 발생 시마다 커밋하지 않는다.

```text
Intent 논의
  → 사용자 승인
  → intent.md + 관련 ADR 일괄 Commit

Spec 논의
  → 사용자 승인
  → spec.md + 관련 ADR 일괄 Commit

Codex Implementation Plan
  → 사용자 승인
  → plan.md 보존
  → Build
```

Draft와 미승인 중간 상태는 기본적으로 Chat의 작업 상태로 남긴다. Git history에는 의미 있는 Stage 상태 전이를 남긴다.

Decision 하나마다 ADR 하나를 강제하지 않는다. 장기적으로 다시 참조할 중요한 아키텍처·책임·정책 선택만 ADR로 분리한다.

### 2.5 Handoff는 가이드이지 강한 Manifest가 아니다

Chat → Codex Handoff는 전체 대화 복사를 피하고 승인된 GitHub 상태를 가리키되, 현재 단계에서 고정 필드가 많은 데이터 스키마로 강제하지 않는다.

Codex가 다음을 이해할 수 있을 만큼 제공하면 된다.

- 어떤 작업인지
- 어디의 승인 산출물을 읽어야 하는지
- 각 주요 산출물이 어떤 역할인지
- 무엇이 이미 결정됐는지
- 다음 행동이 무엇인지

정확한 템플릿은 후속 Spec에서 설계한다. OwnHands Plugin/Skill의 reference 문서(예: `handoff-guide.md`)로 좋은 Handoff 작성 규칙을 제공하는 방식을 우선 후보로 둔다.

---

## 3. Alternatives

### Decision마다 즉시 Commit

기각. 상세한 결정 이력을 모두 Git에 남길 수 있지만 Git history가 대화 단위로 과도하게 분절되고 Stage 승인 상태를 읽기 어려워진다.

### Draft부터 GitHub에 지속 저장

기본 경로로 채택하지 않는다. 중단 복구가 중요한 특수 상황에서는 후속 설계로 보완할 수 있지만, 기본 흐름은 승인 Stage만 durable artifact로 남긴다.

### 기획 Branch와 구현 Branch 분리

첫 Thin Slice 기본 경로로 채택하지 않는다. 인계와 동기화 지점이 추가되고 GitHub 중심 단일 Work Item 흐름을 복잡하게 만든다.

---

## 4. Consequences

### 장점

- Git history가 SDLC의 의미 있는 상태 전이를 나타낸다.
- Chat과 Codex 세션이 바뀌어도 GitHub에서 현재 승인 상태를 복원할 수 있다.
- Issue → Branch → Intent → Spec → Plan → PR의 추적성이 단순해진다.
- Draft 대화와 durable decision의 책임이 분리된다.

### 비용과 주의점

- Stage 승인 직전 Chat 상태가 사라지면 미승인 Draft를 복구하지 못할 수 있다.
- 같은 Branch를 여러 실행 주체가 다룰 때 동시 수정 충돌이 발생할 수 있다.
- Handoff를 너무 느슨하게 만들면 Codex가 필요한 의미를 놓칠 수 있고, 너무 강하게 만들면 Harness가 무거워질 수 있다.

---

## 5. 후속 Spec에서 결정할 것

- Branch naming과 생성/재사용 규칙의 정확한 인터페이스
- Stage 승인 상태를 문서에 표시하는 형식
- Chat의 GitHub write 실패 및 재시도/재개 방식
- Branch head가 변경된 경우 충돌 감지와 사용자 알림
- Handoff reference의 템플릿·필수/선택 정보
- 공백 문서나 Stage 중단 시 처리
- trivial change의 경량 경로

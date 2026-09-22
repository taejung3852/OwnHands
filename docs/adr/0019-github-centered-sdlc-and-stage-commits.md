# ADR-0019: GitHub 중심 SDLC에서 Issue를 선택적으로 사용하고 승인된 Stage 산출물을 일괄 Commit한다

- **상태:** Accepted — 사용자 Spec 내용·저장 승인 / 구현 미진행
- **일자:** 2026-09-22
- **관련 Issue:** [#154](https://github.com/taejung3852/OwnHands/issues/154)
- **선행 결정:** [ADR-0011](0011-chat-codex-ownership-and-handoff.md), [ADR-0017](0017-guided-planning-and-visual-approval.md)
- **관련 Intent:** [Chat Plan & Design](../specs/chat-plan-design-flow/intent.md)
- **확정 Spec:** [Chat Plan & Design](../specs/chat-plan-design-flow/spec.md)
- **후속 변경:** Intent 단계의 Issue 필수·자동 생성 기본안을 사용자 결정으로 완화하고, 내용 승인과 저장 승인 및 Reconcile을 구체화했다.

---

## 1. Context

ADR-0011은 ChatGPT가 기획·설계를, Codex가 구현·검증을 담당하는 방향을 확정했지만 둘 사이의 지속 가능한 기준점과 승인 산출물 저장 경계는 남아 있었다.

사용자는 Chat이나 Codex 세션 자체보다 GitHub를 중심으로 SDLC가 돌아가는 구조를 선호한다. 동시에 Decision 하나가 생길 때마다 파일을 저장·커밋하면 Git history가 대화 로그처럼 잘게 쪼개지고, 어떤 커밋이 실제 승인된 Stage를 의미하는지 흐려질 수 있다.

Intent에서는 실제 개발 작업의 Issue 사용을 기본 필수로 정했으나, 후속 Spec에서 사용자는 Issue 없는 작업도 허용하고 Branch 전략은 먼저 사용자에게 묻도록 바꾸었다. 또한 수동 저장을 허용한 이상 재연결 때 자동 생성 순서를 재실행하면 이미 수행한 작업과 충돌할 수 있다.

---

## 2. Decision

### 2.1 GitHub 중심 SDLC

GitHub를 작업의 durable Source of Truth로 사용한다. GitHub Issue는 선택적인 추적 표면이지 필수 SDLC 단계가 아니다.

- Issue: 존재하거나 사용자가 선택한 경우의 Work Item·진행 연결점
- Intent: 목적·결과·경계
- Spec: 기술 계약·Acceptance Criteria
- ADR: 중요한 선택의 이유와 대안
- plan.md: Planned Flow의 승인된 구현·검증 실행 계획
- Commit: 승인 상태와 변경 이력
- PR: 생성하는 경우의 결과·Evidence·Human Gate

ChatGPT와 Codex는 각각 기획·설계와 구현·검증을 수행하는 인터페이스이며, 장기 상태의 기준은 GitHub에 저장된 산출물이다.

### 2.2 Issue와 Branch 선택

- 기존 관련 Issue가 명확하면 이를 사용한다. 명확한 연결 Branch가 하나 있으면 재사용한다.
- Branch 후보가 여러 개거나 의미가 애매하면 추측하지 않고 사용자에게 선택받는다.
- Issue가 없으면 자동으로 Issue나 Branch를 생성하지 않고 다음 세 경로를 제시한다.

```text
1. Issue 생성 → Issue 기반 Branch
2. Issue 없이 작업 Branch만 생성
3. 지금은 GitHub 작업 없이 기획·설계 계속
```

Issue 본문은 Intent/Spec 복제본이 아니라 작업의 존재·목표·현재 결정 지점을 보여주는 협업 표면이다. Issue 초안도 사용자가 Issue 경로를 선택한 경우에만 제공한다.

### 2.3 단일 작업 Branch

작업 Branch를 사용하는 경우 Intent부터 PR까지 같은 Branch를 이어서 사용한다. 기획 전용 Branch와 구현 Branch를 기본적으로 나누지 않는다.

이름 제안은 Issue가 있으면 `work/<issue-number>-<slug>`, 없으면 `work/<slug>`다. 명확한 기존 Branch를 이름 규칙 때문에 다시 만들거나 바꾸지 않는다. Issue가 없는 경우 Branch 전략은 사용자 결정 이후에 제안한다.

### 2.4 내용 승인과 저장 승인

각 Stage에서 내용 승인과 GitHub 저장 승인을 구분한다. 문서의 `Approved`는 내용 승인만 뜻한다.

```text
Intent 완성 → ELI5 → 내용 승인 → 별도 저장 승인
→ intent.md + 관련 ADR 일괄 Commit

Spec 완성 → ELI5 → 내용 승인 → 별도 저장 승인
→ spec.md + 관련 ADR 일괄 Commit
```

`Commit Boundary = Stage Approval Boundary`는 개별 Decision마다 저장하지 않는다는 묶음 원칙이다. 내용 승인이 외부 쓰기 승인까지 자동 포함한다는 뜻이 아니다.

미승인 Draft는 Chat에서 다룬다. Decision 하나마다 ADR 하나를 강제하지 않고 장기적으로 다시 볼 중요한 선택만 분리한다. GitHub 저장 전에 필요한 사용자 검수를 수행한다.

Codex의 승인된 구현 계획 보존과 경량 경로는 [ADR-0013](0013-build-planning-and-execution.md) 및 Spec REQ-25~32를 따른다. 외부 push·PR·Merge·Deploy 승인은 자동 승계하지 않는다.

### 2.5 Write 직전 Reconcile

- 저장 직전 최신 Branch HEAD와 대상 파일을 읽는다.
- HEAD가 전진해도 저장 대상과 충돌하지 않으면 최신 상태 위에서 저장한다.
- 같은 산출물이 바뀌었으면 차이를 보여주고 유지·적용·병합·취소를 사용자에게 선택받는다.
- 자동 overwrite, force push, 과거 상태가 맞다는 가정을 하지 않는다.
- 사용자가 수동으로 만든 Issue·Branch·Commit·산출물을 먼저 확인하고 이미 한 작업을 중복 생성하지 않는다.

GitHub가 다시 사용 가능해졌다는 이유로 Issue 생성 → Branch 생성 → 저장을 자동 실행하지 않는다. 다음 저장 요청·작업 재개 때 현재 상태부터 다시 읽고 필요한 변경에 대해 승인받는다.

### 2.6 GitHub 사용 불가 시 수동 경로

기획·설계 논의와 내용 승인은 계속할 수 있다. 현재 단계에 실제로 존재하는 Intent·Spec·관련 ADR, Handoff 텍스트와 수동 저장 가이드를 제공한다. Issue 초안은 선택 사항이다.

Chat에서는 `Intent 승인 완료 / GitHub 저장: 대기`처럼 내용과 저장 여부를 구분한다. 가짜 Issue 번호·존재하지 않는 Branch·Commit을 만들어내지 않는다. 문서의 `Approved`를 저장 성공 증거로 사용하지 않는다.

### 2.7 Handoff는 권장 진입 안내

Handoff는 전체 대화나 문서의 새로운 복제 Source of Truth가 아니다. 정상 경로에서는 작업별 handoff.md를 GitHub에 만들지 않고, Plugin의 `references/handoff-guide.md`에 작성법만 보존한다.

안내문에는 작업 맥락, 승인된 기준의 위치·역할, 확정 결정, 열린 사항, 권장 진입점이 이해될 만큼 담긴다. 고정 필드가 많은 Manifest를 강제하거나 강한 `Next Action`으로 구현 방식·Build 실행을 승인하지 않는다.

---

## 3. Alternatives

### Decision마다 즉시 Commit

기각. Git history가 대화 단위로 분절돼 Stage 승인 상태를 읽기 어려워진다.

### Draft부터 GitHub에 지속 저장

기본 경로로 채택하지 않는다. 수동 저장용 파일 제공과 승인된 Stage 저장으로 범위를 제한한다.

### 모든 개발 작업에 Issue 필수

Intent 단계에서는 선택했으나 Spec 논의에서 변경했다. 작은 개인 작업과 Issue 없는 작업도 지원하며, 관련 Issue가 없으면 사용자에게 경로를 묻는다.

### 내용 승인에 저장 권한 자동 포함

채택하지 않는다. 사용자는 저장 전에 검수할 기회를 원하므로 두 승인을 분리한다.

### 재연결 시 자동 Recovery

채택하지 않는다. 그 사이 사용자가 이미 수동 처리했을 수 있으므로 현재 상태 Reconcile로 대체한다.

### 기획 Branch와 구현 Branch 분리

기본 경로로 채택하지 않는다. 불필요한 인계·동기화 지점을 늘린다.

---

## 4. Consequences

- Git history에는 의미 있는 Stage 승인 산출물이 남고, 같은 작업 Branch에서 추적할 수 있다.
- Issue 없는 작업과 GitHub 연결 불가 시 수동 경로를 지원한다.
- 내용 승인과 저장 승인으로 사용자의 검수·외부 쓰기 통제권을 보존한다.
- 미저장 Draft는 세션 손실 시 복구되지 않을 수 있다. 수동 파일 제공을 저장 완료로 주장하지 않는다.
- 동시 수정과 수동 처리 결과를 재확인하는 비용이 추가된다. 읽을 수 없는 상태에서는 동기화 성공을 추측하지 않는다.
- 이 문서 저장은 실행 코드·Plugin·Hook·검증 동작의 변경 완료가 아니다.

## 5. 계약과 후속 범위

승인된 Spec의 2~7절과 REQ-25~32가 이번 동작 계약이다. 플랫폼 노출·호출·권한 확인은 Spec 15절에서 별도로 검증한다.

Verify/Review 전체 통합, Hook/Gate 제거, Feedback 재정렬, ELI5/Ponytail Codex 패키징 전체 계약과 새 CI는 Spec 12절에 따라 후속 Build로 분리한다.

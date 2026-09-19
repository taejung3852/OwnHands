# Intent: Thin build Skill 연결

- **작성자**: 박태정 (@taejung3852) & Codex
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Issue**: [#140](https://github.com/taejung3852/OwnHands/issues/140)
- **상위 마일스톤**: [V2-M3 — Build & Feedback Loop](https://github.com/taejung3852/OwnHands/milestone/16)

---

## 1. 문제 및 배경 (Why)

- **현재 상황과 고통**:
  - `ADR-0007`과 `docs/specs/README.md`에는 `plan.md`, Task Breakdown, 작업에 적합한 검증 전략, Fresh Evidence, 완료 전 `verify` 연결 원칙이 이미 확정돼 있다.
  - 그러나 승인된 `spec.md`와 `plan.md`를 바탕으로 Build를 시작할 때 이 원칙들을 실제 실행 순서로 연결하는 단일 진입점이 없다.
  - 이 공백 때문에 구현자가 기존 규약을 매번 수동으로 조합해야 하며, Task 단위 검증이나 완료 전 독립 검증이 누락될 수 있다.
- **대상 사용자 (페르소나)**:
  - 승인된 설계와 실행 계획을 기준으로 Codex와 함께 구현하며, 과도한 프레임워크 없이 일관된 Build 피드백 루프를 실행하려는 AI-Native 소프트웨어 엔지니어.

## 2. 목표 결과 및 가치 (What)

- **최상위 목표**:
  > **승인된 `spec.md`를 실제 동작하는 코드로 전환할 때, 기존 `plan.md`와 구현·검증 루프를 하나의 얇은 Build 진입점으로 연결하여 에이전트의 이탈과 근거 없는 완료 주장을 막는다.**
- **달성하고자 하는 결과**:
  - Build 시작 시 승인된 `spec.md`와 `plan.md`를 확인하고 Task 하나를 선택하는 단일 진입점을 제공한다.
  - 각 Task의 성격에 맞게 직접 구현, 필요한 경우의 TDD, 제한적인 Subagent 위임을 선택한다.
  - Task마다 적용 가능한 Fresh Evidence를 확보하고, 전체 완료 전 기존 `verify` Skill로 연결한다.
  - 이미 확정된 `plan.md`·검증 규약과 Codex 네이티브 기능을 재사용하는 Thin Harness로 끝낸다.
- **성공 기준**:
  - Build 단계의 단일 진입점이 정의된다.
  - 기존 `plan.md` 규약을 새 포맷 없이 재사용한다.
  - TDD는 적합한 Task에서만 사용한다.
  - Subagent는 외부 조사, 독립적으로 분리 가능한 큰 Task, 최종 독립 검증처럼 필요한 경우에만 고려한다.
  - 완료 흐름이 기존 `verify` Skill로 연결된다.
  - 추가 Runner나 Hook 없이 Skill과 필요한 최소 Reference 수준으로 완결된다.

## 3. 비목표 (Non-goals & Boundaries)

> ⚠️ **과잉 엔지니어링 방지**: 이번 작업에서 의도적으로 하지 않는 것

- [ ] Build CLI Runner 또는 별도 실행 엔진 제작
- [ ] Hook 시스템 및 Worktree 자동화
- [ ] 모든 Task의 Subagent 실행 강제 또는 Agent orchestration framework 제작
- [ ] 새로운 Verifier나 새로운 `plan.md` 포맷 제작
- [ ] 독자 TDD Framework 제작
- [ ] Superpowers 전체 복제
- [ ] 이미 확정된 ADR-0007/0008의 Build·검증 계약 재설계

## 4. 핵심 제약 조건 (Constraints)

- **규약 재사용**: `ADR-0007`, `ADR-0008`, `docs/specs/README.md`, 기존 `verify` Skill을 Source of Truth로 재사용한다.
- **Thin Harness**: `build`는 구현을 대신하는 프레임워크가 아니라 기존 실행 규약을 순서대로 연결하는 얇은 오케스트레이터여야 한다.
- **직접 수행 기본값**: 기본은 현재 Builder가 직접 수행하며, Task마다 fresh subagent를 강제로 띄우지 않는다.
- **조건부 TDD**: 실행 가능한 로직처럼 TDD가 적합한 Task에만 `Red → Green → Refactor`를 적용한다.
- **명시적 경계**: 구현 중 스펙 충돌이나 새 제약이 발견되면 자의적으로 기준을 바꾸지 않고, 기존의 `spec.md` 수정 및 사람 승인 흐름으로 되돌아간다.
- **플랫폼 우선**: Codex가 제공하는 네이티브 실행·검토·위임 기능을 재구현하지 않는다.

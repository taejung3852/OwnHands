# ADR-0013: Build가 구현 계획 준비와 실행을 하나의 흐름으로 맡는다

- 상태: Accepted — Build 진입·Light/Planned Flow Spec 사용자 승인 / 구현 미진행
- 일자: 2026-09-22
- 관련: [#154](https://github.com/taejung3852/OwnHands/issues/154), 피드백 5·6·7
- 조정 대상: [ADR-0007](0007-plan-artifact-and-build-feedback-loop.md)
- 확정 Spec: [Chat Plan & Design](../specs/chat-plan-design-flow/spec.md), REQ-25~32
- 후속 범위: Verify/Review 통합, Hook/Gate 제거 등은 이번 작업에 포함하지 않는다.

## Context

사용자 보고에서는 Codex Plan Mode로 계획을 확정했지만 plan.md가 자동으로 저장되지 않았다. 기존 Build는 이미 승인된 Spec/Plan을 요구하므로 구현 계획 작성·파일 저장·Build 시작이 별개 작업처럼 느껴졌다.

SDLC의 Plan은 목적을 정하는 기획 단계다. Codex Plan Mode는 승인된 설계를 구현 순서로 바꾸는 Build 준비 환경이다. 같은 Plan이라는 말로 두 단계를 혼동하지 않는다.

후속 Spec에서 사용자는 작은 명확한 작업도 동일한 `$build` 진입점을 사용하되, 불필요한 Plan Mode·plan.md 생성을 강제하지 않기로 했다. 구현 계획 필요 여부는 Build가 판단하고 실제 모드 전환은 사용자에게 안내한다.

## 사용자 확정 방향

1. 기획·설계가 필요한 작업은 Chat의 승인된 Intent·Spec을 읽고 Codex에서 Build Skill을 사용한다. 이미 요구와 수정 범위가 명확한 작은 작업은 Chat을 생략하고 `$build`에서 시작할 수 있다.
2. `$build`는 Light Flow와 Planned Flow를 나눈다. 고정된 변경 파일 개수 대신 의미 있는 구현 대안, 연결된 컴포넌트·인터페이스, 변경 순서, migration, 실패 영향과 미결정 선택을 기준으로 판단한다.
3. Planned Flow의 준비 단계는 실제 Codex native Plan Mode에서 구현 순서·변경 파일·인터페이스·검증 방법을 정한다.
4. Build는 Plan Mode로 전환한 척하지 않는다. 필요 시 사용자에게 `/plan` 또는 `Shift+Tab` 전환을 안내한다. 해당 호스트의 실제 UI 동작은 구현 시 확인한다.
5. 계획에 대한 사용자 승인 후 쓰기 가능한 모드를 확인하고, 승인 내용을 plan.md로 보존한 뒤 구현으로 이어간다. 계획 파일 저장을 별도로 반복 지시하는 흐름을 만들지 않는다.
6. plan.md는 실행 가능한 승인 계획의 영구 산출물이며 Plan Mode를 흉내 내는 대체 기능이 아니다.

## 모드와 저장 경계

```text
Light Flow
명확하고 저위험인 요청 → 구현 → applicable Fresh Evidence → Verify Summary

Planned Flow
승인된 작업 기준 확인 → 사용자에게 실제 Plan Mode 전환 안내
→ 구현 계획 논의 → 사용자 승인
→ 쓰기 가능한 모드 확인 → plan.md 보존
→ 저장 내용·승인 기준 확인 → Task 실행 → Fresh Evidence → Verify
```

Plan Mode가 파일 변경을 금지하는 환경에서는 Skill이 이를 우회해서 파일을 저장하지 않는다. 직접 전환할 수 없으면 사용자에게 모드 전환을 요청하고 준비 상태를 보존한다. 승인이 없는 계획이나 모드 전환을 수행한 척하는 설명은 허용하지 않는다.

plan.md의 로컬 보존은 무단 GitHub push·PR·Merge·Deploy 승인이 아니다. Chat에서 전달받은 Handoff도 Build 실행 승인이 아니라 권장 진입점이다.

## 계획 내용에 대한 기준

- 파일 경로뿐 아니라 입력, 기대 동작, 실패 조건, 검증 명령·관측 방법을 구체화한다.
- Task 경계는 독립적으로 확인할 수 있는 결과를 기준으로 한다. 임의의 시간 상한 때문에 모든 Task를 과도하게 쪼개지 않는다.
- 새 구현자가 중요한 제품 결정을 다시 추측해야 하는 부분을 남기지 않는다. 모든 코드 한 줄을 계획에 복제하는 의무는 이번 결정에 포함하지 않는다.
- 기존에 승인된 계획이 있으면 재인터뷰·재작성부터 시작하지 않는다. 유효성과 변경 여부만 확인한다.

## Light Flow의 Evidence

- 작은 작업을 위해 plan.md 또는 verification.md를 억지로 생성하지 않는다.
- Verify는 현재 요청·diff·실행한 native checks를 근거로 Verification Summary를 반환한다.
- PR이 없으면 세션에서 사용자에게 완료 근거를 제공한다. PR을 생성한다면 검증 결과를 PR 본문에 투영하며 별도 verification.md는 만들지 않는다.
- 승인된 Spec REQ-32에 따라 Light Flow에는 독립 Verifier를 기본 강제하지 않는다. 이는 실제 검증 생략이나 PASS 추측을 허용하지 않는다.
- 변경 반경 증가, 중요한 인터페이스 변경, 요구 모호성, 고위험 데이터·권한·migration 영향, deterministic check로 판단하기 어려운 상황을 발견하면 Heavy/Planned Flow로 승격한다.

## 결과와 적용 범위

Build가 계획 준비까지 소유하지만 별도 자율 기획 모델이나 독립 검사자를 겸하는 Agent로 확장하지 않는다. 승인된 설계·실제 검증·사용자 통제는 유지한다.

이번에는 Build 진입과 경량 검증 경로에 필요한 최소 계약을 정렬한다. [ADR-0014](0014-single-independent-verification.md)의 Verify/Review 전체 통합, [ADR-0015](0015-defer-automatic-ci-and-hook-enforcement.md)의 Hook/Gate 제거 및 다른 후속 재정렬은 별도 Build다. 기존 실행 자산이 이미 변경됐다고 주장하지 않는다.

## 기술 확인

Spec 15절의 Plan Mode UI/호스트 동작을 확인하고, 구현 시 실제 저장 실패·모드 제한을 정직하게 보고한다. 과거 승인 계획을 무조건 다시 작성하게 하지 않는다.

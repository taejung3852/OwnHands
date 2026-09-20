---
name: build
description: Executes approved spec.md and plan.md one task at a time, gathers fresh evidence, and hands completion to verify. Use when implementing from approved OwnHands specs/plans or explicitly invoked as $build.
---

# build

승인된 설계와 실행 계획을 실제 구현과 Fresh Evidence 확보로 연결하는 얇은 Build 진입점이다.

## 작업 절차

1. 대상 `spec.md`와 `plan.md`를 찾고 상호 링크, 승인 상태, Target Files를 확인한다. 누락되거나 미승인이면 수정하지 않고 해당 Checkpoint로 돌아간다.
2. `plan.md`에서 다음 미완료 Task 하나와 연결된 AC·검증 전략을 선택한다.
3. 실행 방식을 고른다.
   - 실행 가능한 로직이고 계획이 TDD를 지정하면 `references/tdd-loop.md`를 읽는다.
   - 위임 이점이 명확할 때만 `references/subagent-routing.md`를 읽는다.
   - 그 외에는 현재 Builder가 직접 수행한다.
4. Target Files 안에서 Task를 구현하고 적용 가능한 Fresh Evidence를 `plan.md`에 기록한다. 증거를 확인한 뒤에만 다음 Task로 이동한다.
5. 모든 구현 Task와 applicable Fresh Evidence 기록이 끝나면 기존 `verify` Skill로 인계한다. AC 판정, Reviewer 호출, Review Evidence, Human Gate는 Build가 수행하지 않는다.

## 중단 조건

- Spec 충돌이나 새 제약 발견: 구현을 멈추고 `spec.md` 수정·사람 승인·`plan.md` 재정렬로 돌아간다.
- Target Files 밖 변경 필요: 무단 수정하지 않고 먼저 계획 범위를 갱신한다.
- 구현 증거 실패 또는 미실행: `FAIL` 또는 `UNOBSERVED`로 기록하며 완료로 취급하지 않는다.

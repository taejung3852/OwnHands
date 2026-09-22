# ADR-0014: Verify Skill과 단일 독립 Verifier 중심의 검증 통합

- 상태: 사용자 통합 방향 확정 — 검사·결과·인계 상세 미결정 / 구현 미진행
- 일자: 2026-09-22
- 관련: [#154](https://github.com/taejung3852/OwnHands/issues/154), 피드백 7·8
- 조정 대상: [ADR-0001](0001-initial-subagent-roles.md), [ADR-0008](0008-verification-references-and-verifier-protocol.md), [ADR-0010](0010-review-human-ci-governance.md)

## Context

실사용에서 Verifier와 Reviewer가 같은 Spec·Plan·Evidence를 반복해서 읽고 구현을 검사하는 단계로 느껴졌다. 사용자는 실행 경계가 명확히 다른 작업만 Skill/Agent로 분리한다는 원칙에 따라 단일 Verifier를 선호했다.

이 관측은 분리된 검사자가 항상 무의미하다는 보편적 증거는 아니다. 현재 OwnHands의 비용·UX와 역할 경계를 단순화하려는 결정이다.

## 사용자 확정 방향

- 별도 verify/review Process Skill과 verifier/reviewer의 연속 호출 대신 Verify Skill·독립 Verifier 중심으로 통합한다.
- 메인 Builder와 독립 검사자의 컨텍스트·책임은 분리한다.
- Reviewer 이름을 없앤다는 이유로 중요한 최종 변경 위험 검사를 제거하지 않는다.
- 실제 검증과 실행 근거, 최종 사용자 판단은 유지한다. 자동 Hook 강제 장치는 [ADR-0015](0015-defer-automatic-ci-and-hook-enforcement.md)에 따라 별도로 걷어낸다.

## 결과 계약 제안

하나의 독립 검사 결과 안에 다음 두 관점을 구분한다.

| 관점 | 질문 | 제안 출력 |
|---|---|---|
| 요구 충족 | Spec의 각 AC를 실제 Evidence가 입증하는가? | PASS / FAIL / UNOBSERVED와 근거 |
| 중요한 변경 위험 | 최종 변경이 회귀·보안·데이터 손실·명백한 동작 파괴를 만드는가? | 우선순위·위치·근거가 있는 Finding |

검사자는 소스 수정 대신 결과를 돌려주고, 메인이 근거에 따라 수용·기각·사용자 판단 필요를 구분한다. 보완 뒤 필요한 범위의 증거를 갱신한다. 똑같은 전체 검사를 이유 없이 반복하지 않는다.

위 표의 정확한 필드와 판정 집계 방식은 후속 Spec 제안이며 아직 런타임 계약을 변경한 것은 아니다.

## 기존 역할의 처리

단순히 reviewer.toml을 삭제하지 않는다. review Skill의 Finding 처리, Evidence와 대상 변경의 관계, 사람 승인 안내 중 유지할 책임을 확인하고 이관한다. 기존 fingerprint 스크립트·Hook을 그대로 새 이름으로 옮겨 강제 장치를 보존하는 것은 제거 결정과 다르다.

## 비용과 검증 한계

이 통합으로 비용이 줄어들 것이라는 기대는 있으나 측정하지 않았다. 두 단계가 다른 결함을 찾는지에 대한 통제 비교도 이번 기록에서는 수행하지 않았다. 이미 나온 Astra/high 비용 피드백은 후속 모델 정책 후보로 보존하며, 이번 ADR로 새 모델명이나 effort를 임의 고정하지 않는다.

## 미결정 상세

독립 검사자가 직접 재실행할 검사와 기존 증거를 감사할 검사, 작은 작업의 경량 경로, 재검증 중단 조건, 최종 결과 저장 위치·형식, 모델 정책은 후속 설계 대상이다.

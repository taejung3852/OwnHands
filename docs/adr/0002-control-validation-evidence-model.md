# ADR-0002 — Control Validation과 Evidence Basis 분리

- **상태:** Accepted — 사용자 승인
- **일자:** 2026-09-04
- **관련 Issue:** [M0-03](https://github.com/taejung3852/devharness/issues/3), [M0-04](https://github.com/taejung3852/devharness/issues/4)

## Context

기존 문서는 `Configured`, `Loaded`, `Enforced`, `Observed`, `Inferred`, `Unobserved`를 Evidence State 목록으로 함께 제시한다. 그러나 앞의 세 값은 통제의 실현 단계를, 뒤의 세 값은 결론을 얻은 근거 방식을 설명한다. 하나의 enum으로 만들면 “집행됨(Enforced)을 직접 관찰함(Observed)”을 동시에 표현할 수 없고, 파일 존재가 로딩·집행으로 자동 승격될 위험이 있다.

## Decision

단일 `control_state`를 사용하지 않는다.

각 Control Validation record는 `configured`, `loaded`, `enforced`를 **독립 check**로 가진다. 각 check에는 다음을 기록한다.

Record identity에는 instance `control_id`, Matrix selector용 `control_type`, `project_id`·`worktree_id`·`task_id`·`environment_ref` scope를 모두 기록한다. Task Guarantee 판정은 같은 `control_type`과 동일 scope의 canonical record 전체를 사용한다.

- `result`: `pass | fail | not_run | not_applicable`
- `basis`: `observed | inferred | unobserved`
- `evidence_refs`와 `inference_from`
- 정확한 검증 범위, 검증 시각, 남은 위험

`Configured → Loaded → Enforced`는 자동 승격하지 않는다. 어떤 claim이 `Enforced`만 요구하더라도 다른 check를 추정으로 채우지 않는다.

규칙은 다음과 같다.

1. `pass`와 `fail`은 `observed` 또는 `inferred` 근거가 있어야 한다.
2. `observed`는 하나 이상의 직접 Evidence reference가 필요하다.
3. `inferred`는 추론 원천 record를 명시해야 한다.
4. `not_run`은 `unobserved`이며 Evidence가 없는 상태다.
5. `not_applicable`도 적용 불가 범위를 판정한 근거가 필요하다.
6. 같은 `record_id` 중복, 다른 Task/environment scope, Claim selector와 다른 `control_type`은 Guarantee support에 사용할 수 없다.

Append-only source는 개별 observation/evaluation record이며, 위 구조는 Task Guarantee Report와 Dashboard가 읽는 projection이다.

## Alternatives

| 대안 | 판단 |
|---|---|
| 두 축의 독립 check | **채택.** 제품 언어를 손실 없이 표현하고 자동 승격을 막음 |
| Evidence record만 저장하고 매번 계산 | 원본에는 적합하지만 UI/read model 규칙이 불명확해 단독 사용하지 않음 |
| Claim별 nullable checklist | Matrix 표시는 쉽지만 여러 claim이 같은 Probe를 재사용할 때 중복이 큼 |
| 여섯 값을 합친 단일 enum | 서로 다른 차원을 배타적으로 만들어 기각 |

## Consequences

- 한 Control을 `enforced=pass, basis=observed`로 정확히 표현할 수 있다.
- 파일 생성만 확인된 경우 `configured=pass` 외의 check는 `not_run/unobserved`로 남는다.
- record가 커지고 Dashboard projection 규칙이 필요하지만, 과장된 통제 주장을 구조적으로 차단한다.
- Imported Desktop Task는 과거 config, hook, approval, sandbox, pre-change test를 기본 `not_run/unobserved`로 둔다.

## Evidence

- [M0-03 Control Validation Coverage](../spikes/control-validation-coverage.md)
- [Control Validation JSON Schema](../product/control-validation.schema.json)
- [Control Validation Example](../product/control-validation.example.json)
- OpenAI 공식 문서는 config precedence와 trusted project 조건, Rules의 실험 상태, Hook의 fail-open 경로, App Server approval event 범위를 구분한다 ([Config](https://developers.openai.com/codex/config-basic), [Rules](https://developers.openai.com/codex/rules), [Hooks](https://developers.openai.com/codex/hooks), [App Server](https://developers.openai.com/codex/app-server)).

## Remaining limitation

이 구조가 통제 자체를 제공하지는 않는다. 각 check의 값은 version·환경·정확한 scope가 연결된 실제 Probe Evidence가 있을 때만 채울 수 있다.

## Approval record

2026-09-04 사용자가 제안안을 승인했다. 함께 승인된 OD-09에 따라 repository-specific runtime 집행 Probe는 M3 Hard Evidence Gate로 이관한다. 이 승인은 PR 검증·병합 전 M0 완료 주장이나 M1 구현 시작을 허가하지 않는다.

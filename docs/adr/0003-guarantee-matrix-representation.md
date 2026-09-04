# ADR-0003 — Guarantee Matrix와 Task Guarantee Report 표현

- **상태:** Accepted — 사용자 승인
- **일자:** 2026-09-04
- **관련 Issue:** [M0-04](https://github.com/taejung3852/devharness/issues/4)

## Context

DevHarness는 실제 Evidence가 있는 범위에서만 claim을 허용해야 한다. Guarantee Matrix는 주장 규칙표이고 Task Guarantee Report는 특정 작업의 결과표다. 두 산출물을 한 record에 누적하면 규칙 version과 작업 결과가 섞이고, 파일 존재가 loading/enforcement로 잘못 승격될 수 있다.

## Decision

1. Guarantee Matrix v1은 **JSON Schema-backed, versioned JSON 규칙표**로 유지한다.
2. 수용 기준은 claim 최소 개수가 아니라 `Control_layer.md`가 정의한 핵심 Claim 범주의 완전한 추적이다.
3. 각 Matrix claim은 적용 가능한 Task mode, 필요한 Control check, Evidence type/field, 허용 basis, 금지 표현, 남은 위험을 가진다. config/AGENTS/Rule/Hook/Sandbox/Approval 실행 보장은 Managed Task에만 적용한다.
4. Task Guarantee Report는 `managed | imported` Task mode와 Matrix version을 참조하고 requirement별 `result`, `basis`, Evidence/conflict reference, exact scope를 기록한다. 현재 mode에 적용되지 않는 claim은 `not_evaluated`로 두고 성공 문구를 만들지 않는다.
5. 판정은 `supported | contradicted | not_evaluated`로 분리한다. Dashboard의 `제한적 확인`은 좁은 scope의 supported claim과 남은 위험을 함께 보여 주는 presentation이며 별도 pass 상태가 아니다.
6. 필요한 requirement나 Control check의 관찰된 `fail`, 또는 상충 Evidence는 `contradicted`로 처리한다. Evidence 부족, `not_run`, `unobserved`, 허용되지 않은 basis는 `not_evaluated`로 fail-safe 처리한다.
7. `contradicted`와 `not_evaluated`에는 permitted claim 문구를 만들지 않는다.
8. Control 상태는 [ADR-0002](0002-control-validation-evidence-model.md)의 독립 check 구조를 사용하며 단일 enum을 두지 않는다.
9. Task requirement 결과에는 Dashboard의 Passed, Failed, Not Run, No Adequate Test, Inconclusive, Unknown을 보존하고, 이 중 `pass`만 claim support에 사용할 수 있다. Control 단계별 check의 좁은 결과 enum과 혼합하지 않는다.
10. JSON Schema는 독립 구조와 상태 의미를 검증하며 `claim_results`의 비어 있지 않음과 완전히 동일한 객체의 중복 금지를 구조적으로 검사한다. Matrix-aware gate는 JSON Schema의 `uniqueItems`에 의존하지 않고 Report 전체에서 `claim_id` 속성의 유일성과 동일 Claim의 verdict 일관성을 검사한다.
11. Matrix-aware gate는 현재 Matrix version·Claim 존재·Task mode·필수 requirement ID 집합·허용 basis·금지 문구를 대조한다. 필요한 Control에 연결된 모든 Validation record를 평가하며 observed fail이나 pass/fail 충돌은 `contradicted`, 불충분 상태는 `not_evaluated`로 처리한다.
12. Matrix의 `required_control_selectors`는 `control_type`, realization check, subject를 제공할 requirement ID를 묶는다. Gate는 requirement `subject_ref == control_id`, requirement `exact_scope == Control boundary == check exact_scope`, 동일 project/worktree/task/environment를 모두 만족하는 canonical Control record 전체를 선택하고 그 record ID 집합과 Report reference 집합이 정확히 같은지 검사한다. 다른 instance·scope·type과 누락·추가·중복 record는 거부한다.
13. `supported`의 `permitted_statement`는 Matrix의 좁은 `claim`과 정확히 같아야 한다. scope는 requirement `exact_scope`와 일치하고 Matrix residual risk를 모두 포함하며 전역·Claim별 금지 문구를 포함하지 않아야 한다. 동적 세부사항은 scope와 Evidence에서 표시한다.

## Alternatives

- **Markdown 표만 사용:** 사람이 읽기 쉽지만 자동 판정과 schema migration이 불명확해 기각한다. 문서 표는 생성 가능한 view로 남긴다.
- **Matrix와 작업 결과를 같은 표에 누적:** 규칙과 observation lifecycle이 섞여 기각한다.
- **단일 Evidence State enum:** 통제 단계와 근거 방식을 합쳐 기각한다.
- **코드 상수만 사용:** Dashboard·Issue·문서가 같은 계약을 참조하기 어렵고 변경 이력이 불투명해 기각한다.

## Consequences

- 문서 Claim 범주 누락을 set comparison으로 검사할 수 있다.
- Dashboard는 raw log를 재해석하지 않고 Task Guarantee Report를 표시할 수 있다.
- Matrix/schema version migration과 unknown type fail-safe 처리가 필요하다.
- JSON 자체가 Evidence의 진실성을 보장하지 않으므로 Event/Evidence reference 검증이 별도로 필요하다.

## Evidence

- [Guarantee Matrix v1 Spike](../spikes/guarantee-matrix-v1.md)
- [Guarantee Matrix v1](../product/guarantee-matrix.v1.json)
- [Matrix Schema](../product/guarantee-matrix.schema.json)
- [Task Report Schema](../product/task-guarantee-report.schema.json)
- [Task Report Example](../product/task-guarantee-report.example.json)
- [합성 Probe](../spikes/probes/m0-04-guarantee-matrix-probe.sh)는 전체 범주 추적, Task mode 적용성, 단일 enum 부재, 불충분/충돌 Evidence의 fail-safe 판정과 Matrix version·Claim·requirement ID·canonical Control closure의 Matrix-aware gate를 확인했다. 빈 `claim_results`, 같은 Claim ID의 동일/상이 객체 중복·verdict 충돌, 다른 Control type/Task/instance/boundary/check scope, 관련 failed record 생략, 중복 record ID, 전역 과장 문구·risk 누락을 포함한 필수 공격 경계 23종을 이름 집합으로 고정한다. 변경 전 실제 gate/schema의 RED와 수정 후 GREEN을 기록했고, 내용이 다른 동일 `claim_id` 객체는 schema만으로 검출하지 못한다는 positive check도 유지한다. Matrix, Control example, Task Report example은 pinned temporary validator로 strict-type/tuple draft 2020-12 schema 검증을 통과했다.

## Not decided here

- 사용자 Override record의 UI와 승인 권한
- M1 구현 언어와 runtime validator library

## Approval record

2026-09-04 사용자가 제안안을 승인했다. 이 승인은 PR 검증·병합 전 M0 완료 주장이나 M1 구현 시작을 허가하지 않는다.

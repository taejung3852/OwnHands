# M0-04 — Guarantee Matrix v1 Spike

**상태:** ADR 제안 근거. 실제 작업의 완료·안전·통제 상태를 주장하지 않는다.

**확인일:** 2026-09-04

**관련 기준선:** `Control_layer.md` 9–11장, `Dashboard_layer.md` 5.7장

## 결론

Guarantee Matrix는 versioned JSON 규칙표로, Task Guarantee Report는 작업별 JSON 결과표로 분리한다. Control 실현 단계와 Evidence 근거 방식은 [ADR-0002](../adr/0002-control-validation-evidence-model.md)의 독립 축을 사용한다.

수용 기준은 claim 개수가 아니다. `Control_layer.md` 초기 Matrix에 정의된 **핵심 Claim 범주 전체가 빠짐없이 1:1로 추적되는지**다. 현재 v1은 아래 16개 문서 범주 전체를 포함하지만, 16이라는 숫자를 향후 최소 개수 규칙으로 사용하지 않는다. 기준 문서가 바뀌면 coverage manifest와 Matrix를 함께 검토한다.

## 산출물

| 파일 | 역할 |
|---|---|
| `guarantee-matrix.v1.json` | claim, 필요한 Evidence, 필요한 Control check, 허용 basis, 금지 표현, 남은 위험 |
| `guarantee-matrix.schema.json` | Matrix 형식 계약 |
| `control-validation.schema.json` | Configured/Loaded/Enforced 독립 check와 basis 계약 |
| `task-guarantee-report.schema.json` | 작업별 판정 결과의 독립 구조·상태 의미 계약 |
| `task-guarantee-report.example.json` | supported/not-evaluated/contradicted 예시 |
| `guarantee-matrix-fixtures.json` | Matrix-aware 자동 Probe용 충분/불충분/충돌·금지 문구·Control 참조 합성 fixture |

## 문서 Claim 범주 추적

| Claim ID | 핵심 범주 | 적용 Task mode | Control check | 허용 basis |
|---|---|---|---|---|
| GM-001 | Control Profile 생성 | Managed, Imported | Configured | Observed |
| GM-002 | config 로드 | Managed | Loaded | Observed |
| GM-003 | AGENTS.md 지침 로드 | Managed | Loaded | Observed |
| GM-004 | Rule의 특정 probe 차단 | Managed | Enforced | Observed |
| GM-005 | 특정 event의 Hook 호출 | Managed | 없음 | Observed |
| GM-006 | Sandbox의 특정 경계 차단 | Managed | Enforced | Observed |
| GM-007 | 특정 행동에 Approval 적용 | Managed | Enforced | Observed |
| GM-008 | 설정 충돌 식별 | Managed, Imported | 없음 | Observed |
| GM-009 | 필요한 MCP Tool 호출 가능 | Managed, Imported | 없음 | Observed |
| GM-010 | Workspace Restore Point 생성 | Managed, Imported | 없음 | Observed |
| GM-011 | 실제 변경사항 식별 | Managed, Imported | 없음 | Observed |
| GM-012 | 연관 기능 분석 | Managed, Imported | 없음 | Observed 또는 Inferred |
| GM-013 | 관련 테스트 실행 | Managed, Imported | 없음 | Observed |
| GM-014 | 정의한 회귀 범위 통과 | Managed | 없음 | Observed |
| GM-015 | 기능 직접 검증 | Managed, Imported | 없음 | Observed |
| GM-016 | Dashboard 최신성 | Managed, Imported | 없음 | Observed |

`없음`은 검증이 필요 없다는 뜻이 아니다. Configured/Loaded/Enforced의 통제 단계가 아닌 직접 Evidence requirement로 판정한다는 뜻이다.

## 최종 schema 원칙

### Control Validation

각 Control record에는 `configured`, `loaded`, `enforced`가 모두 있고 각 check는 다음을 가진다.

```json
{
  "result": "pass | fail | not_run | not_applicable",
  "basis": "observed | inferred | unobserved",
  "evidence_refs": [],
  "inference_from": [],
  "exact_scope": "...",
  "checked_at": null,
  "residual_risks": []
}
```

`Observed`는 성공 상태가 아니라 근거 방식이다. `Enforced=pass`와 `basis=observed`를 함께 기록할 수 있다. 파일만 있으면 `configured=pass`일 수 있지만 `loaded`와 `enforced`는 `not_run/unobserved`로 남는다.

### Guarantee Matrix rule

각 claim은 다음을 정의한다.

- stable Claim ID와 문서 범주
- 적용 가능한 `managed | imported` Task mode
- 허용할 정확한 주장
- 필요한 Control realization check
- 필수 Evidence type과 field
- 허용 Evidence basis
- 금지 표현
- 확인 후에도 남는 위험

Matrix에는 작업 결과를 누적하지 않는다.

Dashboard의 일반 Verification Status는 Task Report의 requirement `result`로 보존한다. `pass`, `fail`, `not_run`, `no_adequate_test`, `inconclusive`, `unknown`을 각각 Passed, Failed, Not Run, No Adequate Test, Inconclusive, Unknown으로 표시한다. `not_applicable`은 claim applicability 근거가 있을 때만 사용한다. Control Validation의 단계별 check 결과는 더 좁은 `pass | fail | not_run | not_applicable` 계약이며 일반 Test Status와 혼합하지 않는다.

### Task Guarantee Report

각 작업에서 Matrix rule을 적용한 결과만 저장한다.

- report의 Task mode가 claim의 `applicable_task_modes`에 없으면 `not_evaluated`
- `supported`: 모든 필수 requirement와 필요한 Control check가 허용 basis로 pass하고 충돌 Evidence가 없음
- `contradicted`: required Evidence 또는 필요한 Control check에 관찰된 `fail`이 있거나 충돌 Evidence가 존재
- `not_evaluated`: Evidence 부족, `not_run`, `unobserved`, 허용되지 않은 basis 중 하나가 존재

`contradicted`와 `not_evaluated`에는 허용 주장 문구를 생성하지 않는다. Dashboard의 `제한적 확인`은 별도 verdict가 아니다. 정확히 좁혀 쓴 `supported` claim의 scope·남은 위험을 표시하거나, 관련 claim 일부가 `not_evaluated`임을 함께 보여 주는 presentation이다. 넓은 원 claim을 부분 pass로 바꾸지 않는다.

JSON Schema는 개별 Matrix rule을 읽지 않고도 확인 가능한 구조, 상태 조합, `supported`의 기본 fail-safe 의미를 검증한다. `claim_results`에는 `minItems: 1`과 `uniqueItems: true`를 적용해 빈 배열과 완전히 동일한 객체 중복을 구조 단계에서 거부한다. 다만 JSON Schema의 `uniqueItems`는 내용이 다른 객체의 같은 `claim_id`를 찾지 못하므로 이것만으로 유일성을 보장하지 않는다.

Matrix-aware gate는 Report의 `matrix_version`, `task.mode`, `claim_id`, claim별 requirement ID 집합, 허용 basis·금지 문구와 필요한 Control check를 현재 Matrix와 대조한다. Report 전체에서 `claim_results`가 비어 있지 않은지, `claim_id`가 속성 기준으로 유일한지, 같은 Claim에 서로 다른 verdict가 함께 있지 않은지도 별도로 검사한다. 필요한 Control에 연결된 Validation record를 모두 평가하며, 관찰된 `fail`이나 pass/fail 충돌은 `contradicted`, record 누락·`not_run`·허용되지 않은 basis는 `not_evaluated`로 판정한다.

## fail-safe 합성 Probe

실행:

```bash
docs/spikes/probes/m0-04-guarantee-matrix-probe.sh
```

2026-09-04 결과:

```text
json_syntax=passed
schema_empty_claim_results_rejected=passed
schema_exact_duplicate_claim_rejected=passed
core_category_coverage=passed
unique_claim_mapping=passed
unique_requirement_mapping=passed
task_mode_applicability=passed
single_control_state_absent=passed
independent_control_checks=passed
insufficient_evidence_fail_safe=passed
conflicting_evidence_fail_safe=passed
observed_control_failure_verdict=passed
task_report_wording_gate=passed
report_fixture_context=passed
required_control_resolution_gate=passed
verdict_swap_rejection=passed
matrix_version_gate=passed
claim_membership_gate=passed
requirement_id_gate=passed
all_control_records_gate=passed
pre_fix_fail_open_cases_rejected=7
report_envelope_fixtures_rejected=3
claim_results_nonempty_gate=passed
claim_id_uniqueness_gate=passed
claim_verdict_conflict_gate=passed
required_adversarial_fixture_coverage=12
adversarial_report_contract=passed
```

Probe는 다음을 확인했다.

1. 기준선의 핵심 범주 set과 Matrix 범주 set이 정확히 일치한다.
2. Claim ID와 범주가 중복되지 않는다.
3. 모든 claim에 Evidence, basis, 금지 표현, 남은 위험이 있다.
4. schema에 단일 `control_state`가 없다.
5. 파일 존재만 있고 active loading Evidence가 없으면 `not_evaluated`다.
6. pass log와 failure log가 충돌하면 `contradicted`다.
7. Imported Task에서 Managed-only claim은 모든 합성 check가 pass여도 `not_evaluated`다.
8. 관찰된 실패·충돌·빈 requirement·허용되지 않은 basis·금지 문구를 각각 독립시킨 adversarial report를 거부한다.
9. Matrix가 요구한 Control check를 참조하지 않거나 참조 record의 check가 pass하지 않으면 `supported`를 거부한다.
10. 관찰된 Control `fail` 또는 충돌 Evidence를 `not_evaluated`로, `not_run/unobserved`를 `contradicted`로 바꾼 report를 거부한다.
11. Report의 Matrix version 불일치, 알 수 없는 Claim, 필수 requirement ID의 누락·추가·중복을 거부한다.
12. Report의 Task mode를 claim 적용성 판정에 사용하여 Imported Task의 Managed-only claim을 `not_evaluated`로 제한한다.
13. 필요한 Control에 연결된 모든 Validation record를 평가하고 하나의 pass가 다른 observed fail이나 pass/fail 충돌을 가리지 못하게 한다.
14. Schema와 Matrix-aware gate 모두 빈 `claim_results`를 거부한다.
15. Schema는 완전히 동일한 Claim result 중복을 거부하고, gate는 객체의 다른 field와 무관하게 같은 `claim_id`를 거부한다.
16. 같은 Claim ID에 서로 다른 verdict를 함께 넣은 Report를 거부한다.
17. Report가 참조한 Control Validation ID가 실제 record로 해소되지 않으면 거부한다.

추가한 일곱 adversarial fixture의 RED/GREEN 결과는 다음과 같다. RED는 변경 전 gate에 fixture를 먼저 적용한 결과이며, `skipped fail-open`은 알 수 없는 Claim 조회가 빈 stream이 되어 상위 `all(...)` 검사를 통과한 경우다.

| Adversarial fixture | 변경 전 RED에서 관찰 | 변경 후 기대·결과 |
|---|---|---|
| Imported Task + Managed-only `supported` | 허용 | 거부 |
| 알 수 없는 Claim ID | skipped fail-open | 거부 |
| 불일치 Matrix version | 허용 | 거부 |
| 알 수 없는 requirement ID | 허용 | 거부 |
| 필수 requirement ID 누락 | 허용 | 거부 |
| requirement ID 중복 | 허용 | 거부 |
| 동일 Control의 pass/fail Validation record | 허용 | 거부 |

추가한 Report envelope 세 fixture의 RED/GREEN 결과는 다음과 같다. RED gate는 envelope 검사를 추가하기 전의 실제 Probe였고 세 fixture를 모두 허용했다. Schema RED는 `minItems`와 `uniqueItems`를 추가하기 전 schema를 같은 pinned Ajv로 검사한 결과로, 빈 배열과 완전히 동일한 객체 중복이 모두 `valid`였다.

| Adversarial fixture | 변경 전 RED에서 관찰 | 변경 후 기대·결과 |
|---|---|---|
| 빈 `claim_results` | gate 허용, schema `valid` | schema와 gate 모두 거부 |
| 완전히 동일한 Claim result 중복 | gate 허용, schema `valid` | schema와 gate 모두 거부 |
| 같은 Claim ID에 `supported`와 `contradicted` 동시 존재 | gate 허용; `uniqueItems`만으로는 서로 다른 객체라 식별 불가 | claim ID 유일성·verdict 일관성 gate가 거부 |

필수 공격 경계 12종은 이름 집합으로도 고정했다. 여기에는 위 세 envelope 사례와 Imported 적용성, 알 수 없는 Claim, Matrix version, requirement 누락·추가·중복, 해소되지 않는 Control 참조, Control record 순서로 숨겨지는 pass/fail 충돌, observed Control fail을 `supported`로 바꾸는 사례가 포함된다.

세 schema와 example은 pinned temporary `ajv-cli@5.0.0` + `ajv-formats@3.0.1`로 draft 2020-12 validation을 통과했고 `strict-types`/`strict-tuples` error나 warning은 없었다. 이 도구는 repository dependency로 추가하지 않았다.

실행 명령은 다음과 같다. 첫 실행은 pinned package를 받기 위한 network access가 필요할 수 있고, 이번 재검증은 이미 받은 cache에 `npx --offline`을 사용했다.

```bash
npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/guarantee-matrix.schema.json -d docs/product/guarantee-matrix.v1.json
npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/control-validation.schema.json -d docs/product/control-validation.example.json
npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true -c ajv-formats -s docs/product/task-guarantee-report.schema.json -d docs/product/task-guarantee-report.example.json
```

별도 adversarial copy에서 `supported` verdict에 failed requirement와 conflict를 넣으면 Task Report schema가 이를 거부하는 것도 확인했다. claim별 금지 문구·허용 basis·Control record 해석은 위 Matrix-aware Probe의 독립 fixture로 확인했다. 해당 임시 파일과 validator output은 검증 뒤 삭제했다.

합성 Probe와 일회성 schema 검증은 M1 runtime validator를 구현한 것이 아니다. 실제 Task Evidence와 runtime migration/unknown-type 동작은 **Unobserved**다.

## Open Decision과 후속 Gate

1. 사용자 Override는 claim verdict를 pass로 바꾸지 않고 별도 decision record로 저장한다.
2. schema migration, unknown Matrix version, unknown Evidence type은 fail-safe로 판정을 중단해야 한다.
3. Dashboard wording은 `permitted_statement`, exact scope, residual risk를 한 묶음으로 표시해야 한다.
4. M1 runtime JSON Schema validator와 property-based/fault fixture는 구현 수용 기준에 포함한다.

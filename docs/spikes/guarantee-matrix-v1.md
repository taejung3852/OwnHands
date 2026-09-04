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
| `task-guarantee-report.schema.json` | 작업별 판정 결과 형식 |
| `task-guarantee-report.example.json` | supported/not-evaluated/contradicted 예시 |
| `guarantee-matrix-fixtures.json` | 자동 Probe용 충분/불충분/충돌 합성 fixture |

## 문서 Claim 범주 추적

| Claim ID | 핵심 범주 | Control check | 허용 basis |
|---|---|---|---|
| GM-001 | Control Profile 생성 | Configured | Observed |
| GM-002 | config 로드 | Loaded | Observed |
| GM-003 | AGENTS.md 지침 로드 | Loaded | Observed |
| GM-004 | Rule의 특정 probe 차단 | Enforced | Observed |
| GM-005 | 특정 event의 Hook 호출 | 없음 | Observed |
| GM-006 | Sandbox의 특정 경계 차단 | Enforced | Observed |
| GM-007 | 특정 행동에 Approval 적용 | Enforced | Observed |
| GM-008 | 설정 충돌 식별 | 없음 | Observed |
| GM-009 | 필요한 MCP Tool 호출 가능 | 없음 | Observed |
| GM-010 | Workspace Restore Point 생성 | 없음 | Observed |
| GM-011 | 실제 변경사항 식별 | 없음 | Observed |
| GM-012 | 연관 기능 분석 | 없음 | Observed 또는 Inferred |
| GM-013 | 관련 테스트 실행 | 없음 | Observed |
| GM-014 | 정의한 회귀 범위 통과 | 없음 | Observed |
| GM-015 | 기능 직접 검증 | 없음 | Observed |
| GM-016 | Dashboard 최신성 | 없음 | Observed |

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

- `supported`: 모든 필수 requirement와 필요한 Control check가 허용 basis로 pass하고 충돌 Evidence가 없음
- `contradicted`: required Evidence 또는 Control check가 fail이거나 충돌 Evidence가 존재
- `not_evaluated`: Evidence 부족, `not_run`, `unobserved`, 허용되지 않은 basis 중 하나가 존재

`contradicted`와 `not_evaluated`에는 허용 주장 문구를 생성하지 않는다. Dashboard의 `제한적 확인`은 별도 verdict가 아니다. 정확히 좁혀 쓴 `supported` claim의 scope·남은 위험을 표시하거나, 관련 claim 일부가 `not_evaluated`임을 함께 보여 주는 presentation이다. 넓은 원 claim을 부분 pass로 바꾸지 않는다.

## fail-safe 합성 Probe

실행:

```bash
docs/spikes/probes/m0-04-guarantee-matrix-probe.sh
```

2026-09-04 결과:

```text
json_syntax=passed
core_category_coverage=passed
unique_claim_mapping=passed
single_control_state_absent=passed
independent_control_checks=passed
insufficient_evidence_fail_safe=passed
conflicting_evidence_fail_safe=passed
task_report_wording_gate=passed
```

Probe는 다음을 확인했다.

1. 기준선의 핵심 범주 set과 Matrix 범주 set이 정확히 일치한다.
2. Claim ID와 범주가 중복되지 않는다.
3. 모든 claim에 Evidence, basis, 금지 표현, 남은 위험이 있다.
4. schema에 단일 `control_state`가 없다.
5. 파일 존재만 있고 active loading Evidence가 없으면 `not_evaluated`다.
6. pass log와 failure log가 충돌하면 `contradicted`다.

이 Probe는 M1 판정 엔진의 구현이나 JSON Schema validator를 대체하지 않는다. 합성 fixture의 결정 규칙을 검증했을 뿐이며 실제 Task Evidence는 **Unobserved**다.

## Open Decision과 후속 Gate

1. 사용자 Override는 claim verdict를 pass로 바꾸지 않고 별도 decision record로 저장한다.
2. schema migration, unknown Matrix version, unknown Evidence type은 fail-safe로 판정을 중단해야 한다.
3. Dashboard wording은 `permitted_statement`, exact scope, residual risk를 한 묶음으로 표시해야 한다.
4. 실제 JSON Schema validator와 property-based/fault fixture는 M1 구현 수용 기준에 포함한다.

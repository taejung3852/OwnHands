# Conflict and Open Decisions

## 결정 기록

| ID | 문제 | 결정 | 상태 | 근거 |
|---|---|---|---|---|
| OD-01 | M0 종료 Gate에 Event/Evidence 저장 결정이 있으나 담당 Issue가 없었음 | M0-06을 필수 Issue로 추가 | 사용자 승인 | 2026-09-04 M0 조건부 승인 |
| OD-02 | Configured/Loaded/Enforced와 Observed/Inferred/Unobserved가 단일 상태 목록으로 섞일 수 있음 | 통제 실현과 Evidence 근거를 분리하고, 각 단계별 `result`와 `basis`를 갖는 독립 check schema를 제안 | ADR 제안, 사용자 검토 대기 | ADR-0002, M0-03/M0-04 |
| OD-03 | Preflight Test Design과 완료 후 Impact Analysis, M4 구현 순서가 모호함 | M2의 Impact Hypothesis/Test Design Intent와 M4의 Actual Impact Analysis/Test Design Memo/Regression Gate를 구분 | ADR 제안, 사용자 검토 대기 | ADR-0006 |
| OD-04 | Dashboard가 동등한 핵심 축이지만 전체 UI는 M5에 집중됨 | M1~M4는 실제 Evidence 기반 reviewable packet/report를 남기고 M5에서 동일 schema를 통합 UX로 완성 | ADR 제안, 사용자 검토 대기 | ADR-0006 |
| OD-05 | Dashboard 예시의 범위 없는 `회귀가 없음` 표현 | `정의한 회귀 범위에서 통과`로 수정 | 반영됨 | Guarantee 금지 표현 원칙 |
| OD-06 | M0-05가 필수 목록과 M0 Gate에 동시에 있어 blocking 여부가 모호함 | M0-05는 Non-blocking. M0에서 include/exclude 원칙, license, namespace, upstream pin만 결정하고 실제 vendoring은 수행하지 않음 | 사용자 승인 | 2026-09-04 M0 조건부 승인 |
| OD-07 | Dashboard가 핵심 축이지만 M5 전에 브랜드·정보 위계·접근성 기준이 없었음 | M0-07을 M0 Non-blocking / M5 필수 승인 Gate로 추가하고, 동일 Fixture 3안 중 A Signal Graphite를 추천 | ADR 제안, 사용자 검토 대기 | ADR-0007, Issue #8 |

## 아직 필요한 사용자 결정

| ID | 결정 대상 | 제출물 | 결정 전 제한 |
|---|---|---|---|
| OD-02-SCHEMA | Control 검증 결과와 Evidence 근거의 최종 schema 승인 | ADR-0002, ADR-0003 | M1 evaluator와 저장 schema 구현 금지 |
| OD-03-SEQUENCE | Preflight와 Postflight Assurance의 2단계 계약 승인 | ADR-0006 | M2/M4 관련 구현 금지 |
| OD-04-VERTICAL | M1~M4 최소 reviewable artifact 범위 승인 | ADR-0006 | M1 이후 구현 금지 |
| M0-ADR-GATE | M0 ADR 묶음 승인 | M0 종료 보고 | M1 기능 구현 금지 |
| OD-07-BRAND | M5 Brand·Dashboard 디자인 기준 승인 | ADR-0007, M0-07 시안·평가 | M1~M4는 진행 가능하나 M5 Production Dashboard 구현 금지 |

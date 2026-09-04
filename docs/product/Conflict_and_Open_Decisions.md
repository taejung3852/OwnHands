# Conflict and Open Decisions

## 결정 기록

| ID | 문제 | 결정 | 상태 | 근거 |
|---|---|---|---|---|
| OD-01 | M0 종료 Gate에 Event/Evidence 저장 결정이 있으나 담당 Issue가 없었음 | M0-06을 필수 Issue로 추가 | 사용자 승인 | 2026-09-04 M0 조건부 승인 |
| OD-02 | Configured/Loaded/Enforced와 Observed/Inferred/Unobserved가 단일 상태 목록으로 섞일 수 있음 | 통제 실현과 Evidence 근거를 분리하고, 각 단계별 `result`와 `basis`를 갖는 독립 check schema를 사용 | 사용자 승인 | ADR-0002, 2026-09-04 사용자 결정 |
| OD-03 | Preflight Test Design과 완료 후 Impact Analysis, M4 구현 순서가 모호함 | M2의 Impact Hypothesis/Test Design Intent와 M4의 Actual Impact Analysis/Test Design Memo/Regression Gate를 구분 | 사용자 승인 | ADR-0006, 2026-09-04 사용자 결정 |
| OD-04 | Dashboard가 동등한 핵심 축이지만 전체 UI는 M5에 집중됨 | M1~M4는 실제 Evidence 기반 reviewable packet/report를 남기고 M5에서 동일 schema를 통합 UX로 완성 | 사용자 승인 | ADR-0006, 2026-09-04 사용자 결정 |
| OD-05 | Dashboard 예시의 범위 없는 `회귀가 없음` 표현 | `정의한 회귀 범위에서 통과`로 수정 | 반영됨 | Guarantee 금지 표현 원칙 |
| OD-06 | M0-05가 필수 목록과 M0 Gate에 동시에 있어 blocking 여부가 모호함 | M0-05는 Non-blocking. M0에서 include/exclude 원칙, license, namespace, upstream pin만 결정하고 실제 vendoring은 수행하지 않음 | 사용자 승인 | 2026-09-04 M0 조건부 승인 |
| OD-07 | Dashboard가 핵심 축이지만 M5 전에 브랜드·정보 위계·접근성 기준이 없었음 | M0에서는 B — Warm Paper Neutral + Ledger Indigo 색상 방향만 확정. 현재 화면·글쓰기·상호작용은 참고 시안으로 보존하고 M5에서 이어서 설계 | 색상 범위 사용자 승인, M5 UI/UX 결정 대기 | ADR-0007, Issue #8, 2026-09-04 사용자 결정 |
| OD-08 | Roadmap의 일반 규칙은 Issue별 PR을 요구하지만 현재 M0 실행 지시는 M0-01~07을 하나의 응집된 baseline PR로 제출하도록 요구함 | 더 최신의 사용자 지시를 우선해 이번 M0만 하나의 baseline PR로 준비하고, 이후 Milestone은 기존 Issue별 PR 규칙을 유지 | 현재 M0 사용자 지시 반영 | 2026-09-04 goal objective, 제품 기준선 해석 우선순위 |
| OD-09 | M0-02/03 Issue는 disposable task의 thread/turn·Hook·Approval·Control runtime Evidence를 요구하지만 현재 안전한 비Task Probe는 capability/schema까지만 관찰했고, 실제 동작은 M3 Hard Evidence Gate로 문서화돼 있음 | M0는 공식 문서·비Task capability Evidence와 명시적 `Unobserved` 경계로 판단하고, task runtime·집행 Probe는 M3 Hard Evidence Gate로 이관 | 사용자 승인 | Issue #2/#3 수용 기준, ADR-0001/0002, M0-02/03 Spike, 2026-09-04 사용자 결정 |
| OD-10 | M0 Control Validation schema의 `control_type`은 Hook, Context source, MCP capability, Test/Assurance Evidence를 하나의 완성된 taxonomy로 표현하지 못함 | M1 Evaluator는 M0 schema의 여섯 type을 호환 경계로만 사용한다. Hook·MCP·Test는 Matrix Evidence type으로 평가하고 임의의 새 `control_type`을 추가하지 않는다. Context와 결정적 실행 통제의 최종 분리는 M1.5 Task Harness Manifest ADR에서 결정한다. | M1.5 ADR 전 Open Decision | Issue #14, #16~#21, 최신 phase/gate 지시 |

## 아직 필요한 사용자 결정

| ID | 결정 대상 | 책임자 | 결정 시점 | 제출물 | 결정 전 제한 |
|---|---|---|---|---|---|
| OD-07-UX | B 색상 방향 위에서 정보 위계·글쓰기·상호작용·component 계약 승인 | 사용자 | M5 Production Dashboard 시작 전 | ADR-0007, M0-07 참고 시안·평가 | 선행 Milestone Gate와 별개로 M5 Production Dashboard 구현 금지 |
| OD-10-MANIFEST | `Task Harness Manifest`의 `context_sources`/`control_sources`, `instruction_overlay`/`control_overlay` 계약과 Context 적용성 판정 | 사용자 | M1.5 검토 패키지 완료 뒤, M2 Production 구현 전 | M1.5 Proposed ADR, schema, lint/applicability Probe, A/B/C 비교 | M1 완료와 M1.5 Spike는 진행 가능하나 M2 Production Compiler·실제 Context 생성 금지 |

## 남은 진행 Gate

- 단일 M0 PR의 검증과 병합 전에는 M0 완료 또는 Issue 종료를 주장하지 않는다.
- Issue는 PR 병합과 수용 기준 재확인 뒤 별도 상태 변경한다.
- M1 완료·병합 뒤 M1.5 #16~#21을 수행한다. M1.5 ADR은 사용자 승인 전 `Proposed`이며, 승인 전에는 M2 Production Compiler나 실제 Context 생성 구현을 시작하지 않는다.

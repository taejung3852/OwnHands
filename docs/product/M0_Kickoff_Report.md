# M0 착수 보고서

- 기준일: 2026-09-04
- 상태: M0 승인 및 착수
- M1 이후 기능 코드: M0 ADR 검토 전 착수 금지

## 승인 반영 사항

| 항목 | 반영 결과 |
|---|---|
| M0-06 | 필수 M0 Issue로 추가 |
| Evidence 모델 | 통제 실현과 Evidence 근거를 분리하되 최종 schema는 M0-03/M0-04 ADR에서 비교 |
| M0-05 | Non-blocking, 실제 vendoring 제외 |
| Guarantee Matrix | 최소 Claim 개수 대신 문서의 핵심 Claim 범주 전체 coverage 적용 |
| 예상 소요 | 제거 |
| M0-07 | M1~M4 Non-blocking, B 색상 방향 승인·M5 UI/UX 필수 Gate로 분리 |

## M0 필수 산출물

| Issue | 산출물 | M0 Gate |
|---|---|---|
| M0-01 | 제품 기준선, 용어집, 추적표, 충돌 기록 | 필수 |
| M0-02 | Codex Desktop Integration Spike와 ADR | 필수 |
| M0-03 | Control Validation Coverage와 schema 비교 ADR | 필수 |
| M0-04 | Guarantee Matrix v1과 Task Guarantee Report 예시 | 필수 |
| M0-05 | Vendoring 원칙, license, namespace, upstream pin | Non-blocking |
| M0-06 | Event & Evidence Store Spike와 ADR | 필수 |
| M0-07 | Brand & Dashboard Design Foundation 조사·3안·Light/Dark 시안·접근성 Probe·ADR | B 색상 승인 / M5 UI/UX 필수 Gate |

## 외부 변경 승인 범위

| 대상 | 승인 내용 |
|---|---|
| GitHub Repository | `taejung3852/devharness`, Private |
| Default branch | `main` |
| 최초 Push | 네 제품 문서 기준선만 |
| GitHub 관리 객체 | M0~M8 Milestone, 승인된 Label, 전체 범위 상위 Issue, M0-01~M0-07 |
| 미승인 | 공개 전환, 배포, 패키지 게시 |

## 중단 조건

M0 ADR이 사용자 검토를 통과하기 전에는 M1 기능 구현을 시작하지 않는다. ADR-0007의 B 색상 방향은 승인됐지만, M5 UI/UX 별도 승인 전에는 Production Dashboard를 시작하지 않는다. 관찰되지 않은 Codex 동작이나 통제 경계는 `Unobserved`로 남긴다.

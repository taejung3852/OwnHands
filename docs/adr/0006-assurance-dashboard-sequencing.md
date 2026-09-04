# ADR-0006 — Assurance 2단계와 M1–M5 Review Artifact 순서

- **상태:** Proposed — 사용자 검토 대기
- **일자:** 2026-09-04
- **관련 결정:** OD-03, OD-04

## Context

제품 문서는 Preflight에서 Impact Analysis 초안을 이용해 Test Design Memo를 만든다고 정의하지만, roadmap의 Impact Analysis와 Test Design Guide 구현은 M4에 있다. 또한 Dashboard와 Control은 동등한 핵심 축이지만 통합 Dashboard 구현은 M5에 집중되어 있다. 그대로 해석하면 M2/M3가 아직 없는 M4 기능에 의존하거나, M1–M4가 사람이 검토할 인터페이스 없이 Core만 만드는 결과가 생긴다.

## Decision

### Assurance를 두 단계로 분리

1. **Preflight Assurance Draft (M2):** Project Baseline과 작업 요구사항에서 `Impact Hypothesis`와 `Test Design Intent`를 만든다. 예상 영향, 검증 목표, 선택할 test 관점, 변경 전 baseline 필요 여부, Unobserved를 Contract에 기록한다. 실제 변경 영향이나 test 실행 결과를 주장하지 않는다.
2. **Post-change Assurance (M4):** 실제 diff, dependency/data/trace Evidence로 `Actual Impact Analysis`를 만들고, Preflight draft를 `Test Design Memo`로 갱신한다. 선택된 before/after Evidence를 적용해 Regression Gate를 판정한다.

M2는 M4 분석 engine을 미리 구현하지 않는다. M4는 Preflight draft를 입력으로 받아 실제 Evidence로 수정·확장한다.

### 각 Milestone에 reviewable artifact를 유지

| Milestone | 사용자가 검토할 최소 산출물 | 실제 데이터 원천 |
|---|---|---|
| M1 | Task Guarantee Report + 최소 HTML view | 합성/비민감 fixture의 Event·Evidence |
| M2 | Contract Preview | Project Baseline, Task Overlay, Preflight draft |
| M3 | Control Validation packet | 실제 Managed/Imported adapter Evidence |
| M4 | Assurance packet | 실제 Impact, test, Gate Evidence |
| M5 | 통합 Dashboard UX | M1–M4의 동일 schema와 Evidence reference |

이 중간 산출물은 하드코딩 성공 화면이 아니다. M5가 이 계약들을 Task Review, Harness Status, Feature Validation, Decision Panel로 통합한다.

## Alternatives

- **Preflight에서 M4 전체 engine 선행 구현:** milestone 경계가 무너지고 실제 diff가 없는 단계에서 과한 분석을 만들므로 기각한다.
- **Test Design을 전부 M4까지 연기:** 작업 실행 전 검증 의도와 baseline 수집 시점을 잃으므로 기각한다.
- **Dashboard를 M5까지 완전히 생략:** Control 결과를 사람이 이해·검토할 경로가 없어 제품 목적과 충돌한다.
- **M1에서 최종 Dashboard부터 구현:** 실제 Control/Assurance Evidence 없이 성공 UI를 하드코딩할 위험이 있어 기각한다.

## Consequences

- M2는 예상과 사실을 분리하고, M4는 실제 변경 Evidence로 이를 갱신한다.
- 변경 전 baseline이 필요한지 실행 전에 결정할 수 있다.
- M1–M4 산출물을 사람이 매 단계 검토할 수 있으며, M5는 schema를 다시 만들지 않고 통합 UX에 집중한다.
- roadmap Issue의 문구를 이 두 단계와 packet 계약에 맞게 후속 정리해야 한다.

## Evidence

- `Design_Rationale.md` DR-013/014는 Impact Analysis → Regression Gate와 Preflight Test Design Memo를 모두 요구한다.
- `Control_layer.md` 4장·13장·14장은 Preflight draft와 completion 이후 Impact 갱신을 함께 제시한다.
- `향후계획.md`는 M1 fixture 수직 POC, M2 Preview, M4 Assurance, M5 Dashboard를 정의한다.
- `Dashboard_layer.md`는 하드코딩 성공 화면을 금지하고 모든 핵심 문장을 실제 Evidence에 연결하도록 요구한다.

이 ADR은 사용자 승인 전까지 `Proposed`이며 roadmap 변경이나 M1 구현을 허가하지 않는다.

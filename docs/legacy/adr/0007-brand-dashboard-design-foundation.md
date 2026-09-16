# ADR-0007 — Brand & Dashboard Design Foundation

- **상태:** Accepted — B 색상 방향만 승인, UI/UX는 M5로 이관
- **일자:** 2026-09-04
- **관련 Issue:** [M0-07](https://github.com/taejung3852/devharness/issues/8)
- **Gate:** M1~M4 Non-blocking, M5 Production Dashboard 전에 UI/UX 별도 승인 필수

## Context

DevHarness는 AI 작업 뒤 사람이 겪는 이해·검토·판단 병목을 줄여야 한다. Dashboard는 많은 telemetry를 보여 주는 것보다 결론, 검증 범위, Evidence, 남은 위험, 다음 행동을 짧은 경로로 연결해야 한다.

M5 전에 브랜드·시각 위계·접근성·drill-down 구조를 실제 DevHarness Fixture로 비교하지 않으면, Core schema와 무관한 UI 또는 하드코딩된 성공 화면을 먼저 만들 위험이 있다.

## Accepted Decision — M0 색상 범위

1. DevHarness의 Dashboard 색상 방향은 **B — Warm Paper Neutral + Ledger Indigo**로 정한다.
2. Brand Accent는 탐색·선택·주요 행동에 사용하고 Pass/Warning/Danger 상태색과 구분한다.
3. 현재 Light/Dark token은 M5의 출발점으로 사용한다. 접근성 검증에 필요한 미세 조정은 B 방향을 바꾸는 것으로 보지 않는다.
4. 현재 HTML, 문구, 화면 구조, disclosure 방식과 component 표현은 **참고 시안**이며 이 결정에 포함하지 않는다.

## Deferred to M5 — UI/UX 설계

- 첫 화면의 정보량과 정보 위계
- 쉬운 말 요약과 질문형 상세 공개 방식
- Project/Harness 집계와 Task/Trace 상세의 탐색 구조
- Evidence link, 표, Diagram, Raw output의 component 계약
- font, icon, component library/framework, 반응형 동작
- theme preference 저장과 system theme 동기화
- 실제 사용자 과업과 screen reader 검증
- 실제 Event → Evidence → Guarantee → Dashboard vertical slice 구현

## Alternatives

### A — Signal Graphite

Graphite neutral과 teal/cyan은 상태색 분리가 선명하고 고밀도 기술 화면에 유리하지만, 현재 사용자는 B의 따뜻한 문서 검토 감각을 더 선호했다.

### C — Slate Violet

Cool slate와 violet은 instrumentation 성격이 강하지만, warning/danger가 많은 화면에서 상태색과 시각 경쟁이 커질 수 있다.

### 제품별 UI 복제

빠르게 익숙한 외형을 얻을 수 있지만 DevHarness 고유 정보 계약과 맞지 않고, 제품 고유 색상·layout·Asset 의존을 만든다. 기각한다.

### M5에서 바로 Production UI 구현

실제 Evidence 연결 전에 UI와 성공 상태를 먼저 고정할 위험이 있어 기각한다.

## Consequences

- Brand와 status semantic token이 분리되어 판정 오독 위험을 줄인다.
- M5는 B 색상 방향과 현재 시안을 출발점으로 사용하되, 정보 구조나 상호작용을 그대로 복사할 의무가 없다.
- Light/Dark contrast와 focus는 M5 UI/UX 설계에서 다시 검증한다.
- 현재 시안의 글쓰기·disclosure 방식은 유용한 가설일 뿐 승인된 제품 계약이 아니다.

## Evidence

- [M0-07 참고 조사](../design/m0-07/research.md)
- [3안 비교와 추천](../design/m0-07/design-evaluation.md)
- [Interactive HTML 시안](../design/m0-07/index.html)
- [Probe 결과](../design/m0-07/probe-results.md)
- `screenshots/`: 세 방향 × Light/Dark × 세 화면 18개

Static Probe는 B 기본값, M5 UI/UX 이관 문구, 세 화면의 참고용 한눈에 보기, 질문형 disclosure, 54개 contrast pair, 동일 Fixture 계약을 검사했다. Browser Probe는 18개 상태를 320/390/1440 px에서 검사해 document horizontal overflow 0을 관찰했다. Diagram Design self-check도 통과했다. 이 결과는 참고 시안 품질 Evidence이며 UI/UX 승인 Evidence가 아니다.

## Not decided here

- 최종 제품명, logo, icon set, illustration
- M5 정보 구조, 문구, 탐색, disclosure와 component 계약
- Production component library/framework
- 최종 font file bundling과 subset 전략
- user preference persistence와 system theme 동기화
- 실제 사용자 과업 성공률·시간 기준
- M5 Production UI 구현 승인

## Approval record

2026-09-04 사용자가 현재 시안의 **B 색상 방향을 확정**하고, UI/UX 설계는 M5에서 현재 시안을 이어서 진행하도록 결정했다. 따라서 이 ADR은 색상 범위에 한해 Accepted다. 이 승인은 원격 Issue #8 종료, M5 구현 시작, 현재 화면 구조·글쓰기 방식 승인을 뜻하지 않는다.

# ADR-0007 — Brand & Dashboard Design Foundation

- **상태:** Proposed — 사용자 검토 대기
- **일자:** 2026-09-04
- **관련 Issue:** [M0-07](https://github.com/taejung3852/devharness/issues/8)
- **Gate:** M1~M4 Non-blocking, M5 Production Dashboard 전에 승인 필수

## Context

DevHarness는 AI 작업 뒤 사람이 겪는 이해·검토·판단 병목을 줄여야 한다. Dashboard는 많은 telemetry를 보여 주는 것보다 결론, 검증 범위, Evidence, 남은 위험, 다음 행동을 짧은 경로로 연결해야 한다.

M5 전에 브랜드·시각 위계·접근성·drill-down 구조를 실제 DevHarness Fixture로 비교하지 않으면, Core schema와 무관한 UI 또는 하드코딩된 성공 화면을 먼저 만들 위험이 있다.

## Proposed Decision

1. 브랜드 기준안으로 **Graphite Neutral + Signal Teal/Cyan**을 사용한다.
2. Brand Accent는 탐색·선택·주요 행동에만 사용하고 Pass/Warning/Danger 상태색과 분리한다.
3. Dashboard 정보 구조는 `Change → Checks → Evidence → Decision`을 사용한다.
4. 조사 경로는 `Summary → Trace/Flow → Selected Evidence`를 사용한다.
5. Project/Harness 집계와 개별 Task/Trace 상세를 분리한다.
6. Task Review는 `무엇이 바뀜 / 왜 중요함 / 근거 / 다음 행동` 순서와 Evidence link를 사용한다.
7. Raw Diff, log, raw output은 Progressive Disclosure 뒤에 둔다.
8. Control 실현 단계와 Evidence basis를 별도 축으로 표시한다. Observed/Inferred/Unobserved를 여섯 색 Badge로 만들지 않는다.
9. 변경 관계는 색뿐 아니라 `= / + / − / ?` 기호와 label로 구분한다.
10. UI 본문 font 후보는 Pretendard Variable, code/hash/timestamp 후보는 Geist Mono로 한다. Production bundling과 license notice는 M5 전 별도 검증한다.
11. M5는 이 시안 code를 복사하지 않고 실제 Event → Evidence → Guarantee → Dashboard vertical slice로 구현한다.

## Alternatives

### B — Ledger Indigo

Warm paper neutral과 indigo는 ADR·문서 검토에는 안정적이지만, runtime trace와 미검증 경로의 긴장감이 기준안보다 약하다.

### C — Slate Violet

Cool slate와 violet은 instrumentation 성격이 강하지만, warning/danger가 많은 화면에서 상태색과 시각 경쟁이 커질 수 있다.

### 제품별 UI 복제

빠르게 익숙한 외형을 얻을 수 있지만 DevHarness 고유 정보 계약과 맞지 않고, 제품 고유 색상·layout·Asset 의존을 만든다. 기각한다.

### M5에서 바로 Production UI 구현

실제 Evidence 연결 전에 UI와 성공 상태를 먼저 고정할 위험이 있어 기각한다.

## Consequences

- Dashboard의 첫 화면이 telemetry 양보다 사람의 결정 행동을 우선한다.
- Brand와 status semantic token이 분리되어 판정 오독 위험을 줄인다.
- 동일 schema를 Light/Dark에 적용하고, 최소 contrast와 focus contract를 유지해야 한다.
- Evidence link와 Progressive Disclosure가 component contract가 된다.
- 실제 사용자 과업 시간과 screen reader 사용성은 M5 전/중 추가 Evidence가 필요하다.

## Evidence

- [M0-07 참고 조사](../design/m0-07/research.md)
- [3안 비교와 추천](../design/m0-07/design-evaluation.md)
- [Interactive HTML 시안](../design/m0-07/index.html)
- [Probe 결과](../design/m0-07/probe-results.md)
- `screenshots/`: 세 방향 × Light/Dark × 세 화면 18개

Static Probe는 54개 contrast pair, 동일 Fixture, screen/interaction 계약을 검사했다. Browser Probe는 18개 상태를 320/390/1440 px에서 검사해 document horizontal overflow 0을 관찰했다. Diagram Design self-check도 통과했다.

## Not decided here

- 최종 제품명, logo, icon set, illustration
- Production component library/framework
- 최종 font file bundling과 subset 전략
- user preference persistence와 system theme 동기화
- 실제 사용자 과업 성공률·시간 기준
- M5 Production UI 구현 승인

## Approval condition

사용자가 A/B/C 중 방향을 승인하거나 수정안을 승인해야 이 ADR을 Accepted로 바꿀 수 있다. 시안 제출만으로 Issue #8을 닫지 않는다.

# M0-07 브랜드·Dashboard 시안 평가

- **상태:** B 색상 방향 승인, UI/UX는 M5로 이관
- **Fixture:** M0-06 Event & Evidence Store 합성 Probe의 `ba7394f` 여섯-check snapshot (2026-09-04)
- **비교 조건:** 세 방향 모두 같은 DOM, 문구, Fixture, 화면 구조, 상호작용을 사용하고 semantic token만 바꾼다.
- **Gate:** 이 문서는 M1~M4를 막지 않는다. M5 Production Dashboard의 UI/UX는 별도 승인 전 시작하지 않는다.

## 결정

**B — Ledger Indigo**의 색상 방향을 확정했다.

초기 A/B/C 비교는 같은 DOM·문구·구조에 semantic color token만 바꿨기 때문에 A와 B의 차이는 사실상 색과 온도감뿐이었다. 사용자는 warm paper neutral과 indigo의 문서 검토 감각을 선택했다.

이후 만든 `한눈에 보기 → 질문형 상세 공개` 수정안은 M5에서 이어서 설계할 **참고 시안**으로 남긴다. 화면 구조, 문구, disclosure, component는 이번 승인 범위가 아니다.

## 동일 Fixture

세 방향에 사용한 값은 commit `ba7394f` 시점 M0-06의 실제 합성 Probe 결과다. 이후 추가된 storage checks는 screenshot 비교 대상을 조용히 바꾸지 않기 위해 이 고정 Fixture에 소급 반영하지 않는다.

```text
sqlite_version=3.51.0
journal_mode=delete
partial_write_rollback=passed
duplicate_event_idempotency=passed
evidence_content_hash=passed
projection_rebuild=passed
raw_evidence_git_exclusion=passed
integrity_check=ok
```

화면에는 성공 결과뿐 아니라 실제 전원 손실, disk full, concurrent writer, large blob, retention race, encryption의 **Unobserved** 범위를 함께 표시한다.

## 방향 비교

| 방향 | 디자인 근거 | 장점 | 단점·위험 | 예상 구현 비용 | 판단 |
|---|---|---|---|---|---|
| **A — Signal Graphite** | 무채색 graphite surface + teal/cyan brand signal | 고밀도 정보에서 위계가 안정적이고 상태색과 브랜드색이 가장 잘 분리됨. Light/Dark 일관성이 높음 | 문서 검토 화면이 차갑게 느껴질 수 있음 | 낮음–중간 | 대안 |
| **B — Ledger Indigo** | warm paper neutral + indigo accent | ADR·결정 기록 같은 문서 검토에 안정감이 있고 사용자 선택과 맞음 | runtime trace와 미검증 경로의 긴장감이 A보다 약함 | 낮음 | **색상 방향 승인** |
| **C — Slate Violet** | cool slate neutral + violet accent | trace·instrumentation 제품의 기술적 성격이 분명하고 dark mode 구분감이 좋음 | warning/danger가 많은 화면에서 violet과 상태색의 경쟁이 커질 수 있음 | 중간 | 대안 |

## 화면별 판단

아래 내용은 M5에서 검토를 재개할 때 사용할 가설이다. M0에서 승인된 UI/UX 계약이 아니다.

### Task Review

- 첫 줄에서 “두 곳에 나눠 저장”과 “실제 장애는 아직 모름”을 쉬운 말로 보여 준다.
- 결론·확인·주의 세 칸만 먼저 노출한다.
- 이유, 확인 범위, 미확인 범위, Before/After Diagram은 각각 질문형 disclosure로 연다.
- 펼친 Diagram의 node와 edge Evidence link는 한 번의 선택으로 Evidence Detail에 도달한다.

### Harness Status

- `준비됨 / 실제 확인 / 아직 안 됨` 세 요약을 먼저 표시한다.
- Configured / Loaded / Enforced 표와 Evidence basis 설명은 별도 disclosure로 연다.
- Observed / Inferred / Unobserved는 여섯 색 Badge가 아니라 `◉ / △ / ?` 기호와 글자로 표현한다.
- 첫 행동은 Enforced가 비어 있는 경로를 확인하는 것이다.

### Evidence Detail

- 결론·근거 방식·한계 세 요약만 먼저 읽는다.
- provenance, 검사 6개, 미관찰 경로, Raw output과 판정 한계는 각각 native disclosure 뒤에 둔다.
- 합성 통과와 Production 안전을 같은 의미로 표시하지 않는다.

## UX 우선 기준 평가

| 평가 질문 | Probe/검토 결과 | 상태 |
|---|---|---|
| Raw Diff를 읽지 않고 작업 내용을 설명할 수 있는가 | Task Review의 세 요약만으로 저장 제안, 확인 범위, 남은 위험을 설명할 수 있음 | 충족 |
| 연관 기능과 미검증 영역을 빠르게 찾을 수 있는가 | `아직 모르는 것은 무엇인가요?` disclosure에서 여섯 Unobserved 항목을 확인 | 충족 |
| 필요한 Evidence에 두 번 이하로 접근하는가 | Task Review/Harness Status → Evidence Detail 1회, Raw output까지 2회 | 충족 |
| Dashboard 자체가 새 읽기 병목을 만드는가 | 초기 화면은 세 요약과 다음 행동만 노출하고 표·그림·원시 출력은 모두 접음. 실제 사용자 과업 시간은 도그푸딩 전 Unobserved | 시안 기준 충족, 실사용 검증 필요 |

세 방향은 정보 구조가 같으므로 위 네 기준의 경로 수는 같다. 추천 차이는 정보 밀도와 상태색 간 시각 경쟁에서 발생한다.

## 접근성 결과

| 검사 | 결과 | 해석 |
|---|---|---|
| Light/Dark × 3방향 contrast | 54 pair 검사 통과 | 일반/상태 text 최소 5.66:1, focus 최소 3.82:1 |
| Accessible SVG | Diagram Design self-check 통과 | `<title>`이 첫 child이고 `<desc>`, prefixed ID, `aria-labelledby`가 있음 |
| 색 외 표현 | 통과 | result text, `✓ / ○`, `◉ / △ / ?`, `= / + / − / ?`를 병행 |
| Keyboard 순서 | positive tabindex 0 | native document order를 유지 |
| Focus 표시 | 통과 | 3px semantic focus outline 사용 |
| Disclosure | 통과 | native `<details>/<summary>` 사용 |
| 320/390/1440 px layout | 54 상태 검사 통과 | document-level horizontal overflow 0. table/diagram만 내부 scroll 허용 |
| Reduced motion | 통과 | 필수 animation 없음, reduced-motion rule 포함 |

### 남은 접근성 위험

- Pretendard Variable file을 시안에 bundle하지 않았으므로 실제 Pretendard glyph metric은 **Unobserved**다. 현재 시안은 `Pretendard Variable → Noto Sans KR → system UI` fallback 순서다.
- screen reader별 SVG 내부 link 탐색 차이가 있어, SVG 아래에 동일한 HTML Evidence link를 제공했다. 실제 VoiceOver/NVDA 사용성은 M5 전 별도 사용자 flow Probe가 필요하다.
- Table의 좁은 화면은 내부 가로 scroll을 사용한다. M5에서는 card 대체가 더 이해하기 쉬운지 실제 사용자 과업으로 비교해야 한다.

## Semantic token 경계

| 역할 | A — Signal Graphite 예 | B — Ledger Indigo 예 | C — Slate Violet 예 |
|---|---|---|---|
| Brand Accent | teal/cyan | indigo | violet |
| Neutral | graphite | warm paper gray | cool slate |
| Pass | green | green | green |
| Warning | amber | amber | amber |
| Danger | red | red | red |
| Evidence basis | neutral symbol + label | neutral symbol + label | neutral symbol + label |

색상값은 승인된 B 방향의 출발 token이며 최종 Brand Asset이나 component 계약은 아니다. M5에서 contrast를 다시 확인하면서 세부값을 조정하고, token 이름·font bundling·component usage를 별도 설계한다.

## 구현 비용 범위

여기서 비용은 상대 평가이며 일정 추정이 아니다.

- **낮음:** 현재 semantic token만으로 Light/Dark를 구현할 수 있고 별도 시각 primitive가 거의 없음.
- **낮음–중간:** 상태색 분리와 Evidence-heavy screen의 위계를 함께 검증해야 함.
- **중간:** tinted dark surface와 다양한 상태색의 조합을 component별로 더 많이 검증해야 함.

어느 방향을 선택해도 M5는 먼저 실제 Event/Evidence schema에 연결된 vertical slice로 구현해야 한다. 이 HTML을 Production component로 전환하거나 그대로 복사하지 않는다.

## 결정 기록

- 2026-09-04: B — Warm Paper Neutral + Ledger Indigo 색상 방향 승인
- M5로 이관: 화면 구조, 정보 위계, 글쓰기, disclosure, component, 사용자 검증
- 외부 변경: 원격 push·PR·Issue #8 종료는 별도 승인 전 수행하지 않음

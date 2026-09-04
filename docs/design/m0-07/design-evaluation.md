# M0-07 브랜드·Dashboard 시안 평가

- **상태:** 추천안 제출, 사용자 승인 대기
- **Fixture:** M0-06 Event & Evidence Store 합성 Probe (2026-09-04)
- **비교 조건:** 세 방향 모두 같은 DOM, 문구, Fixture, 화면 구조, 상호작용을 사용하고 semantic token만 바꾼다.
- **Gate:** 이 문서는 M1~M4를 막지 않는다. M5 Production Dashboard는 사용자 승인 전 시작하지 않는다.

## 추천

**A — Signal Graphite**를 M5 디자인 기준안으로 추천한다.

Graphite neutral이 많은 검토 정보를 조용하게 받치고, teal/cyan은 탐색·선택·주요 행동 신호에만 사용된다. Pass의 green, Warning의 amber, Danger의 red와 hue가 분리되어 브랜드 강조와 판정 결과를 혼동할 가능성이 세 안 중 가장 낮다.

사용자 승인 전에는 이 추천을 최종 Brand System으로 기록하지 않는다.

## 동일 Fixture

세 방향에 사용한 값은 M0-06의 실제 합성 Probe 결과다.

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
| **A — Signal Graphite** | 무채색 graphite surface + teal/cyan brand signal | 고밀도 정보에서 위계가 안정적이고 상태색과 브랜드색이 가장 잘 분리됨. Light/Dark 일관성이 높음 | 지나치게 절제하면 차갑게 느껴질 수 있어 문구 tone이 중요함 | 낮음–중간 | **추천** |
| **B — Ledger Indigo** | warm paper neutral + indigo accent | ADR·결정 기록 같은 문서 검토에 안정감이 있고 장문 가독성이 좋음 | runtime trace와 미검증 경로의 긴장감이 A보다 약함. 따뜻한 background가 상태색 조합을 더 복잡하게 할 수 있음 | 낮음 | 대안 |
| **C — Slate Violet** | cool slate neutral + violet accent | trace·instrumentation 제품의 기술적 성격이 분명하고 dark mode 구분감이 좋음 | warning/danger가 많은 화면에서 violet과 상태색의 경쟁이 커질 수 있음 | 중간 | 대안 |

## 화면별 판단

### Task Review

- 첫 줄에서 “저장 결정안은 검토 준비됨”과 “ADR 승인 또는 수정 요청”을 보여 준다.
- `무엇이 바뀜 / 왜 중요함 / 근거 / 다음 행동` 네 블록만 먼저 노출한다.
- Before/After Diagram은 M0-06 범위만 표시하고, `= / + / − / ?` label로 색각과 무관하게 상태를 구분한다.
- node와 edge의 Evidence 링크는 한 번의 선택으로 Evidence Detail에 도달한다.

### Harness Status

- Configured / Loaded / Enforced를 세 개의 독립 column으로 표시한다.
- 각 check 안에서 result와 basis를 분리한다.
- Observed / Inferred / Unobserved는 여섯 색 Badge가 아니라 `◉ / △ / ?` 기호와 글자로 표현한다.
- 첫 행동은 Enforced가 비어 있는 경로를 확인하는 것이다.

### Evidence Detail

- 선택 Evidence의 결론, provenance, 범위 내 검사, 미관찰 경로 순서로 읽는다.
- Raw output, Evidence 연결, 판정 문구 제한은 native disclosure 뒤에 둔다.
- 합성 통과와 Production 안전을 같은 의미로 표시하지 않는다.

## UX 우선 기준 평가

| 평가 질문 | Probe/검토 결과 | 상태 |
|---|---|---|
| Raw Diff를 읽지 않고 작업 내용을 설명할 수 있는가 | Task Review의 결론과 네 설명 블록만으로 저장 제안, 중요성, 근거, 결정 행동을 설명할 수 있음 | 충족 |
| 연관 기능과 미검증 영역을 빠르게 찾을 수 있는가 | Before/After의 `?` node와 Evidence Detail의 여섯 Unobserved 항목을 직접 노출 | 충족 |
| 필요한 Evidence에 두 번 이하로 접근하는가 | Task Review/Harness Status → Evidence Detail 1회, Raw output까지 2회 | 충족 |
| Dashboard 자체가 새 읽기 병목을 만드는가 | 초기 화면은 결론·행동·요약만 노출하고 원시 출력은 접음. 다만 실제 사용자 과업 시간은 도그푸딩 전 Unobserved | 시안 기준 충족, 실사용 검증 필요 |

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

색상값은 시안 token이며 최종 Brand Asset이 아니다. 사용자가 방향을 승인하면 M5 전에 token 이름, contrast contract, font bundling, component usage를 ADR amendment로 고정한다.

## 구현 비용 범위

여기서 비용은 상대 평가이며 일정 추정이 아니다.

- **낮음:** 현재 semantic token만으로 Light/Dark를 구현할 수 있고 별도 시각 primitive가 거의 없음.
- **낮음–중간:** 상태색 분리와 Evidence-heavy screen의 위계를 함께 검증해야 함.
- **중간:** tinted dark surface와 다양한 상태색의 조합을 component별로 더 많이 검증해야 함.

어느 방향을 선택해도 M5는 먼저 실제 Event/Evidence schema에 연결된 vertical slice로 구현해야 한다. 이 HTML을 Production component로 전환하거나 그대로 복사하지 않는다.

## 승인 선택지

1. **A — Signal Graphite 승인:** M5 전 ADR-0007을 Accepted로 바꾸고 token/component 계약을 구체화한다.
2. **B 또는 C 선택:** 선택 이유와 trade-off를 ADR-0007에 반영한다.
3. **수정 요청:** 어떤 화면·정보 위계·색 역할을 바꿀지 기록하고 동일 Fixture로 다시 비교한다.

승인 전 Issue #8은 닫지 않고 `status:in-progress`를 유지한다.

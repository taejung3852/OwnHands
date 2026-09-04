# M0-07 Probe 결과

- **실행일:** 2026-09-04
- **Browser:** Google Chrome 152.0.7977.76
- **실행 환경:** macOS, local file prototype
- **Fixture:** `m0-06-store-probe-ba7394f-2026-09-04` (여섯-check 고정 snapshot)

## Static design probe

실행:

```bash
node docs/design/m0-07/probes/m0-07-design-probe.mjs
```

관찰 결과:

```text
M0-07 design probe: PASSED
fixture_instances=1
brand_directions=3
themes=2
screens=3
capture_states=18
evidence_path_interactions=1
raw_output_interactions=2
contrast_pairs_checked=54
minimum_contrast_ratio=3.82
minimum_text_contrast_ratio=5.66
minimum_focus_contrast_ratio=3.82
remote_stylesheet_references=1
executable_script_tags=0
```

`minimum_contrast_ratio`는 3:1 기준을 적용하는 focus pair를 포함한다. 일반 text와 상태 text에 적용한 4.5:1 기준 pair의 최솟값은 5.66:1이다.

remote stylesheet 한 개는 Google Fonts CSS 후보이며 실행 script나 framework dependency는 없다. 이 Probe는 “Production UI code가 없음”을 자동 판정하지 않는다. 해당 경계는 artifact 위치·목적과 code review로 확인한다.

## Browser layout probe

실행:

```bash
node docs/design/m0-07/probes/m0-07-browser-probe.mjs
node docs/design/m0-07/probes/m0-07-browser-probe.mjs --write-screenshots
```

관찰 결과:

```text
M0-07 browser probe: PASSED
capture_states=18
viewport_widths=320,390,1440
layout_checks=54
document_horizontal_overflow=0
screen_selection_failures=0
initially_open_details=0
progressive_disclosure_toggle=passed
focusable_elements_minimum=46
positive_tabindex=0
```

`--write-screenshots`를 사용하면 같은 검증 session의 1440 × 1800 상태 18개를 `screenshots/`에 갱신한다. 허용한 내부 overflow는 좁은 화면의 Control table과 Before/After Diagram이다. document 자체의 가로 overflow는 허용하지 않는다.

첫 실행에서는 320 px의 Evidence Detail 여섯 상태에서 `evidence-summary`와 `provenance` grid item의 intrinsic minimum width 때문에 document overflow가 재현됐다. 두 grid item에 `min-inline-size: 0`을 적용한 뒤 같은 54개 상태 검사에서 재발하지 않았다.

## Diagram Design self-check

실행:

```bash
python3 /Users/parktaejung/.agents/skills/diagram-design/scripts/self_check.py docs/design/m0-07/index.html
```

관찰 결과:

```text
OK docs/design/m0-07/index.html
```

검사 범위는 accessible SVG contract, remote asset 제한, executable attribute와 script 부재다.

## Screenshot evidence

`screenshots/`에 3방향 × Light/Dark × 3화면의 PNG 18개가 있다. 모든 PNG는 같은 HTML과 같은 Fixture에서 capture fragment만 바꿔 생성했다.

시각 검토에서 다음을 확인했다.

- 1440 × 1800에서 headline, action, 한눈에 보기, 질문형 disclosure가 겹치지 않음
- Light/Dark에서 상태 text와 brand accent가 구분됨
- Task Review의 Diagram은 처음에는 접혀 있고 선택 시 connector가 대각선 없이 읽힘
- Harness Status는 쉬운 요약을 먼저 보여 주고 Control 표와 용어 설명을 별도로 펼침
- Evidence Detail에서 검사 목록, 미확인 경로, Raw output이 초기 화면에 노출되지 않음

## 이 Probe가 증명하지 않는 것

- 실제 사용자 과업 시간 감소
- screen reader별 사용성
- Pretendard Variable 실제 file metric
- Production component/API/backend 연결
- M5 Dashboard 완료 또는 안전
- 최종 Brand Asset 또는 M5 UI/UX 승인

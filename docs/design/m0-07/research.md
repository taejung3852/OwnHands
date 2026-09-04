# M0-07 참고 조사 — UI 시각 체계와 UX 정보 전달

- **상태:** Spike 조사 완료, 사용자 검토 대기
- **확인일:** 2026-09-04
- **범위:** Brand & Dashboard Design Foundation만 다룬다. Production UI와 Brand Asset은 만들지 않는다.
- **원칙:** 참고 제품의 색상·레이아웃·Asset을 복제하지 않고, DevHarness 문제에 필요한 원칙만 추출한다.

## 결론

DevHarness Dashboard는 관측 도구처럼 많은 정보를 보여 주는 화면이 아니라, 사람이 작업을 **설명하고 검증하고 결정하는 순서**를 짧게 만드는 화면이어야 한다.

추천 조합은 다음과 같다.

1. 시각 체계는 **Graphite Neutral + Signal Teal/Cyan**을 기준안으로 사용한다.
2. 첫 화면은 결론과 사용자의 다음 행동을 먼저 보여 준다.
3. 정보 구조는 `Change → Checks → Evidence → Decision`을 따른다.
4. 탐색은 `Summary → Trace/Flow → Selected Evidence`의 세 단계로 제한한다.
5. Control 실현 단계와 Evidence 근거 방식은 서로 다른 축으로 표시한다.
6. 상세 로그·Diff·원시 출력은 Progressive Disclosure 뒤에 둔다.

## UI 시각 참고

| 참고 대상 | 가져오는 원칙 | 가져오지 않는 것 | DevHarness 적용 |
|---|---|---|---|
| Linear | 정보 밀도 안에서 초점과 방향 정보의 대비, 절제된 경계 | 고유 색상, 화면 배치, 컴포넌트 모양 | 핵심 결론은 남기고 주변 chrome은 약하게, 카드 남용 대신 구획선 사용 |
| GitHub Pull Request | 변경·검사·검토·결정이 한 작업 문맥에 모이는 구조 | 탭 배치, merge UI, GitHub 고유 시각 자산 | Task Review를 Change / Checks / Evidence / Decision 흐름으로 구성 |
| Sentry | issue summary에서 대표 event와 관련 trace로 들어가는 방식 | issue 화면 레이아웃과 purple palette | Task 요약에서 선택 Evidence와 원인 문맥으로 이동 |
| Honeycomb | trace summary, waterfall, 선택 span sidebar의 단계적 조사 | waterfall의 색상 규칙과 화면 배치 | Summary → 작업 관련 흐름 → 선택 Evidence의 drill-down |
| LangSmith | project 집계와 trace/run 상세의 분리 | LLM 전용 metric과 token/cost 중심 dashboard | Project/Task 집계와 개별 실행 Evidence 분리 |
| Phoenix | project → trace → span 계층 | observability 제품의 전체 navigation | Harness 전체 상태와 단일 Task 실행 근거 분리 |
| Geist | 배경·component·border·text 용도에 맞춘 scale, 개발자용 Mono | Vercel 브랜드 표현 | 화면/표면/경계/텍스트 semantic token과 기술 정보용 Geist Mono |
| Primer | base가 아닌 functional token 사용, light/dark와 접근성 계약 | GitHub component 외형 | `surface`, `text`, `border`, `accent`, `success`, `warning`, `danger` 역할 토큰 |
| Radix Colors | 단계별 색 용도, gray/brand/semantic scale 분리 | Radix palette의 직접 복제 | Brand Accent와 상태 색상을 별도 scale로 유지 |

### 근거

- Linear는 정보가 많아도 모든 요소에 같은 무게를 주지 않고, 초점이 되는 내용은 유지하면서 orientation 요소는 물러나게 해야 한다고 설명한다. 또한 구조는 강한 선보다 간격·정렬·tone으로 느껴지게 하는 방향을 제시한다. [Linear UI refresh](https://linear.app/now/behind-the-latest-design-refresh), [Linear redesign](https://linear.app/now/how-we-redesigned-the-linear-ui)
- GitHub Pull Request는 Conversation, Commits, Checks, Files changed 같은 문맥을 한 변경 단위에 묶고, merge 상태에서 blocker·approval·requirement를 드러낸다. DevHarness는 이를 그대로 복제하지 않고 Change / Checks / Evidence / Decision 순서로 번역한다. [GitHub Pull Requests reference](https://docs.github.com/en/pull-requests/reference/pull-requests), [Reviewing pull requests](https://docs.github.com/en/pull-requests/get-started/reviewing-pull-requests-quickstart)
- Sentry Issue Details는 대표 event, highlights, stack trace, breadcrumbs, 관련 trace처럼 요약에서 특정 원인 근거로 좁혀 가는 구조를 제공한다. [Sentry Issue Details](https://docs.sentry.io/product/issues/issue-details/)
- Honeycomb Trace Detail은 trace identification, trace summary, waterfall, selected span sidebar 네 영역으로 구성되고, 요약에서 오류·긴 span을 찾은 뒤 선택 span의 field로 내려간다. [Honeycomb Explore Traces](https://docs.honeycomb.io/investigate/analyze/explore-traces)
- LangSmith는 project가 여러 trace를 담고 trace가 run으로 구성된다고 정의하며, project dashboard와 개별 trace 상세을 분리한다. [LangSmith observability concepts](https://docs.langchain.com/langsmith/observability-concepts), [LangSmith dashboards](https://docs.langchain.com/langsmith/dashboards), [LangSmith view traces](https://docs.langchain.com/langsmith/view-traces)
- Phoenix도 project를 trace의 container로, trace를 span의 집합으로 구분한다. [Phoenix tracing concepts](https://arize.com/docs/phoenix/tracing/concepts-tracing/what-are-traces)
- Primer는 base → functional → component token 층을 구분하고, base token을 제품 코드에서 직접 쓰지 않도록 권한다. semantic color는 역할별 foreground/background/border를 가진다. [Primer color usage](https://primer.style/product/getting-started/foundations/color-usage/), [Primer token names](https://primer.style/product/primitives/token-names/)
- Radix는 배경·interactive component·border·solid·accessible text 용도로 scale 단계를 분리하고, custom brand scale을 gray·semantic scale과 별도로 추가하는 방식을 안내한다. [Radix Colors](https://www.radix-ui.com/colors), [Composing a palette](https://www.radix-ui.com/colors/docs/palette-composition/composing-a-palette)
- Geist의 색 체계도 배경, component, border, high-contrast background, text/icon 역할을 구분한다. [Geist colors](https://examples.vercel.com/geist/colors)

## UX 정보 전달 참고

UX 참고는 시각 외형의 출처가 아니다. 사용자가 정보를 이해하는 순서와 관계 표현에만 적용한다.

### ELI5 적용

Task Review의 첫 화면은 다음 순서를 고정한다.

1. 결론과 사용자가 지금 해야 할 행동
2. 무엇이 바뀜
3. 왜 중요함
4. 근거
5. 다음 행동

쉬운 요약은 원문을 대체하지 않는다. 모든 요약은 Evidence Detail 또는 ADR/Spike 원문에 연결되고, 관찰하지 않은 범위는 같은 화면에서 보인다.

### Diagram Design 적용

Before/After Diagram은 전체 시스템을 장식적으로 그리지 않는다. 이번 Fixture에 관련된 `Event → Store → Guarantee Projection → Dashboard Review`만 표현한다.

- `=` 유지, `+` 추가 제안, `−` 제외 제안, `?` 미검증·보류를 색상과 함께 label로 표시한다.
- node와 edge 모두 선택 Evidence로 이동할 수 있다.
- SVG의 대체 설명과 별도의 HTML Evidence link를 함께 제공한다.
- 대각선 연결을 쓰지 않고, 관계가 교차하지 않는 orthogonal flow를 사용한다.

## 정보 구조 결정

```text
Project / Harness aggregate
└─ Task Review
   ├─ Change
   ├─ Checks
   ├─ Evidence
   │  └─ Selected Evidence Detail
   └─ Decision / Next action
```

이 구조는 LangSmith/Phoenix의 집계/개별 trace 분리를 따르되, DevHarness에서는 성능 지표보다 사람의 검토 결정이 최상위 목적이다. Preflight에는 token/cost를 넣지 않고, M8 Usage Analytics와 분리한다.

## Semantic token 원칙

| 층 | 예시 | 규칙 |
|---|---|---|
| Primitive | graphite-950, teal-600 | 구현 내부 scale이며 화면에서 직접 사용하지 않음 |
| Functional | page, surface, text, muted, border, focus | Light/Dark에서 같은 역할 이름을 유지 |
| Brand | brand-accent, brand-soft, brand-ink | 탐색·선택·주요 행동에 사용 |
| Status | success, warning, danger, unknown | 판정 의미에만 사용하고 Brand Accent와 분리 |
| Component | decision-strip, control-row, evidence-link | functional token을 참조하고 수를 제한 |

Evidence basis인 Observed/Inferred/Unobserved는 상태 색상 세트를 새로 만들지 않는다. `◉ / △ / ?` 기호와 글자로 표현하고, 실제 판정 결과에만 success/warning/danger를 사용한다.

## Typography 후보

| 역할 | 후보 | 현재 판단 | Evidence 상태 |
|---|---|---|---|
| UI 본문·한글 제목 | Pretendard Variable | 넓은 weight와 한글 UI 가독성 때문에 우선 후보 | CSS family와 fallback만 구성. 실제 font file bundling/metric은 Unobserved |
| code·hash·timestamp·ID | Geist Mono | code editor·diagram·terminal 용도로 설계된 Mono라 목적에 맞음 | Google Fonts 렌더링으로 시안에서 Observed |
| offline fallback | Noto Sans KR, system-ui, ui-monospace | font network 실패 시 내용 손실 방지 | headless screenshot에서 fallback 가능 경로 Observed |

Pretendard는 공식 package에서 family 이름을 `Pretendard Variable`로 제공한다. Geist Mono는 code·diagram·terminal 용도로 설명되며 두 font 모두 SIL Open Font License 1.1이다. Production bundling과 license notice 방식은 M5 구현 전에 별도 확인한다. [Pretendard package README](https://github.com/orioncactus/pretendard/blob/main/packages/pretendard/README.md), [Geist font repository](https://github.com/vercel/geist-font)

## 접근성 조사 기준

- 일반 텍스트는 WCAG AA 기준인 4.5:1 이상을 목표로 한다.
- focus와 interactive boundary는 3:1 이상을 목표로 한다.
- 색상 외 기호와 visible label을 항상 함께 둔다.
- 실제 link는 `<a>`, 동작 선택은 radio/label, disclosure는 native `<details>`를 사용한다.
- 320 CSS px에서 내용이 잘리지 않도록 table과 diagram만 명시적으로 가로 scroll을 허용한다.
- motion은 필수 정보 전달에 사용하지 않고 reduced-motion을 지원한다.

Primer는 token text에 4.5:1, custom focus에 3:1, interactive element의 올바른 semantic HTML을 요구한다. [Primer Token accessibility](https://primer.style/product/components/token/accessibility/), [Primer accessibility guidance](https://primer.style/accessibility/design-guidance/)

## 복제 방지 기록

이번 시안은 다음을 새로 구성했다.

- DevHarness M0-06의 실제 합성 Fixture와 자체 문구
- 세 브랜드 방향의 독립 semantic token
- `무엇이 바뀜 / 왜 중요함 / 근거 / 다음 행동` review 구조
- Configured/Loaded/Enforced와 Evidence basis를 분리한 table
- M0-06만 다루는 자체 Before/After SVG

참고 제품의 logo, icon asset, screenshot, 고유 component code, 화면 grid, 고유 색상값은 사용하지 않았다.

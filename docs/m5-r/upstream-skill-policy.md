# Upstream Specialized Skill Policy & Provenance

OwnHands M5-R3 라이프사이클은 자체적으로 완결된(self-contained) 얇은 하네스이며, 어떠한 외부 전문 스킬도 **필수 런타임 의존성(hard dependency)**으로 요구하지 않는다.

본 문서는 `work-map`, `verification-spec`, `dashboard` 등에서 선택적·보조적으로 참고(reference)할 수 있는 상위/외부 전문 스킬의 출처(provenance), 라이선스, 호출 기준 및 비가용 시 대체(fallback) 정책을 기록한다.

---

## 핵심 원칙 (Core Rules)

1. **Non-Vendored / Reference Only**:
   - 외부 스킬을 OwnHands 저장소 내부로 벤더링(vendoring)하거나 번들링하지 않는다 (`vendored: no`).
   - 특정 버전이나 커밋으로의 인위적 고정(pinning)을 강제하지 않으며, 호스트 환경(Antigravity, Claude Code, Codex 등)에 설치된 경우에 한해 자율적으로 보조 활용한다.
2. **Never Mandatory**:
   - 전문 스킬이 설치되어 있지 않거나 모델/플랫폼이 지원하지 않더라도 OwnHands의 모든 핵심 라이프사이클(`work-map`, `verification-spec`, `baseline`, `review`, `dashboard`)은 기본 표준 템플릿과 내장 로직만으로 100% 정상 작동해야 한다.
3. **No Automatic Chaining**:
   - 라이프사이클 전환 시 외부 스킬을 무조건 연쇄 호출(chaining)하지 않는다. 오직 명확한 조건이 만족되고 사용자 입력 또는 보조 추론이 실제로 필요할 때만 선별적으로 호출한다.

---

## 1. wayfinder

- **name**: `wayfinder`
- **source**: External / Agent skill ecosystem
- **repository/plugin**: Optional planning & roadmap navigation skill (`superpowers` or equivalent)
- **pinned version or commit**: None (reference only / not vendored)
- **license**: MIT / Apache-2.0 compatible
- **vendored**: no
- **used by**: `skills/work-map`
- **invocation condition**: 복수의 상호 의존성이 얽혀 있거나 선행 아키텍처 결정 경로가 불명확한 대규모 목표/과제를 분해할 때 선택적으로 참고.
- **fallback when unavailable**: `skills/work-map`에 내재화된 표준 분해 절차(문제 식별 ➔ 의사결정 포크 도출 ➔ Work Item 구조화 트리)를 마크다운으로 직접 작성하여 수행.
- **notes**: 단순히 이슈 1개를 쪼개는 일반적인 상황에서는 호출하지 않으며, `work-map` 자체의 내장 가이드라인만으로 작업 분해를 완료한다.

---

## 2. grill-me / grilling

- **name**: `grill-me`
- **source**: Antigravity builtin / Superpowers ecosystem
- **repository/plugin**: Interactive interview & design elicitation skill
- **pinned version or commit**: None (reference only / not vendored)
- **license**: Apache-2.0 / MIT compatible
- **vendored**: no
- **used by**: `skills/work-map`, `skills/verification-spec`
- **invocation condition**: 코드베이스나 기존 문서 조사만으로는 해결할 수 없는 사용자 고유의 비즈니스 정책, 설계 취향, 미확정 요구사항이 남아 있을 때에만 선택적으로 대화형 인터뷰를 진행.
- **fallback when unavailable**: 에이전트가 일반 텍스트 질문 또는 명확한 다지선다 질문을 사용자에게 직접 제시하여 설계 의사결정을 확인.
- **notes**: 일상적인 질문이나 이미 문서화된 사실에 대해서는 호출을 금지하며, 사용자가 명시적으로 `/grill-me`를 요청하거나 핵심 요구사항이 모호할 때만 최소한으로 인터뷰를 수행한다.

---

## 3. eli5

- **name**: `eli5`
- **source**: Agent plugin / Custom skills library
- **repository/plugin**: Plain-language visual explainer skill
- **pinned version or commit**: None (reference only / not vendored)
- **license**: MIT compatible
- **vendored**: no
- **used by**: `skills/dashboard`
- **invocation condition**: 저장된 Review 결과를 비개발자나 최종 의사결정자가 한눈에 이해할 수 있도록 2~3문장의 쉬운 일상어로 요약 브리프(Page-level ELI5)를 생성할 때 선택적으로 참고.
- **fallback when unavailable**: `skills/dashboard`에 내장된 표준 마크다운 요약 서식(달성 내용, 주요 변경, 잔여 영향)을 직접 렌더링.
- **notes**: UI 새로고침이나 대시보드 조회 시 런타임에 재호출되지 않으며, 온디맨드 아티팩트 생성 시 1회 작성 후 캐시된다.

---

## 4. diagram-design

- **name**: `diagram-design`
- **source**: Builtin / Custom skills library
- **repository/plugin**: Architecture & data model diagram generator
- **pinned version or commit**: None (reference only / not vendored)
- **license**: MIT compatible
- **vendored**: no
- **used by**: `skills/dashboard`
- **invocation condition**: 단순 텍스트 표나 Before-After 비교만으로는 파악하기 어려운 복잡한 상태 전이 머신, 분산 서비스 호출 흐름, 데이터 파이프라인 변화를 시각화해야 할 때 선택적으로 다이어그램(SVG/Mermaid) 생성.
- **fallback when unavailable**: 표준 마크다운 표(Table), 텍스트 기반 상태 다이어그램 또는 코드 diff 블록으로 직관적인 비교 자료를 구성.
- **notes**: 단순 CRUD나 단위 버그픽스 등 다이어그램이 불필요한 작업에서는 호출하지 않으며, 오버엔지니어링을 방지한다.

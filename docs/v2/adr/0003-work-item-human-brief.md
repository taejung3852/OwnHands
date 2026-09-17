# ADR-0003 — Work Item(Issue/PR)의 Human Brief 표기 규격과 컨텍스트 분리

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-18
- **관련 Issue:** [#108](https://github.com/taejung3852/OwnHands/issues/108) (선행: [#103](https://github.com/taejung3852/OwnHands/issues/103), [#104](https://github.com/taejung3852/OwnHands/issues/104), [#106](https://github.com/taejung3852/OwnHands/issues/106))

---

## 1. Context (배경 및 문제)

1. **문제의 본질 (정보 해상도의 불일치)**:
   - AI 에이전트가 작성한 Issue/PR은 실행에 필요한 제약·근거·예외·검증까지 담으면서 수백 줄로 길어졌다.
   - 상세한 맥락은 에이전트에게 필수적이지만, 사람은 핵심 판단에 필요한 내용("무엇을 해야 하고, 왜 지금이며, 내가 무엇을 결정/리뷰해야 하는가")을 빠르게 찾기 어려웠다.
   - 사람에게 맞춰 짧게 쓰면 에이전트의 실행 맥락이 부족해지고, 에이전트에 맞춰 길게 쓰면 사람이 읽기 어려워지는 딜레마가 발생했다.

2. **단일 진실 원칙 (Single Source of Truth)**:
   - 사람용과 에이전트용 문서를 별도로 이원화하여 관리하면 반드시 불일치와 동기화 부채가 발생한다.
   - 따라서 **같은 Work Item 본문 안에서 점진적 공개(Progressive Disclosure) 방식으로 정보 밀도를 나누는 규격**이 필요했다.

---

## 2. Decision (결정)

모든 GitHub Issue와 PR 본문은 **`Human Brief (3칸 고정)` + `<details> (상세 맥락)`**의 2단계 계층 구조로 작성하며, 이를 [`.agents/skills/write-issue-pr/SKILL.md`](../../../.agents/skills/write-issue-pr/SKILL.md)에 정식 규격으로 영구 반영한다.

### 2.1 3칸 고정 헤딩 (Three Parts Whole Brief)
Human Brief는 반드시 다음 순서와 소제목(`##`) 3개로만 구성하며, 4번째 칸을 임의로 추가하지 않는다:

| 구분 | PR 본문 헤딩 | Issue 본문 헤딩 | 역할 및 제약 |
|---|---|---|---|
| **Part 1 (what)** | `## 무엇이 바뀌었나` | `## 무엇이 필요한가` | 변경 내용 또는 목표를 결론부터 서술 (최대 5개 항목) |
| **Part 2 (why)** | `## 왜 이렇게 했나` | `## 왜 지금인가` | **목적을 말하는 1~2문장**. 증명·인용·대안은 아래로 보냄 |
| **Part 3 (theirs)**| `## 리뷰할 것` | `## 결정할 것` | **독자의 일(할 일)**을 번호 매겨 명시 (에이전트 일이 아님) |

- **4번째 칸 추가 금지**: 칸이 많아지면 불필요한 패딩(채워 넣기)이 발생하므로 3칸으로 엄격히 제한한다.

### 2.2 접힌 상세 맥락 (`<details>`)
- 근거 자료, 검증 결과, 커밋 이력, 미확인 사양 등은 `<details><summary>상세 맥락 및 검증</summary> ... </details>` 블록 안에 격리한다.
- **분리 기준은 깊이(Depth)이지 독자(Audience)가 아니다**:  
  *"Split the two by depth, never by audience. The folded part is for anyone who wants more, not for machines."*  
  사람 리뷰어도 원하면 언제든 깊은 맥락을 읽을 수 있어야 한다.

### 2.3 단일 사실 투영 원칙 (Projection, not duplication)
- Human Brief는 상세 맥락의 축약 투영(Projection)이다.
- 상세 내용이 뒷받침하지 않는 사실, 상태, 수용 조건을 Human Brief에 날조하거나 별도로 유지하지 않는다.

### 2.4 Explain 스킬과의 책임 경계
- **GitHub Issue/PR**: 가벼운 마크다운 기반의 기본 협업 표현 담당 (유지보수 비용 최소화).
- **Explain 스킬 (`docs/v2/explain-*.html`)**: 복잡한 아키텍처 흐름이나 시각화가 필요할 때 사용자가 명시적으로 호출하는 독립 HTML 아티팩트 담당 ([ADR-0002](0002-explain-visual-story-cards.md)).
- Issue/PR 본문에 HTML 렌더러나 상시 최신 상태를 강제하지 않는다 (V1의 Dashboard 신선도 유지 부채 방지).

---

## 3. Alternatives & Trade-offs (대안 및 트레이드오프 분석)

### 대안 1: 사람/에이전트 탭(Tab) UI로 분리
- **기각 사유**:
  - GitHub 마크다운에는 네이티브 탭 문법이 없다.
  - 독자로 나누면 사람이 접힌 쪽을 전혀 읽지 않게 되어 코드 검수 품질이 저하된다.

### 대안 2: 칸 수를 고정하지 않고 자유 서술
- **기각 사유**: 구조가 매번 달라져 훑어보기(Scanning)가 불가능해지고, Brief 안에 구구절절한 논증과 근거 인용이 다시 침범하는 퇴행이 반복됨 (#103 초기 실측에서 확인).

---

## 4. Consequences (결과 및 영향)

### 긍정적 영향
- PR #109, #111, #112 및 이슈 #103, #104, #106에 성공적으로 dogfooding되어 검증됨.
- 독자가 10초 만에 핵심 변경점과 본인의 검토 영역을 파악할 수 있음.
- 에이전트는 `<details>` 영역에서 실행에 필요한 풍부한 컨텍스트(파일 경로, 라인 번호, 제약 조건)를 온전히 보존받음.

### 주의 및 제약
- Brief의 2번 칸(`왜`)에 증명이나 긴 인용을 넣지 않도록 주의해야 함. 증거는 항상 `<details>`에 둔다.

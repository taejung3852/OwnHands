# ADR-0001 — 초기 Agent/Subagent 역할과 위임 경계

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-17
- **관련 Issue:** [#104](https://github.com/taejung3852/OwnHands/issues/104) (추적: [#101](https://github.com/taejung3852/OwnHands/issues/101), 선행: [#102](https://github.com/taejung3852/OwnHands/issues/102), 관련: [#103](https://github.com/taejung3852/OwnHands/issues/103))

---

## 1. Context (배경 및 문제)

1. **V1의 교훈 (주객전도 방지)**:
   - V1은 검증과 대시보드를 직접 구현하다가 도구 유지보수 비용이 실제 개발보다 커지는 문제를 겪었다.
   - V2는 플랫폼 네이티브 기능(Codex)을 우선 활용하고 시스템을 최소한의 크기로 유지해야 한다.
2. **GORE (Goal-Oriented Requirements Engineering) 원칙**:
   - 에이전트 구성을 밑에서부터 임의로 늘리지 않고, 최상위 목표("사람이 AI와의 협업에서 방향을 잃지 않고 검증 가능한 결과를 낸다")에서 하위 목표(Plan, Build, Test, Review)로 분해하여 꼭 격리가 필요한 자리에만 서브에이전트를 둔다.
3. **플랫폼 확인 사실과 한계**:
   - Codex는 내장 3종(`default`, `worker`, `explorer`)을 제공한다.
   - 커스텀 에이전트는 `.codex/agents/*.toml` 파일로 정의하며 필수 필드는 `name`, `description`, `developer_instructions` 3개다.
   - **한계 (미확인 사양)**: 부모 대화 이력이 자식 서브에이전트에게 자동 상속되는지 여부는 공식 문서에 없다. 서브에이전트 호출에는 컨텍스트 직렬화 및 추가 모델 호출이라는 **코디네이션 비용(Delegation Friction)**이 수반된다.

---

## 2. Decision (결정)

초기 커스텀 서브에이전트로 **3종(`verifier`, `reviewer`, `researcher`)**을 정의하고 `.codex/agents/`에 배치한다.

| 역할 (Agent) | 대상 단계 | `sandbox_mode` | 핵심 책임 | 채택 근거 |
|---|---|---|---|---|
| **`verifier`** | Test | `read-only` | 독립 수용성 검증 및 테스트 판정 | 구현자(부모)의 편향 및 자기합리화 차단 |
| **`reviewer`** | Review | `read-only` | Git diff 및 `AGENTS.md` 규율 검토 | 작성자와 분리된 제3자적 품질/규칙 검토 |
| **`researcher`** | Plan / Design | default | 대량의 웹/문서 자료 수집 및 요약 | 검색 잔여물에 의한 메인 컨텍스트 오염 방지 |

- **Build 단계 서브에이전트**: 보류. 별도 커스텀 에이전트를 만들지 않고, 독립 태스크가 필요할 때만 Codex 내장 `worker`를 호출한다.
- **문서 작성 전담 에이전트 (`writer`)**: **기각**. `explain`과 `write-issue-pr`은 기존 **Skill 체제를 유지**한다.

---

## 3. Alternatives & Trade-offs (대안 및 트레이드오프 분석)

### 대안 1: 문서 작성(`explain`, `write-issue-pr`) 전담 `writer` 에이전트 신설
- **검토 내용**: 메인 에이전트의 컨텍스트를 아끼고 저렴한 모델로 HTML/이슈 본문을 생성하려는 안.
- **기각 사유 (트레이드오프)**:
  - 설명과 이슈 작성은 "지금까지 세션에서 무슨 논의와 결정이 있었는가"라는 **세션 맥락 의존도가 99%**다.
  - Codex는 부모 대화 자동 상속이 보장되지 않으므로, 메인이 수천 토큰의 맥락을 요약 프롬프트로 직렬화해 넘겨야 한다.
  - **핸드오프 비용과 맥락 누락 위험이 절감되는 토큰 이득보다 크다** (Anthropic 가이드: 대화 이력이 필요한 작업은 스킬 유지 권장).

### 대안 2: Build 단계에서 태스크별 서브에이전트 강제 (Superpowers SDD 방식)
- **검토 내용**: 계획 수립 후 태스크 1개마다 fresh subagent를 띄워 구현·커밋하는 방식.
- **보류 사유 (트레이드오프)**:
  - 대형 프로젝트에는 유용하나, Codex 공식 문서가 경고하듯 단일 에이전트보다 토큰 소비가 급증한다.
  - V2 초기 단계에서는 과설계 위험이 크므로 다른 마일스톤 완료 후 재검토한다.

### 대안 3: 커스텀 에이전트 없이 Codex 내장 3종(`default`, `worker`, `explorer`)만 사용
- **검토 내용**: TOML 파일 0개로 시작.
- **기각 사유 (트레이드오프)**:
  - 내장 `explorer`는 `read-heavy`이지 `read-only`가 아니어서 완벽한 쓰기 차단 검수가 불가능하다.
  - 무엇보다 V2의 핵심 철학인 **"독립 맥락의 편향 없는 검수"**를 달성하려면 검수 전담 지침을 가진 `verifier`가 반드시 독립되어야 한다.

---

## 4. Consequences (결과 및 영향)

### 긍정적 영향
- 메인 세션의 컨텍스트를 오염시키지 않고 대규모 리서치 결과를 요약본으로 수신 가능.
- 구현자가 자기 코드를 스스로 통과시키는 편향을 `verifier`로 원천 차단.
- 에이전트 수가 3개로 절제되어 유지보수 부담이 V1 수준으로 비대해지는 위험 방지.

### 주의 및 제약 (Trade-offs)
- `verifier`와 `reviewer` 호출 시, 부모가 "무엇을 검증해야 하는지(수용 조건, 파일 경로)"를 프롬프트에 명확히 명시해야 함.
- 3개 에이전트의 프롬프트와 역할이 겹치지 않도록 `description`을 명확히 정의해야 함.

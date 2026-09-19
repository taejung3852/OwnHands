# ADR-0006 — grill-spec 인터뷰 오케스트레이션 설계 및 안전장치 트레이드오프

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-18
- **관련 Issue:** [#119](https://github.com/taejung3852/OwnHands/issues/119) (V2-M2 실측 — GORE·grill-me 기반 intent/spec 작성 도우미 Skill 정의 및 관통 실측)
- **상위 마일스톤:** [V2-M2 — Plan & Design](https://github.com/taejung3852/OwnHands/milestone/15)
- **연관 ADR:** [ADR-0004 (intent/spec 산출물 규격)](0004-intent-spec-specification.md)

---

## 1. Context (배경 및 문제)

V2-M2에서는 [ADR-0004](0004-intent-spec-specification.md)를 통해 `intent.md`와 `spec.md`의 정식 4대 필드 규격을 확정했다. 그러나 빈 템플릿만 제공했을 때 개발자는 작성에 막막함을 느끼고, AI 에이전트에게 전적으로 위임하면 코드베이스 팩트 확인 없는 겉핥기나 환각에 빠지는 문제가 있었다.

이를 해결하기 위해 GORE(최상위 목표 닻 내리기)와 Matt Pocock의 인터뷰 primitive(grilling 등)를 결합한 도우미 Skill(`grill-spec`)을 설계하면서 다음과 같은 핵심 갈림길과 트레이드오프를 마주했다:
1. 검증된 외부 인터뷰 도구를 전부 자체 재구현할 것인가, 얇게 조율할 것인가?
2. 의도(Plan)와 설계(Design)를 별도 Skill로 쪼갤 것인가, 단일 Skill로 묶을 것인가?
3. 단일 Skill 채택 시 두 단계가 뭉개지는 것을 어떻게 막을 것인가 (강제 종료 vs 기본 대기)?
4. 코드베이스 사실과 사용자 의사결정의 책임을 어떻게 나눌 것인가?
5. 외부 계획 도구(Wayfinder)의 실제 역할과 적용 경계는 무엇인가?

---

## 2. Decision (결정 사항)

OwnHands는 `grill-spec` 도우미를 **"Thin Orchestration Layer"**로 정의하고, 단일 Skill 안에서 **"3대 안전장치(Default Barrier, Explicit Stage Modes, Artifact Traceability)"**를 통해 단계 분리를 보장하기로 결정했다.

### A. Thin Orchestration 채택 (자체 재구현 배제)
- Matt Pocock의 `grilling`, `grill-me` 등 upstream primitive의 핵심 인터뷰 메커니즘을 자체적으로 바닥부터 재구현하지 않는다.
- upstream 도구가 존재하면 그대로 활용하고, OwnHands는 최상위 GORE 닻 내리기와 `intent.md`/`spec.md` 규약 연결만 얇게 조율한다.
- upstream이 없거나 cross-skill 호출이 불가능한 환경을 위해 최소 fallback interview contract를 `references/interview-guide.md`에 구비한다.

### B. 단일 `grill-spec` Skill 채택 (인위적 2개 분할 배제)
- `grill-intent`와 `grill-spec`으로 Skill을 물리 분할하지 않고, 단일 `grill-spec`으로 통합한다.
- 분할하지 않는 대신 **3가지 명시적 Stage Mode**(`intent-only`, `spec-from-intent`, `full-flow`)를 지원하여 의도 파악만 하거나 기존 intent 기반으로 spec만 작성하는 흐름을 자연어로 분기한다.

### C. Default Barrier 채택 (무조건적 턴 종료 배제)
- `intent.md` 초안 작성 후 무조건 턴을 강제 종료(Hard-stop)하지 않고, **기본적으로 사람의 확인을 대기하는 Default Barrier**를 둔다.
- **핵심 계약**: 사람이 승인하지 않은 Intent를 확정된 근거로 취급해 Spec 작성을 직행하지 않는다. 단, 자명한 작업에서의 safe fast-path 가능성을 닫지 않는다.

### D. Fact(Agent) vs Decision(User) 분리 원칙
- 저장소 코드, 설정, 문서에서 조회 가능한 기술적 **Fact는 에이전트가 도구로 직접 조사**한다 (사용자에게 되묻지 않음).
- 최상위 Goal, 비목표(Non-goals), 장애 정책, 트레이드오프 등 **Decision은 사람에게 질문하여 도출**한다 (에이전트가 임의 확정하지 않음).

### E. Wayfinder의 조건부 제한 사용
- Wayfinder를 일반 기능의 코드 검색 도구로 오용하지 않는다.
- 한 세션으로 감당하기 어려운 거대하고 불명확한 다중 세션 과제(`ROUTE-C`)에 한해서만 사전 decision-ticket map 분할 용도로 안내한다.

### F. Decision-bearing Section Review 추가 — 2026-09-20 ([#142](https://github.com/taejung3852/OwnHands/issues/142))
- Fact나 사용자가 이미 명확히 확정한 Decision은 다시 묻지 않고, 선택에 따라 Goal 경계·요구사항·인터페이스·실패 정책·수용 기준이 달라지는 Decision만 Artifact 초안 전에 Review한다.
- 사용자의 반응은 의미에 따라 `맞다`(확정), `아니다`(Goal을 유지하는 대안 2~3개와 트레이드오프), `무슨 소리인지 모르겠다`(쉬운 설명과 예시)의 3-way로 처리한다.
- 사용자에게는 한 번에 하나의 불릿형 Decision Card(`결정할 것 → 핵심 불릿 → 추천 → 선택`)만 보여준다. 핵심 불릿은 최대 3개·각 1줄이며, Section Review는 기존 Artifact Checkpoint를 대체하지 않는다.
- 상세 프로토콜은 기존 `references/interview-guide.md`에 두고 새 Agent·Runner·Hook·기록 Artifact는 만들지 않는다.

---

## 3. Alternatives Considered (고려했던 대안들)

| 갈림길 | 고려했던 대안 | 기각 사유 |
|---|---|---|
| **오케스트레이션 방식** | Matt Pocock upstream 전체 자체 재구현 | • 바퀴의 재발명 및 유지보수 부담 급증<br>• OwnHands의 본질인 GORE + Artifact 규약에 집중하지 못함 |
| **Skill 분할** | `grill-intent` + `grill-spec` 2개 분할 | • 트리거, 컨텍스트, 후속 작업이 강하게 결합되어 있음<br>• 10,000 토큰 카탈로그 예산 낭비 및 불필요한 context handoff 발생 |
| **단계 분리 장치** | Intent 후 무조건 턴 종료 (Hard Barrier) | • 프로세스가 과도하게 경직되어 대화 흐름 단절<br>• OwnHands의 Thin Harness 지향점과 충돌 |
| **도구 라우팅** | 모든 기능에 Wayfinder 기본 연계 | • Wayfinder는 코드 검색기가 아닌 무거운 multi-session 분할 도구이므로 일반 작업에 명백한 과설계 |

---

## 4. Trade-offs (얻은 것과 포기한 것)

### 얻은 것 (+)
1. **구현량 및 복잡도 최소화**: upstream의 검증된 frontier 인터뷰 알고리즘을 재사용하여 코드량과 유지보수 부담을 대폭 절감함.
2. **유연성과 안전성의 공존**: 단일 Skill의 편의성을 누리면서도, Default Barrier와 Artifact Traceability를 통해 미승인 Intent가 Spec으로 오염되는 것을 차단함.
3. **사용자 피로도 경감**: 코드베이스 사실을 에이전트가 직접 조사하므로, 사람은 핵심적인 설계 결정과 비목표 판단에만 집중할 수 있음.

### 포기한 것 (-)
1. **완전한 런타임 통제권**: upstream의 세부 프롬프트나 프론티어 계산 알고리즘을 OwnHands가 100% 자체 소유하지 않으며, 외부 도구 런타임의 변동성에 일부 노출됨. (단, 자체 fallback contract로 완충)
2. **강제적 물리 분리**: 스킬을 2개로 물리 분리했을 때 얻는 기계적 강제성을 포기하고, 프로토콜 및 Default Barrier 지침 기반으로 단계를 분리함.

---

## 5. Consequences (결과 및 향후 지침)

1. **단일 진실의 원천**: 향후 스킬 분할이나 인터뷰 턴 제어 논의가 다시 발생할 경우, 본 ADR의 "카탈로그 예산 보호"와 "Default Barrier" 원칙을 기준으로 판단한다.
2. **아티팩트 추가 억제**: 본 결정은 Skill 내부의 오케스트레이션 규약이며, 기능별로 장황한 `decision.md`를 기본 필수 산출물로 강제 도입하지 않는다. 중요한 장기 아키텍처 결정만 본 문서와 같은 ADR로 남긴다.
3. **M3로의 영향**: M3(Build & Feedback Loop)에서도 자체 거대 빌드 엔진을 만들지 않고, 플랫폼 네이티브 기능 위에 얇은 검증 루프를 얹는 Thin Harness 철학을 일관되게 유지한다.

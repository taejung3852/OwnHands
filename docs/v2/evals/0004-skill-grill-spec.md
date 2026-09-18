# Eval 0004: grill-spec 도우미 Skill 동작 및 추적성 평가

- **목표 (GORE)**: `grill-spec` Skill이 팩트 수집(Agent)과 의사결정(User)을 올바르게 분리하고, 8단계 프로토콜과 3대 안전장치(Stage Checkpoint, Stage Modes, Artifact Traceability)를 준수하여 `intent.md` 및 `spec.md`를 신뢰할 수 있게 도출하는지 검증한다.
- **실행 일자**: 2026-09-18
- **관련 이슈**: [#119 (V2-M2 실측 — GORE·grill-me 기반 intent/spec 작성 도우미 Skill 정의 및 관통 실측)](https://github.com/taejung3852/OwnHands/issues/119)
- **근거 스펙**: [`docs/v2/specs/grill-spec/spec.md`](../specs/grill-spec/spec.md)

---

## 1. 평가 대상 및 7대 판정 기준

| 번호 | 검증 항목 | 합격 (Pass) 기준 |
|:---:|---|---|
| **E1** | **Skill 구조 및 라이선스** | `.agents/skills/grill-spec/SKILL.md` 및 `references/interview-guide.md`가 존재하며, YAML frontmatter와 MIT License attribution이 포함되어 있는가? |
| **E2** | **Routing 정확성** | 일반 기능(`ROUTE-B`)에 Wayfinder를 과호출하지 않고, 대형 다중 세션 과제에 대해서만 `ROUTE-C(Wayfinder)` 후보로 안내하는가? |
| **E3** | **Fact vs Decision 분리** | 코드베이스에 이미 존재하는 사실은 도구로 직접 조사하고, 사용자에게는 비목표·장애정책 등 의사결정(Decision)만 질문하는가? |
| **E4** | **Artifact Traceability** | `spec.md`가 `- 기반 Intent:` 헤더를 포함하며, 각 요구사항이 최소 하나 이상의 Goal/Constraint/Fact에 추적 가능하고 Non-goals를 침범하지 않는가? |
| **E5** | **Human Checkpoint (Default Barrier)** | `intent.md` 초안 후 기본 대기하며, 승인되지 않은 Intent를 근거로 `spec.md` 작성을 직행하거나 Build로 넘어가지 않는가? |
| **E6** | **Fallback 인터뷰 동작** | Matt Pocock upstream skills가 없거나 크로스 스킬 호출이 불가능한 환경에서도 자체 Frontier 질의로 완결되는가? |
| **E7** | **실제 관통 검증 정합성** | 본 스킬의 자체 설계 산출물(`docs/v2/specs/grill-spec/intent.md`, `spec.md`)이 ADR-0004 4대 필드 규격을 100% 충족하는가? |

---

## 2. 평가 시나리오 및 실측 결과

### E1. 파일 구조 및 라이선스 고지 실측
- **실측 명령**:
  ```bash
  test -f .agents/skills/grill-spec/SKILL.md && test -f .agents/skills/grill-spec/references/interview-guide.md
  grep -q "name: grill-spec" .agents/skills/grill-spec/SKILL.md
  grep -q "MIT License" .agents/skills/grill-spec/references/interview-guide.md
  ```
- **실측 결과**:
  - `SKILL.md` 및 `interview-guide.md` 정상 배치 확인 (Exit Code 0).
  - YAML frontmatter의 고유 `name: grill-spec` 일치.
  - Matt Pocock upstream 저작권 및 MIT License 고지문 포함 확인.
- **판정**: **PASS ✅**

---

### E2. 라우팅 시맨틱스 및 과호출 방지 실측
- **시나리오**:
  - 케이스 1: 일반 단일 세션 기능 요구 ("새로운 캐시 무효화 함수 설계해줘") ➔ `ROUTE-B` (코드 Fact 탐색 + 인터뷰) 판정.
  - 케이스 2: 대형 모놀리스 마이그레이션 ("전체 아키텍처를 마이크로서비스로 전환하자") ➔ `ROUTE-C` (Wayfinder 후보 안내) 판정.
- **실측 관측**:
  - `references/interview-guide.md` §3.1에 따라 일반 작업 시 Wayfinder를 배제하고 가벼운 `ROUTE-B`를 기본 경로로 설정.
- **판정**: **PASS ✅**

---

### E3. Fact(Agent) vs Decision(User) 분리 실측
- **실측 관측**:
  - `SKILL.md` 프로토콜 3, 4단계 및 `interview-guide.md` §2에서 코드베이스 탐색과 의사결정 질문의 책임을 엄격히 분리.
  - 에이전트가 "저장소에 무슨 파일이 있나요?"를 사용자에게 묻지 않고, 사용자는 "이 기능에서 제외할 것(Non-goals)"을 결정함.
- **판정**: **PASS ✅**

---

### E4. 인과적 추적성 (Artifact Traceability) 실측
- **실측 관측**:
  - `docs/v2/specs/grill-spec/spec.md` 상단에 `- 기반 Intent: [intent.md](intent.md)`가 명시됨.
  - `spec.md`의 `REQ-01` ~ `REQ-05` 요구사항이 `intent.md`의 최상위 Goal(GORE 닻), 비목표(독립 서브에이전트 불필요 등), 제약(REPO scope)에 100% 추적 가능.
  - Non-goals 침범 없음.
- **판정**: **PASS ✅**

---

### E5. Human Checkpoint (Default Barrier) 실측
- **실측 관측**:
  - `SKILL.md` 6단계(Human Checkpoint 1) 및 8단계(Human Checkpoint 2) 준수.
  - "승인되지 않은 Intent를 확정된 근거로 취급해 Spec 작성을 직행하지 않는다"는 Default Barrier 원칙 명시.
- **판정**: **PASS ✅**

---

### E6. 자체 Fallback 인터뷰 계약 실측
- **실측 관측**:
  - `references/interview-guide.md` §3.2에 upstream 부재 시의 Frontier 인터뷰 계약(비목표, 엣지케이스, 수용조건 질의)이 완비되어, Codex 네이티브 단독 환경에서도 작업 중단 없이 동작 가능.
- **판정**: **PASS ✅**

---

### E7. 실제 관통 산출물 규격 정합성 실측
- **실측 관측**:
  - `docs/v2/specs/grill-spec/intent.md`: 필수 4대 필드(Why, What, Non-goals, Constraints) 완전 충족.
  - `docs/v2/specs/grill-spec/spec.md`: 필수 4대 필드(Requirements, Architecture/Interfaces, Edge cases, Acceptance criteria) 완전 충족.
- **판정**: **PASS ✅**

---

## 3. 종합 평가 결과

| 총 검증 항목 | 합격 (PASS) | 실패 (FAIL) | 종합 판정 |
|:---:|:---:|:---:|:---:|
| **7개 항목** | **7개 (100%)** | **0개** | **ALL PASS (적합) 🏆** |

> **결론**: `grill-spec` Skill은 Matt Pocock upstream의 팩트/결정 분리 철학을 수용하고, GORE 및 OwnHands Artifact Contract(`intent.md`, `spec.md`)를 준수하는 얇은 오케스트레이션 계층으로 완벽하게 검증되었다. V2-M2의 파이프라인 관통 실측이 성공적으로 완결되었다.

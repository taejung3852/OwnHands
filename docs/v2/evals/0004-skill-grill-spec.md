# Eval 0004: grill-spec Skill 정의 및 정적 적합성(Static Conformance) 평가

- **목표 (GORE)**: `grill-spec` Skill이 팩트 수집(Agent)과 의사결정(User) 분리, 8단계 프로토콜, 3대 안전장치(Stage Checkpoint, Stage Modes, Artifact Traceability) 및 ADR-0004 규격을 올바르게 정의하고 있는지 **정적 규격 및 산출물 적합성(Static Conformance)**을 검증한다.
  > ⚠️ **검증 경계 고지 (`AGENTS.md` 준수)**: 본 평가는 문서/설계 및 파이프라인 정적 적합성 검증이며, 실제 에이전트가 런타임에 frontier를 질의응답하는 **대화형 런타임 동작(Runtime Execution)은 검증하지 않았음(Runtime Unverified)**을 명시한다.
- **실행 일자**: 2026-09-18
- **관련 이슈**: [#119 (V2-M2 실측 — GORE·grill-me 기반 intent/spec 작성 도우미 Skill 정의 및 관통 실측)](https://github.com/taejung3852/OwnHands/issues/119)
- **근거 스펙**: [`docs/v2/specs/grill-spec/spec.md`](../specs/grill-spec/spec.md)

---

## 1. 평가 대상 및 7대 판정 기준

| 번호 | 검증 항목 | 합격 (Pass) 기준 | 판정 방식 |
|:---:|---|---|:---:|
| **E1** | **Skill 구조 및 라이선스** | `.agents/skills/grill-spec/SKILL.md` 및 `references/interview-guide.md`가 존재하며, YAML frontmatter와 MIT License attribution이 포함되어 있는가? | 정적 파일/내용 검증 |
| **E2** | **Routing 시맨틱스 정의** | 일반 기능(`ROUTE-B`)에 Wayfinder를 과호출하지 않고, 대형 다중 세션 과제에 대해서만 `ROUTE-C(Wayfinder)` 후보로 안내하도록 문서에 규정되어 있는가? | 정적 설계 검증 |
| **E3** | **Fact vs Decision 분리 지침** | 코드베이스에 이미 존재하는 사실은 도구로 직접 조사하고, 사용자에게는 의사결정(Decision)만 질문하도록 역할 책임이 분리 정의되어 있는가? | 정적 지침 검증 |
| **E4** | **Artifact Traceability** | 산출물 `spec.md`가 `- 기반 Intent:` 헤더를 포함하며, 각 요구사항이 Goal/Constraint/Fact에 추적 가능하고 Non-goals를 침범하지 않는가? | 정적 산출물 대조 |
| **E5** | **Human Checkpoint 규약** | `intent.md` 초안 후 기본 대기(Default Barrier)하며, 승인되지 않은 Intent를 근거로 직행하지 않도록 프로토콜에 규정되어 있는가? | 정적 지침 검증 |
| **E6** | **Fallback 인터뷰 계약 구비** | Matt Pocock upstream skills가 없거나 호출 불가능한 환경에서도 단독 구동될 수 있는 자체 Fallback 질의 계약이 문서로 구비되어 있는가? | 정적 계약 구비 검증 |
| **E7** | **M2 관통 산출물 규격 정합성** | 본 파이프라인을 관통하여 생성된 자체 산출물(`docs/v2/specs/grill-spec/intent.md`, `spec.md`)이 ADR-0004 4대 필드 규격을 100% 충족하는가? | 정적 산출물 검증 |

---

## 2. 평가 시나리오 및 검증 결과

### E1. 파일 구조 및 라이선스 고지 검증
- **검증 명령**:
  ```bash
  test -f .agents/skills/grill-spec/SKILL.md && test -f .agents/skills/grill-spec/references/interview-guide.md
  grep -q "name: grill-spec" .agents/skills/grill-spec/SKILL.md
  grep -q "MIT License" .agents/skills/grill-spec/references/interview-guide.md
  ```
- **검증 결과**:
  - `SKILL.md` 및 `interview-guide.md` 정상 배치 확인 (Exit Code 0).
  - YAML frontmatter의 고유 `name: grill-spec` 확인.
  - Matt Pocock upstream 저작권 및 MIT License 고지문 포함 확인.
- **판정**: **STATIC PASS ✅**

---

### E2. 라우팅 시맨틱스 및 과호출 방지 규약 검증
- **검증 내용**:
  - `references/interview-guide.md` §3.1에 일반 작업 시 Wayfinder를 배제하고 가벼운 `ROUTE-B`를 기본 경로로 설정했는지 확인.
  - 대형 다중 세션 과제에만 `ROUTE-C(Wayfinder)` 후보로 분기하도록 정의됨.
- **한계 고지**: 런타임 동적 라우팅 트리거는 미실행 (Runtime Unverified).
- **판정**: **STATIC PASS (Runtime Unverified) ⚠️**

---

### E3. Fact(Agent) vs Decision(User) 분리 지침 검증
- **검증 내용**:
  - `SKILL.md` 프로토콜 3, 4단계 및 `interview-guide.md` §2에서 코드베이스 탐색과 의사결정 질문의 책임을 엄격히 분리 정의함.
  - "코드베이스에 이미 있는 사실을 사람에게 되묻지 않는다"는 원칙 명시 확인.
- **한계 고지**: 실제 에이전트 대화 세션에서의 발화 분리 여부는 미실측 (Runtime Unverified).
- **판정**: **STATIC PASS (Runtime Unverified) ⚠️**

---

### E4. 인과적 추적성 (Artifact Traceability) 정합성 검증
- **검증 내용**:
  - `docs/v2/specs/grill-spec/spec.md` 상단에 `- 기반 Intent: [intent.md](intent.md)` 헤더 명시 확인.
  - `spec.md`의 `REQ-01` ~ `REQ-05` 요구사항이 `intent.md`의 최상위 Goal(GORE 닻), 비목표, 제약에 매핑됨을 정적 대조 확인.
  - Non-goals 침범 없음 확인.
- **판정**: **STATIC PASS ✅**

---

### E5. Human Checkpoint (Default Barrier) 프로토콜 검증
- **검증 내용**:
  - `SKILL.md` 6단계(Human Checkpoint 1) 및 8단계(Human Checkpoint 2)에 "승인되지 않은 Intent를 확정된 근거로 취급해 Spec 작성을 직행하지 않는다"는 Default Barrier 원칙 명시 확인.
- **한계 고지**: 실제 에이전트의 턴 중단 및 대기 동작은 런타임 미실측 (Runtime Unverified).
- **판정**: **STATIC PASS (Runtime Unverified) ⚠️**

---

### E6. 자체 Fallback 인터뷰 계약 구비 검증
- **검증 내용**:
  - `references/interview-guide.md` §3.2에 upstream 부재 시의 Frontier 인터뷰 계약(비목표, 엣지케이스, 수용조건 질의)이 문서로 완비되어 있는지 확인.
- **한계 고지**: 실제 upstream 부재 환경에서 fallback 인터뷰가 실행되는 런타임 로그는 없음 (Runtime Unverified).
- **판정**: **STATIC PASS (Runtime Unverified) ⚠️**

---

### E7. 실제 관통 산출물 규격 정합성 검증
- **검증 내용**:
  - `docs/v2/specs/grill-spec/intent.md`: ADR-0004 필수 4대 필드(Why, What, Non-goals, Constraints) 완전 충족.
  - `docs/v2/specs/grill-spec/spec.md`: ADR-0004 필수 4대 필드(Requirements, Architecture/Interfaces, Edge cases, Acceptance criteria) 완전 충족.
- **판정**: **STATIC PASS ✅**

---

## 3. 종합 평가 결과

| 총 검증 항목 | 정적 적합 (STATIC PASS) | 런타임 미검증 (Runtime Unverified) | 종합 판정 |
|:---:|:---:|:---:|:---:|
| **7개 항목** | **7개 (100%)** | **4개 항목 (E2, E3, E5, E6)** | **STATIC CONFORMANCE PASS** |

> **검증 결론**:
> - `grill-spec` Skill 정의 및 이를 통해 실측 도출된 `intent.md` / `spec.md` 산출물은 ADR-0004 및 GORE 설계 규격에 대해 **100% 정적 적합(Static Conformance)**을 입증하였다.
> - 다만, 실제 인터뷰 진행, 프론티어 탐색, 런타임 fallback 동작 등 **동적 대화 런타임 상호작용은 미검증(Runtime Unverified)** 상태이며, 이는 향후 실사용 피드백 및 지속적 평가(Continuous Evals) 단계에서 실측 데이터로 보완한다.

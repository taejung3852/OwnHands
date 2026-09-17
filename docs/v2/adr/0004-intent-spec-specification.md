# ADR-0004 — intent.md와 spec.md의 정식 규격 및 저장 구조

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-18
- **관련 Issue:** [#116](https://github.com/taejung3852/OwnHands/issues/116) (선행: [#114 Research Gate](https://github.com/taejung3852/OwnHands/issues/114), [#108 Work Item 표기 규격](https://github.com/taejung3852/OwnHands/issues/108))
- **관련 PR:** [#115](https://github.com/taejung3852/OwnHands/pull/115) (M2 Research Gate)

---

## 1. Context (배경 및 문제)

1. **AI-Native SDLC의 병목 이동**:
   - 코딩 에이전트 환경에서는 코드 생성이 저렴해지는 대신, **"무엇을 만들 것인가(Intent 정의)"**와 **"어떻게 검증할 것인가(Spec & Verification)"**가 개발 성공의 핵심 병목이 된다 ([Anthropic Playbook](../../references/anthropic-playbook.md)).
   - 의도와 기술 설계가 한데 뒤섞이면 구현 디테일에 휘둘려 본래 목적을 상실하거나, 사람이 기술 설계를 검토하기도 전에 에이전트가 코드를 먼저 짜버리는 문제가 발생한다.

2. **Work Item(Issue/PR)과의 명확한 역할 분리**:
   - [ADR-0003](0003-work-item-human-brief.md)에서 확정한 3칸 Human Brief는 **사람이 10초 만에 변경점과 검토 영역을 스캔하기 위한 소통용 규격**이다.
   - 반면 `spec.md`는 코딩 에이전트가 실제 구현(Build)을 수행할 때 참고하는 **엔지니어링 청사진이자 기술적 계약(Technical Contract)**이다.
   - 따라서 `spec.md`를 3칸으로 짧게 요약해 버리면, 에이전트가 데이터 타입, 인터페이스, 엣지 케이스를 **자의적으로 상상(환각)하여 구현**하게 되어 심각한 버그와 재작업을 유발한다.

3. **플랫폼 제약 준수**:
   - Codex의 `project_doc_max_bytes`(기본 32 KiB) 상한선에 걸리지 않도록, `intent.md`와 `spec.md`는 세션별 지침(`AGENTS.md`)과 분리된 **독립 Git 아티팩트**로 관리되어야 한다.

---

## 2. Decision (결정)

OwnHands는 V2-M2(`Plan & Design`)의 정식 산출물로 **`intent.md`와 `spec.md`의 이원화 구조**를 채택하며, 다음 저장 구조 및 필드 규격을 확정한다.

### 2.1 저장 위치 구조

모든 기능/작업의 의도와 설계는 Git 저장소 내 영구 아티팩트로 관리한다:

```text
docs/v2/specs/<feature-name>/
├── intent.md     # 인간이 정의하는 의도·문제·경계
└── spec.md       # AI가 코드베이스를 분석해 작성하는 기술 청사진
```

- 임시 세션이나 휘발성 대화에 두지 않고, 버전 관리(Git)를 통해 아티팩트 체인(Audit Trail)을 보존한다.

---

### 2.2 `intent.md` 규격 — "의도와 경계의 엄밀함"

- **주요 작성자**: 사람 (Human Engineer / Product Owner)
- **핵심 질문**: *"왜, 무엇을 하려는가?"*
- **필수 4대 필드**:
  1. `## 1. 문제 및 배경 (Why)`: 해결하려는 실제 문제의 본질과 사용자 페르소나.
  2. `## 2. 목표 결과 및 가치 (What)`: 이번 작업이 가져올 실질적 사용자 가치와 성공 기준.
  3. `## 3. 비목표 (Non-goals & Boundaries)`: **절대 하지 말아야 할 것, 이번 범위에서 제외할 것** (과잉 엔지니어링 원천 차단).
  4. `## 4. 핵심 제약 조건 (Constraints)`: 플랫폼, 런타임, 비용, 시간, 의존성 제약.

---

### 2.3 `spec.md` 규격 — "기술 구현의 극대화된 디테일"

- **주요 작성자**: AI 에이전트 (코드베이스 정밀 분석 기반 생성) ➔ **사람의 승인 필수**
- **핵심 질문**: *"어떤 기술 구조로 의도를 만족시킬 것인가?"*
- **필수 4대 엔지니어링 필드**:
  1. `## 1. 기술적 요구사항 (Requirements)`: 기능별 세부 사양, 데이터 입력/출력, 상태 전이 규칙.
  2. `## 2. 시스템 아키텍처 및 인터페이스 (Architecture & Interfaces)`: 수정/생성 파일 목록, 데이터 모델 스키마, 함수/API 시그니처.
  3. `## 3. 엣지 케이스 및 예외 처리 (Edge Cases)`: 실패 시나리오, 경계값 조건, 에러 핸들링 정책.
  4. `## 4. 수용성 기준 및 검증 계획 (Acceptance Criteria)`: 자동화 테스트 및 정량적 판정 기준 (실행할 테스트 명령어 포함).

---

### 2.4 인간 게이트키퍼(Human Gate) 원칙

에이전트 시스템은 다음 2단계의 승인 게이트를 엄격히 준수한다:

1. **Gate 1 (Plan ➔ Design)**:  
   사람이 `intent.md`의 문제 정의와 비목표(Non-goals)에 동의하기 전에, 에이전트가 독자적으로 `spec.md`를 작성하거나 코드를 수정하지 않는다.
2. **Gate 2 (Design ➔ Build)**:  
   사람이 `spec.md`의 아키텍처, 인터페이스, 엣지 케이스를 검토하고 승인하기 전에, 에이전트가 코드 구현(Build) 단계로 진입하지 않는다.

---

### 2.5 `AGENTS.md`와의 연결

- `AGENTS.md`의 32 KiB 상한을 보호하기 위해, `AGENTS.md`에는 장황한 spec 템플릿 전문을 넣지 않는다.
- 대신 다음과 같은 얇은 참조 규칙 1줄만 선언한다:
  > *"기획 및 설계 작업 시 `docs/v2/specs/` 규격(`intent.md`, `spec.md`)을 준수한다."*

---

## 3. Consequences (결과 및 영향)

### 긍정적 영향
1. **에이전트의 자의적 환각(추측) 차단**: 상세한 데이터 모델과 엣지 케이스가 사전에 정의되므로, Build 단계에서 에이전트가 코드를 제멋대로 짜는 문제를 방지함.
2. **Shift-Left 검증 달성**: 코드를 다 짠 뒤에 버그를 찾는 것보다 훨씬 저렴한 비용으로 설계 단계에서 구조적 결함을 조기에 발견함.
3. **비목표(Non-goals)의 엄밀성 확보**: `intent.md`에서 하지 말아야 할 것을 명시함으로써, 에이전트가 불필요하게 스코프를 확장(Scope creep)하는 것을 원천 방지함.

### 주의 사항
- `spec.md` 작성을 요약본 수준으로 축소하려는 유혹을 경계해야 한다. 간결함은 `intent.md`와 상단 요약에 맡기고, `spec.md` 본문은 기술적 엄밀성을 최대한 유지해야 한다.

# DevHarness Design Rationale

- **문서 상태:** 주요 설계 결정과 선택 이유를 기록한 기준선
- **작성 기준일:** 2026-09-03
- **대상:** 구현 에이전트, 포트폴리오 작성자, 향후 설계 검토자
- **연계 문서:** `Dashboard_layer.md`, `Control_layer.md`, `향후계획.md`

> 이 문서는 기능 명세가 아니다. DevHarness를 왜 만들며, 왜 현재 구조를 선택했고, 어떤 대안을 검토한 뒤 제외했는지를 기록한다. 구현 중 기능이나 구조를 바꾸려면 이 문서의 이유와 충돌하는지 먼저 확인한다.

---

## 1. 프로젝트의 출발점

### 1.1 실제 경험에서 시작된 문제

코딩 에이전트의 구현 속도는 빠르게 높아졌다. 그러나 작업이 끝난 뒤 사람이 해야 하는 검토는 여전히 오래 걸렸다.

- 무엇을 바꿨는지 파악
- 왜 그렇게 구현했는지 이해
- 요청하지 않은 변경 확인
- 기존 기능에 미치는 영향 추적
- 테스트가 적절한지 검토
- 테스트가 빠뜨린 영역 탐색
- 실제 기능을 직접 실행해 확인
- 다른 사람의 질문에 자기 말로 설명
- 결과를 받아들일지 책임 있게 판단

이 과정은 짧게는 수십 분, 복잡한 작업에서는 구현 시간보다 더 긴 병목이 됐다.

```text
에이전트 구현 속도 증가
        ↓
사람의 이해·검토 속도는 그대로
        ↓
검토가 새로운 병목
        ↓
시간이 부족하면 에이전트 설명을 그대로 신뢰
        ↓
통제권과 책임의 근거가 약화
```

DevHarness는 에이전트를 더 빠르게 만드는 것보다 **빨라진 에이전트의 결과를 사람이 자기 작업으로 전환하는 시간**을 줄이기 위해 시작됐다.

### 1.2 포트폴리오 목적

두 번째 목적은 AI Native Developer로서의 Harness Engineering 역량을 보여주는 것이다.

단순히 다음을 보여주는 프로젝트가 아니다.

- AI에게 많은 코드를 생성시켰다
- 여러 Plugin과 Skill을 설치해 사용했다
- 보기 좋은 Dashboard를 만들었다

보여주려는 역량은 다음이다.

- 에이전트 작업 경계 설계
- 프로젝트별 권한과 정책 구성
- 공식 Harness 기능의 적절한 조합
- 행동과 결과의 Evidence 추적
- 테스트 설계와 회귀 검증
- 자동화와 사람 판단의 경계
- 근거가 없는 완료 선언을 막는 구조
- 실제 도그푸딩을 통한 효과 평가

### 1.3 두 목적의 관계

포트폴리오를 위해 억지로 기능을 만드는 것이 아니다. 실제로 겪은 병목을 해결하는 과정이 Harness Engineering 역량의 Evidence가 된다.

> **실제 개인 도구로 반복 사용한 결과와 실패 기록이 포트폴리오의 핵심 증거다.**

---

## 2. 제품의 중심 명제

> **AI가 작업을 대신하더라도 이해·검증·통제·책임까지 AI에게 넘기지 않는다. DevHarness는 그 상태에 도달하는 사람의 시간을 줄인다.**

이를 세 사용자 상태로 정리한다.

```text
Understand
무엇이 바뀌었는지 이해

Prove
왜 믿을 수 있는지 Evidence 확인

Decide
수용·수정·거절을 사람이 판단
```

이 순서를 바꾸지 않는다. 무엇을 했는지 이해하지 못하면 적절한 검증을 선택할 수 없고, 검증 범위를 모르면 책임 있는 판단을 내릴 수 없다.

---

## 3. 핵심 설계 결정

## DR-001 — 사람의 병목을 주된 Selling Point로 둔다

### 맥락

안전·보안만 전면에 내세우면 DevHarness가 또 하나의 정책 도구나 감시 도구처럼 보일 수 있다.

### 결정

DevHarness의 주된 가치는 **사람이 AI 작업을 이해하고 검토하는 병목 감소**다. 통제와 안전은 이를 신뢰할 수 있게 만드는 필수 기반이다.

### 이유

- 사용자가 실제로 겪은 반복적 고통과 직접 연결된다.
- Impact Analysis와 Regression Gate의 가치도 검토 시간 감소로 설명할 수 있다.
- Dashboard와 Control이 하나의 제품 이야기로 연결된다.
- 도그푸딩 전후 시간을 측정할 수 있다.

### 트레이드오프

병목 감소만 강조하면 안전 요구가 약해 보일 수 있다. 따라서 메시지는 병목 감소를 앞에 두되, Evidence와 Control을 필수 조건으로 둔다.

---

## DR-002 — Dashboard와 Control을 동등한 핵심 축으로 둔다

### 맥락

Dashboard만 만들면 AI 작업 보고서 도구에 그친다. Control만 만들면 사용자에게 또 다른 설정·보안 관리 부담을 준다.

### 결정

- Dashboard: 작업을 이해·검증·판단하는 사용자 경험
- Control: 작업 경계·권한·Evidence·검증을 실제로 만드는 기술 계층

Execution Tracking과 Assurance는 Control 문서 아래의 책임으로 둔다.

### 이유

Dashboard의 주장은 Control Evidence 없이는 신뢰할 수 없다. Control의 가치는 Dashboard에서 사용자가 이해하고 판단할 수 있어야 실현된다.

---

## DR-003 — Dashboard의 첫 목적은 이해다

### 맥락

사용자는 테스트 결과나 raw diff부터 보는 것보다 에이전트가 실제로 무엇을 했는지 먼저 알고 싶었다.

### 결정

Dashboard의 정보 순서를 다음으로 둔다.

```text
기능·사용자 흐름 변화
→ 연관된 기능
→ 검증 상태
→ 상세 Evidence
→ 최종 판단
```

### 이유

- 이해가 검증 선택보다 먼저다.
- 긴 로그를 읽는 기존 병목을 반복하지 않는다.
- 다른 사람에게 설명 가능한 정신 모델을 만든다.

### 트레이드오프

요약이 과도하면 사실이 왜곡될 수 있다. 모든 핵심 문장을 실제 Evidence와 연결한다.

---

## DR-004 — 블랙박스 우선, 화이트박스는 드릴다운한다

### 결정

사용자에게 기능 동작을 먼저 보여주고, 코드·파일·명령·Trace는 필요할 때 펼치게 한다.

### 이유

- 사용자가 코드를 모두 읽지 않아도 기능 변화를 이해할 수 있다.
- 기술 세부사항을 숨기지 않으면서 정보 밀도를 낮춘다.
- ELI5와 ADHD 친화적 표현 원칙을 제품 구조에 반영한다.

### 트레이드오프

블랙박스 설명이 실제 구현과 어긋날 수 있다. 동일 기준선의 diff와 Trace에서 생성하고 요소별 Evidence 연결을 요구한다.

---

## DR-005 — Control은 권한 모드 선택기가 아니라 Task Execution Contract 생성기다

### 맥락

`전체 권한`, `승인 요청`, `읽기 전용` 같은 일반 모드만 고르게 하면 프로젝트와 작업의 구체적인 위험을 반영하지 못한다.

### 결정

프로젝트와 작업을 분석해 다음 경계를 생성한다.

- 수정 범위
- 보호 대상
- Sandbox와 Tool 권한
- Approval Triggers
- 완료·검증 기준
- Gate 기준

### 이유

- 일반 권한 선택과 차별화된다.
- 과도한 승인 피로를 줄인다.
- 작업별로 필요한 최소 권한을 구성할 수 있다.
- Control 결과가 검증 가능한 계약으로 남는다.

---

## DR-006 — Project Baseline과 Task Overlay를 분리한다

### 결정

- Project Baseline: 프로젝트에 반복 적용되는 공통 통제
- Task Overlay: 이번 작업에서만 적용되는 제한·임시 권한·검증 조건

### 이유

매 작업마다 전체 프로젝트 인터뷰를 반복하면 새로운 인간 병목이 생긴다. 반대로 하나의 고정 프로파일만 쓰면 작업별 위험을 반영하지 못한다.

### 트레이드오프

Baseline이 오래되면 잘못된 계약을 만들 수 있다. 구조·의존성·통제 변경과 stale Evidence를 기준으로 갱신한다.

---

## DR-007 — 고정 설문 대신 적응형 Preflight를 사용한다

### 맥락

고정 질문은 신규·기존 프로젝트와 다양한 작업 유형을 제대로 다루지 못했다. 추상적인 모드 선택은 기존 Codex 권한 프리셋과 차별점이 약했다.

### 결정

- 기존 프로젝트: Profiler가 먼저 분석하고 추천안 제시
- 신규 프로젝트: 실패 영향에서 세부 권한으로 drill-down
- 추천안이 맞지 않으면 필요한 질문만 추가

### 이유

사용자 입력을 줄이면서도 프로젝트에 맞는 계약을 만들 수 있다.

### 트레이드오프

내부 분석과 분기 로직은 복잡해진다. 사용자의 반복 선택 부담을 줄이는 것이 더 중요한 제품 가치라고 판단했다.

---

## DR-008 — Managed Task를 기본으로 하고 Imported Task를 제한적으로 지원한다

### 결정

DevHarness Preflight를 거친 작업은 Managed Task다. 이미 시작됐거나 끝난 작업을 가져오면 Imported Task다.

### 이유

작업 시작부터 개입해야 다음을 신뢰할 수 있다.

- 시작 기준선
- 실제 정책 상태
- 행동 Event
- 변경 전 테스트
- 승인과 외부 효과

동시에 도입 전 작업을 완전히 버리지 않기 위해 Imported Task를 제공한다.

### 트레이드오프

Imported Task는 편하지만 Guarantee가 약하다. Dashboard에서 보장 차이를 숨기지 않는다.

---

## DR-009 — 설정 생성과 통제 집행을 구분한다

### 결정

Evidence State를 다음으로 분리한다.

- Configured
- Loaded
- Enforced
- Observed
- Inferred
- Unobserved

### 이유

설정 파일이 존재하는 것만으로 실제 통제가 작동했다고 말하면 거짓 신뢰가 생긴다.

### 트레이드오프

상태 모델과 Validation 구현이 복잡해진다. DevHarness의 신뢰도를 위해 필요한 복잡성이다.

---

## DR-010 — 모든 주요 Control을 검증 범위에 넣는다

### 결정

최종 검증 범위에 다음을 포함한다.

- config 파일 존재와 문법
- 설정 로드
- AGENTS instruction source
- Rules 집행
- Hooks 호출
- Sandbox 적용
- Approval Policy 적용
- MCP·Plugin 가용성
- 설정 충돌과 precedence
- 테스트 명령 실행
- 관찰 불가능 경로

### 이유

일부 파일의 존재만 확인하면 DevHarness는 설정 생성기일 뿐이다. 실제 작동까지 확인해야 검증 기반 Harness가 된다.

### 트레이드오프

모든 경로를 관찰할 수 없을 수 있다. 그 경우 성공으로 처리하지 않고 Unobserved로 남긴다.

---

## DR-011 — Guarantee Matrix와 Task Guarantee Report를 분리한다

### 결정

- Guarantee Matrix: 주장과 필요한 Evidence를 정한 규칙표
- Task Guarantee Report: 이번 작업의 실제 Evidence와 가능한 주장을 기록한 결과표

### 이유

규칙과 실행 결과를 한 표에 누적하면 기준이 작업마다 흔들리고 재사용하기 어렵다.

### 트레이드오프

두 객체를 관리해야 한다. 대신 Dashboard 주장의 출처와 일관성이 높아진다.

---

## DR-012 — 하나의 안전 점수를 만들지 않는다

### 결정

`안전도 92%`, `테스트 80% 이상이면 안전` 같은 단일 판정을 사용하지 않는다.

정량 수치는 다음과 함께 제공한다.

- 정의한 전체 범위
- 선택 기준
- 제외 항목
- 분석 불가 영역

### 이유

식별한 테스트 10개가 실제 전체인지 알 수 없기 때문이다. 숫자만 있으면 정밀해 보이지만 실제보다 강한 신뢰를 준다.

### 트레이드오프

화면이 단일 점수보다 복잡해질 수 있다. ELI5형 요약과 상세 드릴다운으로 보완한다.

---

## DR-013 — Impact Analysis를 Regression Gate의 선행 조건으로 둔다

### 결정

변경된 파일 수만 보지 않고 데이터·Schema·계약·의존·Runtime 관계를 분석해 `연관된 기능`과 관련 테스트를 찾는다.

### 이유

어떤 기존 기능을 검증할지 정하지 못하면 회귀 테스트는 무작위 전체 실행이나 불충분한 일부 실행이 된다.

### 트레이드오프

Impact Analysis는 완전할 수 없다. 분석 범위와 근거를 공개하고 Unobserved를 남긴다.

---

## DR-014 — TDD와 Test Design·Regression을 분리해 결합한다

### 맥락

Red → Green → Refactor는 테스트를 먼저 작성하는 순서를 제공하지만, 어떤 기법과 시나리오가 충분한지를 자동으로 보장하지 않는다.

### 결정

- Preflight: Test Design Memo
- 구현 중: TDD와 테스트 작성
- 완료 전: Impact 기반 Regression Gate

Test Design에는 동등 분할, 경계값, 결정 테이블, 상태 전이, 오류·복구 흐름 등을 고려한다.

### 이유

Superpowers의 장점을 유지하면서 ISTQB CTFL에서 배운 테스트 설계 관점을 보완할 수 있다.

---

## DR-015 — Gate 상태는 고정하고 기준은 작업별로 만든다

### 결정

상태는 다음으로 고정한다.

- Pass
- Soft Block
- Hard Block

그러나 어떤 실패가 Soft 또는 Hard인지 고정 템플릿으로 일괄 지정하지 않는다. Project Baseline과 Task Overlay에서 작업별 기준을 만든다.

### 이유

같은 테스트 실패라도 로컬 실험과 실제 데이터 변경 작업의 의미가 다르다.

### 트레이드오프

판정 로직이 단순하지 않다. 대신 사용자에게 실제 위험에 맞는 통제를 제공한다.

---

## DR-016 — Soft Block Override는 기록하고 Hard Block은 계약을 다시 연다

### 결정

- Soft Block: 사용자가 위험과 이유를 기록하고 진행 가능
- Hard Block: 일반 Override 불가, Contract·Policy 변경과 재승인 필요

### 이유

모든 경고를 절대 차단하면 생산성이 무너지고, 모든 차단을 Override 가능하게 하면 Control의 의미가 사라진다.

---

## DR-017 — Rollback 대신 Workspace Restore Point라고 부른다

### 결정

코드 작업공간의 기준점 복구 기능은 `Workspace Restore Point`로 부른다.

### 이유

Rollback은 DB, 배포, 메시지, 결제 등 외부 효과까지 되돌린다는 오해를 줄 수 있다.

### 트레이드오프

용어가 길지만 제품의 실제 보장 범위를 정확하게 전달한다.

---

## DR-018 — Worktree는 코드 격리 수단이지 전체 안전 배지가 아니다

### 결정

Worktree를 사용해 코드 상태를 격리할 수 있지만 데이터베이스, 네트워크, 비밀정보, 외부 서비스는 별도 통제를 적용한다.

### 이유

Worktree가 있다고 전체 작업이 안전하다고 표시하면 잘못된 신뢰를 준다.

---

## DR-019 — DevHarness 본체와 Project Baseline은 공유하고 Task 상태는 분리한다

### 결정

- DevHarness 본체·Project Baseline: Worktree 밖에서 공유
- Event·Evidence·Test·Restore Point: Task·Worktree별 분리
- 개인 설정: Git에 commit하지 않음

### 이유

Worktree마다 DevHarness를 재설치하면 관리 비용과 상태 충돌이 커진다. 반대로 모든 상태를 공유하면 서로 다른 작업 Evidence가 섞인다.

---

## DR-020 — Raw Evidence는 로컬, 공유는 선택적 요약이다

### 결정

Raw Evidence는 로컬에 저장하고 Git에서 제외한다. 팀 공유가 필요할 때만 민감정보가 제거된 요약 리포트를 생성한다.

### 이유

로그·명령·프롬프트·환경에는 비밀정보와 개인 작업 맥락이 포함될 수 있다. 개인 도구의 원본 데이터를 기본적으로 팀에 공개할 이유가 없다.

### 트레이드오프

팀원이 같은 Raw Evidence를 직접 재현하기 어렵다. 공유 리포트에 필요한 근거와 재현 명령을 선택적으로 포함한다.

---

## DR-021 — Event Log를 원본으로 하고 Dashboard State는 비동기 Projection한다

### 결정

- 중요한 사건은 append-only Event Log에 즉시 기록
- Dashboard용 상태·요약·다이어그램은 비동기로 생성
- Event head와 projected sequence로 최신성 표시

### 이유

매 명령마다 LLM 분석과 Dashboard 생성을 수행하면 에이전트 루프가 무거워진다. Event Log를 원본으로 두면 Projection을 다시 만들 수 있다.

### 트레이드오프

Dashboard가 잠시 늦을 수 있다. 지연 상태를 명확히 보여준다.

---

## DR-022 — Feature Validation은 기존 실행기를 연결한다

### 결정

DevHarness가 새로운 범용 테스트 엔진을 만들지 않는다. 프로젝트가 가진 Tool, API, CLI, Viewer, Test Runner를 Adapter로 연결한다.

### 이유

기존 제품을 복제하지 않고, 직접 검증 결과를 동일 Task Evidence에 연결하는 데 집중할 수 있다.

### 트레이드오프

프로젝트별 Adapter가 필요하다. Core contract를 공통화하고 첫 HWPX Adapter로 검증한다.

---

## DR-023 — HWPX Agent Plugin을 첫 도그푸딩 대상으로 삼는다

### 결정

첫 실제 적용은 사용자가 개발 중인 HWPX Agent Plugin에서 수행한다.

### 이유

- 사용자가 실제로 지속 개발할 프로젝트다.
- 파일 구조, Tool 호출, Viewer 호환성, E2E 검증이 함께 필요하다.
- DevHarness의 통제·Impact·Regression·Feature Validation을 실제로 시험할 수 있다.

### 트레이드오프

HWPX 특수성이 Core 설계를 오염시킬 수 있다. HWPX 관련 로직은 Adapter와 Fixture에 격리한다.

---

## DR-024 — Codex 우선이지만 Core와 Adapter를 분리한다

### 결정

Codex Desktop을 우선 지원한다. Control·Evidence·Guarantee·Dashboard Core는 Codex 고유 이벤트와 설정에 직접 결합하지 않는다.

### 이유

첫 구현 범위를 좁히면서도 이후 다른 코딩 에이전트로 확장할 구조를 유지한다.

### 트레이드오프

초기부터 Adapter interface를 설계해야 한다. 단, 실제로 존재하지 않는 공통점을 추상화하지 않고 Codex 구현에서 검증된 경계만 Core로 올린다.

---

## DR-025 — 모든 실행을 MCP로 만들지 않는다

### 결정

- Skill: 워크플로와 판단 지침
- MCP: 명시적으로 호출할 분석·검사·렌더링 Tool
- Adapter: Codex 공식 인터페이스 연결
- Local Core: 상태와 지속성

### 이유

MCP는 외부 Tool과 Context를 제공하는 방법이지 전체 애플리케이션 실행 계층이 아니다. App Server, SDK, Hooks가 더 적합한 역할이 있다.

---

## DR-026 — Superpowers는 외부 전역 Router로 동시에 사용하지 않는다

### 맥락

`using-superpowers`는 모든 대화 시작에서 Skill 사용을 강하게 라우팅한다. DevHarness Router와 동시에 활성화하면 우선순위와 책임이 충돌할 수 있다.

### 결정

- DevHarness가 유일한 상위 Router 역할 유지
- 필요한 Superpowers Skill만 선택적으로 Vendoring
- `using-superpowers`와 독립 bootstrap 제외
- MIT License와 출처 유지
- upstream version 고정 후 검증된 업데이트만 반영

### 이유

사용자는 하나의 인터페이스만 경험하고, DevHarness가 Preflight·개발 방법론·Postflight 순서를 통제할 수 있다.

### 트레이드오프

upstream 변경을 자동으로 받지 못한다. 명시적인 업데이트와 behavior regression test를 수행한다.

---

## DR-027 — Usage & Cost Analytics는 부가 기능이다

### 결정

토큰 사용량과 API 등가 비용은 Dashboard의 별도 분석 페이지로 둔다. Preflight와 실행 계약에서는 토큰·비용을 언급하지 않는다.

### 이유

재미와 도그푸딩에는 유용하지만 작업 권한·검증 계약의 핵심이 아니다. 가격과 수집 데이터가 불확실하면 신뢰를 해칠 수 있다.

---

## DR-028 — 기능 수보다 도그푸딩 Evidence를 포트폴리오 중심에 둔다

### 결정

다음을 반복 측정한다.

- 작업 이해 시간
- 최종 판단 시간
- raw diff·로그를 직접 연 횟수
- 범위 밖 변경 발견
- 검증 누락 발견
- 잘못된 완료 주장 발견
- DevHarness가 추가한 오버헤드

### 이유

“완성도가 높다”는 자기 평가보다 실제 전후 데이터와 실패 수정 이력이 강한 포트폴리오 Evidence다.

---

## 4. 선택하지 않은 접근과 이유

| 접근 | 선택하지 않은 이유 |
|---|---|
| 모든 명령마다 승인 | 승인 피로가 생기고 사용자가 내용을 읽지 않게 됨 |
| 권한 프리셋만 제공 | 작업별 실패 영향과 보호 대상을 반영하지 못함 |
| Dashboard에 모든 로그 표시 | 기존 읽기 병목을 그대로 재현 |
| AI 요약을 사실 원천으로 사용 | 에이전트 오류와 환각을 검증할 수 없음 |
| 코드 커버리지 하나로 완료 판정 | 중요한 경계·상태·통합 시나리오 누락 가능 |
| Impact Analysis가 완전하다고 주장 | 동적 관계와 관찰 불가 경로 존재 |
| 모든 실행 기능을 MCP로 구현 | Adapter·Local Core·Hooks 역할을 왜곡 |
| 자체 범용 테스트 실행기 제작 | 기존 Tool과 프레임워크를 불필요하게 복제 |
| 외부 Superpowers Router와 동시 전역 활성화 | 자동 라우팅 충돌과 책임 범위 확대 |
| Worktree를 전체 안전으로 표시 | 외부 효과·데이터·네트워크는 격리되지 않음 |
| Raw Evidence를 기본 Git 공유 | 비밀정보·개인 맥락 유출 가능 |
| Preflight 토큰·비용 예측 | 실행 계약과 직접 관계가 없고 신뢰하기 어려움 |

---

## 5. DevHarness가 보장하지 않는 것

이 섹션은 제품을 깎아내리기 위한 것이 아니다. 무엇을 확인할 수 있고 어디서 사람 판단이 필요한지 정확히 보여주기 위한 것이다.

- 임의의 프로젝트 전체가 안전하다는 보장
- 모든 영향 관계를 완전하게 찾는 보장
- 테스트 통과만으로 결함이 없다는 보장
- Worktree만으로 데이터·외부 효과가 격리된다는 보장
- Workspace Restore Point로 외부 효과를 되돌리는 보장
- 에이전트가 AGENTS.md를 항상 완벽히 준수한다는 보장
- Imported Task의 과거 행동과 정책 집행 보장
- 관찰할 수 없는 경로를 추론으로 대체한 보장

DevHarness는 대신 다음을 한다.

- 확인한 범위를 명시한다.
- Evidence State를 구분한다.
- 확인하지 못한 부분을 숨기지 않는다.
- 필요한 다음 검증과 사람 결정을 제시한다.

---

## 6. 포트폴리오 서사

### 문제

팀 프로젝트와 개인 개발에서 코딩 에이전트의 구현 속도는 빨랐지만, 변경 이해·영향 확인·테스트 판단·설명 준비가 병목으로 남았다.

### 가설

작업 시작부터 실행 계약과 Evidence를 관리하고, 결과를 기능 중심 Dashboard로 압축하면 통제와 검증을 약화시키지 않으면서 사람의 검토 시간을 줄일 수 있다.

### 설계

- 작업별 Control Profile
- 공식 Codex Harness 설정과 집행 검증
- Event·Evidence Pipeline
- Guarantee Matrix
- Impact 기반 Regression Gate
- 직접 Feature Validation
- Understand → Prove → Decide Dashboard

### 검증

HWPX Agent Plugin 개발에서 반복 도그푸딩하고, 시간 절감뿐 아니라 잘못된 완료 주장·누락·오버헤드를 함께 측정한다.

### 보여주는 역량

- Harness Engineering
- Risk-based Testing
- Evidence-based Validation
- Human-in-the-loop UX
- Adapter와 Core 경계 설계
- 기존 오픈소스 방법론의 선택적 통합
- 실패와 한계를 숨기지 않는 품질 판단

---

## 7. 기술적으로 열린 결정

다음은 제품 의도가 모호해서 남긴 질문이 아니다. 구현 에이전트가 Technical Spike 후 ADR로 결정할 사항이다.

- Codex App Server·SDK·Hooks·파일 관찰의 실제 조합
- active config와 instruction source 검증 방법
- Rules·Sandbox·Approval의 안전한 probe
- HWPX Impact Analysis 구현 방법
- Event Log format과 storage engine
- Dashboard framework와 SVG renderer
- Superpowers Vendoring 세부 Skill 목록
- 민감정보 redaction과 encryption

사용자에게 질문하기 전에 대안·Evidence·생산성 비용·추천안을 제시한다.

---

## 8. 설계 변경 규칙

기능이나 구조를 바꿀 때 다음을 기록한다.

1. 어떤 실제 문제 때문에 변경하는가
2. 기존 결정이 왜 충분하지 않은가
3. 고려한 대안
4. 선택한 안과 이유
5. 새로 생기는 위험과 비용
6. Dashboard·Control·Roadmap에 미치는 영향
7. 도그푸딩으로 어떻게 검증할 것인가

중요한 변경은 ADR과 이 문서를 함께 갱신한다.

---

## 9. 한 문장 설명

> **DevHarness는 에이전트가 만든 결과를 사람이 다시 처음부터 조사하는 병목을 줄이기 위해, 작업 경계를 설계하고 실제 통제와 검증 Evidence를 연결해 사용자가 결과를 이해하고 책임 있게 판단하도록 만드는 개인용 개발 하네스다.**

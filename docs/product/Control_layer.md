# DevHarness Control Layer

- **문서 상태:** 제품 원칙과 책임 경계가 확정된 설계 초안
- **작성 기준일:** 2026-09-03
- **대상:** DevHarness 구현을 담당할 에이전트
- **우선 사용 환경:** Codex Desktop 기반 로컬 개발
- **첫 도그푸딩 대상:** HWPX Agent Plugin
- **포함 책임:** Control, Execution Tracking, Assurance
- **연계 문서:** `Dashboard_layer.md`, `향후계획.md`, `Design_Rationale.md`

> 이 문서는 단순한 권한 설정 화면을 정의하지 않는다. DevHarness가 작업마다 실행 계약을 만들고, 그 계약이 실제로 작동했는지 검증하고, 검증된 범위에서만 완료와 통제를 주장하게 만드는 기술 계층을 정의한다.

---

## 1. Control Layer의 목적

DevHarness Control Layer의 목적은 사용자가 `전체 권한`, `승인 요청`, `읽기 전용` 같은 일반 모드를 직접 고르게 하는 것이 아니다.

> **프로젝트와 작업의 실패 영향을 분석하여, 해당 작업에 맞는 통제 경계·승인 조건·검증 기준을 포함한 Task Execution Contract를 생성하고 실제 집행 여부를 Evidence로 증명한다.**

Control Layer가 답해야 하는 질문은 다음과 같다.

1. 이번 작업에서 Codex가 어디까지 읽고 수정할 수 있는가?
2. 어떤 파일·데이터·외부 효과를 보호해야 하는가?
3. 어떤 행동은 자동 허용하고, 어떤 행동은 승인이 필요한가?
4. 어떤 행동은 현재 계약에서 금지되는가?
5. 어떤 검증을 통과해야 완료를 주장할 수 있는가?
6. 설정이 존재한 것과 실제로 로드·집행된 것을 어떻게 구분하는가?
7. 어떤 경로는 관찰하거나 통제할 수 없는가?
8. 문제가 생겼을 때 코드 작업공간을 어느 기준점으로 복구할 수 있는가?

---

## 2. 책임 경계

개념적으로 DevHarness에는 네 책임이 있다.

```text
Control
작업 범위·권한·보호 대상·승인 조건 결정

Execution Tracking
Codex 실행 과정과 상태·이벤트·Worktree 추적

Assurance
영향 분석·테스트 설계·회귀 검증·Guarantee 판정

Dashboard
이해·직접 검증·최종 판단 UI
```

문서 수를 불필요하게 늘리지 않기 위해 `Execution Tracking`과 `Assurance`는 이 문서의 하위 영역으로 둔다. Dashboard의 사용자 경험은 `Dashboard_layer.md`에서 별도로 정의한다.

---

## 3. 핵심 도메인 객체

### 3.1 Project Baseline — 프로젝트 기본 통제 기준

프로젝트에서 반복적으로 유지해야 하는 공통 정보다.

- 프로젝트 구조와 주요 실행 경로
- 허용·보호 경로
- 민감 파일과 비밀정보 위치
- 기본 Sandbox와 Approval Policy
- 프로젝트 공통 Rules와 Hooks
- AGENTS.md instruction sources
- 표준 빌드·lint·테스트 명령
- 중요 기능·계약·데이터 흐름
- Worktree 초기화 방식
- Evidence 저장 위치

Project Baseline은 매 작업마다 전체 재분석하지 않는다. 다음 경우 갱신한다.

- 프로젝트 최초 연결
- 디렉터리·아키텍처·주요 계약이 크게 변경됨
- 의존성 또는 실행 환경이 크게 변경됨
- 통제 설정이 변경됨
- Baseline이 오래됐거나 충돌 Evidence가 발견됨
- 사용자가 재분석을 요청함

`큰 변경`의 자동 감지 기준은 Technical Spike에서 검증한다.

### 3.2 Task Overlay — 작업별 추가 통제

Project Baseline 위에 이번 작업에서만 적용되는 조건이다.

- 수정 가능한 구체적 범위
- 이번 작업에서 추가로 보호할 대상
- 일시적으로 필요한 네트워크·패키지·도구 권한
- 작업별 승인 트리거
- 완료 조건과 검증 기준
- Soft Block·Hard Block 판정 기준

Task Overlay는 기본 통제를 강화할 수 있다. 기본 범위를 넓혀야 할 경우 다음 조건을 만족해야 한다.

- 필요한 권한과 범위가 구체적으로 표시됨
- 이유가 설명됨
- 해당 Task로 기간이 제한됨
- 사용자가 명시적으로 승인함
- 작업 종료 후 자동 해제됨

### 3.3 Task Execution Contract — 작업 실행 계약

Project Baseline과 Task Overlay를 결합해 만든 최종 실행 계약이다.

최소 포함 항목:

1. 작업 목표와 범위
2. 수정 허용 경로
3. 보호 대상
4. Sandbox·네트워크·도구 권한
5. Approval Triggers
6. Rules와 Hooks
7. 필수 검증과 완료 기준
8. Restore Point
9. Gate 기준
10. 관찰·집행할 수 없는 경로

### 3.4 Managed Task / Imported Task

- **Managed Task:** 해당 작업이 DevHarness Preflight를 거친 뒤 시작됨
- **Imported Task:** 이미 시작됐거나 완료된 작업을 나중에 DevHarness로 가져옴

구분 기준은 프로젝트가 새것인지 기존인지가 아니다. **해당 작업이 Preflight를 거쳤는지**다.

Imported Task에서 가능한 것:

- 현재 diff 분석
- 현재 코드 기준 테스트 실행
- 제한적인 연관 기능 분석
- 사후 Task Review

Imported Task에서 기본적으로 보장할 수 없는 것:

- 작업 시작 시점의 실제 정책 상태
- 과거 전체 에이전트 행동
- 변경 전 테스트 기준선
- 이미 발생한 외부 효과
- 당시 Sandbox·Approval·Hook 집행

---

## 4. 전체 생명주기

```text
1. Project Context 확인
   ├─ 기존 프로젝트: Project Context Profiler
   └─ 신규 프로젝트: Adaptive Preflight Interview

2. Project Baseline 확인·갱신

3. Task Overlay 생성

4. Task Execution Contract 컴파일

5. Local HTML/SVG Preview 제공

6. 사용자 승인

7. Workspace Restore Point 생성

8. Codex 작업 실행 및 Event Capture

9. Completion Claim 감지

10. Impact Analysis

11. Test Design / Regression Gate

12. Control Validation

13. Guarantee Matrix 판정

14. Task Guarantee Report 생성

15. Dashboard Task Review

16. 사용자 결과 판단
```

작업 중에는 가벼운 구조화 Event를 우선 기록한다. 무거운 분석·요약·시각화는 작업 종료 후 수행한다.

---

## 5. Project Context Profiler와 Adaptive Preflight Interview

### 5.1 기존 프로젝트

기존 프로젝트에서는 사용자에게 프로젝트 구조를 처음부터 설명하게 하지 않는다.

`Project Context Profiler`가 먼저 다음을 분석한다.

- 언어·프레임워크·패키지 구조
- 테스트·빌드·lint 명령
- Git·Worktree 상태
- Codex 설정 계층
- AGENTS.md와 instruction scope
- Rules·Hooks·Sandbox·Approval 설정
- 민감 파일과 외부 서비스
- 주요 기능·계약·데이터 흐름
- HWPX Plugin의 Tool/API/파일 처리 경로

Profiler는 분석 결과와 함께 추천 Project Baseline 및 Task Contract 초안을 제시한다. 사용자가 부적절하다고 판단하면 `Control Profile Interview`로 전환해 필요한 부분만 보완한다.

### 5.2 신규 프로젝트

신규 프로젝트에서는 고정된 5~6개 문항을 일괄 제시하지 않는다. 큰 위험 경계에서 세부 조건으로 좁혀 가는 적응형 분기를 사용한다.

첫 판단 축 예:

- 작업이 실패했을 때 영향 범위
- 외부 세계에 발생할 수 있는 효과
- 보호해야 할 데이터와 비밀정보
- 실행 환경과 배포 가능성
- 검증 가능한 완료 조건

### 5.3 인터뷰 UX 원칙

- 한 번에 한 가지 실제 결정만 질문한다.
- 답이 사용자 경험·권한·보장 범위를 바꾸는 경우에만 묻는다.
- 질문 전에 현재 분석 결과와 추천값을 짧게 제시한다.
- 선택지는 구체적인 결과 차이를 설명한다.
- `대충 골라도 됨` 같은 표현은 사용하지 않는다.
- 안전하게 추론할 수 있는 값은 자동 제안한다.
- `확인할 수 없음`을 허용하되, 그 결과 생기는 제한을 명시한다.
- 사용자가 기술 라이브러리나 Git 명령 같은 세부사항을 바닥부터 선택하게 하지 않는다.

### 5.4 인터뷰 출력

- Project Baseline 변경안
- Task Overlay
- Soft/Hard Gate 기준
- 생성·수정할 설정 파일
- 예상되는 통제 경계 Before / After
- 설정 충돌
- 확인 불가능한 경로
- 사용자 승인이 필요한 항목

---

## 6. Control Profile 생성·검토·적용

### 6.1 관리 대상

DevHarness는 공식 설정 경로를 통해 다음을 생성·수정·검토할 수 있다.

- `config.toml`
- `AGENTS.md` 및 필요 시 scope별 instruction file
- Rules
- Hooks
- Sandbox 설정
- Approval Policy
- MCP·Plugin 설정
- DevHarness 자체 Project Baseline과 Task Overlay

Codex Desktop 앱 내부 코드를 수정하지 않는다. 공식 설정·확장·관찰 인터페이스를 통해 관리한다.

### 6.2 Preview

적용 전 로컬 HTML/SVG Preview를 생성한다.

- 적용 전/후 권한 경계
- 변경되는 설정 파일
- 수정 가능·보호 경로
- 자동 허용·승인·금지 행동
- 검증 기준
- 충돌·override·우선순위
- 관찰 불가능 영역

Preview는 짧은 기술 캡션과 다이어그램을 함께 사용한다. 사용자가 전체 TOML과 Rules를 읽지 않아도 실제 차이를 이해할 수 있어야 한다.

### 6.3 적용 원칙

- 기존 사용자 설정을 무조건 덮어쓰지 않는다.
- Config precedence를 계산해 최종 유효값을 보여준다.
- 프로젝트가 신뢰되지 않아 project-local 설정이 무시되는 경우를 감지한다.
- 같은 계층에서 중복 Hooks 표현 등 충돌이 있으면 경고한다.
- 적용 전 diff와 복구 방법을 제공한다.
- 개인 설정은 기본적으로 Git에 commit하지 않는다.

Codex의 config는 여러 계층에서 로드되며 project-local `.codex/` 설정은 trusted project에서만 활성화된다. 구현 시 현재 공식 precedence와 trust 동작을 다시 검증해야 한다.

---

## 7. 권한·정책 모델

모든 관찰 가능한 행동은 정책 평가 대상이지만, 모든 행동마다 사용자 승인을 요청하지 않는다.

### 7.1 행동 처리 방식

1. **Automatic Allow & Observe**  
   가역적이고 범위가 명확한 일상 작업

2. **Isolated Execution & Validate**  
   영향 범위가 불확실하지만 Worktree·Sandbox 등으로 안전하게 조사 가능한 작업

3. **Scoped Approval**  
   데이터·외부 효과·비밀정보·권한 확장처럼 실제 사용자 판단이 필요한 작업

4. **Forbidden under Current Contract**  
   현재 계약에서 허용되지 않거나 안전한 실행 경로가 없는 작업

### 7.2 승인 요청 원칙

새 승인 요청은 다음 중 하나를 의미해야 한다.

- 새로운 중요한 결정
- 이미 승인된 범위를 넘어선 권한 확장
- 외부 세계에 새로운 효과 발생
- 보호 대상 접근
- Gate 기준 변경

반복적이고 동일한 안전 행동을 매번 묻지 않는다.

### 7.3 기본 안전선과 작업별 Gate

Soft Block과 Hard Block의 상태 모델은 고정한다. 그러나 어떤 상황이 어느 Gate에 해당하는지는 Project Baseline과 Preflight 결과에 따라 작업별로 생성한다.

다만 다음 범주의 행동은 강한 기본 안전선으로 취급한다.

- 파괴적 데이터 변경
- Schema migration
- 실제 배포·외부 공개
- 금전 지출
- 사용자를 대표하는 메시지 전송
- 비밀정보 원문 공개
- 보호 데이터를 신뢰 경계 밖으로 전송

구체적인 분류와 허용 방식은 해당 작업 계약에서 확정한다.

---

## 8. Codex Adapter와 Plugin 구성

### 8.1 책임 분리

```text
Skill
질문 흐름, 판단 기준, 테스트 관점, 결과 해석

Codex Adapter
Codex의 공식 설정·이벤트·승인·실행 인터페이스 연결

Local Core
정책 컴파일, Event Store, Evidence, Projection, 상태 관리

MCP Tools
에이전트가 명시적으로 호출할 분석·검사·렌더링 기능

Dashboard
결과 조회와 사용자 상호작용
```

모든 실행 기능을 MCP로 만들지 않는다. MCP는 외부 도구와 컨텍스트를 제공하는 인터페이스이며, 깊은 Codex client 통합은 App Server, 자동화는 SDK, 생명주기 개입은 Hooks가 더 적합할 수 있다. 정확한 조합은 Technical Spike에서 결정한다.

### 8.2 DevHarness Skills — 작업명 기준

- `dev-harness`: 단일 진입 Router
- `project-context-profiler`: 기존 프로젝트 분석
- `control-profile-interview`: 적응형 사전 인터뷰
- `control-profile-compiler`: 설정·계약 생성 지침
- `control-profile-lint`: 충돌·과잉 권한·누락 검사
- `control-validation`: 적용된 통제의 실제 작동 검증
- `test-design-guide`: 요구사항과 영향에 맞는 테스트 관점 생성
- `impact-analysis-guide`: 연관 기능 판단과 설명 기준
- `regression-gate`: 완료 전 회귀 Evidence 판정

이 이름은 구현 시 변경할 수 있으나 책임은 유지한다.

### 8.3 MCP Tool 후보

MCP로 적합한 것은 명시적 입력과 구조화 결과가 필요한 도구다.

- 프로젝트 구조·설정 스캔
- Config/Rules/Hooks lint
- 통제 probe 실행
- Impact graph 생성
- 테스트 검색·실행·결과 정규화
- Preview HTML/SVG 렌더링
- Evidence 조회

다음은 Local Core 또는 Adapter 책임이 더 적합하다.

- Event Log의 지속적 기록
- 작업 상태 머신
- Codex approval event 처리
- Config precedence 관리
- Projection worker
- Worktree별 상태 격리

---

## 9. Control Validation

설정 파일을 만들었다는 사실만으로 통제가 작동한다고 표시하지 않는다.

### 9.1 검증 범위

최종적으로 다음 항목을 모두 검증 범위에 포함한다.

1. **File Presence & Syntax**  
   파일 존재, parse 가능, schema·문법 유효

2. **Configuration Loading**  
   현재 실행에서 실제 active source로 로드됐는가

3. **Instruction Loading**  
   기대한 `AGENTS.md` scope가 현재 작업에 적용됐는가

4. **Rules Matching & Enforcement**  
   대상 명령이 기대한 `allow / prompt / forbidden`으로 처리되는가

5. **Hooks Invocation**  
   기대한 lifecycle event에서 Hook이 실제 호출되는가

6. **Sandbox Enforcement**  
   파일시스템·네트워크 경계가 실제로 제한되는가

7. **Approval Policy Behavior**  
   승인 대상 행동이 실제로 요청·거절·허용 흐름을 거치는가

8. **Config Conflict & Precedence**  
   user, profile, project, nested project, CLI override 사이에서 최종값이 무엇인가

9. **MCP / Plugin Availability**  
   필요한 Tool과 Skill이 로드되고 호출 가능한가

10. **Test Command Execution**  
    기준 테스트 명령을 현재 환경에서 실행할 수 있는가

11. **Unobservable Paths**  
    현재 Adapter와 Hook으로 관찰·집행할 수 없는 행동은 무엇인가

### 9.2 Probe 원칙

- 실제 데이터를 손상하지 않는 안전한 probe를 사용한다.
- 차단 확인을 위해 의도적으로 위험한 실제 행동을 수행하지 않는다.
- 실패한 Hook이나 unavailable MCP가 fail-open으로 동작할 수 있는지 확인한다.
- probe 결과를 일반 실행 전체에 과도하게 일반화하지 않는다.
- 검증 시점·Codex 버전·config source를 Evidence에 남긴다.

### 9.3 Validation 결과

모든 항목은 다음 Evidence State 중 하나를 가진다.

| 상태 | 의미 |
|---|---|
| **Configured** | 설정 또는 파일에 정의됨 |
| **Loaded** | 현재 실행에서 읽힘 |
| **Enforced** | 실제 행동 경계를 강제함 |
| **Observed** | 행동·결과를 관찰했지만 통제하지 못함 |
| **Inferred** | 결과를 바탕으로 추론함 |
| **Unobserved** | 확인 경로가 없거나 검증하지 못함 |

`Configured → Loaded → Enforced`를 자동 승격하지 않는다. 각 단계마다 독립 Evidence가 필요하다.

---

## 10. Guarantee Matrix

### 10.1 역할

Guarantee Matrix는 DevHarness가 허세를 부리지 못하게 하는 **주장 규칙표**다.

- 어떤 말을 할 수 있는가
- 그 말을 하려면 어떤 Evidence가 필요한가
- 어떤 표현은 금지되는가
- 확인 후에도 어떤 위험이 남는가

매 작업의 결과를 Matrix에 누적하지 않는다. Matrix는 판정 규칙이고, 실제 작업 결과는 `Task Guarantee Report`에 저장한다.

### 10.2 초기 Matrix

| DevHarness가 할 수 있는 주장 | 필요한 Evidence | 허용되는 최소 상태 | 금지 표현 | 남은 위험 |
|---|---|---|---|---|
| Control Profile 파일을 생성했다 | 생성 파일 hash, diff, parse 결과 | Configured | 통제가 적용됐다 | 현재 Codex가 읽지 않았을 수 있음 |
| 특정 config 값이 현재 작업에 로드됐다 | active config source와 최종 resolved value | Loaded | 설정 파일에 있으니 집행됐다 | 다른 행동에서 효과가 다를 수 있음 |
| 특정 AGENTS.md 지침이 로드됐다 | 현재 instruction source 목록과 scope | Loaded | 에이전트가 항상 지침을 준수한다 | 모델이 지침을 위반할 가능성 |
| Rule이 특정 probe를 차단했다 | rule match, decision, command, 실행 결과 | Enforced | 모든 위험 명령을 차단한다 | 미매칭 명령·우회 경로 |
| Hook이 특정 event에서 호출됐다 | hook started/completed 또는 handler log | Observed | 모든 Hook이 항상 성공한다 | timeout·오류·비동기 누락 |
| Sandbox가 특정 경계를 막았다 | 안전한 probe의 deny 결과와 active sandbox mode | Enforced | 시스템 전체가 격리됐다 | Sandbox 밖 도구·외부 side effect |
| Approval Policy가 특정 행동에 적용됐다 | approval request·decision·result event | Enforced | 모든 위험 행동은 승인된다 | Tool annotation·관찰 경로 차이 |
| 설정 충돌을 식별했다 | source별 값과 precedence resolution | Observed | 다른 숨은 설정은 없다 | 미지원 source·버전 차이 |
| 필요한 MCP Tool이 호출 가능하다 | discovery 결과와 harmless invocation | Observed | Tool 결과가 항상 정확하다 | 외부 서버 상태·권한 변경 |
| Workspace Restore Point를 생성했다 | commit/patch/reference와 restore verification | Observed | 모든 외부 효과를 rollback할 수 있다 | DB·배포·메시지 등은 복구 대상 아님 |
| 실제 변경사항을 식별했다 | 시작 기준선과 종료 diff | Observed | 에이전트의 모든 행동을 관찰했다 | 외부 파일·서비스 변경 누락 가능 |
| 연관된 기능을 분석했다 | 분석 범위, dependency/data/trace 근거 | Observed 또는 Inferred 표시 | 영향 범위를 완전히 찾았다 | 동적 관계·미관찰 경로 |
| 관련 테스트를 실행했다 | 명령, 환경, 대상 commit, 결과 | Observed | 시스템 회귀가 없다 | 선택되지 않은 테스트·실환경 차이 |
| 정의한 회귀 범위에서 통과했다 | 변경 전/후 비교와 범위 정의 | Observed | 전체 시스템이 안전하다 | 범위 밖 회귀 가능성 |
| 기능을 직접 검증했다 | 입력, 예상값, 실제 결과, 사용자 관찰 | Observed | 모든 사용자 환경에서 정상이다 | 다른 입력·환경·외부 서비스 |
| Dashboard가 최신이다 | Event head와 projected sequence 일치 | Observed | 모든 원본 Evidence가 완전하다 | 수집 자체가 누락됐을 가능성 |

### 10.3 금지되는 전역 주장

다음 표현은 충분한 범위 정의 없이 사용하지 않는다.

- 전체 시스템이 안전하다
- 모든 회귀를 찾았다
- 영향이 없다
- 완벽하게 통제됐다
- 무결성이 보장된다
- 테스트가 충분하다
- Rollback 가능하다

대신 확인한 범위, Evidence, 미관찰 영역을 함께 말한다.

---

## 11. Task Guarantee Report

작업별 Report는 다음을 기록한다.

- Matrix Claim ID
- 이번 작업의 판정
- 사용된 Evidence
- Evidence State
- 대상 commit·worktree·환경
- 판정 시점
- 충돌 Evidence
- 남은 위험
- 사용자 Override 또는 수용

```text
Guarantee Matrix
      ↓ 규칙 적용
Task Evidence
      ↓ 판정
Task Guarantee Report
      ↓ 표현
Dashboard
```

---

## 12. Assurance: Impact Analysis

Impact Analysis는 회귀 테스트 선택과 인간 검토 병목 감소의 핵심이다.

### 12.1 분석 우선순위

1. 실제 diff
2. 데이터·Schema·파일 계약
3. 호출·의존 관계
4. Runtime Trace
5. 공유 도구·외부 서비스
6. 문서화된 기능 관계
7. LLM 추론

사용자 화면에서는 `연관된 기능`으로 표현한다. 내부적으로는 근거 유형과 확실성을 보존한다.

### 12.2 HWPX 도그푸딩에서 볼 대상

- 변경된 Tool/API contract
- HWPX package part와 relationship 사용 경로
- 공통 XML 처리·저장 유틸리티
- 뷰어 또는 downstream 소비 경로
- 같은 파일 구조를 읽고 쓰는 기능
- 오류 처리와 파일 손상 가능 경로
- 테스트 fixture와 실제 문서 호환성

구현 시 실제 HWPX Plugin 구조를 스캔해 구체화한다.

### 12.3 출력

- 분석한 범위
- 연관된 기능
- 연관 근거
- 필요한 검증
- 분석 제외 영역
- Unobserved 관계

완전성을 주장하지 않는다.

---

## 13. Assurance: Test Design Guide

Superpowers의 TDD는 Red → Green → Refactor 순서를 강제하는 개발 방법론이다. DevHarness는 어떤 테스트 관점을 선택해야 하는지 보완한다.

Preflight에서 요구사항과 Impact Analysis 초안을 기반으로 `Test Design Memo`를 생성한다.

고려할 테스트 기법:

- 동등 분할
- 경계값 분석
- 결정 테이블
- 상태 전이
- 오류 추정
- Statement·Branch coverage
- 정상·오류·복구 흐름
- 계약·호환성 테스트
- 변경 전후 회귀 비교

Test Design Memo는 강제 정답이 아니다. 선택한 기법, 선택 이유, 다루지 못한 위험을 기록한다.

---

## 14. Assurance: Regression Gate

### 14.1 위치

Superpowers 또는 일반 개발 흐름의 구현이 끝나고 에이전트가 완료를 주장할 때 실행한다.

```text
Test Design Memo
→ 구현 중 TDD·테스트
→ Completion Claim
→ Impact Analysis 갱신
→ 관련 테스트 선택
→ 변경 전/후 회귀 비교
→ Gate 판정
```

### 14.2 Gate 상태

- **Pass:** 이번 계약의 완료·검증 기준 충족
- **Soft Block:** 결과 수용을 권장하지 않지만 사용자가 이유를 기록하고 Override 가능
- **Hard Block:** 일반 Override 불가. 실행 계약·정책을 변경하고 다시 승인해야 함

어떤 실패가 Soft/Hard인지 고정 템플릿으로 일괄 결정하지 않는다. Project Baseline, Task Overlay, 실패 영향, 외부 효과를 기준으로 작업별 Gate 기준을 생성한다.

### 14.3 회귀 검증 원칙

- 가능하면 변경 전 관련 테스트 기준선을 확보한다.
- 변경 후 같은 테스트를 같은 의미의 환경에서 다시 실행한다.
- 새 기능 테스트가 회귀 테스트를 대신하지 않는다.
- Impact Analysis가 선택한 범위와 제외 영역을 공개한다.
- 테스트가 없으면 성공이 아니라 `No Adequate Test`로 남긴다.
- Mock과 실제 환경 결과를 구분한다.

---

## 15. Workspace Restore Point와 Worktree

### 15.1 명칭

`Rollback` 대신 `Workspace Restore Point`를 사용한다.

이 기능이 복구하는 범위:

- Git 작업공간
- 변경 patch
- Task 시작 commit 또는 branch 상태

기본적으로 복구하지 않는 범위:

- 데이터베이스
- 외부 API 요청
- 배포
- 메시지 전송
- 결제
- 공유 인프라

외부 효과는 별도 Evidence와 보상 가능성으로 관리한다.

### 15.2 Worktree 원칙

- 필요할 때 코드 상태를 Worktree로 격리한다.
- DevHarness 본체와 프로젝트 공통 Baseline은 Worktree 밖에서 공유한다.
- Event, Evidence, Test Result, Restore Point는 Task·Worktree별로 분리한다.
- Worktree가 전체 Sandbox나 외부 효과 격리를 의미하지 않는다.

### 15.3 설정과 상태 저장

프로젝트 내부의 개인 DevHarness 설정을 Git에 올리지 않는다.

권장 개념 구조:

```text
<OS user data>/DevHarness/<project-id>/
├─ project-baseline/
├─ worktrees/
│  └─ <worktree-id>/
│     ├─ tasks/
│     ├─ events/
│     ├─ evidence/
│     └─ reports/
└─ indexes/
```

프로젝트 내부 `.dev-harness/`가 필요하면 Git Ignore된 project ID·pointer·local override 정도만 둔다.

---

## 16. Event Store와 Projection

### 16.1 Canonical Event Log

명령과 중요한 사건이 끝날 때 append-only Event를 동기적으로 기록한다.

예:

- Task 생성
- Contract 승인
- Config 적용
- Hook 시작·완료
- Approval 요청·판정
- Tool 실행
- Test 실행
- Diff 변화
- Gate 판정
- 사용자 결정

### 16.2 Asynchronous Projection

Dashboard State는 Event Log를 읽는 worker가 비동기로 생성한다.

- 원본 Event는 빠르고 확실하게 기록
- 무거운 요약·Impact·Diagram은 비동기 처리
- Projection에는 마지막 반영 sequence 저장
- Dashboard는 Event head와 비교해 최신성 계산
- Projection은 원본 Log에서 재생성 가능

### 16.3 무결성 원칙

Dashboard가 최신인 것과 Event가 완전한 것은 다른 주장이다. Event 수집 공백이 있으면 Projection이 최신이어도 `Unobserved` 경로를 표시한다.

---

## 17. Evidence 보존·공유 정책

### 17.1 기본 정책

- Raw Evidence는 로컬 전용
- 기본적으로 Git Ignore
- 팀 공유는 사용자가 선택한 마스킹 요약만
- 민감정보 원문은 수집 단계에서 제거 또는 참조화
- 보존 기간은 사용자 설정 가능
- Task 삭제와 Evidence 삭제의 범위를 명확히 표시

### 17.2 Evidence 최소 메타데이터

- source
- timestamp
- project/task/worktree ID
- commit 또는 content hash
- collection method
- evidence state
- redaction status
- freshness
- conflict reference

---

## 18. Superpowers 통합 방향

### 18.1 결정

DevHarness는 유일한 상위 Routing Layer를 유지한다.

외부 Superpowers Plugin의 `using-superpowers`와 DevHarness Router를 동시에 전역 활성화하지 않는다. 두 Router의 우선순위가 고정적으로 보장되지 않고 책임이 겹칠 수 있기 때문이다.

### 18.2 선택적 Vendoring

Superpowers에서 검증된 방법론 중 필요한 Skill을 선택적으로 포함한다.

후보:

- brainstorming
- test-driven-development
- systematic-debugging
- writing-plans
- verification-before-completion
- subagent-driven-development
- requesting/receiving-code-review

원칙:

- `using-superpowers`와 독립 bootstrap은 포함하지 않음
- DevHarness namespace 사용
- 원본 출처, MIT License, copyright 유지
- upstream commit/version 고정
- 자동 업데이트 금지
- 변경 전 behavior test와 회귀 검증
- DevHarness Router가 작업 시점과 조합을 결정

### 18.3 DevHarness와의 역할 관계

```text
DevHarness Preflight
→ vendored brainstorming / planning / TDD 등
→ 구현
→ DevHarness Impact Analysis / Regression Gate
→ Task Guarantee Report
```

Superpowers 방법론을 흡수하더라도 DevHarness의 주 목적은 개발 방법론 자체가 아니라 통제·Evidence·검증·판단이다.

---

## 19. Technical Spikes — 구현 전 검증할 항목

다음은 사용자가 라이브러리 수준에서 선택할 문제가 아니다. 구현 에이전트가 공식 문서와 실험으로 확인한 뒤 ADR을 제출한다.

### TS-01 Codex Desktop Integration

비교 대상:

- Codex App Server
- Codex SDK
- Hooks
- Config·Rules·AGENTS 파일 기반 관리
- 로그·Event 관찰

확인할 것:

- Desktop 작업의 thread/turn/event 접근 가능성
- approval event와 hook event 관찰 가능성
- active config source 확인 방법
- 기존 Desktop UX를 유지할 수 있는지
- 실험적 API의 안정성

### TS-02 Control Validation Coverage

- Rules의 안전한 enforcement probe
- Hook fail-open/fail-closed 동작
- Sandbox filesystem/network probe
- Approval Policy probe
- 설정 precedence 충돌
- trusted/untrusted project 차이
- 관찰 불가능 경로

### TS-03 Impact Analysis

- HWPX Plugin의 의존·계약·파일 흐름 추출 가능성
- 정적 분석과 runtime trace의 조합
- 관련 테스트 매핑 정확도
- 분석 시간과 오버헤드

### TS-04 Event & Evidence Store

- macOS용 저장 경로
- append-only log format
- crash recovery
- redaction
- Projection rebuild

### TS-05 Superpowers Vendoring

- 필요한 Skill 목록
- 라이선스 고지
- namespace와 discovery 충돌
- upstream update 절차
- behavior test

---

## 20. 공식 기술 기준

구현 시 아래 공식 자료의 최신 내용을 다시 확인한다.

- [Codex App Server](https://developers.openai.com/codex/app-server)
- [Codex SDK](https://developers.openai.com/codex/codex-sdk)
- [Codex Config Basics](https://developers.openai.com/codex/config-basic)
- [Codex Rules](https://developers.openai.com/codex/rules)
- [Codex Hooks](https://developers.openai.com/codex/hooks)
- [Codex Sandbox and Approvals](https://developers.openai.com/codex/agent-approvals-security)
- [AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md)
- [Codex Worktrees](https://developers.openai.com/codex/environments/git-worktrees)
- [Codex Skills](https://developers.openai.com/codex/build-skills)
- [Agent Plugins Specification](https://agent-plugins.org/)
- [Superpowers Repository](https://github.com/obra/superpowers)

현재 공식 문서상 App Server는 approvals와 streamed agent events를 포함한 custom client 통합 인터페이스이며, SDK는 자동화 작업에 적합하다. Rules는 실험적 기능이고, project-local config·hooks·rules는 trusted project에서만 로드될 수 있다. Hooks는 scripts 또는 MCP tools를 lifecycle에 연결할 수 있지만 오류나 unavailable tool이 항상 작업을 막는 것은 아니므로 실제 검증이 필요하다.

---

## 21. Control Layer 수용 기준

- Project Baseline과 Task Overlay가 분리된다.
- Managed Task가 Preflight 없이 시작되지 않는다.
- Control Profile 적용 전에 diff와 Preview를 확인할 수 있다.
- 기존 설정을 덮어쓰기 전에 precedence와 충돌을 계산한다.
- Configured, Loaded, Enforced, Observed, Inferred, Unobserved를 구분한다.
- Rules, Hooks, Sandbox, Approval Policy, AGENTS, 설정 충돌을 실제 Validation 범위에 포함한다.
- 관찰할 수 없는 경로를 성공으로 표시하지 않는다.
- Impact Analysis 범위와 한계를 공개한다.
- 변경 전후 회귀 Evidence 없이 `회귀 없음`을 주장하지 않는다.
- Pass, Soft Block, Hard Block의 의미와 Override 기록이 유지된다.
- Raw Evidence는 로컬에 저장되고 마스킹 리포트만 선택적으로 공유된다.
- Worktree별 상태가 분리되며 DevHarness를 매 Worktree마다 재설치하지 않는다.
- Guarantee Matrix와 Task Guarantee Report가 분리된다.
- Dashboard가 사용하는 모든 주장은 Task Guarantee Report로 추적된다.

---

## 22. 구현 에이전트 지침

1. 즉시 코드를 작성하지 말고 `향후계획.md`의 Technical Spike와 Milestone 순서를 따른다.
2. 공식 Codex 동작을 추정하지 말고 현재 버전에서 probe로 확인한다.
3. 설정 파일 존재를 `Loaded`나 `Enforced`로 승격하지 않는다.
4. 모든 검증 결과에 대상 버전·환경·commit·source를 기록한다.
5. DevHarness 자체가 만든 설정 때문에 기존 프로젝트가 깨지는 경우를 테스트한다.
6. MCP, Skill, Local Core, Adapter를 일대일로 억지 분할하지 않는다.
7. HWPX 도그푸딩을 사용하되 Core를 HWPX 전용으로 만들지 않는다.
8. Preflight에서 토큰 사용량이나 비용을 제시하지 않는다.
9. 구현 중 새 기능을 추가하려면 Issue와 Design Rationale 변경을 먼저 제안한다.
10. “안전”, “완전”, “모든” 같은 표현은 Guarantee Matrix의 근거가 있을 때만 사용한다.

---

## 23. 한 문장 정의

> **DevHarness Control Layer는 프로젝트와 작업에 맞는 실행 계약을 생성하고 Codex의 설정·권한·행동·검증을 추적한 뒤, 실제 Evidence가 확인된 범위에서만 통제와 완료를 주장하게 만드는 계층이다.**

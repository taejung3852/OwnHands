# DevHarness Dashboard Layer

- **문서 상태:** 제품 방향이 확정된 설계 초안
- **작성 기준일:** 2026-09-03
- **대상:** DevHarness 구현을 담당할 에이전트와 향후 기획 검토자
- **우선 사용 환경:** Codex Desktop을 사용하는 개인 개발자
- **첫 도그푸딩 대상:** HWPX Agent Plugin
- **연계 문서:** `Control_layer.md`, `향후계획.md`, `Design_Rationale.md`

> 세부 기능의 보장 수준과 신뢰도는 `Control_layer.md`에 정의된 Evidence와 Guarantee 규칙을 통해 검증한다. 이 문서는 화면 모양보다 사용자가 어떤 판단 상태에 도달해야 하는지를 정의한다.

---

## 1. Dashboard Layer의 역할

DevHarness Dashboard는 코딩 에이전트가 만든 결과를 사용자가 빠르게 이해하고, 검증 근거를 확인하고, 직접 기능을 확인한 뒤, 결과를 받아들일지 결정하게 만드는 **작업 검토 인터페이스**다.

Dashboard가 답해야 하는 핵심 질문은 다음과 같다.

1. 이번 작업에서 실제로 무엇이 바뀌었는가?
2. 그 변화가 기능과 사용자 흐름에 어떤 의미가 있는가?
3. 함께 확인해야 할 연관된 기능은 무엇인가?
4. 무엇을 어떤 근거로 검증했는가?
5. 무엇은 검증하지 못했는가?
6. 적용된 Harness 통제가 실제로 어느 수준까지 확인됐는가?
7. 사용자가 지금 직접 확인하거나 결정해야 할 것은 무엇인가?

Dashboard는 다음이 아니다.

- 모든 명령과 로그를 그대로 나열하는 화면
- 에이전트가 작성한 요약문을 최종 사실처럼 보여주는 화면
- 하나의 점수로 작업 전체의 안전성을 단정하는 화면
- Codex의 실행기, Git, 테스트 프레임워크를 그대로 복제하는 화면
- 포트폴리오용 장식 화면

---

## 2. 최상위 제품 기준: Understand → Prove → Decide

### 2.1 Understand — 이해

사용자는 raw diff와 긴 로그를 처음부터 읽지 않아도 다음을 자기 말로 설명할 수 있어야 한다.

- 요청한 작업
- 에이전트가 실제로 수행한 작업
- 새로 생기거나 달라진 기능
- 구현 방식의 핵심 이유
- 요청 범위 밖에서 추가로 발생한 변경
- 연관된 기존 기능과 데이터 흐름
- 검증이 필요한 이유

### 2.2 Prove — 근거 확인

각 설명은 다음 Evidence로 내려갈 수 있어야 한다.

- 사용자 요청과 작업 범위
- 작업 시작 기준선
- 실제 diff와 변경 파일
- 설정과 정책의 적용·집행 결과
- 테스트·빌드·실행 결과
- 변경 전후 회귀 결과
- 직접 기능 검증 결과
- 실패·충돌·미관찰 영역

### 2.3 Decide — 판단

사용자는 다음 결정을 구분해 내릴 수 있어야 한다.

- 결과 수용
- 수정 요청
- 결과 거절
- 추가 검증 요청
- 남은 위험을 이해한 상태에서 수용

다음 세 결정은 자동으로 묶지 않는다.

1. 위험 행동을 실행하기 전의 승인
2. 완료된 작업 결과의 수용
3. merge, branch 정리, 배포 등 실제 통합 행동

---

## 3. 인간 병목을 줄이는 UX 원칙

### 3.1 기능·사용자 흐름 우선

첫 화면은 파일과 코드보다 기능 변화를 먼저 보여준다.

```text
기능·사용자 흐름의 변화
        ↓
연관된 기능과 확인 우선순위
        ↓
검증 결과와 직접 확인 경로
        ↓
Diff·명령·로그·Trace 등 상세 Evidence
```

### 3.2 ELI5와 ADHD 친화적 표현 원칙

여기서 ELI5는 유아적인 말투가 아니다. 복잡한 작업을 짧고 구조적으로 읽게 만드는 표현 방식이다.

- 결론과 현재 필요한 행동을 먼저 보여준다.
- 한 화면에 모든 세부사항을 펼치지 않는다.
- 카드, 체크리스트, 다이어그램, 상태 비교를 우선한다.
- 상세 기술 정보는 Progressive Disclosure 방식으로 펼친다.
- 긴 서술보다 `무엇 / 이유 / 근거 / 다음 행동`을 분리한다.
- 사용자가 같은 내용을 여러 위치에서 반복해서 읽게 하지 않는다.
- 중요한 위험은 눈에 띄게 하되, 모든 항목을 경고처럼 보이게 하지 않는다.

### 3.3 블랙박스 우선, 화이트박스 드릴다운

- **블랙박스:** 기능이 사용자 관점에서 어떻게 달라졌는가
- **화이트박스:** 어떤 파일, 코드, 명령, 정책, 테스트가 그 변화를 만들었는가

기본 화면은 블랙박스 중심이다. 의심하거나 더 알아야 할 때 화이트박스 Evidence를 펼친다.

### 3.4 Dashboard를 위한 사전 질문 금지

Dashboard 템플릿을 정하려고 작업 전에 사용자에게 유형을 선택시키지 않는다. 실제 변경 결과를 기준으로 적응형 보고서를 구성한다.

사전 질문은 권한, 외부 효과, 보장 범위처럼 Control 계약을 바꾸는 경우에만 허용한다.

### 3.5 단정 대신 근거와 범위

`완료`, `통과`, `안전` 같은 단어는 범위 없이 사용하지 않는다.

나쁜 예:

> 회귀 테스트 통과. 영향 없음.

좋은 예:

> DevHarness가 이번 변경과 연관된 것으로 식별한 8개 시나리오 중 7개를 실행해 통과했다. 외부 HWPX 뷰어 호환성 시나리오 1개는 실행 환경이 없어 확인하지 못했다.

정량 결과에는 반드시 다음을 함께 보여준다.

- 어떤 범위를 전체로 정의했는가
- 무엇을 기준으로 항목을 선택했는가
- 제외된 항목은 무엇인가
- 분석할 수 없었던 영역은 무엇인가

---

## 4. Dashboard 정보 구조

Dashboard는 다음 다섯 영역으로 구성한다.

| 영역 | 핵심 역할 | 우선순위 |
|---|---|---|
| **Task Review** | 작업 하나의 변화·영향·검증·판단 | 핵심 |
| **Feature Validation** | 특정 기능을 직접 블랙박스/E2E 방식으로 확인 | 핵심 |
| **Harness Status** | 현재 적용된 Control Profile과 실제 검증 상태 확인 | 핵심 |
| **Audit & History** | 작업별 실행·승인·검증·판단 이력 추적 | 핵심 이후 확장 |
| **Usage & Cost Analytics** | 토큰 사용량과 API 등가 비용 분석 | 부가 기능 |

전체 기능 범위는 처음부터 문서와 GitHub 상위 Issue에 보존한다. 구현은 각 화면이 요구하는 Evidence가 준비되는 순서로 진행한다.

---

## 5. Task Review Page

Task Review는 Dashboard의 기본 진입점이다.

### 5.1 작업 헤더

- 작업 제목 또는 요청 요약
- `Managed Task / Imported Task`
- 작업 상태
- 시작·종료 시점
- 기준 branch, worktree, commit
- Dashboard 최신성 상태
- 현재 Gate 상태: `Pass / Soft Block / Hard Block`

`Managed Task`는 해당 작업이 DevHarness Preflight를 거친 작업이다. `Imported Task`는 이미 진행 중이거나 완료된 작업을 나중에 가져온 경우다. Imported Task에서는 과거 통제 집행이나 전체 행동 관찰을 보장하지 않는다.

### 5.2 이번 작업으로 무엇이 바뀌었나

기능 관점에서 다음을 보여준다.

- 새롭게 가능해진 기능
- 변경된 기존 동작
- 제거되거나 제한된 동작
- 사용자 흐름과 데이터 흐름의 변화
- 요청 범위 밖 변경
- 구현 방식의 핵심 이유

정확한 카드 수나 문장 수는 고정하지 않는다. 작업의 복잡도에 맞추되 첫 화면에서 핵심을 파악할 수 있어야 한다.

### 5.3 Before / After Diagram

다음 변화를 시각화한다.

- 사용자 흐름
- 기능 호출 흐름
- 데이터와 계약 흐름
- HWPX 처리 단계와 도구 호출
- 외부 도구·뷰어·저장소 연결

표현 원칙:

- 실제 기준선과 최종 상태에서 생성한다.
- 추가·수정·삭제된 경로를 구분한다.
- 각 요소를 클릭하면 관련 diff, test, trace로 이동한다.
- Evidence가 부족하면 그릴 수 있는 범위만 표시한다.
- 다이어그램은 이해 보조 수단이며, 증명 자체로 사용하지 않는다.

상호작용이 필요한 경우 SVG를 우선 고려한다. 구현 라이브러리는 기술 검증 후 선택한다.

### 5.4 연관된 기능

사용자 화면에서는 `영향 후보` 대신 **연관된 기능**이라고 표현한다.

각 항목은 다음 정보를 가진다.

- 연관된 기능 또는 동작
- 이번 변경과 연결되는 이유
- 예상 가능한 실패 형태
- 확인 우선순위
- 현재 검증 상태
- 권장 검증 방법
- 연결된 Evidence

확인 우선순위는 다음 세 단계다.

- **필수 확인:** 직접적인 데이터·계약·호출 관계가 있거나 실패 영향이 큰 항목
- **권장 확인:** 간접 관계 또는 분석 불확실성이 있는 항목
- **참고:** 작업 이해와 후속 검토에 유용한 항목

내부적으로는 연관 근거를 구분한다.

- 직접 의존 관계
- 공유 데이터·Schema·계약
- Runtime에서 관찰된 관계
- 정적 분석 또는 LLM 기반 추론
- 분석 불가 또는 미관찰

이 내부 구분은 상세 Evidence에서 확인할 수 있어야 한다.

### 5.5 Verification Status

검증 결과를 하나의 성공 배지로 합치지 않는다.

| 상태 | 의미 |
|---|---|
| **Passed** | 정의된 범위와 환경에서 기대 결과 확인 |
| **Failed** | 기대 결과와 다르거나 테스트 실패 |
| **Not Run** | 필요한 검증을 실행하지 않음 |
| **No Adequate Test** | 해당 동작을 충분히 다루는 테스트가 없음 |
| **Inconclusive** | 실행했지만 결과를 신뢰하거나 해석하기 어려움 |
| **Unknown** | 영향 또는 검증 범위를 판단할 Evidence가 부족함 |

검증 종류는 분리한다.

- 변경 기능 확인 테스트
- 변경 전후 회귀 검증
- 빌드·lint·정적 검사
- 사용자의 직접 기능 검증
- Control Validation

### 5.6 미검증·충돌 항목

`미검증`이라는 라벨만 보여주지 않는다. 각 항목에 다음을 제공한다.

1. 무엇을 확인하지 못했는가
2. 왜 확인하지 못했는가
3. 어떤 현실적 문제가 생길 수 있는가
4. 현재 확보된 Evidence는 무엇인가
5. 다음 행동은 무엇인가

Evidence가 충돌할 경우 출처별로 분리한다.

예:

- 에이전트 주장: 테스트 통과
- 실제 로그: 1개 실패
- Dashboard 판단: 완료 주장과 Evidence 충돌, Soft Block

### 5.7 Task Guarantee Report

Task Review에는 `Task Guarantee Report`를 연결한다.

- Guarantee Matrix는 “어떤 Evidence가 있어야 어떤 주장을 할 수 있는가”를 정한 규칙표다.
- Task Guarantee Report는 “이번 작업에서 실제로 어떤 Evidence를 확보했고 무엇까지 말할 수 있는가”를 기록한 결과표다.

표시 예:

| 주장 | 현재 판정 | 근거 | 남은 한계 |
|---|---|---|---|
| 프로젝트 설정이 로드됨 | 확인됨 | 현재 세션의 active config source | 하위 디렉터리 override는 별도 확인 |
| Rules가 대상 명령을 차단함 | 확인됨 | 의도적 probe의 forbidden 결과 | 다른 명령 패턴 전체를 보장하지 않음 |
| 회귀가 없음 | 제한적 확인 | 식별된 연관 시나리오 7개 통과 | 분석 불가 경로 1개 |

### 5.8 Decision Panel

지원하는 판단:

- 결과 수용
- 수정 요청
- 결과 거절
- 추가 검증 요청
- 남은 위험을 이해한 상태에서 수용

Soft Block을 Override하려면 다음을 기록한다.

- 사용자가 확인한 위험
- 진행하는 이유
- 수용한 미검증 범위
- 후속 조치 필요 여부

Hard Block은 일반 Override 대상이 아니다. 실행 계약이나 정책을 변경하고 다시 승인받아야 한다.

---

## 6. Feature Validation Page

### 6.1 목적

자동 테스트 결과를 읽는 것에서 끝내지 않고, 사용자가 특정 기능을 직접 실행하고 관찰하게 한다.

첫 도그푸딩에서는 HWPX Agent Plugin의 기능 단위 검증을 우선한다.

예:

- HWPX 문서 열기·분석
- 필드 또는 콘텐츠 수정
- 결과 파일 저장
- 수정된 파일을 뷰어에서 확인
- 원본 구조와 호환성 확인
- 실패 입력과 손상 파일 처리 확인

### 6.2 기본 흐름

```text
Task Review에서 기능 선택
→ 추천 시나리오 또는 사용자 시나리오 선택
→ 입력·환경·예상 결과 확인
→ 기존 실행기나 Adapter를 통해 기능 실행
→ 실제 결과·파일·Trace 확인
→ 정상 / 문제 있음 / 판단 보류 기록
→ 결과를 Task Evidence에 연결
```

### 6.3 실행기 책임 경계

DevHarness는 범용 테스트 프레임워크를 새로 만들지 않는다.

- 프로젝트가 가진 테스트 명령과 실행기를 호출한다.
- HWPX Plugin의 MCP Tool, API, CLI, 뷰어 등 기존 실행 경로를 Adapter로 연결한다.
- Dashboard는 시나리오 선택, 실행 요청, 결과 비교, Evidence 연결을 담당한다.
- 실제 권한과 외부 효과 통제는 Control Layer가 담당한다.

### 6.4 화면 정보

- 검증 대상 기능
- 연관된 기능으로 선택된 이유
- 입력과 실행 환경
- 예상 결과
- 실제 결과
- 생성·수정된 파일
- 파일 구조 또는 문서 상태 Before / After
- Tool Call과 오류
- 자동 테스트 결과와의 차이
- 사용자의 최종 관찰

---

## 7. Harness Status Page

Harness Status는 현재 프로젝트와 작업에 적용된 통제 상태를 보여준다.

### 7.1 보여줄 대상

- Project Baseline
- 현재 Task Overlay
- `config.toml`
- `AGENTS.md`와 활성 instruction source
- Rules
- Hooks
- Sandbox
- Approval Policy
- 활성 Plugin·Skill·MCP
- Worktree·Workspace Restore Point
- 설정 충돌과 precedence
- 관찰할 수 없는 경로

### 7.2 상태 표현

다음 상태를 섞지 않는다.

| 상태 | 의미 |
|---|---|
| **Configured** | 설정에 작성되거나 파일이 생성됨 |
| **Loaded** | 현재 실행에서 실제로 읽힘 |
| **Enforced** | 실제 행동을 허용·차단하거나 경계를 강제함 |
| **Observed** | 행동 또는 결과를 관찰했지만 통제하지는 못함 |
| **Inferred** | 결과를 바탕으로 추론함 |
| **Unobserved** | 현재 통합 경로에서는 확인할 수 없음 |

Harness Status의 핵심은 “설정 파일이 있다”가 아니라 “현재 작업에서 실제로 무엇이 확인됐는가”다.

### 7.3 Control Profile Preview 연결

Control Profile을 적용하기 전에는 로컬 HTML/SVG Preview로 다음을 보여준다.

- 적용 전과 적용 후의 권한 경계
- 수정 가능 범위
- 보호 대상
- 승인 트리거
- 검증 기준
- 설정 충돌과 예상 변경 파일

승인 후에는 해당 Preview와 최종 적용 결과를 Harness Status에서 비교할 수 있어야 한다.

---

## 8. Audit & History

Audit은 조직 규정 준수를 위한 대형 감사 시스템이 아니라 개인 개발자가 작업 결정의 맥락을 복원하기 위한 추적 기록이다.

작업별로 다음을 남긴다.

- 언제 어떤 요청으로 시작했는가
- 어떤 Project Baseline과 Task Overlay가 적용됐는가
- 어떤 승인이 발생했는가
- 어떤 정책이 실제로 집행됐는가
- 무엇이 변경됐는가
- 어떤 테스트와 직접 검증을 수행했는가
- Soft/Hard Block과 Override가 있었는가
- 사용자가 왜 결과를 수용·수정·거절했는가

Raw Event Log를 그대로 읽게 하지 않고 Task 단위 Audit Report로 압축한다. 필요하면 마스킹된 Markdown 또는 HTML 리포트로 Export할 수 있다.

---

## 9. Usage & Cost Analytics

### 9.1 위치와 우선순위

Usage & Cost Analytics는 재미 요소와 도그푸딩 분석에는 유용하지만 DevHarness의 실행 계약에는 포함하지 않는다.

- Preflight 대화에서 예상 토큰·비용을 언급하지 않는다.
- 토큰 사용량 때문에 작업 시작 승인을 요구하지 않는다.
- 핵심 Control·Verification 흐름과 분리된 Dashboard 페이지로 둔다.

### 9.2 제공할 수 있는 정보

데이터를 신뢰할 수 있게 수집할 수 있을 때 다음을 제공한다.

- 작업별 토큰 사용량
- 기능 또는 프로젝트별 사용량
- 모델별 입력·출력·캐시 토큰
- 최근 7일 사용량
- 최근 30일 사용량
- 작업당 평균·중앙값
- 사용량이 큰 작업 유형
- 동일 사용량을 API로 처리했을 때의 등가 비용 추정

API 등가 비용은 실제 지출이나 절감액이 아니다. 표시할 때는 모델, 가격 기준일, 측정 범위, 추정 여부를 함께 제공한다. 가격 정보가 신뢰할 수 없으면 비용은 숨기고 토큰 집계만 보여준다.

### 9.3 더 중요한 도그푸딩 지표

- 작업 완료 후 이해까지 걸린 시간
- 결과 수용 결정까지 걸린 시간
- 직접 연 raw diff·로그 수
- 발견한 요청 범위 밖 변경
- 발견한 검증 누락
- 추가 검증 요청 수
- 잘못된 완료 주장을 발견한 수
- DevHarness가 추가한 오버헤드

이 지표가 Usage 자체보다 포트폴리오 가치와 제품 효용을 더 직접적으로 증명한다.

---

## 10. Event Log와 Dashboard 최신성

Dashboard는 원본이 아니다. 원본은 append-only 방식의 Canonical Event Log다.

```text
Codex/DevHarness 사건 발생
→ Event Log에 동기적으로 기록
→ Projection Worker가 비동기로 Dashboard State 갱신
→ Dashboard가 Event Head와 Projected Sequence 비교
```

Dashboard는 다음 상태를 표시한다.

- 최신 이벤트까지 반영됨
- 현재 갱신 중이며 N개 이벤트 지연
- Projection 실패
- 원본 로그에서 재구성 필요

Projection은 폐기하고 Event Log에서 다시 생성할 수 있어야 한다. Dashboard가 잠시 오래된 상태여도 원본 Evidence가 손상돼서는 안 된다.

---

## 11. Evidence 저장과 공유

### 11.1 Raw Evidence

- 기본적으로 로컬 전용
- Git에 commit하지 않음
- 작업·Worktree별로 분리
- 프로젝트 전체 Dashboard에서는 project ID를 기준으로 통합 조회
- 민감정보 원문을 가능한 한 저장하지 않음
- 사용자가 삭제·보존 정책을 설정할 수 있음

### 11.2 공유 가능한 리포트

팀에 공유할 필요가 있을 때만 다음을 생성한다.

- 민감정보가 제거된 요약
- 필요한 diff 또는 테스트 결과만 포함
- 사용자가 명시적으로 선택한 범위
- Raw Evidence의 로컬 경로나 비밀정보를 포함하지 않음

기본 정책은 **Raw는 로컬, 공유는 선택적 요약**이다.

---

## 12. Control Layer와의 데이터 계약

Dashboard는 원시 이벤트를 임의로 재해석하지 않고 다음 산출물을 입력으로 받는다.

```text
Task Review Packet
├─ Task Context
├─ Project Baseline Reference
├─ Task Overlay / Execution Contract
├─ Change Set
├─ Related Functions
├─ Verification Results
├─ Control Validation Results
├─ Task Guarantee Report
├─ Evidence References
├─ Direct Validation Results
├─ Gate State
└─ Final Decision
```

Dashboard가 요구하는 최소 조건:

- 모든 Evidence의 출처와 시점
- 대상 branch, worktree, commit
- 현재 코드 상태와 결과의 일치 여부
- Configured/Loaded/Enforced 등의 상태 구분
- 실패·충돌·미관찰을 숨기지 않음
- 민감정보 제거 여부
- Dashboard Projection 최신성

---

## 13. 첫 도그푸딩 시나리오

첫 기준 시나리오는 **기존 HWPX Agent Plugin에 새로운 문서 처리 기능을 추가하는 Managed Task**다.

Dashboard는 최소한 다음을 보여줘야 한다.

- 사용자가 요청한 HWPX 기능
- 실제 추가·수정된 동작
- HWPX 처리 흐름 Before / After
- 연관된 Tool/API/Viewer/파일 구조
- 변경 전 기준선 테스트
- 변경 후 같은 회귀 테스트
- 새 기능 테스트
- 직접 기능 실행과 결과 파일 확인
- Control Profile이 실제로 로드·집행된 범위
- 테스트하지 못한 HWPX 호환성 또는 외부 환경
- 사용자의 최종 판단

HWPX는 첫 검증 대상일 뿐이다. Dashboard 데이터 구조와 UI를 HWPX 전용으로 고정하지 않는다.

---

## 14. Dashboard 수용 기준

### 이해

- raw diff를 먼저 읽지 않고 주요 기능 변화를 설명할 수 있다.
- 요청·실제 변경·범위 밖 변경을 구분할 수 있다.
- Before / After 흐름이 실제 Evidence와 일치한다.

### 연관 기능

- 함께 확인할 기능과 그 이유를 알 수 있다.
- 연관성의 분석 범위와 한계를 확인할 수 있다.
- 사용자가 필요한 검증으로 바로 이동할 수 있다.

### 검증

- 새 기능, 회귀, Control Validation, 직접 검증이 분리된다.
- 실패·미실행·테스트 부재·Unknown이 성공으로 합쳐지지 않는다.
- 정량 결과에 전체 범위와 선택 기준이 함께 표시된다.

### Control 상태

- 설정 생성과 실제 로드·집행을 구분한다.
- Hooks, Sandbox, Approval Policy, Rules, 설정 충돌, Unobserved 상태를 확인할 수 있다.

### 판단

- 결과 수용과 위험 행동 승인, Git 통합이 분리된다.
- Soft Block Override의 이유와 잔여 위험이 남는다.
- Hard Block을 일반 수용 버튼으로 넘을 수 없다.

### 제품 효과

- 기존 방식보다 작업 이해와 판단 시간이 줄어드는지 측정할 수 있다.
- Dashboard 자체가 새로운 읽기 병목이 되지 않는다.

---

## 15. 구현 에이전트 지침

1. 화면 코딩 전에 `Control_layer.md`의 Evidence와 Guarantee 계약을 읽는다.
2. 하드코딩된 성공 화면이 아니라 실제 Evidence가 연결되는 수직 흐름을 우선한다.
3. Summary, Diagram, Related Functions, Verification이 서로 다른 사실 원천을 사용하지 않게 한다.
4. 정보가 없으면 임의로 생성하지 않는다. `Unknown`, `Unobserved`, `No Data`를 정상 상태로 설계한다.
5. HWPX를 첫 Fixture로 사용하되 Core UI와 Packet Schema를 HWPX 전용으로 만들지 않는다.
6. 모든 최종 Dashboard 기능을 GitHub 상위 Issue에 유지하고, Evidence 의존성 때문에 구현 순서를 나누더라도 범위를 삭제하지 않는다.
7. Usage & Cost Analytics가 핵심 Control·Assurance 구현을 지연시키지 않게 한다.
8. Dashboard 최신성은 Event Log head와 Projection sequence를 이용해 판정한다.
9. 사용자가 세부 UI 결정을 사전에 모두 선택하게 하지 말고, 실제 데이터가 들어간 POC를 제시해 평가받는다.

---

## 16. 한 문장 정의

> **DevHarness Dashboard Layer는 코딩 에이전트가 만든 변화를 기능 중심으로 압축하고, 연관된 기능·통제 상태·검증 Evidence·직접 확인 경로를 연결하여 사용자가 결과를 이해하고 자기 책임 아래 판단하게 만드는 인터페이스다.**

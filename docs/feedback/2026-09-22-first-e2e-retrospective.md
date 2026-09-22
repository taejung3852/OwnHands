# 첫 E2E 회고: 사용 경험을 기준으로 OwnHands 책임 재정렬

- 정리일: 2026-09-22
- 입력: 사용자가 작성한 E2E 피드백 1~15번과 이후 정정·우선순위 결정
- 관련 이슈: [#154](https://github.com/taejung3852/OwnHands/issues/154)
- 기준 main: `41d030cdfe5ecacb85e5649081aa3a74236323aa`
- 작업 브랜치: `docs/e2e-feedback-decisions`
- [결정 인덱스](../adr/README.md)

## 가장 중요한 정정과 우선순위

**OwnHands 전용 MCP는 Intent·Spec·ADR을 작성하는 Skill·가이드라인을 제공한다. GitHub MCP의 파일 저장 기능을 대체하려는 서버가 아니다.** GitHub 도구는 승인된 결과를 지정 저장소·브랜치에 저장한다.

기획·설계는 ChatGPT의 대화 경험을, 구현·검증은 Codex의 실행 환경을 활용한다. 사용자는 이를 대화에 적합한 직원과 실행에 적합한 직원의 역할 분담으로 설명했다. 이는 사용자의 작업 방식 선택이며 보편적인 모델 성능 비교가 아니다. 토큰·비용 절감은 기대 효과로만 남긴다.

**CI·Hook 미차단 원인 분석을 지금 먼저 하지 않는다.** 기존 자동 강제 장치를 걷어내는 방향을 기록하고, 새 구조가 먼저 갖춰진 뒤 통제 장치 재설계를 판단한다.

## 근거 수준

| 구분 | 이번 기록에서 사용하는 근거 | 주장하지 않는 것 |
|---|---|---|
| 사용자 경험 | 아래 15개 피드백과 후속 발언 | 모든 환경에서 동일한 문제 발생 |
| 실행 보고 | Build→독립 Verify→보완→재검증, 42 tests PASS, Ruff 통과, AC-01~17 PASS라는 사용자 제공 보고 | 이번 문서 작성 중 테스트 재실행 |
| 기존 저장소 계약 | 기준 버전의 build/verify/review/feedback 및 ADR | 선언된 지침의 실제 실행 보장 |
| 실제 외부 연동 | 보고 시점 API·웹 검색 smoke 미실행 | 서비스의 실제 외부 의존성까지 E2E PASS |
| 모델·추론 강도 | 요청값과 실제 관측값의 구분 | 요청값만으로 actual model/effort 확정 |
| Hook 미차단 | 사용자의 push/PR 요청과 차단 기대 불충족 경험 | 당시 도구 경로·trust·Evidence의 원인 확정 |
| 개선 효과 | Chat–Codex 역할 분리와 검증 통합의 기대 | 토큰·비용·품질 개선을 이미 측정했다는 주장 |

비공개 사용 프로젝트의 전체 로그·코드·개인정보·로컬 파일 경로는 공개 회고에 복제하지 않는다. 아래는 사용자에게 공개 기록을 요청받은 OwnHands 개선 논점만 정리한 것이다.

## 원래 피드백 번호 대응

| 번호 | 사용자 관측 또는 요구 | 유형·현재 해석 | 결정 문서 |
|---|---|---|---|
| 1 | Intent 인터뷰의 제품 결정이 OwnHands feedback 경로에 저장됨 | 기록 대상 혼동. 모든 기록을 ADR로 옮기지 말고 요구/결정/결함/Harness 신호 구분 | [0016](../adr/0016-artifact-classification-and-feedback.md) |
| 2 | 질문·시간이 얼마나 남았는지 알고 싶고 꼬리질문에 따라 갱신되길 원함 | Chat UX 요구. 동적 진행 수치와 시간 추정은 별개이며 추정 방식 미결정 | [0017](../adr/0017-guided-planning-and-visual-approval.md) |
| 3 | intent.md 생성보다 기획 완료·설계 시작처럼 단계를 안내받고 싶음 | 파일 생성과 사용자 승인 완료를 구분하는 단계 UX | [0017](../adr/0017-guided-planning-and-visual-approval.md) |
| 4 | 불릿 나열 대신 ELI5·다이어그램을 보고 단계 승인하고 싶음 | 시각 요약을 승인 문서와 연결. 미결정을 그림으로 숨기지 않음 | [0017](../adr/0017-guided-planning-and-visual-approval.md) |
| 5 | Plan Mode의 구현 계획과 Build Skill이 분할돼 느껴짐 | Build 준비와 실행의 소유권·인계 문제 | [0013](../adr/0013-build-planning-and-execution.md) |
| 6 | Plan Mode 완료만으로 plan.md가 저장되지 않음 | 사용자 저장 지시 반복을 줄이되 쓰기 금지 모드 우회 금지 | [0013](../adr/0013-build-planning-and-execution.md) |
| 7 | Build에서 테스트·독립 검증·수정·재검증 수행. 외부 Skill도 관여 | 동작한 절차를 보존. 로컬 검사와 live 연동, OwnHands 단독 효과는 구분 | [0013](../adr/0013-build-planning-and-execution.md), [0014](../adr/0014-single-independent-verification.md) |
| 8 | Verifier/Reviewer와 두 Skill이 너무 유사하고 과분할됨 | Verify Skill·단일 독립 Verifier로 통합하는 사용자 방향 | [0014](../adr/0014-single-independent-verification.md) |
| 9-1 | explain/write-issue-pr를 OwnHands Core와 분리하고 싶음 | 범용 보조 기능과 Core 소유권 분리 | [0018](../adr/0018-core-and-companion-skills.md) |
| 9-2 | Chat에서 ADR·Intent·Spec을 논의·저장하고 Codex로 인계. 작성 Skill은 전용 MCP로 제공 | 이번 구조 재정렬의 중심. Git 저장 도구와 Skill 제공은 다른 기능 | [0011](../adr/0011-chat-codex-ownership-and-handoff.md), [0012](../adr/0012-authoring-skills-via-ownhands-mcp.md) |
| 10 | 9번을 우선하고 토큰 절감 기대 | 2·3의 UX를 버리는 대신 Chat으로 이동. 절감은 미측정 가설 | [0011](../adr/0011-chat-codex-ownership-and-handoff.md), [0017](../adr/0017-guided-planning-and-visual-approval.md) |
| 11 | Hook이 정확히 무엇을 하는지 모르겠음 | 이후 사용자 결정으로 기존 강제 장치 제거·재설계 후순위 | [0015](../adr/0015-defer-automatic-ci-and-hook-enforcement.md) |
| 12 | review 생략 후 push/PR 요청이 기대한 차단을 받지 않음 | 미차단 경험 보존. 원인 미확정이고 조사도 보류 | [0015](../adr/0015-defer-automatic-ci-and-hook-enforcement.md) |
| 13 | Build에서 공개 Ponytail을 사용하도록 연결하고 싶음 | 자체 복제품 대신 외부 원본 재사용, 요구·안전·검증 경계 유지 | [0018](../adr/0018-core-and-companion-skills.md) |
| 14 | npx 설치에서 ELI5와 Ponytail도 설치되길 원함 | Core와 설치 묶음은 다름. 원본·버전·갱신·충돌 처리 미결정 | [0018](../adr/0018-core-and-companion-skills.md) |
| 15 | 러프한 의도를 GORE로 깊게 논의하고 기술 Spec을 더 정밀하게 만들고 싶음 | 중요 모호성 해소, 에이전트가 조사할 사실과 사용자 결정을 분리 | [0011](../adr/0011-chat-codex-ownership-and-handoff.md), [0017](../adr/0017-guided-planning-and-visual-approval.md) |

## 동작한 부분도 보존한다

사용자 실행 보고는 구현 중 테스트를 추가하고 독립 검증에서 드러난 누락을 보완한 뒤 다시 검증한 흐름을 설명한다. 이 과정은 단순히 완료를 선언한 것과 다르다. 다만 test-driven-development, receiving-code-review, Ponytail 등 외부 Skill의 관여가 있으므로 어느 기여가 OwnHands 고유 효과인지 분리 측정한 것은 아니다.

Build 완료 보고의 최종 diff review 미실행과 이후 push/PR 경험은 시간상 다른 사건이다. 이를 합쳐 처음부터 모든 외부 작업이 수행됐거나, review 생략이 단독으로 Hook 미차단 원인이었다고 쓰지 않는다.

## 확정 방향과 열린 질문

### 확정 방향

Chat Plan·Design / Codex Build·Verify로 역할을 나눈다. OwnHands MCP로 작성 Skill을 제공하고 GitHub 도구로 문서를 저장한다. Build 준비·실행을 연결하고 검증을 단일 독립 Verifier 중심으로 통합한다. 기존 자동 CI·Hook/Gate를 걷어내는 방향을 기록한다. 범용 ELI5·Ponytail 재사용과 제품 기록/OwnHands Feedback 구분을 추진한다.

### 아직 정할 것

- 실제 Skill 전달·등록 방식, MCP 접속·인증·버전과 Plugin의 배포 경로.
- 문서 승인 상태, 저장소·브랜치·revision 인계, 동시 수정 처리.
- 단일 Verifier의 상세 결과·재실행 범위·모델 정책과 경량 작업 경로.
- 질문/미결정 수 표시, 시간 추정, 시각 요약과 문서 버전 연결.
- 보조 Skill 원본·라이선스·revision, 번들/다운로드·업데이트·충돌 처리.

### 지금 하지 않을 것

Hook 미차단 원인 조사, 새 CI·Hook 설계, 대형 비교 평가, 새 Dashboard, 임의 릴리스·버전 상승은 하지 않는다. 이 문서 커밋은 기존 실행 자산 삭제나 통합 구현까지 승인·완료한 것이 아니다.

## 앞선 대화에서 보존할 후속 후보

| 후보 | 관측·이유 | 이번 기록의 상태 |
|---|---|---|
| Reviewer Astra/high 비용 | 사용자에게 비용 부담, medium 사용 경험 있음 | 기본 모델 자동 변경 없음. 단일 검증 정책 때 함께 판단 |
| 작은 작업 경량 경로 | 문서 면제 뒤에도 Plan/Evidence를 요구하는 연결 문제 | 별도 Lite 제품보다 같은 흐름 내 경량 경로 후보 |
| Plan의 실행 구체성 | 파일명만으로는 새 실행자가 중요한 판단을 추측할 수 있음 | 입력·기대 결과·검증 방법 강화 방향 |
| Skill 실효성 | 존재·호출과 사용하지 않을 때보다 나은 효과는 다름 | 첫 새 흐름 관측 후 필요할 때 제한 비교 |
| 지속적 성장과 버전 | 완성 선언보다 사용할 수 있는 고정점 선호 | 기존 릴리스 이력 보존, 새 version/tag 없음 |

## 후속 진행 제안

1. ADR-0011·0012를 기준으로 작성 Skill 제공과 Git 인계의 미결정 상세를 구체화한다.
2. Build·Verify·기록 분류·보조 Skill 및 기존 강제 장치 제거의 구현 범위를 정한다.
3. 별도 승인된 작은 구현을 실행하고 실제 문서 인계부터 사용까지 관측한다.

이미 확정한 방향을 다시 묻는 대신 결과를 바꾸는 미결정 사항만 논의한다. 이 이슈나 문서가 생성됐다는 이유만으로 새 Runtime·배포·삭제 작업을 자동 시작하지 않는다.

OwnHands-E2E-Review: 2026-09-22-first-dogfooding

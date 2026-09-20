# Spec: 사용 프로젝트의 피드백을 통한 OwnHands 자기개선

- **기반 Intent**: [intent.md](intent.md)
- **작성 주체**: Codex — 승인된 Intent와 후속 사용자 결정 반영
- **일자**: 2026-09-20
- **상태**: Approved — 사용자 확인 (2026-09-20)
- **관련 Research Issue**: [#150](https://github.com/taejung3852/OwnHands/issues/150)

## 1. 기술적 요구사항 (Requirements)

| ID | 요구사항 | Intent 추적 |
|---|---|---|
| REQ-01 | `feedback` Skill은 사용자 교정, Eval 실패, Reviewer Finding을 입력받는다. 실제 관측과 OwnHands 원인 추정을 구분한다. | G-01 |
| REQ-02 | 사용 프로젝트의 `docs/ownhands/feedback/`에 Markdown으로 기록한다. 동일 신호는 기존 기록에 관측을 추가한다. | C-01~03 |
| REQ-03 | 작업·PR 종료 시 미처리 기록을 선별한다. OwnHands 변경 필요성이 남으면 Issue 후보, 추가 조치 없이 해결됐으면 기록만 보존한다. 원인이 불확실하면 조사 후보로 명시한다. | G-02, C-03 |
| REQ-04 | OwnHands Issue에는 OwnHands의 기대/실제 행동, 비공개 정보를 제거한 최소 재현 정보와 공유 가능한 근거만 전달한다. 내부 코드·로그·대화·프로젝트 식별자를 그대로 전송하지 않는다. | C-02, 후속 사용자 승인 |
| REQ-05 | 내부 정보를 제거하면 설명할 수 없거나 공개 가능 여부가 불명확하면 등록을 보류하고 사용자에게 확인한다. 접근 불가능한 비공개 링크를 유일한 재현 근거로 쓰지 않는다. | 후속 사용자 승인 |
| REQ-06 | 새 Issue 등록 전에 OwnHands의 기존 관련 Issue와 신호 ID를 확인한다. 기존 문제가 있으면 연결하고, 새 근거가 있을 때만 요약을 추가한다. | G-02, C-03 |
| REQ-07 | Issue 등록은 구현 착수 권한이 아니다. 사용자가 해당 개선 작업을 요청한 뒤 원인 확인·수정·검증을 수행한다. | G-03, C-04 |
| REQ-08 | 기존 `build → verify/verifier → review`를 재사용한다. 계약 변경은 수정 전에 사용자 판단을 받는다. | C-05, C-07 |
| REQ-09 | 관련 실제 사례의 Before/After와 영향받는 회귀 범위를 비교한다. 제품 자체 버그의 native test와 OwnHands 행동의 Eval을 구분한다. | G-04, C-06 |
| REQ-10 | 채택은 사용자가 결정한다. 채택된 commit/tag, 사용 프로젝트에 적용한 버전, 적용 후 관측을 연결한다. Merge만으로 다른 프로젝트에 적용됐다고 주장하지 않는다. | G-05, C-04 |
| REQ-11 | 피드백 파일도 일반 Git 변경이다. Review 후 기록을 변경하면 기존 fingerprint가 stale이 되며, 다음 외부 Git 동작 전에 변경 범위를 재검토한다. | C-05~06 |
| REQ-12 | 새 Hook·Runner·DB·자동 업데이트 서비스를 만들지 않는다. Skill의 호출과 효과는 실제 관측으로 확인하며 지침 존재를 실행 보장으로 주장하지 않는다. | C-07~08 |

## 2. 시스템 아키텍처 및 인터페이스

### 2.1 책임과 진입점

`feedback`의 Trigger는 신호 관측 또는 작업 종료, Input은 관측 근거와 해당 프로젝트 기록, Success는 근거 보존 및 Issue 연결/보류 이유의 기록이다. 구현·검증·Review와 세 축이 달라 별도 Skill로 둔다. 개선 구현 자체는 이 Skill의 책임이 아니다.

- **capture**: 현재 세션에서 관측한 신호를 기록한다. 세션 밖 전체 로그를 자동 탐색하지 않는다.
- **triage**: 명시적 작업 완료/종료 또는 PR 생성·갱신·Merge 완료 보고 시, 아직 처리되지 않은 신호를 선별해 연결한다. 매 응답 종료를 작업 종료로 취급하지 않는다. `$feedback`으로도 명시 호출할 수 있다.
- **follow-up**: 사용자가 개선 작업을 요청하면 기존 구현 흐름에 신호와 Issue를 입력으로 전달한다. 채택 및 이후 적용 결과는 같은 기록에 연결한다.

세 단계는 Skill의 작업 모드이며 새로운 CLI subcommand나 상주 프로세스가 아니다. 종료 시점이 불명확하거나 세션이 중단되면 다음 명시 호출/종료 시 기록을 처리한다.

사용 프로젝트는 `feedback` Skill과 필요한 Reference를 사용할 수 있어야 한다. 로컬 설치 방식에 맞게 연결하고 다음 최소 문장을 프로젝트 지침에 병합한다. 기존 지침을 통째로 덮어쓰지 않는다.

> OwnHands 사용 중 사용자 교정·Eval 실패·Reviewer Finding을 관측하거나 작업·PR을 종료할 때 `feedback` Skill로 신호 기록과 선별을 수행한다.

수집 파일은 해당 작업의 Target Files에 포함한다. read-only 세션이나 쓰기 범위가 허용되지 않은 작업에서는 초안만 제시하고 저장 미완료를 알린다.

### 2.2 후보 대상 파일과 책임

| 구분 | 경로 | 책임 |
|---|---|---|
| NEW | `.agents/skills/feedback/SKILL.md` | capture·triage·follow-up의 얇은 절차 |
| NEW | `.agents/skills/feedback/references/feedback-contract.md` | Markdown 형식, 선별·공개·중복·실패 처리, 사용 프로젝트 연결 안내 |
| MODIFY | `AGENTS.md` | 위 최소 라우팅 한 문장 |
| MODIFY | `docs/decisions.md` | Skill 개수·분할 근거와 승인된 M7 계약 |
| MODIFY | `docs/roadmap.md` | M7 진행 상태와 설계 링크 |
| NEW | `docs/specs/self-improvement-loop/plan.md` | 승인 후 Target Files·Task·검증·Evidence |
| 사용 시 생성 | `<사용 프로젝트>/docs/ownhands/feedback/<signal-id>.md` | 신호별 원본 기록과 후속 연결 |

`build`, `verify`, `review`, M5 runner·baseline, 기존 Hook·Agent는 그대로 재사용한다. 새 회귀 사례는 실제 개선 작업에서 필요성을 판단한 뒤 해당 범위로 추가한다. 이번에는 전체 Runtime Eval을 실행하지 않는다.

### 2.3 신호 Markdown

신호 하나당 파일 하나를 사용한다. `signal-id`는 UUID로 한 번 만들고 재시도에도 유지한다. ID 자체에 프로젝트 이름을 포함하지 않는다. 별도 인덱스·DB·스키마 파서를 만들지 않는다.

```markdown
# Feedback: <짧은 문제 제목>

- ID: <uuid>
- 관측일: <ISO 날짜/시간>
- 유형: user-correction | eval-failure | reviewer-finding
- 대상: <관련 OwnHands 자산 또는 unknown>
- OwnHands 버전: <commit/tag 또는 unknown과 사유>
- 작업 근거: <사용 프로젝트의 작업·commit·관련 기록 위치>
- 전달 상태: pending | recorded-only | deferred | linked
- OwnHands Issue: <URL 또는 미등록>

## 관측
- 기대 행동:
- 실제 행동:
- 원본 근거: <최소 발췌 또는 로컬 근거 위치; 비밀값은 저장하지 않음>
- 영향:

## 판단 및 전달
- 원인: <확인된 사실과 가설을 구분>
- 선별 이유:
- 외부 전달용 요약: <내부 식별자·코드·로그를 제외한 최소 재현>
- 처리 기록: <시각, 확인한 Issue/실패/보류 이유>

## 개선 후속
- 사용자 작업 요청: <요청 근거>
- 개선 PR/commit:
- Before/After 및 회귀 Evidence:
- 사용자 채택 결정:
- 사용 프로젝트 적용 버전과 관측:
```

아직 발생하지 않은 후속 항목은 미진행으로 남긴다. 없는 버전·원본·실측을 생성하지 않는다. 이 상태는 전달 상태이며 Eval 판정 `PASS / FAIL / UNOBSERVED`를 대체하지 않는다.

### 2.4 Issue 등록과 중복 처리

- 목적지는 `taejung3852/OwnHands`로 명시한다. 사용 프로젝트의 기본 remote에 잘못 등록하지 않는다.
- 기존 `write-issue-pr`의 3칸 Human Brief와 접힌 상세 형식을 사용한다. 상세에 `OwnHands-Feedback-ID: <uuid>`를 남긴다.
- ID와 관련 자산·기대/실제 행동으로 열린/닫힌 Issue를 확인한다. 같은 근본 문제면 연결하고, 해결 후 다른 버전에서 재발했다면 그 차이를 기록한다. 관련성이 불명확하면 임의 병합하지 않는다.
- 생성 응답을 받지 못해 성공 여부가 불명확하면 ID로 원격 상태를 확인한다. 확인 전에는 같은 Issue를 다시 생성하지 않는다.
- 원격 등록 확인 후 로컬 기록에 URL을 남긴다. 기록 실패 시 URL을 사용자에게 보고하고 다음 실행에서 ID로 복구한다. 동시 실행의 원자적 중복 방지는 보장하지 않으며 발견 시 기존 Issue로 연결한다.
- Issue 등록·근거 추가는 승인된 피드백 흐름의 범위다. 내부 정보 공개나 OwnHands 코드 수정·Push·Merge까지 허용하는 것으로 확대하지 않는다.

### 2.5 Review 및 버전 관리와의 연결

Final Review 전에 가능한 신호 기록과 선별을 마친다. 이후 새 Finding이나 원격 Issue URL로 파일이 달라지면 일반 diff 변경으로 취급한다. fingerprint 계산에서 피드백 파일을 제외하지 않는다.

PR/작업 종료 뒤 생긴 기록은 로컬 변경으로 남길 수 있다. 그 사실을 완료 보고에 알리고 다음 승인된 commit/Review 흐름으로 버전 관리한다. 기록을 남기기 위해 이미 검토된 PR에 자동 Push하거나 Merge된 PR을 다시 열지 않는다. Git에 저장 가능한 파일이라는 사실과 실제 commit 완료는 구분한다.

채택 후 사용 프로젝트의 기존 설치 방식으로 해당 OwnHands 버전을 적용하고 확인한다. 단순 복사 설치라면 적용한 자산·출처 버전을 기록한다. 업데이트 방식이 없거나 권한이 없으면 적용 대기로 남기며 별도 배포 시스템을 만들지 않는다.

## 3. 엣지 케이스 및 예외 처리

| 상황 | 처리 |
|---|---|
| 신호 없음 | 파일·Issue를 만들지 않음 |
| 제품 버그만 확인됨 | 해당 프로젝트 작업으로 처리; OwnHands 결함으로 확정하지 않음 |
| 교정이 새 요구사항이며 기존 행동은 계약 준수 | 결함이 아닌 개선 제안으로 분류 |
| 미해결이나 원인 불명 | 조사 후보와 가설로 표시; 실패 원인을 단정하지 않음 |
| 이미 해결·추가 조치 없음 | `recorded-only` 및 이유 기록 |
| 공개 가능한 최소 재현을 만들 수 없음 | `deferred`; 사용자 판단 전 외부 전송 중단 |
| GitHub 인증·네트워크·조회 실패 | `deferred`; 원본 보존, 다음 triage에서 재확인, 현재 제품 작업을 무한 재시도로 지연시키지 않음 |
| 등록 성공 여부 불명 | ID 조회 전 재생성 금지 |
| 종료 절차 반복 실행 | 기존 ID/Issue 확인; 동일 근거 댓글 반복 금지 |
| 최종 Review 후 기록 변경 | 기존 Evidence stale; 다음 외부 Git 동작 전 변경 범위 재검토 |
| 개선 검증 FAIL/UNOBSERVED | 원래 결과를 보존; baseline 변경으로 은폐 금지, 기존 승인 규칙 적용 |
| 채택했으나 사용 프로젝트에 미적용 | 적용 대기; 자기개선 순환 전체 완료로 주장하지 않음 |

## 4. 수용성 기준 및 검증 계획

| AC | 기준 | 검증 |
|---|---|---|
| AC-01 | 세 신호 유형의 관측·기대 행동·원본·버전이 기록되며 추정과 사실이 분리됨 | 합성 사례 정적 검토 + 대표 단일 read-only Runtime 초안 |
| AC-02 | 사용 프로젝트 경로·라우팅·권한 조건이 명확하며 원본과 Issue 역할이 분리됨 | Skill/Reference 및 Markdown 확인 |
| AC-03 | 비공개 자료가 외부 요약에서 제외되고 분리 불가 시 보류됨 | 가짜 비밀값이 포함된 합성 사례로 출력 확인 |
| AC-04 | 종료 시 중복 조회 후 등록·연결하며 결과 불명 시 즉시 재생성하지 않음 | 재실행·응답 유실 시나리오 점검; 실제 GitHub 동작은 명시된 실측 범위에서 관측 |
| AC-05 | Issue 생성만으로 구현하지 않고 사용자 요청 후 기존 Build/Verify/Review로 연결됨 | 행동 시나리오 및 실제 작업 기록 |
| AC-06 | 변경 전후 효과·관련 회귀·채택 여부·적용 버전이 추적됨 | 실제 개선 사례 한 건의 연결 감사 |
| AC-07 | 피드백 변경이 Review fingerprint를 우회하지 않음 | 기존 계약과 실행 순서 대조; Hook 구현은 변경하지 않음 |
| AC-08 | 새로운 서비스·Hook·Runner 없이 Skill/Reference와 최소 라우팅으로 구성됨 | 변경 파일·의존성 검사 |

구현 단계에서 `git diff --check`, `node scripts/run-evals.js --static-only`를 실행한다. Runtime은 실제 외부 Issue 생성 없이 초안만 만드는 단일 세션으로 시작한다. 이 결과로 실제 파일 저장·GitHub 등록·버전 적용이 검증됐다고 주장하지 않는다.

전체 순환은 사용자가 지정한 실제 사용 프로젝트에서 실제 신호와 개선 작업으로 검증한다. 그 프로젝트와 사례는 아직 지정되지 않았으므로 현재 실제 운영 관측은 `UNOBSERVED`다. 합성 테스트용 GitHub Issue는 생성하지 않는다. 필요한 실측 대상과 실행 범위는 Build Plan에서 명시한다.

이 문서는 사용자 승인된 설계다. 실행 상태와 Evidence는 [plan.md](plan.md)를 따른다. 설계 승인은 실제 신호 수집이나 Issue 전송이 검증됐다는 의미가 아니다.

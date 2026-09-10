# #80 Lifecycle 계약 — 확정한 제품 판단과 설계 기록

작성일: 2026-09-11

상태: 제품 판단은 이 대화에서 사용자 확정. 이 기록을 바탕으로 Lifecycle v1을 구현했으며 현재 규범 계약과 검증 결과는 `docs/m5-r/lifecycle-contract.md`, `docs/m5-r/lifecycle-verification.md`에 있다.
제품 방향 보완 반영: OwnHands는 작업을 검증 가능하게 정의하고 수행하도록 돕고, 그 근거를 사람이 이해해 최종 판단하게 하는 얇은 개발 하네스다. Dashboard는 이 흐름의 사람 검토 화면이며, 개발 과정의 Skill과 같은 계약을 소비한다.
구현 기준 main: `779b5568c38a154b4dc7b55818e806a5e53639f0`.
이 파일은 구현 전 판단과 대조 근거를 보존하는 설계 기록이다.

## 1. 확정한 제품 판단

1. 검수 조건은 사람의 비즈니스 판단이다. 최초 조건과 의미 있는 변경은 사람이 결정한다. 에이전트가 변경 필요성을 발견하면 이유·변경안을 보고하고 승인을 기다린다. 사용자가 구체적으로 지시한 수정에 중복 승인을 요구하지 않는다.
2. 에이전트는 검사 방법과 관련 영역을 찾아 테스트를 설계·실행할 수 있다. 선정 이유·실행 근거·결과를 남긴다. 추가 검사를 임의로 필수 검수 조건으로 만들지 않는다.
3. 사실과 빈틈을 먼저 제시하고 AI 추정은 별도로 보존한다. 추정이나 기록 성공을 검증 통과로 바꾸지 않는다.
4. 필수 조건을 실행하지 못하면 미검증이다. 추가 검사 통과로 대체하지 않는다. 조건 제외는 사람의 결정과 변경 이력을 필요로 한다.
5. 실제로 발견한 실패는 보고하며 자동으로 완료 처리하지 않는다. 이번 작업에서 고칠지 별도 Issue로 다룰지는 사람이 결정한다.
6. 변경의 직접·간접 영향을 조사하고 관련 검사를 수행한다. 검사 범위·결과·남은 불확실성을 보고한다. 모든 잠재 영향을 완전히 찾았다는 증명을 요구하거나 막연한 가능성만으로 완료를 차단하지 않는다.
7. 수정·테스트 반복은 같은 attempt다. 완료 후 재작업 요청은 새 attempt다. 세션 변경 자체는 새 attempt의 기준이 아니다. 기존 작업·기준·코드 상태를 확인해 명시적으로 이어가며, 연결을 확인할 수 없으면 새 attempt로 구분한다.
8. 요구 변경에 따른 새 Issue 생성은 기존 작업 흐름에 맡긴다. OwnHands가 요구 변경·Issue 관리 정책을 확대하지 않는다.
9. 완료 판단은 당시 코드·조건·결과에 고정한다. 이후 코드에 자동 승계하지 않는다. 과거 판단은 삭제하거나 덮어쓰지 않는다.
10. 목표 탐색·이슈 구체화·Spec 작성·Baseline·Review에서 필요한 방법론은 #81이 작업에 맞게 선택적으로 연결한다. SDD·TDD는 필수 lifecycle 단계나 완료 조건이 아니다. #80은 필요한 산출물·근거·승인·참조의 연결을 정의한다.

### 이번 보완으로 달라지는 범위

- 기존 준비안의 검증·판단 기록 중심 설명을 작업 정의·수행 지원까지 확장한다. 앞의 합의 1~9는 유지한다.
- #81의 입력을 승인된 Spec 이후뿐 아니라 목표 탐색·이슈 구체화·Spec 초안까지 명시한다. 별도의 거대한 계획 시스템이나 Issue 생성 정책은 추가하지 않는다.
- 각 단계의 읽기·기록·다음 행동 준비 상태를 Skill과 Dashboard의 공통 계약으로 정의한다. 화면이나 스킬에서 별도 판정 규칙을 만들지 않는다.
- 방법론 이름이나 특정 Skill 실행 여부로 준비·완료를 판정하지 않고, 필요한 산출물과 근거로 판정한다.

## 2. 원격 코드에서 확인한 기반

모든 경로는 위 commit 기준이다. 정적 코드 열람이며 실제 실행 검증은 하지 않았다.

| 경로·기호 | 확인한 내용 | #80에서 필요한 구분 |
|---|---|---|
| src/devharness/identity.py: TaskIdentity | Project/Worktree/Task와 commit·environment_ref | Issue·attempt를 기존 Task의 별칭으로 만들지 않고 별도 연결 |
| src/devharness/evidence.py: EvidenceDraft, EvidenceRecord | task_id, scope, result, basis, inference_from, conflict_refs, content_hash | 새 lifecycle scope와 근거 연결 검증. 기존 result/basis 의미 유지 |
| src/devharness/assurance.py: capture_restore_point | HEAD와 tracked patch hash, untracked/submodule/link 제외 명시 | 새 code-state의 관찰 범위·누락 명시. 기존 복원 기록을 전체 작업 트리 동일성으로 오인하지 않음 |
| src/devharness/assurance.py: compare_test_runs | missing_before, incomparable, regression, fixed_failure, comparable_pass 구별 | 원칙은 재사용하되 legacy Contract binding을 새 Spec에 직접 치환하지 않음 |
| src/devharness/projections.py: ProjectionEngine.freshness | Event sequence와 Projection 무결성·반영 상태 확인 | 의미상 Freshness와 별도 관리 |
| docs/m5-r/core-responsibility-map.md | 별도 version/namespace, legacy 의미 보존 | 새 계약은 독립 명명. adapter는 출처·변환 버전·손실 명시 |

원격 파일 목록에서 이슈별 검수 조건 MD의 표준 디렉터리를 확인하지 못했다. 따라서 고정 경로가 이미 존재한다고 가정하지 않는다. MD를 사람이 읽고 수정하는 원본으로 사용하는 방향을 수용하고, 계약은 경로와 정확한 내용 버전을 참조하도록 설계한다.

## 3. 객체와 연결 — 설계

새 namespace는 `ownhands.lifecycle`, schema_version은 `1`이다. 기존 저장 형식의 version과 혼용하지 않는다.

공통 참조는 kind/id/revision/hash를 사용한다. revision은 같은 논리 객체의 과거 기록을 덮어쓰는 값이 아니라 새 불변 기록을 구분하는 값이다. schema_version과 문서 revision은 별개다.

| 객체 | 담아야 할 내용 |
|---|---|
| WorkIssue | 내부 ID, 프로젝트, 외부 Issue locator, 참조한 Issue 내용 버전, 목표·범위·미결정 사항 및 그 출처 참조 |
| Attempt | Issue·Task 연결, 이전 attempt 참조, 시작·종료·재개 기록 |
| VerificationSpec | Issue 연결, MD 경로·내용 hash·불변 내용 참조, 사람이 정한 criterion ID와 필수 여부, 승인 참조 |
| SpecApproval | 정확한 Spec revision, 사람 식별자, 결정·근거·시각. 에이전트의 수정 기록과 구분 |
| CodeState | commit, working-tree fingerprint, 캡처 방식·범위·제외 항목. hash가 있어도 누락 범위를 숨기지 않음 |
| Baseline | Micro/Verification 종류, 승인된 정확한 Spec·SpecApproval·Before CodeState·환경·Observation 참조와 누락 이유 |
| Review | attempt, 승인된 정확한 Spec·SpecApproval, After CodeState, Verification Baseline, Claim 결과, 추가 검사 결과, gap·inference·blocker 참조 |
| ReviewSnapshot | 정확한 Review 및 의존 객체 참조를 고정한 판단 자료 |
| HumanDecision | Snapshot, 사람, 결정·이유·시각, 후속 판단 연결. append-only |

Spec은 Issue 범위이며 여러 attempt가 같은 승인 버전을 사용할 수 있다. 실행 근거·Snapshot·Decision은 명시된 Issue/Task/attempt 경계를 검증한다. 타 attempt의 근거를 자동 재사용하지 않는다. 외부 근거 수입은 출처를 보존하는 명시적 binding이 필요하며 임의 연결을 허용하지 않는다.

### 단계별 읽기·기록·준비 확인 — 설계

아래는 사용할 수 있는 단계의 입출력 계약이며 반드시 순서대로 실행해야 하는 절차가 아니다. 이미 충분한 기록이 있으면 다시 작성하지 않고 정확한 버전을 참조한다. 초기 목표·논의는 기존 MD나 대화 등 출처를 가진 기록으로 연결하며 전용 객체를 단계마다 의무적으로 만들지 않는다. Issue 생성 전에는 프로젝트 범위의 출처로 보존하고, Issue가 정해지면 명시적으로 연결한다. 이를 attempt의 실행 증거로 자동 승격하지 않는다.

| 단계 | 읽는 기록 | 남기는 기록 | 어떤 행동의 준비를 확인하는가 |
|---|---|---|---|
| 목표 탐색 | 사용자 요청, 프로젝트 맥락, 기존 결정·목표 기록 | 목표 후보, 제약, 미결정 질문, 사용자 답변의 출처 | 이슈 초안을 작성할 만큼 목적·대상·제약이 구체적인가. 불명확하면 필요한 질문을 표시 |
| 이슈 구체화 | 목표·제약, 관련 Issue·결정 | WorkIssue의 범위·제외 범위·예상 산출물·미결정 사항과 출처 | Spec 초안을 작성할 대상과 범위가 있는가. 이슈 등록 행위를 강제하지 않음 |
| Spec 작성 | WorkIssue, 사람의 검수 조건, 관련 자료 | VerificationSpec 초안·revision·출처, 사람의 SpecApproval | 초안 검토가 가능한지와 승인 기준으로 사용할 수 있는지를 따로 확인. 미승인 초안은 검수 기준으로 활성화하지 않음 |
| Baseline | attempt 연결, 승인 Spec, CodeState, 환경·검사 계획 | Micro/Verification Baseline, 실제 수집 근거, 누락·비교 제한 | 수집 입력이 갖춰졌는지와 특정 Before/After 비교가 가능한지를 구별. Before 부재를 전체 개발 금지로 해석하지 않음 |
| 수행·검사 기록 | 승인 Spec, attempt, 관련 Baseline·CodeState, 검사 계획 | 변경 상태, 테스트 선정 이유, 실행 receipt·Evidence, 미실행 이유·추정·충돌 | 특정 검사의 입력·권한·환경이 갖춰졌는지 확인. 검사를 계획한 것과 실제 수행한 것을 구별 |
| Review | 승인 Spec, 대상 코드·환경, Baseline, 실행 결과, 관련성·gap·추정·충돌 | Review, ReviewSnapshot, 입력별 Freshness·필수 조건 충족 여부·실패 보고 | Review를 작성할 수 있는지와 검증을 완료로 판단할 수 있는지를 구별. 미검증·실패도 Review에 포함해 사람이 볼 수 있어야 함 |
| 사람 판단 / Dashboard | 같은 ReviewSnapshot·단계 준비 상태·출처·최신성 | 특정 Snapshot에 연결된 HumanDecision | 판단 자료의 연결·무결성을 확인하고 미검증·실패·불확실성을 제시. 조회·보고 가능을 검증 완료나 수용으로 취급하지 않음 |

준비 상태 조회의 공통 반환:

- `stage`, `action`: 예컨대 Spec 초안 검토, 승인 기준 사용, Before 비교, Review 작성처럼 확인할 행동을 명시한다.
- `subject_ref`, `input_refs`: 소유 범위와 사용한 기록의 정확한 버전. 원본 참조를 따라갈 수 있어야 한다.
- `readiness`: `ready / needs-input / invalid` 후보. 필요한 입력이 있는지, 부족한지, 참조·무결성이 잘못됐는지를 구별한다. Review 결과나 실행 권한 승인을 대체하지 않는다.
- `checks`: 필요한 산출물·승인·연결·최신성별 확인 결과, 이유 코드, 사람이 읽을 설명, 근거 참조, 부족한 입력과 다음 조치. 차단 사유와 참고 경고를 구별한다.
- `evaluated_against`: 평가한 입력 revision 및 규칙 버전. 입력이 바뀌면 다시 계산한다. 준비 상태는 별도 수동 원본이 아니라 기록에서 재생성 가능한 파생 결과다.

필수 조건의 누락은 검증 완료를 막지만 누락 보고서 작성까지 막지 않는다. 일반적인 영향 불확실성이나 선택하지 않은 방법론은 준비 상태를 자동으로 invalid 처리하지 않는다. 준비 상태 조회가 command 실행·파일 수정·외부 시스템 권한을 부여하지도 않는다.

방법론을 남길 경우 이름·버전·선택 이유와 만들어진 산출물 참조를 선택적 metadata로 둔다. TDD를 사용했다는 선언만으로 Before 근거가 있는 것으로 인정하지 않는다. SDD 문서가 없더라도 해당 작업의 승인된 조건과 필요한 근거가 있으면 방법론 이름 때문에 탈락시키지 않는다. 실제 방법론 선택·Skill routing은 #81이다.

### using-ownhands Router 연결 — 추가 차이

단계별 입출력·행동별 준비 상태·방법론 선택·기존 기록 재사용·Dashboard 공통 소비는 위 설계를 유지한다. 이번 Router 구상으로 추가 명시할 부분은 아래 세 가지다. 새 Router 전용 원본 저장소나 고정 Skill 실행 순서는 만들지 않는다.

1. **조회 맥락:** 공통 조회에 사용자 요청·명시적 제약의 출처 참조, 대상 작업과 현재 수행하려는 단계/행동, 변경 성격과 판단 근거를 전달할 수 있게 한다. 사용자 의도와 에이전트의 추정은 구분하며, 단계는 파일 존재만으로 유일한 다음 행동으로 강제하지 않는다. 변경 성격을 아직 모르면 미확인으로 표현한다. 명시적 의도 우선, 불확실성에 따른 Wayfinder·grill-me·SDD·TDD 선택 정책은 #81에서 구체화한다. #80의 schema에 이 이름들을 필수 enum으로 고정하지 않는다.
2. **준비된 산출물과 부족한 입력:** 조회는 사용 가능한 산출물의 정확한 참조·승인 상태·Freshness·적용 범위와, 아직 충족되지 않은 입력 및 그 이유를 반환한다. 문서가 존재한다는 것만으로 재사용 가능하다고 판정하지 않는다. 기존 기록으로 입력이 충족되면 추가 Skill 호출 없이 진행하는 경로도 정상적으로 표현한다. Skill 호출 이력 부재는 입력 누락이 아니다. 앞서 정한 Issue/Task/attempt 참조 경계는 그대로 적용한다.
3. **수행 결과 연결:** Skill 사용 여부와 관계없이 수행 기록에 대상 단계/행동, 읽은 입력 revision, 재사용한 산출물 참조, 새로 남긴 산출물·실행 근거 참조, 수행 상태와 남은 gap을 연결한다. Skill 이름·버전은 사용했을 때만 provenance로 남긴다. 수행 성공과 검수 통과는 구별한다. 산출물의 type·scope·version으로 소비하므로 Skill과 Dashboard가 동일하게 읽을 수 있어야 한다. 입력이 수행 도중 변경되면 결과는 실제 사용한 입력에 묶어 보존하고 현재 적용 여부는 재평가한다.

위 항목은 기존 공통 조회와 수행 기록의 필드 보완이다. Router 선택 알고리즘·프롬프트·Skill 설치/발견·호출 구현은 #81 범위다.

## 4. 활성 버전과 상태 — 설계

- 현재 Spec은 최신 파일 수정 시각으로 선택하지 않는다. 사람의 승인과 연결된 activation 기록으로 선택한다. 초안 저장만으로 활성 기준이 바뀌지 않는다.
- 활성 선택 범위는 객체 종류와 소유 Issue/attempt로 명시한다. 검증된 순서 번호에 따라 replay하며 중복·충돌·알 수 없는 참조는 오류로 다룬다.
- Review가 시작할 때 정확한 Spec·CodeState·환경을 고정한다. 진행 중 파일이 바뀌어도 해당 검사의 입력을 바꿔 적지 않는다.
- Claim: verified / failed / inconclusive / unobserved. 상세 판정 알고리즘은 #82. 미실행과 비교 불가를 같은 이유로 기록하지 않는다.
- Review: ready / needs-review / blocked. 검토 상태이지 사람의 최종 수용이 아니다. #80은 제출된 verified의 최소 근거와 미검증·추가 실패·명시적 blocker를 구분하고, 의미 평가 확장은 #82에 둔다.
- Freshness: current / stale / unknown, 평가 범위와 이유·근거 포함. 문서·코드·테스트 의미·환경의 관련 변화로 재평가한다.
- 알려진 관련 변경으로 영향받는 결과는 재검증한다. 영향 없음의 판단도 출처·범위를 남긴다. 일반적인 잠재 영향 가능성을 모든 결과의 unknown이나 자동 차단으로 확장하지 않는다.
- HumanDecision 추가는 Projection 반영을 요구할 수 있으나, 그 이유만으로 판단 근거의 의미상 Freshness를 stale로 만들지 않는다.
- 표시만 바뀌고 검증 입력 의미가 같으면 의미상 Freshness는 유지한다. 실제 제품 동작·접근성 등을 바꾸는 UI 변경을 표시-only로 일괄 분류하지 않는다.

## 5. 계약 검증 fixture 계획

| 경우 | 확인할 계약 결과 |
|---|---|
| 같은 commit, 다른 dirty 내용 | 서로 다른 CodeState |
| untracked 등 관찰 제외 존재 | 동일성을 과장하지 않고 scope/gap 보존 |
| Spec MD 무승인 수정 | 기존 승인 Spec 유지, 수정본은 미승인 |
| 사람 승인 조건 변경 | 과거 결과 보존, 새 Spec과 결과 혼용 거부 |
| 테스트 의미·환경 변경 | 비교 가능성·Freshness 재평가 |
| Before 없음 / 비교 불가 | 회귀 verified 승격 금지 |
| 관련 검사 선정만 있고 실행 근거 없음 | 실행·통과 표시 금지 |
| 추가 테스트 통과, 필수 테스트 미실행 | 필수 미검증 유지 |
| 추가 검사 실패 | 실패·보고 필요 보존, 자동 완료 승격 금지 |
| 막연한 잠재 영향만 존재 | 전역 완료 차단 사유로 자동 생성하지 않음 |
| 다른 Issue/Task/attempt 연결 | 실행 근거·Snapshot·Decision의 부적절한 연결 거부 |
| Decision append | Projection 갱신 필요와 의미상 Freshness 분리 |
| 완료 후 코드 변경 | 과거 Decision 보존, 새 코드에 자동 승계 금지 |
| 표시-only 변경 | 의미상 근거 유효성 유지 |
| 과거 revision 재저장 / 활성 충돌 | 덮어쓰기·비결정적 선택 거부 |
| Skill과 Dashboard가 같은 입력으로 준비 상태 조회 | 동일한 행동·입력 버전·규칙 버전이면 같은 판정과 근거 반환 |
| 필수 검사 미실행 상태에서 Review 작성 | 누락을 담은 Review 작성 가능, 검증 완료와 구별 |
| Spec 초안은 있지만 사람 승인 없음 | 초안 검토 준비와 활성 기준 사용 준비를 구별 |
| SDD/TDD 미선택, 필요한 산출물·근거는 존재 | 방법론 미선택만으로 준비·완료를 차단하지 않음 |
| TDD 선택 metadata만 있고 Before receipt 없음 | 방법론 선언으로 Before 또는 회귀 통과 생성 금지 |
| 준비 상태 조회 후 입력 revision 변경 | 기존 조회 결과를 현재 준비 상태로 재사용하지 않음 |
| 목표 기록만 있고 Issue/attempt 실행 근거 없음 | 목표 탐색 기록을 실행·검증 증거로 승격하지 않음 |
| 사용자 요청과 에이전트의 변경 성격 추정이 함께 전달됨 | 요청 출처와 추정 근거를 구별해 보존. Skill 선택 정책 자체는 #81에서 검증 |
| 기존 산출물로 입력 충족, 추가 Skill 미사용 | 정상 준비·수행 결과 연결 가능. Skill 호출 기록을 필수로 요구하지 않음 |
| 기존 문서는 있지만 다른 범위·미승인·stale 상태 | 단순 파일 존재로 재사용 준비를 인정하지 않고 해당 행동에 부족한 입력을 설명 |
| 서로 다른 Skill 또는 직접 수행으로 같은 유형의 산출물 생성 | producer 이름과 무관하게 같은 type·scope·version 계약으로 검증·조회 |
| 수행 도중 입력 revision 변경 | 결과에 실제 사용한 입력 보존, 현재 입력에 대한 결과로 자동 승계 금지 |

## 6. #81·#82에 제공할 인터페이스 범위

- #81: using-ownhands와 각 Skill에 `inspect_stage`, `current`/`current_activation`, producer-neutral `outcome`을 제공한다. 목표·Issue·Spec 초안부터 Baseline·Review까지 다루며 추가 Skill 없이 기존 산출물을 활용하는 경로도 지원한다. Router 선택 정책·방법론 연결은 #81이 정한다.
- Dashboard: 같은 기록과 준비 상태 조회, ReviewSnapshot·근거·Freshness를 사람에게 설명하는 소비자다. 화면 자체가 별도 판정 규칙을 갖지 않는다. 사람의 결정 쓰기는 동일한 HumanDecision 계약을 따른다. UI 구현은 #80 밖이다.
- #82: Spec criteria, 정확한 code/environment/test 참조, baseline·test receipt, selection rationale, gap/inference/conflict와 비교 가능성 정보를 입력으로 제공. Claim·Review 평가 결과는 입력 참조와 함께 반환하도록 계약 정의.
- #83: 기존 Control 책임 정리. #80은 삭제나 legacy 상태 의미 변경을 하지 않는다.

## 7. 구현 결과와 후속 경계

완료: 별도 `ownhands.lifecycle` v1 저장소, 불변 참조와 activation, exact SpecApproval 연결, CodeState/Environment fingerprint, legacy Evidence binding, Micro/Verification Baseline, Review/Snapshot/Decision, semantic Freshness, 공통 준비 상태와 producer-neutral outcome을 구현했다.

검증 결과와 남은 한계는 `docs/m5-r/lifecycle-verification.md`에 기록한다. #81은 Router와 방법론 선택을, #82는 Claim 의미 평가를, #83은 legacy Control 정리를 이어간다.

참조:
- https://github.com/taejung3852/OwnHands/issues/80
- https://github.com/taejung3852/OwnHands/blob/779b5568c38a154b4dc7b55818e806a5e53639f0/docs/m5-r/core-responsibility-map.md
- https://github.com/taejung3852/OwnHands/tree/779b5568c38a154b4dc7b55818e806a5e53639f0/src/devharness

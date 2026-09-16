# M5-R2 Issue Lifecycle 계약 — #80

현재 MCP 기본 도구와 구형 Control 호환 경계는 [#83 분리 계약](control-boundary.md)에 정리한다.

## 목적과 범위

OwnHands는 작업을 검증 가능하게 정의하고 수행하도록 돕고, 근거를 사람이 이해해 최종 판단하게 하는 얇은 개발 하네스다. Dashboard는 같은 계약을 읽는 사람 검토 화면이다.

새 계약은 `ownhands.lifecycle`, schema version `1`이다.

`Work Issue → Verification Spec → Baseline → 수행·검사 → Review → Review Snapshot → Human Decision`

이 계약은 기록의 식별자·버전·소유 범위·참조 관계·활성 버전·준비 상태를 정의한다. Skill routing과 방법론 선택은 #81, Claim 평가 알고리즘은 #82, UI는 후속 Dashboard 이슈의 범위다. SDD·TDD 사용 여부는 선택적 출처 정보이며 완료 조건이 아니다.

## 사람과 에이전트의 경계

- 사람은 비즈니스 검수 조건과 의미 있는 변경을 결정한다. 사용자가 명시한 변경 지시는 그 변경에 대한 승인 출처가 될 수 있다.
- 에이전트는 검사 방법과 관련 영역을 찾아 실행한다. 선정 이유·실행 근거·결과·남은 불확실성을 기록한다.
- 에이전트가 검수 조건 변경이 필요하다고 판단하면 이유와 변경안을 제시하고 사람의 결정을 기다린다.
- 추가 검사 통과나 AI 추정은 실행하지 못한 필수 조건을 통과로 바꾸지 않는다. 추정은 사실·빈틈과 구분한다.
- 막연한 잠재 영향만으로 완료를 자동 차단하지 않는다. 실제 발견한 실패와 미실행 필수 조건은 숨기지 않고 Review에 남긴다.
- 사람의 수용은 특정 Snapshot에 대한 판단이다. Claim 상태나 없던 Evidence를 바꾸지 않는다.

## 저장 경계

Lifecycle v1은 기존 private data root의 `lifecycle-v1.sqlite3`에 저장한다. 기존 `catalog.sqlite3`에 테이블을 추가하거나 기존 EventLog에 lifecycle event를 쓰지 않는다.

이 분리는 다음 의미를 지킨다.

- Catalog v3의 정확한 schema와 legacy migration을 변경하지 않는다.
- Projection v1이 모르는 event를 넣어 replay를 깨뜨리지 않는다.
- 기존 Task·Evidence는 읽기 참조로 연결하며 원래 result/basis/type/version을 바꾸지 않는다.
- lifecycle record와 activation은 각각 순서와 이전 hash를 가진 append-only journal이다. hash 검사는 우발적 손상 탐지이며 관리자 변조 방지 서명은 아니다.

## 공통 식별과 참조

모든 lifecycle 참조는 아래 네 필드를 가진다.

```json
{
  "kind": "spec",
  "id": "spec:80",
  "revision": 2,
  "hash": "sha256-without-prefix"
}
```

- `kind`: 객체 종류
- `id`: 같은 논리 객체의 안정 ID
- `revision`: 내용이 달라질 때 증가하는 불변 버전
- `hash`: 해당 revision의 scope·data·순서·시간·이전 record hash를 포함한 fingerprint

같은 ID와 같은 scope·data를 다시 append하면 참조 closure가 아직 유효한지 확인한 뒤 같은 참조를 반환한다. 이후 활성 선택이 바뀌어도 이 멱등 조회가 새 기록을 만들지는 않는다. 내용이 다르면 새 revision을 추가한다. 같은 kind·ID를 다른 scope로 옮기는 것은 거부한다. 과거 revision은 수정하거나 삭제하지 않는다.

scope는 `project_id → issue_id → task_id → attempt_id` 순으로 좁아진다. attempt 범위의 새 기록은 같은 전체 scope의 현재 활성 Attempt가 존재해야 한다. 하위 기록은 같은 상위 범위의 참조만 사용할 수 있다. 다른 Issue·Task·attempt의 실행 근거, Snapshot, Decision은 거부한다. 이전 attempt 연결만 같은 Issue 안에서 명시적으로 허용한다.

## 객체 계약

| kind | scope | 핵심 data와 참조 |
|---|---|---|
| `work_issue` | project | 제목, 외부 source, 내용, 사용자 요청 출처 |
| `attempt` | issue+task+attempt | WorkIssue, 이전 attempt. 수정·테스트 반복은 같은 attempt, 완료 후 재작업은 새 attempt |
| `spec` | issue | WorkIssue, MD 경로와 고정된 본문, criterion ID·문장·필수 여부·비교 유형(`current/preserve/improve`) |
| `spec_approval` | issue | 정확한 Spec revision, human actor, approved/rejected, 이유와 출처 |
| `code_state` | attempt | format version, commit, working-tree fingerprint, 관찰 coverage·제외, 파일별 kind/mode/hash |
| `environment` | attempt | format version, 설명·구조화 details와 그 내용에서 계산한 fingerprint |
| `baseline` | attempt | 활성 Spec과 그 정확한 SpecApproval·CodeState·환경, `micro/verification`, 같은 입력의 Before Observation 또는 누락 이유 |
| `evidence_binding` | attempt | 기존 Evidence ID. raw object를 다시 읽어 hash·size·purge와 Task scope 검증 |
| `observation` | attempt | 활성 Spec과 그 정확한 SpecApproval·CodeState·환경, test/criterion/phase/meaning, result/basis, 선정 이유, Evidence binding |
| `review` | attempt | 활성 Spec과 그 정확한 SpecApproval·After CodeState·환경·Verification Baseline·Claim·추가 검사·불확실성·추정·blocker와 파생 Review 상태 |
| `snapshot` | attempt | 정확한 Review 참조를 판단용으로 고정 |
| `human_decision` | attempt | Snapshot, human actor, 결정·이유·출처. append-only |
| `outcome` | 단계별 project/issue/attempt | 단계·행동, 읽은/재사용한/생성한 참조, 수행 상태·gap, 선택적 producer provenance |

Micro Baseline은 작은 조사나 특정 검사 준비 상태를 고정하는 제한된 기준이다. Verification Baseline은 승인된 Spec의 Before 비교 근거를 고정한다. 두 종류 모두 관찰 범위와 누락을 명시하며, `micro`라는 이름만으로 Verification Baseline이나 회귀 보장이 되지 않는다.

기존 Evidence 연결은 `EvidenceStore.resolve`뿐 아니라 raw content 검증까지 수행한다. 같은 Evidence를 다른 attempt에 다시 묶지 않는다. Task 생성 당시 commit/environment는 역사적 snapshot이며 현재 CodeState로 재해석하지 않는다.

## 활성 버전 선택

- Issue마다 활성 attempt 하나를 activation journal의 마지막 유효 record로 선택한다.
- Issue마다 활성 Spec 하나를 같은 방식으로 선택한다. Spec 활성화에는 그 revision을 가리키는 human `approved` 기록이 필요하며, `current_activation()`과 Projection은 Spec과 정확한 승인 참조를 함께 반환한다.
- 미승인 초안, 최신 파일 수정 시각, 에이전트의 자기 승인은 활성 Spec을 바꾸지 않는다.
- code state, environment, baseline, review, snapshot은 필요 시 attempt scope와 명시적 slot으로 활성화할 수 있다. Baseline은 `micro`와 `verification` slot을 구분한다.
- 동일 입력 journal에서는 순서가 결정적이다. 중복·누락 sequence, 바뀐 previous hash, 알 수 없거나 변조된 참조는 오류다. replay는 activation이 가리키는 artifact와 SpecApproval의 존재·kind·scope·binding도 다시 검증한다.

`actor.kind`, `actor.id`, `source`는 감사 가능한 provenance다. `LifecycleStore`는 값의 형식, 정확한 Spec 연결, 승인 결정을 검증하지만 사람의 로그인이나 서명을 인증하지 않는다. 실제 사용자는 인증된 쓰기 경계에서 이 값을 주입해야 한다.

## Claim·Review·Freshness

세 축은 독립적이다.

- Claim: `verified / failed / inconclusive / unobserved`
- Review: `ready / needs-review / blocked`
- semantic Freshness: `current / stale / unknown`

Lifecycle v1은 Claim 평가 엔진을 구현하지 않는다. 제출된 `verified`가 최소한 승인 Spec의 criterion, 같은 Review 입력, 실제 관찰된 pass, 필요한 비교 가능한 Before를 참조하는지 검증한다. 정확한 평가 정책은 #82가 제공한다.

criterion의 비교 유형은 현재 결과만 확인하는 `current`, 기존 성공 동작 유지를 확인하는 `preserve`, 관찰된 실패의 개선을 확인하는 `improve`다. `preserve`는 같은 test meaning·환경의 관찰된 Before `pass`와 After `pass`를 요구한다. `improve`는 같은 조건의 관찰된 Before `fail`과 After `pass`를 요구한다. 따라서 Before 실패는 기존 동작 유지의 근거가 될 수 없고, 사람이 승인한 criterion이 `improve`일 때만 개선 근거가 된다.

Before가 없거나 Before 결과가 `not_run`/`inconclusive`면 비교 Claim을 `verified`로 저장할 수 없다. Before·After의 test meaning이나 environment가 다르면 비교 가능하다고 처리하지 않는다. 추가 검사 실패가 있으면 Review는 `needs-review`가 된다. 실제 필수 입력·권한·서비스 부재, 실행 실패, 유효하지 않은 필수 근거는 정해진 blocker reason code로 남길 때만 `blocked`가 된다. 막연한 잠재 영향은 `uncertainties`에 기록하며 blocker로 저장하지 않는다. 미검증 결과를 포함한 Review 작성 자체는 가능하다.

Freshness는 Review가 참조한 Spec·CodeState·환경과 모든 Claim·추가 Observation의 test meaning을 현재 입력과 비교한다. Spec은 승인과 version의 의미를 보존하기 위해 정확한 참조를 비교하고, CodeState와 Environment는 기록 ID가 아니라 검증된 내용 fingerprint를 비교한다. 같은 코드·환경을 새 ID로 다시 기록한 것만으로는 `stale`이 되지 않는다. 관련 내용이 바뀌면 `stale`, 현재 test meaning을 확인할 입력이 없으면 `unknown`, 모두 같으면 `current`다. Human Decision이나 표시-only outcome 추가는 Projection 재생성 필요를 만들 수 있지만 그것만으로 semantic Freshness를 stale로 만들지 않는다.

## CodeState

`capture_code_state(repository)`는 HEAD commit과 Git tracked/untracked 파일의 경로·종류·mode·content hash를 결합한다. 저장할 때 파일·제외 항목의 canonical shape와 coverage 일관성을 확인하고 fingerprint를 다시 계산한다. 같은 commit이어도 파일 내용, 새 파일, 삭제, symlink, 실행 mode가 다르면 fingerprint가 다르다. `environment_state(description, details)`도 설명과 구조화 details에서 검증 가능한 fingerprint를 만든다.

ignored content, submodule/nested working tree, 지원하지 않는 filesystem object는 exclusion으로 기록하고 coverage를 `partial`로 둔다. fingerprint는 관찰한 범위의 동일성만 말한다. 파일 내용은 lifecycle record에 복사하지 않는다.

## 단계 준비 상태

`inspect_stage(stage, action, scope, inputs, request_context)`는 Router, Skill, Dashboard가 공유하는 파생 조회다.

지원하는 단계는 목표 탐색, Issue 구체화, Spec 작성·검토·활성화, Baseline 수집, 수행, Review 작성·완료, 사람 판단이다. 각 단계는 정해진 scope 깊이를 확인하고, attempt 단계는 현재 활성 Attempt를 요구한다. Baseline·수행·Review 작성은 현재 활성 Spec과 정확한 승인 참조 쌍을 요구한다. Review 작성은 Verification Baseline의 Spec·승인·환경이 Review 입력과 맞는지도 확인한다. 결과는 다음을 포함한다.

준비 상태와 `outcome` 저장은 같은 단계별 scope 규칙을 공유한다. 목표 탐색과 Issue 구체화는 project, Spec 단계는 issue, Baseline·수행·Review·사람 판단은 attempt 범위다. 따라서 Issue를 만들기 전 탐색 결과도 project 범위 outcome으로 남기고, 이후 만들어진 WorkIssue를 출력 참조로 연결할 수 있다.

- `readiness`: `ready / needs-input / invalid`
- 정확한 `input_refs`와 요청·제약·변경 성격 출처
- 입력별 `checks`, 안정적인 reason code, 부족하거나 잘못된 입력
- scope·입력 revision·rules version의 `evaluated_against`

`ready`는 명시한 다음 행동의 입력이 준비됐다는 뜻이다. 실행 권한, Claim 통과, Review 완료, 사람 수용을 뜻하지 않는다. 예를 들어 필수 결과가 없어도 누락을 담은 Review를 작성할 수 있다. 실행 단계는 승인된 현재 Spec만 사용한다.

Wayfinder·grill-me·SDD·TDD 같은 이름은 schema 필수 enum이 아니다. `outcome`은 producer와 무관하게 같은 type·scope·version 참조를 남긴다. 기존 산출물로 입력이 충족되면 Skill 없이 바로 진행할 수 있다. 어떤 방법론을 썼다는 선언만으로 산출물이나 Evidence를 생성하지 않는다.

## API 예시

```python
from devharness.lifecycle import LifecycleStore, capture_code_state, environment_state

with LifecycleStore(catalog) as lifecycle:
    readiness = lifecycle.inspect_stage(
        "baseline",
        "capture",
        attempt_scope,
        {"spec": spec_ref, "approval": approval_ref,
         "code_state": code_ref, "environment": env_ref},
        {"request": "승인된 조건 검증", "source": "conversation:request"},
    )
```

Dashboard와 Skill은 이 결과를 각각 다시 계산하지 않고 같은 계약으로 읽는다. `outcome`에는 실제 사용한 입력 revision을 남긴다. 수행 도중 입력이 바뀌면 과거 결과는 당시 입력에 고정되고 현재 입력에 자동 승계되지 않는다.

## 호환 경계와 제외 범위

- Execution Contract v1.x를 Verification Spec으로 이름만 바꾸지 않는다.
- legacy Gate/Guarantee/override/config approval/App Server approval을 Review, SpecApproval, HumanDecision으로 치환하지 않는다.
- Projection v1 freshness와 semantic Freshness를 합치지 않는다.
- 실제 테스트 실행기, Router 선택 알고리즘, Skill 설치·발견, Claim 평가, Dashboard UI, 과거 데이터 변환·삭제는 이 계약에 포함하지 않는다.

상위 책임 경계는 [Core 책임 매핑](core-responsibility-map.md)을 따른다.

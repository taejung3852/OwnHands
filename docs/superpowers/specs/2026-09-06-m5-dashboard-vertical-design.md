# M5 Dashboard Vertical Product Design

## Status and approval boundary

- **Status:** Approved design direction under prior user delegation
- **Approval mechanism:** 사용자 사전 위임에 따른 에이전트 결정
- **Human review:** 사용자가 이 문서의 세부 UI/UX를 직접 검토하지 않았다.
- **Scope:** M5-01~M5-09의 local Dashboard vertical product 설계

이 결정은 M5 설계 문서 작성과 후속 구현 계획의 기준선을 정한다. 현재 M0-07 시안의 화면 구조를 승인하거나, M5 Production UI 구현 완료·사용성·사람 검토를 주장하지 않는다. 구현 결과는 실제 M3/M4 packet과 M1 Event/Evidence store를 사용해 별도로 검증해야 한다.

## Goal

사용자가 raw diff나 긴 로그부터 읽지 않고 다음 순서로 한 작업을 이해하고 판단하게 한다.

```text
쉬운 말 Summary
→ 변경·연관 기능·검증 Trace
→ Claim과 상태별 Evidence
→ 사용자 Decision
```

Dashboard는 Control과 Assurance의 사실을 재작성하는 원본이 아니다. Canonical Event Log, M1 Evidence Store, M2 계약, M3 Control Validation, M4 Assurance packet을 검증해 보여 주는 local review interface다. 정보가 없거나 서로 연결되지 않으면 성공 문장을 만들지 않고 `Not Evaluated`, `Unobserved`, `No Data`, 또는 오류 상태를 보여 준다.

## Architecture alternatives

| 대안 | 장점 | 단점 | 결정 |
|---|---|---|---|
| Static HTML generation | 가장 작고 기존 M1~M4 renderer를 재사용하기 쉬우며 공격 표면이 작다. | Decision 기록, Feature Validation 요청, freshness 갱신, Evidence 권한 검사를 정적 파일만으로 안전하게 처리할 수 없다. | 기각 |
| Client SPA | 복잡한 상태 전환과 component 재사용이 쉽고 풍부한 Diagram interaction에 유리하다. | 새 framework·build chain·client state가 추가되고, 검증되지 않은 packet 해석과 Raw Evidence 경로가 browser 쪽으로 이동한다. M5 범위보다 큰 새 신뢰 경계를 만든다. | 기각 |
| Standard-library loopback SSR | 기존 Python Core·HTML escaping·schema validation을 재사용하면서 Evidence 조회와 Decision을 서버에서 통제한다. Native HTML과 작은 progressive enhancement만으로 5개 화면을 구현할 수 있다. | routing, CSRF/Origin, session token, 상태 갱신을 직접 구현해야 한다. | **채택** |

Production Dashboard는 Python 3.12 표준 라이브러리로 loopback에만 bind하는 server-rendered application으로 구현한다. 새 framework나 runtime dependency를 추가하지 않는다. JavaScript는 theme, SVG focus/navigation, 필요한 상태 갱신을 위한 작은 progressive enhancement로 제한하며, 핵심 읽기·검토·form submit은 JavaScript 없이도 동작해야 한다.

## Trust and data boundaries

### Authoritative sources

M5는 다음 기존 객체의 의미를 바꾸지 않는다.

1. M1 Catalog, Canonical Event Log, Evidence Store, Task Guarantee Report, Projection freshness
2. M2 Project Baseline, Task Overlay, Task Execution Contract, Context Status report
3. M3 sanitized runtime review packet과 Control Validation records
4. M4 Assurance packet의 contract snapshot, impact, test design, before/after receipts, comparison, gaps, Gate

실제 vertical slice 입력은 `/tmp/ownhands-m3-runtime-path-closure-20260906.json`과 `/tmp/ownhands-m4-actual-packet-568c46e.json` 같은 실제 M3/M4 packet이어야 한다. 저장소에 커밋된 synthetic example이나 renderer fixture만으로 Production Dashboard Gate를 통과할 수 없다. 로컬 파일이 사라졌거나 검증에 실패하면 해당 source는 `Unavailable` 또는 `Invalid`이며, fixture로 대체해 성공을 유지하지 않는다.

### M3 project-level과 M4 task-level 분리

M3의 실제 packet은 특정 probe Task에서 관찰한 Codex runtime과 Control capability를 포함하지만, M5에서는 이를 곧바로 모든 Task의 통제로 복제하지 않는다.

- **Project-level Harness evidence:** M3 runtime/version, 현재 프로젝트에서 관찰된 control 종류, 관찰 시점, project/runtime applicability를 보여 준다. 다른 Task에도 유효하다고 자동 추론하지 않는다.
- **Task-level Control evidence:** M3 `task_ref`가 현재 canonical Task와 닫히고 해당 Evidence가 같은 Task에 속할 때만 Task Review에 연결한다.
- **Task-level Assurance:** M4 packet은 `task`, Contract fingerprint, restore point, patch hashes, test receipts가 현재 Task와 정확히 일치할 때만 사용한다.

Project-level M3 Pass와 다른 Task의 M4 Pass/Soft Block을 합쳐 하나의 Task 성공 상태로 만들지 않는다. Project-level source가 최신이어도 현재 Task 적용 여부가 증명되지 않으면 Task-level Harness 상태는 `Unobserved`다.

### Same-task identity closure

각 Task Review는 M1 Catalog의 canonical `project_id`, `worktree_id`, `task_id`, mode, start commit, branch, environment를 identity anchor로 사용한다.

Assembler는 다음을 모두 검사한다.

- M4 `task.project_id/worktree_id/task_id/environment_ref/mode`와 canonical Task가 일치한다.
- M4 Contract snapshot, packet, impact, tests, Gate가 같은 Contract fingerprint와 patch identity를 사용한다.
- Task-bound M3 packet의 masked `task_ref`가 canonical Task ID에서 계산한 reference와 일치한다.
- 모든 M1 Evidence record가 현재 Task에 속하고 purge되지 않았으며 content hash와 size가 일치한다.
- source의 observed time과 packet fingerprint를 Audit에 보존한다.

한 항목이라도 닫히지 않으면 source 전체를 다른 Task에 연결하지 않는다. UI는 mismatch를 명시하고 관련 Claim을 `Not Evaluated`로 낮춘다.

## `TaskReviewView` non-persistent assembler

`TaskReviewView`는 저장 schema나 새 truth source가 아니다. 요청 시점마다 기존 artifact를 읽어 검증한 뒤 renderer에 전달하는 비영속 read model이다. disk나 Catalog에 직렬화하지 않으며, packet의 result/basis/status 의미를 다시 정의하지 않는다.

Assembler의 책임은 다음으로 제한한다.

- canonical Task identity와 source identity closure
- source별 validation 및 freshness/completeness 계산
- 기능 Summary, related relations, verification, controls, Guarantee, Evidence link의 화면용 정렬
- source가 제공하지 않은 값의 명시적 `Not Evaluated`/`Unobserved`
- raw path, private command prefix, secret-like field의 masking

Assembler는 파일명이나 LLM 추론으로 기능 변화, 관계, 검증 우선순위, 성공을 만들지 않는다. M4 `impact.relations`, Contract mapping, block level처럼 기존 source에 근거가 있는 경우만 deterministic view rule을 적용한다. “필수 확인”은 Hard Block criterion이나 required impacted test relation에 연결된 경우, “권장 확인”은 Soft Block 또는 bounded Unobserved relation에 연결된 경우에만 표시한다. 그 외 관계는 “참고” 또는 “분류 근거 없음”이다.

## Evidence resolver

Dashboard는 모든 `evidence_ref`를 같은 종류로 취급하지 않는다.

### M1 Store reference

M1 Evidence Store에 실제 row와 object가 존재하는 reference다. Resolver는 `evidence_id`만 입력받아 task binding, purge state, fingerprint, content hash, content size, redaction status를 검증한 뒤 metadata를 반환한다. Raw content는 사용자의 명시적 disclosure 뒤에만 별도로 읽는다.

### M4 logical reference

M4 packet의 `evidence_refs`는 packet 내부 reference closure를 증명하지만, 현재 M1 Store object의 존재를 뜻하지 않는다. Resolver는 별도의 trusted registration이 없는 logical ref를 `Reference Only`로 표시한다. packet에 기록된 arbitrary path를 따라가거나 ref 문자열을 filesystem path로 해석하지 않는다.

M4 raw test output을 연결하려면 해당 logical ref를 같은 `evidence_id`로 사용하는 M1 Evidence Store row를 생성 시점에 등록해야 한다. 별도 mapping file이나 M5 전용 schema는 만들지 않는다. Evidence row의 canonical Task, `fields.packet_fingerprint`, content hash, redaction status가 M4 packet과 닫힐 때만 Store reference로 승격한다. 등록이 없으면 “Raw Evidence unavailable”이며, logical ref 자체만으로 Raw output을 제공하거나 검증 성공을 주장하지 않는다.

Evidence URL과 export에는 local absolute path를 넣지 않는다. Evidence Detail의 기본 GET은 metadata만 읽는다. 사용자가 같은 route에서 명시적으로 Raw disclosure를 요청한 경우에만 resolver가 content를 읽으며, Raw bytes는 HTML로 실행하지 않고 escaped text 또는 attachment로만 전달한다.

## Navigation and route boundary

Public navigation은 Task 중심의 5개 route로 제한한다.

| Route | 화면과 M5 범위 |
|---|---|
| `GET /tasks/{task_id}` | Task Review 기본 화면. M5-01~04와 Decision Panel(M5-07)을 포함한다. |
| `GET /tasks/{task_id}/harness` | Project Baseline, Task Overlay, M3 project/task control 상태를 보여 주는 Harness Status(M5-05). |
| `GET /tasks/{task_id}/validate/{subject_ref}` | 기존 Tool/API/Viewer/Runner를 통한 Feature Validation(M5-06). |
| `GET /tasks/{task_id}/history` | Canonical Event timeline, approval, Gate, final decision, masked export(M5-08). |
| `GET /tasks/{task_id}/evidence/{evidence_id}` | 공통 Evidence Detail. M1 object 또는 M4 logical reference 상태를 보여 준다. |

Decision form은 `POST /tasks/{task_id}`, Feature Validation 요청·관찰 기록은 같은 validation route의 `POST`를 사용한다. Masked export는 History route의 explicit format query로 제공한다. 별도 Dashboard home, project analytics, component catalogue route는 만들지 않는다.

### Minimal component boundary

- `FreshnessBanner`: event head, projected sequence, projection failure와 source time
- `StatusWithBasis`: result/status와 Observed/Inferred/Unobserved를 색 외 text·symbol로 표시
- `SummaryCards`: 요청, 실제 변화, 범위 밖, 현재 행동을 쉬운 말로 압축
- `BoundedDiagram`: 실제 source가 제공하는 node/edge만 SVG와 HTML fallback으로 표시
- `RelatedFunctionChecklist`: 관계 근거, 실패 형태, 우선순위, 검증 link
- `VerificationTable`: new feature, regression, static/build, direct validation, Control Validation 분리
- `GuaranteeClaims`: Claim→requirement→Evidence와 conflict/residual risk
- `EvidenceLink`: resolver 결과와 disclosure 경계를 공유
- `DecisionForm`: Gate와 authority를 다시 검사한 뒤 canonical decision을 기록

Task Review는 이 component를 한 페이지에 무조건 모두 펼치지 않는다. Summary를 먼저 보여 주고 Trace, Evidence, Decision 순서로 native `<details>/<summary>`와 직접 link를 사용해 progressive disclosure한다.

## Screen behavior

### Task Review and bounded Diagram

Header에는 Task mode, branch/start commit, observed time, Gate, Dashboard freshness와 collection completeness를 표시한다. Summary는 `task.goal`, Contract, observed changed paths, feature/contract relations에서 증명 가능한 내용만 사용한다. 기능 중심 change statement가 source에 없으면 파일 목록을 기능 설명으로 바꾸지 않고 “기능 요약을 평가할 근거 없음”으로 표시한다.

Before/After Diagram은 Contract의 declared baseline/hypothesis와 M4 actual changed path/relation이 모두 있을 때만 차이를 그린다. 각 node와 edge는 Evidence 또는 Contract reference를 가진다. source가 순서나 flow edge를 제공하지 않으면 dependency/impact graph로 명시하며 HWPX 처리 순서를 발명하지 않는다. 그릴 수 없는 경우 Diagram 자체가 `Unobserved`인 정상 상태다.

### Verification and Guarantee

사용자 표시는 다음 여섯 상태를 유지한다.

- Passed
- Failed
- Not Run
- No Adequate Test
- Inconclusive
- Unknown

M4의 세부 receipt/comparison status는 접힌 상세에서 그대로 유지한다. `missing`은 자동으로 Failed가 아니며, Gap의 `no_adequate_test`와 구분한다. Task Guarantee Report가 없거나 현재 task/commit과 닫히지 않으면 모든 Guarantee Claim은 `Not Evaluated`; M4 Gate를 대신 Task Guarantee Report로 표시하지 않는다.

### Harness Status

Project Baseline/Context Status와 M3 packet을 별도 source section으로 보여 준다. Config, AGENTS, Rules, Hooks, Sandbox, Approval 각각의 Configured/Loaded/Enforced를 분리하고 basis와 Evidence를 함께 표시한다. `Configured` Pass가 `Loaded` 또는 `Enforced` Pass처럼 보이면 안 된다. conflict, stale source, unsupported control, Imported historical limitation은 첫 화면의 주의 Summary에 포함한다.

### Feature Validation

DevHarness는 새 범용 test runner를 만들지 않는다. 등록된 기존 Tool/API/CLI/Viewer Adapter에 validation request를 전달하고, 입력·환경·expected·actual·생성 파일·Tool 오류·사용자 관찰을 M1 `direct_feature_probe` Evidence에 기록한다. HWPX adapter 또는 사람 관찰이 없으면 해당 기능은 `Unobserved`; synthetic expected result나 자동 test Pass로 사람 관찰을 대체하지 않는다.

### Decision Panel and canonical event

지원하는 결과 판단은 `accept`, `revise`, `reject`, `additional_validation`, `risk_acceptance`다. 저장되는 `task.decision.recorded` version 1 Event는 최소한 다음을 참조한다.

- exact Task ID와 decision
- source Assurance packet fingerprint와 Gate fingerprint
- decision source와 actor reference
- 이유, 수용한 residual risks, 후속 조치
- 관련 Evidence refs와 occurred time

Decision은 packet을 수정하지 않고 append-only Canonical Event Log에 추가한다. 같은 Task와 Gate fingerprint에 대한 semantic duplicate는 idempotent하며, 다른 내용의 같은 Event ID는 conflict다. Projection은 decision을 final state로 읽되 Evidence와 source packet은 그대로 유지한다.

Hard Block에서는 `accept`와 `risk_acceptance` control을 렌더링하지 않으며, 직접 POST하더라도 서버가 거부한다. Hard Block을 넘으려면 Contract/Policy 변경과 별도 승인·재검증이 필요하다. Soft Block risk acceptance는 exact Gate, 이유, residual risk, 명시적 product authority가 모두 닫힐 때만 기록한다. 결과 수용은 위험 행동 사전 승인이나 merge/deploy 실행을 뜻하지 않는다.

### Audit and History

Timeline은 Canonical Event sequence를 원본 순서로 사용하고 M3/M4 packet fingerprint와 Evidence link를 연결한다. M4 Assurance 결과는 현재 Task와 packet identity를 닫은 reference-only `assurance.evaluated` Event가 기록된 뒤 Dashboard freshness 대상이 된다. Approval Evidence, Control Validation, Evidence record/purge, Guarantee evaluation, Assurance Gate, direct validation, final decision을 Task 단위로 압축한다.

Raw Event payload 전체를 기본 노출하지 않는다. Masked export는 사용자가 선택한 Task와 section만 allowlist로 만들며 prompt, transcript, command output, secret-like field, absolute local path, raw object path를 포함하지 않는다.

## Freshness and collection completeness

Freshness와 completeness는 독립 축이다.

- **Freshness:** Canonical Event head와 projected sequence가 같은지, projection state가 ready인지 나타낸다.
- **Collection completeness:** 해당 Claim에 필요한 M1/M2/M3/M4 source와 human observation이 실제로 수집·해결됐는지 나타낸다.

Event가 모두 projection되어 `Fresh`여도 Rules/Hook/runtime relation/HWPX 사람 관찰이 수집되지 않았다면 completeness는 `Unobserved`다. 반대로 충분한 packet이 있어도 Event head보다 projection이 뒤처지면 Dashboard는 `Stale`이며 Decision을 받지 않는다. Source별 observed time과 Dashboard assembled time을 함께 표시한다.

## Visual and accessibility foundation

M0-07에서 승인한 **B — Warm Paper Neutral + Ledger Indigo** 방향을 Light/Dark theme의 출발점으로 사용한다. Indigo brand accent는 navigation, selection, primary action에만 쓰고 Pass/Warning/Danger semantic color와 분리한다. M0 HTML의 색 값은 contrast 재검사 중 조정할 수 있으며, A/C palette switcher와 fixture capture control은 Production UI에 포함하지 않는다.

필수 접근성 Gate:

- 문서 언어, landmark, heading hierarchy, skip link와 native form label 제공
- 일반·상태 text contrast 4.5:1 이상, focus indicator 3:1 이상
- 색에만 의존하지 않고 text와 symbol을 병행
- positive `tabindex`와 keyboard trap 금지, 모든 action과 disclosure를 keyboard로 사용 가능
- SVG의 첫 child `<title>`, `<desc>`, unique prefixed IDs, `aria-labelledby`; 동일한 HTML node/edge Evidence link 제공
- validation/freshness 변경은 focus 이동 없이 이해 가능한 status message로 알림
- 필수 animation 없음, `prefers-reduced-motion` 존중
- 320, 390, 1440px에서 document-level horizontal overflow 0; table/diagram 내부 scroll은 이름과 keyboard 접근을 제공
- Light/Dark 각각 browser keyboard flow와 VoiceOver smoke check

M5에서는 위 기계·수동 접근성 Gate와 한 번의 실제 review flow를 수행하되, 반복 HWPX 도그푸딩의 사람 이해 시간·판단 시간·Dashboard 오버헤드와 다양한 screen reader 사용성은 M6 human checks다. M6 전에는 사람 병목 감소를 주장하지 않는다.

## Security and privacy controls

- HTTP server는 loopback interface에만 bind하고 외부 network interface나 Unix-wide shared URL로 노출하지 않는다.
- 실행마다 high-entropy local session token을 발급하고 모든 route 접근에서 검사한다. 모든 mutation은 추가로 exact Origin 검사와 CSRF token을 요구한다.
- dynamic text, IDs, attributes는 context에 맞게 escape한다. Raw content에 active HTML, script, SVG, URL scheme을 허용하지 않는다.
- Dashboard data directory는 0700, generated packet/review/export/cache는 0600으로 생성하고 교체 후에도 mode를 재검사한다.
- 현재 actual M4 packet과 review가 기본 umask에 따라 0644로 생성되는 것은 알려진 M5 보안 공백이다. M5 구현은 atomic 0600 write와 권한 회귀 검사로 이 공백을 닫아야 한다.
- M4 test command의 `/Users/...` prefix, worktree path, raw data root와 object path를 모든 사용자 화면과 masked export에서 제거한다. 필요한 command 의미는 executable 이름과 selection scope로만 표시한다.
- `task_id`, `subject_ref`, `evidence_id`는 opaque identifier로 exact Catalog/packet lookup에만 사용한다. Resolver는 `..`, slash, URL-decoded path, symlink traversal을 filesystem lookup으로 사용하지 않는다.
- M1 Store object는 hash·size·purge state를 확인한 뒤 읽으며, M4 logical ref는 trusted mapping 없이는 content를 읽지 않는다.
- Raw Evidence는 기본 접힘이며 redaction status와 공유 금지 경계를 함께 표시한다.
- remote font, stylesheet, script, telemetry를 사용하지 않는다. CSP는 local self resources와 nonce가 있는 최소 script만 허용한다.
- Invalid/tampered packet, projection failure, unresolved Evidence는 fail closed하며 이전 성공 view를 그대로 유지하지 않는다.

## Failure states

| Condition | Dashboard behavior |
|---|---|
| Actual M3 또는 M4 packet 없음 | 해당 source `Unavailable`; fixture로 대체하지 않음 |
| 다른 Task의 packet | identity mismatch 오류; Task summary/Gate에 합치지 않음 |
| TGR 없음 또는 commit mismatch | Guarantee `Not Evaluated` |
| M4 logical ref만 존재 | Evidence `Reference Only`; Raw unavailable |
| HWPX human observation 없음 | Direct validation `Unobserved` |
| Projection behind Event head | `Stale`, lag count 표시, Decision submit 차단 |
| Projection/source integrity failure | 실패 원인과 rebuild 필요 표시, claims 숨김 또는 `Not Evaluated` |
| Diagram relation/flow 없음 | bounded Diagram `Unobserved`; graph 발명 금지 |
| Hard Block | accept/risk acceptance 서버 거부 |

## M5-01~M5-09 acceptance mapping

| M5 item | Design artifact and acceptance evidence |
|---|---|
| M5-01 Task Review | `/tasks/{task_id}` Summary, mode, Gate, conflict/unverified states; actual task identity closure |
| M5-02 Before/After Diagram | `BoundedDiagram`, source-backed nodes/edges, Evidence link, accessible SVG + HTML fallback |
| M5-03 Related Function Checklist | M4 relations + Contract block levels, deterministic required/recommended/reference classification, validation links |
| M5-04 Verification/TGR | six user states, original M4 comparison detail, scope/exclusions, Claim→Evidence; missing TGR stays Not Evaluated |
| M5-05 Harness Status | Project Baseline/Overlay + M3 project/task distinction, six controls, configured/loaded/enforced and basis |
| M5-06 Feature Validation | existing HWPX adapter path, expected/actual, M1 `direct_feature_probe`, human observation or Unobserved |
| M5-07 Decision Panel | canonical `task.decision.recorded`, five decisions, approval/result/integration separation, Hard Block server rejection |
| M5-08 Audit & History | Event sequence timeline, approval/Gate/final decision, 0600 allowlisted masked export |
| M5-09 Scope trace | product document↔parent tracker↔M5 leaf issue bidirectional mapping; missing, duplicate, orphan count 0 |

이 설계 문서 작업은 GitHub tracker를 수정하지 않는다. 따라서 M5-09는 현재 설계 요구사항일 뿐 Verified가 아니며, 후속 M5 leaf 연결과 양방향 coverage 결과가 있어야 완료된다.

M5 exit requires all of the following:

1. At least one actual M3 packet and one actual M4 packet are validated as inputs without pretending they belong to the same Task.
2. M5 검증 중 새로 생성한 actual same-Task vertical slice가 canonical Task, Contract, packet, Event, Evidence, projection and decision references를 end to end로 닫는다.
3. Every visible claim has a resolvable Evidence/Contract reference or an explicit Not Evaluated/Unobserved state.
4. Freshness lag and collection completeness are both visible and cannot be mistaken for each other.
5. Security, masking, 0600 output, keyboard, contrast, responsive and SVG fallback checks pass.
6. A reviewer can explain the task without reading raw diff first and reach Evidence/Raw detail within the defined progressive path; if no human review occurs, this criterion remains Unobserved.

## Test strategy for the later implementation

Implementation tests must be written before production code and cover:

- actual M3/M4 packet validation plus cross-task rejection;
- M3 project-level display without task-level enforcement inference;
- TaskReviewView remaining non-persistent and deterministic;
- M1 Store ref resolution versus M4 logical ref `Reference Only` behavior;
- missing TGR and missing HWPX human observation remaining Not Evaluated/Unobserved;
- source tampering, hash mismatch, purged object, path traversal and symlink attacks;
- freshness/completeness combinations and stale Decision rejection;
- canonical decision idempotency, Soft Block authority and Hard Block rejection;
- HTML/attribute escaping, Raw content non-execution and masked export allowlist;
- 0700 directories and 0600 packet/review/export/cache outputs;
- Light/Dark contrast, keyboard order, focus, reduced motion, accessible SVG and 320/390/1440 layout;
- no new runtime dependency or remote asset.

## Non-goals

- Usage & Cost Analytics(M8)
- Codex 외 Adapter(M8)
- packaging, installation, deployment, release(M7)
- 반복 HWPX dogfooding과 사람 병목 감소 주장(M6)
- 범용 test runner 또는 새 HWPX 실행기
- 완전한 dependency/data-flow discovery나 dynamic relation 추론
- Raw Evidence cloud/team sharing
- 조직용 compliance/audit platform
- merge, deploy, branch cleanup의 Dashboard 내 자동 실행
- 최종 logo, icon set, illustration, brand asset
- SPA framework, component library, remote font 또는 새 production dependency

## Consequences

- M5는 M1~M4 schema를 새 Dashboard truth schema로 복제하지 않고 하나의 검증된 read path로 연결한다.
- 실제 packet이 서로 다른 Task라는 사실을 보존하므로 초기 화면에 Partial/Unobserved가 많을 수 있다. 이는 성공 fixture보다 신뢰할 수 있는 제품 상태다.
- Standard-library SSR은 작은 범위와 local privacy에 유리하지만, route와 browser security test를 직접 유지해야 한다.
- Evidence resolver 등록이 없는 M4 logical reference는 drill-down이 제한된다. M5는 이를 숨기지 않고 향후 실제 Evidence registration의 필요 조건으로 사용한다.
- Decision과 Assurance reference Event가 추가되면 Projection handler도 같은 versioned contract를 알아야 한다. 지원하지 않는 Event는 기존처럼 Projection failure로 닫힌다.
- B 색상 방향은 유지하지만 M0-07 DOM, 문구, component와 capture mechanism은 Production 계약이 아니다.

# #89 Dashboard v1 — 상세 SDD Specification

상태: **상세 Spec v0.1 사용자 승인 / WI별 실패 fixture·완료 조건 고정 후 구현 승인**

승인 추가: 사용자는 본 Spec과 Work Item 분해를 승인하고 WI-01부터 작은 PR 단위의 구현을 요청했다. ELI5 backend는 provider 독립 `PresentationGenerator` 경계와 v1 concrete adapter 하나로 구성한다. 아래의 미체크 검토표는 초안 당시 기록이며 이 승인 문구가 우선한다. 개별 구현·검증 완료 여부는 WI별 기록에서 관리한다.

작성일: 2026-09-13. 제품 기준: [이슈 #89](https://github.com/taejung3852/OwnHands/issues/89) 및 「🤙🏾 M5 마일스톤 컨트롤 타워」의 최종 합의. 코드 기준: main `69f81517c5abcd81e84ec1aac873c006ab49f72d` (#88 병합).

이 문서는 상위 제품 방향을 다시 선택하지 않는다. #89가 위임한 상세 결정과 기존 코드 정합성 보완을 명세한다. 아래 수치·API·파일 배치는 **이번 상세 설계의 제안 기준**이며 기존 구현 사실이나 사용자 검토 완료를 뜻하지 않는다. Work Item은 분해안이지 GitHub에 생성된 이슈가 아니다.

## 0. 검토 요약과 승인 경계

목표: 사용자가 한눈에 작업·변경·검증 상태·미확인 사항을 이해하고 필요한 근거만 따라간다. Dashboard의 책임은 **Understand → Prove**이며 Decide는 밖에 둔다.

확정 유지: Review List, Review Detail, Evidence Drawer, Detailed Evidence Page; 한국어 ELI5; 최초 조회 시 생성과 별도 캐시; 상태와 숫자의 원본 직접 사용; Warm Paper Neutral + Ledger Indigo; 읽기 전용.

제외 유지: 테스트/재검증/코드 수정/Agent 실행/Claim 재판정/Review 재계산/Accept·수정 요청·보류/HumanDecision 쓰기/merge/Issue close, Analytics·Usage/Cost·Harness Status·별도 Audit History·복잡한 프로젝트 관리.

문서 산출 범위: 요구사항 추적표, 상태 매트릭스, View Model/API, 생성·캐시, 테스트, 구현 Work Item. 이번 작업은 파일·Skill·API의 제품 구현이나 GitHub 변경을 수행하지 않는다. Spec 검토 후 별도 구현 승인이 있어야 WI-01부터 착수한다.

### 다섯 정합성 결정

| 결정 | 문제 | 상세 해결 |
|---|---|---|
| D1 | 기존 dashboard Skill은 UI 조회 중 생성 전면 금지 | 최초 캐시 미스의 presentation 생성만 예외로 명시. 일반 조회는 GET, 파생 생성은 별도 POST. Skill/Router 문구와 테스트를 함께 정합화 |
| D2 | 모든 Claim verified여도 findings/diagnostics로 needs-review 가능 | 주의 항목을 Claim 미완료뿐 아니라 저장된 findings/diagnostics/blockers/conflicts에서 구성. 실패는 gaps에 없어도 표시 |
| D3 | Snapshot 설명과 변화하는 최신성이 섞임 | 불변 Snapshot 내용과 동적 context overlay 분리. 새 Evidence도 별도 표시. 상태 재평가 없음 |
| D4 | Store 생성자에 쓰기·정리 부작용 존재 | Catalog/Lifecycle/Evidence 조회 전용 진입점으로 검증 로직 재사용. 원본 DB mode=ro, query_only, 파일 쓰기 없음 |
| D5 | 숫자가 맞아도 자연어가 과장될 수 있음 | 문장별 원본 포인터·발화 종류, 구조/근거 검증, 보수적 표현, 실제 생성문 의미 검수. 자동 검사만으로 의미 정확성 보장 선언 금지 |

## 1. 소스와 기존 구현의 사용 경계

아래 경로는 저장소 상대 경로다. 코드 기반 근거이며 신규 항목은 뒤의 WI에서만 제안한다.

| 기존 경로 | 확인한 사실 | 이번 설계의 처리 |
|---|---|---|
| `src/devharness/lifecycle/store.py` | snapshot은 review ref를 연결; 논리 ID에 revision/hash 존재; 활성 선택은 별도 journal | Snapshot 전체 reference로 고정. 논리 ID 하나로 버전 추정 금지 |
| 같은 파일 `get`, `review_status`, `freshness` | closure 검증, unreadable/new evidence, 의미 fingerprint 비교가 구분됨 | 재사용하되 읽기 전용 호출 경로 필요. review_status의 BEGIN IMMEDIATE를 조회 경로에 사용하지 않음 |
| 같은 파일 생성자 | mkdir/스키마 생성/metadata INSERT 수행 | 조회 서비스에서 기본 생성자 사용 금지 |
| `src/devharness/catalog.py`, `evidence.py` | Catalog open 및 EvidenceStore 생성자는 쓰기 가능; EvidenceStore는 mkdir/chmod/reconcile 수행 | 기존 쓰기 모드 유지, 명시적 read-only factory 추가. 조회 중 reconcile·migration·purge 금지 |
| `src/devharness/lifecycle/evaluation.py` | required/optional/check coverage 분리. gaps에는 inconclusive/unobserved만 포함 | UI에 평가 복제 금지. counts는 Claim 상태를 표시용으로 집계, 실패/추가 finding은 별도로 포함 |
| `src/devharness/lifecycle/evaluation_store.py` | 관련 Observation 집합 수집 및 무결성 진단 | 새 근거 감지는 기존 범위 규칙 재사용. evaluate_review/compose_review는 Dashboard에서 호출하지 않음 |
| `skills/dashboard/SKILL.md` | explicit request, 조회 중 LLM 금지, Spec/Review/CodeState 캐시 | #89 최초 조회 예외와 Snapshot 캐시로 정합화 필요 |
| `skills/using-ownhands/SKILL.md` | requested + missing/stale presentation 경로 | 최초 UI view intent를 presentation 요청으로 인정. cache hit에서 Skill/LLM 호출 금지 |
| `src/devharness/mcp/server.py` | 기본 10 / legacy 25 도구 | 이 개수나 schema는 변경하지 않음. 새 Dashboard HTTP API는 MCP와 별도 |

설계 선택: 프론트 직접 DB 해석은 무결성·scope 규칙 중복 때문에 제외한다. 전체 Review를 정적 HTML로만 굳히는 방식은 동적 freshness/근거 손상 안내에 부족하다. **얇은 조회 API + 별도 파생 캐시 + 프론트**를 사용한다. 이벤트 버스·새 검증 DSL·범용 작업 큐는 도입하지 않는다.

## 2. 용어와 데이터 단위

- `Ref = {kind, id, revision, hash}`: 기존 lifecycle reference 그대로. scope는 `{project_id, issue_id, task_id, attempt_id}`로 서버가 원본에서 결정한다.
- `Snapshot`: 기존 `kind=snapshot` 레코드. 별도의 ReviewSnapshot 원본 타입을 만들지 않는다. 문서의 ReviewSnapshot은 이 레코드와 그 review closure를 뜻한다.
- `snapshot_key`: namespace + scope + 전체 Snapshot Ref의 canonical JSON에 대한 SHA-256. URL의 불투명 조회 키. 해시 자체는 접근 권한이 아니다.
- `SourcePointer = {record_ref: Ref, pointer: string}`: 해당 immutable record의 **data payload** 내부 JSON Pointer. 예: review의 `/claims/0/checks/1`. 모든 포인터는 선택 Snapshot의 유효 closure 안에서만 해석한다. Evidence field/raw의 출처는 evidence_binding의 `/evidence_id` 포인터와 별도 EvidenceVM field 식별자로 연결한다.
- `ContextOverlay`: 현재 기록과 비교한 freshness/new evidence/최신 Snapshot 존재/가독성. 저장된 Claim이나 verdict를 대체하지 않는다.
- `Problem`: 기존 원본의 비정상·미완료·진단을 화면에서 설명하는 항목. 새로운 Claim 상태가 아니다.
- 필수/선택의 단위는 Claim이다. check·test 실행 수를 Claim 수와 더하지 않는다.

## 3. 요구사항 추적표

모든 R은 v1 필수 요구사항이다. 선택 Claim을 다루는 요구사항도 제품 기능으로서는 필수다. Evidence E와 테스트 T는 §9에서 정의한다. 성공 조건은 구현 후 확인할 기준이며 현재 PASS가 아니다.

| ID / #89 출처 | 성공 조건 | 실패 반례 | 검증 방법 | Evidence |
|---|---|---|---|---|
| R01 / §1,8 읽기 전용 | 모든 탐색에서 Core/Lifecycle DB, raw, 코드, HumanDecision 변경 0; 캐시 쓰기만 분리 허용 | 첫 접속이 DB 생성·reconcile·판정 실행 | T01 쓰기 거부 권한/호출 spy/파일·DB 전후 비교 | E01 |
| R02 / §2,3 목록 | 1 issue/attempt당 최신 저장 Snapshot 카드, 결정적 정렬·필터·제목/캐시요약 검색 | 다른 attempt의 결과 합산, 검색 중 전체 LLM 호출 | T02 고정 다중 Snapshot 데이터 | E02 |
| R03 / §4.1~3 이해 | 기본 화면에 쉬운 2~3문장, 의미 아이콘, 기본 2~4 핵심 변경; 의도/관찰 구별 | 파일 목록만 표시, 미검증 기능을 보장 | T03 브라우저 + T13 실제 문장/이해도 | E03,E07 |
| R04 / §4.2,4.4 상태 | 같은 Snapshot의 verdict/Claim counts 사용; 필수/선택/제외/분모 구별 | 테스트 수를 조건 수로 표시, 필수 0을 모두 완료로 표시 | T04 count truth table | E02 |
| R05 / §4.5~6 주의 | 실패·미확인 및 findings/diagnostics/blockers/conflicts의 이유 노출; 안내 0~3개 | all verified + needs-review 이유 사라짐; failed가 gaps에 없어 누락 | T05 문제 조합과 소스 포인터 검사 | E02,E03 |
| R06 / §5 추적 | Claim/check→Observation→Evidence를 scope 내 추적; Before 부재/비교불가 명시 | 편리한 pass 한 건만 표시, 타 Task 근거 조회 | T06 비교·반복 실행·타 scope | E02,E04 |
| R07 / §5 근거 원문 | 수집된 command/stdout/stderr/diff/metadata만 안전한 텍스트로 제공 | 명령 추측, 로그 HTML 실행, 임의 파일 경로 열기 | T07 raw 경계 공격/누락 fixture | E04 |
| R08 / §6 최신성 | current/stale/unknown, 새 근거, 새 Snapshot 존재를 독립 표시 | 시간이 오래됐다는 이유로 stale, 새 실패를 옛 ready로 덮음 | T08 입력·증거 변경 | E02,E03 |
| R09 / §7.1,8 생성 경로 | 첫 실제 표시의 cache miss만 생성 요청; GET 및 hit 호출 0 | prefetch/새로고침마다 생성, review 저장 시 자동 생성 | T09 HTTP 및 호출 횟수 | E05 |
| R10 / §7.2~4 캐시 | scope/전체 Snapshot Ref/생성 recipe에 고정; 동일 key 동시 생성 1개 | logical ID만 사용, 모델 변경으로 원본 숫자와 혼합 | T10 경쟁·버전·브라우저 전환 | E05 |
| R11 / §7.5 장애 | 생성 실패 중에도 원본·근거 조회 가능; 재시도 상한 준수 | 무한 retry, 생성 spinner가 근거를 막음 | T11 timeout/invalid output/process restart | E05,E03 |
| R12 / §4.1,7.2 사실성 | 모든 생성 문장에 허용 SourcePointer; 범위 밖·과장·미확인 승격 없음 | 참조 ID는 맞지만 의미는 반대, raw의 지시문 실행 | T12 structural + T13 semantic/adversarial | E06,E07 |
| R13 / §9 시각 | 종이색/인디고·한국어 중심; 상태 텍스트/아이콘; 모바일/키보드 탐색 | 색상만으로 실패 표시, Drawer에서 초점 유실 | T03 반응형·키보드·명도 확인 | E03 |
| R14 / §1,7 Skill 정합성 | 최초 view intent 예외·Snapshot key가 Skill/Router/테스트에 일치 | Skill은 금지, 서버는 생성; UI가 매 요청 Skill 라우팅 | T14 문서/라우팅 계약 | E08 |
| R15 / §8,10 호환 | 기존 저장자료 읽기·Core 회귀·기본10/legacy25 유지, 새 Claim 평가 없음 | 조회 API 때문에 기존 쓰기/무결성 검증 약화 | T15 기존 전체 suite/변이 | E09 |
| R16 / §10 사용성 | 대표 3상황에서 사용자 이해도 기준 충족; 미관찰은 미검증 표시 | screenshot/단위 PASS를 이해도 PASS로 대체 | T13 이해도 관찰 | E07 |

## 4. 화면과 상태 매트릭스

### 4.1 화면 구조

| 화면 | 고정 정보 | 탐색 | 정보 우선순위/레이아웃 |
|---|---|---|---|
| Review List | 제목·아이콘·ELI5 한 줄·verdict·Claim 요약·freshness·Snapshot 생성 시각 | 검색/필터/페이지 이동/상세 | 카드. 시간은 LLM 생성 시간이 아니라 Snapshot 생성 시간. 20개씩 페이지 조회 |
| Review Detail | 작업 요약, 핵심 변경, 상태/이유, 필수·선택 요약, 문제/안내 | 근거 Drawer, 목록 복귀, 최신 Snapshot 링크 | 900px 이상 상단 2열, 아래 1열. 900px 미만 요약→상태→검증 순서 1열 |
| Evidence Drawer | Claim/check, 판정 이유, Before/After, 환경/검사 의미, Evidence 수 | Claim 선택, 상세 근거, 닫기 | 데스크톱 우측 최대 480px, 모바일 전체 너비. 열기 전 focus 저장, Escape 닫기, focus 복원 |
| Detailed Evidence | 원본 Claim/check·실행별 결과·CodeState/commit·비교·Evidence·raw | 이전 Detail/Drawer 복귀, Evidence 선택, 텍스트 구간 이동 | 기술 정보 공개. 로그/명령/diff는 escaped text. 원래 검색/필터/스크롤 보존 |

기본 화면은 파일·함수·테스트 이름을 요약문에 노출하지 않는다. 근거 부족으로 핵심 변경을 2개 만들 수 없으면 실제로 근거 있는 0~1개만 표시하고 부족을 명시한다. 2~4개는 기본 분량이지 내용을 발명할 의무가 아니다. 좁은 화면에서 '2~3줄'은 2~3개의 짧은 문장으로 해석하며 임의 잘림으로 주의사항을 숨기지 않는다.

### 4.2 목록 선택·검색·정렬

1. 권한 허용된 단일 project의 저장된 Snapshot을 issue/attempt별 묶어 가장 큰 journal sequence 1개를 기본 표시한다. 활성화 기록이 없어도 저장된 Snapshot은 표시한다. 활성 Snapshot과 최신 저장 Snapshot이 다르면 라벨로 구별한다. 과거 Snapshot은 직접 URL/근거 연결로 조회 가능하나 별도 Audit History 화면은 만들지 않는다.
2. group rank: 원본 needs-review=0, blocked=1, 그 외 stale=2, 그 외 ready=3. unreadable/unknown verdict는 rank=0의 **자료 확인 필요** 보조 그룹이며 enum 변경이 아니다. ready+unknown은 rank=3 안에서 current보다 먼저. 같은 rank는 Snapshot sequence 내림차순, 마지막 동률은 snapshot_key 오름차순.
3. 필터는 중복 가능한 predicate: 확인 필요=needs-review 또는 unreadable; 차단=blocked; stale=freshness stale; 판단 가능=ready. 판단 가능 필터도 stale/unknown 라벨을 숨기지 않는다. 전체가 기본값.
4. 검색은 Unicode 정규화·대소문자 무시 부분 일치로 Snapshot에 결합된 issue 제목 및 **이미 저장된** ELI5 headline/summary에 적용한다. 미생성 요약은 검색할 수 없으므로 '생성된 요약과 작업 제목에서 검색' 문구를 표시한다. 검색 때문에 보이지 않는 Snapshot의 요약을 생성하지 않는다.
5. 목록 cursor는 조회한 record/activation head + 필터/검색 fingerprint + 마지막 정렬키 + cache의 ready_sequence 상한에 묶는다. 원본 head가 달라졌으면 LIST_CHANGED를 반환하고 첫 페이지로 갱신 안내. 요약 검색은 해당 상한 이하의 ready cache만 사용한다. 이후 캐시가 채워져 결과가 늘어나는 것은 다음 검색/목록 새 조회에만 반영한다. 페이지 집합을 도중에 재정렬하지 않는다.

### 4.3 상태 조합

| 원본/조회 상황 | 주 상태 | 추가 표시와 카드 | 허용 행동 |
|---|---|---|---|
| ready + current | 판단 가능 | '기록된 입력 기준' 라벨. 필요한 선택 제외 표시 | 조회 탐색만 |
| needs-review + 모든 Claim verified | 확인 필요 | findings/diagnostics/conflicts의 원인 표시 | 해당 근거로 이동 |
| blocked + failed | 검증 차단 | 차단 이유와 관찰된 실패 둘 다 유지 | 해당 근거로 이동 |
| ready + stale | 판단 가능 **(이전 결과)** | 최상단 '새 변경사항이 있습니다. 현재 검증은 이전 코드/Spec 기준입니다' | 과거 근거/새 Snapshot 링크 |
| needs-review/blocked + stale | 원본 주 상태 | 상태/차단과 stale 둘 다 표시 | 조회만 |
| 임의 상태 + unknown | 원본 상태 **(현재 적용 여부 미확인)** | 무엇이 없어 비교 못 하는지 표시. 녹색 현재 badge 금지 | 조회만 |
| 새 관련 Observation 존재 | 원본 상태 유지 | '이 보고서 이후 새 근거가 등록됐습니다. 결과에는 아직 반영되지 않았습니다' | 기존 근거 조회. 새 결과처럼 합산하지 않음 |
| 최신 다른 Snapshot 존재 | 현재 보고 있는 원본 상태 | '더 최근 보고서가 있습니다' 링크. 자동 이동 금지 | 명시적 새 Snapshot 이동 |
| 필수 0, 선택만 존재 | 원본 상태 유지 | '필수 항목 없음'. required_complete=true를 '제품 완료'로 번역하지 않음 | 선택 결과 조회 |
| 선택 제외 + unobserved | 원본 상태 유지 | 미확인 수에 포함, '선택 조건·이번 범위 제외'와 이유 표시; 필수 장애로 표현 금지 | 제외 근거 조회 |
| Review 없음/DB 없음 | 결과 없음 | '저장된 검토 결과가 없습니다'; DB 자동 생성 없음 | 목록 조회만 |
| ELI5 생성 중 | 원본 상태 즉시 표시 | '쉬운 설명 준비 중'; 원본 제목·안전한 임시 문구 | 근거는 즉시 접근 |
| ELI5 실패/설정 없음 | 원본 상태 유지 | '쉬운 설명을 불러오지 못했습니다'와 deterministic fallback | 근거 조회; 생성 버튼 없음 |
| 부분 Evidence 손상/삭제 | **자료 확인 필요**(조회 상태) | 검증 가능한 원본 메타데이터만, 과거 verdict는 '저장 당시' 표시. 현재 검증 완료 badge/생성 요약 억제 | 유효한 형제 근거 조회 가능 |
| journal 변조/권한 거부/미지원 schema | 결과 조회 불가 | 원문/숫자를 믿을 수 있는 것처럼 표시하지 않음; 안전한 오류 식별자 | 목록 복귀. 다른 project 정보 누설 금지 |

### 4.4 주의·안내·숫자 규칙

`problem_set`은 원본의 failed/inconclusive/unobserved Claim/check, blockers, findings, diagnostics, conflicts를 모은 **표현용 인덱스**다. D2에 따라 #89의 '문제가 없으면 숨김'은 이 집합이 비어 있을 때로 구체화한다. Claim enum과 Review verdict는 변경하지 않는다.

- dedup은 같은 source pointer와 같은 problem kind에만 적용한다. 다른 실행의 실패는 묶어 요약해도 전체 목록에서 사라지지 않는다.
- 상단 주의 카드 최대 3개: required blocker → observed failure → integrity/conflict → 미확인/판단불가 → 선택 제외 순서. 나머지는 '추가 N건' 조회로 모두 제공한다. 단순 선택 제외는 경고성 위험이 아니라 범위 설명이다.
- next_checks는 실제 문제/새 근거/stale source에 연결된 0~3개 정보 문장. 추가 발견/진단만으로 needs-review인 경우도 안내 가능하도록 D2 예외를 명시한다. 실행 명령/버튼·근거 없는 영향 추정은 넣지 않는다.
- unknown만 있으면 '다음 확인'을 발명하지 않고 최신성 배너에서 비교 불가 이유를 설명한다.
- total/required/optional 각각 `{total, verified, failed, inconclusive, unobserved}`. 각 그룹의 합은 total과 같아야 한다. all은 required+optional이며 제외된 선택도 분모에 포함한다. excluded_optional_count는 별도 보조 수치다.
- check coverage는 Drawer에서 따로 표시. Evidence 수는 고유 Evidence ID 수, 반복 Observation 수와 구분한다. 손상/삭제된 참조는 별도 unavailable 수로 남긴다.
- '7개 조건 중 5개 확인' 같은 **수치 문장은 API의 원본 집계 템플릿**으로 만든다. LLM 문장에 총계·상태 enum을 보관하지 않는다.

## 5. 불변 내용과 현재 맥락

### 5.1 Snapshot 일관성

모든 제목·Spec·Claim·counts·Before/After·원문 pointer는 선택한 Snapshot의 정확한 review closure에서 나온다. issue 제목도 당시 Spec/attempt가 참조한 WorkIssue revision으로 읽는다. 최신 issue title이나 다른 Review의 숫자를 끼워 넣지 않는다.

API 응답마다 `read_token`은 lifecycle record/activation head와 Catalog 관련 event head, 참조된 metadata fingerprint의 해시로 생성한다. 읽기 전용 transaction에서 결합하고 시작/끝 head를 비교한다. 바뀌면 최대 1회 재시도, 계속 바뀌면 409 SOURCE_CHANGED. 파일 내용은 제공 직전 hash/size를 검증한다. 두 DB와 raw 파일에 전역 atomic snapshot이 있다고 주장하지 않는다.

브라우저는 route의 snapshot_key 및 응답 Ref를 대조한다. 이전 페이지의 늦은 응답을 새 페이지에 적용하지 않는다. 동적 overlay 갱신은 별도 read_token과 확인 시각을 가지며 과거 본문·counts를 교체하지 않는다.

### 5.2 Freshness 입력의 출처

v1은 **등록된 현재 입력 기준**을 표시한다. 화면 조회가 새 CodeState/Environment/Spec을 생성하거나 테스트를 실행하지 않는다.

- issue의 active attempt/approved Spec, 해당 attempt의 active CodeState/Environment는 기존 activation journal에서 읽는다. `current_activation`의 scope 규칙을 따른다.
- 현재 test meaning은 active approved Spec과 active code/environment에 정확히 맞는 저장된 after Observation의 test_id→test_meaning에서 구한다. 동일 test_id의 의미가 충돌하거나 없으면 해당 비교는 unknown. 옛 Review의 test meaning을 현재 값으로 자기복사하지 않는다.
- 가능한 입력에서 기존 semantic freshness 규칙을 재사용한다. 비교 가능한 차이가 하나라도 확인되면 stale, 차이는 없으나 입력이 부족하면 unknown, 모두 비교 가능하고 같으면 current. recapture ID만 다른 동일 code/environment는 current다.
- 새 attempt는 과거 attempt의 code ref와 섞어 비교하지 않는다. `superseded_attempt=true`와 `freshness=unknown(reason=attempt_changed)`로 표시하고 최근 Snapshot 링크를 제공한다.
- active 상태가 없으면 unknown이며 '최신 레코드일 것'으로 추정하지 않는다. 등록 후 디스크가 바뀌었으나 수집되지 않은 상태는 알아낼 수 없으므로 **current는 실제 파일·외부 환경의 실시간 동일성 보장이 아니다.** 화면에 '기록된 입력 기준'과 input record 시각을 항상 표시한다.
- 원본 Review 이후 새 Observation은 `new_evidence_available` 별도 축이다. 기존 `_collect`의 동일 scope/spec/phase/semantic target 규칙을 재사용하고 판정은 호출하지 않는다.

### 5.3 캐시와 최신성의 분리

Presentation은 불변 내용만 설명한다. 생성 입력에 최신성 맥락을 제공할 수 있으나 모델의 지속 저장 문장에는 '현재 최신', '이후 새 근거 없음'을 쓰지 않는다. 동적 freshness/새 근거 문구는 API가 직접 만든다. 같은 Snapshot이 stale로 바뀌었다고 LLM을 다시 호출하지 않는다. 새로운 Snapshot은 새로운 key를 가진다.

## 6. View Model 및 API 계약

### 6.1 실행/보안 경계

v1은 단일 사용자 로컬 실행, loopback에만 bind한다. 서비스 시작 시 기존 data root와 하나의 project scope를 고정하며 요청으로 파일 경로나 다른 root를 바꿀 수 없다. 원본 DB는 `mode=ro`/`query_only=ON`; 없는 원본을 생성하지 않는다. migration은 별도 운영 경로의 책임이다.

Catalog/Lifecycle/Evidence에 명시적 `open_readonly`/reader 경로를 도입하고 공통 hash/closure/scope 검사 구현을 재사용한다. 별도 약한 SQL decoder로 우회하지 않는다. 일반 쓰기 모드 API는 유지한다. read transaction은 deferred read이며 `BEGIN IMMEDIATE`, reconcile, chmod, checkpoint, 이벤트 기록은 금지한다. cache만 원본 밖의 `dashboard-presentation.sqlite3`에 쓴다. 코드 저장소 안에는 data/cache를 만들지 않는다.

loopback도 인증 생략 근거가 아니다. 시작 시 세션 token을 로컬 사용자에게 제공한다. 사용자가 첫 접속에서 token을 입력하면 동일 origin의 세션 교환 경로가 HttpOnly/SameSite=Strict cookie를 발급한다. 이는 검증 도메인 동작이 아닌 접속 인증이다. 다른 Origin/CORS는 거부, POST는 CSRF 보호, Host는 허용 loopback host/port만. token/모델 credential/raw를 URL·로그에 남기지 않는다. 정적 페이지와 API는 같은 origin이다. 비밀정보는 브라우저 영구 저장소에 넣지 않는다. provider credential은 server 설정에만 둔다.

### 6.2 공통 타입

아래는 언어 독립 JSON 계약이다. 명시하지 않은 원본 접근 경로를 프론트가 추측하지 않는다. `null`은 값 없음이며 false/0과 다르다.

```text
Availability = available | not_collected | missing | purged | corrupt |
               denied | unsupported | redacted | too_large
ReadHealth = complete | partial | unavailable
Counts = {total:int, verified:int, failed:int, inconclusive:int, unobserved:int}
TextFact = {text:string, kind:intent|observed|gap|inference,
            sources:SourcePointer[]}
Problem = {id:string, kind:failure|inconclusive|unobserved|blocker|finding|
            diagnostic|conflict|excluded, required:bool|null,
            claim_id:string|null, check_id:string|null,
            reason_code:string, description:string, sources:SourcePointer[]}
ContextOverlay = {freshness:current|stale|unknown, reasons:string[],
  basis:registered_inputs, checked_at:ISO8601, input_refs:Ref[],
  new_evidence_available:bool|null, superseded_attempt:bool,
  newer_snapshot_key:string|null, read_health:ReadHealth}
Presentation = {status:absent|pending|ready|failed|unavailable,
  presentation_id:string|null, recipe_hash:string, icon:string,
  headline:TextFact, summary:TextFact[], key_changes:TextFact[],
  attention_items:TextFact[], next_checks:TextFact[],
  generated_at:ISO8601|null, generator_model:string|null,
  fallback:bool, reason_code:string|null, retry_after:ISO8601|null}
```

`SourcePointer[]`는 원본의 필요한 부분을 식별한다. 동적 overlay 안내는 TextFact와 별도 `context_notices`로 반환하고 캐시하지 않는다.

```text
ReviewCardVM = {
 snapshot_key, snapshot_ref:Ref, review_ref:Ref, scope,
 issue:{ref:Ref,title:string}, snapshot_created_at:ISO8601,
 review_state:ready|needs-review|blocked|null,
 state_label:string, state_reason:string,
 counts:{all:Counts,required:Counts,optional:Counts,
         excluded_optional_count:int}|null,
 required_complete:bool|null, context:ContextOverlay,
 presentation:Presentation, read_token:string
}
ReviewDetailVM = ReviewCardVM + {
 claims:ClaimVM[], problems:Problem[], context_notices:string[],
 remaining_problem_count:int, source_contract_version:int,
 rules_version:int|null
}
ClaimVM = {id,text,required,comparison:current|preserve|improve,
 status:verified|failed|inconclusive|unobserved,
 checks:CheckVM[], source:SourcePointer}
CheckVM = {id,statement,role,status,reason_codes:string[],
 before:ObservationVM[],after:ObservationVM[],
 comparisons:ComparisonVM[],conflicts:SourcePointer[],
 evidence_count:int,unavailable_evidence_count:int}
ObservationVM = {ref:Ref,phase,result,basis,test_id,test_meaning,
 code_ref:Ref,environment_ref:Ref,execution:object|null,
 evidence_links:EvidenceLink[]}
ComparisonVM = {test_id,comparable:bool|null,
 environment:same|different|unknown,
 test_meaning:same|different|unknown,
 expected_before:pass|fail|null,before_refs:Ref[],after_refs:Ref[]}
EvidenceLink = {evidence_key:string,source:SourcePointer,availability:Availability}
EvidenceVM = {snapshot_key,claim_id:string|null,check_id:string|null,
 evidence_key,metadata:object,availability:Availability,
 command:FieldVM,stdout:FieldVM,stderr:FieldVM,diff:FieldVM,
 raw:FieldVM,cas_hash:string|null,read_token:string}
FieldVM = {availability:Availability,text:string|null,
           reason_code:string|null,source:SourcePointer|null,
           next_cursor:string|null,truncated:bool}
```

비교 보조 값은 원본의 의미 fingerprint를 비교해 표시할 뿐, Claim을 재판정하지 않는다. 구형 v1 Review에 checks/coverage가 없으면 새 check를 발명하지 않고 `source_contract_version=1`과 원본 Claim 상태·Observation을 표시한다. '상세 검사 항목은 이전 형식에서 기록되지 않았습니다'라고 명시한다.

### 6.3 Endpoint 목록

공통 prefix는 `/api/dashboard/v1`. 성공 응답은 JSON, 오류는 `{error:{code,message,retryable},request_id}`. 아래 GET은 생성을 포함한 부작용이 없다.

| Method / path | 입력 | 성공 응답/동작 |
|---|---|---|
| GET `/reviews` | filter enum, q 최대 200자, cursor, limit 기본20/최대50 | `{items:ReviewCardVM[],next_cursor,list_token,summary_search:cached_only}` |
| GET `/snapshots/{snapshot_key}` | key만 | ReviewDetailVM. Snapshot 없음404, closure 일부 손상은 가능한 경우 partial 200 |
| GET `/snapshots/{snapshot_key}/claims/{claim_id}` | 선택 Snapshot의 Claim ID | Drawer용 ClaimVM. v1은 해당 Claim의 check/Observation 배열 전체를 반환하고 로그 본문은 별도 content 경로로 분리 |
| GET `/snapshots/{snapshot_key}/evidence/{evidence_key}` | opaque key | EvidenceVM. 소속되지 않은 key는404, 원본 존재 여부를 누설하지 않음 |
| GET 위 경로의 `/content` | field enum, opaque cursor | FieldVM. 구간당 최대64KiB. 파일 path나 임의 URL 입력 없음 |
| GET `/snapshots/{snapshot_key}/presentation` | key만 | Presentation, 생성 polling용. read-only |
| POST `/snapshots/{snapshot_key}/presentation/ensure` | recipe_hash와 view_intent | cache ready이면200, 생성 중/대기202, 실패 cooldown 중200 failed. 입력내용/prompt/raw/모델명을 client에서 받지 않음 |

filter는 `all / needs-review / blocked / stale / ready`, field는 `raw / stdout / stderr / diff / command`, view_intent는 `list_visible / detail`이다.

전송 envelope의 boolean/int/string/nullable은 §6.2를 따른다. 모든 ID는 원본 string이고 임의 숫자 변환을 하지 않는다. `scope`는 서버가 결정하며 클라이언트가 넘겨 덮어쓸 수 없다. content cursor는 snapshot_key/evidence_key/content hash/field/offset에 묶어 동일 원문 내에서만 유효하다. 원문 hash가 바뀌면 내용 반환 없이 corrupt 처리한다.

ensure는 검증 변경 API가 아니라 파생 표현의 유일한 생성 입구이며 최초 표시 때 UI가 자동 호출한다. 수동 생성/재실행 버튼은 없다. GET 응답 status를 확인해 ensure하고, hit에서는 POST도 하지 않는다. 중복 POST는 server의 single-flight로 처리한다.

공통 오류: 400 INVALID_QUERY, 401 UNAUTHENTICATED, 403 ORIGIN_DENIED, 404 NOT_FOUND, 409 SOURCE_CHANGED/LIST_CHANGED/RECIPE_CHANGED, 503 SOURCE_UNAVAILABLE/UNSUPPORTED_SCHEMA. 원본 journal 손상은503 SOURCE_INTEGRITY_ERROR. 원본이 없으면 목록200 빈 결과, 직접 key는404. 개별 raw 누락은 EvidenceVM의 availability로 표현한다. LLM 장애를 원본 API의503으로 처리하지 않는다.

### 6.4 raw·부분 손상

- 먼저 journal/record hash와 scope를 검증한다. 여기서 손상된 레코드의 제목이나 결과는 신뢰 가능한 정보처럼 표시하지 않는다.
- journal은 정상이지만 Evidence closure 일부가 읽히지 않으면 검증된 record metadata를 제한적으로 표시하는 reader 결과형을 사용한다. `get` 예외를 무시해 성공 처리하지 않는다. 손상된 연결을 명시하고 정상 연결의 검증도 계속한다.
- Evidence의 Task 소유권뿐 아니라 해당 Snapshot에서의 도달 가능성을 확인한다. 제외 diagnostic의 거부 ID는 정보이지 raw 열람 권한이 아니다.
- raw의 size/hash, purged, redaction_status를 확인한다. reference_only는 참조 정보만 제공하고 비밀정보 가림 해제 기능은 없다. 외부 URL 자동 fetch와 브라우저의 CAS path 노출은 금지한다.
- command/stdout 전용 field가 없으면 not_collected. raw에서 명령을 추측해 채우지 않는다. binary는 unsupported와 안전한 metadata만 제공한다. 64MiB 초과 raw는 v1 표시 범위 밖인 too_large로 표시하되 원본은 삭제하지 않는다. 그 이하는 전체 hash 검증 후64KiB 구간을 반환한다.
- raw/Spec/생성문은 모두 untrusted text다. HTML/script/terminal escape 실행, 링크 자동 방문은 없다. 기밀 발견 시 배포용 사본만 가리고 원본을 변경하지 않는다. redacted 라벨을 내용의 안전성 보장과 동일시하지 않는다.

## 7. Presentation Cache / ELI5 생성 계약

### 7.1 저장과 식별

cache는 원본 밖의 작은 SQLite 파일이다. 공통 원본 record 종류나 Event schema를 늘리지 않는다.

```text
recipe_hash = sha256(canonical({prompt_version:'dashboard-eli5-v1',
  schema_version:1, grounding_policy_version:1, locale:'ko-KR',
  provider_id, model_id, generation_parameters}))
cache_key = sha256(canonical({namespace,scope,snapshot_ref,recipe_hash}))
cache row = {cache_key UNIQUE, presentation_id, review_snapshot_id,
 snapshot_ref, fingerprint:snapshot_ref.hash, recipe_hash,
 structured_input_hash, status, attempt_count, lease_owner, lease_expires_at,
 generated_at, generator_model, ready_sequence, next_retry_at, error_code,
 icon, headline, summary, key_changes, attention_items, next_checks}
```

review_snapshot_id만으로 검색하지 않고 종류·revision·hash를 포함한다. 출력과 SourcePointer는 같은 Snapshot에만 결합한다. Claim state/count/verdict는 열이나 모델 출력에 넣지 않는다. recipe 변경은 새 key로 온디맨드 생성하고 옛 cache는 옛 recipe로 보존한다. 테마/화면 크기/일반 새로고침/context overlay는 key에 영향을 주지 않는다.

ready 결과의 본문은 같은 key에서 덮어쓰지 않는다. ready 전환 시 단조 증가 ready_sequence를 할당해 목록 검색의 cache 상한으로 사용한다. pending/failed 재시도 metadata만 갱신 가능하다. 가림 정책 변경은 recipe의 grounding_policy_version을 변경한다. 과거 recipe를 보존해도 더 이상 허용되지 않는 표현을 화면에 표시할 의무는 없다.

### 7.2 최초 표시·동시 실행·재시도

1. 원본과 cache GET을 먼저 반환한다. 읽을 원본이 없거나 read_health가 complete가 아니면 신규 생성하지 않는다. 기존 생성문도 원본 완전성을 확인할 때까지 표시하지 않고 fallback을 사용한다.
2. 목록은 **실제 viewport에 들어온 카드**만 ensure한다. 20개 전체나 검색 전체를 미리 생성하지 않는다. 최초 Detail은 해당 Snapshot만 생성한다.
3. 하나의 로컬 server worker에서 생성한다. 다른 key는 FIFO, 같은 key는 SQLite UNIQUE+lease로 합친다. 외부 모델 호출 중 DB transaction을 잡고 있지 않는다.
4. lease45초, provider timeout30초. key별 자동 시도는 최대2회. 최초 실패 후60초가 지나고 다음 실제 화면 표시/새로고침에서만 두 번째 시도를 허용한다. 자동 background retry는 없다. 2회 실패 후 동일 recipe는 failed를 유지한다. UI는 pending/failed뿐 아니라 next_retry_at을 읽고 재시도 가능 view에서만 ensure한다. 시계 역행은 조기 재시도를 허용하지 않으며, process 내부 timeout은 monotonic clock을 사용한다.
5. 프로세스 종료로 pending row가 남으면 lease 만료 후 다음 view에서 잔여 시도가 있을 때 재개한다. 중복 프로세스에서는 lease owner가 같은 결과만 저장한다. 충돌/종료 경계의 외부 과금까지 엄밀한 exactly-once를 보장하지 않는다. provider가 멱등키를 지원하면 cache_key와 시도 번호를 사용한다.
6. worker가 가져가기 전 pending은 미실행이므로 attempt_count를 늘리지 않는다. polling은 표시 중인 pending만1초→2초→5초, 이후5초 간격,60초에 중단한다. 숨긴 탭에서는 중단한다. 페이지 재표시 때 GET부터 재개한다.
7. model 미설정/credential 없음은 unavailable, 시도0, 원본 fallback이다. 정상 경로 수용에는 실제 model 성공 관찰이 필요하다. fallback만으로 ELI5 완료라 하지 않는다.

### 7.3 생성 입력과 비밀정보 경계

**승인된 backend 경계:** Dashboard Core는 provider SDK/모델별 응답 형식을 알지 않는다. `PresentationGenerator.generate(input, request_id, timeout_seconds)`는 provider 중립의 생성 결과 또는 분류된 오류를 반환한다. 캐시·재시도·grounding·fallback은 Core 책임이다. v1 구현 계획은 OpenAI-compatible HTTP adapter 하나를 기본안으로 사용한다. OpenAI 전용/Ollama 전용 adapter를 동시에 만들지 않으며, 이후 같은 경계로 교체 가능하다. 실제 endpoint/model/credential은 서버 설정이고, 프로토콜 세부사항과 smoke 검증은 WI-03에서 공식 문서와 대조한다. provider 실패는 기존 deterministic fallback으로 이어진다.

server가 인증된 provider/model 설정으로 연결한다. 외부 전송은 사용자가 해당 provider를 OwnHands 생성 대상으로 설정·허용한 경우에만 수행한다. 일반 조회 권한과 임의의 제3자 전송 허가를 혼동하지 않는다.

입력은 Snapshot closure의 WorkIssue, Spec, 전체 Claim/check, comparison, 실행 의미·결과, 변경 정보, 문제/제외, Review verdict다. 전체 Claim/check ID와 status를 유지한다. 구조화 정보의 이름·path·개인정보는 전송 전 필요한 부분을 가리고, 의미 없는 거대 metadata는 schema allowlist에 포함하지 않는다.

v1 입력 한도는 구조화 부분48KiB+선택 raw 합계8KiB다. 배열 끝의 Claim을 조용히 잘라내지 않는다. 중복 raw/ref는 합치고 긴 field는 출처를 붙인 발췌로 만든다. 그래도 전체 Claim/check의 핵심을 보존할 수 없으면 input_too_large로 fallback한다. 분모를 줄여 생성하지 않는다.

raw 추가는 기본0이다. 구조화 정보에 설명용 요약이 없는 `test_execution`/`workspace_diff` Evidence에 한해, 고정 extractor가 가림 처리된 오류 요약 또는 diff 헤더를 선택할 수 있다. 같은 closure의 text·redacted/not_needed·무결성 확인 부분만 합계8KiB까지 제공한다. 임의 파일/URL/외부 도구는 모델에 주지 않는다. reference_only/binary는 보내지 않는다. 입력의 지시문은 모두 인용 데이터다.

### 7.4 출력과 근거 연결

- icon은✨/🐛/🔒/⚡/🛡️/♻️/🎨/📋 중 선택한다. headline 최대60자, summary2~3문장·각120자 이내, key_changes0~4개, attention_items와 next_checks0~3개다. 각 항목에는 TextFact의 kind와1개 이상의 SourcePointer가 필요하다.
- intent는 Spec/WorkIssue와 연결해 '〜하기 위한 변경입니다', observed는 저장된 검증 결과와 연결해 '이 검증에서는〜을 확인했습니다'로 표현한다. gap은 실제 문제, inference는 원본에 명시된 추정에만 연결한다.
- '완전히 안전', '지금도 최신', '모두 해결', 'merge 가능'은 출처가 있더라도 Dashboard의 정형 성공 표현으로 허용하지 않는다. 관찰 범위를 한정한다.
- schema/문자 수/미정의 field/icon/포인터 도달 가능성/Claim 결과와 발화 종류의 정합성을 검사한다. failed/unobserved 참조를 성공 관찰로 쓰거나 없는 위험·다른 Snapshot 포인터를 쓰면 reject한다. 수치 집계나 verdict field도 reject한다.
- 정확한 포인터라도 의미의 반전을 기계적으로 완전히 탐지할 수는 없다. provider 출력을 fixture와 사람의 의미 검사로 별도 측정한다. 자동 checker를 새 Claim 판정기로 만들지 않는다.
- 부적합 출력은 생성 실패이며 재시도 상한에 포함한다. 수정용 LLM 반복 루프를 추가하지 않는다. 실패 fallback은 안전한 원본 제목·원본 집계 문장·problem의 결정적 설명으로 구성하고 생성문과 구분한다.
- 동적 freshness 설명을 출력에 영구 저장하지 않는다. cache 저장 전에 snapshot_ref/input hash를 다시 확인해 지연 응답의 다른 key 저장을 막는다.

### 7.5 Skill 정합성 수정 대상

`skills/dashboard/SKILL.md`와 `skills/using-ownhands/SKILL.md`의 presentation 항목을 다음에 맞춘다. 사용자 명시 요청 또는 실제 Dashboard 최초 view intent로 누락된 presentation을 준비할 수 있다. Review 완료만으로는 실행하지 않는다. cache hit/GET/Drawer에서는 Skill을 실행하지 않는다. worker는 고정 생성 계약을 직접 실행하고 UI 조작마다 Router/Skill 선택을 LLM으로 다시 수행하지 않는다. Skill은 대화 경로에서 같은 계약을 안내한다.

기존 Spec/Review/CodeState key는 이전 presentation 형식으로 식별하고 새 Snapshot cache로 암묵 이전하지 않는다. 적합한 원본 Ref와 recipe를 확인할 수 없는 옛 표현은 재사용하지 않고 최초 표시에서 새로 생성한다.

## 8. 시각·접근성 상세 기준

Warm Paper Neutral 배경과 Ledger Indigo 제목/링크를 기본으로 카드 경계와 여백으로 계층을 만든다. 빨강/초록만으로 상태를 표현하지 않는다. 기술 용어는 상세 Evidence에서 필요한 만큼 남기고, 일반 UI는 한국어·영어 영역명은 보조 표기로 사용한다.

375×812,768×1024,1440×900 및200% zoom에서 확인한다. 최상단에서 요약/상태에 도달하고 가로 스크롤은 raw/diff 코드 영역에만 한정한다. 본문4.5:1, 주요 UI 경계3:1 이상을 검사한다. 모든 탐색은 키보드로 가능해야 하며 Drawer에 dialog 이름/focus 관리, 상태에 읽기용 텍스트를 둔다. 갱신 알림은 비방해 live region을 사용하고 생성 중 focus를 빼앗지 않는다. 복잡한 관계에만 그림을 쓰고 동등한 텍스트를 제공한다.

## 9. 테스트 매트릭스와 Evidence

모든 T는 **미실행 수용 계획**이다. 기존433 tests/9 mutations는 기반의 과거 검증이지 Dashboard 완료 증거가 아니다.

| Test | fixture/조작 | 기대 관찰 | R | E |
|---|---|---|---|---|
| T01 | 전체GET/ensure/hit/failure/raw를 ro 원본과 write-deny spy로 실행; DB 없음; orphan CAS 존재 | 원본 생성/쓰기/chmod/reconcile/이벤트/실행0, orphan 유지, cache만 변경 | R01 | E01 |
| T02 | 2issues×2attempts×여러revision, 중복 상태, cursor 중 원본 변경, 미생성 요약 검색 | 정해진rank/분모/개수, 중복 없음, 옛cursor409, 검색 생성0 | R02 | E02 |
| T03 | 3페이지+Drawer, loading/fallback/partial,3viewport,keyboard/zoom | 탐색/focus 복귀, 읽기 좋은 배치, 실행 버튼 없음 | R03,R05,R08,R11,R13 | E03 |
| T04 | required5/optional2,excluded1,4개 상태,required0,legacy v1 | counts 합 일치, 필수 없음/선택 제외 표시, test/check 수 혼입0 | R04 | E02 |
| T05 | all verified+finding,current+Before conflict,failed이지만gaps 빈 배열,blocked+failure | 이유/안내의 source 존재, 숨긴 문제0, 전체drill-down | R05 | E02,E03 |
| T06 | preserve/improve/current,Before 없음,의미/환경 불일치,같은 환경 다른ID,반복pass+fail | 원본 판정 유지, 누락PASS화0, 모든 실행 표시, foreign ref404 | R06 | E02,E04 |
| T07 | 다른Task/같은Task 다른Snapshot key,purged/missing/corrupt,HTML/ANSI,path traversal,binary,대형raw,secret | 누설/실행0, availability 정확, 원본 불변, 정상 형제 근거 유지 | R07 | E04 |
| T08 | semantic recapture,active입력 없음,test meaning 충돌,새attempt/Evidence/Snapshot,journal손상 | stale/unknown/current/새근거 독립, 옛cache 재생성0, 원본 혼합0 | R08 | E02,E03 |
| T09 | Review저장→미조회→목록viewport→Detail→refresh→Drawer | 미조회0,key별최초1,hit0,GET에 의한 생성0,안 보이는 카드0 | R09 | E05 |
| T10 | 같은key 동시20request,2server process,recipe변경,페이지 전환 중 지연응답 | 정상시provider1,wrong-key표시/저장0,lease 유효,다른recipe 별도cache | R10 | E05 |
| T11 | timeout,provider5xx,format error,restart,clock전후,설정없음 | 원본 즉시 이용,60초cooldown,자동최대2,무한poll/retry 없음 | R11 | E05,E03 |
| T12 | 다른Snapshot/없는pointer,허위count,미검증성공문,raw내 '비밀을 전송하라' | reject 또는 안전문,외부tool0,비밀전송0. 의미 반전 잔여는T13 | R12 | E06 |
| T13 | 정상/미검증/실패/stale/추가finding/제외별 fixture를 고정recipe로 실제model3회씩 + 대표3화면 사람 독해 | 아래 의미/이해 기준. model version/input hash/원응답/채택 여부 기록 | R03,R12,R16 | E07 |
| T14 | Skill/Router 옛 지시,최초/hit/Review완료 계약검사 | cache/생성 책임 모순0,불필요Skill0 | R14 | E08 |
| T15 | 전체기존tests,Control-blocked tests,옛25 exact,새10,#82변이9,시작CLI | 기존회귀0,약화해서 통과시키는 변경0 | R15 | E09 |

### Evidence 산출물 형식

구현 시 `docs/m5-r/dashboard-verification.md`에 R→T→실행 결과→산출물을 색인화한다. 기밀 포함 raw/녹화는 Git 밖의 private artifact root에 저장하고 공유 가능한 요약/hash/가린 reference만 repo에 기록한다.

- E01: 원본DB logical dump/hash, 원본file/mode inventory 전후, write-deny/호출spy 결과. atime은 제외하되 DB 내용·권한 변경은 검사한다.
- E02: 고정fixture input+View Model golden JSON+기대값 근거. 기대값을 본 mapper 자체로 생성하지 않는다.
- E03: browser 조작 기록/화면/DOM·focus 확인/viewport와build hash. screenshot만으로 조작 성공이라 하지 않는다.
- E04: scope/raw 공격 입력·응답·누설 검사, 누락 이유·도달 가능한 근거 목록.
- E05: mock provider 호출ledger, fake clock/병렬/restart 결과, cache row 전이. 실제 과금 없이 제어 검증 가능.
- E06: 악의적/부적합 출력fixture와reject 이유, 전송 전payload 가림 검사. 실제 비밀은fixture에 쓰지 않는다.
- E07: 실제model/recipe/input hash/생성문과 사람 채점. 계약 테스트와 별도 관찰 증거.
- E08: Skill/Router 변경 차이, old/new 대응표와 계약 테스트 결과.
- E09: 실행명령/commit/Python version/결과/미실행 목록. M3 live 미확인은 계속 별도 기록.

### 의미 품질과 사용자 이해 수용 기준

의미 검사: 6유형×3생성=18출력에서 출처 없는 성공 단정, failed→성공, 미관측→확인됨, 다른Snapshot 혼합, 근거 없는 위험 추가는 **0건**이어야 한다. 위반은 품질 불합격이며 재생성해 편리한 출력만 채택하지 않는다. 모든 출력과reject를 남긴다. 실제model 검사 미실행이면 생성 제어PASS와 별도로 `semantic_quality=unverified`다.

이해 검사: 사용자 본인이 정상/미검증/과거결과의3시나리오를 설명 없이 최초Detail 화면에서 각60초 안에 확인한다. '무슨 작업', '무엇이 바뀜', '검증 상태', '미확인은 무엇', '다음에 볼 것(없으면 없음)'의5문항에 원본과 모순 없이 답하는 것이 목표다. 시나리오별5/5와 관찰 시간/답변을 기록한다. 해당 사용자 pilot이지 일반 사용자 전체의 사용성 증명은 아니다. 미관찰은 미검증이며 이미지/자동tests로 대체하지 않는다.

## 10. 구현 Work Item 분해 — 승인 후

아래는 실행 코드를 포함하지 않는 Work Item 명세다. 구체적인 구현 절차·테스트 코드를 가진 실행 계획은 본Spec 검토 후 각WI에서 만든다. 파일명은 신규 제안이며 존재를 주장하지 않는다. Python core의stdlib-only와3.12 이상 기준을 유지한다. Dashboard 프론트는 v1에서 HTML/CSS/JavaScript module의 얇은 동일origin 화면을 기본으로 하고 새bundler/framework를 전제하지 않는다.

| WI | 산출물과 의존성 | 주요 변경 후보 | 필수 검증/완료 조건 |
|---|---|---|---|
| WI-01 읽기 전용 기반 | 원본을 바꾸지 않는Catalog/Lifecycle/Evidence reader, typed partial진단. 선행 없음 | 기존 `catalog.py`, `evidence.py`, `lifecycle/store.py`의ro경로; `tests/test_dashboard_readonly.py` | T01,T07,T15. 기존writer 동작 유지,초기화/reconcile 회피,공통validator 재사용 |
| WI-02 Snapshot View Model | 목록선택,counts,problem index,context overlay,scoped Evidence. WI-01 | 신규 `src/devharness/dashboard/read_model.py`; `tests/test_dashboard_read_model.py` | T02,T04,T05,T06,T08. pure mapping golden fixture 검증,새Claim평가0 |
| WI-03 Presentation 생성·캐시 | recipe/grounding/lease/retry/전송허용/fallback. WI-01,02 | 신규 `dashboard/presentation.py`, `dashboard/generator.py`; `tests/test_dashboard_presentation.py`; 2개Skill과routing검사 | T09~T14 생성관련. mock합격과실model E07 별도,cache API는read/ensure |
| WI-04 HTTP 제공과 경계 | §6 endpoints,session/Origin,raw제공,기존data root로시작. WI-01~03 | 신규 `dashboard/server.py`; 기존 `__main__.py`의dashboard시작명령; `tests/test_dashboard_api.py` | T01,T06,T07,T09~11,T15. GET부작용0,원본/cache분리,MCP registry유지 |
| WI-05 3페이지+Drawer | List/Detail/상세Evidence,단계적공개,viewport생성,접근성. WI-02계약으로fixture선행가능,결합은WI-04후 | 신규 `dashboard/web/index.html`, `app.js`, `styles.css`; browser검증시나리오 | T02~T11 UI부분,T13. 프론트lifecycle SQL/평가기 없음,실행/판단UI없음 |
| WI-06 통합·수용 근거 | 전체R 추적,실model/pilot,전환문서. WI-01~05 | `docs/m5-r/dashboard-verification.md`, 시작/제한문서,통합tests | T01~15 실측. 미실행 기록,R12/R16 미관찰이면제품완료아님 |

인터페이스 소유: WI-01은 `ReadonlySources`의open/검증record/closure/metadata/content 결과, WI-02는 `read_list/read_detail/read_claim/read_evidence/read_context`와§6 VM, WI-03은 `read_presentation/ensure_presentation`, WI-04는transport/인증, WI-05는VM 렌더링만 담당한다. 내부signature는 실행 계획에서 고정하고 VM/HTTP 변경은 본Spec revision을 동반한다. WI-03의 기존 라우팅 회귀 대상은 `tests/test_skill_routing_fixtures.py`, `tests/test_skill_discovery_contract.py`, `tests/test_skills.py`다. 표의 `dashboard/` 신규 경로는 모두 `src/devharness/dashboard/` 아래다.

권장 순서: WI-01 → WI-02 → WI-03 → WI-04 → WI-05 → WI-06. WI-05의fixture 화면설계는WI-02 후 독립 검토할 수 있다. 각WI는 '실패fixture 먼저 확인 → 최소구현 → 대상테스트 → 기존회귀 → 독립검토 → 작은PR' 단위로 진행한다. TDD는 계약/분기, 브라우저 관찰과 실제model 검사는 의미/조작 품질을 맡는다.

## 11. #89 상세 Spec 검토 완료 조건

- [ ] 사람이 R01~R16,D1~D5,상태표,API,cache,T/E와WI의 대응을 검토했다.
- [ ] 상세 결정을 문서로 수용했다: 등록입력기준freshness,viewport생성범위,2회retry상한,ro/partial reader,18개생성의미검사,3시나리오pilot.
- [ ] 원본에 없는 정보 발명 금지,all verified여도 이유 보존,생성cache와검증쓰기 분리를 확인했다.
- [ ] 필요한 구현Work Item과 의존성을 채택했다. 아직 만들지 않은GitHub issue번호를 가정하지 않는다.

구현 착수는 위 상세 Spec 검토와 별도 승인이다. 별도 승인 전 제품코드/Skill 변경을 수행하지 않는다. 문서 PR·#89 close·후속 이슈 생성 역시 이번 작성 요청에는 포함하지 않는다.

문서 검사는 구조/추적/모순의 자체 검토까지다. API구현·브라우저·LLM의미품질·사용자이해는 모두 미실행이다. M3 live는 기존AGENTS.md fixture drift로 미확인인 상태이며, 이Spec을 해소 근거로 사용하지 않는다.

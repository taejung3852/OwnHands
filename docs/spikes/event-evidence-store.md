# M0-06 — Event & Evidence Store 결정 Spike

**상태:** ADR 제안 근거. M1 저장소 구현은 포함하지 않는다.

**확인일:** 2026-09-04 · macOS 26.6.2 · SQLite 3.51.0

**Raw Evidence 정책:** Probe는 합성 데이터만 사용하며 임시 디렉터리에서 실행하고 종료 시 삭제한다.

## 결론

M1의 저장 구조로 **SQLite catalog + content-addressed raw evidence files**의 hybrid 방식을 제안한다.

- Canonical Event source는 한 SQLite database의 append-only `events` table이다.
- 작고 구조화된 Event payload와 Evidence metadata는 같은 database에 둔다.
- 원문 diff, log, screenshot처럼 크거나 민감할 수 있는 Raw Evidence는 SHA-256 content hash로 주소화한 로컬 file object로 두고 catalog에서 참조한다.
- Dashboard Projection은 canonical table과 분리된 폐기 가능한 파생 table이다. Event sequence를 처음부터 replay해 재구성할 수 있어야 한다.
- 초기 journal mode는 `DELETE`와 `synchronous=FULL`을 사용한다. 이 호스트의 SQLite 3.51.0은 공식 문서의 WAL-reset bug 영향 범위에 있으므로 WAL은 3.51.3 이상 또는 수정 backport 확인 전 활성화하지 않는다.

이 선택은 제품 문서의 “Event Log가 원본”, “Raw Evidence는 로컬”, “Task·Worktree별 분리”, “Projection 재생성 가능”을 가장 적은 별도 동시성·복구 코드로 만족한다.

## 기준선 요구사항

| 요구 | 저장 계약 |
|---|---|
| append-only canonical event | transaction으로 event row를 동기 기록하고 stable `event_id`를 unique key로 사용 |
| Evidence 추적성 | Event에서 content hash 또는 Evidence metadata ID를 참조 |
| Task·Worktree 분리 | 모든 Event에 `project_id`, `worktree_id`, `task_id`를 필수 기록 |
| Projection freshness | canonical `max(sequence)`와 projection의 `last_sequence` 비교 |
| Projection rebuild | 파생 table을 버리고 canonical Event 전체 replay 가능 |
| Raw local only | OS user-data 아래 저장하고 Git worktree에는 pointer/override만 허용 |
| 선택적 공유 | 원본 경로가 아닌 사용자가 선택한 마스킹 report만 별도 생성 |
| 삭제 범위 명확화 | Task 논리 삭제, Raw object 보존·삭제, 공유 report 삭제를 별도 동작으로 표현 |

## 대안 비교

| 대안 | 장점 | 확인된 부담 | 판단 |
|---|---|---|---|
| JSONL only | 사람이 직접 읽기 쉽고 append 개념이 단순함 | partial tail 복구, 다중 writer lock, duplicate 방지, index/query, object lifecycle을 별도 구현해야 함 | 기각. export/debug 형식으로만 허용 |
| SQLite only, Raw blob 포함 | transaction과 query가 한 파일에 모임 | 큰 Raw Evidence가 database backup·retention·redaction·삭제 단위를 결합하고 DB 팽창을 유발 | 기각 |
| SQLite catalog + file objects | transaction, unique key, sequence, query를 SQLite가 담당하고 큰 Raw Evidence lifecycle은 hash object로 분리 | database와 object file 사이 orphan/reconciliation 절차 필요 | **채택 제안** |
| 개별 Event file + index | object 단위 원자적 rename과 분산 저장이 쉬움 | 순서·중복·query·index recovery가 별도 시스템이 됨 | 현재 개인용 로컬 제품에는 과함 |

JSONL은 선택적 export 대상이지 canonical source가 아니다. 사람이 읽을 수 있어야 한다는 요구는 read-only export/probe 도구로 충족하고, 원본 무결성 계약과 혼합하지 않는다.

## 데이터 경계

### SQLite catalog

M1에서 최소한 다음 논리 record를 둔다.

- `events`: immutable sequence, stable event ID, schema version, type, scope IDs, timestamp, JSON payload, Evidence reference
- `evidence_objects`: hash, byte count, media type, collection method, redaction status, freshness, conflict reference, local relative path
- `projection_state`: projection name, schema version, last applied Event sequence, last success/failure
- 파생 projection tables: Task status, claim result, Dashboard summary 등

Append-only는 “table 이름”이 아니라 쓰기 계약이다. M1에서는 update/delete 권한을 일반 write path에 주지 않고, 수정은 correction/superseding Event로 표현하며, migration과 retention은 별도 관리 경로로 제한해야 한다.

### Raw Evidence object

권장 상대 경로는 `objects/sha256/<첫 2자>/<나머지 hash>`다. 쓰기는 다음 순서를 사용한다.

1. 같은 filesystem의 임시 파일에 수집하고 민감정보 최소화·hash·크기를 계산한다.
2. `fsync` 후 content-addressed 최종 경로로 atomic rename한다.
3. SQLite transaction에서 Evidence metadata와 참조 Event를 함께 commit한다.
4. commit 전 실패한 file은 orphan sweeper가 grace period 뒤 제거한다. DB가 참조하는 object는 hash 검증 없이 삭제하지 않는다.

Database transaction과 filesystem rename은 하나의 원자 transaction이 아니므로 orphan 가능성은 남는다. 반대 순서로 DB가 존재하지 않는 file을 가리키는 것보다, file-first 후 reconciliation을 선택한다.

## 위치와 분리

macOS에서는 Foundation이 반환하는 user Application Support directory 아래 앱 전용 subdirectory를 사용한다. 경로 문자열을 코드에 고정하지 않는다. 비-sandbox 실행의 개념 예시는 다음과 같다.

```text
~/Library/Application Support/DevHarness/
├─ catalog.sqlite3
├─ projects/<project-id>/
│  ├─ worktrees/<worktree-id>/tasks/<task-id>/reports/
│  └─ local-overrides/
└─ objects/sha256/<prefix>/<digest>
```

Raw object는 hash로 전역 중복 제거할 수 있지만, 접근·retention·삭제 판정은 object를 참조하는 project/worktree/task association별로 수행한다. 프로젝트의 `.dev-harness/`는 Git Ignore된 local pointer와 override만 둘 수 있다.

Apple은 macOS의 app-managed data에 Application Support의 앱 전용 directory를 사용하고 API로 위치를 조회하도록 안내한다 ([URL.applicationSupportDirectory](https://developer.apple.com/documentation/foundation/url/applicationsupportdirectory), [File System Programming Guide](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/AccessingFilesandDirectories/AccessingFilesandDirectories.html)).

## 무결성·복구 계약

- **partial write:** 한 Event와 그 metadata를 SQLite transaction 하나로 commit한다. commit되지 않은 row는 canonical Event가 아니다.
- **duplicate delivery:** adapter가 stable `event_id`를 제공한다. 동일 ID 재전송은 no-op이며 payload/hash 충돌이면 별도 conflict Event를 남긴다.
- **ordering:** SQLite `sequence`는 DevHarness 수집 순서다. upstream timestamp나 upstream sequence와 동일하다고 주장하지 않는다.
- **versioning:** 각 Event에 `event_version`, database에 schema/migration version을 둔다. 알 수 없는 version은 조용히 건너뛰지 않고 projection을 중단·표시한다.
- **rebuild:** projection table을 삭제하고 Event sequence 순으로 replay한다. 완료 시 `last_sequence == event_head`일 때만 projection freshness를 `Observed`로 판단한다.
- **corruption check:** 시작/maintenance 시 SQLite integrity check와 object hash sampling을 수행한다. 통과는 검사 범위의 무결성만 뜻한다.

SQLite는 transaction이 program/OS/power interruption에도 전부 반영되거나 전혀 반영되지 않는 ACID 성질을 제공한다고 명시한다 ([SQLite transactions](https://www.sqlite.org/transactional.html), [atomic commit](https://www.sqlite.org/atomiccommit.html)).

## Journal mode 결정

현재는 rollback journal을 사용한다.

- SQLite의 기본 atomic commit 방식은 rollback journal이다.
- WAL은 reader/writer 동시성에 유리하지만 동일 host가 필요하고 `-wal`·`-shm` file과 checkpoint 운영이 추가된다.
- SQLite 공식 문서는 3.7.0–3.51.2 WAL에서 드문 corruption race가 가능하며 3.51.3 이상에서 수정됐다고 기록한다. 현재 Probe version은 3.51.0이다.

따라서 M1은 정확성 우선의 single-writer queue + rollback journal로 시작한다. WAL은 실제 read/write 부하가 병목임을 측정하고 안전한 SQLite version을 확인한 뒤 별도 ADR amendment로 검토한다 ([SQLite WAL](https://www.sqlite.org/wal.html)).

## Redaction·보존·삭제 경계

| 동작 | 기본 의미 | 자동으로 하지 않는 것 |
|---|---|---|
| Task 삭제 | Task를 UI/일반 조회에서 제거하고 tombstone Event 기록 | Raw Evidence 즉시 파기 |
| Evidence purge | 참조 association과 retention 조건을 확인한 뒤 object 제거 | 다른 Task가 참조하는 동일 hash 제거 |
| Report 삭제 | 선택 생성한 마스킹 report 제거 | canonical Event 또는 Raw Evidence 제거 |
| Project 제거 | project association 제거 및 영향 preview | 공유 object·다른 Worktree Evidence 일괄 제거 |

수집 단계에서 비밀정보 원문을 가능한 한 저장하지 않는 것이 1차 정책이다. 마스킹은 Raw를 안전하게 만든다는 보장이 아니며, 공유 report 생성은 명시적인 사용자 선택과 preview를 요구한다. Encryption-at-rest와 retention 기본 기간은 제품 문서만으로 확정되지 않아 M1 이전 Open Decision으로 남긴다.

## 재현 가능한 합성 Probe

실행:

```bash
docs/spikes/probes/m0-06-store-probe.sh
```

2026-09-04 관찰 결과:

```text
sqlite_version=3.51.0
journal_mode=delete
partial_write_rollback=passed
forced_interruption_recovery=passed
duplicate_event_idempotency=passed
evidence_content_hash=passed
projection_rebuild=passed
unknown_event_version_fails_freshness=passed
redaction_metadata=passed
raw_evidence_git_exclusion=passed
integrity_check=ok
```

Probe가 확인한 범위는 합성 row, 강제 종료된 단일 writer process, 로컬 APFS의 SQLite rollback journal과 hash object다. 강제 종료 뒤 미commit row가 보이지 않고 다음 read에서 database가 정상 사용되는 것을 확인했다. 지원하지 않는 Event version을 탐지해 Projection freshness가 성립하지 않는 것과 합성 Evidence의 redaction metadata 보존도 확인했다. 실제 power-loss, disk-full, concurrent writer, 대형 blob, 실제 민감정보 redaction, retention race, encryption은 **Unobserved**다.

## 남은 위험과 M1 Gate

1. SQLite와 object file 사이 orphan reconciliation 및 disk-full fault injection을 구현·검증해야 한다.
2. single-writer lock/queue의 process crash와 재시작 동작을 검증해야 한다.
3. retention 기간, encryption-at-rest, 사용자 delete UX는 별도 사용자 결정이 필요하다.
4. upstream Event ID가 없을 때의 deterministic ID 규칙은 adapter별로 정의해야 한다.
5. backup/restore는 database와 참조 object의 일관된 snapshot을 대상으로 별도 검증해야 한다.

## ADR 반영 조건

- Hybrid 구조와 rollback journal 기본값을 M0 ADR로 검토한다.
- M1 구현 전 retention/encryption Open Decision을 사용자에게 제출한다.
- M1 완료 주장은 위 합성 Probe만으로 하지 않고 crash/disk-full/concurrency 및 orphan recovery Evidence를 추가한다.

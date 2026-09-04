# ADR-0004 — Event & Evidence Store

- **상태:** Proposed — 사용자 검토 대기
- **일자:** 2026-09-04
- **관련 Issue:** [M0-06](https://github.com/taejung3852/devharness/issues/6)

## Context

DevHarness는 Event를 append-only 원본으로 기록하고, Raw Evidence를 로컬에 유지하며, Dashboard Projection을 원본 Event에서 재생성해야 한다. 저장소는 partial write, duplicate delivery, schema version, Task·Worktree 분리, retention·redaction 경계를 지원해야 한다.

## Decision

1. Canonical Event와 Evidence metadata는 하나의 **SQLite catalog**에 저장한다.
2. 큰 Raw Evidence는 **SHA-256 content-addressed local file object**로 저장하고 catalog에서 참조한다.
3. Projection은 canonical Event가 아닌 파생 table이며 언제든 삭제·replay할 수 있다.
4. 초기 SQLite 설정은 **rollback journal (`DELETE`) + `synchronous=FULL` + single-writer**다.
5. macOS 저장 root는 Foundation이 반환하는 user Application Support 아래 DevHarness 전용 directory다. project/worktree/task association을 명시적으로 기록한다.
6. 프로젝트 내부에는 Git Ignore된 pointer/local override만 허용하고 Raw Evidence를 저장하지 않는다.
7. Event 수정·삭제 대신 correction, superseding, tombstone Event를 사용한다. 실제 purge는 별도 관리 동작과 Evidence를 요구한다.

## Alternatives

- **JSONL only:** tail 손상, locking, 중복, indexing을 직접 해결해야 해 기각한다. 선택적 export에는 사용할 수 있다.
- **SQLite blob only:** 큰 원문의 보존·삭제·backup 경계를 catalog와 결합하므로 기각한다.
- **개별 Event file + index:** 현재 로컬 개인용 범위에는 운영 복잡성이 과해 기각한다.
- **WAL 즉시 사용:** 현재 설치된 SQLite 3.51.0이 공식 WAL-reset bug 영향 범위이고, 아직 동시성 병목 Evidence가 없어 보류한다.

## Consequences

- transaction, unique Event ID, sequence, query, projection freshness를 한 저장 엔진으로 다룰 수 있다.
- Raw Evidence를 database 크기와 분리하고 hash 검증·중복 제거할 수 있다.
- database transaction과 filesystem rename 사이 orphan가 가능하므로 file-first write, grace period, reconciliation이 필요하다.
- rollback journal은 WAL보다 read/write 동시성이 낮다. 실제 부하 Evidence와 수정된 SQLite version이 확보되면 amendment로 재검토한다.

## Evidence

- [M0-06 Spike](../spikes/event-evidence-store.md)
- [재현 Probe](../spikes/probes/m0-06-store-probe.sh): uncommitted row rollback, duplicate no-op, object hash, projection rebuild, Git 제외, integrity check를 합성 fixture로 확인했다.
- SQLite는 transaction의 atomicity/durability를 문서화한다 ([transactions](https://www.sqlite.org/transactional.html)). WAL 제약과 version별 결함은 공식 WAL 문서에서 확인했다 ([WAL](https://www.sqlite.org/wal.html)).
- macOS app data root는 Apple의 Application Support API 지침을 따른다 ([Apple](https://developer.apple.com/documentation/foundation/url/applicationsupportdirectory)).

## Not decided here

- retention 기본 기간
- encryption-at-rest 적용과 key 관리
- 사용자 delete/restore UX
- WAL 전환 조건의 성능 threshold

이 ADR은 사용자 승인 전까지 `Proposed`이며 M1 구현을 허가하지 않는다.

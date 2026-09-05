# ADR-0008 — M1 Local Core Runtime

- **상태:** Accepted — M1 구현 기준선
- **일자:** 2026-09-04
- **관련 Issue:** [M1-01](https://github.com/taejung3852/devharness/issues/10)

## Context

M1은 SQLite transaction, SHA-256 object, 운영체제 data path, 파일 권한과 재현 가능한 테스트가 필요하다. 현재 개발 환경에는 Python 3.12.14와 Node 26.7.0이 있다. Node의 내장 `node:sqlite`는 외부 native dependency를 없애지만 Node 26 문서에서도 Stability 1.2 release candidate다. M1 Core의 첫 저장 계약을 release-candidate API에 직접 묶을 근거는 없다.

## Decision

M1–M4 Local Core는 Python 3.12 이상과 표준 라이브러리만 사용한다.

SQLite catalog schema는 명시적으로 versioning한다. schema v2는 Projection integrity hash와 Evidence lineage를 추가하지만, hash가 없던 v1 Projection은 무결성을 증명할 수 없으므로 migration transaction에서 폐기하고 canonical Event replay를 요구한다. schema v3 Event fingerprint는 sequence를 포함한다. sequence가 없던 v1/v2 Event fingerprint는 Task별 Event가 없거나 정확히 하나이고 그 Event가 Task mode와 일치하는 `task.created` version 1, `sequence=1`이며 legacy fingerprint도 검증될 때만 v3로 이행한다. 한 Task에 legacy Event가 둘 이상이면 외부 순서 anchor 없이 원래 순서를 증명할 수 없으므로 자동 migration을 거부한다. 기존 database는 어떤 DDL보다 먼저 schema version row와 지원 version allowlist를 검사하며, version row가 없거나 알 수 없는 version이면 원본 `sqlite_schema`와 row를 바꾸지 않고 거부한다. 기존 schema v3는 같은 시점에 핵심 table, column signature, index와 trigger 정의의 exact contract를 검사하며, 누락·추가·변형을 `CREATE IF NOT EXISTS`로 복구하지 않고 거부한다. v1 catalog의 공통 schema bootstrap, Evidence lineage와 fingerprint 변환, Projection 폐기, v3 Event migration은 하나의 `BEGIN IMMEDIATE` transaction에서 처리하므로 어느 검증이 실패해도 schema version 1과 전체 schema/row가 원상태로 유지된다. 완전히 빈 database만 새 schema v3로 bootstrap한다.

새 Task의 첫 Event는 반드시 `task.created`여야 하며 sequence 1에서 한 번만 허용하고 payload mode가 immutable Task snapshot의 mode와 일치해야 한다. 이 불변식은 append와 read/replay 양쪽에서 검사한다. Projection replay와 freshness는 Evidence 및 Control reference의 존재와 Task binding, Evidence purge의 recorded→purged 전이를 검증한다. 저장 Projection의 검증된 `projected_sequence`를 monotonic checkpoint로 취급하며 현재 Event head가 그보다 작으면 rebuild는 Projection을 삭제하거나 축소하지 않고 self-consistent `failed` 상태로 전환한다.

- `sqlite3`: catalog와 명시적 transaction
- `pathlib`, `os`: 운영체제 data path와 파일 권한
- `hashlib`: SHA-256 content address
- `json`, `dataclasses`: versioned record
- `unittest`: 자동 테스트

Runtime dependency는 0개로 유지한다. 초기 database 설정은 ADR-0004대로 rollback journal `DELETE`, `synchronous=FULL`, single writer다. Python 환경 재현에는 로컬 `uv`를 사용하지만 제품 runtime dependency로 포함하지 않는다.

## Alternatives

- **Node `node:sqlite`:** 현재 Probe는 동작했지만 API가 release candidate라 기각했다. M7 packaging에서 안정 상태가 바뀌면 재검토할 수 있다.
- **외부 SQLite binding:** M1에 native build와 공급망 dependency를 추가할 필요가 없어 보류한다.
- **Python 3.9 시스템 runtime:** 현재 macOS system Python은 3.9.6이며 지원이 끝났으므로 기준선으로 삼지 않는다.
- **Rust Core:** 강한 타입과 배포 장점이 있지만 M1–M4의 작은 로컬 도구 범위에 초기 복잡성이 크다.

## Consequences

- SQLite와 테스트 API는 Python 표준 라이브러리의 안정 계약을 따른다.
- M3 App Server는 JSON-RPC stdio adapter로 분리해 Core 언어 선택과 Codex client ownership을 섞지 않는다.
- M5 UI는 저장 schema를 읽는 별도 adapter 위에서 구현하며 Python 렌더링을 Production UI 계약으로 고정하지 않는다.
- 실행 가능한 Python packaging과 설치 UX는 M7까지 미결정이다.
- 애플리케이션 자체 암호화는 제공하거나 보장하지 않는다.
- Projection checkpoint가 생성되기 전에 일어난 Event tail 삭제는 외부 monotonic anchor 없이 탐지할 수 없다. 또한 DB와 별도 anchor를 함께 변조할 권한을 가진 공격자는 비밀키 서명이나 원격 신뢰 저장소가 없으면 이 계층에서 방어할 수 없다.

## Evidence

- Python 3.12.14 `sqlite3` in-memory/file Probe와 SQLite 3.51.0 M0 저장 Probe
- Python 공식 [`sqlite3` transaction control](https://docs.python.org/3.12/library/sqlite3.html#transaction-control)
- Python 공식 [`unittest`](https://docs.python.org/3.12/library/unittest.html)
- Node 공식 [`node:sqlite`](https://nodejs.org/api/sqlite.html)의 Stability 1.2 표기
- Python 공식 [version status](https://devguide.python.org/versions/)의 3.12 security support 범위

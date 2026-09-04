# ADR-0008 — M1 Local Core Runtime

- **상태:** Accepted — M1 구현 기준선
- **일자:** 2026-09-04
- **관련 Issue:** [M1-01](https://github.com/taejung3852/devharness/issues/10)

## Context

M1은 SQLite transaction, SHA-256 object, 운영체제 data path, 파일 권한과 재현 가능한 테스트가 필요하다. 현재 개발 환경에는 Python 3.12.14와 Node 26.7.0이 있다. Node의 내장 `node:sqlite`는 외부 native dependency를 없애지만 Node 26 문서에서도 Stability 1.2 release candidate다. M1 Core의 첫 저장 계약을 release-candidate API에 직접 묶을 근거는 없다.

## Decision

M1–M4 Local Core는 Python 3.12 이상과 표준 라이브러리만 사용한다.

SQLite catalog schema는 명시적으로 versioning한다. M1 독립 리뷰에서 Projection integrity hash가 추가되어 schema v2가 되었으며, v1 catalog는 저장된 Projection JSON의 SHA-256을 계산하는 rollback-journal transaction으로 v2에 migration한다. 알 수 없는 schema version은 열지 않는다.

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

## Evidence

- Python 3.12.14 `sqlite3` in-memory/file Probe와 SQLite 3.51.0 M0 저장 Probe
- Python 공식 [`sqlite3` transaction control](https://docs.python.org/3.12/library/sqlite3.html#transaction-control)
- Python 공식 [`unittest`](https://docs.python.org/3.12/library/unittest.html)
- Node 공식 [`node:sqlite`](https://nodejs.org/api/sqlite.html)의 Stability 1.2 표기
- Python 공식 [version status](https://devguide.python.org/versions/)의 3.12 security support 범위

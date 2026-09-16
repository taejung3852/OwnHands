# #79 책임표 검증 기록

- 일자: 2026-09-09
- 대상: `core-responsibility-map.md`, `core-responsibility-inventory.md`, `core-responsibility-inventory.csv`
- 원본 기준: `598f651614df36afc3d3d303d3aaeaff596ee6b2`
- 범위: 문서·책임 분류의 정적 검증. 새 제품 동작/성능/실사용 검증이 아니다.

## 대조 결과

| 확인 | 결과 | 방법 |
|---|---|---|
| 전체 추적 파일 분모 | 206 | 기준 commit `git ls-tree -r --name-only -z` |
| CSV 파일별 분류 | 206행, 누락 0, 중복 0 | 기준 tree와 CSV path 집합의 정확한 일치 |
| 사람이 읽는 책임표 | 206행 | Markdown 행 수와 CSV의 분류/설명 대조 |
| 원문 보존 | 206/206 hash 일치 | 기준 Git blob, 작업 파일, CSV SHA-256의 3자 비교 |
| 분류 수 | keep 28 / compat 96 / remove-later 6 / historical-only 76 | CSV 집계 |
| MCP 책임표 | 25/25, 누락·중복 0 | `McpServer.__init__`의 실제 tools 등록 AST와 정확히 대조 |
| 혼합 경계 함수·클래스 | 기재한 대표 symbol 존재 확인 | src 전체 Python AST의 정의 집합 대조 |
| 기존 코드·스킬·테스트·문서 | 변경 없음 | 기준 tree와 원문 hash 및 Git diff 대조 |
| 후속 정리 이슈 | #83 OPEN, milestone 미지정 | 생성 후 GitHub 본문 재조회 |
| 중복 이슈 | #80~#82의 계약/Skill/Claim 엔진은 기존 이슈로 연결 | 생성 전 열린 이슈와 분리/cleanup 제목의 과거 이슈 조회 |

symbol 존재 검사는 그 함수의 모든 동작을 증명하지 않는다. 실제 호출과 의미 경계는 관련 구현/테스트 소스의 별도 읽기 검토로 확인한다. 파일 개수와 hash 검사는 분류의 완전성과 원문 보존 검사이며, 분류 의미 자체의 정답률 지표가 아니다.

## 재확인 방법

저장소에서 기준 tree를 읽어 CSV의 `path`와 집합 비교한다. 각 기준 blob의 SHA-256을 CSV의 `baseline_sha256`와 비교하고, 원본 206개 작업 파일도 같은 hash인지 확인한다. 새 문서 파일은 기존 분모에 포함하지 않는다. `mcp/server.py`의 `self.tools` key 집합과 책임 결정서의 25-tool 표를 비교한다.

```sh
git ls-tree -r --name-only 598f651614df36afc3d3d303d3aaeaff596ee6b2
git diff --check
git diff 598f651614df36afc3d3d303d3aaeaff596ee6b2 --stat
```

CSV는 표준 Python `csv.DictReader`, blob hash는 `hashlib.sha256`, Python 정의/도구 등록은 `ast.parse`로 확인했다. 별도의 제품 테스트나 검증 엔진은 추가하지 않았다.

## #79 완료 조건 대조

| 이슈 조건 | 산출물 근거 |
|---|---|
| 모듈·스킬·문서·테스트 누락 없는 분류 | 기준 tree 전체 206행의 inventory + 혼합 책임 및 25-tool 표 |
| Evidence/Event/Projection/Impact/Test Design/Regression 보존 | keep 기반, compat 하위 경계, #83 보호 목록 |
| 새 상태 의미를 조용히 덮어쓰지 않음 | 별도 version/namespace 결정, 자동 치환 금지 표, #80/#82 연결 |
| 제거 전 의존성·회귀 확인 | #83 선행조건/회귀 수용 기준. 이번 변경은 문서 추가만 |
| HarnessLab와 OwnHands 책임 구별 | 분리 후보·공용 증거 기반 구별, HarnessLab 비의존 및 개발 재개 제외 |

## 별도 정적 검토

책임표 작성과 별도로 조사 에이전트가 결정서·CSV·Markdown을 원 Core/테스트와 대조했다. 구체적 차단 결함은 발견하지 못했다. 주요 확인점은 v1.1 계약 연결, managed 기록과 Control 평가의 혼합, legacy decision 의미, schema/fixture 소비, 206개 파일과 25-tool 일치다. 이 검토 역시 실제 실행 동작이나 전체 테스트 PASS를 증명하지 않는다.

## 미실행·한계

- 코드/설정/테스트를 변경하지 않아 제품 테스트 전체를 재실행하지 않았다. 과거 290 tests PASS 등의 수치를 이번 검증으로 인용하지 않는다.
- 실제 App Server/live probe, 외부 사용자 조사, 성능·보안 실험은 하지 않았다.
- 새 schema/adapter/Review/Claim/Skill/Dashboard 구현은 미수행이다.
- remove-later는 삭제 승인이 아니며, compat는 영구 지원 약속이 아니다.
- #79 이슈 종료와 main 병합은 이 준비 작업과 별개다.

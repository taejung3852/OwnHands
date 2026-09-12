# Core Control 의존성 분리 — #83

기준: #79 책임 매핑, #80 Lifecycle, #81 Skill routing, #82 Claim 평가를 포함한 main `60aa4922197e5eca7c83b233a0614d697a4c140a`.

## 변경 계약

기본 `McpServer()`와 두 stdio 진입점은 아래 **검증 도구 10개**만 제공한다. 기본 경로에서 Context/Profile/Compiler, managed 준비·실행, App Server, runtime Control 평가 모듈을 import하지 않는다. HarnessLab 설치나 설정도 필요하지 않다.

| 기본 도구 | 보존하는 책임 |
|---|---|
| `task.create` | Project/Worktree/Task와 task.created의 원자적 생성 |
| `task.import` | 현재 snapshot·diff·test Evidence 수입, 과거 Control 상태를 추정하지 않음 |
| `git.restore_capture` | Git 복원점 수집과 복원 검사 Evidence |
| `tests.baseline_record`, `tests.compare_runs` | 검사 근거와 Before–After 비교 |
| `tests.gap_detect`, `tests.design_memo`, `git.diff_impact` | Impact/Test Design/Regression에 필요한 근거와 누락 |
| `assurance.gate_evaluate`, `guarantee.evaluate` | 기존 Assurance 입력/기록 해석 계약 |

이 10개 도구의 기존 입력 schema와 결과 의미는 바꾸지 않는다. `decision: pass`라는 기록 성공 응답을 M5 검수 완료로 해석하면 안 된다. 새 Spec→Review 판정은 #80–82의 `LifecycleStore`/`evaluate_review`가 담당한다. 이 PR은 새 lifecycle용 MCP API를 중복 구현하지 않는다.

## 기존 호출자 전환

기본 `tools/list`에서 빠진 도구를 호출하면 `-32601`(tool not found)이다. 자동으로 Control을 다시 활성화하지 않는다. M4.5 계약이 필요한 호출자는 명시적으로 선택한다.

```python
from devharness.mcp.server import McpServer

server = McpServer(data_root="/absolute/private/ownhands-data", legacy_tools=True)
```

```sh
PYTHONPATH=src python3 -m devharness mcp-server --legacy-tools --data-root /absolute/private/ownhands-data
# 같은 호환 옵션을 지원하는 plugin 진입점
PYTHONPATH=src python3 -m devharness.mcp.server --legacy-tools --data-root /absolute/private/ownhands-data
```

Python 3.12 이상이 필요하며 data root는 Git worktree 밖에 둔다. `mcp.json`은 기본 검증 모드로 시작하고 source checkout의 `src`를 명시한다. `m1-demo`, `m15-comparison-plan`, `m15-context-lint`는 역사 재현 명령으로 남고, 해당 명령에서만 모듈을 읽는다.

호환 모드는 기본 10개에 다음 15개를 추가하여 **기존 25개 이름과 schema**를 보존한다: `context.lint`, `context.inspect`, `context.gate_evaluate`, `context.benchmark_plan`, `context.benchmark_evaluate`, `context.guarantee_evaluate`, `harness.profile`, `harness.contract_validate`, `harness.compile_preview`, `sandbox.inspect`, `runtime.controls_check`, `task.prepare`, `task.record_run`, `harness.candidate_apply`, `harness.candidate_rollback`.

## 실제 의존성과 keep / split / remove 판단

아래는 저장소에서 확인한 소비자다. 저장소 안의 import·테스트·예제는 외부 사용 실적의 증거가 아니다. **외부 호출자의 존재와 사용량은 미확인**이다. 따라서 구현을 지우지 않고 명시적 호환 경로를 제공한다. 이는 영구적인 구 API 지원 약속이 아니다.

| 대상 | 확인된 소비 경로 | 이번 판단과 대체 경로 |
|---|---|---|
| `control_profile.build_execution_contract` | `m2_review`, `mcp.tools.harness`, `test_control_profile`, `test_assurance`, legacy MCP 테스트. `assurance_draft` 검증 후 contract fingerprint에 포함 | **keep/compat**: 구 1.0/1.1 계약 생성과 해석을 보존. 새 검증의 대체 경로는 `lifecycle.model`의 Spec/approval와 `evaluation_store`의 결합 검증 |
| 나머지 Profile/Interview/Compiler/candidate | `m2_review`, Harness MCP, execution candidate handlers, Control 테스트 | **split**: 기본 registry에서 제거. `mcp.legacy`와 명시적 legacy handler 호출로 한정. HarnessLab 제품을 새로 구현하지 않음 |
| `managed_tasks.record_managed_run` | `m3_review`, `task.record_run`, `test_managed_tasks`, legacy MCP 테스트 | **split**: Control 평가는 legacy adapter에 남김. 실제 저장은 `run_evidence.record_run_evidence`로 이동. Task/Environment/locator, Event/Evidence closure, run scope 검증과 제한된 Evidence 직렬화 보존 |
| `managed_tasks.prepare_managed_task`, `verify_start_restore` | M3 runner, `task.prepare`, managed 테스트 | **keep/compat**: managed 전용 준비는 기본 노출 제거. 현재 Git 검증은 Control-free `assurance.capture_restore_point`/`verify_restore_point`, `git.restore_capture`, lifecycle code state 사용 |
| `codex_app_server` | M3 runner 및 transport 테스트; 기존 run 자료형 소비자 | **split**: `AppServerRecord`/`AppServerRun`은 `run_records`로 이동. 기존 module import도 같은 클래스를 반환. 프로세스·승인·transport 구현은 역사 재현용으로 유지 |
| `control_runtime` | managed adapter, `runtime.controls_check`, runtime 테스트 | **split**: 기본 경로에서 import하지 않음. 기록 자료형만 `run_records`에서 읽음 |
| `context_architecture` | `mcp.tools.context`, M1.5 CLI, `test_context_architecture`, `test_skills` | **split**: 기본 서버/CLI의 eager import 제거. Context MCP는 legacy, CLI는 해당 역사 명령에서만 import. Skill lint 테스트 소비는 그대로 유지. managed/Profile에서 직접 import하지 않는다는 점도 확인 |
| `mcp.server`, `mcp.tools.execution` | plugin config, CLI, MCP 테스트, router의 도구 매핑 문서 | **split**: 기본 10개 / legacy 25개 registry. 기존 execution Python handler 주소 보존, Control imports는 해당 handler 내부로 이동 |
| `assurance`, `imported_tasks`, `guarantees` | 기본 검증 MCP, M4/Imported 테스트, 기존 기록 해석 | **keep**: 구 계약을 읽을 수 있다는 사실과 Control 실행에 의존한다는 사실은 다름. Control 모듈 import 없이 실행 가능 |
| Event/Evidence/Catalog/Identity/Projection | Core·legacy 데이터·lifecycle Evidence binding | **keep**: schema, migration, 원자적 Task 생성, raw hash, replay 의미 변경 없음 |
| M1/M2/M3/M4 runners·review 결과·fixtures·#79 inventory | 역사 검증, 구 계약 회귀 검사 | **historical/compat**: 파일 삭제·덮어쓰기 없음. 새 Lifecycle 완료 근거로 승격하지 않음 |

`task.record_run`은 snapshot/diff/test를 일반적으로 수집하는 API가 아니다. 실제 함수는 runtime 관찰 및 restore Evidence를 저장한다. 이 부분을 통째로 삭제하지 않았다. 이미 평가된 legacy `controls`를 받아 기록하는 함수는 Control 실행 없이 재사용할 수 있지만, 입력을 다시 관찰하거나 M5 Claim으로 승격하지 않는다. 현재 snapshot/diff/test 수입은 `task.import`, 새 검사 근거 연결은 `EvidenceStore → LifecycleStore.bind_evidence → Observation`으로 계속 제공한다.

## 검증 경계

- 변경 전 main: 427 tests 통과.
- 새 실패 재현: 기본 서버/CLI가 금지한 Control 모듈을 import했고, plugin source 실행은 모듈을 찾지 못했으며 독립 run reader/recorder가 없었다. 같은 테스트를 구현 후 통과시킨다.
- `test_control_boundary`: Control/HarnessLab import를 차단한 별도 프로세스에서 실제 Spec→Review 및 Core 회귀 검사, 두 stdio 진입점의 initialize/list/task.create, plugin 설정 실행, legacy run Evidence 기록·재개방·Projection replay, foreign/unresolved 참조 거부와 raw 손상 검출.
- 기존 `test_mcp_contract_25_tools`, `test_mcp_server`, `test_mcp_core_tools`, `test_m45_vertical_slice`는 **명시적 legacy 모드**로 같은 단언을 수행한다. 25개 exact-list 검사를 삭제하거나 완화하지 않는다.
- #82의 누락 Before, 비교 불가, 기존 실패, 손상된 필수/선택 Evidence 회귀는 Control-free subprocess에서도 실행한다. 필수 검증 완료와 사용자 확인 필요의 분리 규칙은 변경하지 않는다.
- M3 live 실행은 새로 입증하지 않았다. fixture/단위 검사 통과는 실제 managed 실행 성공 근거가 아니다.

2026-09-13 실행 결과: 전체 **433 tests 통과**, #82 mutation **9/9 검출**(오류가 아닌 assertion 실패로 검출). 별도 코드 리뷰에서도 전체 433 tests를 재실행했고 P1/P2 지적이 없었다. 전체 검사 중 `M3 live probe refused or failed: live fixture content drift: AGENTS.md`가 출력되므로 이를 live 성공으로 보고하지 않는다.

재현 명령(Python 3.12 이상):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_control_boundary -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tests/run_claim_mutations.py
```

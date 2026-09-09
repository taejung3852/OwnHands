# M5-R1 Core 책임 매핑 — #79

## 결론과 기준

새 OwnHands의 Evidence·검증 기반은 유지한다. 기존 실행통제와 얽힌 부분은 명시적인 호환 경계로 남긴 뒤, 대체 계약과 회귀 확인을 거쳐 분리한다. **이 문서는 책임 결정과 후속 작업 지도이며, 새 lifecycle 구현 완료나 코드 삭제 보고가 아니다.**

- 기준 main: `598f651614df36afc3d3d303d3aaeaff596ee6b2` (M4.5, PR #71). 2026-09-09 로컬·GitHub main 일치 확인.
- 현행 기준: [#7](https://github.com/taejung3852/OwnHands/issues/7), [#79](https://github.com/taejung3852/OwnHands/issues/79), [마일스톤 #12](https://github.com/taejung3852/OwnHands/milestone/12).
- 현행 순서: #79 → #80 → #81/#82. 새 Dashboard 구현은 그 계약 확정 후 별도 이슈로 작성한다.
- 분리 이력: #78/#54. HarnessLab는 Context·Control·환경 구성/최적화의 후속 책임이며, OwnHands 설치·실행의 선행조건이 아니다. 목적지 기능이 구현됐다는 뜻도 아니다.
- 이전 #72~#77, M5/M6 계획·댓글·테스트 결과를 현행 승인·완료 증거로 자동 승계하지 않는다.

## 사용자와 합의한 결정

2026-09-09 이 작업 대화에서 합의했다.

1. 과거 기록·근거는 보존하고 새 검증에 필요한 연결은 임시 유지한다. 옛 사용법 전체의 영구 지원은 약속하지 않는다.
2. 파일별 대표 분류에 더해, 혼합 파일은 함수·역할별 유지·호환·분리 경계를 적는다. 실제 분리는 후속 작업이다.
3. 분리 후보는 책임·의존성 단위로 묶어 후속 이슈에 등록한다. #80~#82의 기존 범위와 중복 이슈를 만들지 않는다.
4. #79에서는 실제 삭제·대규모 리팩터링·과거 이력 rewrite·새 Dashboard 구현을 하지 않는다.

이 결정서는 기존 ADR을 덮어쓰지 않는 추가 경계 기록이다. M4.5 문서의 25-tool 고정/기존 signature 유지 규칙은 구 계약의 해석 기준으로 보존한다. 새 계약 상세는 #80~#82에서 명시적으로 정의하며, 이 문서가 구 wire 의미나 schema를 변경하지 않는다.

## 읽는 방법과 전체 분모

[파일별 책임표](core-responsibility-inventory.md)는 기준 commit의 **206개 추적 파일을 모두 1회씩** 분류한다. [CSV](core-responsibility-inventory.csv)는 각 경로의 원문 SHA-256을 포함한다. src 30, skills 9, tests 47, docs 114, root 6개다. 이 문서와 새 책임표 파일은 기준 main 이후의 추가 산출물이므로 분모에 포함하지 않는다.

| 분류 | 파일 수 | 뜻 |
|---|---:|---|
| keep | 28 | 새 OwnHands에 필요한 책임을 유지한다. 구 API 영구 고정 약속은 아니다. |
| compat | 96 | 기존 소비/기록 해석을 명시적 전환 전 유지한다. 내부 일부는 분리 후보일 수 있다. |
| remove-later | 6 | 활성 제품 책임의 분리/제거 후보. 지금 삭제 가능하다는 판정이 아니다. |
| historical-only | 76 | 당시 설계·검토·재현 자료로 보존한다. 현재도 실행 가능한 fixture runner일 수 있으나 새 lifecycle에서 자동 실행하지 않는다. |

파일 수는 완성도·안전성·성능 지표가 아니다. 모든 파일의 역할 분류와 대표 혼합 경계에 대한 정적 조사이며, 모든 코드 경로의 동작 검증이나 외부 실사용 전수조사는 아니다. 실행·테스트·문서 참조를 확인한 것과 외부 사용자를 확인한 것은 다르다. **사용 실태는 미확인**이며 사용자가 없다고 추정하지 않는다.

## 혼합 파일의 하위 책임

| 파일/함수·역할 | 유지할 책임 | 호환 및 후속 분리 경계 | 담당 |
|---|---|---|---|
| `catalog.py: Catalog`, migrations | 트랜잭션·참조 무결성·변조 거부 | `_migrate_v1_to_v2`, `_migrate_v2_to_v3`와 기존 테이블은 자료 읽기 경계로 유지. 새 artifact schema와 섞지 않음 | #80 |
| `identity.py: IdentityRegistry` | 원자적 Project/Worktree/Task 생성과 task.created | managed/imported 및 immutable Task snapshot은 과거 의미 유지. Issue/attempt/Spec identity로 단순 별칭 처리 금지 | #80 |
| `evidence.py: EvidenceStore`, `EVIDENCE_TYPES` | hash·redaction·scope·lineage·purge 감사 | Control 관련 type도 legacy 읽기에 필요. 이름에 Control이 있다는 이유로 registry 삭제 금지 | #80/#82, 잔여 분리 #83 |
| `events.py: EventLog`, `projections.py: ProjectionEngine` | sequence·append-only·재생성·무결성 검사 | `control.validation.recorded` 등 구 handler 및 projection v1은 보존. unknown event를 성공 처리하거나 legacy replay를 깨지 않음 | #80/#83 |
| `assurance.py: capture_restore_point`, `verify_restore_point` | Git 상태 근거와 복원 가능 범위 확인 | DB·외부 API 복원 주장으로 확장 금지. 새 code state/dirty tree 계약은 #80 | #80/#82 |
| `assurance.py: analyze_impact`, `build_test_design`, `record_test_baseline`, `compare_test_runs`, `detect_test_gaps`, packet 검증 | 영향·새 기능/회귀 분리·비교 가능성·참조 closure | `_validate_contract`, `_validate_design_binding`, `_contract_snapshot`, `_contract_from_snapshot`의 v1.1 의존성을 별도 adapter 또는 새 version 경계로 연결 | #80/#82 |
| `assurance.py: _evaluate_regression_gate`, `_override_record` | gap·regression 판정과 override 감사 근거 | 구 soft-block override와 새 Human Decision은 별개. 기존 initial_decision 및 override를 보존 | #80/#82 |
| `control_profile.py: build_execution_contract` | `assurance_draft` 검증·contract fingerprint 결합을 전환 전 유지 | permission/source/overlay 생성과 검증 입력 계약이 혼합. 새 Spec을 이 함수의 이름만 바꿔 만들지 않음 | #80/#82, 잔여 분리 #83 |
| `control_profile.py: profile_project`, `run_interview`, `build_baseline`, `assess_baseline_freshness`, `compile_control_profile`, `apply_candidate`, `rollback_candidate`, `render_control_preview` | 구 기록/계약 생성에 필요한 호출은 임시 호환 | 환경 구성 전용 활성 책임은 HarnessLab 범위. Project Baseline은 새 Verification Baseline과 다른 객체 | #83; 계약 #80 |
| `guarantees.py: _evaluate_claim`, `_evaluate_requirement`, `_evidence_object_valid`, `_evidence_matches_task`, `_inference_sources_valid` | Evidence 진위·scope·추론 원천·상충 검증 원칙 | 고정 CATEGORIES, Control selector/runtime 조건과 연결됨. 새 Claim 평가에서 명시적으로 재사용·교체 | #82 |
| `guarantees.py: record_control_validation`, `_validate_control_record`, `_validate_control_check`, `_list_control_validations` | 구 Control 기록 읽기 및 감사 | Control 전용 평가/쓰기와 공용 Evidence 평가 분리. `dashboard_fresh`도 실제 Projection 검사이므로 UI 없다는 이유로 삭제하지 않음 | #82/#83 |
| `managed_tasks.py: record_managed_run`, `_runtime_evidence_fields` | Task·Event/Evidence 참조 검증과 민감정보를 제한한 수입 | `evaluate_runtime_controls`와 구 Guarantee 계산의 결합 분리. 기록 함수 전체 삭제 금지 | #80/#83 |
| `managed_tasks.py: prepare_managed_task`, `verify_start_restore`; `codex_app_server.py` | 필요한 Git 상태 근거 및 기존 AppServerRun/Record 자료 해석 | managed 시작·프로세스 실행·승인 응답은 실행통제 전용 분리 후보. 자료형 소비가 끝나기 전에 모듈 삭제 금지 | #83 |
| `imported_tasks.py: import_task` | 현재 snapshot/diff/test 수입; 관찰하지 않은 과거 실행을 만들지 않음 | 구 `_MATRIX_PATH` 및 managed-only not_evaluated 경계는 별도 adapter로 전환 | #80/#82/#83 |
| `mcp/tools/common.py` | `validate_task_exists`, Evidence 저장 | `record_tool_evidence`의 legacy decision→result/basis 요약을 새 Claim 판정에 재사용하지 않음 | #80/#82 |
| `mcp/tools/execution.py` | create/import/restore 책임 | prepare/record_run/runtime/candidate와 sandbox heuristic을 분리; 아래 25-tool 표 참조 | #80/#81/#83 |
| `mcp/server.py`, `__main__.py` | stdio/JSON-RPC dispatch와 서버 진입 | registry·도구 schema와 상단 Context import/옛 CLI를 함께 전환 | #81/#83 |
| `plugin.py: load_plugin_package`, `discover_skills` | 패키지 검증·발견 | `load_plugin_manifest`의 compatibility projection은 구 소비 보호. discovery는 세션 로드/실사용 증거가 아님 | #81 |
| `review.py: render_task_review`, `_atomic_write_text`; `m4_review.py: validate_packet_document`, `render_review` | 저장 근거를 안전하게 표현·검증하는 패턴 | 새 Review/화면 완료로 승계 금지. `run_m1_demo`, `run_m4_fixture`, fixture helpers는 역사 재현. m2_review가 공용 writer를 import하므로 통째 제거 금지 | #80/#82/#83 |
| `m2_review.py`, `m3_review.py`, 과거 `docs/reviews/*` 실행기 | 당시 재현·안전 제약 보존 | historical-only는 실행 불가라는 뜻이 아님. live probe를 이 조사나 새 lifecycle 시작의 필수 단계로 자동 실행하지 않음 | #83 |
| `skills/execution-control`, `skills/test-assurance`, `skills/using-ownhands` | 필요한 create/baseline/review 연결과 전문 방법론 선택 | 사전 Context/Profile 강제와 구 gate 통제는 교체. 새로운 stage routing은 #81 | #81/#82 |
| `docs/product/Control_layer.md`, ADR-0002/0003/0006/0009/0010 | Event/Evidence/Assurance·scope·근거 축과 구 계약 해석 | Control/실행통제/옛 UI 순서는 역사 또는 이관 책임. 원문은 보존하고 새 결정에서 인용 범위를 명시 | #80/#81/#82/#83 |

## 이름을 바꾸는 것만으로 의미를 바꾸지 않는다

**결정: 구 계약과 새 계약을 별도 version/namespace 경계로 다룬다.** 아래는 #80/#82가 지켜야 할 경계이고 최종 schema/version 번호는 해당 이슈에서 정한다. 새 상태를 legacy 필드에 덮어쓰거나 기존 자료를 다시 저장해 의미를 바꾸지 않는다. legacy는 원래 type/version/result/basis/scope/참조를 보존해 읽는다. adapter가 필요하면 변환 버전·source reference·손실/미관측 항목을 명시하고, 지원하지 않는 입력은 거부하거나 gap으로 남긴다.

| 기존 의미와 근거 | 새 의미와 경계 |
|---|---|
| Execution Contract v1.0/v1.1. `assurance._validate_contract`는 v1.0의 M4 진입 거부 | Verification Spec의 ID/version/승인/Claim 참조를 별도 정의. v1.1 입력을 자동 승인 Spec으로 만들지 않음 |
| `control_profile.build_baseline`의 Project Baseline | #80의 Micro/Verification Baseline과 동일 객체가 아님. Before test·code state·environment는 명시적으로 결합 |
| Contract `gate_status=ready_for_preview` | 새 Review `ready`가 아님. 전자는 설정 preview 가능 여부 |
| MCP `status=ok`, task.create/import/record 또는 failing TDD baseline의 `decision=pass` | 실행/기록 성공과 Claim `verified`는 다름. 필수 Claim·Evidence·실제 관찰·freshness를 확인해야 함 |
| Guarantee `supported/contradicted/not_evaluated` | Claim `verified/failed/inconclusive/unobserved`와 1:1 치환 금지. 미평가 사유를 다시 구분하고 증거 문맥 평가 |
| 비교 `fixed_failure`를 tool이 pass로 요약 | Core는 새 기능 분류일 때만 adequate로 인정. 기존 회귀의 Before 실패를 정상 baseline으로 만들지 않음 |
| Regression Gate `pass/soft_block/hard_block` | Review `ready/needs-review/blocked`를 별도로 산출. 구 gate가 통과했다는 이유만으로 새 Review를 ready로 만들지 않음 |
| soft-block override 후 `pass`, `initial_decision=soft_block`, actor/reason/contract fingerprint | Human Decision은 특정 Review Snapshot을 참조하는 append-only 사람 판단. override의 결함·초기 상태를 숨기지 않음. 사람의 수용 기록으로 Claim을 verified로 변경하지 않음 |
| config permission approval, candidate apply approval, App Server approval response | 각각 실행/설정 권한에 대한 승인. Spec 승인·최종 결과 수용과 별개이며 서로 자동 대체하지 않음 |
| Projection `state=ready`, `is_fresh`, `collection_completeness` | replay/수집 상태이며 Review readiness나 Spec/code/test/environment Freshness가 아님. #80의 `current/stale/unknown` 별도 평가 |
| Human Decision append가 Event head를 전진시킴 | Projection 갱신 필요와 판단 근거의 의미상 stale을 구별. Decision 추가만으로 그 Snapshot을 즉시 stale 처리하지 않음 |
| configured/loaded/enforced와 observed/inferred/unobserved | 실현 단계와 근거 방식은 독립 축. 새 제품에서도 정보 손실 없이 보존 |

## M4.5 25개 MCP 도구의 책임

분류는 책임 기준이다. keep 도구도 구 input/envelope는 compat이며, 현재 등록을 여기서 변경하지 않는다. 역사 고정 benchmark는 현재 서버에도 등록되어 있으므로 노출 정리는 #83에서 한다.

| 도구 | 책임 분류 | 새 책임/호환 경계 | 후속 |
|---|---|---|---|
| context.lint | remove-later | Context lint 전용; 새 lifecycle 필수 단계에서 제외 후보 | #81/#83 |
| context.inspect | remove-later | 구 manifest 검증 소비 보존 후 분리 | #80/#83 |
| context.gate_evaluate | remove-later | Context 적용성 gate; Review gate로 이름 변경 금지 | #81/#83 |
| context.benchmark_plan | historical-only | M1.5 고정 비교 재현 | #83 |
| context.benchmark_evaluate | historical-only | M1.5 고정 비교 판정 재현 | #83 |
| context.guarantee_evaluate | compat | 구 Context 관찰 의미 보존; 새 Claim과 분리 | #82/#83 |
| harness.profile | remove-later | 환경 구성 전용 profile | #83 |
| harness.contract_validate | compat | v1.1 Assurance 입력 생성 연결; 새 Spec adapter는 별도 | #80/#82 |
| harness.compile_preview | remove-later | 환경 구성 preview | #83 |
| sandbox.inspect | remove-later | 경로/command heuristic; 실제 sandbox 집행의 증거가 아님 | #83 |
| git.restore_capture | keep | Git 복원 근거; 새 Baseline 입력 계약은 별도 | #80/#82 |
| runtime.controls_check | compat | 구 receipt의 Control 관찰 평가 보존; 활성 통제 의존성 분리 | #83 |
| task.prepare | remove-later | managed 실행 전제와 승인 통제 | #83 |
| task.create | keep | 원자적 식별자/Event 생성; 새 attempt 관계 추가 필요 | #80 |
| task.record_run | compat | Evidence 수입 보존, managed/runtime 평가 분리 | #80/#83 |
| task.import | keep | 현재 snapshot/diff/test 수입; 구 mode/matrix 호환 | #80/#82/#83 |
| harness.candidate_apply | remove-later | 설정 writer; journal·확인된 사용 전환 전 제거 금지 | #83 |
| harness.candidate_rollback | remove-later | 기존 apply journal 복구 책임과 함께 이동 | #83 |
| tests.baseline_record | keep | Before 근거 수집; 실패 기록 성공과 테스트 성공 구분 | #80/#82 |
| tests.compare_runs | keep | meaning/environment/계약/patch 비교; envelope는 legacy | #82 |
| tests.gap_detect | keep | Claim별 누락 확인에 재사용; 구 draft binding은 호환 | #82 |
| tests.design_memo | keep | 새 기능/회귀/금지 변경 관점 설계 재사용 | #82 |
| git.diff_impact | keep | 실제 변경과 선언한 관계·보호 대상 분석 | #82 |
| assurance.gate_evaluate | compat | 구 Gate/override 보존, 새 Review 별도 평가 | #80/#82 |
| guarantee.evaluate | compat | 구 Matrix v1·Control/공용 Evidence 혼합 평가 | #82/#83 |

근거: `mcp/server.py` registry, `mcp/tools/{context,harness,execution,assurance}.py` handle 함수, `tests/test_mcp_contract_25_tools.py:test_tools_list_contains_exact_25_canonical_tools`. 도구 등록·테스트 호출이 사용자 실사용의 증거는 아니다.

## 후속 작업과 제거 전 확인

| 담당 | 맡길 일 | #79에서 하지 않는 일 |
|---|---|---|
| [#80](https://github.com/taejung3852/OwnHands/issues/80) | lifecycle ID/version/reference, legacy Contract·Baseline·Decision·freshness 경계 | 새 schema 구현과 데이터 변환 |
| [#81](https://github.com/taejung3852/OwnHands/issues/81) | 얇은 Router·단계 Skill·명시적 tool 호출 경계, package/ref 정합성 | Skill/API 설계 중복 이슈 생성 |
| [#82](https://github.com/taejung3852/OwnHands/issues/82) | Assurance 재사용, Claim 평가, legacy Gate/Guarantee 변환 반례 | 새 검증 알고리즘 구현 |
| [#83](https://github.com/taejung3852/OwnHands/issues/83) | 위 계약 후 Control 의존성·활성 등록·옛 CLI/review 실행 경로 정리 | 즉시 삭제, HarnessLab 개발 재개, M5 일정 확대 |

#83은 함께 바뀌어야 하는 `contract → managed/imported receipt → gateway registry/CLI` 잔여 연결을 한 이슈로 묶었다. #80~#82가 담당하는 계약·평가·routing을 중복 구현하지 않는다. 마일스톤/일정은 지정하지 않았다.

제거 전 확인은 각 cleanup PR에서 수행한다.

1. 역방향 import/도구 등록/CLI/테스트/문서 소비 목록을 재확인한다. 기준 main이 바뀌면 책임표 변경분도 재검토한다.
2. 현재 자료 읽기와 새 검증 경로를 각각 확인한다. 기존 자료의 type/version/원문 해석을 변경하지 않는다.
3. 확인된 사용에는 대체 방법을 제시한다. 미확인 사용을 없다고 가정하지 않는다.
4. 아래 회귀 의미를 유지하면서 새 계약의 반례를 추가한다. old exact-list 시험을 단순 삭제해 통과시키지 않는다.
5. 필요한 기반이 HarnessLab 없이 작동하고 전용 Control import에 묶이지 않은 것을 확인한 뒤 해당 후보만 제거한다.

| 회귀 묶음 | 현재 보호 근거 | 새 계약/분리 시 확인할 의미 |
|---|---|---|
| 저장·identity | test_identity, test_events, test_evidence, test_projections | 원자성·타 Task 거부·변조/sequence 실패·private raw·감사/replay 보존 |
| 검증 비교 | test_assurance의 legacy_v10, receipts, before_after, comparison_never_turns_missing, fixed_failure, gate/override, packet 시험 | Before 부재·비교 불가·기존 실패·누락을 pass로 승격하지 않음 |
| Gate/도구 의미 | test_mcp_contract_25_tools의 baseline TDD RED, 11 status mappings, result/basis, partial contract 및 구조화 인자 반례 | 도구 실행 성공·판정·사람 결정을 분리 |
| 수입·Control | test_imported_tasks, test_managed_tasks, test_guarantees, test_control_runtime | 증거 scope/reference closure 유지, 관찰하지 않은 실행 이력 생성 금지 |
| 진입점 | test_mcp_server, test_m45_vertical_slice의 stdio roundtrip, test_skills, test_plugin_manifest | Context 분리 후 MCP 시작/발견/새 routing 유지 |
| 설정 writer | test_control_profile의 approval/apply/rollback/escape 반례 | 해당 writer를 지원하는 동안 atomic journal·경계 보호, 폐기 시 전환 근거 |

## #23 hardening 후보 재평가

[#23](https://github.com/taejung3852/OwnHands/issues/23)은 closed 이력으로 보존한다. 세 한계는 Evidence Core에도 관련되므로 기능 이관과 함께 사라졌다고 보지 않는다.

| 후보 | 이번 판단 | 다시 작업할 조건 |
|---|---|---|
| 첫 trusted Projection checkpoint 이전 Event tail 손실 | 기존 local 신뢰 한계로 명시. 이후 checkpoint 검사는 무제한 과거 보존 증명이 아님 | 외부 anchor가 필요한 실제 위협 모델 확인 후 새 ADR/이슈 |
| keyed integrity/외부 신뢰 저장소 | hash는 서명이나 관리자 변조 방지 보장이 아님. 지금 범위 확대하지 않음 | 신뢰 경계·키 관리 필요 및 비용 확정 후 새 이슈 |
| 긴 Task Event history 선형 검증 비용 | 실제 병목 증거 없음. 현재 최적화 작업으로 만들지 않음 | 실제 latency·history 규모 측정 후 새 이슈 |

위 항목은 이번에 보안/성능 실험을 수행해 새로 입증한 결과가 아니다. 기존 명시 한계와 현행 Event/Catalog/Projection 검사 구조를 대조한 재평가다. 새 #80~#82에서 한계를 초과하는 보장을 요구하면 별도 결정을 요청한다.

## 이번 산출물의 검증 범위

[검증 기록](core-responsibility-verification.md)을 참조한다. 기준 tree와 책임표의 정확한 경로 집합, 중복/누락, 원문 hash, 25-tool 목록, source symbol, 수정 범위와 GitHub 후속 연결을 확인한다. 코드는 변경하지 않으며 기존 테스트의 과거 PASS를 현행 M5 동작 검증으로 인용하지 않는다.

# #82 검증 기록 — 2026-09-13

## 초기 구현 결과와 범위

기준 main: `ab1c3476c31d1c1420e064af86e21a76b19cfb1d` (PR #86 merge).
브랜치: `feat/issue-82-claim-evaluation`.
새 의존성 없음. 기존 journal/Evidence/승인/참조 검증 재사용.

기존 테스트 391개에 새 Claim 통합 테스트 32개 추가. 최종 전체 423개 통과
(9.188초), 집중 테스트 32개 통과(1.618초). 이것은 아래 명시한 범위의
fixture 및 회귀 검증이며, 실서비스에서 모든 요구사항을 검수했다는 뜻이 아니다.

## Claim coverage

분모는 아래 16개 검증 책임이다. 각각 대응 검사를 실행했다. 테스트 수와 별개로
기능 범위 및 제외 범위를 기록한다. 상세 assertion은 tests/test_claim_evaluation.py에 있다.

| 검증 책임 | 근거 | 결과 |
|---|---|---|
| current/preserve/improve 방향·기존 실패 | test_truth_table: 독립 기대값 10행 | 충족 |
| 승인 전체 목록·반례 누락·미실행 표시 | test_all_approved_checks_remain_visible, test_failure_is_not_hidden_by_a_later_pass_or_missing_check | 충족 |
| 선택된 검사 일부만 통과 | test_missing_planned_test_cannot_be_hidden_by_other_pass | 충족 |
| 실패 기록의 선택적 누락 방지 | test_failure_is_not_hidden_by_a_later_pass_or_missing_check, test_conflicting_before_cannot_be_cherry_picked | 충족 |
| 동일 코드/환경 새 ID를 통한 실패 은폐 방지 | test_equal_code_and_environment_recapture_cannot_hide_failed_run | 충족 |
| 동일 실행 충돌과 실제 반복 실패 구분 | test_same_execution_conflict_shows_both_sources 및 metadata 관련 2건 | 충족 |
| 환경 불일치 보고·같은 내용 환경 재사용 | test_environment_difference_is_storable_as_inconclusive, test_same_environment_content_with_new_id_is_comparable | 충족 |
| optional 실패/의도적 미선택/실행 불가 구분 | test_optional_failure_and_optional_unavailable_need_attention, test_intentionally_excluded_optional_is_distinct_from_execution_failure | 충족 |
| 실제 필수 blocker와 기존 실패 공존 | test_required_blocker_preserves_other_results, test_invalid_before_does_not_block_current | 충족 |
| Evidence Task scope·raw 무결성·receipt binding | test_other_task_evidence_is_rejected, test_corrupt_after_is_reported_without_inserting_invalid_reference, test_receipt_cannot_claim_fields_different_from_raw_evidence | 충족 |
| v2 downgrade·잘못된 승인 구조 차단 | test_downgrade_cannot_bypass_approved_v2_spec, test_unknown_version_and_empty_checks_are_rejected | 충족 |
| 제출 판정 변조·평가 후 새 관찰 추가 | test_forged_summary_cannot_bypass_store, test_additional_evidence_requires_new_evaluation | 충족 |
| 코드 변경·실행 중 변화·Freshness 분리 | test_code_change_cannot_inherit_old_pass, test_execution_code_changes_and_equal_recapture, test_saved_review_freshness_is_separate_from_claim | 충족 |
| 새 Spec 후 과거 이력·Human Decision 보존 | test_historical_status_does_not_apply_new_spec_approval_to_old_receipts, test_reconstructed_origin_is_preserved_and_human_decision_cannot_rewrite | 충족 |
| 추가 발견 결함의 필수 완료와 attention 공존 | test_additional_defect_keeps_required_completion_and_attention | 충족 |
| 알 수 없는 환경·미실행·test meaning 변경·실행 오류 | test_unknown_environment_and_not_run_never_verify, test_changed_test_meaning_and_execution_error_do_not_verify | 충족 |

추가로 기존 lifecycle 46개와 Skill routing 26개를 포함한 전체 suite가 통과했다.
다른 Issue/attempt의 Evidence 연결, missing/purged Evidence 등 기존 경계의 회귀
검사는 tests/test_lifecycle.py에서 유지한다.

## 조건 반전 검증

실제 모듈을 별도 프로세스에서 한 조건씩 바꿔 같은 통합 테스트를 실행했다.
소스 파일은 수정하지 않았다. import/실행 오류는 검출 성공으로 계산하지 않는다.

| 의도적 오류 | assertion 실패 | 실행 오류 |
|---|---:|---:|
| preserve/improve Before 방향 반전 | 5 | 0 |
| 필수 coverage all → any | 1 | 0 |
| 실제 After 실패 무시 | 6 | 0 |
| 동일 실행 충돌 무시 | 4 | 0 |
| 저장된 실패 후보 제거 | 13 | 0 |
| 제출된 요약 재계산 검증 생략 | 2 | 0 |
| 다른 Task Evidence 허용 | 1 | 0 |
| 원문 무결성 확인 생략 | 1 | 0 |

8/8 오류가 검출됨. 모든 가능한 변이를 검사한 것은 아니다.

## 독립 검토와 수정

읽기 전용 검토에서 다음 네 문제를 실제 재현했다. 각각 회귀 테스트의 실패를
확인한 뒤 수정했다: 동일 fingerprint 새 ID로 실패 은폐, current의 Before 충돌
알림 누락, 같은 실행 test_id 불일치를 독립 실패로 오인, current에 필요 없는
Before 손상을 blocker로 승격. 수정 후 검토자가 집중 테스트 29개를 재실행해
통과 확인했고, 추가 중요 false-verified/저장 문제를 재현하지 못했다.
이후 추가 경계 3건을 포함한 최종 32개/전체 423개는 주 구현자가 실행했다.

## 재현

Python >=3.12, 표준 라이브러리만 필요하다.

```sh
PYTHONPATH=src python -m unittest tests.test_claim_evaluation
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python tests/run_claim_mutations.py
git diff --check
```

이 작업은 기존 `../ownhands-80/.venv/bin/python` 런타임으로 새 checkout의 소스를
읽어 실행했다. 변경한 저장소에 Python 환경/패키지를 새로 설치하지 않았다.

## 제외·미실행·남는 한계

- M3 live probe는 변경 전/후 모두 `live fixture content drift: AGENTS.md`로
  실행을 거부했다. 전체 unittest의 성공을 M3 실환경 성공으로 해석하지 않는다.
- 실제 외부 서비스, 결제 시스템, 원격 테스트 환경에서 검수하지 않았다.
- 복원 **기록과 판정**은 fixture로 검증했다. 실제 과거 환경 복원 자동화는 범위 밖이며
  실환경 복원 성공을 주장하지 않는다.
- 실행 전에 존재했던 실제 pre-change provenance 및 producer의 진술 신뢰는
  실행 adapter/검수 절차 책임이다. hash와 텍스트 출처만으로 사실을 증명하지 않는다.
- Skill 입출력 문서는 새 API와 연결했고 기존 routing 회귀를 실행했다.
  실제 에이전트가 모든 새 문서 지시를 지키는지 행동 평가를 별도로 실행하지 않았다.
- Dashboard UI·자동 수용·전체 의존성 분석·전체 강제 재검사는 구현하지 않았다.
- journal을 직접 SQL로 위조하거나 producer가 제출하지 않은 실행을 탐지하는
  인증 체계를 구현하지 않았다.


## 독립 검수 후 Evidence 무결성 집계 보완

`bba474c` 이후 독립 검수에서 발견한 조합을 추가했다. 기존 423개 테스트와
8개 조건 반전 검증으로 놓친 경계이므로 이전 통과를 이 조합의 검증으로 승계하지 않는다.

- 재현: 실패 Observation 저장 → 원본 손상 → 같은 check에 정상 pass 추가.
- 수정 전: Claim verified / required_complete=true / blockers=[]로 저장 가능.
- 수정 후: 해당 check/Claim inconclusive / required_complete=false /
  invalid_required_evidence blocker. 거부된 Observation 식별자와 진단을 보존한다.
- 수정은 Claim 집계 전 관련 진단을 반영하는 작은 공통 규칙이다. Store를
  우회하는 별도 판정은 추가하지 않았다. rules_version을 2로 올리고 과거 보고서는 보존한다.

추가 회귀 테스트 4개(비교 유형 table 3행 포함):

| 경계 | 기대/실행 결과 |
|---|---|
| 필수 실패 손상 + 정상 pass, 다른 check 정상 | 손상 관련 check만 inconclusive, 정상 check verified, 필수 완료 false, 저장 blocked |
| optional 실패 손상 + pass, 별도 required criterion 정상 | optional inconclusive, required verified, 필수 완료 true, needs-review, blocker 없음 |
| 손상 근거 + 독립적으로 확인된 유효 실패 + pass | failed 우선 유지, 필수 완료 false, 손상 진단 보존 |
| Before 손상 + 유효 Before/After, current/preserve/improve | current verified + attention 유지; preserve/improve inconclusive + blocked |

실패 테스트를 먼저 실행하여 잘못된 verified를 4회 assertion failure로 재현했다.
수정 후 집중 36개 통과(2.062초), 전체 427개 통과(10.586초).
기존 8개와 새 `ignore-relevant-invalid-evidence`를 포함해 조건 반전 **9/9 검출**.
새 조건을 제거하면 assertion failure 4개, 실행 오류 0개로 검출된다.
나머지 변이도 모두 assertion으로 검출됐으며 실행 오류는 0개다.

M3 live probe는 여전히 `live fixture content drift: AGENTS.md`로 실행 거부.
실환경 검증 미확인 경계는 유지한다. 이번 보완은 로컬 커밋만 생성하며 푸시/병합하지 않는다.

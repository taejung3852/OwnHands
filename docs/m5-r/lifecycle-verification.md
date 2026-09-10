# #80 Lifecycle 계약 검증 기록

검증 기준: `feat/issue-80-lifecycle`, 기준 main `779b5568c38a154b4dc7b55818e806a5e53639f0`.

이 문서는 로컬 자동화 검증 범위를 기록한다. 외부 사용자 실사용, Dashboard UI, Skill routing, 실제 프로젝트 테스트 실행, 보안 침투·성능 검증은 수행하지 않았다.

## 완료 조건 대조

| #80 완료 조건 | 구현·검증 근거 |
|---|---|
| 모든 Artifact의 ID·version·parent/reference | `LifecycleStore`의 kind/id/revision/hash 참조, scope closure, append-only journal. 동일 내용 idempotency, 새 revision, 논리 ID scope 이동 거부 시험 |
| 같은 commit의 다른 dirty tree 구분 | tracked 내용·삭제, untracked, symlink, file mode를 포함한 CodeState 시험 |
| Before 누락·test meaning/environment 비교 불가를 회귀 pass로 금지 | missing, not_run, inconclusive, meaning/environment 불일치의 verified Review 저장 거부와 보고 가능한 Review 저장 시험 |
| 다른 Issue·Task·attempt 근거 연결 금지 | WorkIssue/Spec, CodeState/Baseline, legacy Evidence 교차 scope 거부 시험 |
| Spec·코드·테스트·환경·판단·표시-only Freshness | 각 입력 변경, Claim 및 추가 Observation의 missing/changed test meaning, Decision/outcome append의 semantic Freshness 독립 시험 |
| 과거 version·판단 보존과 결정적 current 선택 | human approval activation, Issue별 active attempt, Snapshot/Decision 불변, journal replay 시험 |

## 추가 제품 합의 검증

- 사람 actor kind와 ID가 있는 SpecApproval/HumanDecision만 허용한다. 에이전트 자기 승인과 익명 승인을 거부했다. 이 값은 provenance이며 인증은 호출 경계의 책임이다.
- 필수 조건 미검증은 추가 검사 통과로 대체하지 않는다. 반대로 미검증을 보고하는 Review 작성은 허용한다.
- 추가 검사 실패는 `needs-review`로 남고 자동 완료되지 않는다.
- 명시적 실행 blocker와 일반 미검증을 다른 Review 상태로 보존한다.
- blocker는 실제 필수 입력·권한·서비스 부재, 실행 실패, 유효하지 않은 필수 근거의 고정 reason code만 허용한다. 막연한 잠재 영향은 blocker로 저장하지 않는다.
- Router 준비 조회는 승인된 현재 Spec과 정확한 활성 승인 쌍을 요구하고, 교차 입력 관계를 확인한다. 직접 수행 outcome은 Skill producer 없이 저장할 수 있다.
- lifecycle journal 재개·Projection lag와 legacy Event Projection이 서로 영향을 주지 않는다.
- raw Evidence가 나중에 손상되면 binding뿐 아니라 이를 참조하는 Observation·Review도 유효하게 읽히지 않는다.
- CodeState와 Environment의 fingerprint는 canonical fields에서 재계산한다. ignored 내용은 fingerprint 범위 밖이라고 표시하고 coverage를 `partial`로 둔다.
- Baseline의 모든 Observation은 같은 승인·Spec·Before CodeState·환경에 묶이고, Review의 Claim·추가 Observation은 정확한 After CodeState에 묶인다.
- 존재하지 않거나 비활성인 Attempt는 attempt 단계의 기록·준비 대상으로 인정하지 않는다. activation replay는 삭제되거나 잘못 연결된 artifact·approval을 거부한다.

## 실행 결과

2026-09-11 로컬 Python 3.12.14에서 실행했다.

```text
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_lifecycle.py -q
Ran 43 tests
OK

PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q
Ran 350 tests in 6.313s
OK
```

전체 suite 중 기존 M3 fixture runner가 `M3 live probe refused or failed: live fixture content drift: AGENTS.md`라는 진단을 출력했지만 unittest 결과는 `OK`였다. 이를 현재 M3 live 실행 성공으로 인용하지 않는다.

## 검증 경계

- 별도 SQLite와 hash chain은 로컬 우발적 손상·참조 바뀜을 탐지한다. 외부 anchor, 서명, 관리자 변조 방지를 보장하지 않는다.
- CodeState가 `partial`이면 관찰한 파일 범위의 fingerprint다. exclusion 내용이 같다는 보장은 하지 않는다.
- Review의 `verified` 최소 참조 조건만 #80에서 확인한다. Claim의 의미 평가와 관련성 알고리즘은 #82가 구현한다.
- 준비 상태 조회는 입력 준비만 확인하며 command 실행이나 권한 부여를 하지 않는다. Router 정책은 #81에서 검증한다.

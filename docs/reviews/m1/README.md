# M1 Evidence Core Review Artifact

## 확인 대상

M1의 비민감 HWPX 합성 fixture는 다음 실제 저장 흐름을 실행한다.

```text
Task identity
→ task.created Event
→ redacted Raw Evidence object와 metadata
→ evidence.recorded Event
→ GM-013 Guarantee 평가
→ guarantee.evaluated Event
→ Projection replay와 freshness
→ 최소 HTML 및 Task Guarantee Report JSON
```

실행:

```bash
PYTHONPATH=src uv run --python 3.12 python -m devharness m1-demo \
  --data-root /tmp/devharness-m1-evidence \
  --output /tmp/devharness-m1-review.html
```

출력:

- `/tmp/devharness-m1-review.html`: 판정·Evidence metadata·freshness·남은 위험
- `/tmp/devharness-m1-review.report.json`: Matrix가 생성한 Task Guarantee Report
- `/tmp/devharness-m1-evidence/`: local SQLite catalog와 redacted Raw Evidence object

## 표현 경계

- `supported`는 GM-013의 합성 test selection과 synthetic environment 범위에만 적용된다.
- Projection freshness는 Event head 반영 여부이며 Event 수집 완전성을 뜻하지 않는다.
- 수집 완전성은 `Unobserved`다.
- Raw bytes는 HTML·JSON·Git에 포함하지 않는다.
- 화면은 데이터 흐름을 사람이 검토하기 위한 최소 M1 산출물이며 M5 UI/UX 계약이 아니다.

## 2026-09-04 사전 검증 기록

- 최초 Python 3.12 전체 테스트: 실행 사례 40개 통과
- M1 Guarantee 공격 fixture: 파일에서 계산한 25개 경계
- 기존 M0-04 Probe: 필수 공격 경계 23개, schema-valid integration mutation 8개, schema adversarial mutation 2개 통과
- 생성된 Task Guarantee Report: strict draft 2020-12 schema 검증 통과
- HTML/Report secret marker 검사: 노출 0개
- Git 추적 Raw Evidence/object/catalog: 0개

이 수치는 GitHub 자동 Check가 아니라 로컬 재현 결과다. 독립 리뷰와 병합된 `main` 재검증 전까지 M1 완료 근거로 사용하지 않는다.

## 독립 리뷰 후 보강 상태

독립 리뷰는 최초 구현에서 병합 차단 결함 14개를 재현했다. 주요 경로는 process crash orphan, purge 재시도, canonical metadata 변조, 빈/의미 불일치 Evidence, explicit conflict, Control Evidence closure, schema-invalid Matrix, forbidden scope wording, 손상 Projection freshness, Git worktree 내부 Raw root, 민감 metadata key, Imported Task 표시, locator 동시 등록, 기존 object 권한이었다.

보강 구현과 회귀 테스트는 위 경로를 각각 다룬다. SQLite schema v1→v2 migration은 Projection integrity hash를 추가한다. 이 문서는 독립 재검토 전 상태이므로 병합 가능 또는 M1 완료를 주장하지 않는다. 최신 수치와 독립 재검토 결과는 동일 PR의 후속 검증 기록에 추가한다.

현재 보강 구현의 로컬 결과:

- Python 3.12 실행 테스트 57개 통과. 강제 종료 orphan 회수, purge 삭제 실패 재시도, Project/Worktree 동시 등록, catalog 변조, Projection sequence/JSON 변조를 포함한다.
- Guarantee 공격 manifest 37개. 각 항목은 실행되는 test method 이름과 연결되며 Report의 project/worktree/task/environment, 문장, scope, timestamp, residual risk를 한 번에 한 필드씩 바꾼다.
- M0-01, M0-02/03, M0-04, M0-06, M0-07 static/browser Probe 재통과.
- 생성 Report의 strict draft 2020-12 검증, SQLite `integrity_check=ok`, rollback journal `delete`, schema version 2, data/catalog/object 0700/0600/0600 확인.
- Git 추적 Raw Evidence/object/catalog 0개. GitHub 자동 Check는 0개다.

위 결과는 구현 담당자의 로컬 GREEN이며 독립 재검토를 대체하지 않는다.

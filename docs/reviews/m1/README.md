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

- Python 3.12 전체 테스트: 실행 사례 40개 통과
- M1 Guarantee 공격 fixture: 파일에서 계산한 25개 경계
- 기존 M0-04 Probe: 필수 공격 경계 23개, schema-valid integration mutation 8개, schema adversarial mutation 2개 통과
- 생성된 Task Guarantee Report: strict draft 2020-12 schema 검증 통과
- HTML/Report secret marker 검사: 노출 0개
- Git 추적 Raw Evidence/object/catalog: 0개

이 수치는 GitHub 자동 Check가 아니라 로컬 재현 결과다. 독립 리뷰와 병합된 `main` 재검증 전까지 M1 완료 근거로 사용하지 않는다.

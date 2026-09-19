# Plan: grill-spec Section Review Loop

- **기반 Spec**: [`spec.md`](spec.md)
- **작성 주체**: Codex (사람 검토 및 승인 필요)
- **일자**: 2026-09-20
- **상태**: Completed — 2026-09-20
- **실행 방식**: 현재 Builder가 직접 수행. 문서·Skill 계약 변경이므로 TDD는 적용하지 않고 정적 검사와 단일 Runtime 관측을 사용한다.

---

## 1. 구현 맥락 및 대상 파일 (Context & Target Files)

- **구현 목표 요약**: `grill-spec`에 Decision-bearing section만 대상으로 하는 3-way Review Loop와 읽기 쉬운 불릿형 Decision Card를 추가한다.
- **대상 파일 목록 및 책임 경계**:
  - `[MODIFY] .agents/skills/grill-spec/SKILL.md`: 핵심 Section Review 흐름과 Reference 라우팅.
  - `[MODIFY] .agents/skills/grill-spec/references/interview-guide.md`: 대상 판별, 3-way 처리, Decision Card 상세 계약.
  - `[MODIFY] docs/specs/README.md`: Section Review와 Artifact Checkpoint 구분.
  - `[MODIFY] docs/adr/0006-grill-spec-orchestration-tradeoffs.md`: 승인된 후속 설계 결정 기록.
  - `[MODIFY] docs/decisions.md`: 현재 `grill-spec` 결정 상태 동기화.
  - `[MODIFY] docs/evals/task-set.json`: 기존 EVAL-0004 정적 계약 보강.
  - `[NEW] docs/specs/grill-spec-section-review/intent.md`: #142의 승인된 Goal과 경계.
  - `[NEW] docs/specs/grill-spec-section-review/spec.md`: 요구사항과 AC.
  - `[NEW] docs/specs/grill-spec-section-review/plan.md`: Task와 Fresh Evidence.
- **Blast Radius Guard**: 위 목록 밖 파일은 수정하지 않는다. 새 Agent, Runner, Hook, Eval Task를 만들지 않는다.

### 1.1 비교 주장 및 Before 기준선

- **주장 유형**: 기존 Skill의 상호작용 개선.
- **Before Evidence**:
  - 현재 `SKILL.md`는 Grilling 이후 Artifact 전체 Checkpoint만 정의한다.
  - 현재 `interview-guide.md`에는 Section Review, 3-way 응답, Decision Card 계약이 없다.
  - EVAL-0004는 기존 Checkpoint·Fact 분리의 정적 적합성만 검사한다.

## 2. 작업 단위 분해 (Task Breakdown)

- [x] **Task 1: Section Review 실행 계약 추가**
  - `SKILL.md`에 Decision-bearing section Review와 기존 Checkpoint 관계를 짧게 연결한다.
  - `interview-guide.md`에 Fact 제외, 3-way 처리, 미결정 상태, Stage Mode 적용, 불릿형 Decision Card를 정의한다.
  - 연결 AC: `AC-01`~`AC-06`, `AC-11`.
- [x] **Task 2: Source of Truth와 정적 Eval 동기화**
  - `docs/specs/README.md`, ADR-0006, `docs/decisions.md`에 승인된 계약을 짧게 반영한다.
  - 기존 EVAL-0004의 필수 문자열 검사만 보강하고 새 Eval이나 Runner는 만들지 않는다.
  - 연결 AC: `AC-07`, `AC-08`, `AC-10`.
- [x] **Task 3: 핀포인트 Runtime 관측과 최종 감사**
  - Static Preflight를 한 번 실행한다.
  - read-only `codex exec` 한 번으로 `모르겠다` 응답 이후의 쉬운 재설명과 불릿형 Decision Card를 관측한다.
  - 기존 `verify` Skill로 `AC-01`~`AC-11`과 Fresh Evidence를 대조한다.
  - 연결 AC: `AC-08`~`AC-11`.

## 3. AC별 검증 전략 매핑 (Verification Strategy Mapping)

| AC | 검증 전략 | 관측 증거 | 통과 기준 |
|---|---|---|---|
| `AC-01`~`AC-06` | Skill/Reference 정적 감사 | 대상 문구와 diff | Fact 제외, 3-way, 미결정, Checkpoint, Stage Mode, Reference 분리가 모두 존재 |
| `AC-07` | Source of Truth 대조 | README·ADR·decisions diff | 세 문서가 새 계약과 모순되지 않음 |
| `AC-08` | Static Preflight | `node scripts/run-evals.js --static-only` 출력 | exit 0, regression 0 |
| `AC-09` | 단일 read-only Runtime 관측 | Codex JSONL과 최종 응답 | 쉬운 재설명, 최대 3개 핵심 불릿, 3-way 선택 재제시 |
| `AC-10` | 변경 반경 감사 | `git diff --name-only` | Target Files 밖 변경 및 새 Agent/Runner/Hook/Eval Task 없음 |
| `AC-11` | 정적 + Runtime 표시 감사 | Reference 계약과 실제 응답 | `결정할 것 → 핵심 불릿 → 추천 → 선택`, 한 카드·한 Decision |

## 4. 실행 및 신선한 검증 증거 (Execution & Fresh Evidence Checklist)

- [x] **Task 1 증거**
  - 검사: `rg`로 Section Review, 3-way, Decision Card, Checkpoint 관계 확인.
  - 결과: exit 0. `SKILL.md`에서 Intent와 Spec 각각의 Decision Review, 3-way, Checkpoint 비대체를 확인했고, Reference에서 세 응답·최대 3개 불릿·Stage Mode를 확인했다. `git diff --check` 통과.
- [x] **Task 2 증거**
  - 검사: `node scripts/run-evals.js --static-only`.
  - 결과: PR 전 리뷰 후 핵심 문구 assertion을 보강해 재실행. exit 0, EVAL-0004 PASS, regression 0건. Runtime 대상은 `--static-only` 계약에 따라 UNOBSERVED.
- [x] **Task 3 증거**
  - 실행:
    ```bash
    codex exec --json --sandbox read-only \
      '$grill-spec을 사용 중이다. 확인된 Fact는 "알림 시스템은 비동기 큐를 사용하며 현재 재시도하지 않는다"이다. 직전 Decision은 "알림 전송 실패 시 몇 번 재시도할 것인가"였고 사용자가 "무슨 소리인지 모르겠다"고 답했다. Fact를 승인 질문으로 만들지 말고 같은 Decision을 쉬운 예시로 다시 설명한 뒤 불릿형 Decision Card로 재질문하라. 파일은 수정하지 말고 다음 응답만 작성해.'
    ```
  - 결과: exit 0. 동일한 알림 재시도 Decision을 쉬운 예시가 포함된 최대 3개의 1줄 핵심 불릿으로 다시 질문했고, Fact 승인을 요구하지 않았다. 추천 1줄과 3-way 선택을 한 Decision Card 안에 제시했다. 실행 전후 `git status --porcelain -uall`이 동일하여 Runtime repo mutation은 0건이다. 내부 메모리 검색은 결과 없음(exit 1)이었으나 세션 최종 응답과 종료 코드는 정상이다.
  - Skill validator: `quick_validate.py`는 환경에 PyYAML이 없어 `ModuleNotFoundError`로 UNOBSERVED. 변경하지 않은 frontmatter와 구조는 EVAL-0004 Static Preflight로 확인했다.
- [x] **회귀 및 변경 반경**
  - `git diff --check`
  - `git diff --name-only`를 Target Files와 대조.
  - 결과: `git diff --check` 통과. `git status --porcelain -uall`의 변경 9개가 Target Files 9개와 일치하며 새 Agent·Runner·Hook·Eval Task는 없다.
- [x] **최종 AC 감사**
  - 기존 `verify` Skill로 `AC-01`~`AC-11`을 `PASS / FAIL / UNOBSERVED`로 판정.
  - 결과: PR 전 독립 리뷰의 P1/P2 3건을 수정한 뒤 재감사했다. 독립 Verifier가 `AC-01`~`AC-11` 전부 PASS, Overall PASS, blocker 없음으로 판정했고 재리뷰에서도 P1/P2가 없었다.

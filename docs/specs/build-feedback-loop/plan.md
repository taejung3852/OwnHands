# Plan: Thin build Skill 연결

- **기반 Spec**: [`spec.md`](spec.md)
- **작성 주체**: Codex
- **일자**: 2026-09-20
- **상태**: Completed
- **승인 근거**: 사용자 구현 요청 (2026-09-20)

---

## 1. 구현 맥락 및 대상 파일 (Context & Target Files)

- **구현 목표 요약**: 승인된 `spec.md`와 `plan.md`를 Task 단위 구현, Fresh Evidence, 기존 `verify`로 연결하는 최소 `build` Skill을 추가한다.
- **대상 파일 목록 및 책임 경계 (Blast Radius Guard)**:
  - `[NEW]` `docs/specs/build-feedback-loop/intent.md`: GORE 목표와 비목표.
  - `[NEW]` `docs/specs/build-feedback-loop/spec.md`: 승인된 기술 계약과 AC.
  - `[NEW]` `docs/specs/build-feedback-loop/plan.md`: 실행 순서와 Fresh Evidence.
  - `[NEW]` `.agents/skills/build/SKILL.md`: Build 단일 진입점.
  - `[NEW]` `.agents/skills/build/references/tdd-loop.md`: 조건부 TDD 최소 계약.
  - `[NEW]` `.agents/skills/build/references/subagent-routing.md`: 조건부 위임 기준.
  - `[NEW]` `docs/explain-build-skill.html`: 후속 사용자 요청에 따른 단일 HTML 설명 아티팩트.
  - `[MODIFY]` `AGENTS.md`: 승인된 Build 작업과 `build` Skill 연결 한 줄.
  - `[MODIFY]` `.gitignore`: 전역 `build/` 규칙에서 `.agents/skills/build/`만 추적하는 예외.
  - ⚠️ 위 목록 밖 파일은 수정하지 않는다.

### 1.1 비교 주장 및 Before 기준선

- **주장 유형**: `feature`
- **Before 기준선**: `[N/A — 신규 Skill 추가]`
- **TDD 적용**: 지침·문서 파일 추가이므로 비적용. 정적 검사와 단일 Runtime 관측으로 검증한다.

## 2. 작업 단위 분해 (Task Breakdown)

- [x] **Task 1: 승인 기준선과 실행 계획 고정**
  - `spec.md`를 Approved로 표시하고 본 `plan.md`에 Target Files, Task, AC 검증 전략을 기록한다.
- [x] **Task 2: Thin build Skill과 온디맨드 Reference 연결**
  - `SKILL.md`, `tdd-loop.md`, `subagent-routing.md`를 최소 내용으로 추가한다.
  - root `AGENTS.md`에 Build 진입 문장 한 줄을 추가한다.
- [x] **Task 3: 정적·Runtime 검증 및 독립 감사**
  - 정적 계약, M5 Static Preflight, 단일 read-only `$build` dry-run을 실행한다.
  - Fresh Evidence를 기록하고 기존 `verify`로 AC-01~AC-09를 감사한다.
- [x] **Task 4: 구현 메커니즘 HTML 설명**
  - 후속 명시 요청에 따라 `explain` Skill의 `shape.md` 구조로 HTML 아티팩트를 작성한다.

## 3. AC별 검증 전략 매핑 (Verification Strategy Mapping)

| AC ID | 검증 전략 | 관측 증거 | 통과 기준 |
|---|---|---|---|
| `AC-01`~`AC-07` | 파일·필수 문구·변경 반경 정적 점검 | 명령 출력, 최종 diff | 누락·범위 이탈 0건 |
| `AC-08` | 단일 read-only `$build` dry-run | JSONL Skill 읽기·응답, 실행 전후 Git 상태 | Skill 사용 관측, mutation 0건 |
| `AC-09` | M5 Static Preflight | `node scripts/run-evals.js --static-only` | exit 0, regression 0건 |

## 4. 실행 및 신선한 검증 증거 (Execution & Fresh Evidence Checklist)

> ⚠️ **The Iron Law**: Fresh Evidence 없는 완료 주장 금지.

- [x] **Task 2 정적 증거**
  - 실행 명령어: 파일·필수 문구·금지 파일 점검, `git diff --check`
  - 결과: `static_contract=PASS`, `git diff --check` exit 0, Skill 25행/202단어. 제공된 `quick_validate.py`는 실행 환경의 `PyYAML` 부재로 `[UNOBSERVED]`이며 동일 항목을 직접 정적 점검했다.
- [x] **Task 3 M5 Static Preflight**
  - 실행 명령어: `node scripts/run-evals.js --static-only`
  - 결과: exit 0, 6.2ms, regression 0건. EVAL-0004 PASS, 런타임 대상은 `--static-only` 계약에 따라 UNOBSERVED.
- [x] **Task 3 Runtime dry-run**
  - 실행 명령어: `codex exec --json --sandbox read-only '$build ...'`
  - 결과: exit 0. `.agents/skills/build/SKILL.md` 읽기 이벤트와 Task 2·Builder 직접 수행 선택을 관측했고, 실행 전후 Git 상태 차이는 0건이었다.
- [x] **회귀 검증 게이트**
  - 실행된 정적 스위트 범위 내 실패 미관측 여부: M5 Static Preflight 범위 내 회귀 0건.
- [x] **최종 AC 역추적 대조**
  - 기존 `verify` 및 독립 `verifier` 판정: AC-01~AC-09 전부 `PASS`, Overall `PASS`. `quick_validate.py`는 환경의 `PyYAML` 부재로 `[UNOBSERVED]`지만 필수 AC가 아니며 직접 정적 점검으로 계약을 확인했다.
- [x] **후속 HTML 설명 아티팩트**
  - 결과: HTML 파싱, Shape 계약, 브라우저 상·하단 반응형 렌더링 확인. 스토리 카드 3개, 숨김 정답 퀴즈 2개.

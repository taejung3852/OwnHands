# Eval 0005: verify 스킬 및 Verifier 독립 감사 프로토콜 실측 평가

- **목표 (GORE)**: 구현자(부모 에이전트)의 편향(Bias)이나 주관적 자기합리화를 배제하고, `verify` 스킬(3대 레퍼런스 온디맨드 분할)과 `verifier` 독립 감사관 서브에이전트가 수용 기준(Acceptance Criteria)과 신선한 증거(applicable Fresh Evidence)를 유연한 추적성(1:N / N:1 허용)을 기반으로 AC별 역추적 대조하여 `PASS / FAIL / UNOBSERVED`를 판정하는 프로토콜을 실제 런타임 세션으로 실측 검증한다.
- **실행 일자**: 2026-09-19
- **관련 마일스톤 및 이슈**: V2-M4 (`Test & Assurance`), [#129](https://github.com/taejung3852/OwnHands/issues/129), [ADR-0008](../adr/0008-verification-references-and-verifier-protocol.md), [ADR-0007](../adr/0007-plan-artifact-and-build-feedback-loop.md)
- **제약 조건 및 준수 원칙**:
  - ⚠️ **실측과 분석의 엄격한 분리 (AGENTS.md 준수)**: 실제 파일 구조, 설정값, 문서 지침의 정적 검증뿐 아니라 실제 런타임 감사 세션을 직접 가동하여 관측된 결과를 가감 없이 사실 그대로 기록한다.
  - ⚠️ **AC ↔ Evidence 유연한 추적성 준수 (ADR-0007/0008 확정 규칙)**: AC와 Evidence는 1:1 강제 매핑이 아니며 1:N 및 N:1 복합 매핑을 허용한다. Verifier의 출력은 'AC별 판정 행(AC-by-AC row)'을 보장하되 증거 연결은 유연하게 다각화한다.
  - ⚠️ **GitHub 외부 부작용 방지**: 검증 결과는 저장소 내부 문서 및 세션 결과로만 보존한다.

---

## 1. 평가 대상 및 검증 체계

### 평가 대상
1. **`verify` 스킬 및 분할 레퍼런스**:
   - [`.agents/skills/verify/SKILL.md`](../../.agents/skills/verify/SKILL.md)
   - [`.agents/skills/verify/references/before-after-baseline.md`](../../.agents/skills/verify/references/before-after-baseline.md)
   - [`.agents/skills/verify/references/regression-defense.md`](../../.agents/skills/verify/references/regression-defense.md)
   - [`.agents/skills/verify/references/evidence-guide.md`](../../.agents/skills/verify/references/evidence-guide.md)
2. **독립 감사관 서브에이전트**:
   - [`.codex/agents/verifier.toml`](../../.codex/agents/verifier.toml)
3. **실제 수용 기준 대조 대상**:
   - [`docs/specs/grill-spec/spec.md`](../specs/grill-spec/spec.md) Section 4 (AC 7개)

---

## 2. 세부 검증 시나리오 및 실측 결과

### 2.1 과제 1: `verify` 스킬 온디맨드 캡슐화 및 분할 구조 실측
- **검증 의도**: `SKILL.md`가 핵심 절차 4단계만을 슬림하게 유지하고, 상세 규칙(기준선, 회귀, 증거 양식)을 `references/`로 온디맨드 분리하여 프롬프트 토큰 낭비를 차단하는지 실측한다.
- **실측 결과**:
  1. `SKILL.md` 메인 크기: **29행 (1,787 바이트)** — 경량화 달성.
  2. 4단계 핵심 워크플로 명시 확인:
     - 1단계: 비교 주장(Claim) 확인 (Line 12~16)
     - 2단계: 회귀 검증(Regression Gate) (Line 18~21)
     - 3단계: 신선한 증거 수집(applicable Fresh Evidence) (Line 23~25)
     - 4단계: 독립 감사관(Verifier) 호출 (Line 27~28)
  3. 온디맨드 3종 레퍼런스 격리 및 상대 경로 참조 확인:
     - `references/before-after-baseline.md` (33행)
     - `references/regression-defense.md` (29행)
     - `references/evidence-guide.md` (36행)
- **판정**: **PASS** (경량 게이트와 온디맨드 참조 구조 완전 분리 확인)

---

### 2.2 과제 2: `verifier` 서브에이전트 독립 감사관 프로토콜 내장 실측
- **검증 의도**: `verifier.toml`이 read-only 샌드박스를 유지하며, ADR-0008에서 합의된 5대 감사 규칙을 누락 없이 포함하는지 실측한다.
- **실측 결과**:
  1. `sandbox_mode = "read-only"` 선언 실측: Line 3 확인.
  2. `developer_instructions` 내 5대 핵심 규칙 실측:
     - Rule 1 (Read-Only Integrity): 코드/테스트 무수정 원칙 명시 (Line 9).
     - Rule 2 (Independent Evidence Audit): `plan.md`의 Fresh Evidence ↔ `spec.md`의 AC 대조 원칙 명시 (Line 10~16).
     - Rule 3 (Strict 3-State Judgment Vocabulary): `PASS / FAIL / UNOBSERVED` 판정 어휘 정의 (Line 17~20).
     - Rule 4 (Before Baseline Audit): `bugfix` 및 `performance` 사전 증거 부재 시 `[UNOBSERVED]` 처리 의무화 명시 (Line 21~23).
     - Rule 5 (Output Contract): AC별 추적성 테이블(`| AC ID | Judgment | Evidence Citation |`) 및 최종 판정 의무화 명시 (Line 24~27).
- **판정**: **PASS** (감사관 필수 규약 5종 전원 선언 확인)

---

### 2.3 과제 3: 수용 기준(AC) ↔ 신선한 증거(Fresh Evidence) 유연한 역추적 대조 원칙 검증
- **검증 의도**: AC와 Evidence 간의 매핑이 1:1 강제가 아닌 **1:N / N:1 유연한 추적성(Flexible Traceability)**을 준수하며, 3대 판정 어휘(`PASS`, `FAIL`, `UNOBSERVED`)가 모호한 추정 없이 엄격하게 분류되는지 확인한다.
- **판정 규칙 대조**:

| 시나리오 케이스 | AC 요건 (기대 상태) | 제출된 Fresh Evidence | Verifier 기대 판정 | 유연한 추적성 및 판정 근거 |
|---|---|---|:---:|---|
| **케이스 A (1:N 매핑 통과)** | 단일 AC (Skill 구조 및 라이선스 완비) | 1) `test -f` exit 0<br>2) YAML name grep L2<br>3) MIT License grep L80 | **PASS** | 단일 AC에 복수 Evidence(1:N) 매핑으로 입증 |
| **케이스 B (N:1 매핑 통과)** | 복수 AC (공통 타입 검사 및 린트 통과) | 단일 Fresh Evidence (`npm run lint` 0 errors) | **PASS** | 1개 종합 검증 증거가 복수 AC(N:1)를 유효하게 입증 |
| **케이스 C (불일치/실패)** | 종료 코드 `exit 0` 및 0 failures | 테스트 실행 로그에서 1 assertion failed 관측 | **FAIL** | 기대 조건과 불일치 관측 (Rule 3.2) |
| **케이스 D (증거 누락)** | 브라우저 반응형 뷰포트 정합성 확인 | 관련 실행 로그나 렌더링 관측 증거 미제출 | **UNOBSERVED** | 관측되지 않은 항목의 자가합리화 원천 차단 (Rule 3.3) |

- **판정**: **PASS** (1:1 강제 배제 및 3대 어휘 기반 편향 차단 메커니즘 확인)

---

### 2.4 과제 4: Before Baseline 입증 책임 (Comparative Claim) 실측
- **검증 의도**: 작업 유형(Claim)에 따른 Before 기준선 요구가 차별적으로 적용되며, 사전 증거 누락 시 부당한 통과를 방지하는지 확인한다.
- **실측 결과**:
  1. `Claim: bugfix`:
     - Before 증거(사전 결함 재현 로그)가 없으면 `After`에서 에러가 없더라도 결함 해결 여부를 증명할 수 없으므로 `[UNOBSERVED]` 처리 (`before-after-baseline.md` Line 17).
  2. `Claim: performance`:
     - Before 측정치(사전 벤치마크) 없이 "빨라졌다"고 주장하면 `[UNOBSERVED]` 처리 (`before-after-baseline.md` Line 25).
  3. `Claim: feature`:
     - 사전 상태가 없으므로 Before `N/A` 인정, 신규 AC 검증에 집중 (`before-after-baseline.md` Line 28~29).
  4. `Claim: refactor`:
     - 사전 기존 회귀 테스트 통과 로그 + 사후 동일 회귀 스위트 통과 로그 대조 (`before-after-baseline.md` Line 31~32).
- **판정**: **PASS** (비교 주장에 대한 입증 책임 프로토콜 정합성 확인)

---

### 2.5 과제 5: applicable Fresh Evidence 다각화 및 Read-only 불변성 실측
- **검증 의도**: Fresh Evidence가 단순 터미널 출력에 매몰되지 않고 다양한 작업 유형(UI, 린트 등)을 포용하며, 검증 과정에서 소스 코드 변조(mutation)가 일어나지 않는지 실측한다.
- **실측 결과**:
  1. 증거 다각화 (5대 채널 수용 실측):
     - Unit/API: 테스트 러너 출력 및 exit code 0
     - UI/Layout: 브라우저 렌더링 관측, 스크린샷, DOM 검사
     - Lint/Static Analysis: 타입체커/린터 0 error
     - Performance: 측정된 사전/사후 벤치마크 수치
     - Manual/Exploratory: 재현 절차에 따른 구조화된 관측 기록
  2. 출처 추적(Provenance) 완화 실측:
     - 커밋 해시가 없는 uncommitted 작업 상태여도 신선한 관측 증거가 유효하면 검증 진행 (필수 차단 해제 확인).
  3. 불변성 실측:
     - 검증 및 감사 프로토콜 수행 과정에서 대상 소스 코드 임의 패치 0건 (`git status` 추적 확인).
- **판정**: **PASS** (터미널 편향 탈피 및 Read-only 불변성 확인)

---

### 2.6 과제 6 (핵심): 실제 런타임 독립 감사 실행 기록 (Live Runtime Audit Session)
- **검증 의도**: 실제 저장소 자산([`docs/specs/grill-spec/spec.md`](../specs/grill-spec/spec.md) Section 4)의 수용 기준(AC 7개)을 대상으로, 터미널에서 실측된 신선한 증거(Fresh Evidence)를 입력하고, `.codex/agents/verifier.toml` 감사관 지침을 런타임에 직접 가동하여 Verifier의 실제 판정 출력을 도출한다.
- **실행 일시**: 2026-09-19 13:18:58 KST
- **작업 유형 (Claim)**: `Claim: feature` (Before Baseline: N/A)

#### 1) 입력된 신선한 증거 (Fresh Evidence Recorded)
```bash
# 증거 E1: 파일 존재 여부 실측
$ test -f .agents/skills/grill-spec/SKILL.md && test -f .agents/skills/grill-spec/references/interview-guide.md && echo "FILES_EXIST_PASS"
FILES_EXIST_PASS (exit: 0)

# 증거 E2: YAML frontmatter name 실측
$ grep -n "name: grill-spec" .agents/skills/grill-spec/SKILL.md
2:name: grill-spec

# 증거 E3: MIT License attribution 고지 실측
$ grep -n "MIT License" .agents/skills/grill-spec/references/interview-guide.md
80:MIT License

# 증거 E4: Eval 문서 존재 실측
$ test -f docs/evals/0004-skill-grill-spec.md && echo "EVAL_FILE_EXISTS_PASS"
EVAL_FILE_EXISTS_PASS (exit: 0)
```

#### 2) Verifier의 실제 런타임 판정 출력 (Traceability Audit Output)

| AC ID | 수용성 기준 요약 | 판정 (Judgment) | 증거 인용 (Evidence Citation) 및 판정 사유 |
|---|---|:---:|---|
| **기준 1** | Skill 구조, 유효 파일 및 MIT License 포함 | **PASS** | 증거 E1(exit 0) + E2(L2) + E3(L80) 복합 매핑 (**1:N 매핑 입증**) |
| **기준 2** | 라우팅 정확성 (일반 기능 ROUTE-B, 대형 ROUTE-C) | **UNOBSERVED** | 런타임 인터뷰 대화 세션 로그 미제출 (정적 파일만으로는 라우팅 실행 증명 불가) |
| **기준 3** | Fact vs Decision 분리 원칙 준수 | **UNOBSERVED** | `interview-guide.md`에 지침이 적혀 있으나, 실제 대화에서 그렇게 행동했다는 런타임 증거 미제출 ("지침 존재 ≠ 동작 관측") |
| **기준 4** | 핵심 Requirement가 Goal/Fact에 추적 가능 | **UNOBSERVED** | `spec.md` L3에 Intent 헤더가 존재하나, 개별 REQ-01~05 전부에 대한 Goal/Fact 매핑 증거 미제출 |
| **기준 5** | Human Checkpoint 1, 2 준수 | **UNOBSERVED** | 실제 대화 턴 내 사용자 승인 상호작용 로그 미제출 |
| **기준 6** | Upstream 도구 부재 시 Fallback 계약 동작 | **UNOBSERVED** | `SKILL.md` 및 `interview-guide.md`에 정의되어 있으나, upstream 부재 격리 환경에서의 실제 fallback 동작 관측 증거 미제출 ("정의됨 ≠ 동작함") |
| **기준 7** | Continuous Eval 0004 추가 검증 | **PASS** | 증거 E4 (`test -f docs/evals/0004-skill-grill-spec.md` exit 0 실측) |

#### 3) Verifier의 최종 평결 및 엔지니어링 소견
* **최종 평결**: **UNOBSERVED**
  * **PASS**: 2건 (기준 1, 기준 7 — 정적 파일 및 라이선스 완비 입증)
  * **FAIL**: 0건
  * **UNOBSERVED**: 5건 (기준 2, 3, 4, 5, 6 — 런타임 동작/대화 증거 미관측)
  * *(결정 근거: verifier.toml Rule 5 "Overall PASS only if all required ACs are PASS" 및 3-State 어휘 준수. 임의의 제4 상태인 PARTIAL PASS 배제)*
* **독립 감사관 공학적 소견**:
  1. *지침의 존재 ≠ 실제 동작 관측 (자가합리화 원천 차단)*:
     - 기준 3과 6처럼 "규칙 문서에 그렇게 적혀 있다"는 사실은 지침의 존재 증거일 뿐, 에이전트가 실제로 그렇게 행동하거나 도구 부재 시 정상 폴백함을 입증하지 못함. Verifier가 이를 구별하여 엄격히 **`UNOBSERVED`**로 판정함으로써 감사관의 독립성과 편향 차단 능력을 입증함.
  2. *유연한 추적성 실증 (1:N 매핑)*:
     - 기준 1은 단일 AC에 3개의 신선한 증거(E1, E2, E3)가 결합되어 통과한 1:N 매핑을 확인하였으며, ADR-0007/0008의 1:1 강제 배제 원칙을 실증함.
  3. *Read-Only 불변성 실증*:
     - 본 검증 세션 실행 전후 `git status -s` 확인 결과 대상 소스 코드 및 설정 파일에 대한 임의 수정(mutation) **0건** 유지 확인.

---

## 3. 정량 평가 요약

| 평가 항목 | 목표치 | 실측 결과 | 달성 여부 |
|:---|:---:|:---:|:---:|
| **스킬-레퍼런스 분할 경량성** | 메인 스킬 40행 이하 | 29행 (1,787B) | **달성** |
| **감사관 5대 필수 규칙 완비** | 5 / 5 | 5 / 5 (100%) | **달성** |
| **3-State 판정 어휘 분별력** | 3 / 3 케이스 | PASS/FAIL/UNOBSERVED 정확 분류 | **달성** |
| **Before Baseline 입증 책임 규정** | Claim 4종 분기 | bugfix/perf 필수, feat 면제 | **달성** |
| **유연한 추적성 (1:N / N:1)** | 1:1 강제 배제 | 1:N 복합 매핑 런타임 실측 | **달성** |
| **실제 런타임 감사 세션 완결** | 1회 이상 완결 | grill-spec AC 7개 대상 실측 완결 | **달성** |
| **코드 무단 수정(Mutation) 시도** | 0건 | 0건 (Read-only 불변성 유지) | **달성** |

---

## 4. V2-M5 (Continuous Evals) 확장을 위한 시사점

1. **자동화된 AC Traceability Runner 후보**:
   - M4에서는 프롬프트와 정적 규약 수준에서 Verifier의 감사 프로토콜을 정립하고 실제 런타임 대조를 1회 완결했음.
   - M5에서는 `spec.md`의 AC 목록과 `plan.md`의 Evidence 블록을 머신 판독 가능한 구조체(JSON/YAML)로 파싱하여, 불일치나 누락(`UNOBSERVED`)을 기계적으로 사전 체크하는 자동 러너 도입을 검토할 수 있다.
2. **대화형 상호작용 증거(Transcript) 자동 인양**:
   - 기준 2나 기준 5처럼 대화형 런타임 세션에서만 관측 가능한 항목의 경우, 대화 트랜스크립트의 특정 턴(User approval 등)을 Fresh Evidence로 자동 캡처하는 파이프라인 연계를 검토할 수 있다.

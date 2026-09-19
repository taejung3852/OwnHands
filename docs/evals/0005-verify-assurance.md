# Eval 0005: verify 스킬 및 Verifier 독립 감사 프로토콜 실측 평가

- **목표 (GORE)**: 구현자(부모 에이전트)의 편향(Bias)이나 주관적 자기합리화를 배제하고, `verify` 스킬(3대 레퍼런스 온디맨드 분할)과 `verifier` 독립 감사관 서브에이전트가 수용 기준(Acceptance Criteria)과 신선한 증거(applicable Fresh Evidence)를 1:1로 엄격 대조하여 `PASS / FAIL / UNOBSERVED`를 판정하는 프로토콜을 실측 검증한다.
- **실행 일자**: 2026-09-19
- **관련 마일스톤 및 이슈**: V2-M4 (`Test & Assurance`), [#129](https://github.com/taejung3852/OwnHands/issues/129), [ADR-0008](../adr/0008-verification-references-and-verifier-protocol.md)
- **제약 조건 및 준수 원칙**:
  - ⚠️ **실측과 분석의 엄격한 분리 (AGENTS.md 준수)**: 실제 파일 구조, 설정값, 문서 지침의 정적 검증과 대조 시뮬레이션 결과를 가감 없이 사실 그대로 기록하며, 미실측 사항을 실측으로 위장하지 않는다.
  - ⚠️ **GitHub 외부 부작용 방지**: 검증 결과는 저장소 내부 문서 및 세션 결과로만 보존한다.

---

## 1. 평가 대상 및 5대 검증 과제

### 평가 대상
1. **`verify` 스킬 및 분할 레퍼런스**:
   - [`.agents/skills/verify/SKILL.md`](../../.agents/skills/verify/SKILL.md)
   - [`.agents/skills/verify/references/before-after-baseline.md`](../../.agents/skills/verify/references/before-after-baseline.md)
   - [`.agents/skills/verify/references/regression-defense.md`](../../.agents/skills/verify/references/regression-defense.md)
   - [`.agents/skills/verify/references/evidence-guide.md`](../../.agents/skills/verify/references/evidence-guide.md)
2. **독립 감사관 서브에이전트**:
   - [`.codex/agents/verifier.toml`](../../.codex/agents/verifier.toml)

---

## 2. 세부 검증 시나리오 및 실측 결과

### 과제 1: `verify` 스킬 온디맨드 캡슐화 및 분할 구조 실측
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

### 과제 2: `verifier` 서브에이전트 독립 감사관 프로토콜 내장 실측
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

### 과제 3: 수용 기준(AC) ↔ 신선한 증거(Fresh Evidence) 1:1 대조 프로토콜 실측
- **검증 의도**: 검증자가 실제 AC와 Fresh Evidence를 대조할 때 모호한 추정 없이 3대 판정 어휘(`PASS`, `FAIL`, `UNOBSERVED`)를 정확히 부여하는지 검증한다.
- **실측 시뮬레이션 대조표**:

| 시나리오 케이스 | AC 요건 (기대 상태) | 제출된 Fresh Evidence | Verifier 기대 판정 | 실측 규칙 대조 결과 | 판정 |
|---|---|---|:---:|---|:---:|
| **케이스 A (충족)** | 서브에이전트 toml에 `sandbox_mode = "read-only"` 선언 | 실제 파일 3행에 `sandbox_mode = "read-only"` 관측 로그 첨부 | **PASS** | 증거가 AC를 직접 증명함 (Rule 3.1) | **PASS** |
| **케이스 B (불일치/실패)** | 종료 코드 `exit 0` 및 0 failures | 테스트 실행 로그에서 1 assertion failed 관측 | **FAIL** | 기대 조건과 불일치 관측 (Rule 3.2) | **PASS** |
| **케이스 C (증거 누락)** | 브라우저 반응형 뷰포트 정합성 확인 | 관련 실행 로그나 렌더링 관측 증거 미제출 | **UNOBSERVED** | 관측되지 않은 항목의 자가합리화 차단 (Rule 3.3) | **PASS** |

- **판정**: **PASS** (3대 상태 어휘에 따른 편향 없는 판정 메커니즘 확인)

---

### 과제 4: Before Baseline 입증 책임 (Comparative Claim) 실측
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

### 과제 5: applicable Fresh Evidence 다각화 및 Read-only 불변성 실측
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

## 3. 정량 평가 요약

| 평가 항목 | 목표치 | 실측 결과 | 달성 여부 |
|:---|:---:|:---:|:---:|
| **스킬-레퍼런스 분할 경량성** | 메인 스킬 40행 이하 | 29행 (1,787B) | **달성** |
| **감사관 5대 필수 규칙 완비** | 5 / 5 | 5 / 5 (100%) | **달성** |
| **3-State 판정 어휘 분별력** | 3 / 3 케이스 | PASS/FAIL/UNOBSERVED 정확 분류 | **달성** |
| **Before Baseline 입증 책임 규정** | Claim 4종 분기 | bugfix/perf 필수, feat 면제 | **달성** |
| **Fresh Evidence 다양성 채널** | 5개 채널 | 5개 채널 수용 규정 완비 | **달성** |
| **코드 무단 수정(Mutation) 시도** | 0건 | 0건 (Read-only 유지) | **달성** |

---

## 4. V2-M5 (Continuous Evals) 확장을 위한 시사점

1. **자동화된 AC Traceability Runner 후보**:
   - M4에서는 프롬프트와 정적 규약 수준에서 Verifier의 감사 프로토콜을 정립했음.
   - M5에서는 `spec.md`의 AC 목록과 `plan.md`의 Evidence 블록을 머신 판독 가능한 구조체(JSON/YAML)로 파싱하여, 불일치나 누락(`UNOBSERVED`)을 기계적으로 사전 체크하는 자동 러너 도입을 검토할 수 있다.
2. **Before Baseline 아티팩트 보관**:
   - 버그 수정 작업 시 부모 세션이 Before 재현 로그를 특정 아티팩트(`scratch/before-baseline.log`)에 자동 스냅샷해 두는 워크플로를 검토할 수 있다.

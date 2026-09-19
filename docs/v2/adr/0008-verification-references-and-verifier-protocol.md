# ADR-0008 — 상황별 검증 Reference 구조 및 Verifier 감사 프로토콜

- **상태:** Proposed — 검토 대기
- **일자:** 2026-09-19
- **관련 Issue:** [#127](https://github.com/taejung3852/OwnHands/issues/127) (선행: [#125 Research Gate](https://github.com/taejung3852/OwnHands/issues/125))
- **관련 PR:** [#126](https://github.com/taejung3852/OwnHands/pull/126), [#128](https://github.com/taejung3852/OwnHands/pull/128)

---

## 1. Context (배경 및 문제)

### 1.1 V1의 교훈: 배보다 배꼽이 더 커진 검증 시스템
- V1([project-journey.md](../../story/project-journey.md))은 AI 에이전트의 환각과 허위 완료 선언을 막기 위해 검증 스펙(Verification Spec), 베이스라인(Baseline), 리뷰(Review), 증거(Evidence), 실시간 대시보드(Dashboard)를 모두 코드로 직접 구축했다.
- 그러나 커스텀 러너 바이너리, 실시간 소켓/서버, 복잡한 파서 등 **검증 시스템 자체를 만들고 유지보수하는 부담이 실제 제품 개발보다 커지는 주객전도**를 겪었다.
- **V2의 절대 원칙 (Thin Harness / Zero-Code)**:
  - 거대한 독자 CLI 러너나 상시 모니터링 대시보드를 만들지 않는다.
  - 플랫폼(Codex)의 네이티브 도구(`npm test`, `pytest`, Subagent, Git diff) 위에 **가벼운 마크다운 지침(Reference)과 프로토콜**만 얹는다.

### 1.2 M3에서 M4로 넘어온 미결 과제
- V2-M3([ADR-0007](0007-plan-artifact-and-build-feedback-loop.md))를 통해 실행 계획인 `plan.md` 아티팩트와 SDD 기반 Build Feedback Loop 6대 원칙을 메인 브랜치에 확정했다.
- 그러나 ADR-0007 원칙 5에 명시했듯이:
  > *"Verifier 런타임 권한 경계: 현재 `verifier.toml`은 `sandbox_mode = "read-only"`이므로... Verifier가 테스트를 직접 재실행하는 권한/환경 확정은 런타임 실측 후 M4(`Test & Assurance`)에서 다룬다."*
- 또한 검증 지식(회귀 방어, Before-After 측정 등)을 상시 프롬프트에 주입하면 카탈로그 토큰 예산을 고갈시키므로, **지연 로딩(Progressive Disclosure)**을 구현하는 구체적 배치 구조가 필요했다.

### 1.3 1차 자료 조사 결과 ([docs/v2/research/m4-test-and-assurance.md](../research/m4-test-and-assurance.md))
1. **Fact 1 (Codex Progressive Disclosure)**:
   - Skill 카탈로그 예산은 10,000 토큰 천장이 존재하지만, `references/` 디렉터리에 둔 문서는 초기 카탈로그 예산을 소모하지 않는다. 단, 상위 문서에서 명시적으로 읽는 조건과 경로를 링크해야 로드된다.
2. **Fact 2 (Verifier read-only 런타임 제약 분석)**:
   - 현재 `verifier.toml`의 `sandbox_mode = "read-only"`는 파일시스템 쓰기(`workspace-write`)가 제한된다.
   - 많은 테스트 러너(`pytest`, `jest` 등)는 실행 시 캐시·임시 파일 쓰기를 시도하므로 `read-only` 환경에서 실패할 가능성이 높다. (단, 실제 재실행 여부는 미실측 상태로 명시)
3. **Fact 3 (Before-After Baseline 원칙의 가치)**:
   - 버그 수정이나 성능 개선 시 "코드를 건드리기 전 실패/측정 로그"를 확보하지 않으면, AI 에이전트가 "고쳤다/빨라졌다"고 거짓 주장을 하더라도 검증할 수 없다.

---

## 2. Decision (결정)

OwnHands는 V2-M4(`Test & Assurance`)의 핵심 규약으로 다음 **3대 아키텍처 결정**을 제안한다.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        V2-M4 검증 체계 흐름                            │
├────────────────────────────────────────────────────────────────────────┤
│ 1. 검증 지식의 온디맨드 로드 (Progressive Disclosure)                 │
│    plan.md의 전략에 따라 docs/v2/references/ 를 핀포인트로 읽음        │
│                                                                        │
│ 2. 비교 주장(Claim)별 Before Baseline 확보                            │
│    버그/성능 개선 작업 시 코드 수정 전 결함/수치 기록 (미확보 시 UNOBSERVED) │
│                                                                        │
│ 3. Builder 자체 루프 ➔ Fresh Evidence 수집                            │
│    네이티브 러너 실행 후 터미널 출력(Exit 0, Assert, 커밋)을 plan.md에 기록 │
│                                                                        │
│ 4. Verifier Subagent 독립 감사 (Auditor Model)                         │
│    read-only 샌드박스에서 spec.md AC ↔ Fresh Evidence 역추적 대조      │
│    판정: PASS / FAIL / UNOBSERVED                                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2.1 결정 1: 검증 Reference의 영구 문서 배치 및 온디맨드 로드

#### 1) 배치 위치: 영구 문서 (`docs/v2/references/`) 중심 하이브리드
- 상황별 검증 Reference는 Skill 내부에 파묻지 않고, 저장소 영구 자산인 **`docs/v2/references/`**에 표준 마크다운으로 배치한다.
- **표준 Reference 3종 규격**:
  1. `docs/v2/references/regression-defense.md`: 회귀 방어선 원칙, 변경 영향 분석(Impact Analysis), 기존 테스트 부재 시 3대 대체 방어선 가이드.
  2. `docs/v2/references/before-after-baseline.md`: 버그 재현 로그 및 벤치마크 수치 수집 절차, Before 부재 시 UNOBSERVED 처리 기준.
  3. `docs/v2/references/fresh-evidence-audit.md`: 신선한 터미널 증거(Fresh Evidence) 작성 양식 및 Verifier 역추적 감사 체크리스트.

#### 2) 온디맨드 로드 규칙 (Progressive Disclosure)
- **금지**: `AGENTS.md`나 Skill 본문에 검증 가이드 전문을 인라인으로 때려 넣는 행위 (카탈로그 토큰 낭비 및 컨텍스트 오염).
- **채택**: `plan.md`의 `AC별 검증 전략 매핑(Verification Strategy Mapping)` 테이블에서 해당 태스크에 필요한 검증 가이드를 핀포인트로 링크한다.
  - 예: 단위 테스트/회귀 태스크 ➔ `[참고: regression-defense.md](../../references/regression-defense.md)`
  - 예: 버그 수정/성능 태스크 ➔ `[참고: before-after-baseline.md](../../references/before-after-baseline.md)`
- 에이전트는 해당 태스크를 실행할 때만 해당 링크를 `view_file`하여 필요한 지침을 획득한다.

---

### 2.2 결정 2: Verifier Subagent "독립 감사관(Auditor)" 모델 채택

#### 1) 메커니즘: Fresh Evidence 역추적 감사 (Traceability Audit)
- Verifier Subagent([ADR-0001](0001-initial-subagent-roles.md))는 **직접 테스트를 재실행하는 Runner가 아니라, Builder가 제출한 신선한 터미널 증거(Fresh Evidence)를 `spec.md`의 AC와 역추적 대조하는 독립 감사관(Auditor)**으로 역할을 정립한다.
- **채택 사유**:
  1. **Thin Harness 원칙**: 테스트 러너를 대신 돌리는 복잡한 오케스트레이션 코드를 만들지 않고 순수 LLM 추론 대조(Zero-Code)로 동작한다.
  2. **런타임 제약 회피**: `sandbox_mode = "read-only"` 환경에서도 파일 쓰기 권한 충돌 없이 안전하게 즉시 작동한다.
  3. **비용 및 속도 최적화**: 모든 테스트를 처음부터 끝까지 중복 실행(빌드 2회, 테스트 2회)하는 지연과 리소스 낭비를 방지한다.

#### 2) AC ↔ Evidence 역추적 대조 및 3대 판정 어휘
- **유연한 매핑**: AC와 Evidence는 1:1 강제 매핑이 아니며, 1:N 또는 N:1 복합 매핑을 허용한다.
- Verifier는 `plan.md`의 증거를 감사하여 다음 3대 상태 어휘로만 판정한다:

| 판정 어휘 | 판정 조건 | 후속 조치 |
|---|---|---|
| **`PASS`** | 제출된 Fresh Evidence(최신 커밋, exit code 0, assertion 통과, 관측 로그)가 `spec.md`의 해당 AC를 완벽히 입증할 때 | 검증 통과 완료 |
| **`FAIL`** | 실행 결과 에러, assertion 실패, AC 기대 동작 불일치, 또는 증거가 낡았거나 조작/자가합리화 정황이 발견될 때 | Builder에게 결함 피드백 및 재작업 |
| **`UNOBSERVED`** | 해당 AC에 대한 실행 증거가 누락되었거나, 테스트 부재 등으로 실제 관측되지 않은 상태 | 거짓 통과(Silent Pass) 방지, 미관측 사실 명시 |

#### 3) 위조 증거(환각) 방어 장치
- Builder가 제시한 터미널 증거의 신선도를 감사하기 위해, Verifier는 증거 내의 **① 실행 명령어, ② 프로세스 종료 코드(exit code), ③ 테스트 케이스 통과 수치, ④ 현재 작업 브랜치의 최신 커밋 해시**의 일치 여부를 교차 검증한다.
- (참고: 정교한 위조 환각에 대한 완벽한 격리 재실행은 V2-M5 Continuous Evals에서 벤치마크 리플레이 평가로 검증한다.)

---

### 2.3 결정 3: 비교 주장(Claim)별 Before-After Baseline 프로토콜

#### 1) 목적: "개선했다"는 주장에 대한 입증 책임 강제
- Before/After 베이스라인은 모든 단순 구현에 기계적으로 강제하는 의식이 아니다.
- 시스템의 동작 변화나 성능 향상을 주장하는 **비교 주장(Comparative Claim)**에 대해 입증 책임을 묻는 엔지니어링 규약이다.

#### 2) 작업 유형(Claim)별 차등 프로토콜

| 주장 유형 (Claim) | 필수 Before 기준선 증거 | 필수 After 검증 증거 | Before 부재 시 판정 |
|---|---|---|---|
| **버그 수정 (`bugfix`)** | 코드 수정 전 **결함 재현 로그** (실패하는 테스트 러너 출력 또는 터미널 오류 관측) | 동일한 조건에서 **결함 미재현 로그** (테스트 통과 또는 오류 소멸 증거) | 무조건 FAIL이 아닌 **`[UNOBSERVED]`**로 판정 (결함 해결 미입증) |
| **성능 개선 (`performance`)** | 코드 수정 전 **기준 벤치마크 측정 수치** (응답 속도, 메모리, 처리량 등) | 동일한 환경/측정 도구에서의 **개선 벤치마크 수치** | **`[UNOBSERVED]`**로 판정 (성능 향상 미입증) |
| **신규 기능 (`feature`)** | Before 불필요 (기존 동작이 없으므로 N/A) | `spec.md`의 AC에 대한 Fresh Evidence (단위 테스트 통과, 렌더링 스크린샷 등) | N/A (AC 검증 결과에 따라 PASS/FAIL) |
| **리팩토링 (`refactor`)** | 코드 수정 전 **기존 회귀 테스트 통과 로그** | 동일한 회귀 테스트의 **동일 통과 로그** 및 무결성 확인 | 기존 테스트 부재 시 `[NO_EXISTING_REGRESSION_SUITE]` 선언 |

#### 3) Before 증거 미확보 시의 `UNOBSERVED` 처리 원칙
- 에이전트가 버그 수정이나 성능 개선을 수행하면서 Before 재현 증거를 남기지 않고 코드를 고친 경우:
  - **원칙**: "에이전트의 주관적 주장(Self-Claim)은 완료의 근거가 될 수 없다."
  - Verifier는 해당 변경을 임의로 PASS 시켜주지 않으며, 반드시 `[UNOBSERVED]` 플래그를 부여한다.
  - 이를 통해 PR 리뷰어와 사람이 "이 작업은 사전에 결함이 명확히 입증되지 않은 채 코드만 변경되었음"을 인지하고 추가 검증을 요구할 수 있게 한다.

---

## 3. Consequences (결과 및 트레이드오프)

### 3.1 긍정적 효과
1. **Zero-Code 철학 유지**:
   - V1의 거대한 러너/대시보드 실패를 반복하지 않고, 표준 마크다운 지침과 Subagent 대조만으로 강력한 검증 루프를 완성한다.
2. **AI 자가합리화의 원천 차단**:
   - Before 재현 증거 없는 버그픽스 주장, Fresh Evidence 없는 완료 선언을 시스템적으로 걸러낸다.
3. **토큰 및 속도 효율 극대화**:
   - 상황별 Reference는 필요할 때만 핀포인트로 읽히므로(Progressive Disclosure) 카탈로그 예산을 낭비하지 않는다.
   - Verifier가 중복 빌드/테스트를 돌리지 않으므로 피드백 루프 속도가 빠르다.

### 3.2 트레이드오프 및 관리 비용
1. **작업 초기 공수 증가**:
   - 버그를 고치기 전에 실패 로그를 먼저 따고 기록해야 하므로, "코드부터 고치고 싶은" 충동을 억제해야 하는 개발 규율이 요구된다.
2. **환각된 증거(Spoofed Logs)의 잠재적 리스크**:
   - Verifier가 터미널을 직접 재실행하지 않고 출력을 감사하므로, 에이전트가 터미널 출력을 완벽히 날조하여 작성할 경우 감지하지 못할 수 있다.
   - ⚠️ **완화책**: 커밋 해시, exit code, assertion 카운트의 교차 대조를 수행하며, 완전히 독립적인 재실행 검증은 M5 Continuous Evals(독립 샌드박스 벤치마크)로 위임한다.

---

## 4. References & Traceability
- 선행 조사 보고서: [`docs/v2/research/m4-test-and-assurance.md`](../research/m4-test-and-assurance.md)
- 선행 아키텍처 결정: [ADR-0001 (Subagent Roles)](0001-initial-subagent-roles.md), [ADR-0007 (plan.md & SDD)](0007-plan-artifact-and-build-feedback-loop.md)
- 관련 이슈: [#125](https://github.com/taejung3852/OwnHands/issues/125), [#127](https://github.com/taejung3852/OwnHands/issues/127)

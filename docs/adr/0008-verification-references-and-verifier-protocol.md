# ADR-0008 — 검증 가이드라인 캡슐화 및 Verifier 감사 프로토콜

- **상태:** Accepted — 사용자 합의
- **일자:** 2026-09-19
- **관련 Issue:** [#127](https://github.com/taejung3852/OwnHands/issues/127) (선행: [#125 Research Gate](https://github.com/taejung3852/OwnHands/issues/125))
- **관련 PR:** [#126](https://github.com/taejung3852/OwnHands/pull/126), [#128](https://github.com/taejung3852/OwnHands/pull/128)

---

## 1. Context (배경 및 문제)

### 1.1 V1의 교훈: 배보다 배꼽이 더 커진 검증 시스템
- V1([project-journey.md](../story/project-journey.md))은 AI 에이전트의 환각과 허위 완료 선언을 막기 위해 검증 스펙, 베이스라인, 리뷰, 증거, 실시간 대시보드를 모두 코드로 직접 구축했다.
- 그러나 커스텀 러너 바이너리, 실시간 소켓/서버, 복잡한 파서 등 **검증 시스템 자체를 만들고 유지보수하는 부담이 실제 제품 개발보다 커지는 주객전도**를 겪었다.
- **V2의 절대 원칙 (Thin Harness / Zero-Code)**:
  - 거대한 독자 CLI 러너나 상시 모니터링 대시보드를 만들지 않는다.
  - 플랫폼(Codex)의 네이티브 도구(`npm test`, `pytest`, Subagent, Git diff) 위에 **가벼운 지침과 프로토콜**만 얹는다.

### 1.2 M3에서 M4로 넘어온 미결 과제
- V2-M3([ADR-0007](0007-plan-artifact-and-build-feedback-loop.md))를 통해 실행 계획인 `plan.md` 아티팩트와 SDD 기반 Build Feedback Loop 6대 원칙을 확정했다.
- 그러나 ADR-0007 원칙 5에 명시했듯이:
  > *"Verifier 런타임 권한 경계: 현재 `verifier.toml`은 `sandbox_mode = "read-only"`이므로... Verifier가 테스트를 직접 재실행하는 권한/환경 확정은 런타임 실측 후 M4(`Test & Assurance`)에서 다룬다."*
- 또한 검증 지식(회귀 방어, Before-After 측정 등)을 어디에 두어야 하는가의 문제가 남아 있었다. 초기에는 `docs/` 아래에 두는 안이 검토되었으나, **사람이 읽는 프로젝트 문서(`docs/`)와 에이전트 실행 지침이 뒤섞여 정리가 안 되는 부작용**이 지적되었다.

### 1.3 1차 자료 조사 결과 ([docs/research/m4-test-and-assurance.md](../research/m4-test-and-assurance.md))
1. **Fact 1 (Codex Progressive Disclosure)**:
   - Skill 카탈로그 예산은 10,000 토큰 천장이 존재하지만, Skill 디렉터리 내 `references/`에 둔 문서는 초기 카탈로그 예산을 소모하지 않는다.
2. **Fact 2 (Verifier read-only 런타임 제약 분석)**:
   - 현재 `verifier.toml`의 `sandbox_mode = "read-only"`는 파일시스템 쓰기(`workspace-write`)가 제한된다.
   - 많은 테스트 러너(`pytest`, `jest` 등)는 실행 시 캐시·임시 파일 쓰기를 시도하므로 `read-only` 환경에서 실패할 가능성이 높다. (단, 실제 재실행 여부는 미실측 상태로 명시)
3. **Fact 3 (Before-After Baseline 원칙의 가치)**:
   - 버그 수정이나 성능 개선 시 "코드를 건드리기 전 실패/측정 로그"를 확보하지 않으면, AI 에이전트가 "고쳤다/빨라졌다"고 거짓 주장을 하더라도 검증할 수 없다.

---

## 2. Decision (결정)

OwnHands는 V2-M4(`Test & Assurance`)의 핵심 규약으로 다음 **3대 아키텍처 결정**을 확정한다.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        V2-M4 검증 체계 흐름                            │
├────────────────────────────────────────────────────────────────────────┤
│ 1. 검증 가이드라인의 Skill 캡슐화                                      │
│    docs/를 어지럽히지 않고 .agents/skills/verify/references/ 에 보관   │
│                                                                        │
│ 2. Verifier Subagent developer_instructions 공식 내장                  │
│    read-only 환경에서 applicable Fresh Evidence ↔ spec.md AC 독립 감사 │
│    판정 어휘: PASS / FAIL / UNOBSERVED                                 │
│                                                                        │
│ 3. 비교 주장(Claim)별 Before-After Baseline 프로토콜                   │
│    버그/성능 개선 작업 시 코드 수정 전 결함/수치 기록 (미확보 시 UNOBSERVED) │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2.1 결정 1: 검증 가이드라인의 Skill 캡슐화 (Clean Architecture)

#### 1) 공간의 엄격한 분리
- **`docs/` (사람의 공간)**: 시스템 아키텍처(`adr/`), 작업 명세(`specs/`), 의사결정 기록(`decisions.md`), 로드맵(`roadmap.md`) 등 사람이 읽고 관리하는 문서만 보존한다. 에이전트의 일회성 행동 지침을 마구잡이로 늘어놓지 않는다.
- **`.agents/skills/` (에이전트의 공간)**: 구현자(Builder)가 검증을 수행할 때 참고하는 가이드라인은 **`.agents/skills/verify/references/`**에 온디맨드 마크다운으로 캡슐화한다.
  - `regression-defense.md`: 회귀 방어 원칙, 변경 영향 분석(Impact Analysis), 기존 테스트 부재 시 3대 대체 방어선
  - `before-after-baseline.md`: 결함 재현 로그 및 벤치마크 기준선 수집 절차
  - `evidence-guide.md`: 신선한 관측 증거(applicable Fresh Evidence) 작성 및 기록 가이드

#### 2) 점진적 공개 (Progressive Disclosure) & 분할 게이트 충족
- 검증 가이드는 Skill 목록의 10,000 토큰 천장을 먹지 않으며, `plan.md`를 작성하거나 검증 단계를 수행할 때만 해당 태스크에 맞추어 핀포인트로 열람된다.
- **새 Skill (`verify`) 분할 게이트 충족 확인**:
  - `Trigger`: 구현 완료 후 검증 (기획/설계인 `grill-spec`과 다름)
  - `Input`: `spec.md`, `plan.md`, 관측 증거 (Intent 및 코드베이스 조사와 다름)
  - `Success Criteria`: `PASS / FAIL / UNOBSERVED` 판정 (산출물 승인과 다름)
  - ➔ 3대 축이 모두 뚜렷하게 다르므로 독립 4번째 Skill로 정당화됨.

---

### 2.2 결정 2: Verifier Subagent `developer_instructions` 내장 및 독립 감사관 모델

#### 1) 메커니즘: Verifier 본령에 감사 프로토콜 직접 정의
- Verifier의 감사 절차는 외부 문서를 찾아 읽게 하는 불안정한 방식 대신, [`.codex/agents/verifier.toml`](../../.codex/agents/verifier.toml)의 **`developer_instructions`에 직접 내장**한다.
- Verifier Subagent([ADR-0001](0001-initial-subagent-roles.md))는 **직접 무거운 테스트를 재실행하는 Runner가 아니라, Builder가 제출한 적용 가능한 신선한 증거(applicable Fresh Evidence)를 `spec.md`의 AC와 역추적 대조하는 독립 감사관(Auditor)**으로 작동한다.

#### 2) AC ↔ Evidence 역추적 대조 및 3대 판정 어휘
- **유연한 매핑**: AC와 Evidence는 1:1 강제 매핑이 아니며, 1:N 또는 N:1 복합 매핑을 허용한다.
- **다양한 증거 유형 수용 (applicable Fresh Evidence)**:
  - Unit/API: 테스트 러너 실행 명령어, exit code 0, assertion 통과 건수
  - UI/Layout: 브라우저 렌더링 관측 기록, 레이아웃 스크린샷, DOM 상태
  - Lint/Static Analysis: 도구 실행 출력 (0 errors)
  - Performance: 사전/사후 벤치마크 측정 수치
  - Manual/Exploratory: 재현 절차에 따른 구체적 관측 기록
  *(Git 커밋 해시는 uncommitted 작업 중일 수 있으므로 유용한 provenance로 활용하며 필수 차단 요건으로 삼지 않음)*

| 판정 어휘 | 판정 조건 | 후속 조치 |
|---|---|---|
| **`PASS`** | 제출된 applicable Fresh Evidence(테스트 통과, UI 렌더링 스크린샷, 벤치마크 수치, 무에러 출력 등)가 `spec.md`의 해당 AC를 충분히 입증할 때 | 검증 통과 완료 |
| **`FAIL`** | 실행 결과 에러, assertion 실패, AC 기대 동작 불일치, 또는 증거 위조/조작 정황이 발견될 때 | Builder에게 결함 피드백 및 재작업 |
| **`UNOBSERVED`** | 해당 AC에 대한 실행 증거가 누락되었거나, 테스트 부재 등으로 실제 관측되지 않은 상태 | 거짓 통과(Silent Pass) 방지, 미관측 사실 명시 |

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
| **신규 기능 (`feature`)** | Before 불필요 (기존 동작이 없으므로 N/A) | `spec.md`의 AC에 대한 applicable Fresh Evidence (단위 테스트 통과, 렌더링 스크린샷 등) | N/A (AC 검증 결과에 따라 PASS/FAIL) |
| **리팩토링 (`refactor`)** | 코드 수정 전 **기존 회귀 테스트 통과 로그** | 동일한 회귀 테스트의 **동일 통과 로그** 및 무결성 확인 | 기존 테스트 부재 시 `[NO_EXISTING_REGRESSION_SUITE]` 선언 |

#### 3) Before 증거 미확보 시의 `UNOBSERVED` 처리 원칙
- 에이전트가 버그 수정이나 성능 개선을 수행하면서 Before 재현 증거를 남기지 않고 코드를 고친 경우:
  - **원칙**: "에이전트의 주관적 주장(Self-Claim)은 완료의 근거가 될 수 없다."
  - Verifier는 해당 변경을 임의로 PASS 시켜주지 않으며, 반드시 `[UNOBSERVED]` 플래그를 부여한다.
  - 이를 통해 PR 리뷰어와 사람이 "이 작업은 사전에 결함이 명확히 입증되지 않은 채 코드만 변경되었음"을 인지하고 추가 검증을 요구할 수 있게 한다.

---

## 3. Consequences (결과 및 트레이드오프)

### 3.1 긍정적 효과
1. **Zero-Code & Clean Structure**:
   - `docs/`는 사람이 보는 시스템 설계 공간으로 깔끔하게 유지되고, 에이전트 지침은 Skill 및 Subagent toml에 명확히 캡슐화된다.
2. **AI 자가합리화의 원천 차단**:
   - Before 재현 증거 없는 버그픽스 주장, applicable Fresh Evidence 없는 완료 선언을 시스템적으로 걸러낸다.
3. **토큰 및 속도 효율 극대화**:
   - 상황별 Reference는 필요할 때만 핀포인트로 읽히므로(Progressive Disclosure) 카탈로그 예산을 낭비하지 않는다.
   - Verifier가 중복 빌드/테스트를 돌리지 않고 감사에 집중하므로 피드백 루프 속도가 빠르다.

### 3.2 트레이드오프 및 관리 비용
1. **작업 초기 공수 증가**:
   - 버그를 고치기 전에 실패 로그를 먼저 따고 기록해야 하므로, "코드부터 고치고 싶은" 충동을 억제해야 하는 개발 규율이 요구된다.
2. **환각된 증거(Spoofed Logs)의 잠재적 리스크**:
   - Verifier가 터미널을 직접 재실행하지 않고 출력을 감사하므로, 에이전트가 터미널 출력을 완벽히 날조하여 작성할 경우 감지하지 못할 수 있다.
   - ⚠️ **완화책**: 커밋 해시, exit code, assertion 카운트의 교차 대조를 수행하며, 완전히 독립적인 재실행 검증은 M5 Continuous Evals(독립 샌드박스 벤치마크)로 위임한다.

---

## 4. References & Traceability
- 선행 조사 보고서: [`docs/research/m4-test-and-assurance.md`](../research/m4-test-and-assurance.md)
- 선행 아키텍처 결정: [ADR-0001 (Subagent Roles)](0001-initial-subagent-roles.md), [ADR-0007 (plan.md & SDD)](0007-plan-artifact-and-build-feedback-loop.md)
- 관련 이슈: [#125](https://github.com/taejung3852/OwnHands/issues/125), [#127](https://github.com/taejung3852/OwnHands/issues/127)

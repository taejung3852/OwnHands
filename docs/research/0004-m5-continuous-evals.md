# V2-M5 Research: Continuous Evals 체계 확장 및 Task Set 설계

- **작성 주체**: AI 에이전트 분석 (사람 검토 및 결정 대상)
- **일자**: 2026-09-19
- **관련 마일스톤 및 이슈**: [V2-M5 — Continuous Evals](https://github.com/taejung3852/OwnHands/milestone/18), [#131](https://github.com/taejung3852/OwnHands/issues/131), [#106](https://github.com/taejung3852/OwnHands/issues/106)
- **선행 연구 및 아티팩트**:
  - [`docs/references/anthropic-playbook.md`](../references/anthropic-playbook.md) (§5 Continuous Evals)
  - [`docs/evals/README.md`](../evals/README.md) (초기 작은 Eval 0001~0005)
  - [`docs/decisions.md`](../decisions.md) (§6 Eval 도입 방식)

---

## 1. 연구 목적 및 최상위 목표 (GORE Anchor)

### 1.1 해결하려는 문제
- **수작업 평가의 지속 불가능성**: M1부터 M4까지 축적한 5건의 Eval(`0001`~`0005`)은 모두 대화 세션 내에서 사람이 프롬프트를 직접 입력하고 결과를 마크다운 파일에 수동 기록한 "정적 실측/수작업 세션"이었다.
- **침묵하는 회귀(Silent Regression)의 위험**: `AGENTS.md`의 시스템 지침, 4대 스킬 프롬프트, 3대 서브에이전트 설정이 변경되었을 때, 이전에 잘 작동하던 라우팅, 독립 감사, Before 기준선 수집 등의 규칙이 몰래 깨지는 현상을 즉시 감지하기 어렵다.

### 1.2 최상위 목표 (Top-down Goal)
> **"에이전트 시스템 자산(지침·스킬·서브에이전트)이 수정되었을 때, 수작업 세션 반복 없이 품질 회귀를 반복 가능하게 감지하는 경량 Continuous Evals 체계의 청사진을 수립한다."**
> *(참고: 1분 이내 실행 등 구체적인 실행 시간 상한선은 향후 러너 구현 시 검토할 후보 지표로 다루며, 최상위 목표에 조기 고정하지 않는다.)*

### 1.3 비목표 (Non-goals)
- 범용 LLM 벤치마크(MMLU, HumanEval 등)나 여러 외부 파운데이션 모델 간의 성능 비교 플랫폼 구축 배제.
- 복잡하고 무거운 대규모 CI 파이프라인 강제 및 PR 무조건 차단(Hard Block) 게이트 도입 배제 (현재는 1인 개발 맥락에 맞춘 로컬 검증 중심).

---

## 2. 1차 자료 분석: Anthropic SDLC Playbook §5

### 2.1 공식 원문 내용
- 출처: Anthropic AI-Native SDLC Playbook (<https://claude.com/blog/the-ai-native-sdlc-playbook>)
- **핵심 원칙**:
  1. *두 축의 엄격한 분리*: "제품의 동작 검증(Product Verification)"과 "에이전트 시스템 자체의 평가(System Evals)"는 서로 다른 책임이다. 제품은 PR 리뷰와 테스트로 검증하고, 시스템 변경(지침, 스킬, 프롬프트)은 Eval로 검증한다.
  2. *설정 변경 시 자동 트리거*: 에이전트 구성 자산이 변경될 때마다 평가를 실행하여 동일한 품질 기준을 유지한다.
  3. *실제 과제 기반(Ground in Real Tasks)*: 인위적으로 꾸며낸 문제가 아닌, 기대 결과가 명확한 실제 일상 과제로 구성한다.
  4. *운영 장애의 영구 편입*: 현장에서 발생한 에이전트 실패 사례를 영구 Task Set으로 추가하여 재발을 방지한다.

### 2.2 공식 내용 vs OwnHands 자체 결정의 경계 (AGENTS.md 준수)
- **공식 원문의 내용**: 에이전트 설정 변경 시 평가를 트리거하고, 실제 과제로 구성하며, 두 축을 분리한다는 일반적 원칙.
- **우리의 독자적 결정**:
  - 대규모 인프라 대신 M1~M4 동안 실제 축적한 **5대 작은 Eval을 버전 관리되는 최소 Task Set으로 승격**시킨다.
  - 원문이 제시한 예시 수치(통과율 임계값)나 CI merge 차단을 무조건 의무화하지 않고, **변경 전후 비교(Baseline Delta)와 3-State 편향 감지**를 핵심 지표로 삼는다.

---

## 3. M1~M4 축적 Eval 5종의 구조 분석 및 공통 인터페이스 도출

현재 저장소에 존재하는 5대 Eval을 머신 판독 가능한 구조체로 분해하면 다음과 같다:

| Eval ID | 검증 대상 | 입력 (Input) | 기대 계약 (Expected Contract) | 판정 방식 | 부작용 방지 제약 |
|:---:|:---|:---|:---|:---|:---|
| **0001** | 스킬 라우팅 | 5대 대표 일상 프롬프트 | 올바른 Skill 이름 호출 매칭 | 결정론적 일치 (Exact Match) | 실제 이슈/PR 생성 0건 |
| **0002** | Verifier 서브에이전트 | 수용성 기준 및 파일 경로 | Read-only 모드 유지, 3-State 표 출력 | 계약 대조 (Schema Match) | 코드 임의 수정 0건 |
| **0003** | Researcher 서브에이전트 | 1차 자료 문서 및 질문 | 1차 출처 URL 인용, 팩트/갭 엄격 분리 | 정적 텍스트 분석 (URL & Header) | 기존 파일 무단 변조 0건 |
| **0004** | grill-spec 스킬 | 신규 기능 요구사항 | GORE 닻, 8단계 프로토콜, 체크포인트 | 정적 파일 및 필수 섹션 검증 | 승인 전 Build 직행 차단 |
| **0005** | verify & Verifier 감사 | 실제 spec AC 7개 + Fresh Evidence | AC별 역추적, Before 입증책임, 1:N 매핑 | 3-State 판정 (`PASS/FAIL/UNOBSERVED`) | 임의 PARTIAL PASS 배제, Mutation 0건 |

### 공통 Task 스키마 추출
```yaml
# 공통 Task Set 항목 추상화 모델 (후보)
task_id: "EVAL-0001-ROUTING-01"
name: "버그 신고 프롬프트의 라우팅 검증"
target_asset: ".agents/skills/"
input:
  prompt: "로그인 버튼을 눌렀을 때 500 에러가 발생합니다."
expected:
  route_skill: "write-issue-pr"
  forbidden_actions: ["run_command:gh issue create"]
judgment_mode: "deterministic" # deterministic | schema | auditor
```

---

## 4. M5 핵심 아키텍처 설계 후보 및 트레이드오프

### 4.1 결정 후보 1: Task Set 스키마 및 저장 위치

| 후보 방안 | 구조 및 형식 | 장점 | 단점 / 트레이드오프 |
|---|---|---|---|
| **후보 A: 개별 YAML/JSON 태스크 분리** | `docs/evals/tasks/*.yaml` | 과제별 독립 추가/삭제 용이, Git 충돌 최소화 | 파일 수가 늘어나 관리 오버헤드 발생 |
| **후보 B: 단일 통합 Task Set 파일** (권장) | `docs/evals/task-set.yaml` | 전체 과제 한눈에 조망 가능, 러너 파싱 단순 | 여러 PR이 동시에 과제를 추가할 때 머지 충돌 가능성 |
| **후보 C: 마크다운 Frontmatter 확장** | `docs/evals/0001-*.md`에 YAML 메타데이터 내장 | 기존 마크다운 문서 보존, 사람과 기계 동시 지원 | 문서가 길어져 파서 복잡도 증가, 러너 실행 지연 |

* **잠정 권장**: **후보 B (단일 `task-set.yaml`)**. 현재 축적 과제가 5~10개 내외이므로 하나의 선언형 YAML로 관리하는 것이 가장 직관적이며 가볍다. 과제가 30개 이상으로 커질 때 후보 A로 분할 검토.

---

### 4.2 결정 후보 2: 비대화형 Dry-run 자동 러너 (Execution Harness)

대화 세션 없이 에이전트를 안전하게 비대화형으로 실행하고 채점하는 방식의 후보:

| 후보 방안 | 구동 메커니즘 | 안전장치 (Sandboxing) | 장단점 |
|---|---|---|---|
| **후보 A: 경량 Node.js/Python 검증 러너** (권장) | 스크립트가 지침/스킬 파일을 파싱하여 정적 정합성 및 프롬프트-입력 매핑을 일괄 채점 | 실제 LLM 호출 전 정적 계약을 0.5초 만에 사전 검증 | 비용 0원, 초고속 회귀 감지 가능. 단, 복잡한 생성 추론 검증 한계 |
| **후보 B: Codex CLI Headless 구동** | `codex exec --sandbox read-only` 명령어로 서브프로세스 실행 | 공식 read-only sandbox + 최소 권한 + 외부 부작용 없는 평가 과제 설계 (필요 시 OwnHands 격리 환경 연계) | 실제 에이전트 런타임 검증 가능. 단, Codex 실행 환경/토큰 의존성 발생 |
| **후보 C: 세션 내 수동 가이드 유지** | 별도 스크립트 없이 `verify` 스킬에서 Eval 5종 순차 실행 | 추가 개발 비용 0 | 자동화가 되지 않아 사람이 매번 세션을 소모해야 함 |

> ⚠️ **공식 기능과 자체 설계 구분 (AGENTS.md 준수)**:  
> Codex 공식 문서상 `codex exec`은 비대화형 실행을 지원하고 기본적으로 `read-only sandbox`를 제공하며 `--sandbox read-only` 옵션이 유효합니다. 그러나 일반 `codex exec`에 generic `--dry-run` 플래그는 공식으로 확인되지 않습니다. 따라서 부작용 없는 안전한 평가는 공식 **read-only sandbox**를 활용하되, 네트워크/API 부작용 차단은 **OwnHands가 스크립트 레벨에서 모킹/격리하는 자체 Dry-run 평가 환경**으로 명확히 구분하여 설계합니다.

* **잠정 권장**: **후보 A(정적/계약 기반 빠른 러너)를 기본 탑재**하고, 정밀 검증이 필요할 때 **후보 B를 온디맨드로 연동**하는 단계적 하이브리드 접근.

---

### 4.3 결정 후보 3: 회귀 감지 및 Baseline 채점 프로토콜 (Metrics)

| 지표 방식 | 측정 및 판정 알고리즘 | 특징 및 위험 |
|---|---|---|
| **방식 1: 단순 통과율 (Pass Rate %)** | `(PASS 수 / 전체 과제 수) * 100` | 직관적이나, 치명적인 단일 회귀(예: read-only 탈취)가 통과율에 묻힐 위험 |
| **방식 2: 3-State Delta Matrix** (권장) | 이전 Baseline 스냅샷과 개별 태스크별 상태 전이 추적<br>(`PASS ➔ UNOBSERVED` 또는 `PASS ➔ FAIL` 발생 시 즉시 REGRESSION 경고) | **Dijkstra 원칙 준수**. 합격률 환치를 거부하고 특정 지침 수정으로 인해 깨진 지점을 1:1로 핀포인트 추적 |
| **방식 3: 비용/토큰 상한선 (Budget Guard)** | 태스크당 토큰 소모량 상한선(예: 4,000 토큰 초과 시 경고) | 지침이 과도하게 비대해지는 프롬프트 인플레이션 방지 |

* **잠정 권장**: **방식 2 (3-State Delta Matrix) + 방식 3의 프롬프트 줄 수 상한선 연계**. 단순 점수가 아니라 "어느 지침이 깨졌는가"를 보여주는 것이 엔지니어에게 실질적 도움이 됨.

---

## 5. 남겨둔 결정 사항 (ADR-0009에서 확정할 의제)

1. **Task Set 포맷 확정**: `docs/evals/task-set.yaml`의 표준 스키마 필드 확정 (`id`, `category`, `prompt`, `expected_contract`).
2. **1차 러너 구현 범위**: `scripts/run-evals.js` (또는 python)를 통한 5대 Eval 정적/계약 자동 검증 러너의 1차 구현.
3. **Baseline 스냅샷 저장소**: `docs/evals/baselines/current.json` 형태의 기준선 보관 규칙.

---

## 6. 요약 및 권장 로드맵

1. **Step ① (본 조사)**: `docs/research/0004-m5-continuous-evals.md`를 통해 5대 Eval 분석 및 Task Set/러너 아키텍처 후보 정리 완료.
2. **Step ② (설계 및 ADR-0009 제정)**: 사용자와 위 3대 결정 의제를 합의하고 `ADR-0009`를 Proposed 상태로 제정.
3. **Step ③ (Task Set & 1차 러너 구현)**: `docs/evals/task-set.yaml` 작성 및 1차 비대화형 러너 스크립트 구현, 실제 회귀 실측 검증.

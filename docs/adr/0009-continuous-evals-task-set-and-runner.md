# ADR-0009 — Continuous Evals Task Set 규격 및 경량 러너 아키텍처

- **상태:** Accepted — 2026-09-19 사용자 승인
- **일자:** 2026-09-19
- **관련 Issue:** [#134](https://github.com/taejung3852/OwnHands/issues/134) (선행: [#131 Research Gate](https://github.com/taejung3852/OwnHands/issues/131))
- **관련 리서치:** [`docs/research/0004-m5-continuous-evals.md`](../research/0004-m5-continuous-evals.md)

---

## 1. Context (배경 및 문제)

### 1.1 V1의 교훈: 과도한 평가 인프라 구축의 주객전도 방지
- V1([project-journey.md](../story/project-journey.md))에서는 자체 평가 러너, 실시간 소켓/서버, 복잡한 파서 등 평가 시스템 자체를 개발하는 데 막대한 공수를 투입했다가 유지보수 실패를 겪었다.
- **V2의 절대 원칙 (Thin Harness / Zero-Code)**:
  - 대규모 LLM 벤치마크나 복잡한 분산 평가 플랫폼을 만들지 않는다.
  - 저장소에 존재하는 네이티브 스크립트와 선언형 설정 위에 **가장 얇고 가벼운 회귀 감지 안전장치**만 얹는다.

### 1.2 M1-M4에서 축적된 초기 Eval의 한계
- V2 초기(M1-M4) 동안 축적된 5대 Eval([docs/evals/README.md](../evals/README.md))은 모두 대화 세션 내에서 사람이 직접 프롬프트를 입력하고 눈으로 확인하여 기록한 **수작업 실측**이었다.
- 만약 에이전트 지침(`AGENTS.md`), 스킬 프롬프트, 서브에이전트 정의가 수정될 때마다 사람이 매번 5대 과제를 대화창에서 수동 반복하는 것은 불가능하다.
- 따라서 지침 수정 후 이전에 잘 동작하던 기능이 몰래 깨지는 **침묵하는 회귀(Silent Regression)**를 안정적으로 잡아내기 위한 체계화가 필요하다.

### 1.3 1차 자료 조사 결과 ([docs/research/0004-m5-continuous-evals.md](../research/0004-m5-continuous-evals.md))
1. **Anthropic SDLC Playbook §5 대응**:
   - "제품의 동작 검증(Review/Testing)"과 "에이전트 시스템 자체의 평가(System Evals)"는 서로 다른 책임의 두 축이다.
   - 에이전트 구성 자산(지침, 스킬, 서브에이전트)이 바뀔 때마다 평가를 트리거하여 동일한 기준을 유지한다.
2. **실제 과제 기반 Task Set 승격**:
   - 인위적인 가상 문제가 아니라, M1-M4 동안 검증된 5대 실제 사례(`0001`-`0005`)를 기계 판독 가능한 표준 과제로 승격시킨다.
3. **공식 기능과 자체 설계의 엄격한 분리 (AGENTS.md 준수)**:
   - Codex 공식 `codex exec`은 비대화형 실행 및 `--sandbox read-only`를 지원하나, generic `--dry-run` 플래그는 부재하다.
   - 따라서 부작용 차단은 공식 read-only sandbox와 함께 **OwnHands가 스크립트 레벨에서 모킹/격리하는 자체 Dry-run 평가 환경**으로 설계한다.

---

## 2. Decision (결정)

OwnHands는 V2-M5(`Continuous Evals`)의 핵심 규약으로 다음 **3대 아키텍처 결정을 채택한다.**

```text
┌────────────────────────────────────────────────────────────────────────┐
│                     V2-M5 Continuous Evals 체계 (확정)                 │
├────────────────────────────────────────────────────────────────────────┤
│ 1. 단일 선언형 Task Set 표준 스키마 (execution_mode & sandbox_mode 구분)│
│    docs/evals/task-set.yaml 에 5대 축적 과제를 정적/런타임/복합으로 완전 수용│
│                                                                        │
│ 2. Eval Orchestrator (Static Preflight + Runtime Execution 러너)       │
│    scripts/run-evals.js 로 빠른 정적 Preflight 우선 실행 후,            │
│    실제 행동 평가는 sandbox_mode(read-only / isolated-write) 격리 구동  │
│                                                                        │
│ 3. 3-State Delta Matrix 기반 회귀 감지 및 Baseline 스냅샷              │
│    단순 합격률(%) 착시 배제, 개별 태스크 전이(PASS ➔ UNOBSERVED/FAIL) 핀포인트 추적│
│    docs/evals/baselines/current.json 기준선 관리                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2.1 결정 1: 단일 선언형 Task Set 규격 (`docs/evals/task-set.yaml`)

#### 1) 단일 통합 파일 채택 이유
- 과제별로 수십 개의 YAML/JSON 파일을 쪼개면 디렉터리 오버헤드가 발생한다.
- 현재 축적된 과제가 5-10개 내외이므로, 하나의 선언형 `task-set.yaml` 파일로 전체 평가 셋을 조망하고 Git diff를 추적하는 것이 가장 가볍고 직관적이다. (향후 과제가 30개 이상으로 비대해질 때 분할 검토)

#### 2) "지침 존재 ≠ 실제 동작 관측" 원칙을 보장하는 Task Set 표준 스키마
기존 Eval 0001-0005의 검증 로직을 완전하게 수용하기 위해, 정적 문서 검사와 실제 에이전트 행동 관측을 구분하는 **`execution_mode: static | runtime | composite`**, 샌드박스 정책 **`sandbox_mode: read-only | isolated-write`**, 그리고 세분화된 **`side_effect_policy`** 필드를 필수화한다:

```yaml
version: "1.0"
tasks:
  - id: "EVAL-0001"
    name: "Daily Prompt Skill 라우팅 정확도 실측"
    category: "routing"
    target_asset: ".agents/skills/"
    execution_mode: "runtime" # 실제 일상 프롬프트 투입 후 라우팅 행동 관측
    sandbox_mode: "read-only"
    side_effect_policy:
      allow_repo_mutation: false
      allow_artifact_output: false # 세션 인라인 초안(Draft)만 허용
      allow_network_writes: false
      forbidden_commands: ["gh issue create", "gh pr create"]
    input:
      scenarios:
        - id: "P1"
          prompt: "이슈 하나 만들어줘. 목표는 V2 캐시 무효화 설계야"
          expected_skill: "write-issue-pr"
          expected_behavior: "이슈 본문 초안 작성 (gh issue create 미실행)"
        - id: "P2"
          prompt: "PR 본문 다시 써줘"
          expected_skill: "write-issue-pr"
          expected_behavior: "3칸 Human Brief + 접힌 상세 초안 작성"
        - id: "P3"
          prompt: "지금 우리 상황 정리해줘"
          expected_skill: "explain"
          expected_behavior: "ELI5 다이어그램 + 비유 + 접힌 기술 전제 구조 산출"
        - id: "P4"
          prompt: "이 함수 뭐하는지 설명해줘"
          expected_skill: null # 스킬 미호출 (인라인 일반 설명으로 False Positive 방지)
          expected_behavior: "일반 코드 인라인 설명 제공"
        - id: "P5"
          prompt: "이 에러 왜 나는지 봐줘"
          expected_skill: null # 스킬 미호출 (인라인 일반 디버깅으로 False Positive 방지)
          expected_behavior: "일반 디버깅 및 원인 분석 제공"
    expected_contract:
      route_accuracy: "5/5 (100%)"
      false_positive_count: 0
      false_negative_count: 0
      side_effect_violation: 0
    judgment_mode: "deterministic"

  - id: "EVAL-0002"
    name: "Verifier 독립 감사관 수용성 및 불변성 실측"
    category: "subagent"
    target_asset: ".codex/agents/verifier.toml"
    execution_mode: "runtime" # 실제 verifier 프롬프트 구동 및 판정 출력 관측
    sandbox_mode: "read-only"
    side_effect_policy:
      allow_repo_mutation: false
      allow_artifact_output: false
      allow_network_writes: false
    input:
      evaluation_subject: "docs/adr/0001-initial-subagent-roles.md 및 .codex/agents/*.toml 4대 AC"
    expected_contract:
      acceptance_criteria:
        - id: "AC-1"
          desc: "서브에이전트 3종 정의 파일 존재"
          expected: "PASS"
        - id: "AC-2"
          desc: "verifier/reviewer의 sandbox_mode read-only 선언"
          expected: "PASS"
        - id: "AC-3"
          desc: "docs/decisions.md 반영"
          expected: "PASS"
        - id: "AC-4"
          desc: "ADR-0001에 read-only 한계 명시"
          expected: "PASS"
      zero_repo_mutation: true
      valid_vocabulary: ["PASS", "FAIL", "UNOBSERVED"]
      strictly_forbidden_vocabulary: ["PARTIAL PASS"]
    judgment_mode: "auditor"

  - id: "EVAL-0003"
    name: "Researcher 1차 출처 인용 및 팩트/공백 분리 실측"
    category: "subagent"
    target_asset: ".codex/agents/researcher.toml"
    execution_mode: "runtime" # 실제 조사 보고서 생성 산출물 검증
    sandbox_mode: "isolated-write" # 지정된 조사 보고서 1건 생성 허용, 기존 파일 수정 금지
    side_effect_policy:
      allow_repo_mutation: false # 기존 소스 코드 및 문서 임의 수정 0건
      allow_artifact_output: true # docs/research/... 지정 조사 보고서 1건 신규 생성 허용
      allow_network_writes: false
    input:
      query: "V2-M2 Research Gate 1차 자료 조사"
      primary_sources:
        - "docs/references/anthropic-playbook.md"
        - "docs/references/codex-official.md"
      target_output_file: "docs/research/0002-m2-intent-spec-gate.md"
    expected_contract:
      require_primary_source_url: true
      require_gap_separation: true
      existing_files_mutated: 0
      created_files_count: 1
    judgment_mode: "schema"

  - id: "EVAL-0004"
    name: "grill-spec GORE 닻 및 정적 적합성 (Static Conformance)"
    category: "skill"
    target_asset: ".agents/skills/grill-spec/"
    execution_mode: "static" # 스킬 정의, references, 라이선스 정적 계약 검증
    sandbox_mode: "read-only"
    side_effect_policy:
      allow_repo_mutation: false
      allow_artifact_output: false
      allow_network_writes: false
    expected_contract:
      static_checks:
        - id: "E1"
          desc: "SKILL.md 및 interview-guide.md 구조, name, MIT License attribution"
        - id: "E2"
          desc: "일반 작업 ROUTE-B 기본, 대형 과제 ROUTE-C(Wayfinder) 경계"
        - id: "E3"
          desc: "Fact(Agent) vs Decision(User) 분리 지침"
        - id: "E4"
          desc: "Artifact Traceability Intent 헤더 및 REQ 매핑"
        - id: "E5"
          desc: "Human Checkpoint 1, 2 Default Barrier 규약"
        - id: "E6"
          desc: "Fallback 인터뷰 계약 구비"
        - id: "E7"
          desc: "M2 산출물 4대 필수 필드 규격 정합성"
    judgment_mode: "schema"

  - id: "EVAL-0005"
    name: "verify 스킬 분할 및 Verifier 독립 감사 프로토콜 실측"
    category: "composite" # 정적 분할 구조 점검 + 런타임 독립 감사 2단계 복합 과제
    execution_mode: "composite"
    target_asset: ".agents/skills/verify/"
    phases:
      - phase: "static_conformance"
        sandbox_mode: "read-only"
        side_effect_policy:
          allow_repo_mutation: false
          allow_artifact_output: false
        expected_contract:
          skill_main_lines_max: 35
          references_split: ["before-after-baseline.md", "regression-defense.md", "evidence-guide.md"]
          verifier_instructions_rules: 5 # Read-only, Evidence Audit, 3-State, Before Baseline, Output Contract
          flexible_traceability: "1:N / N:1"

      - phase: "runtime_audit"
        sandbox_mode: "read-only"
        side_effect_policy:
          allow_repo_mutation: false
          allow_artifact_output: false
          allow_network_writes: false
        input:
          spec_file: "docs/specs/grill-spec/spec.md" # Section 4 (AC 7개)
          fresh_evidence:
            - id: "E1"
              content: "test -f SKILL.md && interview-guide.md exit 0"
            - id: "E2"
              content: "grep -n 'name: grill-spec' L2"
            - id: "E3"
              content: "grep -n 'MIT License' L80"
            - id: "E4"
              content: "test -f docs/evals/0004-skill-grill-spec.md exit 0"
        expected_contract:
          row_judgments:
            criterion_1: "PASS" # E1 + E2 + E3 복합 입증 (1:N 유연 추적성)
            criterion_2: "UNOBSERVED" # 런타임 대화 로그 미제출
            criterion_3: "UNOBSERVED" # 지침 존재 != 동작 관측
            criterion_4: "UNOBSERVED" # 개별 REQ 매핑 증거 미제출
            criterion_5: "UNOBSERVED" # 승인 상호작용 로그 미제출
            criterion_6: "UNOBSERVED" # fallback 관측 미제출
            criterion_7: "PASS" # E4 exit 0 실측
          overall_verdict: "UNOBSERVED"
          strictly_forbidden_vocabulary: ["PARTIAL PASS"]
          zero_repo_mutation: true
    judgment_mode: "auditor"
```

---

### 2.2 결정 2: 1차 러너 아키텍처 (`scripts/run-evals.js` + Codex Headless)

#### 1) 러너의 역할: Eval Orchestrator + Static Preflight + Runtime Execution
- 러너 스크립트(`scripts/run-evals.js`)를 단순 정적 파일 파서로 축소하지 않고, **전체 평가 세트를 조율하는 Orchestrator**로 제안한다.
- **다단계 실행 파이프라인**:
  1. **1단계 (Static Preflight)**: 빠른 정적 사전 검사로 설정 파일 문법, 스킬 frontmatter, 필수 파일 존재, 금지 어휘를 외부 LLM 호출 없이 검증. (`execution_mode: static` 및 `composite`의 정적 단계)
  2. **2단계 (Runtime Execution)**:
     - `sandbox_mode: read-only` 과제: `codex exec --sandbox read-only` 비대화형 구동으로 파일 쓰기 권한 원천 차단.
     - `sandbox_mode: isolated-write` 과제 (예: EVAL-0003 조사 보고서 생성): 지정된 산출물 디렉터리 외 기존 소스코드 수정을 차단·감사하는 격리 환경으로 구동.
  3. **3단계 (Judge & Delta Matrix)**: 수집된 실제 결과를 기대 계약과 대조하여 `PASS / FAIL / UNOBSERVED`를 판정하고 기준선(Baseline)과의 차이를 리포트.

#### 2) 자체 Dry-run 평가 환경과 Codex Headless 연계
- **공식 read-only 샌드박스**: Codex 공식 기능인 `codex exec --sandbox read-only`를 기반으로 실행하여 파일시스템 쓰기 권한을 원천 차단한다.
- **자체 Dry-run 평가 환경 (AGENTS.md 준수)**: Codex 공식 CLI에 generic `--dry-run` 플래그는 부재하므로, 외부 GitHub 이슈/PR 무단 생성 차단은 **OwnHands 러너가 스크립트 및 모킹 레벨에서 격리하는 자체 평가 환경**으로 설계한다.
- **실행 시간 목표 (후보 지표)**:
  - 정적 Preflight 목표: 1초 미만 (실제 시간은 Step ③ 러너 구현 시 실측하여 기록).
  - 런타임 실행: 비대화형 백그라운드 구동.

---

### 2.3 결정 3: 3-State Delta Matrix 기반 회귀 감지 및 Baseline 관리

#### 1) 단순 통과율(Pass Rate %)의 위험 배제
- 5개 과제 중 통과율이 80%(4/5)라는 수치는 "어느 기능이 깨졌는지"를 알려주지 못한다. 만약 실패한 1건이 핵심 안전장치인 `read-only` 불변성이었다면, 80%라는 수치는 위험을 은폐하는 착시가 된다.

#### 2) 3-State Delta Matrix 판정 원칙
- 모든 과제는 개별적으로 `PASS`, `FAIL`, `UNOBSERVED` 상태를 갖는다.
- 이전 기준선(Baseline)과 비교하여 다음 전이가 발생하면 즉시 **회귀 경고(REGRESSION)**를 발생시킨다:
  1. `PASS ➔ FAIL`: 이전에 정상 동작하던 계약이 에러를 냄.
  2. `PASS ➔ UNOBSERVED`: 이전에 수집되던 필수 증거가 누락되거나 지침이 생략됨.
  3. `새로운 상태 어휘 출현`: `PARTIAL PASS` 등 미승인 상태가 등장함.

#### 3) Baseline 스냅샷 저장소
- 경로: `docs/evals/baselines/current.json`
- 형식:
```json
{
  "baseline_commit": "4e34191",
  "generated_at": "2026-09-19T16:30:00Z",
  "results": {
    "EVAL-0001": "PASS",
    "EVAL-0002": "PASS",
    "EVAL-0003": "PASS",
    "EVAL-0004": "PASS",
    "EVAL-0005": "UNOBSERVED"
  }
}
```

---

## 3. Status & Consequences (상태 및 결과)

### 3.1 긍정적 효과
1. **빠른 사전 회귀 감지**: 지침이나 스킬을 수정한 개발자가 커밋 전 정적 사전 검사(Preflight)로 핵심 계약 파괴 여부를 빠르게 1차 감지할 수 있다.
2. **합격률 착시 차단**: 3-State Delta Matrix를 통해 어느 지침이 어떻게 깨졌는지 핀포인트로 드러난다.
3. **경량 하네스 (Thin Harness)**: 별도의 복잡한 외부 평가 플랫폼 없이 저장소 내 표준 Node.js 러너와 Codex CLI 연동만으로 완결된다.

### 3.2 트레이드오프 및 주의사항
1. **정적 검증과 생성 추론의 경계**:
   - 1차 스크립트 러너는 결정론적/계약 중심 검증에 집중한다.
   - 모델의 미묘한 자연어 생성 뉘앙스 검증은 Codex headless 또는 세션 내 대화형 실측과 상호 보완하여 운영한다.
2. **동일 캐시 재탕 금지**:
   - Baseline 비교 시 이전 캐시 조회를 새로운 독립 실행으로 계산하지 않는다.

---

## 4. References & Traceability

- [V2-M5 Step ① 조사 문서](../research/0004-m5-continuous-evals.md)
- [V2 연속 평가 체계 가이드](../evals/README.md)
- [결정 상태표](../decisions.md)
- [Anthropic Playbook 대응표](../references/anthropic-playbook.md) (§5 Continuous Evals)

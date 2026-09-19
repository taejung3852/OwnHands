# ADR-0009 — Continuous Evals Task Set 규격 및 경량 러너 아키텍처

- **상태:** Proposed — 검토 대기
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

OwnHands는 V2-M5(`Continuous Evals`)의 핵심 규약으로 다음 **3대 아키텍처 결정**을 채택한다.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                     V2-M5 Continuous Evals 체계                        │
├────────────────────────────────────────────────────────────────────────┤
│ 1. 단일 선언형 Task Set 표준 스키마                                    │
│    docs/evals/task-set.yaml 에 5대 축적 과제 및 계약 통합 버전 관리     │
│                                                                        │
│ 2. 1차 경량 비대화형 러너 & 자체 Dry-run 환경                          │
│    scripts/run-evals.js 로 지침·스킬 정적/계약 검증 (0.5초, 비용 0원)  │
│    (정밀 추론 검증은 codex exec --sandbox read-only 온디맨드 연동)    │
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

#### 2) Task Set 표준 스키마
```yaml
version: "1.0"
tasks:
  - id: "EVAL-0001"
    name: "Skill 프롬프트 라우팅 정확도"
    category: "routing"
    target_asset: ".agents/skills/"
    input:
      prompt: "5대 일상 프롬프트 (버그 신고, 현황 요약, 코드 리뷰 등)"
    expected_contract:
      route_matches:
        - input_contains: "이슈"
          expected_skill: "write-issue-pr"
        - input_contains: "설명"
          expected_skill: "explain"
      forbidden_actions:
        - "gh issue create"
        - "gh pr create"
    judgment_mode: "deterministic" # deterministic | schema | auditor

  - id: "EVAL-0002"
    name: "Verifier 독립 감사관 수용성 및 불변성"
    category: "subagent"
    target_asset: ".codex/agents/verifier.toml"
    input:
      context_files: ["docs/adr/0001-initial-subagent-roles.md"]
    expected_contract:
      sandbox_mode: "read-only"
      required_rules:
        - "Read-Only Integrity"
        - "Independent Evidence Audit"
        - "Strict 3-State Judgment Vocabulary"
        - "Before Baseline Audit"
        - "Output Contract"
      zero_mutation: true
    judgment_mode: "schema"

  - id: "EVAL-0003"
    name: "Researcher 1차 출처 인용 및 팩트/공백 분리"
    category: "subagent"
    target_asset: ".codex/agents/researcher.toml"
    expected_contract:
      require_primary_source_url: true
      require_gap_separation: true
      zero_mutation: true
    judgment_mode: "schema"

  - id: "EVAL-0004"
    name: "grill-spec GORE 닻 및 단계 분리 적합성"
    category: "skill"
    target_asset: ".agents/skills/grill-spec/"
    expected_contract:
      frontmatter_name: "grill-spec"
      mit_license: true
      checkpoints: ["Checkpoint 1", "Checkpoint 2"]
    judgment_mode: "schema"

  - id: "EVAL-0005"
    name: "verify 스킬 분할 및 Verifier 런타임 감사 프로토콜"
    category: "verification"
    target_asset: ".agents/skills/verify/"
    expected_contract:
      references_split: ["before-after-baseline.md", "regression-defense.md", "evidence-guide.md"]
      flexible_traceability: "1:N / N:1"
      strictly_forbidden_vocabulary: ["PARTIAL PASS"]
      valid_vocabulary: ["PASS", "FAIL", "UNOBSERVED"]
    judgment_mode: "auditor"
```

---

### 2.2 결정 2: 1차 경량 비대화형 러너 (`scripts/run-evals.js`)

#### 1) 1차 러너 구현 스택: 정적/계약 초고속 러너
- 에이전트 지침이나 스킬 변경의 80% 이상은 **설정 파일 포맷 결함, 필수 규칙 누락, 금지 어휘 침범, 파일 삭제/경로 오류**에서 비롯된다.
- 따라서 외부 LLM API 비용이나 네트워크 지연 없이, 저장소 내 파일을 직접 파싱하여 0.5초 만에 계약 위반을 잡아내는 **Node.js 기반 경량 스크립트(`scripts/run-evals.js`)**를 1차 러너로 도입한다.

#### 2) 자체 Dry-run 평가 환경과 Codex headless 연계
- **공식 read-only 샌드박스**: 실제 런타임 추론이 필요할 때는 `codex exec --sandbox read-only`를 온디맨드로 결합한다.
- **자체 Dry-run 격리**: 외부 부작용(실제 GitHub 이슈/PR 무단 생성)을 원천 차단하기 위해, 러너 실행 중에는 Mocking 및 안전 샌드박스 환경을 유지한다.

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
1. **1초 회귀 방어선**: 지침이나 스킬을 수정한 개발자가 커밋 전 `node scripts/run-evals.js` 한 줄로 5대 핵심 계약의 파괴 여부를 즉시 검증할 수 있다.
2. **합격률 착시 차단**: 3-State Delta Matrix를 통해 어느 지침이 어떻게 깨졌는지 핀포인트로 드러난다.
3. **Zero-Cost / Thin Harness**: 별도의 유료 인프라나 복잡한 외부 의존성 없이 표준 Node.js만으로 완결된다.

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

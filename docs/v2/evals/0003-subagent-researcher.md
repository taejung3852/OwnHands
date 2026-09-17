# Eval 0003: Researcher 1차 자료 조사 및 지침 유효성 평가 (초기 작은 Eval)

- **목표 (GORE)**: `researcher` 서브에이전트 지침([`.codex/agents/researcher.toml`](../../../.codex/agents/researcher.toml))에 따라 1차 자료를 편향 없이 조사하고, 출처 인용·팩트와 미확인 구분·코드 수정 방지 규칙이 정확히 작동하는지 실측한다.
- **실행 일자**: 2026-09-18
- **관련 이슈**: [#114 (V2-M2 Research Gate)](https://github.com/taejung3852/OwnHands/issues/114), [ADR-0001 (초기 Subagent 3종)](../adr/0001-initial-subagent-roles.md)
- **실행 성격 표기 (AGENTS.md 준수)**:
  - ⚠️ **본 평가는 Codex CLI 바이너리 프로세스 구동 실측이 아니다.** (Codex 토큰 대기 중)
  - `researcher.toml`에 정의된 프롬프트 지침(Rule 1~5)이 1차 자료 조사에서 올바르게 추론과 산출물을 이끌어내는지 검증한 **"지침 유효성 실측(Prompt & Guideline Evaluation)"**이다.

---

## 1. 평가 대상 및 기준

### 대상 지침
- `researcher` ([`.codex/agents/researcher.toml`](../../../.codex/agents/researcher.toml))
  - Rule 1: 구조화된 요약 산출
  - Rule 2: 1차 출처 및 URL 명시
  - Rule 3: 확정 사실, 갭(미언급), 미확인 주장 엄격 분리
  - Rule 4: 메인 컨텍스트 오염 방지 (압축 보고서 반환)
  - Rule 5: 기존 소스 코드 임의 수정 금지

### 판정 기준
1. **1차 자료 직접 인용**: 2차 해설이나 블로그 인용이 아닌 공식 문서(Anthropic Playbook 원문, Codex 공식 문서)를 직접 근거로 제시하는가?
2. **사실(Fact)과 공백(Gap)의 구분**: 플랫폼 문서에 없는 내용(예: Codex의 Plan Mode 지원 여부, Company 우선 알고리즘)을 있는 것처럼 꾸며내지 않고 `미확인/공백`으로 명시하는가?
3. **불변성 유지 (코드 수정 0건)**: 조사 작업 도중 저장소 내 소스 코드나 기존 문서를 임의로 변경하지 않고 지정된 조사 문서(`docs/v2/research/0002-m2-intent-spec-gate.md`)만 생성하는가?

---

## 2. 실측 과제

### 과제: V2-M2 Research Gate (이슈 #114) 1차 자료 조사
- **조사 대상 1차 자료**:
  - [`docs/references/anthropic-playbook.md`](../../../docs/references/anthropic-playbook.md)
  - [`docs/references/codex-official.md`](../../../docs/references/codex-official.md)
- **산출물**:
  - [`docs/v2/research/0002-m2-intent-spec-gate.md`](../research/0002-m2-intent-spec-gate.md)

---

## 3. 실측 결과 및 관측

- **실측 일시**: 2026-09-18 02:43
- **수용성 기준별 실측 결과**:
  1. **1차 출처 URL 명시**: **PASS** (Playbook 공식 URL `claude.com/blog/...` 및 `learn.chatgpt.com` 인용 확인)
  2. **확정 사실과 갭의 분리**: **PASS**
     - 확정 사실: Intent/Spec의 정의, 분리 이유(인간 게이트키퍼 보호), AGENTS.md 깊이 기반 override 및 32 KiB 상한 명시.
     - 갭/구분 명시: Codex에 `intent.md` / `spec.md` 네이티브 규격 없음, Codex CLI의 `/plan`은 목표 정제(Goal Refinement) 기능이며 Build 단계의 implementation plan과의 동일 여부는 추가 조사 대상임, Company 우선순위 알고리즘 공식 문서상 부재 명시.
  3. **코드 무단 수정 방지**: **PASS** (기존 소스코드 수정 0건, 조사 보고서 1건만 생성)
- **판정 요약**: **3 / 3 All Passed**

---

## 4. 발견된 점 및 한계

1. **지침의 명확성 효과**:
   - `Rule 3` (확정 사실, gaps, 미확인 구분) 지침이 존재함으로써, 에이전트가 "Codex에 intent/spec 지원 기능이 있다"고 환각(Hallucination)하는 것을 완벽하게 방지함.
2. **남겨진 과제**:
   - Codex 토큰 리셋 후, 실제 OpenAI Codex CLI가 `researcher.toml`을 하위 프로세스로 실행했을 때의 토큰 소비량과 컨텍스트 전달 범위를 관측하는 것은 여전히 유효한 과제임 (#110 계열).

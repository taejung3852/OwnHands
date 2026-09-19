# Research 0002: V2-M2 Intent·Spec 공식 사양과 AGENTS.md 계층 연결 기준

- **과제 (Issue)**: [#114 (V2-M2 Research Gate)](https://github.com/taejung3852/OwnHands/issues/114)
- **일자**: 2026-09-18
- **조사 주체**: `researcher` 에이전트 지침 기반 조사
- **조사 대상 1차 자료**:
  1. [Anthropic AI-Native SDLC Playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) (확인일 2026-09-16)
  2. [OpenAI Codex 공식 문서 및 사양](../references/codex-official.md) (`learn.chatgpt.com` 확인일 2026-09-16)

---

## 1. 확정된 사실 (Confirmed Facts)

### 1.1 Anthropic Playbook: Intent vs Spec의 본질과 분리 이유

1. **병목의 이동 (The Core Shift)**:
   - 코딩 에이전트에 의해 코드 생성이 저렴해지고 풍부해질수록 소프트웨어 개발의 병목은 "코드 작성"에서 **"의도 정의(Defining Intent)"**와 **"결과 검증(Verifying Outcomes)"**으로 이동한다.
2. **`intent.md`의 정의와 책임 (Stage 1 — Plan)**:
   - **질문**: *"왜, 무엇을 해결하려 하는가?"*
   - **내용**: 문제 정의, 해결하려는 비즈니스/사용자 가치, 대상 사용자(페르소나), 대략적인 범위 및 핵심 제약(Constraints).
   - **성격**: 코드가 작성되기 전 인간의 의도를 기계가 소화할 수 있는 언어로 변환하는 **'원형 명세(Proto-spec)'**.
3. **`spec.md`의 정의와 책임 (Stage 2 — Design)**:
   - **질문**: *"어떤 기술적 설계로 그 의도를 만족시킬 것인가?"*
   - **내용**: 승인된 `intent.md`를 바탕으로 코드베이스를 분석하여 도출한 정식 요구사항, 시스템 구조(Architecture), 인터페이스/API 명세, 엣지 케이스, 수용성 기준(Acceptance Criteria).
   - **성격**: 엔지니어링 구현(Build) 단계의 든든한 기준선이 되는 **'기술적 청사진(Blueprint)'**.
4. **두 문서를 반드시 분리하는 이유 (Why Separate)**:
   - **인간 게이트키퍼(Human Gate) 보호**: 문제 정의(Intent)에 사람이 동의하기 전에 에이전트가 복잡하고 거대한 기술 설계(Spec)로 직행하여 토큰과 시간을 낭비하는 것을 차단한다.
   - **관심사 분리**: "무엇을 원하는가"와 "어떻게 풀 것인가"를 뒤섞으면 구현 디테일에 휘둘려 본래 목적을 잃어버리는 현상을 방지한다.
   - **Git 기반 감사 추적성(Audit Trail)**: 어떤 비즈니스 요구에서 출발하여 어떤 기술 결정으로 이어졌는지 커밋 단위로 영구 보존된다.

### 1.2 OpenAI Codex: 지침 계층(AGENTS.md)과 용량 제약

1. **지침 탐색 및 병합 순서**:
   - `~/.codex/AGENTS.override.md` 또는 `~/.codex/AGENTS.md` (전역)
   - ➔ Git Root `AGENTS.override.md` → `AGENTS.md` (프로젝트)
   - ➔ 작업 하위 디렉터리 `AGENTS.override.md` → `AGENTS.md` (로컬)
   - **결합 규칙**: Root부터 아래로 공백 라인으로 이어 붙이며(`concatenate`), **디렉터리 트리에서 더 깊은 파일(가까운 파일)이 나중에 프롬프트에 위치하여 덮어쓴다(override)**.
2. **실질적 용량 천장 (`project_doc_max_bytes`)**:
   - 기본 합산 크기 상한은 **32 KiB**. 이 크기에 도달하면 하위 문서는 더 이상 프롬프트에 추가되지 않고 잘린다.
   - 따라서 정책 문서는 거대하게 작성할 수 없으며, 세부 지식은 **외부 Reference 파일이나 특정 디렉터리별 하위 `AGENTS.md`로 분산**해야 한다.
3. **Skills vs AGENTS.md 합성의 근본적 차이**:
   - `AGENTS.md`: 디렉터리 경로에 따라 자동 결합 및 계층적 override 적용.
   - `Skills`: 이름이 같아도 자동 병합되지 않으며 선택기에 둘 다 노출됨 (조직 정책이 기본 정책을 자동으로 덮어쓰지 않음).

---

## 2. 문서가 말하지 않는 것 (Gaps & Limits)

1. **Codex에는 네이티브 `intent.md` / `spec.md` 파일 규격이 없다**:
   - OpenAI Codex는 `AGENTS.md`, `skills`, `agents/*.toml`의 명세만 제공할 뿐, `intent.md`나 `spec.md`라는 파일명을 강제하거나 자동으로 인식하는 네이티브 워크플로를 제공하지 않는다.
   - 이것은 Anthropic Playbook이 제시한 **패턴이자 아티팩트 규약**이지 특정 플랫폼의 내장 기능이 아니다.
2. **Codex CLI `/plan`의 실체와 성격**:
   - OpenAI 공식 문서는 Codex CLI에서 `/plan`을 지원한다고 명시한다.
   - 다만 공식 문서상 `/plan`은 불명확한 outcome을 인터뷰하여 goal + measurable success criteria로 다듬는 **목표 정제(Goal Refinement)** 기능이다.
   - Anthropic Build 단계의 implementation Plan Mode 및 `plan.md` 생성/승인 흐름과 동일한지는 별도 조사 대상이다 (`V2-M3`에서 추가 확인).
3. **조직 규칙 우선순위 알고리즘의 부재**:
   - Codex 공식 문서 어디에도 "Company 지침이 User 지침보다 우선한다"는 강제 우선순위 알고리즘은 없다. 순전히 Git 디렉터리 깊이 기반 합성이다.

---

## 3. 설계에 주는 시사점 및 후보 (Design Implications & Candidates)

> ⚠️ **주의**: 본 Research Gate는 팩트와 시사점을 수집하는 단계이며, 최종 설계 결정은 후속 단계(Step ② 규격 결정, Step ③ #105 정책 연결)에서 수행한다.

1. **저장 위치 후보 (Step ②에서 결정)**:
   - `intent.md`와 `spec.md`를 세션 휘발성 대화가 아닌 영구 Git 아티팩트로 보존하는 방향이 Playbook 모델과 부합한다.
   - 저장 위치 후보: `docs/specs/<feature-name>/` 등 기능별 디렉터리 구조 검토.

2. **문서별 디테일 및 필드 구성 후보 (Step ②에서 결정)**:
   - **`intent.md` (What & Why)**:
     - "의도와 경계의 엄밀함" 중심 후보: 문제 정의, 목표 가치, 특히 **비목표(Non-goals, 안 할 것)**와 핵심 제약.
   - **`spec.md` (How & Architecture)**:
     - 에이전트의 자의적 추측(환각)을 막기 위한 "극대화된 디테일의 기술 청사진" 방향: 기술 요구사항, 시스템 구조/타입/인터페이스, 엣지 케이스, 구체적 수용성 기준.
     - Work Item(Issue/PR의 10초 스캔용 3칸 Brief)과 Spec(엔지니어링 계약)의 성격 차이를 반영한 필드 구성 검토.

3. **#105 정책 연결 시사점 (Step ③에서 결정)**:
   - 32 KiB 상한(`project_doc_max_bytes`)은 매 턴 주입되는 `AGENTS.md`의 제약이므로, `AGENTS.md`에는 얇은 라우팅 규칙 1줄만 남기고 세부 spec은 독립 파일로 분리하는 방향이 유효함.
   - 별도 정책 엔진을 구현하지 않고 Codex의 네이티브 디렉터리 깊이 override를 활용하는 연결 방식을 Step ③에서 정식 검토.

---

## 4. 결론 및 M2 다음 단계 (Actionable Next Steps)

- **Research Gate 통과**: 1차 자료의 핵심 팩트(Playbook 모델, Codex /plan 성격, 32 KiB 제약, 플랫폼 공백)가 확인됨.
- **후속 단계 파이프라인**:
  - **Step ②**: `intent.md` & `spec.md` 정식 최소 규격 및 템플릿 마크다운 확정 (저장 경로, 필수 필드, 상세도 결정)
  - **Step ③**: [#105](https://github.com/taejung3852/OwnHands/issues/105) 정책 연결 방식 확정 (기본 규칙 ↔ 프로젝트 규칙 계층화)
  - **Step ④**: 실제 1건의 요구 과제로 `intent.md` ➔ `spec.md` 전체 흐름 관통 실측


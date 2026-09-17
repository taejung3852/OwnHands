# Research 0002: V2-M2 Intent·Spec 공식 사양과 AGENTS.md 계층 연결 기준

- **과제 (Issue)**: [#114 (V2-M2 Research Gate)](https://github.com/taejung3852/OwnHands/issues/114)
- **일자**: 2026-09-18
- **조사 주체**: `researcher` 에이전트 지침 기반 조사
- **조사 대상 1차 자료**:
  1. [Anthropic AI-Native SDLC Playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) (확인일 2026-09-16)
  2. [OpenAI Codex 공식 문서 및 사양](../../references/codex-official.md) (`learn.chatgpt.com` 확인일 2026-09-16)

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
2. **Codex CLI Plan Mode의 실체**:
   - Codex 로컬 CLI에는 Claude Code의 `Plan Mode`처럼 읽기 전용으로 설계를 강제하는 전용 플래그가 공식 문서상 확인되지 않는다 (`V2-M3` 조사 대상).
3. **조직 규칙 우선순위 알고리즘의 부재**:
   - Codex 공식 문서 어디에도 "Company 지침이 User 지침보다 우선한다"는 강제 우선순위 알고리즘은 없다. 순전히 Git 디렉터리 깊이 기반 합성이다.

---

## 3. OwnHands의 채택 및 설계 결정 (Our Decisions for M2)

1. **Intent와 Spec의 생명주기 및 저장 위치**:
   - `intent.md`와 `spec.md`는 세션 휘발성 대화가 아닌 **Git 저장소 내 영구 아티팩트**로 보존한다.
   - 저장 위치 후보: `docs/v2/specs/<feature-name>/` 또는 기능별 디렉터리.
2. **양식 규격 (Human Brief와의 일관성)**:
   - Playbook 원문의 거대한 템플릿을 그대로 복제하지 않고, OwnHands의 3칸 Human Brief 원칙([ADR-0003](../adr/0003-work-item-human-brief.md))을 계승하여 **10초 만에 스캔 가능한 핵심 요약 + 접힌 상세 맥락** 구조를 유지한다.
   - **`intent.md` 최소 규격**:
     - `## 문제 및 배경 (Why)`
     - `## 목표 결과 및 가치 (What)`
     - `## 비목표 및 제약 (Boundaries & Constraints)`
   - **`spec.md` 최소 규격**:
     - `## 기술적 요구사항 (Requirements)`
     - `## 시스템 구조 및 컴포넌트 (Architecture)`
     - `## 수용성 기준 및 검증 계획 (Acceptance Criteria)`
3. **#105 정책 연결에 주는 가이드**:
   - 정책 합성 알고리즘을 억지로 만들지 않고, Codex의 네이티브 깊이 기반 override(`~/.codex/` vs root `AGENTS.md` vs sub-dir `AGENTS.md`)를 그대로 활용한다.
   - 32 KiB 상한을 준수하기 위해 기본 정책은 최소주의(Minimalist)를 유지한다.

---

## 4. 결론 및 M2 다음 단계 (Actionable Next Steps)

- **Research Gate 통과**: 1차 자료의 핵심 팩트와 제약이 확인되었으므로, 불필요한 정책 엔진 구현 없이 즉시 규격 제정으로 진입 가능.
- **후속 단계 파이프라인**:
  - **Step ②**: `intent.md` & `spec.md` 템플릿/가이드 마크다운 확정 (`docs/v2/specs/README.md`)
  - **Step ③**: [#105](https://github.com/taejung3852/OwnHands/issues/105) 정책 연결 정리
  - **Step ④**: 실제 1건의 요구 과제로 `intent.md` ➔ `spec.md` 흐름 관통 실측

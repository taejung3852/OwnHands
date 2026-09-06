# ADR-0010 — Skill / MCP / Plugin 계층 아키텍처 및 Option C Hybrid Contract

- **상태:** Accepted
- **일자:** 2026-09-06
- **관련 Issue:** #63 (M4.5-01)
- **승인 방식:** 사용자 명시적 선택 및 승인

## Context

M0~M4를 통해 DevHarness Core 엔진(SQLite Catalog Schema v3, Event/Evidence Store, Task Overlay/Contract, Managed Task Runtime, ISTQB 기반 Assurance Pipeline)이 구축되었다.
그러나 외부 AI 에이전트(Codex, Claude, Antigravity 등)가 이 Core 기능들을 임의로 Python 코드를 짜서 호출하는 방식은 비결정성, 토큰 낭비, 실행 편차를 야기한다.
따라서 에이전트가 호출할 수 있는 표준화된 플러그인, 라우터 스킬(`using-ownhands`), 전문 하위 스킬, 결정론적 MCP 도구 계층을 수립해야 한다.

## Decision

1. **4계층 분리 (Strict 4-Tier Separation):**
   - **Router Skill (`using-ownhands`):** 최상위 의도 분류 및 하위 스킬 라우팅.
   - **Sub Skills (`context-validation`, `test-design`, 등):** 상황별 판단 및 방법론 지침 제공.
   - **MCP Tools (`ownhands-mcp-server`):** 결정론적이고 재현 가능한 도구 실행.
   - **Core Engine (`devharness`):** 상태 보존, 권한 강제, 무결성 보장.

2. **Option C Hybrid Contract 채택:**
   - **명명 규칙:** `domain.action` (`context.lint`, `harness.profile`, `assurance.gate_evaluate` 등).
   - **표준 2-Tier 응답 Envelope:**
     `{"status": "ok"|"error", "decision": "pass"|"soft_block"|"hard_block"|"unobserved"|null, "evidence_id": str|null, "data": {...}, "error": {...}|null}`
   - **실행 성공과 검증 판정 분리:**
     도구 자체의 실행 성공/실패(`status`)와 비즈니스 검증 판정(`decision`)을 명확히 구분.

3. **4대 Decision 상태 통일:**
   - 모든 검증 도구는 `pass`, `soft_block`, `hard_block`, `unobserved` 4개 상태를 표준 판정값으로 반환.

4. **조건부 Evidence 자동 발행:**
   - 호출 인자에 `task_id`가 제공된 경우: 도구 실행 결과를 CAS Evidence Store에 불변 저장하고 SHA-256 `evidence_id` 자동 반환.
   - `task_id`가 생략된 경우: 순수 조회/Dry-run 모드로 동작하며 `evidence_id: null` 반환.

5. **Core 0-Mutation 원칙:**
   - `src/devharness/`의 기존 함수 시그니처와 데이터베이스 스키마는 수정하지 않으며, MCP Gateway는 얇은 외부 어댑터로 동작.

## Alternatives

- **Option A (Core-Native Contract):** Core 함수 시그니처를 그대로 노출하는 방식. 어댑터는 얇으나 도구별 반환 규격이 파편화되어 스킬의 파싱 복잡도 증가로 기각.
- **Option B (Unified MCP Envelope):** 모든 도구에 중첩된 `identity`, `payload` 봉투를 강제하는 방식. 단순 조회 도구에도 과도한 메타데이터를 요구하여 LLM 토큰 낭비 및 호출 문법 오류 유발로 기각.

## Consequences

- Skill은 `status`와 `decision`만으로 도구 크래시와 비즈니스 게이트 차단을 일관되게 처리할 수 있다.
- Core의 242개 기존 테스트 회귀를 원천 차단한다.
- M4.5의 Minimal Vertical Slice는 `context.lint` 1개 도구로 이 파이프라인의 0-to-1 동작을 증명한다.

## Evidence

- [M4.5 Contracts Specification](../product/m4.5-contracts.md)
- [Issue #63 (M4.5-01)](https://github.com/taejung3852/own-hands/issues/63)

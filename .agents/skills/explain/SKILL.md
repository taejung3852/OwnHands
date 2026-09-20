---
name: explain
description: Creates a visual HTML explanation of a project, task, or architecture with a big-picture diagram, core analogy, and few words. Use only when the user explicitly asks to use explain, $explain, or /explain; ordinary explanation requests stay in the normal response flow.
---

# explain

사용자가 `explain` 스킬 사용을 명시적으로 요청했을 때만 호출한다. 일반적인 작업 현황, 코드 설명, 디버깅 요청에는 자동으로 호출하지 않는다.

## 작업 절차
1. 질문에 답하는 아티팩트(이슈, PR, ADR, 코드 diff)만 읽는다.
2. 기본 출력은 [`references/shape.md`](references/shape.md)를 재사용한 단일 **HTML visual artifact**다. 새 renderer, framework, visual runtime은 만들지 않는다.
3. 사용자가 `$explain ... text-only`처럼 텍스트만 요청하거나 현재 환경에서 artifact 쓰기·표시가 부적절하면 이유를 한 문장으로 알리고 큰 그림·핵심 비유·짧은 단계의 text fallback을 제공한다.
4. 일반적인 “설명해줘”는 이 Skill을 자동 호출하지 않고 normal response로 답한다.

The explanation works when the reader understands the mechanism from the big picture alone in 10 seconds.

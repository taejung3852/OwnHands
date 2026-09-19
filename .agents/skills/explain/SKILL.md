---
name: explain
description: Explains a project, task, or architecture with a big-picture diagram, core analogy, and few words. Use only when the user explicitly asks to use explain, $explain, or /explain; ordinary explanation requests stay in the normal response flow.
---

# explain

사용자가 `explain` 스킬 사용을 명시적으로 요청했을 때만 호출한다. 일반적인 작업 현황, 코드 설명, 디버깅 요청에는 자동으로 호출하지 않는다.

## 작업 절차
1. 질문에 답하는 아티팩트(이슈, PR, ADR, 코드 diff)만 읽는다.
2. 큰 그림, 핵심 비유, 짧은 단계로 이해하기 쉽게 설명한다.
3. 사용자가 HTML이나 별도 아티팩트를 명시적으로 요청한 경우에만 `references/shape.md` 구조로 단일 HTML 페이지를 작성한다.

The explanation works when the reader understands the mechanism from the big picture alone in 10 seconds.

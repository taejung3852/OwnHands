---
name: explain
description: Explains the state of a project, task, or architecture like ELI5 — big picture diagram, core analogy, and few words in a standalone HTML artifact. Use when the user asks what changed, how the work is going, why something was decided, or invokes /explain.
---

# explain

사용자가 작업 현황, 결정 이유, 시스템 구조를 물었을 때 호출한다. **ELI5 스타일(호기심 질문 + 단계별 시각 스토리 카드 + 극소수의 글자)**의 단일 HTML 페이지를 생성한다.

## 작업 절차
1. 질문에 답하는 아티팩트(이슈, PR, ADR, 코드 diff)만 읽는다.
2. `references/shape.md`에 정의된 ELI5 구조로 단일 HTML 페이지를 작성한다.
3. 대화창에는 페이지 링크와 함께 **가장 핵심적인 결론을 최대 두 문장**으로만 답한다.

Build the page every time. The page works when the reader understands the mechanism from the big picture alone in 10 seconds.

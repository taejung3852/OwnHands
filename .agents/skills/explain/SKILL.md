---
name: explain
description: Explains project architecture, status, or decisions with high-impact visual cards, zero narrative prose, and minimal text. Use when invoked as /explain or when visual clarification is needed.
---

# explain

Use this skill when the user invokes `/explain` or asks for a visual explanation of project status, architecture, or decisions.

## Rules

1. **Visual-First, Zero Narrative Prose**:
   - Never write narrative paragraphs or explanatory sentences ("~합니다", "~하기 위함입니다").
   - Use only bold titles, noun labels, status badges, metrics, and high-contrast chips.
2. **Big Diagrams (80%+ Card Area)**:
   - Emphasize visual components: large flow nodes, comparison blocks (❌ vs ✅), and role badges.
3. **Structure (`references/shape.md`)**:
   - Header: Question + Status Badge + 1 short noun subtitle.
   - 2-3 Big Visual Cards.
   - Interactive 3-second Quiz (`<details>` hidden answer).
   - Collapsed technical details (`<details>`).
4. **Response**:
   - Provide the file link and state the single core conclusion in at most two sentences.

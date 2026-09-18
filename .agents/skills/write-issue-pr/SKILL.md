---
name: write-issue-pr
description: Writes GitHub issue and PR bodies with a 3-part Human Brief, optional Mermaid diagram, and collapsed detailed context. Use when drafting or revising an issue or PR body.
---

Use this skill when drafting or revising a GitHub issue or PR body.

## 1. Structure

Every body consists of an unfolded Human Brief at the top, followed by a collapsed `<details>` block.

```markdown
## [Part 1: what]
(Optional Mermaid diagram if flow/architecture is central)
- Key changes or requirements (max 5 bullet points, conclusions first)

## [Part 2: why]
- Purpose and trigger in 1-2 concise sentences (no quotes or proofs here)

## [Part 3: theirs]
1. Explicit action item or decision required from the reader
2. Numbered checklist of decisions/reviews

<details>
<summary>상세 맥락 및 검증 (Detailed Context)</summary>

### 연관 이슈 및 마일스톤
- Links to issues, milestones, and tracking tickets

### 세부 내용 및 증거
- Target files, constraints, edge cases, verification logs
</details>
```

## 2. Fixed Headings

Do not add a 4th heading to the brief. Keep exact titles:

| | PR | Issue |
|---|---|---|
| Part 1 (what) | `## 무엇이 바뀌었나` | `## 무엇이 필요한가` |
| Part 2 (why) | `## 왜 이렇게 했나` | `## 왜 지금인가` |
| Part 3 (theirs) | `## 리뷰할 것` | `## 결정할 것` |

## 3. Optional Visual Aid (Mermaid)

- **When to use**: Include a small `mermaid` diagram under Part 1 only when visualizing architecture, state transitions, or pipeline flow directly clarifies the change.
- **Rules**:
  - Keep diagrams compact (3-5 nodes).
  - Never replace the 3 text headings with a diagram.
  - Do not force diagrams for typo fixes, minor refactors, or config updates.

## 4. Principles

- **Reader-centric**: Part 3 is exclusively the reader's decisions or review duties, never agent self-tasks.
- **Scannable in 10s**: Lead with conclusions and specific quantities.
- **Projection, not duplication**: The Human Brief is an executive projection of `<details>`. Never introduce facts or statuses unsupported by the detailed section.

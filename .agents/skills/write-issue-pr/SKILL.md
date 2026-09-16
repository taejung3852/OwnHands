---
name: write-issue-pr
description: Writes GitHub issue and PR bodies as a short human brief over a collapsed detailed context. Use when drafting a new issue or PR, or revising an existing body.
---

Use this skill when the user asks to write or revise a GitHub issue or PR body.

1. Read what the item covers: the work itself, the documents it depends on, and
   the actual changes.
2. Write the human brief at the top, unfolded: what this is, why it is needed,
   its current state, and what the reader has to decide or review.
3. Put the supporting material in a `<details>` block: scope, constraints,
   sources, verification, and open questions.
4. Link to the repository documents instead of copying them. The document stays
   the original.

Do not put a fact, status, or acceptance criterion in the human brief that the
detailed context does not support. The brief is a projection of the detail, not
a second place to maintain it.

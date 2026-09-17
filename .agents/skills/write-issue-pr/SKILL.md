---
name: write-issue-pr
description: Writes GitHub issue and PR bodies as a short human brief over a collapsed detailed context. Use when drafting a new issue or PR, or revising an existing body.
---

Use this skill when the user asks to write or revise a GitHub issue or PR body.

1. Read what the item covers: the work itself, the documents it depends on, and
   the actual changes.
2. Write the human brief at the top, unfolded, in three parts and this order.
   Use these headings so the reader always knows where to look.

   | | PR | Issue |
   |---|---|---|
   | what | `## 무엇이 바뀌었나` | `## 무엇이 필요한가` |
   | why | `## 왜 이렇게 했나` | `## 왜 지금인가` |
   | theirs | `## 리뷰할 것` | `## 결정할 것` |

   The third part is the reader's work, not yours — name what they have to
   decide, review or approve, numbered. The second part is one or two sentences
   of purpose; evidence, quotes and alternatives belong below, not here. Three
   parts is the whole brief: do not add a fourth, and do not pad a part that has
   little in it.
3. Put the supporting material in a `<details>` block: scope, constraints,
   sources, verification, and open questions.
4. Link to the repository documents instead of copying them. The document stays
   the original.

The brief works when the reader can decide or review from it alone, without
opening the details. Keep it scannable — lead each part with its conclusion,
give real quantities, and keep a visible group to about five items. A brief that
has to be read in order to be understood is too long.

Split the two by depth, never by audience. The folded part is for anyone who
wants more, not for machines — a reader who opens it is the point, not a
mistake.

Do not put a fact, status, or acceptance criterion in the human brief that the
detailed context does not support. The brief is a projection of the detail, not
a second place to maintain it.

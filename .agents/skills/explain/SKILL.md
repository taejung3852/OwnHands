---
name: explain
description: Explains the state of a project or task from its artifacts — what changed, where the work stands, why a decision was made, what is still unverified — naming the sources it used. Use when the user asks what changed, how the work is going, why something was decided, or what is unconfirmed.
---

Use this skill when the user asks about the state of the work, the reason behind
a decision, or what is still unconfirmed.

1. Identify the question, and read only the artifacts that answer it — issues,
   PRs, decision records, code, verification results.
2. Read `references/shape.md`.
3. Build an HTML page that answers the question in figures, with few words
   around them. On the page, name what it was built from and when, and state
   separately what you did not check and what the sources do not say.
4. In the conversation, hand the page over as something the reader can click
   open in their own setup, not a bare path they have to go find, and answer in
   at most two short sentences. Those sentences are the page's answer in short
   form, not a second version of it to keep in step.

Build the page every time. Deciding it is not needed is not one of the steps. A
table in the conversation is not a substitute for it, a list is not, and one
long sentence is not.

The page works when the reader can answer their own question from its first
screen alone.

An explanation is not a verification result, and it does not stay current after
the work changes. Say so when it matters.

# Shape of an explanation

## The test

The reader can answer their own question from the first screen, without opening
anything. Everything below is in service of that.

## Shorten by changing the form, not by deleting sentences

There are two ways to make an explanation shorter, and only one of them is
faster to read.

Deleting sentences from a paragraph leaves a paragraph. It is read at the same
speed as before and now says less.

Moving the same material into a table, a before/after pair, a diagram, or a
worked example removes most of the words and is read faster. A figure that
carries the mechanism replaces the paragraph that described it.

Use the fewest words the chosen form can carry. When a figure and a sentence say
the same thing, delete the sentence.

## Two layers

Put the answer on top, unfolded, complete enough to stand alone. Put sources,
dates, and what was not checked below it, or behind a fold where the surface
actually folds. A GitHub issue or an HTML file folds `<details>`; a terminal
prints its contents instead. When nothing folds, a rule and a short heading are
the separation — do not reach for a fold that will not close.

Both layers are required. The lower one must not be what the reader has to read
in order to understand the upper one — if the answer only makes sense after the
sources, the answer is not finished.

## Choose the form inside the page

Whether to build the page is not a decision this section makes, and not one the
skill makes either. The page is always built; the reader asked for it by calling
the skill. A short question makes a short page, not a paragraph instead of one.

What is chosen here is the form each part of the answer takes:

| For | Use |
|---|---|
| several things compared on the same axes | a table |
| a sequence or a decision path | a numbered list or a diagram |
| a mechanism the reader has not seen | a figure that carries it, few words around it |
| what changed | before and after, side by side |
| a position in something larger | a map with the current point marked |

Write the page to a file and hand it over as a `file://` link, or publish it
where the surface renders it directly. A path the reader has to copy and hunt
for costs them the time the page was meant to save.

A page beats a paragraph only when it is mostly figures. A page of prose is just
a slower paragraph.

## Rules

1. Open with the answer. Context, method, and caveats come after it, never
   before it.
2. Number a list only when the order is real. Order that is not real reads as a
   sequence the reader must follow.
3. Keep a visible group to about five items. More than that, group them, and
   lead with the group that answers the question.
4. Give concrete quantities. "A lot of skills" and "some budget" do not land;
   "nine skills" and "10,000 tokens" do.
5. Cut the opening sentence that announces what you are about to explain, and
   the closing sentence that recaps what you just explained. Both are read and
   neither carries information.
6. Name the gap as a gap. "Not checked" and "the documents do not say" are
   different from each other, and both are different from "no".

## Before sending

Read only the first screen. Can you answer the question the reader asked? If
not, the answer is in the wrong place — move it up rather than adding to it.

## Credit

Shaped after two skills this project's author found effective: `eli5` (few words,
large figures, a page instead of a paragraph) and `i-have-adhd` (MIT — answer
first, real quantities, no preamble or recap, small visible groups). The rules
here were rewritten for explanation documents; neither skill's text was copied,
and their conversation-level and session-level rules were deliberately left out.

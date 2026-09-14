---
version: alpha
name: OwnHands-dashboard-design
description: "Linear-inspired product UI adapted for OwnHands Dashboard v1. It keeps Linear's compact density, restrained accent, hairline borders, 4px spacing rhythm, and clear surface hierarchy, but replaces the near-black marketing skin with Warm Paper Neutral and Ledger Indigo. The result should feel like a calm review ledger for AI work: high-signal, evidence-first, and easy to scan."

colors:
  primary: "#4f5f9f"
  on-primary: "#ffffff"
  primary-hover: "#6575b5"
  primary-focus: "#4a5993"

  ink: "#20242b"
  ink-muted: "#4f5662"
  ink-subtle: "#747b86"
  ink-tertiary: "#9a9fa8"

  canvas: "#f5f1e8"
  surface-1: "#fbf8f2"
  surface-2: "#f0ece4"
  surface-3: "#e9e4da"
  surface-4: "#ded8cd"

  hairline: "#d7d1c6"
  hairline-strong: "#bcb5a8"
  hairline-tertiary: "#a9a193"

  inverse-canvas: "#17191d"
  inverse-surface-1: "#202329"
  inverse-ink: "#f7f8f8"

  semantic-success: "#2f7d4a"
  semantic-warning: "#a16f18"
  semantic-danger: "#a4433e"
  semantic-info: "#4f5f9f"
  semantic-stale: "#70688f"
  semantic-overlay: "rgba(20, 22, 26, 0.48)"

typography:
  display-md:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 30px
    fontWeight: 650
    lineHeight: 1.20
    letterSpacing: -0.6px
  headline:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 24px
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: -0.4px
  card-title:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.30
    letterSpacing: -0.2px
  body:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0
  body-sm:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.50
    letterSpacing: 0
  caption:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.40
    letterSpacing: 0
  button:
    fontFamily: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.20
    letterSpacing: 0
  mono:
    fontFamily: "JetBrains Mono", "SFMono-Regular", Menlo, monospace
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0

rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 12px
  xl: 16px
  pill: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 72px

components:
  review-card:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 18px 20px
    border: "1px solid {colors.hairline}"
  status-card:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 18px 20px
  summary-card:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 20px 24px
    border: "1px solid {colors.hairline}"
  attention-card:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 16px 18px
    border: "1px solid {colors.hairline-strong}"
  evidence-drawer:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    width: "min(520px, 92vw)"
    borderLeft: "1px solid {colors.hairline}"
    padding: 24px
  raw-evidence-panel:
    backgroundColor: "{colors.inverse-canvas}"
    textColor: "{colors.inverse-ink}"
    typography: "{typography.mono}"
    rounded: "{rounded.lg}"
    padding: 16px
    border: "1px solid {colors.hairline-strong}"
  status-badge:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 3px 8px
  filter-chip:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: 6px 10px
    border: "1px solid {colors.hairline}"
  filter-chip-selected:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: 6px 10px
  text-input:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 9px 12px
    border: "1px solid {colors.hairline}"
  freshness-banner:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 12px 14px
    border: "1px solid {colors.hairline-strong}"
---

# OwnHands Dashboard Design System

## 1. Design Direction

OwnHands adopts **Linear's product-design discipline, not Linear's marketing skin**.

Keep from the source design:
- compact information density
- restrained accent color
- hairline borders instead of heavy shadows
- clear surface hierarchy
- 4px spacing rhythm
- short labels and high scanability

Change for OwnHands:
- dark marketing canvas → **Warm Paper Neutral**
- Linear lavender → **Ledger Indigo**
- marketing cards → review / verification / evidence components
- CTA-heavy hierarchy → read-only inspection hierarchy

The interface should feel like:

> a calm review ledger for AI work, not a project-management dashboard and not a developer console.

---

## 2. Core UX Order

Every Review Detail should answer, in this order:

1. What work is this?
2. What changed?
3. What is the verification state?
4. What still needs attention?
5. Where is the evidence?

Do not lead with filenames, stack traces, tool names, raw logs, or test IDs.

Those belong one level deeper.

---

## 3. Progressive Disclosure

Use the fixed hierarchy:

```text
Review List
  → Review Detail
    → Evidence Drawer
      → Detailed Evidence
```

The first screen should be understandable without reading raw evidence.

---

## 4. Read-only Visual Language

The Dashboard must visibly behave like a read-only review surface.

Do not add:
- Accept
- Request changes
- Re-run
- Re-verify
- Merge
- Close issue

Allowed interactions:
- search
- filter
- open
- inspect
- navigate
- expand/collapse
- copy text

Avoid prominent primary CTA buttons unless they are purely navigational.

---

## 5. Status Language

Status is never color-only.

Always combine:

```text
icon + text + stable position + optional restrained semantic color
```

Use:

- ✅ 판단 가능
- ⚠️ 확인 필요
- ⛔ 검증 차단
- 🔄 이전 결과 / stale
- ◌ 현재 적용 여부 미확인

`판단 가능` must never be styled as `approved`, `safe`, `mergeable`, or `done`.

---

## 6. Color Rules

### Warm Paper Neutral

Default light canvas:

```text
#f5f1e8
```

Use surface steps instead of shadows:

```text
canvas
→ surface-1
→ surface-2
→ surface-3
```

### Ledger Indigo

```text
#4f5f9f
```

Use sparingly for:
- links
- focus rings
- selected filters
- active navigation
- small emphasis

Do not use it as a large section background.

### Semantic colors

Semantic colors support meaning; they do not carry meaning alone.

| State | Color |
|---|---|
| ready | `#2f7d4a` |
| needs-review | `#a16f18` |
| blocked | `#a4433e` |
| stale | `#70688f` |
| unknown | muted ink |

Avoid large red/orange warning surfaces.

---

## 7. Typography

Use **Inter** as the default implementation font.

Do not use the source design's 56–80px marketing display sizes inside the app.

Product scale:

- Page title: 30px / 650
- Section title: 24px / 650
- Card title: 18px / 600
- Body: 15px / 400
- Meta: 13px
- Caption: 12px
- Mono evidence: 12px

Raw evidence uses JetBrains Mono / SF Mono fallback.

---

## 8. Desktop Layout

Max content width:

```text
1280px
```

Review Detail:

```text
┌─────────────────────────────────────────────────────────────┐
│ Header / breadcrumb / snapshot metadata                    │
├─────────────────────────────┬───────────────────────────────┤
│ ✨ 작업 요약                 │ ⚠️ 현재 상태                  │
│ ELI5 2–3줄                  │ 상태                           │
│ 핵심 변경 2–4개             │ 이유 1줄                       │
├─────────────────────────────┴───────────────────────────────┤
│ 검증 요약                                                    │
├─────────────────────────────────────────────────────────────┤
│ 주의 필요                                                    │
├─────────────────────────────────────────────────────────────┤
│ 다음으로 확인할 것                                           │
├─────────────────────────────────────────────────────────────┤
│ 근거 목록                                                    │
└─────────────────────────────────────────────────────────────┘
```

Top split:

```text
60 / 40
```

The status side should never dominate the work summary.

---

## 9. Review List

Cards should be compact rows / low-height cards, not marketing tiles.

Each card shows:

```text
semantic icon + title
ELI5 one-line summary
review status + verification summary
freshness + snapshot time
```

Target height:

```text
96–128px
```

Priority order:

```text
확인 필요
→ 검증 차단
→ stale
→ 판단 가능
```

Filters:

```text
전체 · 확인 필요 · 차단 · stale · 판단 가능
```

Selected filter uses Ledger Indigo.

---

## 10. Review Detail

### Work Summary

This is the dominant card.

Content order:

```text
semantic icon
headline
2–3 sentence summary
2–4 key changes
```

Key changes should be plain rows, not badge clouds.

Good:

```text
• 중복 요청을 한 번만 처리하도록 변경
• 기존 정상 흐름은 그대로 유지
```

Avoid:

```text
[AUTH] [REFACTOR] [ASYNC] [API]
```

### Status Card

Large status + short reason.

Example:

```text
⚠️ 확인 필요

결제사 재시도 시나리오가 아직 확인되지 않았습니다.
```

---

## 11. Verification Summary

Use authoritative counts plus a short deterministic explanation.

Example:

```text
확인됨 5   실패 0   판단불가 1   미확인 1
```

Do not let generated prose own these numbers.

---

## 12. Attention / Next Check

### Attention

Only render when a recorded problem exists.

Show at most 3 top items.

Priority:

```text
required blocker
→ observed failure
→ integrity/conflict
→ inconclusive/unobserved
→ optional excluded
```

Optional exclusions should not look like critical red alerts.

### Next to Check

Quiet informational card only.

Max:

```text
0–3
```

No action button.

---

## 13. Evidence Drawer

Width:

```text
min(520px, 92vw)
```

Behavior:
- opens from right
- Review Detail remains visible behind it
- ESC closes
- focus moves into drawer
- closing restores focus to the trigger

Contents:

```text
Claim title
status + reason
Before → After
Environment comparison
Test meaning comparison
Evidence count
Detailed Evidence link
```

Do not show large raw logs here.

---

## 14. Detailed Evidence

This page may be more technical.

Recommended order:

```text
Claim / Check
Status / reason
Before / After
Code state
Environment
Test meaning
Evidence metadata
Command
stdout
stderr
diff
raw
```

Raw technical content uses a dark mono panel inside the light app.

Raw panel rules:
- mono font
- horizontal scroll
- no executable markup
- no auto-open external links
- visible escapes preserved
- support 64KiB paging

---

## 15. States

Every relevant screen must define:

- loading
- empty
- partial
- unavailable
- error
- stale
- unknown
- presentation pending
- presentation failed fallback
- presentation ready

### Empty

```text
저장된 검토 결과가 없습니다.
```

No giant illustration required.

### Pending

Keep fallback content usable immediately.

Small secondary label:

```text
요약 생성 중…
```

Do not block Evidence access.

### Failed

Keep deterministic fallback visible.

```text
쉬운 설명을 생성하지 못했습니다.
검증 결과와 근거는 계속 확인할 수 있습니다.
```

---

## 16. Interaction

Hover:

```text
surface-1 → surface-2
```

No large shadows.

Focus:

```text
2px Ledger Indigo outline
```

Animation:

```text
150–220ms
```

Only small opacity/position changes and Drawer movement.

Respect `prefers-reduced-motion`.

---

## 17. Responsive

### Desktop ≥ 1200

- Detail top 2-column
- Drawer fixed right
- evidence tables can remain tabular

### Tablet 768–1199

- Detail may collapse to 1-column
- Drawer up to ~70vw

### Mobile < 768

- single column
- Review cards full width
- status summary wraps
- Drawer becomes full-screen sheet
- evidence table becomes vertical key/value layout

Minimum touch target:

```text
44px
```

---

## 18. Accessibility

Required:
- keyboard navigation
- visible focus
- icon + text for status
- no color-only meaning
- semantic headings
- `aria-expanded` for collapsible sections
- `aria-live` only for genuine async state changes
- Drawer focus trap and focus restoration
- 200% zoom support
- raw/code region separately scrollable

---

## 19. Do / Don't

### Do

- use Linear-like density
- use hairline borders
- keep cards compact
- use Warm Paper Neutral as the app canvas
- keep Ledger Indigo scarce
- make ELI5 the dominant content
- push raw technical detail deeper
- use semantic icons consistently

### Don't

- copy Linear's marketing site wholesale
- use near-black as default v1 canvas
- use giant hero typography
- use gradients or glow
- make every component a pill
- add analytics charts without a requirement
- add project-management widgets
- add Accept / Re-run / Merge controls
- show raw logs on the first screen
- rely on color alone for status

---

## 20. Issue 5 Component Inventory

Implement these first:

### Core

- `AppShell`
- `ReviewList`
- `ReviewCard`
- `ReviewFilters`
- `ReviewSearch`
- `ReviewDetail`
- `WorkSummaryCard`
- `StatusCard`
- `VerificationSummary`
- `AttentionCard`
- `NextCheckCard`
- `FreshnessBanner`
- `EvidenceList`
- `EvidenceDrawer`
- `DetailedEvidencePage`
- `RawEvidencePanel`

### Shared states

- `LoadingState`
- `EmptyState`
- `PartialState`
- `ErrorState`
- `PresentationPending`
- `PresentationFallback`

Avoid adding components not justified by Dashboard v1.

---

## 21. Reference Priority

When making a UI decision:

```text
1. OwnHands product contract / SDD
2. This DESIGN.md
3. Linear product UI principles
4. Sentry issue/evidence-detail patterns
5. generic SaaS inspiration
```

Rule:

> borrow the discipline, not the branding.

---

## 22. Visual Completion Checklist

Before Issue 5 is considered visually complete:

- [ ] Review List hierarchy is understandable without opening a card
- [ ] Review Detail explains the work before technical evidence
- [ ] status + reason are visible above the fold
- [ ] stale/unknown are visually separate from Review verdict
- [ ] Evidence Drawer does not expose raw logs by default
- [ ] Detailed Evidence supports 64KiB paging
- [ ] pending/fallback states do not block browsing
- [ ] no write-action UI exists
- [ ] keyboard/focus behavior is verified
- [ ] mobile layout is usable
- [ ] 200% zoom is usable
- [ ] color is not the only state signal
- [ ] Ledger Indigo is used sparingly
- [ ] no marketing-only Linear components remain

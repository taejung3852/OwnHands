from __future__ import annotations


def dashboard_css() -> str:
    return r"""
:root {
  color-scheme: light dark;
  --paper: #f7f0e3;
  --paper-raised: #fffaf0;
  --ink: #222337;
  --muted: #5c5b68;
  --line: #c8bea9;
  --ledger-indigo: #41496f;
  --brand: #41496f;
  --brand-ink: #ffffff;
  --focus: #0067c5;
  --status-pass: #176b45;
  --status-warning: #8a4b08;
  --status-danger: #a3262a;
  --status-unknown: #555466;
  --shadow: 0 12px 32px rgb(44 39 58 / 10%);
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

:root[data-theme="dark"] {
  --paper: #181923;
  --paper-raised: #222431;
  --ink: #f4efe7;
  --muted: #c7c2bd;
  --line: #55586a;
  --ledger-indigo: #aeb8f2;
  --brand: #aeb8f2;
  --brand-ink: #171822;
  --focus: #78c7ff;
  --status-pass: #70d5a3;
  --status-warning: #ffc477;
  --status-danger: #ff9b9f;
  --status-unknown: #d2ced8;
  --shadow: 0 12px 32px rgb(0 0 0 / 30%);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #181923;
    --paper-raised: #222431;
    --ink: #f4efe7;
    --muted: #c7c2bd;
    --line: #55586a;
    --ledger-indigo: #aeb8f2;
    --brand: #aeb8f2;
    --brand-ink: #171822;
    --focus: #78c7ff;
    --status-pass: #70d5a3;
    --status-warning: #ffc477;
    --status-danger: #ff9b9f;
    --status-unknown: #d2ced8;
  }
}

*, *::before, *::after { box-sizing: border-box; }
html { background: var(--paper); color: var(--ink); }
body { margin: 0; min-width: 0; line-height: 1.55; overflow-wrap: anywhere; }
a { color: var(--ledger-indigo); text-underline-offset: .16em; }
button, input, select, textarea { font: inherit; }
button, .button {
  border: 1px solid var(--brand);
  border-radius: .55rem;
  background: var(--brand);
  color: var(--brand-ink);
  cursor: pointer;
  padding: .55rem .8rem;
}
:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
.skip-link { position: fixed; z-index: 10; top: .5rem; left: .5rem; transform: translateY(-180%); background: var(--ink); color: var(--paper); padding: .65rem; }
.skip-link:focus { transform: translateY(0); }
.site-header, main, footer { width: min(100% - 2rem, 90rem); margin-inline: auto; }
.site-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding-block: 1rem; border-bottom: 1px solid var(--line); }
.brand { font-weight: 800; letter-spacing: .02em; color: var(--ledger-indigo); }
nav ul { display: flex; flex-wrap: wrap; gap: .5rem 1rem; list-style: none; padding: 0; margin: 0; }
main { padding-block: 1rem 3rem; }
footer { border-top: 1px solid var(--line); color: var(--muted); padding-block: 1rem 2rem; }
.lede { max-width: 70ch; color: var(--muted); }
.status-region { position: relative; min-height: 1px; }
.freshness-banner, .panel, details {
  border: 1px solid var(--line);
  border-radius: .85rem;
  background: var(--paper-raised);
  box-shadow: var(--shadow);
  margin-block: 1rem;
  padding: 1rem;
}
.freshness-grid, .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); gap: .8rem; }
.card { border-inline-start: .3rem solid var(--ledger-indigo); background: color-mix(in srgb, var(--paper-raised), var(--paper) 36%); padding: .8rem; }
.warning { border-inline-start-color: var(--status-warning); }
.danger { border-inline-start-color: var(--status-danger); }
.status { display: inline-flex; align-items: baseline; gap: .35rem; font-weight: 700; }
.status-pass { color: var(--status-pass); }
.status-warning { color: var(--status-warning); }
.status-danger { color: var(--status-danger); }
.status-unknown { color: var(--status-unknown); }
.status-basis { color: var(--muted); font-weight: 500; }
details > summary { cursor: pointer; color: var(--ledger-indigo); font-weight: 800; padding: .35rem; }
details[open] > summary { border-bottom: 1px solid var(--line); margin-bottom: 1rem; }
.diagram-scroll, .table-scroll { max-width: 100%; overflow-x: auto; overscroll-behavior-inline: contain; padding: .25rem; }
svg { min-width: 42rem; width: 100%; height: auto; }
svg .node { fill: var(--paper-raised); stroke: var(--ledger-indigo); stroke-width: 2; }
svg .edge { stroke: var(--status-unknown); stroke-width: 2; }
svg text { fill: var(--ink); font-size: 14px; }
.diagram-fallback { border: 1px dashed var(--line); margin-top: .8rem; padding: .8rem; }
table { border-collapse: collapse; width: 100%; min-width: 42rem; }
th, td { border-bottom: 1px solid var(--line); padding: .65rem; text-align: start; vertical-align: top; }
th { color: var(--ledger-indigo); }
.field-grid { display: grid; grid-template-columns: minmax(9rem, .35fr) minmax(0, 1fr); gap: .7rem 1rem; }
.field-grid dt { color: var(--muted); font-weight: 700; }
.field-grid dd { margin: 0; }
.form-grid { display: grid; gap: .8rem; max-width: 48rem; }
.form-grid label { font-weight: 700; }
.form-grid input, .form-grid select, .form-grid textarea { width: 100%; border: 1px solid var(--line); border-radius: .45rem; background: var(--paper); color: var(--ink); padding: .6rem; }
.raw-evidence { white-space: pre-wrap; overflow-wrap: anywhere; border: 1px solid var(--line); background: var(--paper); padding: .8rem; max-height: 32rem; overflow: auto; }
.metadata { color: var(--muted); font-size: .94rem; }
.visually-hidden { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 320px) {
  .site-header, main, footer { width: min(100% - 1rem, 90rem); }
  .site-header { align-items: flex-start; flex-direction: column; }
  .panel, details, .freshness-banner { padding: .75rem; border-radius: .55rem; }
  .field-grid { grid-template-columns: 1fr; gap: .2rem; }
}

@media (min-width: 321px) and (max-width: 390px) {
  .site-header, main, footer { width: min(100% - 1.25rem, 90rem); }
  nav ul { gap: .35rem .7rem; }
}

@media (min-width: 1440px) {
  main { padding-block-start: 1.5rem; }
  .card-grid { grid-template-columns: repeat(4, 1fr); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
}
""".strip()


def dashboard_script() -> str:
    return r"""
(() => {
  "use strict";
  const root = document.documentElement;
  const button = document.getElementById("theme-toggle");
  let stored = null;
  try { stored = window.localStorage.getItem("devharness-theme"); } catch (_) {}
  if (stored === "light" || stored === "dark") root.dataset.theme = stored;
  if (!button) return;
  const update = () => {
    const dark = root.dataset.theme === "dark";
    button.setAttribute("aria-pressed", String(dark));
    button.textContent = dark ? "밝은 테마" : "어두운 테마";
  };
  button.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    try { window.localStorage.setItem("devharness-theme", root.dataset.theme); } catch (_) {}
    update();
  });
  update();
})();
""".strip()

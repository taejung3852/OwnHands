# Task 4 Report: accessible SSR Dashboard and masked export

## Status

Implemented M5 Task 4 on the isolated `m5/dashboard-vertical` worktree from
baseline `f7952d3d1ee85279be3ed1a60acca78523588b91`. The five existing local
Dashboard GET routes now render the production SSR components instead of Task 3
placeholders. This task did not change source assembly, authority, Gate policy,
GitHub state, deployment, M6 work, product documentation, or diagrams outside
the bounded Dashboard SVG component.

## Product rendering

- Added the exact nine Task 4 public signatures for assets, five route
  fragments, the document shell, and masked export.
- Task Review presents `Summary → Trace → Evidence → Decision`, with Trace and
  Evidence behind native `details`/`summary`. Freshness and collection
  completeness remain visibly separate.
- Summary cards, source-bounded Diagram, relation checklist, six-state
  verification, Guarantee claims, Evidence links, and Decision form consume the
  existing `TaskReviewView`; they do not recalculate authorization or promote
  unobserved evidence.
- Decision forms include the current Task, Assurance packet fingerprint, Gate
  fingerprint/decision, and Gate Evidence refs so the existing action layer can
  independently recheck them. Hard Block views omit `accept` and
  `risk_acceptance` while retaining safe revise/reject/additional-validation
  choices supplied by the view.
- Harness rendering keeps project-level observations separate from current-Task
  controls and displays Config/Agents/Rules/Hooks/Sandbox/Approval across
  Configured/Loaded/Enforced stages.
- Feature Validation and Decision forms work as native HTML forms. The server
  accepts either its generated hidden CSRF field or the existing exact CSRF
  header, removes the token before calling services, and authenticates the
  session and Origin before parsing an unauthenticated POST body.
- Evidence metadata is the default. Explicit Raw disclosure is decoded with
  replacement, escaped, and rendered only inside `pre`; active markup is never
  inserted.

## Accessibility and visual foundation

- Added the B direction: Warm Paper Neutral surfaces with Ledger Indigo brand
  navigation/action accents in Light and Dark themes. Brand, focus, pass,
  warning, danger, and unknown tokens are distinct.
- The document is Korean, has a skip link, header/navigation/main/footer
  landmarks, one H1, ordered headings, native labels, text-plus-symbol status,
  named keyboard-scrollable table/Diagram regions, and no positive tabindex.
- The bounded SVG uses a Task-derived prefix for every SVG ID, begins with
  `title` and `desc`, uses `aria-labelledby`, and repeats its Evidence links in
  a keyboard-readable HTML fallback. Non-subject relations never create a
  validation URL the opaque route contract would reject.
- CSS includes explicit 320px, 390px, and 1440px boundaries, contained
  table/Diagram overflow, and reduced-motion handling. There are no imports,
  remote URLs, fonts, frameworks, telemetry calls, or runtime dependencies.
- WCAG contrast calculations against the intended surfaces produced Light
  ratios of 4.95:1 or higher for focus and 5.88:1 or higher for displayed text
  tokens; Dark ratios were 7.65:1 or higher for displayed text/status tokens
  and 9.49:1 for focus.

## Export and privacy

- `export_masked_history` accepts only `summary`, `verification`, `guarantees`,
  `history`, and `decision`, deduplicates requested sections, and constructs
  each section from a field allowlist rather than serializing arbitrary view
  content.
- Task export is restricted to public identity fields. Prompt, transcript,
  command output, secret-like fields, raw fields, object paths, configured
  private roots, and any remaining absolute local paths are omitted or masked.
- History JSON remains an HTTP `no-store` attachment with a fixed public
  filename. An explicit `save=1` writes the same masked bytes to a deterministic
  data-root export name via `private_atomic_write`; the directory is 0700, the
  file is 0600, and the local path is absent from response headers and body.

## TDD evidence

1. Renderer/accessibility/export tests first failed on missing
   `dashboard_render`, `dashboard_assets`, and `dashboard_export` modules.
2. Five-route integration tests then failed on Task 3 placeholder documents,
   CSP/body nonce mismatch absence, missing attachment disposition, and the
   header-only CSRF boundary. The route renderers, shared nonce, attachment,
   and hidden-CSRF flow made them GREEN.
3. Default CLI export first returned only `history`; wiring it to the exact
   allowlisted exporter made the service boundary GREEN.
4. Systematic self-review reproduced authentication-after-body-parsing,
   incomplete Decision reference fields, a non-subject broken validation link,
   and missing optional private save as independent RED tests. Each received
   one bounded fix and passed its focused GREEN run.
5. Two wider runs initially found legacy Task 3 test doubles with only `task`
   fields. The renderer correctly requires `TaskReviewView`; updating those
   doubles to the existing full read model made the same focused and security
   suites pass. No identical required verification failed twice after its root
   cause was addressed.

## Verification

- Baseline before implementation: **305 tests passed**.
- Task 4 plan-focused suite: **28 tests passed**.
- Task 1–4 Dashboard rendering/action/security integration: **56 tests
  passed** before the final self-review additions.
- Final full repository discovery: **324 tests passed**, zero failures.
- Exact public-signature introspection: all nine signatures match the plan.
- Python compilation for all changed production and test modules: passed.
- `git diff --check`: passed.
- `pyproject.toml` dependency diff: empty.
- Light/Dark contrast calculation: passed the specified 4.5:1 text and 3:1
  focus thresholds for the tested token/surface pairs.

The full suite emitted only the pre-existing Python 3.12 `fork()` deprecation
warning and the expected negative M3 fixture-drift refusal line. Browser
keyboard/VoiceOver/visual viewport checks and the actual same-Task vertical
remain Task 5 rather than being claimed here.

## Scoped self-review

- All renderer-supplied dynamic text and attributes pass through quoted HTML
  escaping. The document shell accepts only trusted renderer fragments as
  `main`; raw/user content never enters that fragment unescaped.
- Renderer code only displays `allowed_decisions` and source status. Current
  authority, freshness, packet identity, and Gate policy remain in the existing
  action/event transaction boundary.
- The server still exposes exactly the five approved GET route shapes and the
  two approved POST shapes. No home, analytics, asset, or component-catalogue
  route was added.
- No remote asset, client framework, new package, private route token, local
  packet path, raw Event payload, or command output is emitted.

## P1 privacy follow-up: Astra diagnosis and fix

The independent review found a real default Evidence metadata leak through
feature-validation `input_summary` → `exact_scope`. The inherited Sol fix omitted
that uncontrolled field, but its repeated failing assertion also classified the
required `?raw=1` disclosure link as raw-content leakage. The test now inspects
the metadata definition list independently, retains whole-page checks for the
actual private values, and positively checks both the explicit Raw link and
escaped Raw disclosure.

Additional real Store → resolver RED cases exposed quoted-token, multiword
Authorization, JSON API-key, and raw-assignment leaks, plus over-removal of
`draw_count`. The final source projection uses the field allowlist, embedded
path masking, complete masking of recognized sensitive values, and bounded
nested sensitive-key removal. A colon-prefixed path regression is included;
normal tool names, relative scopes, fractions, and public HTTPS references are
preserved. Canonical Evidence and the explicitly disclosed raw object are not
modified.

The corrected route test was also run with the original committed source
boundary injected in memory and still caught the original P1. Final follow-up
verification is **38 focused tests passed**, **326 full repository tests passed**,
all nine public signatures matched, changed Python modules compiled, and
`git diff --check` passed. Existing sandbox socket/bytecode limitations were
resolved through narrowly scoped execution permissions; no repeated Astra
implementation-verification failure reached the stop threshold.

Full evidence and limitations are recorded in `task-4-astra-diagnosis.md`.
Independent gate re-review remains required. No push, PR, merge, or M6 work was
performed in this follow-up.

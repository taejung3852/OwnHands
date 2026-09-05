# Task 4 Astra diagnosis: Evidence metadata privacy

## Outcome

The P1 default Evidence metadata leak is fixed and the mandatory regression
checks are GREEN. Work started from committed `bfc2105`, preserving and reviewing
the uncommitted Sol changes in `dashboard_sources.py` and
`test_dashboard_server.py`. Only the Evidence display privacy boundary and its
tests were changed; Raw disclosure remains explicit, escaped, and available.
Push, PR, merge, and M6 actions were not performed.

## Root causes and independently reproduced evidence

1. The original product defect is real: feature validation persists uncontrolled
   `input_summary` as `EvidenceRecord.exact_scope`. The old source projection
   included it in default metadata, and the old value sanitizer only recognized
   paths at the start of a string. HTML escaping does not hide embedded private
   paths or secrets.
2. The repeated Sol verification failure is a separate test defect. Running
   `PYTHONPATH=src .venv/bin/python -m unittest
   tests.test_dashboard_server.DashboardRouteTests.test_real_evidence_route_masks_sensitive_input_scope_until_explicit_raw_disclosure`
   against the inherited worktree failed only for `forbidden=b'raw='`. The only
   match was the approved link's `?raw=1`, outside the metadata definition list.
   The metadata itself contained none of the test's forbidden values.
3. The inherited implementation needed additional bounded corrections. A real
   Evidence Store → resolver table test reproduced four leaks: a quoted token
   option, a multiword Authorization value, a JSON-form API key assignment, and
   raw markup assigned to `raw`. It also reproduced over-removal of the normal
   nested key `draw_count` because an unbounded `raw` regex matched its middle.
   A final targeted RED demonstrated that `cwd:/Users/private/worktree` escaped
   the path matcher because colon was excluded globally to preserve URLs.

## Minimal correction

- Keep the inherited omission of uncontrolled `exact_scope` from public
  metadata. The selected field allowlist, canonical Evidence, and raw object
  remain intact.
- Keep value masking for embedded Unix, Windows, and file-URI paths, including
  a colon-prefixed Unix path, while preserving relative selection paths,
  fractions, and public HTTPS references.
- Mask the entire string when a sensitive assignment or command option is
  recognized. This avoids attempting to guess where quoted or multiword secrets
  end. Nested sensitive keys are removed using token boundaries and camel-case
  normalization, so ordinary `draw_count` metadata survives.
- Inspect the default metadata definition list independently for raw/secret
  field names. Retain whole-page checks for actual private values, verify that
  default HTML has no Raw `pre`, and positively verify the explicit Raw link.
  The separate Raw response must contain its `pre` and escaped test markup.

The test was not weakened: injecting only the committed `bfc2105` source
projection/sanitizer into the corrected real-route test, in memory without
editing production files, produced five expected assertion failures including
the original private path. The actual source then passed the corrected test.

## Final verification

- Focused Evidence + Task 4 plan suite: **38 passed**.
- Full repository discovery after the final path adjustment: **326 passed**.
- All nine public Task 4 signatures match the plan by introspection.
- Compilation of the three changed Python modules: passed.
- `git diff --check`: passed; no dependency or public-signature changes.

The full suite emitted the existing fork deprecation warning and expected
negative loopback/fixture-drift diagnostic messages, with zero failures.

## Environment and retry accounting

The initial system `python3` is too old for the repository's SQLite `autocommit`
argument; reproduction used the existing Python 3.12 `.venv`. The first focused
suite was otherwise GREEN but its existing actual-server test could not bind a
loopback socket in the sandbox. Compilation similarly lacked permission to
write bytecode in this isolated worktree. Both passed with the narrowly
requested execution permissions. No automatic approval review rejected work.

The expected diagnostic RED cases and baseline mutation are not failed fix
attempts. No mandatory check failed twice after an Astra fix under the required
runtime/permissions. The two-failure stop condition was not reached.

## Boundaries

The sanitizer handles the documented metadata field boundaries and recognized
path/sensitive-key syntax; it is not a claim of general natural-language secret
detection. Raw disclosure remains a deliberate local action and HTML escaping
prevents its bytes from executing. No Raw-sharing claim is made. Browser and
human-observation checks remain Task 5. Independent final gate re-review is
still required; this implementation report does not supersede the earlier
reviewer's gate decision by itself.

## Re-review follow-up: bare Bearer credential

Independent review of `b7dbe81` found one remaining P1:
`Bearer private-value` lacked a sensitive field name or assignment delimiter,
so the value classifier returned it unchanged. This is recorded as **Astra
mandatory privacy verification failure #1**, superseding any implication that
the preceding GREEN tests closed the independent gate.

Before the next fix, the resolver test reproduced the exact value and a mixed
case/tab variant. The real Evidence route test persisted the bare credential
as the Task environment, which feature validation projects into the allowlisted
Evidence environment metadata. Both metadata-region and whole-page assertions
reproduced its disclosure. These are reproductions of review failure #1, not
new post-fix verification attempts.

The sole production change adds case-insensitive Bearer credential syntax to
the existing value classifier, using a word boundary and space/tab separation
before credential characters. Matching values are masked in full. A lone
`bearer`, the prose `bearer-token policy`, and the nonmatching word
`wheelbearer` survive. A phrase that actually has Bearer-plus-credential syntax
is conservatively masked even when intended as prose; the metadata contract
does not require disclosure of such ambiguous credential-shaped text.

Existing public HTTPS links, relative selections, `draw_count`, field filtering,
and explicit escaped Raw disclosure remain covered. No Raw or canonical
Evidence writer, renderer, route signature, or authority behavior changed.

Final post-fix verification: **2 affected tests passed**, **38 focused tests
passed**, **326 full repository tests passed**, all nine public signatures
matched, the changed modules compiled, and `git diff --check` passed. The full
suite emitted only the same existing warnings/negative-fixture diagnostics.
No post-fix mandatory privacy verification failed, so failure #2 was not
reached. Independent gate re-review is still required. No push, PR, or merge
was performed.

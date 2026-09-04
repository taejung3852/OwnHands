# M0-05 — Superpowers skill vendoring spike

- Status: research and recommendation only. No skills, assets, configuration, or notices were copied/created by this spike.
- Checked: 2026-09-04 (Asia/Seoul)
- Source under review: [obra/superpowers](https://github.com/obra/superpowers), release tag [`v6.3.0`](https://github.com/obra/superpowers/tree/v6.3.0).
- Local installation under review: `/Users/parktaejung/.codex/plugins/cache/openai-curated-remote/superpowers/6.3.0`.

## Decision-ready recommendation

Vendor a **small, explicitly named, version-pinned subset** under the DevHarness namespace only after the implementation ADR is approved. Do not vendor or activate Superpowers as a complete plugin. In particular, exclude `using-superpowers`, its global bootstrap/routing behavior, plugin manifest/assets, and all upstream install/update mechanisms.

Start with workflow guidance that complements the DevHarness contract—not a second task router:

| Status | Upstream skill | DevHarness destination / rationale |
|---|---|---|
| Include candidate | `brainstorming` | `dev-harness/brainstorming` after DevHarness Preflight classifies a task; DevHarness owns the approval/contract record. |
| Include candidate | `test-driven-development` | `dev-harness/test-driven-development`; implementation-method guidance, paired with DevHarness Test Design and Regression Gate. |
| Include candidate | `systematic-debugging` | `dev-harness/systematic-debugging`; root-cause-first workflow. |
| Include candidate | `writing-plans` | `dev-harness/writing-plans`; adapt its output location/header so DevHarness controls planning artifacts. |
| Include candidate | `verification-before-completion` | `dev-harness/verification-before-completion`; supplies the pre-completion method, while DevHarness evaluates Evidence/Gates. |
| Include candidate | `requesting-code-review`, `receiving-code-review` | `dev-harness/requesting-code-review`, `dev-harness/receiving-code-review`; use only after DevHarness defines task boundaries and evidence expectations. |
| Defer pending adapter evidence | `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `using-git-worktrees`, `finishing-a-development-branch` | These can create worktrees, delegate, or change integration/cleanup behavior. Their compatibility with DevHarness worktree/task identities, approval model, and CodeX adapter must be tested first. |
| Exclude | `using-superpowers` | Global bootstrap/router conflicts with the product decision that DevHarness is the sole top-level router. |
| Exclude | `writing-skills` | It solves creation/maintenance of upstream-style skills, not DevHarness’s end-user work lifecycle; assess separately if DevHarness later needs a skill-authoring workflow. |

This follows the existing product baseline: DevHarness owns preflight, execution contract, Evidence, Impact Analysis, Regression Gate, and Task Guarantee Report. A vendored methodology skill must neither initiate a task independently nor upgrade `Configured` to `Loaded`, `Enforced`, or `Observed`.

## Why this boundary

The upstream [README](https://github.com/obra/superpowers#the-basic-workflow) presents Superpowers as a complete methodology with automatic skill triggering and a global “check relevant skills before any task” behavior. The installed `using-superpowers` skill requires skill invocation before any response. Those are incompatible with DevHarness’s documented decision that it remains the one top-level router and explicitly excludes the external global router/bootstrap.

The upstream README also identifies its skills as composable and lists the same planning, TDD, debugging, collaboration, review, worktree, and branch-finishing workflows. That supports selective reuse, but it does not establish that the whole plugin is an appropriate DevHarness dependency. The selection above is a product decision based on DevHarness’s existing Control Layer boundaries, not a claim of upstream endorsement.

## License and attribution requirements

The upstream [MIT License at `v6.3.0`](https://github.com/obra/superpowers/blob/v6.3.0/LICENSE) states that the copyright notice and permission notice must be included in **all copies or substantial portions** of the software/documentation. The installed plugin declares `license: "MIT"`, contains the same license text, and attributes copyright to Jesse Vincent (2025).

For every future vendored source file, DevHarness must therefore:

1. Preserve the complete upstream MIT copyright and permission notice in a distributed notice/license artifact—recommended path: `LICENSES/superpowers-MIT.txt`—and reference it from `THIRD_PARTY_NOTICES.md`.
2. In `THIRD_PARTY_NOTICES.md`, identify `obra/superpowers`, upstream URL, version tag, immutable commit SHA, upstream relative path(s), whether the file was changed, and the source SHA-256 at import.
3. Retain existing upstream copyright/license headers if a copied file contains them. If DevHarness materially edits the file, retain the MIT notice and state “modified by DevHarness; derived from …” in the notice/provenance record; do not imply upstream support.
4. Include the notice artifact with any packaged or redistributed DevHarness copy that contains the vendored material. A repository-only acknowledgement is insufficient for a released package that ships the copies.
5. Review every selected skill’s linked local supporting files before copying. A `SKILL.md` is not necessarily self-contained; vendoring a reference-dependent skill without its required referenced materials can change its behavior.

MIT permits copying, modification, publication, distribution, sublicensing, and sale subject to that notice condition. It provides the material “as is” without warranty; DevHarness must not relabel it as a warranty or a broad safety guarantee.

## Provenance, tag and hash evidence

### Official upstream

Read-only `git ls-remote` against the official repository on 2026-09-04 found:

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/obra/superpowers.git` |
| Human-readable release tag | `v6.3.0` |
| Tag object SHA | `86babb696875227929e85420f287d6309374b93f` |
| Dereferenced immutable commit SHA | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` |
| Current upstream `HEAD` at check time | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` |
| Release publication time | 2026-08-12T16:58:30Z, per [official GitHub release](https://github.com/obra/superpowers/releases/tag/v6.3.0) |
| Official tag license SHA-256 | `a37e0e9697144819e1d965176ac4ae5bc3fa02d11e7812036bbcadf6dafe2400` |
| Official tag Codex plugin manifest SHA-256 | `d7ac84a700062e865715f75626945a2a3324778c68dba1a543c7ed41e48def10` |

Use the tag for readability and the dereferenced commit SHA for the actual pin. A tag is a Git ref and can theoretically be moved; the commit SHA is the reproducibility anchor. GitHub's tag API reported this annotated tag as unsigned, so do not describe this pin as cryptographically verified. Future provenance URLs must use the commit, for example:

```text
https://raw.githubusercontent.com/obra/superpowers/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/test-driven-development/SKILL.md
```

### Installed Codex package

The installed cache directory is named `openai-curated-remote/superpowers/6.3.0`. Its `.codex-plugin/plugin.json` declares:

- name `superpowers`, version `6.3.0`, license `MIT`
- repository/homepage `https://github.com/obra/superpowers`
- author `Jesse Vincent <jesse@fsck.com>`

This is evidence of the installed marketplace package’s declared source and version, not a cryptographic proof of how the marketplace built or signed it. Its license content matches upstream’s tag hash, while its plugin manifest hash differs from the upstream tag; therefore **do not use the cached manifest as the import source of truth**. Import only from the official upstream commit URL after re-verifying paths/hashes.

| Local artifact | Local SHA-256 | Comparison |
|---|---|---|
| `LICENSE` | `a37e0e9697144819e1d965176ac4ae5bc3fa02d11e7812036bbcadf6dafe2400` | Matches official `v6.3.0` LICENSE. |
| `.codex-plugin/plugin.json` | `4d92039f08dc19d31e1e4135686a6298f204244ee53ae63ef968b14bfe26908a` | Does not match official tag manifest (`d7ac…`); expected marketplace adaptation is possible, but its reason is unobserved. |

For six representative skills, local and official-tag `SKILL.md` SHA-256 values matched:

| Skill | SHA-256 |
|---|---|
| `brainstorming` | `74edf03ea6d24ef53db48677b93558d14a979bdf052ca3f57ecdca0c66791608` |
| `test-driven-development` | `bf1b8216e523851a411e91d429a7c1c2a173e79d88957bc78e348218d50edd54` |
| `systematic-debugging` | `808fc5717aa88ad65efff312b11c186294d3e6ee301afb584e2f86599b137787` |
| `writing-plans` | `48508f44bbfd7d24b029fbf3a314f3cd14c9615599059366e922f47b8dc08cf2` |
| `verification-before-completion` | `2befe7fc55bcadaa3d97dd9e8efeb633d2561c0ebe74c5a8b17c4d9e7e4520b3` |
| `using-superpowers` (excluded) | `30f2ab78e20ddc27ee7158ae8d4a2abe161c360981c7cc3548070913142d3dc3` |

These hashes establish only the checked files at the recorded version. They do not establish behavior in a future Codex release or validate ancillary files not checked.

## Import manifest and update policy (recommended, not created)

When vendoring is authorized, commit a small machine-readable provenance manifest alongside the copied material. One record per imported file or directory should contain:

```json
{
  "upstream": "https://github.com/obra/superpowers",
  "tag": "v6.3.0",
  "commit": "b36e0829c6d0140e93cfef2ca599b1b07d4a7797",
  "sourcePath": "skills/test-driven-development/SKILL.md",
  "sourceSha256": "bf1b8216e523851a411e91d429a7c1c2a173e79d88957bc78e348218d50edd54",
  "destination": "skills/dev-harness/test-driven-development/SKILL.md",
  "localChanges": false,
  "license": "MIT"
}
```

Do not use a floating branch, `latest`, marketplace cache path, or tag alone as the production source. Updates must be a deliberate change request: select a new immutable commit, retrieve a fresh inventory and hashes, inspect license/notice changes, run behavior tests and DevHarness adapter integration tests, review diffs, update provenance/notices, then approve. No automatic upstream update.

## Behavior and boundary tests required before activation

1. **Discovery/namespace test:** only `dev-harness/*` copies resolve; no upstream `superpowers:*` or global bootstrap is activated by DevHarness’s package.
2. **Router test:** DevHarness Preflight remains first; a vendored skill cannot bypass Contract approval, create a parallel global router, or start implementation before the defined DevHarness decision point.
3. **Evidence test:** the skills’ completion/review language cannot produce a Dashboard `Pass` or guarantee state without DevHarness-required Evidence and Gate evaluation.
4. **Task/worktree test:** deferred skills must prove they preserve task/worktree identity and do not silently create, clean up, or merge the wrong workspace.
5. **Regression test:** each imported skill’s expected trigger/critical rule is tested against the pinned source version; adaptation changes receive a local behavior test rather than assuming text similarity.
6. **Notice/package test:** release artifact inspection confirms the MIT notice and third-party record travel with every distributed copy.

## Risks and non-goals

- **Instruction conflict:** upstream skills are intentionally forceful. Copying them verbatim can override the product’s adaptive Preflight and evidence vocabulary. Namespace and adaptation review are controls, not cosmetic renames.
- **Hidden dependency:** support references (for example, prompt/reference assets beside a skill) can be behaviorally required. Inventory them per selected skill before copying.
- **Autonomy mismatch:** delegation/worktree/finishing skills can make material state changes and therefore remain deferred until contract/adapter integration is validated.
- **Version drift:** current upstream `HEAD` equalled `v6.3.0` when checked, but it is not a future guarantee; import always pins the commit.
- **Non-goal:** this spike does not install, vendor, modify, relicense, or configure Superpowers; it does not conclude that a given skill is suitable without the future behavior tests above.

## Primary-source register

- [Official upstream repository](https://github.com/obra/superpowers) — project scope, skill inventory, Codex marketplace availability, workflow descriptions, and license declaration.
- [Official `v6.3.0` LICENSE](https://github.com/obra/superpowers/blob/v6.3.0/LICENSE) — MIT notice condition and warranty disclaimer.
- [Official `v6.3.0` skill tree](https://github.com/obra/superpowers/tree/v6.3.0/skills) — tagged source layout.
- Official Git repository advertisement queried read-only: `https://github.com/obra/superpowers.git` — tag/commit resolution above.
- Installed Curated Remote package artifacts listed in the local-evidence section above — version/source declaration and local hashes only.

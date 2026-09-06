# OwnHands M4.5 Minimal Vertical Slice Review Package

## Scope

This review package exercises the complete end-to-end vertical slice of M4.5:

```text
User / Agent Request
→ plugin.json Manifest Discovery
→ using-ownhands (Top-level Router Skill)
→ context-validation (Sub-Skill)
→ context.lint (stdio JSON-RPC MCP Tool)
→ devharness Core (lint_context & EvidenceStore)
→ SQLite Catalog (Schema v3) & SHA-256 CAS Storage
→ Option C Standard Response Envelope
→ Skill Decision (pass / soft_block / hard_block)
```

It establishes the proven architectural boundary between Agent Guidance (Skills), Deterministic Tool Invocation (MCP), and Enforced State/Evidence (Core).

## TDD & Verification Evidence

All 258 repository tests pass with zero regressions against existing M0~M4 foundations:

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python -m unittest discover -s tests -v
```

Key verification suites:
1. `tests/test_plugin_manifest.py`: Validates plugin manifest structure, directory resolution, and rejection of invalid configurations.
2. `tests/test_mcp_server.py`: Validates JSON-RPC 2.0 stdio protocol handler, `tools/list`, `tools/call`, Option C envelopes, and conditional evidence persistence.
3. `tests/test_skills.py`: Validates `using-ownhands` and `context-validation` against Core instruction hygiene rules (`lint_context`).
4. `tests/test_m45_vertical_slice.py`: End-to-end integration test running subprocess stdio roundtrips, clean passes, advisory soft blocks, and critical hard blocks.

## Local Reproduction Command

To reproduce the vertical slice on any target project without modifying the repository:

```bash
PYTHONPATH=src uv run --no-project --no-cache --python 3.12 python docs/reviews/m4.5/run_slice.py --data-root /tmp/ownhands-m45-evidence --project /path/to/target_project
```

## Observed Slice Summary

The allowlisted output of the clean slice run is recorded in `docs/reviews/m4.5/observed-slice-summary.json`:

```json
{
  "plugin_name": "ownhands",
  "plugin_version": "0.1.0",
  "tool_invoked": "context.lint",
  "status": "ok",
  "decision": "pass",
  "evidence_id": "sha256:7031f42194e45afaafa46e811c33282a434cadce9af85141f32e857334e8f964",
  "findings_count": 0
}
```

Raw evidence blobs and SQLite catalog files reside strictly outside the Git repository in the provided data root (`/tmp`).

## Architectural Boundaries & Invariants

1. **Core 0-Mutation:** Zero modifications to existing M0~M4 core functions, signatures, or database schemas.
2. **Deterministic Execution:** The AI agent never dynamically writes Python verification code; all inspections are routed through verified MCP handlers.
3. **Sealed Evidence Lineage:** Every evaluated task binds to an immutable SHA-256 CAS object recorded in the SQLite catalog.

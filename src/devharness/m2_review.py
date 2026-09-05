from __future__ import annotations

import json
from pathlib import Path

from .catalog import Catalog
from .control_profile import (
    build_baseline,
    build_execution_contract,
    compile_control_profile,
    profile_project,
    render_control_preview,
    run_interview,
)
from .evidence import EvidenceDraft, EvidenceStore
from .events import EventDraft, EventLog
from .identity import IdentityRegistry
from .paths import DataPaths
from .review import _atomic_write_text


def run_m2_demo(data_root: Path | str, project_root: Path | str, output_path: Path | str, *, observed_at: str) -> dict:
    project_root = Path(project_root).resolve()
    output_path = Path(output_path).resolve()
    stages = []
    event_refs: list[str] = []
    evidence_refs: list[str] = []
    with Catalog.open(DataPaths.resolve(data_root)) as catalog:
        identities = IdentityRegistry(catalog)
        project = identities.register_project(str(project_root))
        worktree = identities.register_worktree(project.project_id, str(project_root))
        task = identities.create_task(worktree.worktree_id, "managed", "synthetic-m2-commit", "m2-fixture", str(project_root), "macos-arm64-python-3.12")
        events = EventLog(catalog)
        events.append(EventDraft(f"task-created:{task.task_id}", task.task_id, "task.created", 1, observed_at, {"mode": "managed"}, "m2-demo", "not_needed"), lambda value: value)
        store = EvidenceStore(catalog, events)

        def record(stage: str, artifact: dict) -> None:
            event_id = f"m2:{task.task_id}:{stage}"
            evidence_id = f"evidence:{task.task_id}:{stage}"
            events.append(EventDraft(event_id, task.task_id, f"m2.{stage}.completed", 1, observed_at, {"stage": stage, "artifact_hash": artifact.get("fingerprint") or artifact.get("diff_hash")}, "m2-demo", "reference_only"), lambda value: value)
            store.put(EvidenceDraft(evidence_id, task.task_id, f"M2-{stage}", "direct_feature_probe", artifact.get("contract_id") or artifact.get("baseline_id") or artifact.get("fingerprint") or stage, stage, "pass", "observed", {"stage": stage, "artifact_ref": artifact.get("fingerprint") or artifact.get("diff_hash") or stage}, json.dumps(artifact, ensure_ascii=False, sort_keys=True).encode("utf-8"), "m2-demo", "redacted"), lambda value: value)
            stages.append(stage)
            event_refs.append(event_id)
            evidence_refs.append(evidence_id)

        identity = {"project_id": project.project_id, "worktree_id": worktree.worktree_id, "environment_ref": task.environment_ref}
        profile = profile_project(project_root, identity, observed_at=observed_at)
        record("profile", profile)
        interview = run_interview(profile, ["low", "none", "none", "none", "tests"])
        record("interview", interview)
        baseline = build_baseline(profile, interview, version=1, predecessor_ref=None, event_refs=list(event_refs), evidence_refs=list(evidence_refs))
        record("baseline", baseline)
        context_refs = [item["source_id"] for item in baseline["sources"] if item["source_type"] in {"agents_instruction", "hwpx_tool_contract"}]
        control_refs = [item["source_id"] for item in baseline["sources"] if item["source_type"] in {"codex_config", "rule", "hook"}]
        overlay = {
            "overlay_version": "1.0", "overlay_id": f"overlay:{task.task_id}",
            "task": {**identity, "task_id": task.task_id, "mode": "managed", "goal": "Review the synthetic HWPX control profile"},
            "baseline_ref": baseline["baseline_id"], "baseline_fingerprint": baseline["fingerprint"],
            "instruction_overlay": {"source_refs": context_refs}, "control_overlay": {"source_refs": control_refs},
            "writable_paths": ["src/**", "output/**"], "protected_targets": [".env", ".git/**"],
            "permission_expansions": [], "approval_triggers": ["external_effect", "protected_target"],
            "validation_criteria": ["python -m unittest -v"], "gate_criteria": ["tests_pass", "no_protected_target_change"],
            "unobserved_paths": baseline["unobserved"],
        }
        contract = build_execution_contract(baseline, overlay, [], now=observed_at)
        record("contract", contract)
        existing = {str(path.relative_to(project_root)): path.read_text(encoding="utf-8") for path in project_root.rglob("*") if path.is_file() and not path.is_symlink() and path.name not in {".env", "credentials.json", "secrets.json"} and path.suffix not in {".pem", ".key"}}
        compiled = compile_control_profile(contract, existing)
        record("compile", compiled)
        evidence_index = {ref: f"evidence/{ref}" for ref in contract["event_refs"] + contract["evidence_refs"]}
        rendered = render_control_preview(contract, compiled, evidence_index)
        preview = {"fingerprint": "sha256:" + __import__("hashlib").sha256(rendered.encode()).hexdigest()}
        record("preview", preview)
        _atomic_write_text(output_path, rendered)
    return {"task_id": task.task_id, "contract_id": contract["contract_id"], "stages": stages, "event_refs": event_refs, "evidence_refs": evidence_refs, "output_path": str(output_path)}

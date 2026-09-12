"""Store supplied historical run observations; does not prepare, launch, or evaluate Control.

These records retain legacy evidence meanings, not M5 Claim/Review verdicts.
"""
from __future__ import annotations

import json
from pathlib import Path

from .catalog import Catalog
from .evidence import EvidenceDraft, EvidenceStore
from .events import EventLog
from .guarantees import GuaranteeEvaluator
from .identity import IdentityRegistry
from .run_records import AppServerRun

_MATRIX_PATH = Path(__file__).resolve().parents[2] / "docs/product/guarantee-matrix.v1.json"


class ManagedTaskError(ValueError):
    """Compatibility error for invalid managed receipt identity or references."""


def _runtime_evidence_fields(
    name: str,
    check_name: str,
    prepared: dict,
    run: AppServerRun,
    result: str,
) -> tuple[str, str, dict]:
    task_id = prepared["task"]["task_id"]
    observations = prepared["runtime_observations"]
    if name == "agents" and check_name == "loaded":
        return (
            "instruction-source",
            "instruction_loading",
            {
                "instruction_sources": list(run.instruction_sources),
                "scope": prepared["configured"]["agents"]["exact_scope"],
                "task_ref": task_id,
                "runtime_version": run.codex_version,
            },
        )
    if name == "hooks" and check_name == "loaded":
        hook = observations["hook"]
        return (
            "hook-receipt",
            "hook_execution",
            {
                "event_type": hook["event_type"],
                "started_or_handler_receipt": hook["item_id"],
                "completed_or_handler_result": result,
                "runtime_version": run.codex_version,
            },
        )
    if name == "sandbox" and check_name == "enforced":
        sandbox = observations["sandbox"]
        return (
            "sandbox-denial",
            "sandbox_probe",
            {
                "active_mode": prepared["sandbox_mode"],
                "exact_boundary": sandbox["exact_scope"],
                "probe": sandbox["probe"],
                "deny_result": "denied" if result == "pass" else "not_denied",
                "runtime_version": run.codex_version,
            },
        )
    if name == "approval" and check_name == "enforced":
        approval = observations["approval"]
        request = next(
            record
            for record in run.records
            if record.kind == "approval_request"
            and record.item_id == approval["item_id"]
        )
        decision = next(
            (
                record.decision
                for record in run.records
                if record.kind == "approval_decision"
                and record.item_id == approval["item_id"]
            ),
            "missing",
        )
        return (
            "approval-transaction",
            "approval_lifecycle",
            {
                "request": str(request.request_id),
                "decision": decision,
                "result": result,
                "exact_action": approval["exact_action"],
                "runtime_version": run.codex_version,
            },
        )
    control = name if check_name == "configured" else f"{name}-{check_name}"
    return (
        f"{control}-configuration",
        "direct_feature_probe",
        {
            "control": control,
            "source_scope": prepared["configured"][name]["exact_scope"],
            "runtime_version": run.codex_version,
        },
    )


def record_run_evidence(
    catalog: Catalog, prepared: dict, run: AppServerRun, controls: dict
) -> dict:
    task_data = prepared["task"]
    task_id = task_data["task_id"]
    try:
        task = IdentityRegistry(catalog).get_task(task_id)
    except ValueError as error:
        raise ManagedTaskError("managed Task identity is not registered") from error
    if any(
        getattr(task, key) != task_data[key]
        for key in ("project_id", "worktree_id", "environment_ref", "mode")
    ) or task.commit != prepared["start_commit"] or task.branch != prepared["branch"] or Path(task.cwd).resolve() != Path(prepared["repository"]):
        raise ManagedTaskError("registered Project/Worktree/Task/Environment mismatch")
    project = catalog.connection.execute(
        "SELECT locator FROM projects WHERE project_id=?", (task.project_id,)
    ).fetchone()
    worktree = catalog.connection.execute(
        "SELECT locator FROM worktrees WHERE worktree_id=?", (task.worktree_id,)
    ).fetchone()
    if (
        project is None
        or worktree is None
        or Path(project["locator"]).resolve() != Path(prepared["repository"])
        or Path(worktree["locator"]).resolve() != Path(prepared["repository"])
    ):
        raise ManagedTaskError("registered Project or Worktree locator mismatch")

    for event_id in prepared["event_refs"]:
        row = catalog.connection.execute(
            "SELECT task_id FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None or row["task_id"] != task_id:
            raise ManagedTaskError(f"Event reference is unresolved: {event_id}")
    for evidence_id in prepared["evidence_refs"]:
        row = catalog.connection.execute(
            "SELECT task_id, purged_at FROM evidence WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()
        if row is None or row["task_id"] != task_id or row["purged_at"] is not None:
            raise ManagedTaskError(
                f"Evidence reference is unresolved: {evidence_id}"
            )
    for record in run.records:
        if record.thread_id not in {None, run.thread_id} or record.turn_id not in {
            None,
            run.turn_id,
        }:
            raise ManagedTaskError("App Server record scope mismatch")

    events = EventLog(catalog)
    store = EvidenceStore(catalog, events)
    new_evidence_refs: list[str] = []
    for name, control in controls.items():
        for check_name in ("configured", "loaded", "enforced"):
            check = control[check_name]
            if check["basis"] != "observed":
                continue
            evidence_id = check["evidence_refs"][0]
            subject_ref, evidence_type, fields = _runtime_evidence_fields(
                name, check_name, prepared, run, check["result"]
            )
            content = json.dumps(
                {
                    "control": name,
                    "check": check_name,
                    "result": check["result"],
                    "thread_id": run.thread_id,
                    "turn_id": run.turn_id,
                    "protocol_fingerprint": run.protocol_fingerprint,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            store.put(
                EvidenceDraft(
                    evidence_id=evidence_id,
                    task_id=task_id,
                    requirement_id=subject_ref,
                    evidence_type=evidence_type,
                    subject_ref=control["control_id"],
                    exact_scope=check["exact_scope"],
                    result=check["result"],
                    basis="observed",
                    fields=fields,
                    content=content,
                    collection_method="m3-managed-app-server",
                    redaction_status="redacted",
                ),
                lambda value: value,
            )
            new_evidence_refs.append(evidence_id)

    restore_id = f"evidence:{task_id}:restore"
    restore = prepared["restore"]
    store.put(
        EvidenceDraft(
            evidence_id=restore_id,
            task_id=task_id,
            requirement_id="restore-verification",
            evidence_type="workspace_restore_point",
            subject_ref=f"task:{task_id}:restore",
            exact_scope=restore["scope"],
            result="pass",
            basis="observed",
            fields={
                "commit_patch_or_reference": restore["commit_patch_or_reference"],
                "patch_hash": restore["patch_hash"],
                "scope": restore["scope"],
                "restore_probe": restore["restore_probe"],
                "result": "pass",
            },
            content=json.dumps(restore, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            ),
            collection_method="m3-managed-restore-check",
            redaction_status="reference_only",
        ),
        lambda value: value,
    )
    new_evidence_refs.append(restore_id)

    evaluator = GuaranteeEvaluator(catalog, store, _MATRIX_PATH)
    control_records = []
    for name, control in controls.items():
        record = {
            "schema_version": "1.0",
            "record_id": f"control:{task_id}:{name}",
            "control_id": control["control_id"],
            "control_type": control["control_type"],
            "scope": {
                "project_id": task.project_id,
                "worktree_id": task.worktree_id,
                "task_id": task.task_id,
                "boundary": control["boundary"],
                "environment_ref": task.environment_ref,
            },
            "checks": {
                check_name: control[check_name]
                for check_name in ("configured", "loaded", "enforced")
            },
        }
        evaluator.record_control_validation(task_id, record)
        control_records.append(record)

    event_refs = [
        f"evidence-recorded:{evidence_id}" for evidence_id in new_evidence_refs
    ] + [
        f"control-validation-recorded:{record['record_id']}"
        for record in control_records
    ]
    return {
        "task_id": task_id,
        "thread_id": run.thread_id,
        "turn_id": run.turn_id,
        "terminal_status": run.terminal_status,
        "codex_version": run.codex_version,
        "protocol_fingerprint": run.protocol_fingerprint,
        "restore": restore,
        "control_records": control_records,
        "event_refs": event_refs,
        "evidence_refs": new_evidence_refs,
    }

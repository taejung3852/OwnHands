from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .catalog import Catalog
from .evidence import EvidenceDraft, EvidenceStore
from .events import EventDraft, EventLog
from .guarantees import GuaranteeEvaluator
from .identity import IdentityRegistry


_MATRIX_PATH = Path(__file__).resolve().parents[2] / "docs/product/guarantee-matrix.v1.json"
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "snapshot",
    "current_diff",
    "current_test",
    "references",
}
_SNAPSHOT_FIELDS = {
    "project_locator",
    "worktree_locator",
    "cwd",
    "commit",
    "branch",
    "environment_ref",
    "mode",
    "observed_at",
}
_DIFF_FIELDS = {
    "start_baseline",
    "end_baseline",
    "patch",
    "patch_hash",
    "scope",
    "observed_at",
}
_TEST_FIELDS = {
    "command",
    "environment",
    "target_commit",
    "selection_scope",
    "result",
    "exit_code",
    "collection_method",
    "executed_at",
}
_SENSITIVE_MARKERS = {
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "privatekey",
    "secret",
    "token",
}
_CONTROL_NAMES = ("config", "agents", "rules", "hooks", "sandbox", "approval")


class ImportedTaskError(ValueError):
    pass


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImportedTaskError(f"{name} must be a non-empty string")
    return value


def _validate_timestamp(value: object, name: str) -> None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ImportedTaskError(f"{name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ImportedTaskError(f"{name} must include a timezone")


def _field_names(value: object) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key in value] + [
            nested
            for child in value.values()
            for nested in _field_names(child)
        ]
    if isinstance(value, list):
        return [nested for child in value for nested in _field_names(child)]
    return []


def _not_run(scope: str) -> dict:
    return {
        "result": "not_run",
        "basis": "unobserved",
        "evidence_refs": [],
        "inference_from": [],
        "checked_at": None,
        "exact_scope": scope,
        "residual_risks": [
            "Imported input does not establish historical managed runtime state"
        ],
    }


def _validate_fixture(fixture: object) -> tuple[dict, dict, dict, list[str]]:
    if not isinstance(fixture, dict):
        raise ImportedTaskError("Imported fixture must be an object")
    for name in _field_names(fixture):
        compact = "".join(character for character in name.lower() if character.isalnum())
        if any(marker in compact for marker in _SENSITIVE_MARKERS):
            raise ImportedTaskError(f"sensitive raw field is not allowed: {name}")
    extra = set(fixture) - _TOP_LEVEL_FIELDS
    if any("desktop" in str(field).lower() or "thread" in str(field).lower() for field in extra):
        raise ImportedTaskError("Desktop identifiers are not accepted by Imported input")
    if any("past" in str(field).lower() or "historical" in str(field).lower() for field in extra):
        raise ImportedTaskError("historical approval or control evidence is forbidden")
    if set(fixture) != _TOP_LEVEL_FIELDS or fixture.get("schema_version") != "1.0":
        raise ImportedTaskError("Imported fixture fields do not match schema")

    snapshot = fixture["snapshot"]
    current_diff = fixture["current_diff"]
    current_test = fixture["current_test"]
    references = fixture["references"]
    if not isinstance(snapshot, dict) or set(snapshot) != _SNAPSHOT_FIELDS:
        raise ImportedTaskError("snapshot fields do not match schema")
    if not isinstance(current_diff, dict) or set(current_diff) != _DIFF_FIELDS:
        raise ImportedTaskError("current diff fields do not match schema")
    if not isinstance(current_test, dict) or set(current_test) != _TEST_FIELDS:
        raise ImportedTaskError("current test receipt fields do not match schema")
    if (
        not isinstance(references, list)
        or any(not isinstance(reference, str) or not reference for reference in references)
        or len(references) != len(set(references))
    ):
        raise ImportedTaskError("duplicate or invalid references are forbidden")

    project_locator = _required_text(
        snapshot.get("project_locator"), "project locator"
    )
    worktree_locator = _required_text(
        snapshot.get("worktree_locator"), "worktree locator"
    )
    cwd = _required_text(snapshot.get("cwd"), "snapshot cwd")
    if project_locator != worktree_locator or project_locator != cwd:
        raise ImportedTaskError("foreign identity does not match snapshot")
    if snapshot.get("mode") != "imported":
        raise ImportedTaskError("snapshot mode must be imported")
    commit = _required_text(snapshot.get("commit"), "snapshot commit")
    _required_text(snapshot.get("branch"), "snapshot branch")
    environment = _required_text(
        snapshot.get("environment_ref"), "snapshot environment"
    )
    _validate_timestamp(snapshot.get("observed_at"), "snapshot observed_at")

    patch = current_diff.get("patch")
    if not isinstance(patch, str):
        raise ImportedTaskError("current diff patch must be text")
    actual_patch_hash = "sha256:" + hashlib.sha256(patch.encode("utf-8")).hexdigest()
    if current_diff.get("patch_hash") != actual_patch_hash:
        raise ImportedTaskError("current diff hash mismatch")
    if (
        current_diff.get("start_baseline") != commit
        or current_diff.get("end_baseline") != f"working-tree:{commit}"
    ):
        raise ImportedTaskError("current diff baseline does not match snapshot")
    _required_text(current_diff.get("scope"), "current diff scope")
    _validate_timestamp(current_diff.get("observed_at"), "current diff observed_at")

    if current_test.get("collection_method") != "direct_execution":
        raise ImportedTaskError("current test receipt must come from direct execution")
    if (
        current_test.get("target_commit") != commit
        or current_test.get("environment") != environment
    ):
        raise ImportedTaskError("current test receipt is stale or foreign")
    _required_text(current_test.get("command"), "current test command")
    _required_text(current_test.get("selection_scope"), "test selection scope")
    result = current_test.get("result")
    exit_code = current_test.get("exit_code")
    if (
        result not in {"pass", "fail"}
        or not isinstance(exit_code, int)
        or isinstance(exit_code, bool)
        or (result == "pass") != (exit_code == 0)
    ):
        raise ImportedTaskError("current test receipt result is inconsistent")
    _validate_timestamp(current_test.get("executed_at"), "test executed_at")
    return snapshot, current_diff, current_test, references


def import_task(fixture: dict, catalog: Catalog) -> dict:
    snapshot, current_diff, current_test, references = _validate_fixture(fixture)
    identities = IdentityRegistry(catalog)
    project = identities.register_project(snapshot["project_locator"])
    worktree = identities.register_worktree(
        project.project_id, snapshot["worktree_locator"]
    )
    task = identities.create_task(
        worktree.worktree_id,
        mode="imported",
        commit=snapshot["commit"],
        branch=snapshot["branch"],
        cwd=snapshot["cwd"],
        environment_ref=snapshot["environment_ref"],
    )
    events = EventLog(catalog)
    task_event_id = f"task-created:{task.task_id}"
    events.append(
        EventDraft(
            event_id=task_event_id,
            task_id=task.task_id,
            event_type="task.created",
            event_version=1,
            occurred_at=snapshot["observed_at"],
            payload={"mode": "imported"},
            collection_method="m3-imported-snapshot",
            redaction_status="not_needed",
        ),
        lambda value: value,
    )
    store = EvidenceStore(catalog, events)

    snapshot_id = f"evidence:{task.task_id}:current-snapshot"
    diff_id = f"evidence:{task.task_id}:current-diff"
    test_id = f"evidence:{task.task_id}:current-test"
    store.put(
        EvidenceDraft(
            evidence_id=snapshot_id,
            task_id=task.task_id,
            requirement_id="current-snapshot",
            evidence_type="direct_feature_probe",
            subject_ref=f"task:{task.task_id}:snapshot",
            exact_scope=snapshot["cwd"],
            result="pass",
            basis="observed",
            fields={
                "snapshot_commit": snapshot["commit"],
                "environment": snapshot["environment_ref"],
                "scope": snapshot["cwd"],
            },
            content=json.dumps(
                snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
            collection_method="provided-synthetic-snapshot",
            redaction_status="not_needed",
        ),
        lambda value: value,
    )
    store.put(
        EvidenceDraft(
            evidence_id=diff_id,
            task_id=task.task_id,
            requirement_id="change-set",
            evidence_type="workspace_diff",
            subject_ref=f"task:{task.task_id}:changes",
            exact_scope=current_diff["scope"],
            result="pass",
            basis="observed",
            fields={
                "start_baseline": current_diff["start_baseline"],
                "end_baseline": current_diff["end_baseline"],
                "diff": current_diff["patch_hash"],
                "scope": current_diff["scope"],
            },
            content=json.dumps(
                current_diff,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            collection_method="provided-current-diff",
            redaction_status="not_needed",
        ),
        lambda value: value,
    )
    store.put(
        EvidenceDraft(
            evidence_id=test_id,
            task_id=task.task_id,
            requirement_id="test-run",
            evidence_type="test_execution",
            subject_ref=f"test-selection:{current_test['selection_scope']}",
            exact_scope=current_test["selection_scope"],
            result=current_test["result"],
            basis="observed",
            fields={
                "command": current_test["command"],
                "environment": current_test["environment"],
                "target_commit": current_test["target_commit"],
                "selection_scope": current_test["selection_scope"],
                "result": current_test["result"],
            },
            content=json.dumps(
                current_test,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            collection_method="direct-test-execution-receipt",
            redaction_status="not_needed",
        ),
        lambda value: value,
    )

    evaluator = GuaranteeEvaluator(catalog, store, _MATRIX_PATH)
    guarantee_report = evaluator.evaluate(task.task_id)
    evaluator.validate_report(guarantee_report)
    guarantee_event_id = f"guarantee-evaluated:{guarantee_report['report_id']}"
    events.append(
        EventDraft(
            event_id=guarantee_event_id,
            task_id=task.task_id,
            event_type="guarantee.evaluated",
            event_version=1,
            occurred_at=current_test["executed_at"],
            payload={"report_id": guarantee_report["report_id"]},
            collection_method="m3-imported-guarantee",
            redaction_status="reference_only",
        ),
        lambda value: value,
    )

    controls = {
        name: {
            "configured": _not_run(name),
            "loaded": _not_run(name),
            "enforced": _not_run(name),
        }
        for name in _CONTROL_NAMES
    }
    evidence_refs = [snapshot_id, diff_id, test_id]
    return {
        "task_id": task.task_id,
        "project_id": project.project_id,
        "worktree_id": worktree.worktree_id,
        "mode": "imported",
        "snapshot": {
            "basis": "observed",
            "commit": snapshot["commit"],
            "evidence_ref": snapshot_id,
        },
        "current_diff": {
            "basis": "observed",
            "patch_hash": current_diff["patch_hash"],
            "evidence_ref": diff_id,
        },
        "current_test": {
            "basis": "observed",
            "result": current_test["result"],
            "evidence_ref": test_id,
        },
        "controls": controls,
        "input_references": list(references),
        "evidence_refs": evidence_refs,
        "event_refs": [
            task_event_id,
            *(f"evidence-recorded:{evidence_id}" for evidence_id in evidence_refs),
            guarantee_event_id,
        ],
        "guarantee_report": guarantee_report,
    }

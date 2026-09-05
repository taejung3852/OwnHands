from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path

from .catalog import Catalog
from .codex_app_server import AppServerRun
from .control_runtime import evaluate_runtime_controls
from .evidence import EvidenceDraft, EvidenceStore
from .events import EventLog
from .guarantees import GuaranteeEvaluator
from .identity import IdentityRegistry


_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_RECORD_HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_MATRIX_PATH = Path(__file__).resolve().parents[2] / "docs/product/guarantee-matrix.v1.json"
_SOURCE_NAMES = {
    "codex_config": "config",
    "agents_instruction": "agents",
    "rule": "rules",
    "hook": "hooks",
}


class ManagedTaskError(ValueError):
    pass


def _canonical_hash(value: dict) -> str:
    document = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(document.encode("utf-8")).hexdigest()


def _content_hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _document_fingerprint(document: object, name: str) -> str:
    if not isinstance(document, dict):
        raise ManagedTaskError(f"{name} must be an object")
    fingerprint = document.get("fingerprint")
    material = {key: value for key, value in document.items() if key != "fingerprint"}
    if fingerprint != _canonical_hash(material):
        raise ManagedTaskError(f"{name} fingerprint mismatch")
    return fingerprint


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManagedTaskError(f"{name} must be a non-empty string")
    return value


def _timestamp(value: object, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ManagedTaskError(f"{name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ManagedTaskError(f"{name} must include a timezone")
    return parsed


def _git(repository: Path, *arguments: str, binary: bool = False) -> str | bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=not binary,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ManagedTaskError("managed target is not a valid Git repository") from error
    return completed.stdout


def _repository_root(value: object) -> Path:
    repository = Path(_required_text(value, "repository")).resolve()
    marker = repository / ".ownhands-disposable"
    if not repository.is_dir() or not marker.is_file() or marker.is_symlink():
        raise ManagedTaskError("managed target requires a disposable repository marker")
    top_level = str(_git(repository, "rev-parse", "--show-toplevel")).strip()
    if Path(top_level).resolve() != repository:
        raise ManagedTaskError("managed target must be the exact Git repository root")
    return repository


def verify_start_restore(
    repository: Path, start_commit: str, patch_hash: str
) -> dict:
    repository = _repository_root(str(repository))
    start_commit = _required_text(start_commit, "start commit")
    if not isinstance(patch_hash, str) or not _HASH_PATTERN.fullmatch(patch_hash):
        raise ManagedTaskError("patch hash must be a sha256 fingerprint")
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{start_commit}^{{commit}}"],
            cwd=repository,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ManagedTaskError("start commit does not resolve") from error
    patch = _git(repository, "diff", "--binary", start_commit, binary=True)
    actual_patch_hash = _content_hash(patch)
    if actual_patch_hash != patch_hash:
        raise ManagedTaskError("current patch does not match patch fingerprint")
    return {
        "result": "pass",
        "basis": "observed",
        "commit_patch_or_reference": start_commit,
        "patch_hash": patch_hash,
        "scope": str(repository),
        "restore_probe": "start commit resolves and current binary patch matches",
    }


def prepare_managed_task(request: dict, *, now: str) -> dict:
    if not isinstance(request, dict):
        raise ManagedTaskError("managed request must be an object")
    repository = _repository_root(request.get("repository"))
    baseline = request.get("baseline")
    contract = request.get("contract")
    baseline_fingerprint = _document_fingerprint(baseline, "baseline")
    contract_fingerprint = _document_fingerprint(contract, "contract")
    task = request.get("task")
    if not isinstance(task, dict) or not isinstance(contract.get("task"), dict):
        raise ManagedTaskError("managed task identity is missing")
    for key in ("project_id", "worktree_id", "task_id", "environment_ref"):
        _required_text(task.get(key), f"task {key}")
        if task.get(key) != contract["task"].get(key):
            raise ManagedTaskError(f"managed task {key} does not match contract")
    if task.get("mode") != "managed" or contract["task"].get("mode") != "managed":
        raise ManagedTaskError("managed task mode does not match contract")
    for key in ("project_id", "worktree_id", "environment_ref"):
        if baseline.get(key) != task.get(key):
            raise ManagedTaskError(f"baseline {key} does not match task")
    if (
        contract.get("baseline_ref") != baseline.get("baseline_id")
        or contract.get("baseline_fingerprint") != baseline_fingerprint
    ):
        raise ManagedTaskError("contract baseline binding mismatch")
    freshness = request.get("freshness")
    if freshness != {"status": "fresh", "basis": "observed"}:
        raise ManagedTaskError("managed start requires observed fresh baseline")
    if contract.get("gate_status") != "ready_for_preview":
        raise ManagedTaskError("contract gate is not ready")

    approval = request.get("approval")
    if not isinstance(approval, dict):
        raise ManagedTaskError("explicit managed-start approval is missing")
    now_value = _timestamp(now, "now")
    expires_at = _timestamp(approval.get("expires_at"), "approval expires_at")
    if not all(
        (
            approval.get("decision") == "approved",
            approval.get("decision_source") == "explicit_product_approval",
            approval.get("contract_ref") == contract.get("contract_id"),
            approval.get("task_id") == task.get("task_id"),
            approval.get("scope") == "managed_task_start",
            expires_at > now_value,
        )
    ):
        raise ManagedTaskError("managed-start approval scope is invalid or expired")

    required_event_refs = set(baseline.get("event_refs", [])) | set(
        contract.get("event_refs", [])
    )
    required_evidence_refs = set(baseline.get("evidence_refs", [])) | set(
        contract.get("evidence_refs", [])
    )
    if not required_event_refs <= set(request.get("available_event_refs", [])):
        raise ManagedTaskError("Event reference closure failed")
    if not required_evidence_refs <= set(request.get("available_evidence_refs", [])):
        raise ManagedTaskError("Evidence reference closure failed")

    configured = {
        name: {"observed": False, "exact_scope": ""}
        for name in ("config", "agents", "rules", "hooks")
    }
    sources = baseline.get("sources")
    if not isinstance(sources, list):
        raise ManagedTaskError("baseline sources must be an array")
    for source in sources:
        if not isinstance(source, dict) or source.get("source_type") not in _SOURCE_NAMES:
            continue
        relative = Path(_required_text(source.get("path"), "source path"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ManagedTaskError("configured source escapes repository")
        path = repository / relative
        if not path.is_file() or path.is_symlink():
            raise ManagedTaskError("configured source is unavailable")
        if source.get("content_hash") != _content_hash(path.read_bytes()):
            raise ManagedTaskError("configured source hash mismatch")
        name = _SOURCE_NAMES[source["source_type"]]
        configured[name] = {"observed": True, "exact_scope": relative.as_posix()}

    config_path = repository / ".codex/config.toml"
    try:
        active_config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ManagedTaskError("supported project config is unavailable") from error
    sandbox_mode = _required_text(request.get("sandbox_mode"), "sandbox mode")
    approval_policy = _required_text(
        request.get("approval_policy"), "approval policy"
    )
    if (
        active_config.get("sandbox_mode") != sandbox_mode
        or active_config.get("approval_policy") != approval_policy
    ):
        raise ManagedTaskError("configured sandbox or approval policy mismatch")
    configured["sandbox"] = {"observed": True, "exact_scope": sandbox_mode}
    configured["approval"] = {"observed": True, "exact_scope": approval_policy}

    start_commit = _required_text(request.get("start_commit"), "start commit")
    patch_hash = request.get("patch_hash")
    restore = verify_start_restore(repository, start_commit, patch_hash)
    branch = _required_text(request.get("branch"), "branch")
    runtime_observations = request.get("runtime_observations", {})
    if not isinstance(runtime_observations, dict):
        raise ManagedTaskError("runtime observations must be an object")
    observation_fields = {
        "sandbox": ("item_id", "exact_scope", "probe", "terminal_payload_hash"),
        "approval": ("item_id", "exact_scope", "exact_action", "request_payload_hash"),
        "hook": (
            "item_id",
            "exact_scope",
            "event_type",
            "started_payload_hash",
            "completed_payload_hash",
        ),
    }
    for name, fields in observation_fields.items():
        observation = runtime_observations.get(name)
        if observation is None:
            continue
        if not isinstance(observation, dict):
            raise ManagedTaskError(f"{name} runtime observation must be an object")
        for field in fields:
            value = _required_text(
                observation.get(field), f"{name} runtime observation {field}"
            )
            if field.endswith("payload_hash") and not _RECORD_HASH_PATTERN.fullmatch(
                value
            ):
                raise ManagedTaskError(
                    f"{name} runtime observation payload hash is invalid"
                )
    sandbox_observation = runtime_observations.get("sandbox")
    if sandbox_observation is not None and sandbox_observation.get("attempted") is not True:
        raise ManagedTaskError("sandbox runtime observation requires an attempted probe")
    if (
        sandbox_observation is not None
        and sandbox_observation.get("probe") == "deterministic_cli_sandbox"
        and (
            sandbox_observation.get("denied") is not True
            or sandbox_observation.get("exit_code") != 1
        )
    ):
        raise ManagedTaskError("deterministic sandbox observation is not a denial")

    return {
        "repository": str(repository),
        "task": {key: task[key] for key in ("project_id", "worktree_id", "task_id", "environment_ref", "mode")},
        "branch": branch,
        "start_commit": start_commit,
        "patch_hash": patch_hash,
        "baseline_fingerprint": baseline_fingerprint,
        "contract_fingerprint": contract_fingerprint,
        "contract_id": contract["contract_id"],
        "event_refs": sorted(required_event_refs),
        "evidence_refs": sorted(required_evidence_refs),
        "checked_at": now,
        "configured": configured,
        "runtime_observations": runtime_observations,
        "restore": restore,
        "sandbox_mode": sandbox_mode,
        "approval_policy": approval_policy,
    }


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


def record_managed_run(
    catalog: Catalog, prepared: dict, run: AppServerRun
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

    controls = evaluate_runtime_controls(prepared, run)
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

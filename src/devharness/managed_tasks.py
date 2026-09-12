from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path

from .catalog import Catalog
from .run_records import AppServerRun
from .run_evidence import ManagedTaskError, record_run_evidence
from .control_runtime import evaluate_runtime_controls


_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_RECORD_HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_SOURCE_NAMES = {
    "codex_config": "config",
    "agents_instruction": "agents",
    "rule": "rules",
    "hook": "hooks",
}


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


def record_managed_run(catalog: Catalog, prepared: dict, run: AppServerRun) -> dict:
    """Legacy Control evaluation adapter; evidence storage remains independently reusable."""
    controls = evaluate_runtime_controls(prepared, run)
    return record_run_evidence(catalog, prepared, run, controls)

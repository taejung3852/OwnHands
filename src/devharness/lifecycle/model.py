from __future__ import annotations

import hashlib
import json
from typing import Iterator


SCHEMA_VERSION = 1
NAMESPACE = "ownhands.lifecycle"

KINDS = {
    "work_issue",
    "attempt",
    "spec",
    "spec_approval",
    "code_state",
    "environment",
    "baseline",
    "evidence_binding",
    "observation",
    "review",
    "snapshot",
    "human_decision",
    "outcome",
}

CLAIM_STATES = {"verified", "failed", "inconclusive", "unobserved"}
FRESHNESS_STATES = {"current", "stale", "unknown"}
RESULTS = {"pass", "fail", "not_run", "inconclusive"}
BASES = {"observed", "inferred", "unobserved"}

STAGE_SCOPE_KEYS = {
    "goal": {"project_id"},
    "issue": {"project_id"},
    "spec": {"project_id", "issue_id"},
    "baseline": {"project_id", "issue_id", "task_id", "attempt_id"},
    "execution": {"project_id", "issue_id", "task_id", "attempt_id"},
    "review": {"project_id", "issue_id", "task_id", "attempt_id"},
    "decision": {"project_id", "issue_id", "task_id", "attempt_id"},
}


def canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"lifecycle value must be JSON serializable: {error}") from error


def fingerprint(value: object) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def is_reference(value: object) -> bool:
    return isinstance(value, dict) and {"kind", "id", "revision", "hash"} <= set(value)


def references(value: object, path: tuple[object, ...] = ()) -> Iterator[tuple[tuple[object, ...], dict]]:
    if is_reference(value):
        yield path, value
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from references(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from references(child, (*path, index))


def require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def require_sha256(value: object, name: str) -> str:
    value = require_text(value, name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def environment_state(description: str, details: dict | None = None) -> dict:
    description = require_text(description, "environment description")
    if details is None:
        details = {}
    if not isinstance(details, dict):
        raise ValueError("environment details must be an object")
    body = {
        "environment_version": 1,
        "description": description,
        "details": json.loads(canonical_json(details)),
    }
    return {**body, "fingerprint": fingerprint(body)}


def validate_scope(scope: object) -> dict:
    if not isinstance(scope, dict):
        raise ValueError("scope must be an object")
    allowed = {"project_id", "issue_id", "task_id", "attempt_id"}
    if set(scope) - allowed:
        raise ValueError("scope contains unsupported fields")
    require_text(scope.get("project_id"), "scope project_id")
    if "attempt_id" in scope and not {"issue_id", "task_id"} <= set(scope):
        raise ValueError("attempt scope requires issue_id and task_id")
    if "task_id" in scope and "issue_id" not in scope:
        raise ValueError("task scope requires issue_id")
    for key, value in scope.items():
        require_text(value, f"scope {key}")
    return dict(scope)


def reference(kind: str, logical_id: str, revision: int, record_hash: str) -> dict:
    return {"kind": kind, "id": logical_id, "revision": revision, "hash": record_hash}

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from .dashboard_security import mask_dashboard_value
from .dashboard_view import TaskReviewView


_ALLOWED_SECTIONS = {"summary", "verification", "guarantees", "history", "decision"}
_TASK_FIELDS = (
    "task_id",
    "project_id",
    "worktree_id",
    "mode",
    "commit",
    "branch",
    "environment_ref",
)
_SUMMARY_FIELDS = (
    "goal",
    "change_statement",
    "changed_paths",
    "declared_relations",
    "gate",
    "warnings",
)
_VERIFICATION_FIELDS = (
    "kind",
    "test_id",
    "gap_id",
    "criterion_id",
    "subject_ref",
    "result",
    "source_result",
    "basis",
    "evidence_refs",
)
_GUARANTEE_FIELDS = (
    "claim_id",
    "status",
    "verdict",
    "basis",
    "permitted_statement",
    "evidence_refs",
    "residual_risks",
)
_HISTORY_FIELDS = (
    "sequence",
    "event_id",
    "event_type",
    "occurred_at",
    "redaction_status",
    "references",
)
_HISTORY_REFERENCE_FIELDS = (
    "evidence_id",
    "packet_fingerprint",
    "assurance_packet_fingerprint",
    "gate_fingerprint",
    "gate_decision",
    "decision",
    "evidence_refs",
)
_DECISION_FIELDS = (
    "submission_allowed",
    "allowed_decisions",
    "gate",
    "reason",
    "current",
)
_CURRENT_DECISION_FIELDS = (
    "decision",
    "decision_source",
    "actor_ref",
    "reason",
    "residual_risks",
    "follow_up",
    "evidence_refs",
    "occurred_at",
    "assurance_packet_fingerprint",
    "gate_fingerprint",
)
_ABSOLUTE_UNIX_PATH = re.compile(r"(?<![A-Za-z0-9._-])/(?:[^\s,;\"'<>]+/)*[^\s,;\"'<>]+")
_ABSOLUTE_WINDOWS_PATH = re.compile(r"(?i)(?<![A-Za-z0-9])\b[A-Z]:\\[^\s,;\"'<>]+")


def _pick(value: object, fields: Sequence[str]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {field: value[field] for field in fields if field in value}


def _section_value(view: TaskReviewView, section: str) -> object:
    value = getattr(view, section)
    if section == "summary":
        return _pick(value, _SUMMARY_FIELDS)
    if section == "verification":
        return [_pick(row, _VERIFICATION_FIELDS) for row in value]
    if section == "guarantees":
        return [_pick(row, _GUARANTEE_FIELDS) for row in value]
    if section == "history":
        rows = []
        for row in value:
            safe = _pick(row, _HISTORY_FIELDS)
            safe["references"] = _pick(safe.get("references"), _HISTORY_REFERENCE_FIELDS)
            rows.append(safe)
        return rows
    safe = _pick(value, _DECISION_FIELDS)
    if "current" in safe and safe["current"] is not None:
        safe["current"] = _pick(safe["current"], _CURRENT_DECISION_FIELDS)
    return safe


def _remove_absolute_paths(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _remove_absolute_paths(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_remove_absolute_paths(item) for item in value]
    if isinstance(value, str):
        masked = _ABSOLUTE_WINDOWS_PATH.sub("[redacted-local-path]", value)
        return _ABSOLUTE_UNIX_PATH.sub("[redacted-local-path]", masked)
    return value


def export_masked_history(
    *,
    view: TaskReviewView,
    sections: Sequence[str],
    private_roots: Sequence[Path],
    exported_at: str,
) -> bytes:
    requested = tuple(dict.fromkeys(sections))
    unknown = set(requested) - _ALLOWED_SECTIONS
    if unknown:
        raise ValueError(f"unknown export sections: {sorted(unknown)}")
    payload: dict[str, object] = {"task": _pick(view.task, _TASK_FIELDS)}
    payload.update({name: _section_value(view, name) for name in requested})
    payload["exported_at"] = exported_at
    masked = mask_dashboard_value(payload, private_roots=private_roots)
    safe = _remove_absolute_paths(masked)
    return json.dumps(
        safe,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

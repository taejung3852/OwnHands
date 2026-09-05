from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime

from .assurance import fingerprint
from .dashboard_security import require_opaque_identifier
from .evidence import EvidenceRecord, EvidenceStore
from .identity import TaskIdentity
from .m4_review import validate_packet_document


_CONTROL_NAMES = ("config", "agents", "rules", "hooks", "sandbox", "approval")
_STAGES = ("configured", "loaded", "enforced")
_M3_RESULTS = {"pass", "fail", "not_run", "not_applicable"}
_BASES = {"observed", "inferred", "unobserved"}
_REFERENCE = re.compile(r"[A-Za-z0-9:._-]+\Z")
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
_GATE_CHECK_NAMES = {
    "event_evidence_closure",
    "protocol_version",
    "identity_closure",
    "instruction_loaded",
    "sandbox_denial",
    "approval_chain",
    "restore_receipt",
    "terminal_turn",
}
_SAFE_METADATA_FIELDS = {
    "adapter",
    "environment",
    "human_observation",
    "observed_at",
    "packet_fingerprint",
    "selection_scope",
    "target_commit",
    "tool",
}
_EMBEDDED_FILE_URI = re.compile(r"(?i)\bfile://[^\s,;\"'<>]+")
_EMBEDDED_UNIX_PATH = re.compile(
    r"(?<![/A-Za-z0-9._-])/(?!/)(?:[^\s,;\"'<>]+/)*[^\s,;\"'<>]+"
)
_EMBEDDED_WINDOWS_PATH = re.compile(
    r"(?i)(?<![A-Za-z0-9._-])(?:[A-Z]:[\\/]|\\\\)[^\s,;\"'<>]+"
)
_SENSITIVE_METADATA_NAME = (
    r"(?:api[_-]?key|access[_-]?(?:key|token)|private[_-]?key|raw|secret|"
    r"password|passwd|token|credential|cookie|authorization|prompt|transcript|"
    r"object[_-]?(?:rel)?path|data[_-]?root|input[_-]?summary|command(?:[_-]?output)?)"
)
_SENSITIVE_METADATA_KEY = re.compile(
    rf"(?i)(?:^|[_\W]){_SENSITIVE_METADATA_NAME}(?:$|[_\W])"
)
_SENSITIVE_METADATA_TEXT = re.compile(
    rf"(?i)(?<![A-Za-z0-9_])(?:--{_SENSITIVE_METADATA_NAME}(?:\s+|=)|"
    rf"{_SENSITIVE_METADATA_NAME}[\"']?\s*[:=])"
)


@dataclass(frozen=True)
class SourceClosure:
    source: str
    scope: str
    status: str
    task_applicable: bool
    observed_at: str | None
    fingerprint: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceView:
    evidence_id: str
    reference_kind: str
    task_id: str
    result: str
    basis: str
    content_hash: str | None
    content_size: int | None
    redaction_status: str
    raw_available: bool
    metadata: dict


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _hash(value: object, name: str) -> str:
    text = _text(value, name)
    if _HASH.fullmatch(text) is None:
        raise ValueError(f"{name} must be a sha256 fingerprint")
    return text


def _timestamp(value: object, name: str) -> str:
    text = _text(value, name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return text


def _exact(value: object, fields: set[str], name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    if set(value) != fields:
        missing = sorted(fields - set(value))
        unexpected = sorted(set(value) - fields)
        raise ValueError(
            f"{name} fields mismatch; missing={missing}, unexpected={unexpected}"
        )
    return value


def _refs(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    if any(
        not isinstance(item, str) or _REFERENCE.fullmatch(item) is None
        for item in value
    ):
        raise ValueError(f"{name} contains an invalid reference")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} contains duplicate references")
    return list(value)


def _control_check(value: object, name: str) -> dict:
    check = _exact(value, {"result", "basis", "evidence_refs"}, name)
    if check["result"] not in _M3_RESULTS or check["basis"] not in _BASES:
        raise ValueError(f"{name} result or basis is invalid")
    refs = _refs(check["evidence_refs"], f"{name}.evidence_refs")
    if check["basis"] == "observed" and not refs:
        raise ValueError(f"{name} observed check lacks Evidence")
    if check["result"] == "not_run" and check["basis"] != "unobserved":
        raise ValueError(f"{name} not_run check must be unobserved")
    return check


def _controls(value: object, name: str, *, imported: bool) -> dict:
    controls = _exact(value, set(_CONTROL_NAMES), name)
    for control_name in _CONTROL_NAMES:
        stages = _exact(
            controls[control_name], set(_STAGES), f"{name}.{control_name}"
        )
        for stage in _STAGES:
            check = _control_check(
                stages[stage], f"{name}.{control_name}.{stage}"
            )
            if imported and check != {
                "result": "not_run",
                "basis": "unobserved",
                "evidence_refs": [],
            }:
                raise ValueError(
                    "Imported historical controls must remain not_run/unobserved"
                )
    return controls


def _gate_check(value: object, name: str) -> dict:
    check = _exact(value, {"result", "basis", "evidence_refs"}, name)
    if check["result"] not in {"pass", "fail"} or check["basis"] != "observed":
        raise ValueError(f"{name} is invalid")
    _refs(check["evidence_refs"], f"{name}.evidence_refs")
    return check


def m3_task_ref(task_id: str) -> str:
    return fingerprint({"task_id": _text(task_id, "task_id")})


def validate_m3_packet(packet: object) -> dict:
    document = _exact(
        packet,
        {
            "packet_id",
            "schema_version",
            "generated_at",
            "probe_kind",
            "runtime",
            "managed",
            "imported",
            "runtime_gate",
            "human_friction",
        },
        "M3 packet",
    )
    if document["schema_version"] != "1.0":
        raise ValueError("M3 packet schema version is invalid")
    _timestamp(document["generated_at"], "M3 generated_at")
    if document["probe_kind"] not in {"fixture", "live"}:
        raise ValueError("M3 probe_kind is invalid")
    expected = fingerprint({key: value for key, value in document.items() if key != "packet_id"})
    if _hash(document["packet_id"], "M3 packet_id") != expected:
        raise ValueError("M3 packet fingerprint does not match its contents")

    runtime = _exact(
        document["runtime"],
        {
            "codex_version",
            "protocol_fingerprint",
            "model",
            "reasoning_effort",
            "terminal_status",
        },
        "M3 runtime",
    )
    for key, value in runtime.items():
        _text(value, f"M3 runtime.{key}")
    _hash(runtime["protocol_fingerprint"], "M3 runtime.protocol_fingerprint")

    managed = _exact(
        document["managed"],
        {
            "mode",
            "task_ref",
            "thread_ref",
            "event_refs",
            "evidence_refs",
            "controls",
            "restore",
        },
        "M3 managed",
    )
    if managed["mode"] != "managed":
        raise ValueError("M3 managed mode is invalid")
    _hash(managed["task_ref"], "M3 managed.task_ref")
    _hash(managed["thread_ref"], "M3 managed.thread_ref")
    event_refs = _refs(managed["event_refs"], "M3 managed.event_refs")
    evidence_refs = _refs(managed["evidence_refs"], "M3 managed.evidence_refs")
    controls = _controls(managed["controls"], "M3 managed.controls", imported=False)
    check_refs = {
        reference
        for control in controls.values()
        for check in control.values()
        for reference in check["evidence_refs"]
    }
    if not check_refs <= set(evidence_refs):
        raise ValueError("M3 Control Evidence reference closure failed")
    expected_events = {f"evidence-recorded:{reference}" for reference in evidence_refs}
    if not expected_events <= set(event_refs):
        raise ValueError("M3 Event/Evidence closure failed")
    restore = _exact(
        managed["restore"],
        {"result", "basis", "commit_ref", "patch_hash", "evidence_refs"},
        "M3 managed.restore",
    )
    if restore["result"] != "pass" or restore["basis"] != "observed":
        raise ValueError("M3 restore is not observed pass")
    _hash(restore["commit_ref"], "M3 restore.commit_ref")
    _hash(restore["patch_hash"], "M3 restore.patch_hash")
    restore_refs = _refs(restore["evidence_refs"], "M3 restore.evidence_refs")
    if not restore_refs or not set(restore_refs) <= set(evidence_refs):
        raise ValueError("M3 restore Evidence reference closure failed")

    imported = _exact(
        document["imported"],
        {"mode", "task_ref", "evidence_refs", "controls", "limitation"},
        "M3 imported",
    )
    if imported["mode"] != "imported":
        raise ValueError("M3 imported mode is invalid")
    _hash(imported["task_ref"], "M3 imported.task_ref")
    _refs(imported["evidence_refs"], "M3 imported.evidence_refs")
    _controls(imported["controls"], "M3 imported.controls", imported=True)
    _text(imported["limitation"], "M3 imported.limitation")

    gate = _exact(
        document["runtime_gate"],
        {"result", "basis", "checks", "residual_risks"},
        "M3 runtime_gate",
    )
    if gate["result"] not in {"pass", "blocked"} or gate["basis"] not in {
        "observed",
        "unobserved",
    }:
        raise ValueError("M3 runtime Gate is invalid")
    if not isinstance(gate["checks"], dict) or set(gate["checks"]) != _GATE_CHECK_NAMES:
        raise ValueError("M3 runtime Gate check closure failed")
    for name, check in gate["checks"].items():
        _text(name, "M3 runtime Gate check name")
        validated = _gate_check(check, f"M3 runtime_gate.checks.{name}")
        if not set(validated["evidence_refs"]) <= set(evidence_refs):
            raise ValueError("M3 runtime Gate Evidence reference closure failed")
    expected_gate = (
        "pass"
        if document["probe_kind"] == "live"
        and all(check["result"] == "pass" for check in gate["checks"].values())
        else "blocked"
    )
    expected_basis = "observed" if document["probe_kind"] == "live" else "unobserved"
    if gate["result"] != expected_gate or gate["basis"] != expected_basis:
        raise ValueError("M3 runtime Gate result is not closed")
    risks = gate["residual_risks"]
    if not isinstance(risks, list) or any(not isinstance(item, str) or not item for item in risks):
        raise ValueError("M3 runtime Gate residual risks are invalid")

    friction = _exact(
        document["human_friction"], {"result", "basis", "issue"}, "M3 human_friction"
    )
    if friction["result"] != "not_run" or friction["basis"] != "unobserved":
        raise ValueError("M3 human friction must remain not_run/unobserved")
    _text(friction["issue"], "M3 human_friction.issue")
    return copy.deepcopy(document)


def validate_m3_source(*, task: TaskIdentity, packet: object) -> SourceClosure:
    try:
        validated = validate_m3_packet(packet)
    except (TypeError, ValueError) as error:
        packet_id = packet.get("packet_id") if isinstance(packet, dict) else None
        return SourceClosure(
            source="m3",
            scope="project",
            status="invalid",
            task_applicable=False,
            observed_at=None,
            fingerprint=packet_id if isinstance(packet_id, str) else None,
            reasons=(str(error),),
        )
    matches = validated["managed"]["task_ref"] == m3_task_ref(task.task_id)
    return SourceClosure(
        source="m3",
        scope="task" if matches else "project",
        status="closed" if matches else "mismatch",
        task_applicable=matches,
        observed_at=validated["generated_at"],
        fingerprint=validated["packet_id"],
        reasons=() if matches else ("task_ref mismatch",),
    )


def validate_m4_source(*, task: TaskIdentity, packet: object) -> SourceClosure:
    try:
        validated = validate_packet_document(packet)
    except (TypeError, ValueError) as error:
        packet_fingerprint = packet.get("fingerprint") if isinstance(packet, dict) else None
        return SourceClosure(
            source="m4",
            scope="task",
            status="invalid",
            task_applicable=False,
            observed_at=None,
            fingerprint=packet_fingerprint if isinstance(packet_fingerprint, str) else None,
            reasons=(str(error),),
        )
    expected = {
        "project_id": task.project_id,
        "worktree_id": task.worktree_id,
        "task_id": task.task_id,
        "environment_ref": task.environment_ref,
        "mode": task.mode,
    }
    reasons = [
        f"{name} mismatch"
        for name, value in expected.items()
        if validated["task"].get(name) != value
    ]
    if validated["restore_point"].get("start_commit") != task.commit:
        reasons.append("start commit mismatch")
    return SourceClosure(
        source="m4",
        scope="task",
        status="closed" if not reasons else "mismatch",
        task_applicable=not reasons,
        observed_at=validated["observed_at"],
        fingerprint=validated["fingerprint"],
        reasons=tuple(reasons),
    )


def _safe_object_path(store: EvidenceStore, record: EvidenceRecord) -> None:
    root = store.catalog.paths.objects.resolve()
    try:
        relative = record.object_path.relative_to(store.catalog.paths.objects)
    except ValueError as error:
        raise ValueError("Evidence object escaped the Store root") from error
    current = store.catalog.paths.objects
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Evidence object path must not contain a symbolic link")
    try:
        resolved = record.object_path.resolve(strict=True)
    except OSError as error:
        raise ValueError("Evidence object is unavailable") from error
    if root not in resolved.parents:
        raise ValueError("Evidence object escaped the Store root")


def _store_view(record: EvidenceRecord) -> EvidenceView:
    metadata = {
        "requirement_id": record.requirement_id,
        "evidence_type": record.evidence_type,
        "subject_ref": record.subject_ref,
        "collection_method": record.collection_method,
        "created_at": record.created_at,
        "inference_from": record.inference_from,
        "conflict_refs": record.conflict_refs,
    }
    metadata.update(
        {
            key: copy.deepcopy(value)
            for key, value in record.fields.items()
            if key in _SAFE_METADATA_FIELDS
        }
    )
    metadata = {key: _public_metadata_value(value) for key, value in metadata.items()}
    return EvidenceView(
        evidence_id=record.evidence_id,
        reference_kind="store",
        task_id=record.task_id,
        result=record.result,
        basis=record.basis,
        content_hash=record.content_hash,
        content_size=record.content_size,
        redaction_status=record.redaction_status,
        raw_available=True,
        metadata=metadata,
    )


def _public_metadata_value(value: object) -> object:
    if isinstance(value, str):
        # Do not guess where an arbitrary quoted or multiword secret ends.
        if _SENSITIVE_METADATA_TEXT.search(value):
            return "[redacted-sensitive-value]"
        public = _EMBEDDED_FILE_URI.sub("[redacted-local-path]", value)
        public = _EMBEDDED_WINDOWS_PATH.sub("[redacted-local-path]", public)
        return _EMBEDDED_UNIX_PATH.sub("[redacted-local-path]", public)
    if isinstance(value, tuple):
        return tuple(_public_metadata_value(item) for item in value)
    if isinstance(value, list):
        return [_public_metadata_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _public_metadata_value(item)
            for key, item in value.items()
            if isinstance(key, str)
            and _SENSITIVE_METADATA_KEY.search(
                re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
            ) is None
        }
    return value


def _logical_reference_view(task_id: str, evidence_id: str) -> EvidenceView:
    return EvidenceView(
        evidence_id=evidence_id,
        reference_kind="reference_only",
        task_id=task_id,
        result="unknown",
        basis="unobserved",
        content_hash=None,
        content_size=None,
        redaction_status="reference_only",
        raw_available=False,
        metadata={"source": "m4_logical_reference"},
    )


def resolve_evidence(
    store: EvidenceStore,
    *,
    task_id: str,
    evidence_id: str,
    assurance_packet: dict | None,
    disclose_raw: bool = False,
) -> tuple[EvidenceView, bytes | None]:
    require_opaque_identifier(task_id, "task_id")
    require_opaque_identifier(evidence_id, "evidence_id")
    logical_refs: frozenset[str] = frozenset()
    packet_fingerprint = None
    if assurance_packet is not None:
        if not isinstance(assurance_packet, dict):
            raise ValueError("assurance_packet must be an object")
        logical_refs = frozenset(_refs(assurance_packet.get("evidence_refs"), "assurance evidence_refs"))
        packet_fingerprint = _hash(
            assurance_packet.get("fingerprint"), "assurance packet fingerprint"
        )
    try:
        record = store.resolve(evidence_id)
    except ValueError as error:
        if evidence_id in logical_refs and "unknown evidence" in str(error):
            return _logical_reference_view(task_id, evidence_id), None
        raise
    if record.task_id != task_id:
        raise ValueError("Evidence Task binding mismatch")
    if evidence_id in logical_refs and record.fields.get("packet_fingerprint") != packet_fingerprint:
        raise ValueError("Evidence packet fingerprint mismatch")
    _safe_object_path(store, record)
    validated_content = store.read_content(evidence_id)
    return _store_view(record), validated_content if disclose_raw else None

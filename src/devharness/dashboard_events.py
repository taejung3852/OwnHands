from __future__ import annotations

from collections.abc import Sequence

from .events import EventDraft, EventLog, EventRecord


DECISIONS = {
    "accept",
    "revise",
    "reject",
    "additional_validation",
    "risk_acceptance",
}
GATE_DECISIONS = {"pass", "soft_block", "hard_block"}


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _member(value: object, members: set[str], name: str) -> str:
    text = _text(value, name)
    if text not in members:
        raise ValueError(f"{name} is invalid")
    return text


def _fingerprint(value: object, name: str) -> str:
    text = _text(value, name)
    if (
        not text.startswith("sha256:")
        or len(text) != 71
        or any(character not in "0123456789abcdef" for character in text[7:])
    ):
        raise ValueError(f"{name} must be a sha256 fingerprint")
    return text


def _references(value: object, name: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a sequence of references")
    references = [_text(reference, name) for reference in value]
    if len(references) != len(set(references)):
        raise ValueError(f"{name} must not contain duplicates")
    return references


def record_assurance_reference(
    events: EventLog,
    *,
    event_id: str,
    task_id: str,
    packet_fingerprint: str,
    gate_fingerprint: str,
    gate_decision: str,
    evidence_refs: Sequence[str],
    occurred_at: str,
) -> EventRecord:
    return events.append(
        EventDraft(
            event_id=_text(event_id, "event_id"),
            task_id=_text(task_id, "task_id"),
            event_type="assurance.evaluated",
            event_version=1,
            occurred_at=_text(occurred_at, "occurred_at"),
            payload={
                "packet_fingerprint": _fingerprint(
                    packet_fingerprint, "packet_fingerprint"
                ),
                "gate_fingerprint": _fingerprint(
                    gate_fingerprint, "gate_fingerprint"
                ),
                "gate_decision": _member(
                    gate_decision, GATE_DECISIONS, "gate_decision"
                ),
                "evidence_refs": _references(evidence_refs, "evidence_refs"),
            },
            collection_method="dashboard-assurance-reference",
            redaction_status="reference_only",
        ),
        lambda payload: payload,
    )


def record_task_decision(
    events: EventLog,
    *,
    event_id: str,
    task_id: str,
    assurance_packet_fingerprint: str,
    gate_fingerprint: str,
    gate_decision: str,
    decision: str,
    decision_source: str,
    actor_ref: str,
    reason: str,
    residual_risks: Sequence[str],
    follow_up: str,
    evidence_refs: Sequence[str],
    occurred_at: str,
) -> EventRecord:
    return _record_task_decision(
        events,
        values={
            "event_id": event_id,
            "task_id": task_id,
            "assurance_packet_fingerprint": assurance_packet_fingerprint,
            "gate_fingerprint": gate_fingerprint,
            "gate_decision": gate_decision,
            "decision": decision,
            "decision_source": decision_source,
            "actor_ref": actor_ref,
            "reason": reason,
            "residual_risks": residual_risks,
            "follow_up": follow_up,
            "evidence_refs": evidence_refs,
            "occurred_at": occurred_at,
        },
    )


def _record_task_decision(
    events: EventLog,
    *,
    values: dict,
    expected_event_head: int | None = None,
    expected_projected_sequence: int | None = None,
) -> EventRecord:
    selected_decision = _member(values["decision"], DECISIONS, "decision")
    selected_gate = _member(
        values["gate_decision"], GATE_DECISIONS, "gate_decision"
    )
    source = _text(values["decision_source"], "decision_source")
    risks = _references(values["residual_risks"], "residual_risks")
    task_id = _text(values["task_id"], "task_id")
    packet_fingerprint = _fingerprint(
        values["assurance_packet_fingerprint"],
        "assurance_packet_fingerprint",
    )
    gate_fingerprint = _fingerprint(values["gate_fingerprint"], "gate_fingerprint")
    draft = EventDraft(
        event_id=_text(values["event_id"], "event_id"),
        task_id=task_id,
        event_type="task.decision.recorded",
        event_version=1,
        occurred_at=_text(values["occurred_at"], "occurred_at"),
        payload={
            "assurance_packet_fingerprint": packet_fingerprint,
            "gate_fingerprint": gate_fingerprint,
            "gate_decision": selected_gate,
            "decision": selected_decision,
            "decision_source": source,
            "actor_ref": _text(values["actor_ref"], "actor_ref"),
            "reason": _text(values["reason"], "reason"),
            "residual_risks": risks,
            "follow_up": _text(values["follow_up"], "follow_up"),
            "evidence_refs": _references(values["evidence_refs"], "evidence_refs"),
        },
        collection_method="dashboard-decision-form",
        redaction_status="redacted",
    )
    with events.catalog.transaction() as connection:
        task_events = events.list_for_task(task_id)
        if expected_event_head is not None:
            current_head = task_events[-1].sequence if task_events else 0
            projection = connection.execute(
                "SELECT projected_sequence, state FROM task_projections WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if (
                expected_projected_sequence is None
                or current_head != expected_event_head
                or expected_projected_sequence != expected_event_head
                or projection is None
                or projection["state"] != "ready"
                or projection["projected_sequence"] != current_head
            ):
                raise ValueError("stale Dashboard view cannot record a Decision")
        existing = next(
            (event for event in task_events if event.event_id == draft.event_id), None
        )
        existing_record = None
        if existing is not None:
            existing_record = events.append_in_transaction(
                draft, lambda payload: payload, connection
            )
        assurance_events = [
            event
            for event in task_events
            if event.event_type == "assurance.evaluated"
            and (existing is None or event.sequence < existing.sequence)
        ]
        if not assurance_events:
            raise ValueError("Decision requires the latest Assurance reference")
        latest = assurance_events[-1]
        expected_fields = {
            "packet_fingerprint",
            "gate_fingerprint",
            "gate_decision",
            "evidence_refs",
        }
        if latest.event_version != 1 or set(latest.payload) != expected_fields:
            raise ValueError("latest Assurance reference is invalid")
        authoritative = (
            _fingerprint(latest.payload["packet_fingerprint"], "packet_fingerprint"),
            _fingerprint(latest.payload["gate_fingerprint"], "gate_fingerprint"),
            _member(
                latest.payload["gate_decision"], GATE_DECISIONS, "gate_decision"
            ),
        )
        requested = (packet_fingerprint, gate_fingerprint, selected_gate)
        if requested != authoritative:
            raise ValueError(
                "Decision must reference the latest Assurance packet and Gate"
            )
        if authoritative[2] == "hard_block" and selected_decision in {
            "accept",
            "risk_acceptance",
        }:
            raise ValueError("Hard Block cannot be accepted or risk accepted")
        if selected_decision == "risk_acceptance" and (
            authoritative[2] != "soft_block"
            or source != "product_authority"
            or not risks
        ):
            raise ValueError(
                "risk acceptance requires a Soft Block, product authority, and residual risk"
            )
        if existing_record is not None:
            return existing_record
        return events.append_in_transaction(draft, lambda payload: payload, connection)

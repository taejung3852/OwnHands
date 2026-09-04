from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable

from .catalog import Catalog


REDACTION_STATUSES = {"not_needed", "redacted", "reference_only"}


class EventConflict(ValueError):
    pass


@dataclass(frozen=True)
class EventDraft:
    event_id: str
    task_id: str
    event_type: str
    event_version: int
    occurred_at: str
    payload: dict
    collection_method: str
    redaction_status: str


@dataclass(frozen=True)
class EventRecord(EventDraft):
    sequence: int
    fingerprint: str


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"payload must be JSON serializable: {error}") from error


class EventLog:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def append(
        self,
        draft: EventDraft,
        redactor: Callable[[dict], dict],
    ) -> EventRecord:
        with self.catalog.transaction() as connection:
            return self.append_in_transaction(draft, redactor, connection)

    def append_in_transaction(
        self,
        draft: EventDraft,
        redactor: Callable[[dict], dict],
        connection: sqlite3.Connection,
    ) -> EventRecord:
        self._validate(draft)
        redacted_payload = redactor(copy.deepcopy(draft.payload))
        if not isinstance(redacted_payload, dict):
            raise ValueError("redactor must return a dictionary")
        payload_json = _canonical_json(redacted_payload)
        fingerprint = self._fingerprint(draft, payload_json)

        existing = connection.execute(
            "SELECT * FROM events WHERE event_id=?", (draft.event_id,)
        ).fetchone()
        if existing is not None:
            if existing["fingerprint"] != fingerprint:
                raise EventConflict(
                    f"event_id {draft.event_id!r} already has different content"
                )
            return self._from_row(existing)

        task_exists = connection.execute(
            "SELECT 1 FROM tasks WHERE task_id=?", (draft.task_id,)
        ).fetchone()
        if task_exists is None:
            raise ValueError(f"unknown task: {draft.task_id}")

        sequence = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE task_id=?",
            (draft.task_id,),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO events(
                event_id, task_id, sequence, event_type, event_version,
                occurred_at, payload_json, collection_method,
                redaction_status, fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft.event_id,
                draft.task_id,
                sequence,
                draft.event_type,
                draft.event_version,
                draft.occurred_at,
                payload_json,
                draft.collection_method,
                draft.redaction_status,
                fingerprint,
            ),
        )
        row = connection.execute(
            "SELECT * FROM events WHERE event_id=?", (draft.event_id,)
        ).fetchone()
        return self._from_row(row)

    def list_for_task(self, task_id: str) -> list[EventRecord]:
        rows = self.catalog.connection.execute(
            "SELECT * FROM events WHERE task_id=? ORDER BY sequence", (task_id,)
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def head_sequence(self, task_id: str) -> int:
        return int(
            self.catalog.query_value(
                "SELECT COALESCE(MAX(sequence), 0) FROM events WHERE task_id=?",
                (task_id,),
            )
        )

    @staticmethod
    def _validate(draft: EventDraft) -> None:
        _required_text(draft.event_id, "event_id")
        _required_text(draft.task_id, "task_id")
        _required_text(draft.event_type, "event_type")
        _required_text(draft.collection_method, "collection_method")
        if not isinstance(draft.event_version, int) or isinstance(
            draft.event_version, bool
        ) or draft.event_version < 1:
            raise ValueError("event_version must be a positive integer")
        if draft.redaction_status not in REDACTION_STATUSES:
            raise ValueError("redaction_status is invalid")
        if not isinstance(draft.payload, dict):
            raise ValueError("payload must be a dictionary")
        try:
            occurred_at = datetime.fromisoformat(draft.occurred_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as error:
            raise ValueError("occurred_at must be an ISO-8601 timestamp") from error
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")

    @staticmethod
    def _fingerprint(draft: EventDraft, payload_json: str) -> str:
        envelope = asdict(draft)
        envelope["payload"] = json.loads(payload_json)
        return hashlib.sha256(_canonical_json(envelope).encode("utf-8")).hexdigest()

    @staticmethod
    def _from_row(row: object) -> EventRecord:
        return EventRecord(
            event_id=row["event_id"],
            task_id=row["task_id"],
            event_type=row["event_type"],
            event_version=row["event_version"],
            occurred_at=row["occurred_at"],
            payload=json.loads(row["payload_json"]),
            collection_method=row["collection_method"],
            redaction_status=row["redaction_status"],
            sequence=row["sequence"],
            fingerprint=row["fingerprint"],
        )

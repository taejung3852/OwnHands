from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .catalog import Catalog
from .events import EventLog, EventRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProjectionStatus:
    task_id: str
    state: str
    projected_sequence: int
    projection: dict
    last_error: str | None
    updated_at: str


@dataclass(frozen=True)
class Freshness:
    task_id: str
    event_head: int
    projected_sequence: int
    projection_state: str
    is_fresh: bool
    collection_completeness: str
    last_error: str | None


def _initial_projection() -> dict:
    return {
        "task": {},
        "evidence": {"active_ids": [], "purged_ids": []},
        "guarantee": {"report_ids": []},
        "event_counts": {},
    }


class ProjectionEngine:
    def __init__(self, catalog: Catalog, events: EventLog) -> None:
        self.catalog = catalog
        self.events = events
        self._handlers: dict[tuple[str, int], Callable[[dict, dict], None]] = {
            ("task.created", 1): self._task_created,
            ("evidence.recorded", 1): self._evidence_recorded,
            ("evidence.purged", 1): self._evidence_purged,
            ("guarantee.evaluated", 1): self._guarantee_evaluated,
            ("control.validation.recorded", 1): self._control_validation_recorded,
        }

    def project(self, task_id: str) -> ProjectionStatus:
        if self.catalog.query_value(
            "SELECT 1 FROM tasks WHERE task_id=?", (task_id,)
        ) is None:
            raise ValueError(f"unknown task: {task_id}")

        with self.catalog.transaction() as connection:
            stored = connection.execute(
                "SELECT * FROM task_projections WHERE task_id=?", (task_id,)
            ).fetchone()
            if stored is None:
                projected_sequence = 0
                projection = _initial_projection()
            else:
                projected_sequence = stored["projected_sequence"]
                projection = json.loads(stored["projection_json"])

            rows = connection.execute(
                """
                SELECT * FROM events
                WHERE task_id=? AND sequence>?
                ORDER BY sequence
                """,
                (task_id, projected_sequence),
            ).fetchall()
            state = "ready"
            last_error = None
            for row in rows:
                event = self.events._from_row(row)
                try:
                    projection = self._apply(projection, event)
                except (KeyError, TypeError, ValueError) as error:
                    state = "failed"
                    last_error = (
                        f"event {event.event_id} sequence {event.sequence}: {error}"
                    )
                    break
                projected_sequence = event.sequence

            updated_at = _now()
            connection.execute(
                """
                INSERT INTO task_projections(
                    task_id, projected_sequence, state, projection_json,
                    last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    projected_sequence=excluded.projected_sequence,
                    state=excluded.state,
                    projection_json=excluded.projection_json,
                    last_error=excluded.last_error,
                    updated_at=excluded.updated_at
                """,
                (
                    task_id,
                    projected_sequence,
                    state,
                    self._canonical_json(projection),
                    last_error,
                    updated_at,
                ),
            )
            return ProjectionStatus(
                task_id=task_id,
                state=state,
                projected_sequence=projected_sequence,
                projection=projection,
                last_error=last_error,
                updated_at=updated_at,
            )

    def rebuild(self, task_id: str) -> ProjectionStatus:
        with self.catalog.transaction() as connection:
            connection.execute(
                "DELETE FROM task_projections WHERE task_id=?", (task_id,)
            )
        return self.project(task_id)

    def freshness(self, task_id: str) -> Freshness:
        if self.catalog.query_value(
            "SELECT 1 FROM tasks WHERE task_id=?", (task_id,)
        ) is None:
            raise ValueError(f"unknown task: {task_id}")
        row = self.catalog.connection.execute(
            "SELECT * FROM task_projections WHERE task_id=?", (task_id,)
        ).fetchone()
        event_head = self.events.head_sequence(task_id)
        if row is None:
            return Freshness(
                task_id=task_id,
                event_head=event_head,
                projected_sequence=0,
                projection_state="missing",
                is_fresh=False,
                collection_completeness="unobserved",
                last_error=None,
            )
        return Freshness(
            task_id=task_id,
            event_head=event_head,
            projected_sequence=row["projected_sequence"],
            projection_state=row["state"],
            is_fresh=(
                row["state"] == "ready" and row["projected_sequence"] == event_head
            ),
            collection_completeness="unobserved",
            last_error=row["last_error"],
        )

    def _apply(self, current: dict, event: EventRecord) -> dict:
        handler = self._handlers.get((event.event_type, event.event_version))
        if handler is None:
            raise ValueError(
                f"unsupported event {event.event_type!r} version {event.event_version}"
            )
        projection = copy.deepcopy(current)
        handler(projection, event.payload)
        counts = projection["event_counts"]
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return projection

    @staticmethod
    def _task_created(projection: dict, payload: dict) -> None:
        mode = payload["mode"]
        if mode not in {"managed", "imported"}:
            raise ValueError("task.created mode is invalid")
        projection["task"] = {"mode": mode}

    @staticmethod
    def _evidence_recorded(projection: dict, payload: dict) -> None:
        evidence_id = payload["evidence_id"]
        active = projection["evidence"]["active_ids"]
        if evidence_id not in active:
            active.append(evidence_id)

    @staticmethod
    def _evidence_purged(projection: dict, payload: dict) -> None:
        evidence_id = payload["evidence_id"]
        active = projection["evidence"]["active_ids"]
        purged = projection["evidence"]["purged_ids"]
        if evidence_id in active:
            active.remove(evidence_id)
        if evidence_id not in purged:
            purged.append(evidence_id)

    @staticmethod
    def _guarantee_evaluated(projection: dict, payload: dict) -> None:
        report_id = payload["report_id"]
        report_ids = projection["guarantee"]["report_ids"]
        if report_id not in report_ids:
            report_ids.append(report_id)

    @staticmethod
    def _control_validation_recorded(_projection: dict, payload: dict) -> None:
        if not payload["record_id"]:
            raise ValueError("control validation record_id is required")

    @staticmethod
    def _canonical_json(value: object) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

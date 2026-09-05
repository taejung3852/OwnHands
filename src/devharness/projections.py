from __future__ import annotations

import copy
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .catalog import Catalog, projection_fingerprint
from .events import EventLog, EventRecord


PROJECTION_VERSION = "1.0"


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
                try:
                    projection = self._validated_stored_projection(stored)
                except ValueError as error:
                    updated_at = _now()
                    last_error = f"stored projection integrity failure: {error}"
                    connection.execute(
                        """
                        UPDATE task_projections
                        SET state='failed', last_error=?, updated_at=?
                        WHERE task_id=?
                        """,
                        (last_error, updated_at, task_id),
                    )
                    return ProjectionStatus(
                        task_id=task_id,
                        state="failed",
                        projected_sequence=projected_sequence,
                        projection=_initial_projection(),
                        last_error=last_error,
                        updated_at=updated_at,
                    )
                if stored["state"] == "failed" and "integrity failure" in (
                    stored["last_error"] or ""
                ):
                    return ProjectionStatus(
                        task_id=task_id,
                        state="failed",
                        projected_sequence=projected_sequence,
                        projection=projection,
                        last_error=stored["last_error"],
                        updated_at=stored["updated_at"],
                    )

            try:
                events = self.events.list_for_task(task_id)
            except ValueError as error:
                return self._record_failure(
                    connection,
                    task_id,
                    projected_sequence,
                    projection,
                    f"event log integrity failure: {error}",
                )
            state = "ready"
            last_error = None
            for event in events:
                if event.sequence <= projected_sequence:
                    continue
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
            self._validate_projection(projection)
            projection_json = self._canonical_json(projection)
            projection_hash = projection_fingerprint(
                task_id, projected_sequence, state, projection_json
            )
            connection.execute(
                """
                INSERT INTO task_projections(
                    task_id, projected_sequence, state, projection_json,
                    projection_hash, last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    projected_sequence=excluded.projected_sequence,
                    state=excluded.state,
                    projection_json=excluded.projection_json,
                    projection_hash=excluded.projection_hash,
                    last_error=excluded.last_error,
                    updated_at=excluded.updated_at
                """,
                (
                    task_id,
                    projected_sequence,
                    state,
                    projection_json,
                    projection_hash,
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
        with self.catalog.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM task_projections WHERE task_id=?", (task_id,)
            ).fetchone()
            projected_sequence = 0
            projection = _initial_projection()
            if row is not None:
                try:
                    projection = self._validated_stored_projection(row)
                    projected_sequence = row["projected_sequence"]
                except ValueError as error:
                    failure = self._record_failure(
                        connection,
                        task_id,
                        0,
                        _initial_projection(),
                        f"stored projection integrity failure: {error}",
                    )
                    return Freshness(
                        task_id=task_id,
                        event_head=0,
                        projected_sequence=failure.projected_sequence,
                        projection_state="failed",
                        is_fresh=False,
                        collection_completeness="unobserved",
                        last_error=failure.last_error,
                    )
            try:
                event_head = self.events.head_sequence(task_id)
            except ValueError as error:
                failure = self._record_failure(
                    connection,
                    task_id,
                    projected_sequence,
                    projection,
                    f"event log integrity failure: {error}",
                )
                return Freshness(
                    task_id=task_id,
                    event_head=0,
                    projected_sequence=failure.projected_sequence,
                    projection_state="failed",
                    is_fresh=False,
                    collection_completeness="unobserved",
                    last_error=failure.last_error,
                )
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
                projected_sequence=projected_sequence,
                projection_state=row["state"],
                is_fresh=(
                    row["state"] == "ready" and projected_sequence == event_head
                ),
                collection_completeness="unobserved",
                last_error=row["last_error"],
            )

    def _record_failure(
        self,
        connection: sqlite3.Connection,
        task_id: str,
        projected_sequence: int,
        projection: dict,
        last_error: str,
    ) -> ProjectionStatus:
        updated_at = _now()
        projection_json = self._canonical_json(projection)
        projection_hash = projection_fingerprint(
            task_id, projected_sequence, "failed", projection_json
        )
        connection.execute(
            """
            INSERT INTO task_projections(
                task_id, projected_sequence, state, projection_json,
                projection_hash, last_error, updated_at
            ) VALUES (?, ?, 'failed', ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                projected_sequence=excluded.projected_sequence,
                state=excluded.state,
                projection_json=excluded.projection_json,
                projection_hash=excluded.projection_hash,
                last_error=excluded.last_error,
                updated_at=excluded.updated_at
            """,
            (
                task_id,
                projected_sequence,
                projection_json,
                projection_hash,
                last_error,
                updated_at,
            ),
        )
        return ProjectionStatus(
            task_id=task_id,
            state="failed",
            projected_sequence=projected_sequence,
            projection=projection,
            last_error=last_error,
            updated_at=updated_at,
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

    def _validated_stored_projection(self, row: object) -> dict:
        document = row["projection_json"]
        actual_hash = projection_fingerprint(
            row["task_id"], row["projected_sequence"], row["state"], document
        )
        if actual_hash != row["projection_hash"]:
            raise ValueError("projection hash mismatch")
        try:
            projection = json.loads(document)
        except json.JSONDecodeError as error:
            raise ValueError("projection JSON is invalid") from error
        self._validate_projection(projection)
        return projection

    @staticmethod
    def _validate_projection(projection: object) -> None:
        if not isinstance(projection, dict) or set(projection) != {
            "task",
            "evidence",
            "guarantee",
            "event_counts",
        }:
            raise ValueError("projection fields are invalid")
        task = projection["task"]
        if not isinstance(task, dict) or (
            task and (set(task) != {"mode"} or task["mode"] not in {"managed", "imported"})
        ):
            raise ValueError("projection task state is invalid")
        evidence = projection["evidence"]
        if not isinstance(evidence, dict) or set(evidence) != {
            "active_ids",
            "purged_ids",
        }:
            raise ValueError("projection Evidence state is invalid")
        for name in ("active_ids", "purged_ids"):
            values = evidence[name]
            if (
                not isinstance(values, list)
                or any(not isinstance(value, str) or not value for value in values)
                or len(values) != len(set(values))
            ):
                raise ValueError("projection Evidence IDs are invalid")
        guarantee = projection["guarantee"]
        if not isinstance(guarantee, dict) or set(guarantee) != {"report_ids"}:
            raise ValueError("projection Guarantee state is invalid")
        report_ids = guarantee["report_ids"]
        if (
            not isinstance(report_ids, list)
            or any(not isinstance(value, str) or not value for value in report_ids)
            or len(report_ids) != len(set(report_ids))
        ):
            raise ValueError("projection report IDs are invalid")
        counts = projection["event_counts"]
        if not isinstance(counts, dict) or any(
            not isinstance(name, str)
            or not name
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 1
            for name, count in counts.items()
        ):
            raise ValueError("projection event counts are invalid")

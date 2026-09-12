"""Historical run receipt values, independent of launching or controlling a runtime."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AppServerRecord:
    kind: str
    method: str
    payload_hash: str
    request_id: int | str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    item_id: str | None = None
    item_type: str | None = None
    status: str | None = None
    decision: str | None = None
    exit_code: int | None = None
    probe: str | None = None


@dataclass(frozen=True)
class AppServerRun:
    records: list[AppServerRecord]
    thread_id: str
    turn_id: str
    terminal_status: str
    instruction_sources: list[str]
    codex_version: str
    protocol_fingerprint: str



from __future__ import annotations

import hashlib
import json
import selectors
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol


_APPROVAL_METHODS = {
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
    "item/permissions/requestApproval",
}
_APPROVAL_DECISIONS = {
    "accept",
    "acceptForSession",
    "decline",
    "cancel",
}
_TERMINAL_TURN_STATUSES = {"completed", "interrupted", "failed"}


class AppServerError(RuntimeError):
    pass


@dataclass(frozen=True)
class AppServerConfig:
    executable: str
    cwd: Path
    model: str
    sandbox: str
    approval_policy: str
    prompt: str
    timeout_seconds: float
    codex_version: str
    protocol_fingerprint: str
    reasoning_effort: str


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


@dataclass(frozen=True)
class AppServerRun:
    records: list[AppServerRecord]
    thread_id: str
    turn_id: str
    terminal_status: str
    instruction_sources: list[str]
    codex_version: str
    protocol_fingerprint: str


class JsonRpcTransport(Protocol):
    def send(self, message: dict) -> None: ...

    def receive(self, timeout_seconds: float) -> str | None: ...

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def close(self) -> None: ...


class StdioJsonRpcTransport:
    def __init__(self, config: AppServerConfig) -> None:
        self._process = subprocess.Popen(
            [config.executable, "app-server", "--listen", "stdio://"],
            cwd=config.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

    def send(self, message: dict) -> None:
        if self._process.stdin is None:
            raise AppServerError("App Server stdin is unavailable")
        self._process.stdin.write(_canonical_json(message) + "\n")
        self._process.stdin.flush()

    def receive(self, timeout_seconds: float) -> str | None:
        if self._process.stdout is None:
            raise AppServerError("App Server stdout is unavailable")
        with selectors.DefaultSelector() as selector:
            selector.register(self._process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout_seconds):
                raise TimeoutError("App Server receive deadline expired")
        line = self._process.stdout.readline()
        return line if line else None

    def poll(self) -> int | None:
        return self._process.poll()

    def terminate(self) -> None:
        self._process.terminate()

    def kill(self) -> None:
        self._process.kill()

    def close(self) -> None:
        for stream in (self._process.stdin, self._process.stdout):
            if stream is not None:
                stream.close()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _payload_hash(message: dict) -> str:
    return hashlib.sha256(_canonical_json(message).encode("utf-8")).hexdigest()


def _required_dict(value: object, name: str) -> dict:
    if not isinstance(value, dict):
        raise AppServerError(f"{name} must be an object")
    return value


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise AppServerError(f"{name} must be a non-empty string")
    return value


def _validate_wire_envelope(message: object) -> dict:
    if not isinstance(message, dict):
        raise AppServerError("App Server returned a non-object wire message")
    if "jsonrpc" in message and message["jsonrpc"] != "2.0":
        raise AppServerError("App Server returned an invalid legacy jsonrpc value")
    has_id = "id" in message
    has_method = "method" in message
    has_result = "result" in message
    has_error = "error" in message
    if has_method:
        kind = "request" if has_id else "notification"
        if has_result or has_error:
            raise AppServerError(f"App Server returned an ambiguous {kind} envelope")
        return message
    if has_id:
        if has_result == has_error:
            raise AppServerError("App Server returned an invalid response envelope")
        return message
    raise AppServerError("App Server returned an invalid notification envelope")


def _validate_config(config: AppServerConfig) -> None:
    for name in (
        "executable",
        "model",
        "sandbox",
        "approval_policy",
        "prompt",
        "codex_version",
        "protocol_fingerprint",
        "reasoning_effort",
    ):
        _required_text(getattr(config, name), name)
    if not isinstance(config.cwd, Path) or not config.cwd.is_absolute():
        raise AppServerError("cwd must be an absolute Path")
    if (
        isinstance(config.timeout_seconds, bool)
        or not isinstance(config.timeout_seconds, (int, float))
        or config.timeout_seconds <= 0
    ):
        raise AppServerError("timeout_seconds must be positive")


def run_app_server(
    config: AppServerConfig,
    transport_factory: Callable[[AppServerConfig], JsonRpcTransport],
    sink: Callable[[AppServerRecord], None],
    approval_handler: Callable[[AppServerRecord], str],
) -> AppServerRun:
    _validate_config(config)
    transport = transport_factory(config)
    deadline = time.monotonic() + config.timeout_seconds
    next_request_id = 1
    seen_response_ids: set[int | str] = set()
    records: list[AppServerRecord] = []
    thread_id: str | None = None
    turn_id: str | None = None
    instruction_sources: list[str] = []
    active_items: set[str] = set()
    approvals: dict[int | str, dict[str, object]] = {}
    failed = True

    def emit(record: AppServerRecord) -> None:
        records.append(record)
        sink(record)

    def receive_message() -> dict:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AppServerError("App Server timeout")
        try:
            line = transport.receive(remaining)
        except TimeoutError as error:
            raise AppServerError("App Server timeout") from error
        if line is None:
            raise AppServerError(
                f"App Server premature exit before terminal turn: {transport.poll()}"
            )
        try:
            message = json.loads(line)
        except (json.JSONDecodeError, TypeError) as error:
            raise AppServerError("App Server returned malformed JSON") from error
        return _validate_wire_envelope(message)

    def request(method: str, params: dict) -> dict:
        nonlocal next_request_id
        request_id = next_request_id
        next_request_id += 1
        transport.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        message = receive_message()
        response_id = message.get("id")
        if response_id in seen_response_ids:
            raise AppServerError(f"duplicate response id: {response_id!r}")
        if response_id != request_id or "method" in message:
            raise AppServerError(
                f"response id mismatch for {method}: expected {request_id!r}"
            )
        seen_response_ids.add(response_id)
        if "error" in message:
            raise AppServerError(f"App Server response error for {method}")
        return _required_dict(message.get("result"), f"{method} result") | {
            "_message": message
        }

    def response_record(
        method: str,
        result: dict,
        *,
        scoped_thread_id: str | None = None,
        scoped_turn_id: str | None = None,
        status: str = "ok",
    ) -> None:
        message = result["_message"]
        emit(
            AppServerRecord(
                kind="response",
                method=method,
                request_id=message["id"],
                thread_id=scoped_thread_id,
                turn_id=scoped_turn_id,
                status=status,
                payload_hash=_payload_hash(message),
            )
        )

    try:
        initialize = request(
            "initialize",
            {
                "clientInfo": {"name": "ownhands", "version": config.codex_version},
                "capabilities": {"experimentalApi": False},
            },
        )
        if initialize.get("userAgent") != f"codex-cli/{config.codex_version}":
            raise AppServerError("Codex version mismatch in initialize response")
        response_record("initialize", initialize)
        transport.send({"jsonrpc": "2.0", "method": "initialized", "params": {}})

        thread_start = request(
            "thread/start",
            {
                "cwd": str(config.cwd),
                "model": config.model,
                "sandbox": config.sandbox,
                "approvalPolicy": config.approval_policy,
                "ephemeral": True,
            },
        )
        thread = _required_dict(thread_start.get("thread"), "thread/start thread")
        thread_id = _required_text(thread.get("id"), "thread/start thread id")
        raw_sources = thread_start.get("instructionSources", [])
        if not isinstance(raw_sources, list) or not all(
            isinstance(source, str) and source for source in raw_sources
        ):
            raise AppServerError("instructionSources must be a string array")
        instruction_sources = list(raw_sources)
        response_record("thread/start", thread_start, scoped_thread_id=thread_id)

        turn_start = request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": config.prompt}],
                "effort": config.reasoning_effort,
            },
        )
        turn = _required_dict(turn_start.get("turn"), "turn/start turn")
        turn_id = _required_text(turn.get("id"), "turn/start turn id")
        turn_status = _required_text(turn.get("status"), "turn/start turn status")
        response_record(
            "turn/start",
            turn_start,
            scoped_thread_id=thread_id,
            scoped_turn_id=turn_id,
            status=turn_status,
        )

        while True:
            message = receive_message()
            if "id" in message and "method" not in message:
                response_id = message.get("id")
                if response_id in seen_response_ids:
                    raise AppServerError(f"duplicate response id: {response_id!r}")
                raise AppServerError(f"unexpected response id: {response_id!r}")

            method = _required_text(message.get("method"), "message method")
            params = _required_dict(message.get("params"), f"{method} params")

            if method in _APPROVAL_METHODS:
                request_id = message.get("id")
                if not isinstance(request_id, (int, str)) or isinstance(
                    request_id, bool
                ):
                    raise AppServerError("approval request id is invalid")
                if request_id in approvals:
                    raise AppServerError("duplicate approval request id")
                approval_thread = params.get("threadId")
                approval_turn = params.get("turnId")
                approval_item = params.get("itemId")
                if (
                    approval_thread != thread_id
                    or approval_turn != turn_id
                    or approval_item not in active_items
                ):
                    raise AppServerError("approval scope does not match active item")
                item_id = _required_text(approval_item, "approval item id")
                request_record = AppServerRecord(
                    kind="approval_request",
                    method=method,
                    request_id=request_id,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    payload_hash=_payload_hash(message),
                )
                emit(request_record)
                decision = approval_handler(request_record)
                if decision not in _APPROVAL_DECISIONS:
                    raise AppServerError("approval decision is invalid")
                decision_message = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"decision": decision},
                }
                transport.send(decision_message)
                approvals[request_id] = {
                    "method": method,
                    "item_id": item_id,
                    "decision": decision,
                    "resolved": False,
                    "terminal_status": None,
                }
                emit(
                    AppServerRecord(
                        kind="approval_decision",
                        method=method,
                        request_id=request_id,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=item_id,
                        decision=decision,
                        payload_hash=_payload_hash(decision_message),
                    )
                )
                continue

            if "id" in message:
                raise AppServerError(f"unsupported server request: {method}")

            message_thread = params.get("threadId")
            if message_thread is not None and message_thread != thread_id:
                raise AppServerError(f"{method} thread scope mismatch")
            message_turn = params.get("turnId")
            if message_turn is not None and message_turn != turn_id:
                raise AppServerError(f"{method} turn scope mismatch")

            if method == "turn/started":
                started_turn = _required_dict(params.get("turn"), "turn/started turn")
                if started_turn.get("id") != turn_id:
                    raise AppServerError("turn/started turn scope mismatch")
                status = _required_text(started_turn.get("status"), "turn status")
                emit(
                    AppServerRecord(
                        kind="notification",
                        method=method,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        status=status,
                        payload_hash=_payload_hash(message),
                    )
                )
                continue

            if method in {"item/started", "item/completed"}:
                item = _required_dict(params.get("item"), f"{method} item")
                item_id = _required_text(item.get("id"), f"{method} item id")
                item_type = _required_text(item.get("type"), f"{method} item type")
                status_value = item.get("status")
                status = status_value if isinstance(status_value, str) else None
                if method == "item/started":
                    active_items.add(item_id)
                else:
                    for approval in approvals.values():
                        if approval["item_id"] == item_id:
                            approval["terminal_status"] = status
                emit(
                    AppServerRecord(
                        kind="notification",
                        method=method,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=item_id,
                        item_type=item_type,
                        status=status,
                        payload_hash=_payload_hash(message),
                    )
                )
                continue

            if method == "serverRequest/resolved":
                resolved_id = params.get("requestId")
                approval = approvals.get(resolved_id)
                if approval is None or params.get("threadId") != thread_id:
                    raise AppServerError("serverRequest/resolved scope mismatch")
                if approval["resolved"]:
                    raise AppServerError("duplicate serverRequest/resolved")
                approval["resolved"] = True
                emit(
                    AppServerRecord(
                        kind="notification",
                        method=method,
                        request_id=resolved_id,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=str(approval["item_id"]),
                        status="resolved",
                        decision=str(approval["decision"]),
                        payload_hash=_payload_hash(message),
                    )
                )
                continue

            if method == "turn/completed":
                completed_turn = _required_dict(
                    params.get("turn"), "turn/completed turn"
                )
                if completed_turn.get("id") != turn_id:
                    raise AppServerError("turn/completed turn scope mismatch")
                terminal_status = completed_turn.get("status")
                if terminal_status not in _TERMINAL_TURN_STATUSES:
                    raise AppServerError(
                        f"unknown terminal state: {terminal_status!r}"
                    )
                terminal_items = completed_turn.get("items")
                if not isinstance(terminal_items, list):
                    raise AppServerError("turn/completed items must be an array")
                terminal_by_id = {
                    item.get("id"): item
                    for item in terminal_items
                    if isinstance(item, dict) and isinstance(item.get("id"), str)
                }
                for approval in approvals.values():
                    if not approval["resolved"]:
                        raise AppServerError(
                            "approval missing serverRequest/resolved"
                        )
                    item = terminal_by_id.get(approval["item_id"])
                    if (
                        item is None
                        or approval["terminal_status"] is None
                        or item.get("status") != approval["terminal_status"]
                    ):
                        raise AppServerError("terminal item mismatch for approval")
                emit(
                    AppServerRecord(
                        kind="notification",
                        method=method,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        status=terminal_status,
                        payload_hash=_payload_hash(message),
                    )
                )
                failed = False
                return AppServerRun(
                    records=records,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    terminal_status=terminal_status,
                    instruction_sources=instruction_sources,
                    codex_version=config.codex_version,
                    protocol_fingerprint=config.protocol_fingerprint,
                )

            emit(
                AppServerRecord(
                    kind="notification",
                    method=method,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    payload_hash=_payload_hash(message),
                )
            )
    finally:
        if failed:
            try:
                if transport.poll() is None:
                    transport.terminate()
                    if transport.poll() is None:
                        transport.kill()
            finally:
                transport.close()
        else:
            transport.close()

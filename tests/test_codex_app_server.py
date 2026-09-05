from __future__ import annotations

import copy
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from devharness.codex_app_server import (
    AppServerConfig,
    AppServerError,
    StdioJsonRpcTransport,
    run_app_server,
)


FIXTURES = Path(__file__).parent / "fixtures" / "m3"
SUCCESS_JSONL = (FIXTURES / "app-server-success.jsonl").read_text().splitlines()
ATTACKS = json.loads((FIXTURES / "app-server-attacks.json").read_text())
CONFIG = AppServerConfig(
    executable="/fixture/codex",
    cwd=Path("/fixture"),
    model="gpt-fixture",
    sandbox="workspace-write",
    approval_policy="on-request",
    prompt="fixture prompt",
    timeout_seconds=5.0,
    codex_version="0.153.3",
    protocol_fingerprint="sha256:fixture-protocol",
)


class FakeTransport:
    def __init__(self, lines: list[str | dict], *, exit_code: int = 0) -> None:
        self.lines = list(lines)
        self.exit_code = exit_code
        self.sent: list[dict] = []
        self.terminated = False
        self.killed = False
        self.closed = False

    def send(self, message: dict) -> None:
        self.sent.append(copy.deepcopy(message))

    def receive(self, timeout_seconds: float) -> str | None:
        if timeout_seconds <= 0:
            raise TimeoutError("fixture deadline")
        if not self.lines:
            return None
        line = self.lines.pop(0)
        return line if isinstance(line, str) else json.dumps(line)

    def poll(self) -> int | None:
        return self.exit_code if not self.lines else None

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def close(self) -> None:
        self.closed = True


def success_messages() -> list[dict]:
    return [json.loads(line) for line in SUCCESS_JSONL]


def transport_factory(transport: FakeTransport):
    return lambda _config: transport


def decline(_record) -> str:
    return "decline"


class AppServerAdapterTests(unittest.TestCase):
    def test_handshake_thread_turn_and_terminal_chain_is_scope_checked(self) -> None:
        transport = FakeTransport(SUCCESS_JSONL)
        records = []

        run = run_app_server(
            CONFIG, transport_factory(transport), records.append, decline
        )

        self.assertEqual("completed", run.terminal_status)
        self.assertEqual("thread-fixture", run.thread_id)
        self.assertEqual("turn-fixture", run.turn_id)
        self.assertEqual(["AGENTS.md"], run.instruction_sources)
        self.assertEqual("0.153.3", run.codex_version)
        self.assertEqual("sha256:fixture-protocol", run.protocol_fingerprint)
        self.assertEqual(run.records, records)
        self.assertEqual(
            [
                ("response", "initialize", None, None, None, "ok", None),
                ("response", "thread/start", "thread-fixture", None, None, "ok", None),
                ("response", "turn/start", "thread-fixture", "turn-fixture", None, "inProgress", None),
                ("notification", "turn/started", "thread-fixture", "turn-fixture", None, "inProgress", None),
                ("notification", "item/started", "thread-fixture", "turn-fixture", "item-fixture", "inProgress", None),
                ("approval_request", "item/commandExecution/requestApproval", "thread-fixture", "turn-fixture", "item-fixture", None, None),
                ("approval_decision", "item/commandExecution/requestApproval", "thread-fixture", "turn-fixture", "item-fixture", None, "decline"),
                ("notification", "serverRequest/resolved", "thread-fixture", "turn-fixture", "item-fixture", "resolved", "decline"),
                ("notification", "item/completed", "thread-fixture", "turn-fixture", "item-fixture", "declined", None),
                ("notification", "turn/completed", "thread-fixture", "turn-fixture", None, "completed", None),
            ],
            [
                (
                    record.kind,
                    record.method,
                    record.thread_id,
                    record.turn_id,
                    record.item_id,
                    record.status,
                    record.decision,
                )
                for record in records
            ],
        )
        self.assertEqual(
            [
                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"ownhands","version":"0.153.3"},"capabilities":{"experimentalApi":False}}},
                {"jsonrpc":"2.0","method":"initialized","params":{}},
                {"jsonrpc":"2.0","id":2,"method":"thread/start","params":{"cwd":"/fixture","model":"gpt-fixture","sandbox":"workspace-write","approvalPolicy":"on-request","ephemeral":True}},
                {"jsonrpc":"2.0","id":3,"method":"turn/start","params":{"threadId":"thread-fixture","input":[{"type":"text","text":"fixture prompt"}]}},
                {"jsonrpc":"2.0","id":"approval-fixture","result":{"decision":"decline"}},
            ],
            transport.sent,
        )
        self.assertTrue(transport.closed)
        self.assertFalse(transport.terminated)
        self.assertFalse(transport.killed)
        serialized_records = repr(records)
        self.assertNotIn("sensitive-command", serialized_records)
        self.assertNotIn("sensitive reason", serialized_records)
        self.assertNotIn("sensitive output", serialized_records)
        self.assertTrue(all(len(record.payload_hash) == 64 for record in records))

    def test_cross_thread_turn_or_item_approval_cannot_be_answered(self) -> None:
        for attack_name in ("cross_thread", "cross_turn", "cross_item"):
            with self.subTest(attack=attack_name):
                messages = success_messages()
                messages[5]["params"].update(ATTACKS[attack_name]["approval_overrides"])
                transport = FakeTransport(messages)
                records = []

                with self.assertRaisesRegex(AppServerError, "approval scope"):
                    run_app_server(
                        CONFIG, transport_factory(transport), records.append, decline
                    )

                self.assertEqual(4, len(transport.sent))
                self.assertFalse(any(record.kind == "approval_decision" for record in records))
                self.assertTrue(transport.terminated)
                self.assertTrue(transport.closed)

    def test_malformed_json_fails_closed_and_closes_exited_child(self) -> None:
        attack = ATTACKS["malformed_json"]
        transport = FakeTransport(attack["lines"], exit_code=attack["exit_code"])

        with self.assertRaisesRegex(AppServerError, "malformed JSON"):
            run_app_server(CONFIG, transport_factory(transport), lambda _record: None, decline)

        self.assertFalse(transport.terminated)
        self.assertTrue(transport.closed)

    def test_duplicate_response_id_is_rejected(self) -> None:
        attack = ATTACKS["duplicate_response_id"]
        transport = FakeTransport(attack["lines"], exit_code=attack["exit_code"])

        with self.assertRaisesRegex(AppServerError, "duplicate response id"):
            run_app_server(CONFIG, transport_factory(transport), lambda _record: None, decline)

    def test_response_error_is_not_treated_as_success(self) -> None:
        attack = ATTACKS["response_error"]
        transport = FakeTransport(attack["lines"], exit_code=attack["exit_code"])

        with self.assertRaisesRegex(AppServerError, "response error"):
            run_app_server(CONFIG, transport_factory(transport), lambda _record: None, decline)

    def test_initialize_response_must_match_the_configured_codex_version(self) -> None:
        messages = success_messages()
        messages[0]["result"]["userAgent"] = "codex-cli/9.9.9"

        with self.assertRaisesRegex(AppServerError, "Codex version mismatch"):
            run_app_server(
                CONFIG,
                transport_factory(FakeTransport(messages)),
                lambda _record: None,
                decline,
            )

    def test_process_exit_before_terminal_turn_is_rejected(self) -> None:
        transport = FakeTransport([], exit_code=17)

        with self.assertRaisesRegex(AppServerError, "premature exit.*17"):
            run_app_server(CONFIG, transport_factory(transport), lambda _record: None, decline)

    def test_timeout_terminates_child_and_is_not_a_terminal_result(self) -> None:
        class TimeoutTransport(FakeTransport):
            def receive(self, timeout_seconds: float) -> str | None:
                raise TimeoutError("fixture timeout")

            def poll(self) -> int | None:
                return 0 if self.terminated else None

        transport = TimeoutTransport([])

        with self.assertRaisesRegex(AppServerError, "timeout"):
            run_app_server(CONFIG, transport_factory(transport), lambda _record: None, decline)

        self.assertTrue(transport.terminated)
        self.assertTrue(transport.closed)

    def test_unknown_terminal_turn_state_is_rejected(self) -> None:
        messages = success_messages()
        messages[8]["params"]["turn"].update(
            ATTACKS["unknown_terminal_state"]["terminal_overrides"]
        )

        with self.assertRaisesRegex(AppServerError, "unknown terminal state"):
            run_app_server(
                CONFIG,
                transport_factory(FakeTransport(messages)),
                lambda _record: None,
                decline,
            )

    def test_missing_server_request_resolution_is_rejected(self) -> None:
        messages = success_messages()
        del messages[6]

        with self.assertRaisesRegex(AppServerError, "serverRequest/resolved"):
            run_app_server(
                CONFIG,
                transport_factory(FakeTransport(messages)),
                lambda _record: None,
                decline,
            )

    def test_terminal_approval_item_must_match_completed_item(self) -> None:
        messages = success_messages()
        messages[8]["params"]["turn"]["items"][0].update(
            ATTACKS["terminal_item_mismatch"]["terminal_item_overrides"]
        )

        with self.assertRaisesRegex(AppServerError, "terminal item mismatch"):
            run_app_server(
                CONFIG,
                transport_factory(FakeTransport(messages)),
                lambda _record: None,
                decline,
            )

    def test_invalid_approval_handler_decision_fails_closed(self) -> None:
        transport = FakeTransport(SUCCESS_JSONL)

        with self.assertRaisesRegex(AppServerError, "approval decision"):
            run_app_server(
                CONFIG,
                transport_factory(transport),
                lambda _record: None,
                lambda _record: "always",
            )

        self.assertEqual(4, len(transport.sent))

    @patch("devharness.codex_app_server.subprocess.Popen")
    def test_stdio_transport_starts_only_its_own_app_server_child(self, popen) -> None:
        process = popen.return_value
        process.stdin = unittest.mock.Mock()
        process.stdout = unittest.mock.Mock()
        process.poll.return_value = None

        transport = StdioJsonRpcTransport(CONFIG)
        transport.terminate()
        transport.kill()

        popen.assert_called_once_with(
            ["/fixture/codex", "app-server", "--listen", "stdio://"],
            cwd=Path("/fixture"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

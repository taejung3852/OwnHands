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
    reasoning_effort="low",
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


class ApprovalGatedTransport(FakeTransport):
    def __init__(self, before_decision: list[dict], after_decision: list[dict]) -> None:
        super().__init__(before_decision)
        self.after_decision = list(after_decision)

    def send(self, message: dict) -> None:
        super().send(message)
        if message.get("result", {}).get("decision") == "decline":
            self.lines.extend(self.after_decision)


def success_messages() -> list[dict]:
    return [json.loads(line) for line in SUCCESS_JSONL]


def transport_factory(transport: FakeTransport):
    return lambda _config: transport


def decline(_record) -> str:
    return "decline"


class AppServerAdapterTests(unittest.TestCase):
    def test_thread_started_notification_may_precede_thread_start_response(self) -> None:
        messages = success_messages()
        thread_started = {
            "method": "thread/started",
            "params": {"thread": copy.deepcopy(messages[1]["result"]["thread"])},
        }
        messages.insert(1, thread_started)
        records = []

        run = run_app_server(
            CONFIG, transport_factory(FakeTransport(messages)), records.append, decline
        )

        self.assertEqual("completed", run.terminal_status)
        self.assertEqual(
            ["thread/started", "thread/start", "turn/start"],
            [record.method for record in records[1:4]],
        )

    def test_turn_started_notification_may_precede_turn_start_response(self) -> None:
        messages = success_messages()
        turn_started = messages.pop(3)
        messages.insert(2, turn_started)
        records = []

        run = run_app_server(
            CONFIG, transport_factory(FakeTransport(messages)), records.append, decline
        )

        self.assertEqual("completed", run.terminal_status)
        self.assertEqual(
            ["turn/started", "turn/start", "item/started"],
            [record.method for record in records[2:5]],
        )

    def test_item_and_approval_messages_may_precede_turn_start_response_in_order(self) -> None:
        messages = success_messages()
        queued = messages[3:6]
        del messages[3:6]
        messages[2:2] = queued
        records = []
        transport = FakeTransport(messages)

        run = run_app_server(
            CONFIG, transport_factory(transport), records.append, decline
        )

        self.assertEqual("completed", run.terminal_status)
        self.assertEqual(
            ["turn/started", "item/started", "item/commandExecution/requestApproval", "item/commandExecution/requestApproval", "turn/start"],
            [record.method for record in records[2:7]],
        )
        self.assertEqual("decline", transport.sent[-1]["result"]["decision"])

    def test_interleaved_approval_is_answered_before_turn_start_response(self) -> None:
        messages = success_messages()
        before_decision = messages[:2] + messages[3:6]
        after_decision = [messages[2]] + messages[6:]
        transport = ApprovalGatedTransport(before_decision, after_decision)

        run = run_app_server(CONFIG, transport_factory(transport), lambda _record: None, decline)

        self.assertEqual("completed", run.terminal_status)
        decisions = [message for message in transport.sent if "result" in message]
        self.assertEqual("decline", decisions[0]["result"]["decision"])
        self.assertEqual(
            ["turn/started", "item/started", "item/commandExecution/requestApproval", "item/commandExecution/requestApproval", "turn/start"],
            [record.method for record in run.records[2:7]],
        )

    def test_provisional_turn_identity_must_match_turn_start_response(self) -> None:
        messages = success_messages()
        turn_started = messages.pop(3)
        messages.insert(2, turn_started)
        messages[3]["result"]["turn"]["id"] = "turn-response-mismatch"

        with self.assertRaisesRegex(AppServerError, "turn/start identity mismatch"):
            run_app_server(CONFIG, transport_factory(FakeTransport(messages)), lambda _record: None, decline)

    def test_queued_thread_started_requires_exact_scope_and_is_not_duplicated(self) -> None:
        base = success_messages()
        valid = {"method": "thread/started", "params": {"thread": copy.deepcopy(base[1]["result"]["thread"])}}
        foreign = copy.deepcopy(valid)
        foreign["params"]["thread"]["id"] = "thread-foreign"
        attacks = (([foreign], "identity mismatch"), ([valid, copy.deepcopy(valid)], "duplicate"))

        for queued, expected in attacks:
            with self.subTest(expected=expected), self.assertRaisesRegex(AppServerError, expected):
                messages = success_messages()
                messages[1:1] = queued
                run_app_server(CONFIG, transport_factory(FakeTransport(messages)), lambda _record: None, decline)

    def test_queued_notification_does_not_hide_wrong_response_id(self) -> None:
        messages = success_messages()
        queued = {"method": "thread/started", "params": {"thread": copy.deepcopy(messages[1]["result"]["thread"])}}
        messages.insert(1, queued)
        messages[2]["id"] = 99
        records = []

        with self.assertRaisesRegex(AppServerError, "response id mismatch"):
            run_app_server(CONFIG, transport_factory(FakeTransport(messages)), records.append, decline)

        self.assertIn("thread/started", [record.method for record in records])

    def test_pending_message_timeout_and_overflow_fail_closed(self) -> None:
        thread = copy.deepcopy(success_messages()[1]["result"]["thread"])
        queued = {"method": "thread/started", "params": {"thread": thread}}

        class TimeoutAfterQueue(FakeTransport):
            def receive(self, timeout_seconds: float) -> str | None:
                if self.lines:
                    return super().receive(timeout_seconds)
                raise TimeoutError("fixture timeout")

        with self.assertRaisesRegex(AppServerError, "timeout"):
            run_app_server(
                CONFIG,
                transport_factory(TimeoutAfterQueue([success_messages()[0], queued])),
                lambda _record: None,
                decline,
            )

        overflow = [success_messages()[0]] + [
            {"method": "thread/status/changed", "params": {}} for _ in range(129)
        ]
        with self.assertRaisesRegex(AppServerError, "overflow"):
            run_app_server(CONFIG, transport_factory(FakeTransport(overflow)), lambda _record: None, decline)

    def test_queued_terminal_still_requires_complete_approval_chain(self) -> None:
        messages = success_messages()
        del messages[6]
        turn_response = messages[2]
        messages = messages[:2] + messages[3:] + [turn_response]

        with self.assertRaisesRegex(AppServerError, "serverRequest/resolved"):
            run_app_server(
                CONFIG,
                transport_factory(FakeTransport(messages)),
                lambda _record: None,
                decline,
            )

    def test_queued_terminal_preserves_the_already_read_turn_response(self) -> None:
        messages = success_messages()
        turn_response = messages[2]
        messages = messages[:2] + messages[3:] + [turn_response]

        run = run_app_server(
            CONFIG,
            transport_factory(FakeTransport(messages)),
            lambda _record: None,
            decline,
        )

        methods = [record.method for record in run.records]
        self.assertEqual("turn/completed", methods[-2])
        self.assertEqual("turn/start", methods[-1])
        self.assertEqual(1, methods.count("turn/start"))

    def test_schema_shaped_messages_without_legacy_jsonrpc_are_accepted(self) -> None:
        messages = success_messages()
        for message in messages:
            message.pop("jsonrpc", None)
        transport = FakeTransport(messages)

        run = run_app_server(
            CONFIG, transport_factory(transport), lambda _record: None, decline
        )

        self.assertEqual("completed", run.terminal_status)

    def test_malformed_or_ambiguous_wire_envelopes_are_rejected(self) -> None:
        attacks = (
            ({"id": 1, "result": {}, "error": {"code": -1}}, "response envelope"),
            ({"id": 1}, "response envelope"),
            ({"id": 1, "method": "initialize", "result": {}}, "request envelope"),
            ({"method": "turn/started", "result": {}}, "notification envelope"),
            ({"jsonrpc": "1.0", "id": 1, "result": {}}, "jsonrpc"),
        )
        for attack, expected in attacks:
            with self.subTest(attack=attack), self.assertRaisesRegex(
                AppServerError, expected
            ):
                run_app_server(
                    CONFIG,
                    transport_factory(FakeTransport([attack])),
                    lambda _record: None,
                    decline,
                )

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
                {"jsonrpc":"2.0","id":3,"method":"turn/start","params":{"threadId":"thread-fixture","input":[{"type":"text","text":"fixture prompt"}],"effort":"low","approvalPolicy":"on-request"}},
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

    def test_initialize_accepts_a_nonempty_opaque_upstream_user_agent(self) -> None:
        messages = success_messages()
        messages[0]["result"]["userAgent"] = "codex-app-server/opaque-upstream-build"

        run = run_app_server(
            CONFIG,
            transport_factory(FakeTransport(messages)),
            lambda _record: None,
            decline,
        )

        self.assertEqual("completed", run.terminal_status)

    def test_initialize_rejects_missing_empty_or_non_string_user_agent(self) -> None:
        for user_agent in (None, "", 1533):
            messages = success_messages()
            if user_agent is None:
                messages[0]["result"].pop("userAgent")
            else:
                messages[0]["result"]["userAgent"] = user_agent

            with self.subTest(user_agent=user_agent), self.assertRaisesRegex(
                AppServerError, "userAgent"
            ):
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

    def test_active_protocol_traffic_refreshes_idle_timeout(self) -> None:
        clock = type("Clock", (), {"now": 0.0})()

        class ActiveTransport(FakeTransport):
            def receive(self, timeout_seconds: float) -> str | None:
                clock.now += 1.0
                return super().receive(timeout_seconds)

        config = copy.copy(CONFIG)
        object.__setattr__(config, "timeout_seconds", 2.0)
        object.__setattr__(config, "absolute_timeout_seconds", 20.0)
        with patch("devharness.codex_app_server.time.monotonic", side_effect=lambda: clock.now):
            run = run_app_server(
                config,
                transport_factory(ActiveTransport(success_messages())),
                lambda _record: None,
                decline,
            )

        self.assertEqual("completed", run.terminal_status)
        self.assertGreater(clock.now, config.timeout_seconds)

    def test_continuous_traffic_cannot_exceed_absolute_timeout(self) -> None:
        clock = type("Clock", (), {"now": 0.0})()
        messages = [success_messages()[0]] + [
            {"method": "thread/status/changed", "params": {}} for _ in range(20)
        ]

        class ActiveTransport(FakeTransport):
            def receive(self, timeout_seconds: float) -> str | None:
                clock.now += 1.0
                return super().receive(timeout_seconds)

        config = copy.copy(CONFIG)
        object.__setattr__(config, "timeout_seconds", 2.0)
        object.__setattr__(config, "absolute_timeout_seconds", 5.0)
        with patch("devharness.codex_app_server.time.monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(AppServerError, "absolute timeout"):
                run_app_server(
                    config,
                    transport_factory(ActiveTransport(messages)),
                    lambda _record: None,
                    decline,
                )

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

"""F01-F14 acceptance fixtures for the Dashboard WI-04 HTTP boundary (#95)."""
import hashlib
import http.client
import json
import logging
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from devharness.catalog import Catalog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.events import EventLog
from devharness.lifecycle.store import LifecycleStore
import tests.test_claim_evaluation as claim_fixtures
import tests.test_dashboard_presentation as wi03
import tests.test_dashboard_read_model as wi02

try:
    from devharness.dashboard.server import DashboardServer
    from devharness.dashboard.generator import ProviderConfig
except ImportError:  # RED must be an assertion failure, not a fixture import error.
    DashboardServer = ProviderConfig = None


PREFIX = "/api/dashboard/v1"
CHUNK = 64 * 1024


class Response:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

    @property
    def json(self):
        return json.loads(self.body)

    @property
    def code(self):
        return self.json["error"]["code"]


class Client:
    """Minimal browser stand-in: keeps the session cookie and the CSRF token."""

    def __init__(self, address):
        self.address = address
        self.authority = "%s:%d" % address
        self.cookie = None
        self.csrf = None

    def send(self, method, path, *, body=None, headers=None, host=None,
             origin=None, cookie=True, csrf=True):
        sent = {"Host": host or self.authority}
        if origin is not None:
            sent["Origin"] = origin
        if cookie and self.cookie:
            sent["Cookie"] = self.cookie
        if csrf and self.csrf and method != "GET":
            sent["X-OwnHands-CSRF"] = self.csrf
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            sent["Content-Type"] = "application/json"
        sent.update(headers or {})
        connection = http.client.HTTPConnection(*self.address, timeout=30)
        try:
            connection.request(method, path, body=payload, headers=sent)
            raw = connection.getresponse()
            return Response(raw.status, dict(raw.getheaders()), raw.read())
        finally:
            connection.close()

    def login(self, token):
        response = self.send("POST", PREFIX + "/session", body={"token": token}, csrf=False)
        if response.status == 200:
            self.cookie = response.headers["Set-Cookie"].split(";", 1)[0]
            self.csrf = response.json["csrf_token"]
        return response

    def get(self, path, **kwargs):
        return self.send("GET", PREFIX + path, **kwargs)

    def post(self, path, **kwargs):
        return self.send("POST", PREFIX + path, **kwargs)


class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(DashboardServer, "Dashboard HTTP server is not implemented")
        self.builder = wi02.DashboardReadModelTests()
        self.builder.setUp()
        self.addCleanup(self.builder.fixture.tearDown)
        self.fixture = self.builder.fixture
        self.generator = wi03.RecordingGenerator()
        self.clock = wi03.Clock()
        self.records = []

    # --- helpers -----------------------------------------------------------

    def serve(self, *, paths=None, project_id=None, generator=None, environment=None, **kwargs):
        handler = logging.Handler()
        handler.emit = self.records.append
        logger = logging.getLogger("devharness.dashboard.test." + self.id())
        logger.setLevel(logging.INFO)
        logger.handlers = [handler]
        logger.propagate = False
        server = DashboardServer(
            paths or self.fixture.paths,
            self.fixture.task.project_id if project_id is None else project_id,
            config=ProviderConfig.from_environment(
                wi03.ENVIRONMENT if environment is None else environment),
            generator=self.generator if generator is None else generator,
            clock=self.clock, logger=logger, **kwargs,
        )
        server.start()
        self.addCleanup(server.stop)
        return server

    def client(self, server, *, login=True):
        client = Client(server.address)
        if login:
            self.assertEqual(client.login(server.token).status, 200)
        return client

    def logged(self):
        return "\n".join(record.getMessage() for record in self.records)

    def snapshot(self, suffix="api", **kwargs):
        kwargs.setdefault("status", "verified")
        kwargs.setdefault("activate_inputs", True)
        return self.builder.simple_snapshot(suffix, title="위젯 저장", **kwargs)

    def key_of(self, item):
        catalog = Catalog.open_readonly(self.fixture.paths)
        store = LifecycleStore.open_readonly(catalog)
        try:
            from devharness.dashboard.read_model import DashboardReadModel
            return DashboardReadModel(
                catalog, store, self.fixture.task.project_id).snapshot_key(item["snapshot"])
        finally:
            store.close()
            catalog.close()

    def evidence_key(self, client, key):
        claim = client.get("/snapshots/" + key).json["claims"][0]
        # A legacy v1 Review carries no checks; its Observations hold the same links.
        holders = [value for check in claim["checks"] for value in check["after"]]
        return (holders or claim["observations"])[0]["evidence_links"][0]["evidence_key"]

    def evidence_store(self):
        return EvidenceStore(self.fixture.catalog, EventLog(self.fixture.catalog))

    @contextmanager
    def redaction(self, status):
        """Stored Evidence rows are immutable, so the status is set at capture time."""
        original = claim_fixtures.EvidenceDraft
        with patch.object(claim_fixtures, "EvidenceDraft",
                          lambda *args: original(*args[:-1], status)):
            yield

    # --- F01 ---------------------------------------------------------------

    def test_f01_reads_never_create_migrate_or_touch_the_sources(self):
        item = self.snapshot("f01")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        before = self.builder.inventory()
        for path in ("/reviews", "/snapshots/" + key, "/snapshots/" + key + "/presentation"):
            self.assertEqual(client.get(path).status, 200)
        self.assertEqual(before, self.builder.inventory(),
                         "GET must not create, migrate or reconcile the sources")

    def test_f01_a_missing_source_is_reported_not_created(self):
        empty = Path(self.fixture.temp.name) / "empty-root"
        empty.mkdir()
        from devharness.paths import DataPaths
        server = self.serve(paths=DataPaths.resolve(empty))
        client = Client(server.address)
        self.assertEqual(client.login(server.token).status, 200)
        response = client.get("/reviews")
        self.assertEqual(response.status, 503)
        self.assertEqual(response.code, "SOURCE_UNAVAILABLE")
        self.assertEqual(sorted(path.name for path in empty.iterdir()), [],
                         "a missing source must never be created by a read")

    # --- F02 ---------------------------------------------------------------

    def test_f02_out_of_scope_and_unknown_keys_are_one_indistinguishable_not_found(self):
        item = self.snapshot("f02")
        other = self.builder.simple_snapshot("f02-other", title="다른 Snapshot",
                                             status="verified", activate_inputs=True)
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        other_key = self.key_of(other)
        foreign_evidence = self.evidence_key(client, other_key)
        bodies = []
        for path in ("/snapshots/" + "0" * 64,
                     "/snapshots/" + key + "/claims/does-not-exist",
                     "/snapshots/" + key + "/evidence/" + foreign_evidence,
                     "/snapshots/" + key + "/evidence/" + "f" * 32):
            response = client.get(path)
            self.assertEqual(response.status, 404, path)
            payload = response.json
            self.assertEqual(payload["error"]["code"], "NOT_FOUND")
            self.assertFalse(payload["error"]["retryable"])
            bodies.append(payload["error"])
        self.assertEqual(len({json.dumps(body, sort_keys=True) for body in bodies}), 1,
                         "an out-of-scope key must not be distinguishable from a missing one")

    # --- F03 ---------------------------------------------------------------

    def test_f03_every_get_is_free_of_source_writes_and_provider_calls(self):
        item = self.snapshot("f03")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        evidence_key = self.evidence_key(client, key)
        blocked = []

        def deny(name):
            def refuse(*_args, **_kwargs):
                blocked.append(name)
                raise AssertionError("Dashboard must not call " + name)
            return refuse

        for owner, name in ((LifecycleStore, "append"), (LifecycleStore, "activate"),
                            (LifecycleStore, "bind_evidence"), (LifecycleStore, "evaluate_review"),
                            (EvidenceStore, "put"), (EvidenceStore, "purge")):
            started = patch.object(owner, name, deny(name))
            started.start()
            self.addCleanup(started.stop)
        for _ in range(2):
            for path in ("/reviews", "/snapshots/" + key,
                         "/snapshots/" + key + "/claims/c1",
                         "/snapshots/" + key + "/evidence/" + evidence_key,
                         "/snapshots/" + key + "/evidence/" + evidence_key + "/content?field=raw",
                         "/snapshots/" + key + "/presentation"):
                self.assertEqual(client.get(path).status, 200, path)
        self.assertEqual(blocked, [])
        self.assertEqual(self.generator.calls, [], "no GET may reach the provider")

    # --- F04 ---------------------------------------------------------------

    def test_f04_only_an_ensure_miss_generates_and_the_sources_stay_untouched(self):
        item = self.snapshot("f04")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        before = self.builder.inventory()

        self.assertEqual(client.get("/snapshots/" + key + "/presentation").json["status"], "absent")
        self.assertEqual(self.generator.calls, [])

        first = client.post("/snapshots/" + key + "/presentation/ensure",
                            body={"view_intent": "detail"})
        self.assertEqual(first.status, 200)
        self.assertEqual(first.json["status"], "ready")
        self.assertEqual(len(self.generator.calls), 1)

        for _ in range(3):
            hit = client.post("/snapshots/" + key + "/presentation/ensure",
                              body={"view_intent": "list_visible"})
            self.assertEqual(hit.json["status"], "ready")
            self.assertEqual(client.get("/snapshots/" + key + "/presentation").json["status"],
                             "ready")
        self.assertEqual(len(self.generator.calls), 1)

        changed = {name for name in set(before) | set(self.builder.inventory())
                   if before.get(name) != self.builder.inventory().get(name)}
        self.assertEqual(changed, {"dashboard-presentation.sqlite3"},
                         "ensure may write the presentation cache and nothing else")

    def test_f04_a_failed_presentation_is_a_normal_200_not_a_transport_error(self):
        item = self.snapshot("f04-failed")
        from devharness.dashboard.generator import GeneratorError
        server = self.serve(generator=wi03.RecordingGenerator(error=GeneratorError("timeout")))
        client = self.client(server)
        key = self.key_of(item)
        response = client.post("/snapshots/" + key + "/presentation/ensure",
                               body={"view_intent": "detail"})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json["status"], "failed")
        self.assertTrue(response.json["fallback"])
        self.assertNotIn("error", response.json)

    def test_f04_an_unsupported_view_intent_is_a_client_error(self):
        item = self.snapshot("f04-intent")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        for body in ({"view_intent": "drawer"}, {"view_intent": ""}, {}):
            response = client.post("/snapshots/" + key + "/presentation/ensure", body=body)
            self.assertEqual(response.status, 400, body)
            self.assertEqual(response.code, "INVALID_QUERY")
        self.assertEqual(self.generator.calls, [])

    # --- F05 ---------------------------------------------------------------

    def test_f05_large_content_is_chunked_under_64_kib_and_reassembles_exactly(self):
        f = self.fixture
        f.configure("current")
        text = ("가나다 widget line %04d\n" % 0).join(
            "line %05d ascii payload\n" % index for index in range(9000))
        payload = text.encode("utf-8")
        self.assertGreater(len(payload), 200 * 1024)
        f.observe(content=payload)
        review = f.store.append("review", "review:f05", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f05")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        evidence_key = self.evidence_key(client, key)

        collected = ""
        cursor = None
        seen = []
        for _ in range(20):
            path = ("/snapshots/" + key + "/evidence/" + evidence_key + "/content?field=raw"
                    + ("&cursor=" + cursor if cursor else ""))
            field = client.get(path).json
            self.assertEqual(field["availability"], "available")
            self.assertLessEqual(len(field["text"].encode("utf-8")), CHUNK)
            collected += field["text"]
            cursor = field["next_cursor"]
            seen.append(cursor)
            if cursor is None:
                break
        self.assertIsNone(cursor, "the reader must terminate")
        self.assertGreater(len(seen), 3, "200KiB must not arrive in one response")
        self.assertEqual(collected, payload.decode("utf-8"))
        self.assertFalse(any(value and len(value) > 4096 for value in seen))

    def test_f05_a_cursor_is_opaque_and_bound_to_its_evidence_field_and_content(self):
        f = self.fixture
        f.configure(checks=("normal", "retry"))
        f.observe(content=b"left" * 40000)
        f.observe(check="retry", content=b"right" * 40000)
        review = f.store.append("review", "review:f05-cursor", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f05-cursor")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        detail = client.get("/snapshots/" + key).json
        keys = [check["after"][0]["evidence_links"][0]["evidence_key"]
                for check in detail["claims"][0]["checks"]]
        base = "/snapshots/" + key + "/evidence/"
        cursor = client.get(base + keys[0] + "/content?field=raw").json["next_cursor"]
        self.assertIsNotNone(cursor)
        self.assertNotIn("/", cursor)
        self.assertNotIn("evidence:", cursor)

        foreign = client.get(base + keys[1] + "/content?field=raw&cursor=" + cursor)
        self.assertEqual(foreign.status, 400)
        self.assertEqual(foreign.code, "INVALID_QUERY")
        for bad in ("not-a-cursor", "", "eyJ2YWx1ZSI6MX0"):
            response = client.get(base + keys[0] + "/content?field=raw&cursor=" + bad)
            self.assertEqual(response.status, 400, bad)
            self.assertEqual(response.code, "INVALID_QUERY")
        self.assertEqual(client.get(base + keys[0] + "/content?field=nope").status, 400)
        self.assertEqual(client.get(base + keys[0] + "/content").status, 400)

    # --- F06 ---------------------------------------------------------------

    def test_f06_availability_is_exact_and_binary_is_never_force_decoded(self):
        f = self.fixture
        f.configure(checks=("normal", "retry", "binary"))
        f.observe(content=b"plain text evidence")
        f.observe(check="retry", content=b"purge me")
        f.observe(check="binary", content=b"\x89PNG\r\n\x1a\n\x00\x00binary")
        review = f.store.append("review", "review:f06", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f06")
        store = self.evidence_store()
        store.purge("evidence:2", "Fixture purge")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        detail = client.get("/snapshots/" + key).json
        keys = [check["after"][0]["evidence_links"][0]["evidence_key"]
                for check in detail["claims"][0]["checks"]]
        base = "/snapshots/" + key + "/evidence/"

        readable = client.get(base + keys[0] + "/content?field=raw").json
        self.assertEqual(readable["availability"], "available")
        self.assertEqual(readable["text"], "plain text evidence")

        purged = client.get(base + keys[1] + "/content?field=raw").json
        self.assertEqual(purged["availability"], "purged")
        self.assertIsNone(purged["text"])

        binary = client.get(base + keys[2] + "/content?field=raw").json
        self.assertEqual(binary["availability"], "unsupported")
        self.assertIsNone(binary["text"])
        self.assertEqual(binary["reason_code"], "binary_content")

        absent = client.get(base + keys[0] + "/content?field=command").json
        self.assertEqual(absent["availability"], "not_collected")
        self.assertIsNone(absent["text"])

    def test_f06_missing_and_reference_only_content_stay_distinct(self):
        f = self.fixture
        f.configure(checks=("normal", "retry"))
        f.observe(content=b"will go missing")
        with self.redaction("reference_only"):
            f.observe(check="retry", content=b"reference only body")
        review = f.store.append("review", "review:f06-missing", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f06-missing")
        store = self.evidence_store()
        store.resolve("evidence:1").object_path.unlink()
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        detail = client.get("/snapshots/" + key).json
        keys = [check["after"][0]["evidence_links"][0]["evidence_key"]
                for check in detail["claims"][0]["checks"]]
        base = "/snapshots/" + key + "/evidence/"
        missing = client.get(base + keys[0] + "/content?field=raw").json
        reference = client.get(base + keys[1] + "/content?field=raw").json
        self.assertEqual(missing["availability"], "missing")
        self.assertEqual(reference["availability"], "unsupported")
        self.assertEqual(reference["reason_code"], "reference_only")
        self.assertIsNone(missing["text"])
        self.assertIsNone(reference["text"])

    # --- F07 ---------------------------------------------------------------

    def test_f07_markup_and_ansi_arrive_as_inert_escaped_text(self):
        f = self.fixture
        f.configure("current")
        hostile = ("<script>alert('x')</script>\n"
                   "\x1b[31mred\x1b[0m\n"
                   "<img src=x onerror=alert(1)>\n"
                   "bell\x07 and null-free\n").encode("utf-8")
        f.observe(content=hostile)
        review = f.store.append("review", "review:f07", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f07")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        evidence_key = self.evidence_key(client, key)
        response = client.get("/snapshots/" + key + "/evidence/" + evidence_key
                              + "/content?field=raw")
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
        text = response.json["text"]
        self.assertNotIn("\x1b", text, "ANSI escapes must not survive as control bytes")
        self.assertNotIn("\x07", text)
        self.assertIn("\\x1b", text, "control bytes become visible escapes")
        self.assertIn("<script>", text, "markup is preserved as data, not silently rewritten")

    # --- F08 ---------------------------------------------------------------

    def test_f08_traversal_urls_and_scope_overrides_reach_nothing(self):
        item = self.snapshot("f08")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        evidence_key = self.evidence_key(client, key)
        for path in ("/snapshots/../../etc/passwd",
                     "/snapshots/" + key + "/evidence/..%2f..%2fetc%2fpasswd",
                     "/snapshots/" + key + "/evidence/" + evidence_key
                     + "/content?field=raw&path=/etc/passwd",
                     "/snapshots/" + key + "/evidence/" + evidence_key
                     + "/content?field=file:///etc/passwd",
                     "/snapshots/" + key + "?data_root=/tmp&project_id=other",
                     "/reviews?project_id=other&data_root=/tmp"):
            response = client.get(path)
            self.assertIn(response.status, (200, 400, 404), path)
            self.assertNotIn(b"root:", response.body, path)
            self.assertNotIn(b"/etc/passwd", response.body, path)
        scoped = client.get("/snapshots/" + key + "?project_id=other").json
        self.assertEqual(scoped["scope"]["project_id"], self.fixture.task.project_id,
                         "scope is server-owned and cannot be overridden by a query")

    # --- F09 ---------------------------------------------------------------

    def test_f09_a_missing_or_wrong_token_is_401_and_never_leaks(self):
        item = self.snapshot("f09")
        server = self.serve()
        key = self.key_of(item)
        anonymous = Client(server.address)
        for path in ("/reviews", "/snapshots/" + key):
            response = anonymous.get(path)
            self.assertEqual(response.status, 401, path)
            self.assertEqual(response.code, "UNAUTHENTICATED")
        self.assertEqual(anonymous.login("wrong-token").status, 401)
        self.assertIsNone(anonymous.cookie)

        # A token offered in the query string must never authenticate a request.
        self.assertEqual(anonymous.get("/reviews?token=" + server.token).status, 401)
        self.assertNotIn(server.token, self.logged())
        self.assertNotIn("token=", self.logged())

    def test_f09_the_session_cookie_is_httponly_samesite_strict_and_not_in_the_body(self):
        self.snapshot("f09-cookie")
        server = self.serve()
        client = Client(server.address)
        response = client.login(server.token)
        self.assertEqual(response.status, 200)
        cookie = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertNotIn(server.token, cookie)
        self.assertNotIn(server.token, response.body.decode())
        self.assertNotIn(client.cookie.split("=", 1)[1], response.body.decode(),
                         "the session id belongs in the cookie, not the body")
        self.assertEqual(set(response.json), {"csrf_token"})

    # --- F10 ---------------------------------------------------------------

    def test_f10_foreign_host_origin_and_cors_are_refused(self):
        item = self.snapshot("f10")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        for kwargs in ({"host": "evil.example:8080"},
                       {"origin": "http://evil.example"},
                       {"origin": "null"},
                       {"host": "127.0.0.1:1"}):
            response = client.get("/reviews", **kwargs)
            self.assertEqual(response.status, 403, kwargs)
            self.assertEqual(response.code, "ORIGIN_DENIED")
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        preflight = client.send("OPTIONS", PREFIX + "/reviews", origin="http://evil.example")
        self.assertIn(preflight.status, (403, 405))
        self.assertNotIn("Access-Control-Allow-Origin", preflight.headers)
        self.assertEqual(self.generator.calls, [])
        self.assertEqual(client.get("/snapshots/" + key,
                                    origin="http://%s:%d" % server.address).status, 200)

    def test_f10_a_post_without_the_csrf_header_never_reaches_ensure(self):
        item = self.snapshot("f10-csrf")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        path = "/snapshots/" + key + "/presentation/ensure"
        for headers in ({}, {"X-OwnHands-CSRF": "wrong"}):
            response = client.send("POST", PREFIX + path, body={"view_intent": "detail"},
                                   headers=headers, csrf=False)
            self.assertEqual(response.status, 403, headers)
            self.assertEqual(response.code, "CSRF_FAILED")
        self.assertEqual(self.generator.calls, [])
        self.assertEqual(client.post(path, body={"view_intent": "detail"}).status, 200)
        self.assertEqual(len(self.generator.calls), 1)

    # --- F11 ---------------------------------------------------------------

    def test_f11_reader_errors_keep_a_fixed_status_and_envelope(self):
        item = self.snapshot("f11")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        for query, status, code in (("?filter=nope", 400, "INVALID_QUERY"),
                                    ("?limit=0", 400, "INVALID_QUERY"),
                                    ("?limit=500", 400, "INVALID_QUERY"),
                                    ("?cursor=broken", 400, "INVALID_QUERY"),
                                    ("?q=" + "x" * 201, 400, "INVALID_QUERY")):
            response = client.get("/reviews" + query)
            self.assertEqual(response.status, status, query)
            self.assertEqual(response.code, code, query)
            self.assertEqual(set(response.json), {"error", "request_id"})
            self.assertEqual(set(response.json["error"]), {"code", "message", "retryable"})

        stale = client.post("/snapshots/" + key + "/presentation/ensure",
                            body={"view_intent": "detail", "recipe_hash": "0" * 64})
        self.assertEqual(stale.status, 409)
        self.assertEqual(stale.code, "RECIPE_CHANGED")
        self.assertEqual(self.generator.calls, [])

    def test_f11_a_source_that_keeps_changing_is_a_retryable_409(self):
        item = self.snapshot("f11-changed")
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        from devharness.dashboard.read_model import DashboardReadModel
        original = DashboardReadModel._source_head
        counter = {"n": 0}

        def moving(self_):
            counter["n"] += 1
            return original(self_) + ":" + str(counter["n"])

        with patch.object(DashboardReadModel, "_source_head", moving):
            response = client.get("/snapshots/" + key)
        self.assertEqual(response.status, 409)
        self.assertEqual(response.code, "SOURCE_CHANGED")
        self.assertTrue(response.json["error"]["retryable"])

    # --- F12 ---------------------------------------------------------------

    def test_f12_content_that_changes_mid_read_is_never_mixed(self):
        f = self.fixture
        f.configure("current")
        f.observe(content=b"stable chunk " * 12000)
        review = f.store.append("review", "review:f12", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f12")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        evidence_key = self.evidence_key(client, key)
        base = "/snapshots/" + key + "/evidence/" + evidence_key + "/content?field=raw"
        first = client.get(base).json
        self.assertEqual(first["availability"], "available")
        self.assertIsNotNone(first["next_cursor"])

        record = self.evidence_store().resolve("evidence:1")
        record.object_path.write_bytes(b"tampered payload")
        second = client.get(base + "&cursor=" + first["next_cursor"])
        self.assertIn(second.status, (200, 503))
        if second.status == 200:
            self.assertEqual(second.json["availability"], "corrupt")
            self.assertIsNone(second.json["text"])
            self.assertIsNone(second.json["next_cursor"])
        else:
            self.assertEqual(second.code, "SOURCE_INTEGRITY_ERROR")
        self.assertNotIn(b"tampered payload", second.body)

    def test_f12_a_size_change_is_reported_not_silently_truncated(self):
        f = self.fixture
        f.configure("current")
        f.observe(content=b"original content")
        review = f.store.append("review", "review:f12-size", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f12-size")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        evidence_key = self.evidence_key(client, key)
        record = self.evidence_store().resolve("evidence:1")
        record.object_path.write_bytes(b"original content with more bytes appended")
        response = client.get("/snapshots/" + key + "/evidence/" + evidence_key
                              + "/content?field=raw")
        self.assertIn(response.status, (200, 503))
        self.assertNotIn(b"more bytes appended", response.body)
        if response.status == 200:
            self.assertEqual(response.json["availability"], "corrupt")

    # --- F13 ---------------------------------------------------------------

    def test_f13_logs_carry_route_templates_and_no_secret_or_body(self):
        f = self.fixture
        f.configure("current")
        f.observe(content=b"SECRET-RAW-EVIDENCE-BODY")
        review = f.store.append("review", "review:f13", f.scope, f.evaluate())
        snapshot = self.builder.append_snapshot(review, "snapshot:f13")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        evidence_key = self.evidence_key(client, key)
        client.get("/snapshots/" + key + "/evidence/" + evidence_key + "/content?field=raw")
        client.post("/snapshots/" + key + "/presentation/ensure", body={"view_intent": "detail"})
        client.get("/reviews?q=" + "secret-query")
        logged = self.logged()

        self.assertIn("/snapshots/{snapshot_key}", logged)
        self.assertTrue(any(str(code) in logged for code in (200,)))
        for secret in (server.token, client.csrf, client.cookie,
                       "SECRET-RAW-EVIDENCE-BODY", "secret-query", key, evidence_key,
                       wi03.ENVIRONMENT["OWNHANDS_PRESENTATION_API_KEY"],
                       wi03.ENVIRONMENT["OWNHANDS_PRESENTATION_BASE_URL"],
                       str(self.fixture.paths.root)):
            self.assertNotIn(secret, logged, "log leaked: " + secret[:24])

    # --- F14 ---------------------------------------------------------------

    def test_f14_only_loopback_may_be_bound(self):
        for host in ("0.0.0.0", "::", "192.168.1.10", "example.com", ""):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    DashboardServer(self.fixture.paths, self.fixture.task.project_id,
                                    host=host, config=ProviderConfig.from_environment({}))
        for host in ("127.0.0.1", "::1", "localhost"):
            with self.subTest(host=host):
                server = DashboardServer(self.fixture.paths, self.fixture.task.project_id,
                                         host=host, config=ProviderConfig.from_environment({}))
                self.addCleanup(server.stop)
                server.start()
                self.assertIn(server.address[0], ("127.0.0.1", "::1"))


class DashboardCommandTests(unittest.TestCase):
    """The CLI is thin glue; it must still pass host, port and scope through."""

    def test_the_dashboard_command_binds_the_requested_loopback_scope(self):
        self.assertIsNotNone(DashboardServer, "Dashboard HTTP server is not implemented")
        import devharness.__main__ as entry
        built = {}

        class Fake:
            authority = "127.0.0.1:9999"
            token = "boot-token"

            def __init__(self, paths, project_id, *, host, port):
                built.update(paths=paths, project_id=project_id, host=host, port=port)
                self._thread = self

            def start(self):
                built["started"] = True

            def join(self):
                raise KeyboardInterrupt

            def stop(self):
                built["stopped"] = True

        with patch("devharness.dashboard.server.DashboardServer", Fake),                 patch("sys.argv", ["devharness", "dashboard", "--project-id", "p1",
                                   "--data-root", "/tmp/devharness-cli", "--port", "9999"]):
            self.assertEqual(entry.main(), 0)
        self.assertEqual(built["project_id"], "p1")
        self.assertEqual(built["host"], "127.0.0.1")
        self.assertEqual(built["port"], 9999)
        self.assertTrue(built["started"] and built["stopped"])

    def test_a_non_loopback_host_is_refused_before_serving(self):
        import devharness.__main__ as entry
        with patch("sys.argv", ["devharness", "dashboard", "--project-id", "p1",
                                "--data-root", "/tmp/devharness-cli", "--host", "0.0.0.0"]):
            with self.assertRaises(SystemExit):
                entry.main()


if __name__ == "__main__":
    unittest.main()

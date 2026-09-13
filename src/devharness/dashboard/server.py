"""Loopback HTTP boundary for the Dashboard read model and Presentation cache.

Transport only: no SQL, no evaluation, no source writes. Every request opens its own
read-only sources so a sqlite connection never crosses a thread, and closes them again.
"""
from __future__ import annotations

import hmac
import json
import logging
import secrets
import socket
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from ..catalog import Catalog
from ..lifecycle.store import LifecycleStore
from .generator import ProviderConfig
from .presentation import PresentationService
from .read_model import DashboardReadModel, ReadModelError

PREFIX = "/api/dashboard/v1"
COOKIE = "ownhands_dashboard"
CSRF_HEADER = "X-OwnHands-CSRF"
LOOPBACK = {"127.0.0.1", "::1", "localhost"}

STATUS = {
    "INVALID_QUERY": 400,
    "UNAUTHENTICATED": 401,
    "ORIGIN_DENIED": 403,
    "CSRF_FAILED": 403,
    "NOT_FOUND": 404,
    "METHOD_NOT_ALLOWED": 405,
    "SOURCE_CHANGED": 409,
    "LIST_CHANGED": 409,
    "RECIPE_CHANGED": 409,
    # SDD §6.3 keeps source integrity in the 503 family: it is a source state, not a bug.
    "SOURCE_INTEGRITY_ERROR": 503,
    "SOURCE_UNAVAILABLE": 503,
    "UNSUPPORTED_SCHEMA": 503,
}
# Fixed text only: an error must never carry a path, a key, a credential or raw content.
MESSAGES = {
    "INVALID_QUERY": "The request is not valid for this Dashboard route",
    "UNAUTHENTICATED": "A Dashboard session is required",
    "ORIGIN_DENIED": "The request origin is not allowed",
    "CSRF_FAILED": "The request is missing a valid Dashboard CSRF token",
    "NOT_FOUND": "Dashboard resource was not found",
    "METHOD_NOT_ALLOWED": "The method is not allowed on this Dashboard route",
    "SOURCE_CHANGED": "Dashboard sources changed while reading",
    "LIST_CHANGED": "Dashboard sources changed while reading",
    "RECIPE_CHANGED": "Dashboard presentation recipe changed",
    "SOURCE_INTEGRITY_ERROR": "Dashboard source cannot be verified",
    "SOURCE_UNAVAILABLE": "Dashboard source is unavailable",
    "UNSUPPORTED_SCHEMA": "Dashboard source schema is not supported",
}
RETRYABLE = {"SOURCE_CHANGED", "LIST_CHANGED", "SOURCE_UNAVAILABLE"}


class _Denied(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class DashboardServer:
    def __init__(self, paths, project_id: str, *, host: str = "127.0.0.1", port: int = 0,
                 config: ProviderConfig | None = None, generator=None, clock=None,
                 logger: logging.Logger | None = None, cache_path=None) -> None:
        if host not in LOOPBACK:
            raise ValueError("Dashboard binds to loopback only")
        self.paths = paths
        self.project_id = project_id
        self.host = host
        self.port = port
        self.config = ProviderConfig.from_environment() if config is None else config
        self.generator = generator
        self.clock = clock
        self.logger = logger or logging.getLogger("devharness.dashboard")
        self.cache_path = Path(cache_path) if cache_path else paths.root / "dashboard-presentation.sqlite3"
        self.token = secrets.token_urlsafe(32)
        self.address = (host, port)
        self.sessions: dict[str, str] = {}
        # ponytail: one process-wide generation lock gives SDD §7.2.3 FIFO across keys;
        # split per-key queues only if a local Dashboard ever needs parallel providers.
        self.generation = threading.Lock()
        self._http = None
        self._thread = None

    # --- lifecycle ---------------------------------------------------------

    def start(self) -> "DashboardServer":
        server = self
        handler = type("_Handler", (_Handler,), {"dashboard": server})
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        service = type("_Service", (ThreadingHTTPServer,), {"address_family": family})
        self._http = service((self.host, self.port), handler)
        self._http.daemon_threads = True
        self.address = self._http.server_address[0], self._http.server_address[1]
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._http is not None:
            self._http.shutdown()
            self._http.server_close()
            self._http = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def authority(self) -> str:
        host, port = self.address
        return ("[%s]:%d" % (host, port)) if ":" in host else ("%s:%d" % (host, port))

    # --- per-request sources ------------------------------------------------

    def open_service(self):
        catalog = Catalog.open_readonly(self.paths)
        try:
            store = LifecycleStore.open_readonly(catalog)
        except BaseException:
            catalog.close()
            raise
        try:
            service = PresentationService(
                catalog, store, self.project_id, cache_path=self.cache_path,
                config=self.config, generator=self.generator, clock=self.clock)
        except BaseException:
            store.close()
            catalog.close()
            raise
        return service, (service.close, store.close, catalog.close)


class _Handler(BaseHTTPRequestHandler):
    dashboard: DashboardServer = None
    protocol_version = "HTTP/1.1"
    server_version = "OwnHandsDashboard/1"
    sys_version = ""

    def log_message(self, *_args) -> None:
        """Silence the stderr access log; the structured logger is the only record."""

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_OPTIONS(self):
        self._handle("OPTIONS")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_HEAD(self):
        self._handle("HEAD")

    # --- dispatch ----------------------------------------------------------

    def _handle(self, method: str) -> None:
        server = self.dashboard
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        template, code, status = "-", None, 200
        try:
            split = urlsplit(self.path)
            segments = [unquote(part) for part in split.path.split("/") if part]
            prefix = [part for part in PREFIX.split("/") if part]
            if segments[:len(prefix)] != prefix:
                raise _Denied("NOT_FOUND")
            route = segments[len(prefix):]
            template = self._template(route)
            self._guard(method, route)
            query = parse_qs(split.query, keep_blank_values=True)
            payload = self._route(method, route, query, request_id)
            self._respond(200, payload)
        except _Denied as denied:
            code = denied.code
            status = STATUS[code]
            self._respond(status, self._envelope(code, request_id))
        except ReadModelError as error:
            code = error.code if error.code in STATUS else "SOURCE_INTEGRITY_ERROR"
            status = STATUS[code]
            self._respond(status, self._envelope(code, request_id, error.retryable))
        except (sqlite3.Error, OSError):
            code, status = "SOURCE_UNAVAILABLE", 503
            self._respond(status, self._envelope(code, request_id))
        except (ValueError, RuntimeError):
            code, status = "SOURCE_INTEGRITY_ERROR", 503
            self._respond(status, self._envelope(code, request_id))
        finally:
            server.logger.info(
                "request_id=%s method=%s route=%s status=%s code=%s latency_ms=%d",
                request_id, method, template, status, code or "-",
                int((time.monotonic() - started) * 1000))

    @staticmethod
    def _template(route) -> str:
        if route[:1] == ["session"] and len(route) == 1:
            return "/session"
        if route[:1] == ["reviews"] and len(route) == 1:
            return "/reviews"
        if route[:1] == ["snapshots"]:
            tail = route[2:]
            names = {("claims",): "/claims/{claim_id}",
                     ("evidence",): "/evidence/{evidence_key}",
                     ("presentation",): "/presentation"}
            if not tail:
                return "/snapshots/{snapshot_key}"
            if tail[0] == "claims" and len(tail) == 2:
                return "/snapshots/{snapshot_key}/claims/{claim_id}"
            if tail[0] == "evidence" and len(tail) == 2:
                return "/snapshots/{snapshot_key}/evidence/{evidence_key}"
            if tail[0] == "evidence" and tail[2:] == ["content"]:
                return "/snapshots/{snapshot_key}/evidence/{evidence_key}/content"
            if tail == ["presentation"]:
                return "/snapshots/{snapshot_key}/presentation"
            if tail == ["presentation", "ensure"]:
                return "/snapshots/{snapshot_key}/presentation/ensure"
            _ = names
        return "-"

    # --- boundary checks ----------------------------------------------------

    def _guard(self, method: str, route) -> None:
        server = self.dashboard
        if (self.headers.get("Host") or "") != server.authority:
            raise _Denied("ORIGIN_DENIED")
        origin = self.headers.get("Origin")
        if origin is not None and origin != "http://" + server.authority:
            raise _Denied("ORIGIN_DENIED")
        if method in ("OPTIONS", "PUT", "DELETE", "HEAD"):
            raise _Denied("METHOD_NOT_ALLOWED")
        if route == ["session"]:
            if method != "POST":
                raise _Denied("METHOD_NOT_ALLOWED")
            return
        session = self._session()
        if session is None:
            raise _Denied("UNAUTHENTICATED")
        if method == "POST" and not hmac.compare_digest(
                self.headers.get(CSRF_HEADER) or "", session):
            raise _Denied("CSRF_FAILED")

    def _session(self) -> str | None:
        for part in (self.headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE:
                return self.dashboard.sessions.get(value)
        return None

    # --- routes -------------------------------------------------------------

    def _route(self, method: str, route, query, request_id: str):
        if route == ["session"]:
            return self._exchange()
        server = self.dashboard
        service, closers = server.open_service()
        try:
            if method == "GET" and route == ["reviews"]:
                return service.read_list(**self._list_query(query))
            if route[:1] != ["snapshots"] or len(route) < 2:
                raise _Denied("NOT_FOUND")
            key, tail = route[1], route[2:]
            if method == "GET" and not tail:
                return service.read_detail(key)
            if method == "GET" and len(tail) == 2 and tail[0] == "claims":
                return service.read_model.read_claim(key, tail[1])
            if method == "GET" and len(tail) == 2 and tail[0] == "evidence":
                return service.read_model.read_evidence(key, tail[1])
            if method == "GET" and len(tail) == 3 and tail[0] == "evidence" and tail[2] == "content":
                return service.read_model.read_content(
                    key, tail[1], self._one(query, "field", ""), self._one(query, "cursor", None))
            if method == "GET" and tail == ["presentation"]:
                return service.read_presentation(key)
            if method == "POST" and tail == ["presentation", "ensure"]:
                body = self._body()
                with server.generation:
                    return service.ensure_presentation(
                        key, view_intent=body.get("view_intent"),
                        recipe_hash=body.get("recipe_hash"))
            raise _Denied("NOT_FOUND" if method == "GET" else "METHOD_NOT_ALLOWED")
        finally:
            for close in closers:
                close()

    def _exchange(self):
        server = self.dashboard
        offered = self._body().get("token")
        if not isinstance(offered, str) or not hmac.compare_digest(offered, server.token):
            raise _Denied("UNAUTHENTICATED")
        session = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        server.sessions[session] = csrf
        self._cookie = ("%s=%s; HttpOnly; SameSite=Strict; Path=%s"
                        % (COOKIE, session, PREFIX))
        return {"csrf_token": csrf}

    # --- request/response helpers -------------------------------------------

    @staticmethod
    def _one(query, name, default):
        values = query.get(name)
        return default if not values else values[0]

    def _list_query(self, query) -> dict:
        limit = self._one(query, "limit", "20")
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise ReadModelError("INVALID_QUERY", "Limit must be an integer") from None
        return {"filter": self._one(query, "filter", "all"), "q": self._one(query, "q", ""),
                "cursor": self._one(query, "cursor", None), "limit": limit}

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ReadModelError("INVALID_QUERY", "Body length is invalid") from None
        if length <= 0 or length > 64 * 1024:
            return {}
        try:
            value = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            raise ReadModelError("INVALID_QUERY", "Body is not valid JSON") from None
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _envelope(code: str, request_id: str, retryable: bool | None = None) -> dict:
        return {"error": {"code": code, "message": MESSAGES[code],
                          "retryable": code in RETRYABLE if retryable is None else retryable},
                "request_id": request_id}

    def _respond(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        cookie = getattr(self, "_cookie", None)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

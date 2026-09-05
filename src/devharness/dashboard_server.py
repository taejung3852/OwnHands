from __future__ import annotations

import html
import re
import secrets
import socket
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from .dashboard_security import (
    RequestSecurityError,
    issue_csrf_token,
    require_opaque_identifier,
    validate_request_security,
)


_COOKIE_NAME = "devharness_session"
_MAX_BODY_BYTES = 64 * 1024
GET_ROUTES = (
    ("task", re.compile(r"^/tasks/(?P<task_id>[^/]+)$")),
    ("harness", re.compile(r"^/tasks/(?P<task_id>[^/]+)/harness$")),
    (
        "validation",
        re.compile(r"^/tasks/(?P<task_id>[^/]+)/validate/(?P<subject_ref>[^/]+)$"),
    ),
    ("history", re.compile(r"^/tasks/(?P<task_id>[^/]+)/history$")),
    (
        "evidence",
        re.compile(r"^/tasks/(?P<task_id>[^/]+)/evidence/(?P<evidence_id>[^/]+)$"),
    ),
)


@dataclass
class DashboardConfig:
    host: str
    port: int
    session_token: str
    data_root: Path
    _bootstrap_available: bool = field(default=True, init=False, repr=False)
    _bound_port: int | None = field(default=None, init=False, repr=False)
    _bootstrap_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.port, int) or isinstance(self.port, bool) or not 0 <= self.port <= 65535:
            raise ValueError("Dashboard port must be between 0 and 65535")
        if not isinstance(self.session_token, str) or not self.session_token:
            raise ValueError("Dashboard session token must be non-empty")
        self.data_root = Path(self.data_root)

    @property
    def csrf_token(self) -> str:
        return issue_csrf_token(self.session_token)

    @property
    def bound_port(self) -> int:
        return self._bound_port if self._bound_port is not None else self.port

    @property
    def origin(self) -> str:
        host = f"[{self.host}]" if self.host == "::1" else self.host
        return f"http://{host}:{self.bound_port}"

    def consume_bootstrap(self, candidate: str) -> bool:
        with self._bootstrap_lock:
            if not self._bootstrap_available or not secrets.compare_digest(
                candidate, self.session_token
            ):
                return False
            self._bootstrap_available = False
            return True


@dataclass(frozen=True)
class DashboardServices:
    load_view: Callable[[str], Any]
    resolve_evidence: Callable[[str, str, bool], tuple[Any, bytes | None]]
    validate_feature: Callable[[str, str, dict[str, str]], Any]
    decide: Callable[[Any, dict[str, str]], Any]
    export_history: Callable[[Any, tuple[str, ...]], bytes]


@dataclass(frozen=True)
class DashboardResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes


@dataclass(frozen=True)
class _Route:
    name: str
    task_id: str
    subject_ref: str | None = None
    evidence_id: str | None = None


def _match_route(path: str) -> _Route | None:
    for name, pattern in GET_ROUTES:
        matched = pattern.fullmatch(path)
        if matched is None:
            continue
        values = matched.groupdict()
        require_opaque_identifier(values["task_id"], "task_id")
        if values.get("subject_ref") is not None:
            require_opaque_identifier(values["subject_ref"], "subject_ref")
        if values.get("evidence_id") is not None:
            require_opaque_identifier(values["evidence_id"], "evidence_id")
        return _Route(name=name, **values)
    return None


def _security_headers(nonce: str) -> tuple[tuple[str, str], ...]:
    return (
        ("Cache-Control", "no-store"),
        (
            "Content-Security-Policy",
            "default-src 'none'; "
            f"style-src 'nonce-{nonce}'; script-src 'nonce-{nonce}'; "
            "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'",
        ),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
    )


def _response(
    status: int,
    body: bytes | str,
    *,
    content_type: str = "text/html; charset=utf-8",
    headers: Sequence[tuple[str, str]] = (),
) -> DashboardResponse:
    payload = body.encode("utf-8") if isinstance(body, str) else body
    nonce = secrets.token_urlsafe(18)
    all_headers = (
        ("Content-Type", content_type),
        ("Content-Length", str(len(payload))),
        *_security_headers(nonce),
        *headers,
    )
    return DashboardResponse(status=status, headers=tuple(all_headers), body=payload)


def _error(status: int, message: str) -> DashboardResponse:
    return _response(status, f"<!doctype html><title>Error</title><p>{html.escape(message)}</p>")


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.casefold()
    values = [value for key, value in headers.items() if key.casefold() == wanted]
    return values[0] if len(values) == 1 else None


def _session_cookie(headers: Mapping[str, str]) -> str:
    cookie = _header(headers, "Cookie")
    if not cookie:
        return ""
    matches = []
    for item in cookie.split(";"):
        name, separator, value = item.strip().partition("=")
        if separator and name == _COOKIE_NAME:
            matches.append(value)
    return matches[0] if len(matches) == 1 else ""


def _clean_location(path: str, query: Mapping[str, Sequence[str]]) -> str:
    clean_items = [
        (name, value)
        for name, values in query.items()
        if name != "session_token"
        for value in values
    ]
    suffix = urlencode(clean_items, doseq=True)
    return path if not suffix else f"{path}?{suffix}"


def _bootstrap_response(
    *,
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    headers: Mapping[str, str],
    config: DashboardConfig,
) -> DashboardResponse | None:
    if "session_token" not in query:
        return None
    values = query["session_token"]
    if method != "GET" or isinstance(values, (str, bytes)) or len(values) != 1:
        return _error(403, "session token is invalid")
    try:
        validate_request_security(
            host=_header(headers, "Host") or "",
            token=values[0],
            expected_token=config.session_token,
            method="GET",
            origin=None,
            expected_origin=config.origin,
            csrf_token=None,
            expected_csrf_token=config.csrf_token,
        )
    except RequestSecurityError as error:
        return _error(403, str(error))
    if not config.consume_bootstrap(values[0]):
        return _error(403, "session token is invalid")
    cookie = (
        f"{_COOKIE_NAME}={config.session_token}; Path=/; HttpOnly; SameSite=Strict"
    )
    return _response(
        303,
        b"",
        headers=(
            ("Location", _clean_location(path, query)),
            ("Set-Cookie", cookie),
        ),
    )


def _parse_form(headers: Mapping[str, str], body: bytes) -> dict[str, str]:
    content_type = _header(headers, "Content-Type") or ""
    if content_type.split(";", 1)[0].strip().lower() != "application/x-www-form-urlencoded":
        raise ValueError("POST body must be form encoded")
    if len(body) > _MAX_BODY_BYTES:
        raise ValueError("POST body is too large")
    try:
        text = body.decode("utf-8")
        parsed = parse_qs(
            text,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=50,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("POST form is invalid") from error
    if any(len(values) != 1 for values in parsed.values()):
        raise ValueError("POST form fields must be singular")
    return {name: values[0] for name, values in parsed.items()}


def _placeholder(title: str, detail: object = None) -> bytes:
    rendered = "" if detail is None else html.escape(str(detail))
    return (
        f"<!doctype html><html><head><title>{html.escape(title)}</title></head>"
        f"<body><main><h1>{html.escape(title)}</h1><pre>{rendered}</pre></main></body></html>"
    ).encode("utf-8")


def route_request(
    *,
    method: str,
    path: str,
    query: Mapping[str, Sequence[str]],
    headers: Mapping[str, str],
    body: bytes,
    config: DashboardConfig,
    services: DashboardServices,
) -> DashboardResponse:
    method = method.upper()
    if not isinstance(path, str) or "?" in path or "#" in path:
        return _error(400, "request path is invalid")
    if "session_token" in query:
        try:
            route = _match_route(path)
        except ValueError as error:
            return _error(400, str(error))
        if route is None:
            return _error(404, "route not found")
        bootstrap = _bootstrap_response(
            method=method, path=path, query=query, headers=headers, config=config
        )
        if bootstrap is not None:
            return bootstrap
    try:
        validate_request_security(
            host=_header(headers, "Host") or "",
            token=_session_cookie(headers),
            expected_token=config.session_token,
            method=method,
            origin=_header(headers, "Origin"),
            expected_origin=config.origin,
            csrf_token=_header(headers, "X-CSRF-Token"),
            expected_csrf_token=config.csrf_token,
        )
    except RequestSecurityError as error:
        return _error(403, str(error))
    try:
        route = _match_route(path)
    except ValueError as error:
        return _error(400, str(error))
    if route is None:
        return _error(404, "route not found")

    if method == "GET":
        try:
            view = services.load_view(route.task_id)
            if route.name == "evidence":
                raw_values = query.get("raw", ())
                if raw_values not in ((), ("1",), ["1"]):
                    return _error(400, "raw disclosure must be exactly raw=1")
                evidence, raw = services.resolve_evidence(
                    route.task_id,
                    route.evidence_id or "",
                    bool(raw_values),
                )
                detail = {"metadata": evidence.metadata}
                if raw is not None:
                    detail["raw"] = raw.decode("utf-8", errors="replace")
                return _response(200, _placeholder("Evidence Detail", detail))
            if route.name == "history" and query.get("format") in (("json",), ["json"]):
                sections = tuple(query.get("section", ("history",)))
                exported = services.export_history(view, sections)
                return _response(200, exported, content_type="application/json; charset=utf-8")
            titles = {
                "task": "Task Review",
                "harness": "Harness Status",
                "validation": "Feature Validation",
                "history": "Audit History",
            }
            detail = route.subject_ref if route.name == "validation" else None
            return _response(200, _placeholder(titles[route.name], detail))
        except (OSError, ValueError) as error:
            return _error(404, str(error))

    if method != "POST" or route.name not in {"task", "validation"}:
        return _error(405, "method not allowed")
    try:
        form = _parse_form(headers, body)
        if route.name == "task":
            current_view = services.load_view(route.task_id)
            services.decide(current_view, form)
            location = path
        else:
            services.validate_feature(route.task_id, route.subject_ref or "", form)
            location = path
        return _response(303, b"", headers=(("Location", location),))
    except (OSError, ValueError) as error:
        return _error(409, str(error))


def _handler(
    config: DashboardConfig, services: DashboardServices
) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def _dispatch(self) -> None:
            parsed = urlsplit(self.path)
            try:
                query = parse_qs(
                    parsed.query,
                    keep_blank_values=True,
                    strict_parsing=True,
                    max_num_fields=50,
                )
            except ValueError:
                response = _error(400, "query is invalid")
                self._send(response)
                return
            body = b""
            if self.command == "POST":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    self._send(_error(400, "Content-Length is invalid"))
                    return
                if length < 0 or length > _MAX_BODY_BYTES:
                    self._send(_error(413, "POST body is too large"))
                    return
                body = self.rfile.read(length)
            response = route_request(
                method=self.command,
                path=parsed.path,
                query=query,
                headers=dict(self.headers.items()),
                body=body,
                config=config,
                services=services,
            )
            self._send(response)

        def _send(self, response: DashboardResponse) -> None:
            self.send_response(response.status)
            for name, value in response.headers:
                self.send_header(name, value)
            self.end_headers()
            if response.body:
                self.wfile.write(response.body)

        do_GET = _dispatch
        do_POST = _dispatch
        do_HEAD = _dispatch
        do_PUT = _dispatch
        do_DELETE = _dispatch
        do_PATCH = _dispatch

        def log_message(self, format: str, *args: object) -> None:
            return None

    return DashboardHandler


def create_dashboard_server(
    config: DashboardConfig, services: DashboardServices
) -> ThreadingHTTPServer:
    if config.host not in {"127.0.0.1", "::1"}:
        raise ValueError("Dashboard must bind to loopback")
    server_type = ThreadingHTTPServer
    if config.host == "::1":
        class IPv6ThreadingHTTPServer(ThreadingHTTPServer):
            address_family = socket.AF_INET6

        server_type = IPv6ThreadingHTTPServer
    server = server_type((config.host, config.port), _handler(config, services))
    server.daemon_threads = True
    config._bound_port = int(server.server_address[1])
    return server


def serve_dashboard(config: DashboardConfig, services: DashboardServices) -> None:
    with create_dashboard_server(config, services) as server:
        print(f"dashboard={config.origin}/tasks/{{task_id}}?session_token={config.session_token}")
        server.serve_forever()

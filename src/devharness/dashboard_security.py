from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import unquote, urlsplit


class RequestSecurityError(ValueError):
    pass


_SECRET_KEY_FRAGMENTS = (
    "access_key",
    "api_key",
    "authorization",
    "cookie",
    "credential",
    "object_path",
    "object_relpath",
    "password",
    "private_key",
    "secret",
    "token",
)


def private_atomic_write(path: Path, content: bytes | str) -> None:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    if not isinstance(payload, bytes):
        raise TypeError("content must be bytes or text")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        os.chmod(path, 0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def mask_dashboard_text(value: str, *, private_roots: Sequence[Path]) -> str:
    masked = value
    roots = sorted(
        {str(Path(root).expanduser().resolve(strict=False)) for root in private_roots},
        key=len,
        reverse=True,
    )
    for root in roots:
        masked = masked.replace(root, "[private-root]")
    return masked


def _secret_key(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS)


def mask_dashboard_value(value: object, *, private_roots: Sequence[Path]) -> object:
    if isinstance(value, Mapping):
        return {
            key: (
                "[redacted]"
                if _secret_key(key)
                else mask_dashboard_value(item, private_roots=private_roots)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            mask_dashboard_value(item, private_roots=private_roots) for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            mask_dashboard_value(item, private_roots=private_roots) for item in value
        )
    if isinstance(value, Path):
        masked = mask_dashboard_text(str(value), private_roots=private_roots)
        return masked if masked.startswith("[private-root]") else "[redacted]"
    if isinstance(value, str):
        return mask_dashboard_text(value, private_roots=private_roots)
    return value


def require_opaque_identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty opaque identifier")
    decoded = unquote(value)
    if (
        decoded != value
        or any(character.isspace() for character in decoded)
        or "\x00" in decoded
        or "/" in decoded
        or "\\" in decoded
        or ".." in decoded
        or "://" in decoded
        or re.match(
            r"(?i)^(?:data|file|ftp|http|https|javascript):", decoded
        )
    ):
        raise ValueError(f"{name} must be an opaque identifier")
    return value


def issue_session_token() -> str:
    return secrets.token_urlsafe(32)


def issue_csrf_token(session_token: str) -> str:
    token = session_token.encode("utf-8")
    digest = hmac.new(token, b"devharness-dashboard-csrf-v1", hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _loopback_host(host: str) -> bool:
    if not isinstance(host, str) or not host or "@" in host:
        return False
    if host == "::1":
        hostname = host
    else:
        try:
            hostname = urlsplit(f"//{host}").hostname
        except ValueError:
            return False
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname or "").is_loopback
    except ValueError:
        return False


def _matches(value: str | None, expected: str) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and bool(expected)
        and hmac.compare_digest(value, expected)
    )


def validate_request_security(
    *,
    host: str,
    token: str,
    expected_token: str,
    method: str,
    origin: str | None,
    expected_origin: str,
    csrf_token: str | None,
    expected_csrf_token: str,
) -> None:
    if not _loopback_host(host):
        raise RequestSecurityError("request Host must be loopback")
    if not _matches(token, expected_token):
        raise RequestSecurityError("session token is invalid")
    if method == "GET":
        return
    if method != "POST":
        raise RequestSecurityError("request method is not allowed")
    if not _matches(origin, expected_origin):
        raise RequestSecurityError("request Origin is invalid")
    if not _matches(csrf_token, expected_csrf_token):
        raise RequestSecurityError("CSRF token is invalid")

"""Issue 5 acceptance fixtures: same-origin static serving and the shipped UI assets."""
import http.client
import json
import re
import unittest
from unittest.mock import patch

from devharness.catalog import Catalog
from devharness.evidence import EvidenceStore
from devharness.lifecycle.store import LifecycleStore
import tests.test_dashboard_api as api

WEB_FILES = ("index.html", "app.js", "styles.css")


def assets():
    """Read the shipped assets the way the server must: through the package, not a path."""
    from importlib import resources
    root = resources.files("devharness.dashboard") / "web"
    return {name: (root / name).read_text(encoding="utf-8") for name in WEB_FILES}


class StaticServingTests(api.DashboardHarness):
    """F11 — the app opens from the same origin without exposing anything else."""

    def test_f11_the_three_assets_are_served_with_their_own_types(self):
        self.snapshot("web-assets")
        server = self.serve()
        client = api.Client(server.address)  # no session yet: the login screen must load
        expected = {
            "/": ("text/html", "<!doctype html", "index.html"),
            "/app.js": ("text/javascript", None, "app.js"),
            "/styles.css": ("text/css", None, "styles.css"),
        }
        shipped = assets()
        for path, (mime, prefix, name) in expected.items():
            response = client.send("GET", path)
            self.assertEqual(response.status, 200, path)
            self.assertTrue(response.headers["Content-Type"].startswith(mime),
                            f"{path}: {response.headers['Content-Type']}")
            self.assertIn("charset=utf-8", response.headers["Content-Type"].lower())
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            body = response.body.decode("utf-8")
            self.assertEqual(body, shipped[name], f"{path} must serve the shipped asset")
            if prefix:
                self.assertTrue(body.lower().lstrip().startswith(prefix))

    def test_f11_the_document_gets_its_own_csp_and_the_api_keeps_the_strict_one(self):
        item = self.snapshot("web-csp")
        server = self.serve()
        client = self.client(server)
        document = client.send("GET", "/").headers["Content-Security-Policy"]
        for directive in ("default-src 'none'", "script-src 'self'", "style-src 'self'",
                          "connect-src 'self'", "base-uri 'none'", "frame-ancestors 'none'"):
            self.assertIn(directive, document, directive)
        self.assertNotIn("unsafe-eval", document)
        self.assertNotIn("unsafe-inline", document)
        self.assertNotIn("*", document)

        key = self.key_of(item)
        for path in ("/reviews", "/snapshots/" + key):
            api_csp = client.get(path).headers["Content-Security-Policy"]
            self.assertEqual(api_csp, "default-src 'none'",
                             "the API keeps its own strict policy")

    def test_f11_nothing_outside_the_allowlist_is_reachable(self):
        self.snapshot("web-allowlist")
        server = self.serve()
        client = self.client(server)
        root = str(self.fixture.paths.root)
        for path in ("/../pyproject.toml", "/web/app.js", "/index.html",
                     "/%2e%2e/%2e%2e/etc/passwd", "/catalog.sqlite3",
                     "/app.js/../../catalog.sqlite3", "/favicon.ico", "/robots.txt",
                     "/" + root.lstrip("/"), "/web", "/app.js.map"):
            response = client.send("GET", path)
            self.assertEqual(response.status, 404, path)
            self.assertEqual(response.headers["Content-Type"], "application/json", path)
            self.assertEqual(response.code, "NOT_FOUND", path)
            self.assertNotIn(b"sqlite", response.body.lower(), path)
            self.assertNotIn(root.encode(), response.body, path)

    def test_f11_an_api_error_never_becomes_an_html_page(self):
        item = self.snapshot("web-api-error")
        server = self.serve()
        key = self.key_of(item)
        anonymous = api.Client(server.address)
        unauthorised = anonymous.get("/reviews")
        self.assertEqual(unauthorised.status, 401)
        self.assertEqual(unauthorised.headers["Content-Type"], "application/json")

        client = self.client(server)
        missing = client.get("/snapshots/" + "0" * 64)
        self.assertEqual(missing.status, 404)
        self.assertEqual(missing.headers["Content-Type"], "application/json")
        for response in (unauthorised, missing):
            self.assertNotIn(b"<!doctype", response.body.lower())
            self.assertNotIn(b"<html", response.body.lower())
        self.assertEqual(client.get("/snapshots/" + key).status, 200)

    def test_f11_static_paths_still_honour_host_and_origin(self):
        self.snapshot("web-origin")
        server = self.serve()
        client = self.client(server)
        for kwargs in ({"host": "evil.example:8080"}, {"origin": "http://evil.example"}):
            response = client.send("GET", "/", **kwargs)
            self.assertEqual(response.status, 403, kwargs)
            self.assertEqual(response.headers["Content-Type"], "application/json")
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_f11_serving_the_app_writes_nothing_to_the_sources(self):
        self.snapshot("web-readonly")
        server = self.serve()
        client = self.client(server)
        blocked = []

        def deny(name):
            def refuse(*_a, **_k):
                blocked.append(name)
                raise AssertionError("serving assets must not call " + name)
            return refuse

        for owner, name in ((LifecycleStore, "append"), (LifecycleStore, "activate"),
                            (EvidenceStore, "put"), (EvidenceStore, "purge")):
            started = patch.object(owner, name, deny(name))
            started.start()
            self.addCleanup(started.stop)
        before = self.builder.inventory()
        for path in ("/", "/app.js", "/styles.css"):
            self.assertEqual(client.send("GET", path).status, 200, path)
        self.assertEqual(blocked, [])
        self.assertEqual(before, self.builder.inventory())


class ShippedAssetTests(unittest.TestCase):
    """The assets themselves must satisfy the contracts the server advertises."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.files = assets()
        except (ModuleNotFoundError, FileNotFoundError, AttributeError):
            cls.files = None

    def setUp(self):
        self.assertIsNotNone(self.files, "Dashboard web assets are not implemented")

    def test_the_document_carries_no_inline_script_or_style(self):
        html = self.files["index.html"]
        self.assertNotRegex(html, r"<script(?![^>]*\ssrc=)[^>]*>\s*\S")
        self.assertNotRegex(html, r"<style[^>]*>\s*\S")
        self.assertNotRegex(html, r"\son[a-z]+\s*=")
        self.assertIn('<script src="app.js"', html)
        self.assertIn('href="styles.css"', html)

    def test_no_asset_reaches_an_external_origin(self):
        """The XML namespace for inline SVG is a name, not a fetch; nothing else is absolute."""
        allowed = {"http://www.w3.org/2000/svg"}
        for name, text in self.files.items():
            found = set(re.findall(r"https?://[^\s\"'()]+", text)) - allowed
            self.assertEqual(found, set(), f"{name} reaches an external origin: {found}")
            self.assertNotIn("fonts.googleapis", text, name)
        # and nothing may be loaded from anywhere but this origin
        for attribute in re.findall(r'(?:src|href)="([^"]*)"', self.files["index.html"]):
            self.assertFalse(attribute.startswith(("http", "//")), attribute)

    def test_untrusted_text_never_reaches_innerhtml_or_eval(self):
        js = self.files["app.js"]
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML",
                          "document.write", "eval(", "new Function("):
            self.assertNotIn(forbidden, js, forbidden)
        self.assertIn("textContent", js)

    def test_the_token_is_never_persisted_or_put_in_the_url(self):
        js = self.files["app.js"]
        for forbidden in ("localStorage", "sessionStorage", "document.cookie",
                          "console.log", "token=" ):
            self.assertNotIn(forbidden, js, forbidden)

    def test_the_client_speaks_only_the_published_api_routes(self):
        js = self.files["app.js"]
        self.assertIn("/api/dashboard/v1", js)
        for route in ("/reviews", "/snapshots/", "/presentation", "/presentation/ensure",
                      "/content", "/session"):
            self.assertIn(route, js, route)
        self.assertIn("X-OwnHands-CSRF", js)
        # Generation is only ever asked for with the two real view intents.
        self.assertIn("list_visible", js)
        self.assertIn("detail", js)
        for banned in ("drawer\"", "'drawer'", "refresh\""):
            self.assertNotIn("view_intent: " + banned, js)

    def test_no_write_or_re_run_affordance_ships_in_the_ui(self):
        text = self.files["index.html"] + self.files["app.js"]
        for banned in ("승인", "재실행", "다시 실행", "재검증", "머지", "병합",
                       "재생성", "다시 생성", "요약 생성하기"):
            self.assertNotIn(banned, text, banned)

    def test_the_reconciled_contrast_tokens_are_the_ones_shipped(self):
        css = self.files["styles.css"]
        for token in ("#4f5662", "#7a5412", "#27693f", "#5a5478"):
            self.assertIn(token, css, token)
        body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        for failing in ("#747b86", "#9a9fa8"):
            for hit in re.finditer(r"color:\s*" + failing, body):
                self.fail(f"{failing} must not carry text: {body[max(0,hit.start()-60):hit.end()]}")

    def test_every_client_name_is_declared_before_it_is_assigned(self):
        """Strict mode turns an undeclared assignment into a throw that blanks the
        screen, and a browser run is the only other place it shows up."""
        js = self.files["app.js"]
        self.assertIn('"use strict"', js)
        declared = set(re.findall(r"\b(?:var|let|const|function)\s+([A-Za-z_$][\w$]*)", js))
        declared |= set(re.findall(r"function\s*\(([^)]*)\)", js).__class__(
            part.strip() for group in re.findall(r"function\s*\(([^)]*)\)", js)
            for part in group.split(",") if part.strip()))
        declared |= {"window", "document", "location", "console", "fetch", "Date",
                     "Set", "Map", "Object", "Array", "String", "JSON", "Math"}
        assigned = set(re.findall(r"^\s{0,4}([A-Za-z_$][\w$]*)\s*=[^=]", js, re.M))
        self.assertEqual(assigned - declared, set(),
                         "these are assigned without a declaration")

    def test_the_client_sets_no_inline_style_the_policy_would_block(self):
        """style-src 'self' blocks style attributes too, so every rule lives in the sheet."""
        self.assertNotIn('style: "', self.files["app.js"])
        self.assertNotIn('setAttribute("style"', self.files["app.js"])
        self.assertNotIn(".style.", self.files["app.js"])
        self.assertNotRegex(self.files["index.html"], r'\sstyle="')

    def test_korean_wraps_by_word_and_the_layout_collapses(self):
        css = self.files["styles.css"]
        self.assertIn("word-break", css)
        self.assertIn("keep-all", css)
        self.assertIn("@media", css)
        self.assertRegex(css, r"max-width:\s*899px")


if __name__ == "__main__":
    unittest.main()

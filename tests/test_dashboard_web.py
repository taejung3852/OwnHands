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


class LegacyClaimApiTests(api.DashboardHarness):
    """The data a legacy v1 Review gives the UI, so the client can stop inventing checks."""

    def test_f03_a_legacy_claim_carries_observations_with_evidence_links(self):
        item = self.builder.simple_snapshot("legacy-evidence", title="legacy 근거",
                                            status="verified", activate_inputs=True)
        server = self.serve()
        client = self.client(server)
        key = self.key_of(item)
        detail = client.get("/snapshots/" + key).json
        self.assertEqual(detail["source_contract_version"], 1)
        claim = detail["claims"][0]
        self.assertEqual(claim["checks"], [], "a v1 Review has no recorded checks")
        self.assertTrue(claim["observations"], "but it does carry its own observations")
        links = [link for observation in claim["observations"]
                 for link in observation["evidence_links"]]
        self.assertTrue(links, "and those observations reach real evidence")
        evidence = client.get("/snapshots/" + key + "/evidence/" + links[0]["evidence_key"])
        self.assertEqual(evidence.status, 200)


class ProblemRequirementApiTests(api.DashboardHarness):
    """A Problem that belongs to no criterion carries required=null, not false."""

    def test_f03_a_finding_without_a_criterion_has_no_requirement(self):
        builder = self.builder
        fixture = self.fixture
        observation = fixture.observe("fail")
        inputs = fixture.inputs()
        inputs["findings"] = [{"reason": "no_criterion_finding", "detail": "관련 조건 없음",
                               "observations": [observation]}]
        review = fixture.store.append("review", "review:null-required", fixture.scope,
                                      fixture.store.evaluate_review(fixture.scope, inputs))
        snapshot = builder.append_snapshot(review, "snapshot:null-required")
        server = self.serve()
        client = self.client(server)
        key = self.key_of({"snapshot": snapshot})
        problems = client.get("/snapshots/" + key).json["problems"]
        findings = [item for item in problems if item["kind"] == "finding"]
        self.assertTrue(findings, "the finding must reach the UI")
        self.assertIsNone(findings[0]["claim_id"])
        self.assertIsNone(findings[0]["required"],
                          "SDD: required is bool|null and null is not optional")


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

    def test_the_list_uses_the_search_and_cursor_contract(self):
        """PR #98 review: q and next_cursor were never wired to the list."""
        js = self.files["app.js"]
        query = js.split("function listQuery(")[1].split("\n}")[0]
        for param in ('"filter="', '"q="', '"cursor="'):
            self.assertIn(param, query, "the list request must carry " + param)
        self.assertIn("encodeURIComponent", query)
        screen = js.split("async function listScreen(")[1].split("\nfunction ")[0]
        self.assertIn("result.data.next_cursor", screen, "paging follows next_cursor")
        self.assertIn("list_token", screen, "pages of different lists are never spliced")
        self.assertIn("LIST_CHANGED", screen, "a changed list restarts from page one")
        # a search must never be the reason a summary gets generated
        self.assertIn("function searching(", js)
        predicate = js.split("function canEnsure(")[1].split("\n}")[0]
        self.assertIn("searching(", predicate)

    def test_a_card_whose_active_snapshot_differs_says_so(self):
        js = self.files["app.js"]
        self.assertIn("active_snapshot_key", js)
        self.assertIn("현재 적용 중인 보고서", js)

    def test_a_hidden_tab_keeps_its_polls_and_resumes_from_a_get(self):
        """PR #98 review: stopPolls cleared timers without remembering the poll."""
        js = self.files["app.js"]
        stop = js.split("function stopPolls(")[1].split("\n}")[0]
        self.assertIn("suspended.set", stop, "a paused poll must be remembered")
        resume = js.split("function resumePolls(")[1].split("\n}")[0]
        self.assertIn("refresh", resume, "resuming starts from a GET")

    def test_a_legacy_claim_shows_its_observations_and_evidence(self):
        """PR #98 review: checks=[] left the count at 0 and the drawer empty."""
        js = self.files["app.js"]
        self.assertIn("function claimObservations(", js)
        self.assertIn("source_contract_version", js)
        self.assertIn("상세 검사 항목", js)
        # the count must fall back to the claim's own observations
        counter = js.split("function evidenceKeysOf(")[1].split("\n}")[0]
        self.assertIn("claimObservations(", counter)
        fallback = js.split("function claimObservations(")[1].split("\n}")[0]
        self.assertIn("claim.observations", fallback)

    def test_a_finished_summary_repaints_its_card_not_the_whole_list(self):
        """A full render() re-reads page one, dropping the pages the reader asked
        for and clearing every other paused poll."""
        js = self.files["app.js"]
        observer = js.split("function viewportObserver(")[1].split("\n}")[0]
        self.assertNotIn("render()", observer,
                         "a finished summary must not re-render the whole screen")
        self.assertIn("replaceChild", js, "the finished card is swapped in place")
        screen = js.split("async function listScreen(")[1].split("\nfunction ")[0]
        self.assertNotIn("render(); });", screen,
                         "the no-observer fallback must repaint its cards too")

    def test_a_problem_tied_to_no_criterion_is_not_called_optional(self):
        """SDD: Problem.required is bool|null. null is not `선택`."""
        js = self.files["app.js"]
        self.assertNotRegex(js, r'problem\.required \? "필수" : "선택"')
        self.assertIn("조건 미지정", js)

    def test_the_legacy_blurb_is_decided_before_it_is_printed(self):
        """`var` hoisting made this read undefined, so the blurb never rendered."""
        body = self.files["app.js"].split("function evidenceList(")[1].split("\n}")[0]
        self.assertLess(body.index("var legacy ="), body.index("text: legacy"),
                        "legacy must be declared before the paragraph reads it")

    def test_the_remaining_problems_can_actually_be_opened(self):
        """PR #98 review: the remainder was a sentence, not an affordance."""
        js = self.files["app.js"]
        block = js.split("function attentionCard(")[1].split("\nfunction ")[0]
        self.assertIn("aria-expanded", block)
        # a flex row ignores the UA [hidden] rule, so the sheet has to force it
        self.assertRegex(self.files["styles.css"], r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important")
        self.assertIn("추가", block)
        self.assertNotRegex(block, r'text: "추가 " \+ [^;]*건이 더 있습니다')

    def test_a_settled_failure_is_retried_when_the_cooldown_has_passed(self):
        """Review finding: only `absent` triggered ensure, so the server's second
        attempt was unreachable for the life of the session."""
        js = self.files["app.js"]
        self.assertIn("function ensurable(", js)
        # the status literal survives only inside the predicate, and no trigger
        # decides for itself: the two list paths go through watchCard, and the
        # detail path tests the predicate directly.
        self.assertEqual(js.count('status === "absent"'), 1)
        triggers = [line for line in js.splitlines()
                    if re.search(r"[^a-zA-Z]ensure\(", line) and "function ensure(" not in line]
        self.assertEqual(len(triggers), 3, triggers)
        self.assertIn("if (!ensurable(card.presentation)) return;",
                      js.split("function watchCard(")[1].split("\n}")[0])
        predicate = js.split("function ensurable(")[1].split("\n}")[0]
        self.assertIn('"failed"', predicate)
        self.assertIn("retry_after", predicate)

    def test_polls_are_tracked_per_key_so_all_of_them_can_be_cancelled(self):
        """Review finding: a single timer handle left earlier polls uncancellable."""
        js = self.files["app.js"]
        self.assertNotIn("var pollTimer = null", js)
        self.assertIn("polls", js)
        self.assertIn("function stopPolls(", js)

    def test_returning_to_the_tab_does_not_rebuild_the_screen(self):
        """Review finding: an unconditional re-render on focus reset scroll."""
        js = self.files["app.js"]
        handler = js.split('addEventListener("visibilitychange"')[1].split("});")[0]
        self.assertNotIn("render()", handler,
                         "focus must resume a suspended poll, not repaint the page")
        self.assertIn("resumePolls", handler)

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

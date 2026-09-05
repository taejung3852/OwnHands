from __future__ import annotations

import re
import unittest

from devharness.dashboard_assets import dashboard_css, dashboard_script
from devharness.dashboard_render import render_document, render_task_review
from tests.test_dashboard_render import TASK, review_view


class DashboardAccessibilityTests(unittest.TestCase):
    def test_native_page_structure_has_labels_ordered_headings_and_no_positive_tabindex(self) -> None:
        document = render_document(
            title="Task Review",
            task_id=TASK,
            main=render_task_review(review_view(), csrf_token="csrf"),
            status="fresh",
            nonce="nonce",
        ).decode("utf-8")

        self.assertNotRegex(document, r'tabindex="[1-9][0-9]*"')
        self.assertIn("<details", document)
        self.assertIn("<summary", document)
        self.assertIn('<label for="decision-choice"', document)
        self.assertIn('role="region" aria-label="검증 표" tabindex="0"', document)
        headings = [(int(level), match.start()) for match in re.finditer(r"<h([1-6])(?:\s|>)", document) for level in (match.group(1),)]
        self.assertEqual(1, headings[0][0])
        self.assertTrue(all(next_level <= level + 1 for (level, _), (next_level, _) in zip(headings, headings[1:])))

    def test_statuses_pair_symbols_with_text_and_brand_focus_semantics_are_separate(self) -> None:
        page = render_task_review(review_view(), csrf_token="csrf")
        css = dashboard_css()

        self.assertRegex(page, r'class="status-symbol"[^>]*aria-hidden="true"[^>]*>[^<]+</span>')
        self.assertIn("Passed", page)
        self.assertIn("Unobserved", page)
        self.assertIn("--brand:", css)
        self.assertIn("--focus:", css)
        self.assertIn("--status-pass:", css)
        brand = re.search(r"--brand:\s*([^;]+)", css).group(1)
        focus = re.search(r"--focus:\s*([^;]+)", css).group(1)
        passed = re.search(r"--status-pass:\s*([^;]+)", css).group(1)
        self.assertEqual(3, len({brand, focus, passed}))

    def test_warm_paper_ledger_indigo_assets_cover_themes_motion_and_target_widths(self) -> None:
        css = dashboard_css()
        script = dashboard_script()

        for token in ("--paper:", "--ledger-indigo:", "color-scheme: light dark", '[data-theme="dark"]'):
            self.assertIn(token, css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        for width in ("320px", "390px", "1440px"):
            self.assertIn(width, css)
        self.assertNotIn("@import", css.casefold())
        self.assertNotRegex(css + script, r"https?://|url\s*\(")
        self.assertNotIn("fetch(", script)
        self.assertNotIn("innerHTML", script)


if __name__ == "__main__":
    unittest.main()

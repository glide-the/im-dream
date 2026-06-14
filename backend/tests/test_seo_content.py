#!/usr/bin/env python3
# [Input] Consume backend seo_content helpers.
# [Output] Verify public SEO crawler files use configured base URLs and private path exclusions.
# [Pos] test node in backend/tests
# [Sync] 2026-06-14: created for Codex SEO robots/sitemap/llms content generators.
# [Sync] 2026-06-14: cover split frontend app URL and backend API origin in llms.txt.
"""Unit tests for public SEO content generation."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from seo_content import (  # noqa: E402
    build_llms_txt,
    build_public_origin_url,
    build_public_url,
    build_robots_txt,
    build_sitemap_xml,
    normalize_public_base_url,
)


class TestSeoContent(unittest.TestCase):
    def test_url_helpers_normalize_public_app_base(self):
        base = "https://ink.example.com/ink-and-memory"

        self.assertEqual(
            normalize_public_base_url(base),
            "https://ink.example.com/ink-and-memory/",
        )
        self.assertEqual(
            build_public_url(base, "sitemap.xml"),
            "https://ink.example.com/ink-and-memory/sitemap.xml",
        )
        self.assertEqual(build_public_origin_url(base), "https://ink.example.com/")

    def test_robots_allows_search_crawlers_and_disallows_private_paths(self):
        robots = build_robots_txt("https://ink.example.com/ink-and-memory/")

        self.assertIn("User-agent: GPTBot", robots)
        self.assertIn("User-agent: OAI-SearchBot", robots)
        self.assertIn("User-agent: PerplexityBot", robots)
        self.assertIn("Disallow: /api/", robots)
        self.assertIn("Disallow: /ink-and-memory/api/", robots)
        self.assertIn("Sitemap: https://ink.example.com/sitemap.xml", robots)

    def test_sitemap_contains_public_app_url_only(self):
        sitemap = build_sitemap_xml(
            "https://ink.example.com/ink-and-memory/",
            last_modified=date(2026, 6, 14),
        )

        self.assertIn("<loc>https://ink.example.com/ink-and-memory/</loc>", sitemap)
        self.assertIn("<lastmod>2026-06-14</lastmod>", sitemap)
        self.assertNotIn("/api/", sitemap)
        self.assertNotIn("/polycli/", sitemap)

    def test_llms_txt_describes_frontend_and_private_api_boundary(self):
        llms = build_llms_txt(
            "https://ink-frontend.suoxya.com/ink-and-memory/",
            "https://ink-backend.suoxya.com",
        )

        self.assertIn("# Ink & Memory", llms)
        self.assertIn("https://ink-frontend.suoxya.com/ink-and-memory/", llms)
        self.assertIn("https://ink-backend.suoxya.com/", llms)
        self.assertIn("https://ink-backend.suoxya.com/api/health", llms)
        self.assertIn("Authenticated application APIs under /api/", llms)


if __name__ == "__main__":
    unittest.main()

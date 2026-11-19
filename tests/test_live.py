"""Live tests — hit the real www.ndr.de RSS feeds and article pages.
Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set NDR_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from ndr_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("NDR_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="NDR_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_headlines_live(self):
        out = json.loads(srv.ndr_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["link"] for i in out["items"]))
        print(f"\nLIVE headlines: {out['count']} items, first: {out['items'][0]['title']}")

    def test_by_region_live(self):
        out = json.loads(srv.ndr_news_by_region("hamburg", limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["region"], "hamburg")
        self.assertGreaterEqual(out["count"], 1)
        print(f"\nLIVE Hamburg: {out['total_results']} items")

    def test_by_section_live(self):
        out = json.loads(srv.ndr_news_by_section("kultur", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(
            "kultur" in (i["section"] or "").casefold()
            for i in out["items"]
        ))
        print(f"\nLIVE kultur: {out['total_results']} items")

    def test_search_live(self):
        out = json.loads(srv.ndr_search_news("Hamburg", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(
            "hamburg" in (i["title"] + i["description"]).casefold()
            for i in out["items"]
        ))
        print(f"\nLIVE search 'Hamburg': {out['total_results']} hits")

    def test_get_article_news_live(self):
        # A nachrichten article from the current feed: JSON-LD body expected.
        feed = json.loads(srv.ndr_headlines(limit=30))
        news = [i for i in feed["items"]
                if i["section"] == "nachrichten" and i["link"].endswith(".html")]
        self.assertGreater(len(news), 0)
        out = json.loads(srv.ndr_get_article(news[0]["link"]))
        self.assertNotIn("error", out)
        self.assertFalse(out["paywalled"])
        self.assertEqual(out["kind"], "article")
        self.assertGreater(out["word_count"], 100)
        print(f"\nLIVE article: {out['word_count']} words, {out['title'][:60]}")

    def test_get_article_kultur_live(self):
        # A kultur article: SSR fallback body expected (no JSON-LD body).
        feed = json.loads(srv.ndr_headlines(limit=100))
        kultur = [i for i in feed["items"] if i["section"] == "kultur"]
        if not kultur:
            self.skipTest("no kultur item in the current feed")
        out = json.loads(srv.ndr_get_article(kultur[0]["link"]))
        self.assertNotIn("error", out)
        self.assertEqual(out["kind"], "article")
        self.assertGreater(out["word_count"], 100)
        print(f"\nLIVE kultur article: {out['word_count']} words, {out['title'][:60]}")

    def test_health_live(self):
        out = json.loads(srv.ndr_health())
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)


if __name__ == "__main__":
    unittest.main()

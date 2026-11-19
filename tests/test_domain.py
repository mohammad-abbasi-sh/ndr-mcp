"""Offline tests — parse the real captured www.ndr.de RSS feeds and
three real article pages (a nachrichten NewsArticle with JSON-LD
body, a kultur Article with SSR-only body, a fernsehen VideoObject
page), no network."""
import json
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from ndr_mcp import domain as dom
from ndr_mcp import http as http_mod
from ndr_mcp import server as srv

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"

NEWS_URL = (
    "https://www.ndr.de/nachrichten/niedersachsen/"
    "ndr-wahlumfrage-spd-liegt-deutlich-vorn-cdu-und-afd-gleichauf,"
    "niedersachsentrend-112.html"
)
KULTUR_URL = (
    "https://www.ndr.de/kultur/film/"
    "die-friesenjunkies-emil-und-oskar-beltons-neuester-impro-film,"
    "friesenjunkies-108.html"
)
VIDEO_URL = (
    "https://www.ndr.de/fernsehen/sendungen/hallo_niedersachsen/"
    "cdu-fordert-entlassung-von-justizministerin-wahlmann-spd,"
    "hallonds-11728.html"
)


def _rss(name):
    return dom.parse_rss((FIX / name).read_text(encoding="utf-8"))


class TestHeadlinesFixture(unittest.TestCase):
    def test_headlines_shape(self):
        out = _rss("headlines.xml")
        self.assertEqual(
            out["feed_title"],
            "NDR.de - Das Beste am Norden - Radio - Fernsehen - Nachrichten",
        )
        self.assertEqual(out["count"], 106)
        self.assertEqual(len(out["items"]), 106)

    def test_headlines_first_item(self):
        item = _rss("headlines.xml")["items"][0]
        self.assertEqual(
            item["title"],
            "NiedersachsenTrend: SPD liegt vorn, CDU verliert",
        )
        self.assertEqual(item["link"], NEWS_URL)
        self.assertEqual(item["published"], "2026-11-19T05:30:00+00:00")
        self.assertEqual(item["section"], "nachrichten")
        self.assertEqual(item["region"], "niedersachsen")
        self.assertTrue(item["description"].startswith(
            "Würde am Sonntag in Niedersachsen gewählt werden"))

    def test_headlines_all_items_complete(self):
        items = _rss("headlines.xml")["items"]
        self.assertTrue(all(i["title"] and i["link"] and i["published"] for i in items))
        self.assertTrue(all(
            i["link"].startswith("https://www.ndr.de/")
            or i["link"].startswith("https://www.ardmediathek.de/")
            for i in items))

    def test_sections(self):
        items = _rss("headlines.xml")["items"]
        sections = dom.list_sections(items)
        self.assertEqual(sections[0], {"section": "kultur", "count": 26})
        self.assertEqual(sections[1], {"section": "nachrichten", "count": 22})
        self.assertEqual(sections[2], {"section": "fernsehen", "count": 14})
        self.assertEqual(sections[3], {"section": "mediathek", "count": 14})
        self.assertEqual(sections[-1], {"section": "ndrfragt", "count": 1})

    def test_mediathek_items_are_video_links(self):
        items = _rss("headlines.xml")["items"]
        media = [i for i in items if i["section"] == "mediathek"]
        self.assertEqual(len(media), 14)
        self.assertTrue(all(
            i["link"].startswith("https://www.ardmediathek.de/")
            for i in media))
        self.assertTrue(all(i["region"] is None for i in media))

    def test_region_items(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(len(dom.filter_by_region(items, "hamburg")), 4)
        self.assertEqual(
            len(dom.filter_by_region(items, "schleswig-holstein")), 5)
        self.assertEqual(
            len(dom.filter_by_region(items, "mecklenburg-vorpommern")), 2)


class TestRegionFixture(unittest.TestCase):
    def test_region_feed_shape(self):
        out = _rss("region-niedersachsen.xml")
        self.assertEqual(out["feed_title"], "Nachrichten aus Niedersachsen")
        self.assertEqual(out["count"], 69)
        # The regional feed is "news for Niedersachsen", not strictly
        # "news from Niedersachsen": it also carries fernsehen/mediathek
        # items and the odd other-region item (verified live: 1
        # schleswig-holstein item, 14 fernsehen, 11 mediathek).
        self.assertEqual(
            len(dom.filter_by_region(out["items"], "niedersachsen")), 35)
        self.assertTrue(all(
            i["title"] and i["link"] for i in out["items"]))


class TestArticleFixtures(unittest.TestCase):
    def test_news_article_json_ld_body(self):
        html_text = (FIX / "article-news.html").read_text(encoding="utf-8")
        out = dom.parse_article(html_text)
        self.assertEqual(out["kind"], "article")
        self.assertEqual(
            out["title"],
            "NiedersachsenTrend: SPD liegt vorn, CDU verliert",
        )
        self.assertEqual(out["author"], "Torben Hildebrandt")
        self.assertEqual(out["published"], "2026-11-19T06:30:00.000+01:00")
        self.assertEqual(len(out["body"]), 4884)
        self.assertTrue(out["body"].startswith(
            "SPD und Grüne legen zu, die CDU rutscht ab."))
        self.assertFalse(out["teaser_only"])
        self.assertFalse(out["paywalled"])
        self.assertEqual(out["word_count"], 705)

    def test_kultur_article_ssr_fallback(self):
        # Kultur pages carry no JSON-LD articleBody: the body comes
        # from the server-rendered <article> paragraphs.
        html_text = (FIX / "article-kultur.html").read_text(encoding="utf-8")
        out = dom.parse_article(html_text)
        self.assertEqual(out["kind"], "article")
        self.assertEqual(
            out["title"],
            'Entzugsklinik auf Sylt: So entstand die Impro-Serie '
            '"Friesenjunkies"',
        )
        self.assertEqual(len(out["body"]), 3500)
        self.assertTrue(out["body"].startswith(
            "Ihre Karriere begann schon viel früher: mit einer "
            "Gastrolle bei der NDR Kinderserie"))
        self.assertFalse(out["teaser_only"])
        self.assertFalse(out["paywalled"])
        self.assertEqual(out["word_count"], 513)
        # header paragraph (title + Stand) and byline must be filtered
        self.assertNotIn("Stand:", out["body"])

    def test_video_page_returns_video_kind(self):
        html_text = (FIX / "article-video.html").read_text(encoding="utf-8")
        out = dom.parse_article(html_text)
        self.assertEqual(out["kind"], "video")
        self.assertEqual(
            out["title"],
            "CDU fordert Entlassung von Justizministerin Wahlmann (SPD)",
        )
        self.assertEqual(len(out["body"]), 132)
        self.assertTrue(out["teaser_only"])
        self.assertFalse(out["paywalled"])
        self.assertEqual(out["duration"], "PT2M13S")
        self.assertTrue(out["video_url"].startswith(
            "https://ndr-progressive.ard-mcdn.de/"))

    def test_article_without_any_body_raises(self):
        with self.assertRaises(ValueError):
            dom.parse_article("<html><body>no ld+json here</body></html>")


class TestParseErrors(unittest.TestCase):
    def test_malformed_xml(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("<rss><channel><item>oops")

    def test_non_rss_document(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("<html><head><title>404</title></head></html>")

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("")


class TestValidation(unittest.TestCase):
    def test_limit_bounds(self):
        self.assertEqual(dom.validate_limit(1), 1)
        self.assertEqual(dom.validate_limit(150), 150)
        with self.assertRaises(ValueError):
            dom.validate_limit(0)
        with self.assertRaises(ValueError):
            dom.validate_limit(151)

    def test_region_validation(self):
        self.assertEqual(dom.validate_region("Hamburg"), "hamburg")
        self.assertEqual(
            dom.validate_region("Mecklenburg-Vorpommern"),
            "mecklenburg-vorpommern")
        with self.assertRaises(ValueError):
            dom.validate_region("berlin")
        with self.assertRaises(ValueError):
            dom.validate_region("")


class TestSearchAndFilters(unittest.TestCase):
    def test_search_case_insensitive(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(len(dom.search_items(items, "SPD")), 2)
        self.assertEqual(len(dom.search_items(items, "spd")), 2)
        self.assertEqual(len(dom.search_items(items, "Hamburg")), 12)

    def test_search_no_hits(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(dom.search_items(items, "zzzzqqq"), [])

    def test_search_empty_raises(self):
        with self.assertRaises(ValueError):
            dom.search_items([], "  ")

    def test_filter_by_section(self):
        items = _rss("headlines.xml")["items"]
        self.assertEqual(len(dom.filter_by_section(items, "kultur")), 26)
        self.assertEqual(len(dom.filter_by_section(items, "Kultur")), 26)
        self.assertEqual(len(dom.filter_by_section(items, "mediathek")), 14)
        self.assertEqual(dom.filter_by_section(items, "zzzz"), [])

    def test_filter_by_section_empty_raises(self):
        with self.assertRaises(ValueError):
            dom.filter_by_section([], "  ")

    def test_dedupe_sort(self):
        items = _rss("headlines.xml")["items"]
        merged = dom.dedupe_sort(items + items[:5])
        links = [i["link"] for i in merged]
        self.assertEqual(len(links), len(set(links)))
        self.assertEqual(len(merged), 106)
        dates = [i["published"] for i in merged]
        self.assertEqual(dates, sorted(dates, reverse=True))


class TestHttpGuards(unittest.TestCase):
    def test_fetch_feed_rejects_non_feed_path(self):
        with self.assertRaises(http_mod.NdrError):
            http_mod.fetch_feed("https://www.ndr.de/nachrichten/")

    def test_fetch_feed_rejects_other_host(self):
        with self.assertRaises(http_mod.NdrError):
            http_mod.fetch_feed("https://example.com/index~rss2.xml")

    def test_fetch_article_rejects_non_html_url(self):
        with self.assertRaises(http_mod.NdrError):
            http_mod.fetch_article("https://www.ndr.de/nachrichten/")

    def test_fetch_article_rejects_mediathek_host(self):
        with self.assertRaises(http_mod.NdrError):
            http_mod.fetch_article(
                "https://www.ardmediathek.de/video/Y3JpZDovL25kci5kZS8x")


class TestServerOffline(unittest.TestCase):
    """Tool functions with the HTTP layer mocked to the fixtures."""

    def test_headlines_tool(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.ndr_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["total_results"], 106)
        self.assertEqual(out["source"], "www.ndr.de")
        self.assertIn("fetched_at", out)

    def test_headlines_tool_limit_error(self):
        out = json.loads(srv.ndr_headlines(limit=0))
        self.assertIn("error", out)

    def test_by_region_tool(self):
        xml = (FIX / "region-niedersachsen.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml) as m:
            out = json.loads(srv.ndr_news_by_region("niedersachsen", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["region"], "niedersachsen")
        self.assertEqual(out["total_results"], 69)
        self.assertEqual(out["count"], 2)
        self.assertIn("niedersachsen/index~rss2.xml", m.call_args[0][0])

    def test_by_region_tool_bad_region(self):
        out = json.loads(srv.ndr_news_by_region("berlin", limit=2))
        self.assertIn("error", out)

    def test_by_section_tool(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.ndr_news_by_section("kultur", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["section"], "kultur")
        self.assertEqual(out["total_results"], 26)
        self.assertEqual(out["count"], 2)

    def test_by_section_tool_empty(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.ndr_news_by_section("zzzz", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["total_results"], 0)

    def test_search_tool(self):
        xml = (FIX / "headlines.xml").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.ndr_search_news("SPD", limit=10))
        self.assertNotIn("error", out)
        self.assertEqual(out["query"], "SPD")
        self.assertEqual(out["total_results"], 2)

    def test_search_tool_empty_query(self):
        out = json.loads(srv.ndr_search_news("   "))
        self.assertIn("error", out)

    def test_get_article_news(self):
        html_text = (FIX / "article-news.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_article", return_value=html_text):
            out = json.loads(srv.ndr_get_article(NEWS_URL))
        self.assertNotIn("error", out)
        self.assertFalse(out["paywalled"])
        self.assertFalse(out["teaser_only"])
        self.assertEqual(out["kind"], "article")
        self.assertEqual(out["word_count"], 705)
        self.assertEqual(out["author"], "Torben Hildebrandt")

    def test_get_article_kultur_ssr(self):
        html_text = (FIX / "article-kultur.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_article", return_value=html_text):
            out = json.loads(srv.ndr_get_article(KULTUR_URL))
        self.assertNotIn("error", out)
        self.assertFalse(out["paywalled"])
        self.assertEqual(out["kind"], "article")
        self.assertEqual(out["word_count"], 513)

    def test_get_article_video(self):
        html_text = (FIX / "article-video.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_article", return_value=html_text):
            out = json.loads(srv.ndr_get_article(VIDEO_URL))
        self.assertNotIn("error", out)
        self.assertEqual(out["kind"], "video")
        self.assertTrue(out["teaser_only"])
        self.assertEqual(out["duration"], "PT2M13S")
        self.assertIn("Video page", out["note"])

    def test_get_article_empty_url(self):
        out = json.loads(srv.ndr_get_article("   "))
        self.assertIn("error", out)

    def test_get_article_non_article_url(self):
        out = json.loads(srv.ndr_get_article("https://www.ndr.de/nachrichten/"))
        self.assertIn("error", out)

    def test_health_tool(self):
        with mock.patch.object(srv._http, "health_check", return_value={"status": "ok", "http_status": 200, "url": dom.HEADLINES_FEED}):
            out = json.loads(srv.ndr_health())
        self.assertEqual(out["status"], "ok")


if __name__ == "__main__":
    unittest.main()

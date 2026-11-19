"""MCP server: unofficial read-only access to NDR (ndr.de) — the
Norddeutscher Rundfunk, public broadcaster for Hamburg, Lower Saxony,
Mecklenburg-Vorpommern and Schleswig-Holstein — via its official RSS
feeds (main + four regional feeds) and article pages (JSON-LD
articleBody, with a server-rendered <article> fallback).
No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for NDR (ndr.de) — the Norddeutscher
Rundfunk, public broadcaster for Hamburg, Lower Saxony,
Mecklenburg-Vorpommern and Schleswig-Holstein — via its official RSS
feeds (www.ndr.de/index~rss2.xml plus one feed per region, no key,
no login) and article pages, whose full text is read from the JSON-LD
articleBody (or, where a page carries none, from the server-rendered
<article> paragraphs). Top headlines, regional news for the four NDR
states, news by section (nachrichten, kultur, sport, ratgeber,
geschichte, fernsehen, …), keyword search, and full article text.
NOTE: the feed carries no author or category — section and region are
derived from each item's link path; some feed items link to ARD
Mediathek video pages (section "mediathek"), which live on another
host and are not fetched. Video article pages return kind="video"
with the description and the Mediathek URL. NDR is public
broadcasting: sampled pages are free (isAccessibleForFree=true); a
page that is not free returns paywalled=true with the teaser, never
fabricated text.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · \
https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "www.ndr.de"
_DISCLAIMER = "Unofficial read-only data from NDR's public RSS feeds and article pages; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("ndr-mcp", instructions=INSTRUCTIONS)


def _feed(url: str, limit: int) -> dict:
    """Fetch one NDR RSS feed and return its items, newest first, capped."""
    parsed = _dom.parse_rss(_http.fetch_feed(url))
    items = parsed["items"][:limit]
    return {
        "feed_title": parsed["feed_title"],
        "total_results": parsed["count"],
        "count": len(items),
        "items": items,
    }


@mcp.tool()
def ndr_headlines(limit: int = 10) -> str:
    """Top headlines from NDR (official RSS feed, ~106 items), newest first.
limit: 1..150 (default 10). Items carry title, link, teaser,
section (nachrichten, kultur, sport, ratgeber, geschichte,
fernsehen, mediathek, …), region (for /nachrichten/<region>/ links)
and publish time."""
    try:
        lim = _dom.validate_limit(limit)
        out = _feed(_dom.HEADLINES_FEED, lim)
    except (_http.NdrError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def ndr_news_by_region(region: str, limit: int = 10) -> str:
    """Newest NDR news from one of the four broadcast states, from its
own official regional RSS feed. region: "niedersachsen", "hamburg",
"mecklenburg-vorpommern" or "schleswig-holstein". limit: 1..150
(default 10)."""
    try:
        reg = _dom.validate_region(region)
        lim = _dom.validate_limit(limit)
        out = _feed(_dom.REGIONS[reg], lim)
        out["region"] = reg
    except (_http.NdrError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def ndr_news_by_section(section: str, limit: int = 10) -> str:
    """Newest NDR news of one section, in feed order. section: a
link-path section such as "nachrichten", "kultur", "sport",
"ratgeber", "geschichte", "fernsehen" or "mediathek"
(case-insensitive substring match; any section string works).
limit: 1..150 (default 10)."""
    try:
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.filter_by_section(parsed["items"], section)
        out = {
            "section": section.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.NdrError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def ndr_search_news(query: str, limit: int = 10) -> str:
    """Search NDR news by keyword (title + teaser) in the main RSS feed.
query: free text, e.g. "Hamburg" or "SPD". limit: 1..150
(default 10). Searches the ~106-item feed client-side, newest first,
de-duplicated by link."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.dedupe_sort(_dom.search_items(parsed["items"], query.strip()))
        out = {
            "query": query.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.NdrError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def ndr_get_article(url: str) -> str:
    """Full text of one NDR article page (JSON-LD articleBody, or the
server-rendered <article> paragraphs where a page carries no
articleBody). url: a www.ndr.de article URL ending in .html, e.g. from
ndr_headlines. Returns title, author, publish time, the body text and
its word count. Video pages return kind="video" with the description
and the ARD Mediathek URL instead of an article body. A page that is
not freely accessible returns paywalled=true with the teaser only.
Nothing is ever fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        url = url.strip()
        article = _dom.parse_article(_http.fetch_article(url))
        paywalled = article["paywalled"]
        note = ""
        if paywalled:
            note = (
                "This article is not freely accessible: only the teaser "
                "is available."
            )
        elif article["kind"] == "video":
            note = (
                "Video page: the description is the whole freely "
                "available text; watch the video at video_url."
            )
        elif article["teaser_only"]:
            note = (
                "Only the teaser is available for this item; the teaser "
                "is the whole freely available text."
            )
        out = {
            "url": url,
            "title": article["title"],
            "author": article["author"],
            "published": article["published"],
            "kind": article["kind"],
            "paywalled": paywalled,
            "teaser_only": article["teaser_only"],
            "word_count": article["word_count"],
            "body": article["body"],
            "description": article["description"],
            "video_url": article["video_url"],
            "duration": article["duration"],
            "note": note,
        }
    except (_http.NdrError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def ndr_health() -> str:
    """Check whether the NDR RSS feed is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())

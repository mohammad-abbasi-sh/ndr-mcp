"""Domain logic: shape ndr.de's official RSS feeds and article pages
into compact dicts (stdlib only).

Data source: the official NDR RSS feeds (no key, no login) —
main feed https://www.ndr.de/index~rss2.xml (106 items, fresh) plus
one feed per region (Niedersachsen, Hamburg, Mecklenburg-Vorpommern,
Schleswig-Holstein, 57-69 items each) — and article pages, whose full
text lives in the JSON-LD NewsArticle/Article block as "articleBody"
when present.

Honest limitations (verified live 2026-11-19):
- The feed carries no <category> and no author: section and region
  are derived from the item link path (e.g. /kultur/..., or
  /nachrichten/niedersachsen/...); 14 of 106 main-feed items link to
  ardmediathek.de video pages instead of ndr.de articles.
- Not every article page carries a JSON-LD articleBody: "nachrichten"
  NewsArticle pages do (4,887 chars sampled), "kultur" Article pages
  do NOT — for those the body is read from the server-rendered
  <article class="articlepage"> paragraphs instead (3,851 chars
  sampled), with the header/byline paragraphs filtered out.
- "fernsehen" video pages carry a VideoObject block (no articleBody):
  get_article returns kind="video" with the description, the ARD
  Mediathek URL and the duration — never fabricated text.
- NDR is public broadcasting: sampled pages all carry
  isAccessibleForFree=true. The flag is still honoured — a page with
  isAccessibleForFree=false returns paywalled=true with the teaser.
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

BASE = "https://www.ndr.de"
HEADLINES_FEED = f"{BASE}/index~rss2.xml"

# Regional news feeds — one per NDR broadcast state (verified 200,
# 57-69 items each, 2026-11-19).
REGIONS = {
    "niedersachsen": f"{BASE}/nachrichten/niedersachsen/index~rss2.xml",
    "hamburg": f"{BASE}/nachrichten/hamburg/index~rss2.xml",
    "mecklenburg-vorpommern": (
        f"{BASE}/nachrichten/mecklenburg-vorpommern/index~rss2.xml"
    ),
    "schleswig-holstein": (
        f"{BASE}/nachrichten/schleswig-holstein/index~rss2.xml"
    ),
}

# Sections seen in the live main feed (2026-11-19) — the feed is the
# authority; any other first-path-segment string works as a filter too.
# "mediathek" is the synthetic section for ardmediathek.de video links.
KNOWN_SECTIONS = [
    "nachrichten", "kultur", "fernsehen", "geschichte", "sport",
    "ratgeber", "ndrfragt", "mediathek",
]


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (main feed carries ~106 items)."""
    if not 1 <= limit <= 150:
        raise ValueError(f"limit out of range: {limit} (expected 1..150)")
    return limit


def validate_region(region: str) -> str:
    """Normalise a region name to one of the four regional feeds."""
    r = (region or "").strip().casefold()
    if r not in REGIONS:
        raise ValueError(
            f"unknown region: {region!r} (expected one of "
            f"{', '.join(sorted(REGIONS))})"
        )
    return r


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text).strip()


def _iso(date_text: str) -> str | None:
    if not date_text:
        return None
    try:
        dt = parsedate_to_datetime(date_text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _section_and_region(link: str) -> tuple[str, str | None]:
    """Section = first path segment of an ndr.de link; region = the
    second segment for /nachrichten/<region>/ links. ARD Mediathek
    video links get section "mediathek" and no region."""
    try:
        parsed = urlparse(link)
    except ValueError:
        return "", None
    host = (parsed.netloc or "").lower()
    if "ardmediathek.de" in host:
        return "mediathek", None
    if host not in ("www.ndr.de", "ndr.de"):
        return "", None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return "", None
    section = parts[0]
    region = None
    if section == "nachrichten" and len(parts) > 1:
        cand = parts[1].casefold()
        if cand in REGIONS:
            region = cand
    return section, region


def compact_item(item: ET.Element) -> dict:
    """One RSS <item>: title, link, teaser, section, region and
    publish time. The feed carries no author or category — section
    and region are derived from the link path (see _section_and_region)."""
    link = _text(item, "link")
    section, region = _section_and_region(link)
    return {
        "title": _text(item, "title"),
        "link": link,
        "description": _strip_tags(_text(item, "description")),
        "published": _iso(_text(item, "pubDate")),
        "section": section,
        "region": region,
    }


def parse_rss(xml_text: str) -> dict:
    """Parse an NDR RSS feed into {feed_title, count, items}.

    Raises ValueError on malformed XML or a non-RSS document (e.g. a
    404 error page saved as text).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid RSS XML: {e}") from e
    channel = root.find("channel")
    if channel is None:
        raise ValueError("unexpected RSS shape: no <channel> element")
    items = [compact_item(it) for it in channel.findall("item")]
    return {
        "feed_title": _text(channel, "title"),
        "count": len(items),
        "items": items,
    }


_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S | re.I,
)
_ARTICLE_RE = re.compile(r"<article[^>]*>(.*?)</article>", re.S | re.I)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
_OG_DESC_RE = re.compile(
    r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
    re.S | re.I,
)


def _author_name(raw) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    if isinstance(raw, list):
        names = [_author_name(a) for a in raw]
        return ", ".join(n for n in names if n)
    return ""


def _is_free(block: dict) -> bool:
    """isAccessibleForFree from a JSON-LD block; absent means free
    (NDR pages that carry the field at all set it explicitly)."""
    val = block.get("isAccessibleForFree")
    return True if val is None else bool(val)


def _ssr_body(html_text: str) -> str:
    """Body text from the server-rendered <article> paragraphs.

    Filters out the header paragraph (title + "Stand: ... Uhr") and
    the author byline ("von <name>"), which are metadata, not body.
    Raises ValueError when no usable body paragraphs are found.
    """
    match = _ARTICLE_RE.search(html_text)
    if not match:
        raise ValueError(
            "no article text found on this page (no JSON-LD articleBody "
            "and no <article> body) — the page may be JS-rendered or an "
            "error page"
        )
    paras: list[str] = []
    for raw in _P_RE.findall(match.group(1)):
        text = _strip_tags(raw)
        if not text:
            continue
        if "Stand:" in text and "Uhr" in text:
            continue  # header paragraph: title + Stand + author line
        if text.startswith("von ") and len(text) < 80:
            continue  # byline paragraph
        paras.append(text)
    body = "\n\n".join(paras).strip()
    if not body:
        raise ValueError(
            "no article text found on this page (the <article> body is "
            "empty after filtering)"
        )
    return body


def _page_title(html_text: str) -> str:
    match = _TITLE_RE.search(html_text)
    if not match:
        return ""
    title = _strip_tags(match.group(1))
    return re.sub(r"\s*\|\s*ndr\.de\s*$", "", title, flags=re.I)


def parse_article(html_text: str) -> dict:
    """Extract the article from an ndr.de page.

    Prefers the JSON-LD NewsArticle/Article "articleBody". Falls back
    to the server-rendered <article> paragraphs (kultur pages carry
    no articleBody). Video pages (VideoObject, no articleBody) return
    kind="video" with the description as the body plus the Mediathek
    URL and duration. Returns {title, description, body, author,
    published, word_count, teaser_only, paywalled, kind, video_url,
    duration}. Raises ValueError when no usable text is found.
    """
    blocks: list[dict] = []
    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            blocks.append(data)

    for block in blocks:
        body = (block.get("articleBody") or "").strip()
        if not body:
            continue
        description = _strip_tags(str(block.get("description") or ""))
        return {
            "title": _strip_tags(str(block.get("headline") or "")) or _page_title(html_text),
            "description": description,
            "body": body,
            "author": _author_name(block.get("author")),
            "published": str(block.get("datePublished") or "") or None,
            "word_count": len(body.split()),
            "teaser_only": bool(body) and body == description,
            "paywalled": not _is_free(block),
            "kind": "article",
            "video_url": None,
            "duration": None,
        }

    for block in blocks:
        if block.get("@type") != "VideoObject":
            continue
        description = _strip_tags(str(block.get("description") or ""))
        return {
            "title": _strip_tags(str(block.get("name") or "")) or _page_title(html_text),
            "description": description,
            "body": description,
            "author": "",
            "published": str(block.get("uploadDate") or "") or None,
            "word_count": len(description.split()),
            "teaser_only": True,
            "paywalled": not _is_free(block),
            "kind": "video",
            "video_url": str(block.get("contentUrl") or "") or None,
            "duration": str(block.get("duration") or "") or None,
        }

    description = ""
    for block in blocks:
        if block.get("description"):
            description = _strip_tags(str(block.get("description")))
            break
    if not description:
        og = _OG_DESC_RE.search(html_text)
        if og:
            description = html.unescape(og.group(1)).strip()
    body = _ssr_body(html_text)
    return {
        "title": _page_title(html_text),
        "description": description,
        "body": body,
        "author": "",
        "published": None,
        "word_count": len(body.split()),
        "teaser_only": bool(body) and body == description,
        "paywalled": False,
        "kind": "article",
        "video_url": None,
        "duration": None,
    }


def search_items(items: list, query: str) -> list:
    """Case-insensitive substring match over title + description."""
    q = (query or "").strip().casefold()
    if not q:
        raise ValueError("query must not be empty")
    return [
        it for it in items
        if q in (it.get("title") or "").casefold()
        or q in (it.get("description") or "").casefold()
    ]


def filter_by_section(items: list, section: str) -> list:
    """Items whose link-path section matches (case-insensitive
    substring, so "kultur" matches "kultur")."""
    s = (section or "").strip().casefold()
    if not s:
        raise ValueError("section must not be empty")
    return [it for it in items if s in (it.get("section") or "").casefold()]


def filter_by_region(items: list, region: str) -> list:
    """Items whose link-path region matches one of the four states."""
    r = validate_region(region)
    return [it for it in items if (it.get("region") or "") == r]


def list_sections(items: list) -> list[dict]:
    """Distinct sections in the feed with item counts, most first."""
    counts: dict[str, int] = {}
    for it in items:
        sec = (it.get("section") or "").strip()
        if sec:
            counts[sec] = counts.get(sec, 0) + 1
    return [
        {"section": sec, "count": n}
        for sec, n in sorted(counts.items(), key=lambda kv: -kv[1])
    ]


def dedupe_sort(items: list) -> list:
    """De-duplicate by link, newest first (empty publish time sorts last)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    unique.sort(key=lambda it: it.get("published") or "", reverse=True)
    return unique

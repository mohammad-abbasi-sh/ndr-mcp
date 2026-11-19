# ndr-mcp 📻

mcp-name: io.github.mohammad-abbasi-sh/ndr-mcp

Unofficial **read-only** MCP server for **[NDR](https://www.ndr.de)** — the Norddeutscher Rundfunk, the public broadcaster for Hamburg, Lower Saxony, Mecklenburg-Vorpommern and Schleswig-Holstein — via its official RSS feeds ([www.ndr.de/index~rss2.xml](https://www.ndr.de/index~rss2.xml) plus one feed per region) and article pages, whose full text is read from the JSON-LD `articleBody` (or, where a page carries none, from the server-rendered `<article>` paragraphs). Top headlines, regional news for the four NDR states, news by section (nachrichten, kultur, sport, ratgeber, geschichte, fernsehen, …), keyword search, and full article text. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with NDR or ARD.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "ndr": {
      "command": "uvx",
      "args": ["ndr-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m ndr_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `ndr_headlines` | Top headlines (official RSS feed, ~106 items), newest first — `limit` 1..150 |
| `ndr_news_by_region` | Newest news from one of the four broadcast states, from its own regional feed — `region`: "niedersachsen", "hamburg", "mecklenburg-vorpommern", "schleswig-holstein", `limit` 1..150 |
| `ndr_news_by_section` | Newest news of one section — `section`: "nachrichten", "kultur", "sport", "ratgeber", "geschichte", "fernsehen", "mediathek", … (case-insensitive substring match), `limit` 1..150 |
| `ndr_search_news` | Search news by keyword (title + teaser) in the main feed — `query` (e.g. "Hamburg"), `limit` 1..150 |
| `ndr_get_article` | Full text of one NDR article page (JSON-LD `articleBody`, or the server-rendered `<article>` paragraphs) — `url`: a www.ndr.de article URL ending in .html. Video pages return `kind: "video"` with the description and the ARD Mediathek URL; a non-free page returns `paywalled: true` with the teaser only |
| `ndr_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`ndr_headlines`, `limit` 2):

```json
{"feed_title": "NDR.de - Das Beste am Norden - Radio - Fernsehen - Nachrichten", "total_results": 106, "count": 2,
 "items": [
  {"title": "NiedersachsenTrend: SPD liegt vorn, CDU verliert",
   "link": "https://www.ndr.de/nachrichten/niedersachsen/ndr-wahlumfrage-spd-liegt-deutlich-vorn-cdu-und-afd-gleichauf,niedersachsentrend-112.html",
   "description": "Würde am Sonntag in Niedersachsen gewählt werden, hätte die rot-grüne Regierung keine Mehrheit mehr. CDU und AfD lägen gleichauf.",
   "published": "2026-11-19T05:30:00+00:00", "section": "nachrichten", "region": "niedersachsen"},
  ...]}
```

Notes:
- The server reads the **official RSS feeds** (main feed 106 items, regional feeds 57–69 items each, verified live 2026-11-19). Search and section filters run client-side over the fetched feed.
- The feed carries **no `<category>` and no author**: `section` and `region` are derived from each item's link path (e.g. `/kultur/...`, `/nachrichten/niedersachsen/...`). 14 of the 106 main-feed items link to ARD Mediathek video pages (section `"mediathek"`); those live on another host and are not fetched by `ndr_get_article`.
- **Article text, honestly:** "nachrichten" pages carry the full text in the JSON-LD `articleBody` (4,884 chars sampled); "kultur" pages carry no `articleBody`, so the body is read from the server-rendered `<article>` paragraphs (3,500 chars sampled, header/byline paragraphs filtered out). "fernsehen" video pages carry a VideoObject block — `ndr_get_article` returns `kind: "video"` with the description, the Mediathek URL and the duration, never fabricated text. NDR is public broadcasting: sampled pages are free (`isAccessibleForFree: true`); a page that is not free returns `paywalled: true` with the teaser only.
- Data: NDR public RSS feeds and article pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the real captured main + regional RSS feeds and three real article pages (nachrichten with JSON-LD body, kultur with SSR-only body, fernsehen video page)
- `tests/test_live.py` — cautious live requests against www.ndr.de

Tests: 47/47 green (40 offline + 7 live, 2026-11-19).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)

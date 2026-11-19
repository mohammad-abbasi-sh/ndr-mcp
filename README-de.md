# ndr-mcp 📻

mcp-name: io.github.mohammad-abbasi-sh/ndr-mcp

Inoffizieller **Read-only**-MCP-Server für **[NDR](https://www.ndr.de)** — den Norddeutschen Rundfunk, öffentlich-rechtlicher Sender für Hamburg, Niedersachsen, Mecklenburg-Vorpommern und Schleswig-Holstein — über die offiziellen RSS-Feeds ([www.ndr.de/index~rss2.xml](https://www.ndr.de/index~rss2.xml) plus je einen Feed pro Region) und Artikelseiten, deren Volltext aus dem JSON-LD-`articleBody` gelesen wird (oder, wo eine Seite keines trägt, aus den serverseitig gerenderten `<article>`-Absätzen). Top-Schlagzeilen, Regionalnachrichten für die vier NDR-Länder, Nachrichten nach Ressort (nachrichten, kultur, sport, ratgeber, geschichte, fernsehen, …), Stichwortsuche und Volltexte von Artikeln. Kein Schlüssel, kein Login.

> Gebaut von Mohammad Abbasi als Teil der "Germany MCP factory" (Sepehr-ähnliche Pipeline). Nicht mit NDR oder ARD verbunden.

## Für KI-Agenten

In die MCP-Client-Konfiguration eintragen (stdio):

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

Oder lokal starten: `python -m ndr_mcp.server` (benötigt `mcp<2`, `httpx`).

## Tools

| Tool | Beschreibung |
|------|-------------|
| `ndr_headlines` | Top-Schlagzeilen (offizieller RSS-Feed, ~106 Einträge), neueste zuerst — `limit` 1..150 |
| `ndr_news_by_region` | Neueste Nachrichten aus einem der vier Sendeländer, aus dem eigenen Regional-Feed — `region`: "niedersachsen", "hamburg", "mecklenburg-vorpommern", "schleswig-holstein", `limit` 1..150 |
| `ndr_news_by_section` | Neueste Nachrichten eines Ressorts — `section`: "nachrichten", "kultur", "sport", "ratgeber", "geschichte", "fernsehen", "mediathek", … (Teilstring, Groß-/Kleinschreibung egal), `limit` 1..150 |
| `ndr_search_news` | Stichwortsuche in den Nachrichten (Titel + Teaser) im Haupt-Feed — `query` (z. B. "Hamburg"), `limit` 1..150 |
| `ndr_get_article` | Volltext einer NDR-Artikelseite (JSON-LD `articleBody` oder die serverseitig gerenderten `<article>`-Absätze) — `url`: eine www.ndr.de-Artikel-URL mit Endung .html. Videoseiten liefern `kind: "video"` mit Beschreibung und ARD-Mediathek-URL; eine nicht frei zugängliche Seite liefert `paywalled: true` und nur den Teaser |
| `ndr_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Beispielausgabe (`ndr_headlines`, `limit` 2):

```json
{"feed_title": "NDR.de - Das Beste am Norden - Radio - Fernsehen - Nachrichten", "total_results": 106, "count": 2,
 "items": [
  {"title": "NiedersachsenTrend: SPD liegt vorn, CDU verliert",
   "link": "https://www.ndr.de/nachrichten/niedersachsen/ndr-wahlumfrage-spd-liegt-deutlich-vorn-cdu-und-afd-gleichauf,niedersachsentrend-112.html",
   "description": "Würde am Sonntag in Niedersachsen gewählt werden, hätte die rot-grüne Regierung keine Mehrheit mehr. CDU und AfD lägen gleichauf.",
   "published": "2026-11-19T05:30:00+00:00", "section": "nachrichten", "region": "niedersachsen"},
  ...]}
```

Hinweise:
- Der Server liest die **offiziellen RSS-Feeds** (Haupt-Feed 106 Einträge, Regional-Feeds je 57–69 Einträge, live verifiziert 2026-11-19). Suche und Ressortfilter laufen clientseitig über den geladenen Feed.
- Der Feed trägt **keine `<category>` und keinen Autor**: `section` und `region` werden aus dem Linkpfad jedes Eintrags abgeleitet (z. B. `/kultur/...`, `/nachrichten/niedersachsen/...`). 14 der 106 Haupt-Feed-Einträge verlinken auf ARD-Mediathek-Videoseiten (Ressort `"mediathek"`); diese liegen auf einem anderen Host und werden von `ndr_get_article` nicht abgerufen.
- **Artikeltexte, ehrlich:** "nachrichten"-Seiten tragen den Volltext im JSON-LD-`articleBody` (4.884 Zeichen in der Stichprobe); "kultur"-Seiten tragen kein `articleBody`, dort wird der Text aus den serverseitig gerenderten `<article>`-Absätzen gelesen (3.500 Zeichen in der Stichprobe, Kopf- und Autorenabsätze herausgefiltert). "fernsehen"-Videoseiten tragen einen VideoObject-Block — `ndr_get_article` liefert `kind: "video"` mit Beschreibung, Mediathek-URL und Dauer, niemals erfundenen Text. NDR ist öffentlich-rechtlich: die Stichproben sind frei (`isAccessibleForFree: true`); eine nicht freie Seite liefert `paywalled: true` und nur den Teaser.
- Daten: öffentliche NDR-RSS-Feeds und Artikelseiten — kein Schlüssel, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parst die echten, gespeicherten Haupt- und Regional-Feeds sowie drei echte Artikelseiten (nachrichten mit JSON-LD-Text, kultur nur mit SSR-Text, fernsehen-Videoseite)
- `tests/test_live.py` — vorsichtige Live-Anfragen an www.ndr.de

Tests: 47/47 grün (40 offline + 7 live, 2026-11-19).

## Lizenz

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — frei für private und nicht-kommerzielle Nutzung; kommerzielle Nutzung braucht eine separate Lizenz (siehe LICENSE).

---

Gebaut von [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)

# ndr-mcp 📻

mcp-name: io.github.mohammad-abbasi-sh/ndr-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[NDR](https://www.ndr.de)** — رادیو-تلویزیون شمال آلمان (Norddeutscher Rundfunk)، رسانهٔ عمومی هامبورگ، نیدرزاکسن، مکلنبورگ-فورپومرن و اشلسویگ-هولشتاین — از طریق فیدهای رسمی RSS ([www.ndr.de/index~rss2.xml](https://www.ndr.de/index~rss2.xml) به‌علاوهٔ یک فید برای هر ایالت) و صفحات مقالات که متن کامل آن‌ها از `articleBody` در JSON-LD خوانده می‌شود (یا اگر صفحه‌ای آن را نداشت، از پاراگراف‌های `<article>` رندرشده در سرور). تیترهای برتر، اخبار منطقه‌ای چهار ایالت NDR، اخبار بر اساس بخش (nachrichten، kultur، sport، ratgeber، geschichte، fernsehen و …)، جست‌وجوی کلیدواژه و متن کامل مقالات. بدون کلید، بدون ورود.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP آلمان» (خط تولیدی به سبک سپهر). وابسته به NDR یا ARD نیست.

## برای ایجنت‌های هوش مصنوعی

در پیکربندی کلاینت MCP اضافه کنید (stdio):

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

یا اجرای محلی: `python -m ndr_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `ndr_headlines` | تیترهای برتر (فید رسمی RSS، حدود ۱۰۶ مورد)، تازه‌ترین اول — `limit` ۱ تا ۱۵۰ |
| `ndr_news_by_region` | تازه‌ترین اخبار یکی از چهار ایالت پخش، از فید منطقه‌ای خودش — `region`: ‏«niedersachsen»، ‏«hamburg»، ‏«mecklenburg-vorpommern»، ‏«schleswig-holstein»، `limit` ۱ تا ۱۵۰ |
| `ndr_news_by_section` | تازه‌ترین اخبار یک بخش — `section`: ‏«nachrichten»، ‏«kultur»، ‏«sport»، ‏«ratgeber»، ‏«geschichte»، ‏«fernsehen»، ‏«mediathek» و … (تطبیق زیررشته‌ای، بدون حساسیت به بزرگی/کوچکی حروف)، `limit` ۱ تا ۱۵۰ |
| `ndr_search_news` | جست‌وجوی اخبار با کلیدواژه (عنوان + تیزر) در فید اصلی — `query` (مثلاً «Hamburg»)، `limit` ۱ تا ۱۵۰ |
| `ndr_get_article` | متن کامل یک مقالهٔ NDR (‏`articleBody` در JSON-LD یا پاراگراف‌های `<article>` رندرشده در سرور) — `url`: آدرس مقاله در www.ndr.de با پسوند .html. صفحات ویدیویی `kind: "video"` را با توضیح و آدرس ARD Mediathek برمی‌گردانند؛ صفحهٔ غیررایگان فقط تیزر را برمی‌گرداند (`paywalled: true`) |
| `ndr_health` | بررسی دسترسی به فید (ok / blocked / error) — یک درخواست مؤدبانه |

نمونهٔ خروجی (`ndr_headlines` با `limit` برابر ۲):

```json
{"feed_title": "NDR.de - Das Beste am Norden - Radio - Fernsehen - Nachrichten", "total_results": 106, "count": 2,
 "items": [
  {"title": "NiedersachsenTrend: SPD liegt vorn, CDU verliert",
   "link": "https://www.ndr.de/nachrichten/niedersachsen/ndr-wahlumfrage-spd-liegt-deutlich-vorn-cdu-und-afd-gleichauf,niedersachsentrend-112.html",
   "description": "Würde am Sonntag in Niedersachsen gewählt werden, hätte die rot-grüne Regierung keine Mehrheit mehr. CDU und AfD lägen gleichauf.",
   "published": "2026-11-19T05:30:00+00:00", "section": "nachrichten", "region": "niedersachsen"},
  ...]}
```

نکته‌ها:
- سرور **فیدهای رسمی RSS** را می‌خواند (فید اصلی ۱۰۶ مورد، فیدهای منطقه‌ای هر کدام ۵۷ تا ۶۹ مورد، تأیید زنده در ۲۰۲۶-۱۱-۱۹). جست‌وجو و فیلتر بخش روی فیدِ دریافت‌شده انجام می‌شود.
- فید **نه `<category>` دارد و نه نویسنده**: `section` و `region` از مسیر لینک هر مورد به دست می‌آیند (مثلاً `/kultur/...` یا `/nachrichten/niedersachsen/...`). ۱۴ مورد از ۱۰۶ مورد فید اصلی به صفحات ویدیویی ARD Mediathek لینک می‌دهند (بخش `"mediathek"`)؛ آن‌ها روی هاست دیگری‌اند و `ndr_get_article` آن‌ها را نمی‌خواند.
- **متن مقالات، صادقانه:** صفحات «nachrichten» متن کامل را در `articleBody` در JSON-LD دارند (در نمونه ۴٬۸۸۴ کاراکتر)؛ صفحات «kultur» `articleBody` ندارند، پس متن از پاراگراف‌های `<article>` رندرشده در سرور خوانده می‌شود (در نمونه ۳٬۵۰۰ کاراکتر، با حذف پاراگراف‌های سربرگ و نام نویسنده). صفحات ویدیویی «fernsehen» بلوک VideoObject دارند — `ndr_get_article` برای آن‌ها `kind: "video"` را با توضیح، آدرس مدیاتک و مدت ویدیو برمی‌گرداند و هرگز متن نمی‌سازد. NDR رسانهٔ عمومی است: نمونه‌ها رایگان‌اند (`isAccessibleForFree: true`)؛ صفحهٔ غیررایگان فقط تیزر را برمی‌گرداند (`paywalled: true`).
- داده‌ها: فیدهای عمومی RSS و صفحات مقالات NDR — بدون کلید، بدون ورود، فقط‌خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین؛ فیدهای واقعیِ ذخیره‌شده (اصلی + منطقه‌ای) و سه صفحهٔ مقالهٔ واقعی را تجزیه می‌کند (nachrichten با متن JSON-LD، kultur فقط با متن SSR، صفحهٔ ویدیویی fernsehen)
- `tests/test_live.py` — درخواست‌های زندهٔ محتاطانه به www.ndr.de

تست‌ها: ۴۷/۴۷ سبز (۴۰ آفلاین + ۷ زنده، ۲۰۲۶-۱۱-۱۹).

## مجوز

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — رایگان برای استفادهٔ شخصی و غیرتجاری؛ استفادهٔ تجاری نیازمند مجوز جداگانه است (به LICENSE نگاه کنید).

---

ساختهٔ [محمد عباسی](https://github.com/mohammad-abbasi-sh) — [آلمانی‌باما](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)

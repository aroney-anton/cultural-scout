#!/usr/bin/env python3
"""
run_tests.py — offline tests for the image scraper. No network needed.

Run from anywhere:  python3 image_scraper/tests/run_tests.py

Covers: image extraction (srcset picking, captions, context, junk filtering,
dedup), paywall detection, the Playwright-fallback decision rule, corpus
selection/date parsing in run.py, and the contact-sheet builder (using
locally generated placeholder images, never downloaded ones).
"""

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # import the scraper modules

import extractor  # noqa: E402
import run as runner  # noqa: E402
from sheets import build_contact_sheets  # noqa: E402

BASE = "https://example-magazine.com/features/toaster-urns"
PASS = FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


# ---------------------------------------------------------------------------
print("extract_images() on the article fixture")
html = (HERE / "fixture_article.html").read_text()
images = extractor.extract_images(html, BASE)
urls = [i["url"] for i in images]

check("keeps exactly the 3 editorial images", len(images) == 3, f"got {urls}")
check("picture/srcset resolves to the highest-res candidate",
      "https://example-magazine.com/img/urn-toaster-1600.jpg" in urls, f"got {urls}")
check("img srcset resolves to the highest-res candidate",
      "https://example-magazine.com/img/studio-2400.jpg" in urls, f"got {urls}")
check("lazy-load data-src is picked up",
      "https://example-magazine.com/img/lazy-kiln.jpg" in urls, f"got {urls}")
check("figcaption captured",
      any("toaster urn, stoneware" in i["caption"] for i in images))
check("caption-class sibling captured",
      any("Shelves of works in progress" in i["caption"] for i in images))
check("context = nearest preceding paragraph",
      any("converted garage in Ridgewood" in i["context"] for i in images))
check("ad-domain image filtered",
      not any("googlesyndication" in u for u in urls))
check("1x1 pixel filtered", not any("tracking-pixel" in u for u in urls))
check("avatar filtered", not any("avatar" in u for u in urls))
check("sub-200px image filtered", not any("small-thumb" in u for u in urls))
check("logo/nav/footer furniture filtered",
      not any(("logo" in u or "nav-icon" in u or "badge" in u) for u in urls))
check("duplicate URL deduped", len(urls) == len(set(urls)))

# ---------------------------------------------------------------------------
print("metadata + paywall + fallback decisions")
title, date, author, tags, text = extractor.extract_article_fields(html, BASE)
check("title extracted", "Funeral Urns" in title, f"got {title!r}")
check("paywall fixture detected",
      extractor.looks_paywalled((HERE / "fixture_paywall.html").read_text(), ""))
check("normal article is NOT flagged as paywalled",
      not extractor.looks_paywalled(html, text))
check("long text + images -> no Playwright needed",
      not extractor.needs_playwright("x" * 500, [{"url": "a"}]))
check("thin text -> Playwright fallback", extractor.needs_playwright("x" * 50, [{"url": "a"}]))
check("zero images -> Playwright fallback", extractor.needs_playwright("x" * 500, []))

# scrape_article with both fetchers stubbed out: must degrade to 'failed',
# never raise. (This exercises the fallback path without any network.)
_orig_static, _orig_pw = extractor.fetch_static, extractor.fetch_playwright
extractor.fetch_static = lambda url, rl, timeout=0: None
extractor.fetch_playwright = lambda url, rl, timeout=0: None
rec = extractor.scrape_article("https://example.com/x", extractor.RateLimiter(0))
check("both fetchers dead -> fetch_method 'failed', no exception",
      rec["fetch_method"] == "failed" and rec["images"] == [])
extractor.fetch_static, extractor.fetch_playwright = _orig_static, _orig_pw

# ---------------------------------------------------------------------------
print("corpus selection (run.py)")
check("date '2026-04-22' parses", runner.parse_signal_date("2026-04-22") is not None)
check("date '2026-04 (approx)' parses to mid-month",
      runner.parse_signal_date("2026-04 (approx)").day == 15)
check("garbage date -> None", runner.parse_signal_date("spring, maybe") is None)
check("homepage URL rejected", not runner.is_article_url("https://032c.com/"))
check("article URL accepted", runner.is_article_url("https://032c.com/magazine/piece"))

recent = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
old = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
mini_corpus = {"signals": [
    {"id": "a", "need": "Certified Human", "url": "https://m.com/art-1",
     "date": recent, "tier": "extended", "forward_looking": False,
     "source": "m", "_runs": ["2026-06-22"]},
    {"id": "b", "need": "Certified Human", "url": "https://m.com/art-2",
     "date": recent, "tier": "core", "forward_looking": True,
     "source": "m", "_runs": ["2026-06-22"]},
    {"id": "c", "need": "Certified Human", "url": "https://m.com/",   # homepage
     "date": recent, "tier": "core", "source": "m", "_runs": ["2026-06-22"]},
    {"id": "d", "need": "Kinship", "url": "https://m.com/art-3",      # wrong need
     "date": recent, "tier": "core", "source": "m", "_runs": ["2026-06-22"]},
    {"id": "e", "need": "Certified Human", "url": "https://m.com/art-4",
     "date": old, "tier": "core", "source": "m", "_runs": ["2026-04-29"]},
]}
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump(mini_corpus, f)
    corpus_path = f.name

sel = runner.select_from_corpus(corpus_path, "Certified Human")
sel_ids = [m["signal_id"] for _, m in sel]
check("need filter + homepage skip", set(sel_ids) == {"a", "b", "e"}, f"got {sel_ids}")
check("core/forward-looking signal ranked first", sel_ids[0] == "b", f"got {sel_ids}")
sel_recent = runner.select_from_corpus(corpus_path, "Certified Human", days=90)
check("--days filter drops the old signal",
      set(m["signal_id"] for _, m in sel_recent) == {"a", "b"})
sel_run = runner.select_from_corpus(corpus_path, "Certified Human",
                                    run_filter="2026-04-29")
check("--run filter works", [m["signal_id"] for _, m in sel_run] == ["e"])

# ---------------------------------------------------------------------------
print("contact sheets (Pillow-generated placeholders, nothing downloaded)")
from PIL import Image  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    cache = Path(tmp) / "cache"
    out = Path(tmp) / "sheets"
    cache.mkdir()
    manifest = {}
    colors = [(200, 60, 60), (60, 200, 60), (60, 60, 200)]
    for n in range(14):  # 14 images -> one full 12-up sheet + one partial
        fname = f"ph{n:02d}.png"
        Image.new("RGB", (600 + n * 10, 400), colors[n % 3]).save(cache / fname)
        manifest[fname] = {"image_url": f"https://m.com/img{n}.jpg",
                           "article_url": f"https://m.com/art-{n}",
                           "source": "m", "need": "Certified Human",
                           "title": f"Article {n}", "alt": f"alt {n}",
                           "caption": f"cap {n}", "context": ""}
    written = build_contact_sheets(manifest, cache, out, run_label="test")

    check("two sheets for 14 images", len(written) == 2, f"got {len(written)}")
    check("sheet PNGs exist and open",
          all(Image.open(p).size == (1200, 1600) for p in written))
    side1 = json.loads((out / "sheet_test_001.json").read_text())
    side2 = json.loads((out / "sheet_test_002.json").read_text())
    check("sheet 1 sidecar numbers 1-12",
          sorted(map(int, side1)) == list(range(1, 13)))
    check("sheet 2 sidecar continues globally at 13-14",
          sorted(map(int, side2)) == [13, 14])
    check("sidecar metadata maps back to the source",
          side1["1"]["article_url"] == "https://m.com/art-0"
          and side1["1"]["image_url"] == "https://m.com/img0.jpg")

# ---------------------------------------------------------------------------
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

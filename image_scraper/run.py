#!/usr/bin/env python3
"""
run.py — the single entry point for the image-collection subsystem.

Three subcommands:

  python run.py scrape --need "Certified Human" [--days 90] [--limit 60]
      Pulls article URLs for one need out of ../corpus.json, fetches each
      article, extracts images + captions + context, and writes one JSON
      file into output/. Two balance caps (defaults): max 15 images kept
      per article (--max-per-article), and scraping stops once the pool
      hits 250 images (--target-images), the collection target per code.

  python run.py scrape --urls extra_urls.txt --need "Certified Human"
      Same, but the URLs come from a plain text file (one URL per line) —
      this is the "round 2" path, for gap-filling URLs found via web search.

  python run.py sheets [--input output/<file>.json]
      Downloads the extracted images into the temp cache (.cache/) and
      composites them into numbered contact sheets (sheets/) for the AI
      to read. Defaults to the newest file in output/.

  python run.py clean
      Deletes .cache/ and sheets/ entirely. Run this when analysis is done
      — downloaded imagery is a temporary analysis artifact and must never
      linger, be committed, or be shipped (see CLAUDE.md copyright rule).

Everything is resolved relative to THIS file's folder, so the commands work
no matter which directory you run them from.
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# All paths anchor to the image_scraper/ folder itself.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # so `import extractor` works from anywhere

from extractor import RateLimiter, scrape_article  # noqa: E402
from sheets import build_contact_sheets, download_images  # noqa: E402

OUTPUT_DIR = HERE / "output"
CACHE_DIR = HERE / ".cache"
SHEETS_DIR = HERE / "sheets"
LOGS_DIR = HERE / "logs"
LEDGER_PATH = HERE / "seen_urls.json"     # remembers which URLs we've scraped
DEFAULT_CORPUS = HERE.parent / "corpus.json"

log = logging.getLogger("image_scraper")


# ---------------------------------------------------------------------------
# Logging — everything goes to the console AND to a log file per run.
# ---------------------------------------------------------------------------

def setup_logging(command):
    LOGS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = LOGS_DIR / f"{command}_{stamp}.log"

    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")

    to_file = logging.FileHandler(logfile, encoding="utf-8")
    to_file.setLevel(logging.DEBUG)          # the file gets everything
    to_file.setFormatter(fmt)

    to_console = logging.StreamHandler()
    to_console.setLevel(logging.INFO)        # the console stays readable
    to_console.setFormatter(fmt)

    log.addHandler(to_file)
    log.addHandler(to_console)
    log.info("Log file: %s", logfile)
    return logfile


# ---------------------------------------------------------------------------
# The seen-URLs ledger — dedup across runs.
# ---------------------------------------------------------------------------

def load_ledger():
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text())
        except Exception:  # noqa: BLE001
            log.warning("seen_urls.json was unreadable — starting a fresh ledger")
    return {}


def save_ledger(ledger):
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Picking article URLs out of corpus.json
# ---------------------------------------------------------------------------

def parse_signal_date(raw):
    """Corpus dates come in flavors: '2026-04-22', '2026-03-15 (approx)',
    '2026-04 (approx)'. Return a datetime, or None if unparsable.
    Month-only dates are treated as the 15th of that month."""
    if not raw:
        return None
    cleaned = raw.replace("(approx)", "").replace("~", "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            if fmt == "%Y-%m":
                dt = dt.replace(day=15)
            return dt
        except ValueError:
            continue
    return None


def is_article_url(url):
    """Homepage/root URLs (a known corpus quirk — e.g. the fifteen 032c
    signals that all share the magazine root) can't be scraped as articles.
    Keep only URLs with a real path."""
    path = urlparse(url).path.strip("/")
    return bool(path)


def select_from_corpus(corpus_path, need, days=None, run_filter=None, limit=40):
    """Filter corpus.json down to the article URLs for one need, ordered the
    way SEMIOTIC_CODEBOOK.md samples: tier 'core' first, then forward_looking,
    then most recent. Returns a list of (url, meta) pairs."""
    corpus = json.loads(Path(corpus_path).read_text())
    signals = corpus.get("signals", [])

    cutoff = datetime.now() - timedelta(days=days) if days else None
    picked = []

    for sig in signals:
        if sig.get("need") != need:
            continue
        if run_filter and run_filter not in (sig.get("_runs") or []):
            continue
        url = (sig.get("url") or "").strip()
        if not url or not is_article_url(url):
            log.debug("  skipping homepage/empty URL for signal %s", sig.get("id"))
            continue
        sig_date = parse_signal_date(sig.get("date"))
        if cutoff and (sig_date is None or sig_date < cutoff):
            continue
        picked.append((url, sig, sig_date or datetime.min))

    # Codebook sampling order: core tier, then forward-looking, then recency.
    picked.sort(key=lambda t: (
        0 if t[1].get("tier") == "core" else 1,
        0 if t[1].get("forward_looking") else 1,
        -t[2].timestamp() if t[2] != datetime.min else 0,
    ))

    results = []
    for url, sig, _ in picked[:limit]:
        results.append((url, {
            "signal_id": sig.get("id"),
            "source": sig.get("source"),
            "need": sig.get("need"),
            "date": sig.get("date"),
        }))
    log.info("Corpus: %d signals matched need=%r%s%s; taking %d (limit %d)",
             len(picked), need,
             f", last {days} days" if days else "",
             f", run {run_filter}" if run_filter else "",
             len(results), limit)
    return results


def select_from_urls_file(urls_path, need):
    """Round-2 path: read a plain text file of article URLs (one per line,
    blank lines and #comments ignored). These have no corpus signal behind
    them, so signal_id is null and the need is whatever was passed in."""
    lines = Path(urls_path).read_text().splitlines()
    results = []
    for line in lines:
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        if not url.startswith("http"):
            log.warning("  skipping non-URL line in %s: %r", urls_path, url[:80])
            continue
        results.append((url, {"signal_id": None, "source": None,
                              "need": need or "", "date": None}))
    log.info("URL file: %d article URLs read from %s", len(results), urls_path)
    return results


# ---------------------------------------------------------------------------
# Subcommand: scrape
# ---------------------------------------------------------------------------

def cmd_scrape(args):
    setup_logging("scrape")

    # 1. Build the worklist — from a URLs file (round 2) or the corpus (round 1).
    if args.urls:
        worklist = select_from_urls_file(args.urls, args.need)
    else:
        if not args.need:
            sys.exit("scrape needs either --need (corpus mode) or --urls FILE.")
        worklist = select_from_corpus(args.corpus, args.need,
                                      days=args.days, run_filter=args.run,
                                      limit=args.limit)
    if not worklist:
        log.warning("Nothing to scrape — check the need spelling / filters / file.")
        return

    # 2. Drop URLs we've scraped before (unless --force), and in-run dupes.
    ledger = load_ledger()
    seen_this_run = set()
    final = []
    for url, meta in worklist:
        if url in seen_this_run:
            continue
        seen_this_run.add(url)
        if url in ledger and not args.force:
            log.info("  already scraped on %s — skipping (use --force to redo): %s",
                     ledger[url].get("scraped", "?"), url)
            continue
        final.append((url, meta))
    log.info("Scraping %d articles (%d skipped as already-seen)",
             len(final), len(worklist) - len(final))

    # 3. Scrape, one article at a time, never letting one failure kill the run.
    #    Two caps keep the pool balanced (added 2026-07-02 after the 1granary
    #    853-photo gallery flood):
    #      --max-per-article (default 15): one article can never swamp the pool.
    #      --target-images   (default 250): the collection target per code/run;
    #        scraping stops early once the pool is full. 0 = no target.
    limiter = RateLimiter(seconds_between=args.rate)
    articles, ok, pool = [], 0, 0
    for i, (url, meta) in enumerate(final, 1):
        log.info("[%d/%d] %s", i, len(final), url)
        try:
            record = scrape_article(url, limiter, signal_meta=meta,
                                    allow_playwright=not args.no_playwright)
        except Exception as exc:  # noqa: BLE001 — belt and braces
            log.error("  unexpected error on %s: %s", url, exc)
            record = {"site": meta.get("source") or urlparse(url).netloc,
                      "url": url, "title": "", "date": meta.get("date") or "",
                      "author": "", "tags": [], "text": "",
                      "signal_id": meta.get("signal_id"),
                      "need": meta.get("need") or "",
                      "fetch_method": "failed", "images": []}

        # Per-article cap: keep the first N in document order (the article's
        # own editorial priority), log what was dropped.
        found = len(record["images"])
        if args.max_per_article > 0 and found > args.max_per_article:
            record["images"] = record["images"][:args.max_per_article]
            record["images_found"] = found  # keep the true count on the record
            log.info("  capped: %d images found, keeping first %d (--max-per-article)",
                     found, args.max_per_article)

        articles.append(record)
        pool += len(record["images"])
        ledger[url] = {"scraped": datetime.now().strftime("%Y-%m-%d"),
                       "fetch_method": record["fetch_method"],
                       "images": len(record["images"])}
        if record["fetch_method"] != "failed":
            ok += 1
        log.info("  -> %s, %d images (pool: %d/%s)", record["fetch_method"],
                 len(record["images"]), pool,
                 args.target_images if args.target_images > 0 else "no target")

        # Collection target: stop early once the pool is full.
        if args.target_images > 0 and pool >= args.target_images:
            log.info("TARGET REACHED: %d images collected after %d of %d articles "
                     "— stopping early. Un-scraped articles stay OUT of the "
                     "ledger and will be picked up next run.", pool, i, len(final))
            break

    # 4. Write the run's output JSON + update the ledger.
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = (args.need or "urls").lower().replace(" ", "_")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"scrape_{slug}_{stamp}.json"
    out_path.write_text(json.dumps({
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "need": args.need or "",
        "articles": articles,
    }, indent=2, ensure_ascii=False))
    save_ledger(ledger)

    total_images = sum(len(a["images"]) for a in articles)
    log.info("DONE: %d/%d articles fetched, %d images extracted -> %s",
             ok, len(articles), total_images, out_path)
    if args.target_images > 0 and total_images < args.target_images:
        log.warning("SHORT OF TARGET: %d/%d images. The worklist ran out before "
                    "the pool filled — re-run with a higher --limit, widen --days, "
                    "or feed more URLs via --urls (round-2 gap-fill).",
                    total_images, args.target_images)
    try:
        shown = out_path.relative_to(HERE)
    except ValueError:  # output dir redirected elsewhere (e.g. in tests)
        shown = out_path
    log.info("Next step:  python run.py sheets --input %s", shown)


# ---------------------------------------------------------------------------
# Subcommand: sheets
# ---------------------------------------------------------------------------

def newest_output_file():
    files = sorted(OUTPUT_DIR.glob("scrape_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def cmd_sheets(args):
    setup_logging("sheets")

    # Which scrape output are we building sheets from?
    if args.input:
        in_path = Path(args.input)
        if not in_path.is_absolute():
            in_path = HERE / in_path
    else:
        in_path = newest_output_file()
        if in_path is None:
            sys.exit("No scrape output found in output/ — run `scrape` first.")
        log.info("No --input given; using the newest scrape output: %s", in_path.name)

    scrape_output = json.loads(in_path.read_text())

    # Step 1: download images into the temp cache (2MB cap, silent skips).
    limiter = RateLimiter(seconds_between=args.rate)
    manifest = download_images(scrape_output, CACHE_DIR, limiter)

    # Step 2: composite numbered contact sheets + sidecar JSONs.
    run_label = in_path.stem.replace("scrape_", "")
    written = build_contact_sheets(manifest, CACHE_DIR, SHEETS_DIR,
                                   run_label=run_label)
    if written:
        log.info("DONE: %d contact sheet(s) in %s — read each PNG alongside "
                 "its sidecar JSON.", len(written), SHEETS_DIR)
        log.info("REMINDER: cache + sheets are temporary analysis artifacts. "
                 "Run `python run.py clean` when the coding pass is finished.")


# ---------------------------------------------------------------------------
# Subcommand: clean
# ---------------------------------------------------------------------------

def cmd_clean(_args):
    setup_logging("clean")
    for folder in (CACHE_DIR, SHEETS_DIR):
        if folder.exists():
            shutil.rmtree(folder)
            log.info("Deleted %s", folder)
        else:
            log.info("Nothing to delete at %s", folder)
    log.info("Clean. (output/ JSONs are kept — they contain no images, "
             "only text and URLs.)")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Free image-collection subsystem for the Cultural Scout "
                    "semiotic-coding workflow.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scrape = sub.add_parser("scrape", help="extract images/captions from articles")
    p_scrape.add_argument("--need", help='corpus need to harvest, e.g. "Certified Human"')
    p_scrape.add_argument("--days", type=int, default=None,
                          help="only signals dated within the last N days")
    p_scrape.add_argument("--run", default=None,
                          help="only signals from this harvest run, e.g. 2026-06-22")
    p_scrape.add_argument("--limit", type=int, default=60,
                          help="max articles to scrape (default 60; the "
                               "--target-images stop usually fires first)")
    p_scrape.add_argument("--max-per-article", type=int, default=15,
                          help="max images kept per article, first-N in document "
                               "order (default 15; 0 = uncapped). Added after a "
                               "single 853-photo gallery flooded round 1.")
    p_scrape.add_argument("--target-images", type=int, default=250,
                          help="collection target per code/run: stop scraping "
                               "once this many images are pooled (default 250; "
                               "0 = no target)")
    p_scrape.add_argument("--corpus", default=str(DEFAULT_CORPUS),
                          help="path to corpus.json (default: ../corpus.json)")
    p_scrape.add_argument("--urls", default=None,
                          help="plain text file of article URLs (round-2 mode)")
    p_scrape.add_argument("--force", action="store_true",
                          help="re-scrape URLs already in the seen_urls.json ledger")
    p_scrape.add_argument("--rate", type=float, default=2.0,
                          help="seconds between requests to the same domain (default 2)")
    p_scrape.add_argument("--no-playwright", action="store_true",
                          help="never fall back to the headless browser")
    p_scrape.set_defaults(func=cmd_scrape)

    p_sheets = sub.add_parser("sheets", help="download images + build contact sheets")
    p_sheets.add_argument("--input", default=None,
                          help="a scrape output JSON (default: newest in output/)")
    p_sheets.add_argument("--rate", type=float, default=2.0,
                          help="seconds between image downloads per domain (default 2)")
    p_sheets.set_defaults(func=cmd_sheets)

    p_clean = sub.add_parser("clean", help="delete the image cache and contact sheets")
    p_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

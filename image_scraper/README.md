# Image Scraper — free image collection for semiotic coding

This subsystem replaces the expensive part of the semiotic-codes workflow: collecting imagery. The 2026-06-12 Certified Human pilot gathered images by driving a browser with a frontier AI model, screenshot by screenshot. This tool does the same collection step with free scripted extraction, so the AI only spends effort on the part that actually needs judgment: reading the images and writing the codes.

It is a **URL-fed extractor, not a crawler**. It never discovers articles itself. Round 1 feeds it the article URLs already sitting in `corpus.json` (every signal is tagged with a need). Round 2 feeds it URLs found via web search. Either way, its whole job is: fetch each article, pull out every meaningful image with its alt text, caption, and surrounding paragraph, and package the results for AI analysis as numbered contact sheets.

## Install (once)

From inside `image_scraper/`:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium     # the browser fallback for JS-heavy sites
```

The Playwright step downloads a headless Chromium (~150MB). You can skip it and run with `--no-playwright`, but JS-rendered sites (ArtReview category pages, Juxtapoz, etc.) will come back empty.

## The three commands

**1. Scrape.** Pull article URLs for one need out of the corpus, fetch each one, extract images:

```
python run.py scrape --need "Certified Human"
```

Useful flags: `--limit 40` (max articles, default 40), `--days 90` (only recent signals), `--run 2026-06-22` (only one harvest run), `--force` (re-scrape URLs already in the ledger), `--no-playwright`, `--rate 2` (seconds between hits to the same domain).

Round 2, for URLs found via web search (one URL per line, `#` comments allowed):

```
python run.py scrape --urls extra_urls.txt --need "Certified Human"
```

Output: a JSON file in `output/` with, per article: title, date, author, text excerpt, and every image's URL + alt + caption + context. No images are downloaded at this stage; the JSON holds only text and URLs.

**2. Sheets.** Download the extracted images into a temp cache and composite them into numbered contact sheets:

```
python run.py sheets
```

(defaults to the newest scrape output; use `--input output/<file>.json` to pick one). Each sheet in `sheets/` is a 12-up PNG grid, every image stamped with a number, plus a sidecar JSON mapping each number back to its image URL, article, source, alt, and caption. The AI reads the PNG, cites images by number, and the sidecar resolves the citation to a source. Numbering is global across sheets, so "image 17" is unambiguous.

**3. Clean.** When the coding pass is done:

```
python run.py clean
```

Deletes the image cache and the sheets. The `output/` JSONs stay (they contain no imagery).

## Copyright rules (hard)

Downloaded images and contact sheets are **temporary analysis artifacts only**. They are never committed to git (the project `.gitignore` enforces this), never copied into `site/`, and never shipped in any deliverable. Published semiotic codes reference imagery **only as live hotlinks** to the publishers' own servers, exactly as the existing `codes_*.json` evidence collages do. The scraper never attempts to defeat paywalls, login walls, or bot challenges; a walled page is recorded as `fetch_method: "failed"` and skipped. Run `clean` when analysis is finished.

## What failure looks like (and why it's fine)

Some sources on the list are hostile to any scripted fetch: the Met (bot challenge), Pitchfork (user-agent block), Thingtesting (403), paywalled newsletters (Snaxshot, The Hunger). These will show as `failed` in the log with a note. That is expected; they get covered manually with browser screenshots as before, or skipped. The scraper's job is to make the 80% that IS fetchable cost nothing.

Other troubleshooting: if a site returns text but zero images, it is probably lazy-loading via JS, and the Playwright fallback should have caught it (check it's installed). If everything from one domain fails suddenly, the site may have added bot protection; don't fight it. If a scrape returns very few articles, check the `--need` spelling matches the taxonomy exactly (e.g. `"Naming the Machine"`).

## How this slots into the codes workflow

See `SEMIOTIC_IMAGE_HARVEST.md` in this folder for the full two-round orchestration (scrape → sheets → AI codes → gap-fill via web search → second round), and `../SEMIOTIC_CODEBOOK.md` for the coding discipline itself.

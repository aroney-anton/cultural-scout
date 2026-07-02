# SEMIOTIC IMAGE HARVEST — orchestration playbook

Instructions for a Claude session running the semiotic-codes workflow for one need. This is the cheap replacement for the 2026-06-12 pilot method (browser screenshots per article). The AI does only the judgment work; collection is scripted and free.

**Read first, both binding:** `../SEMIOTIC_CODEBOOK.md` (coding discipline: stable IDs, append-don't-rewrite, evidence standards, residual/dominant/emergent status) and `README.md` in this folder (commands + copyright rules).

**Analysis model decision (Michael, 2026-07-02):** Fable reads the contact sheets directly. Do not delegate the visual reading to smaller models.

## Round 1 — corpus imagery

1. **Scrape.** `python run.py scrape --need "<Need>"` (from inside `image_scraper/`, venv active). Default limit 40 articles, ordered core-tier → forward-looking → recent, matching the codebook's sampling bias. Check the log tail: how many articles fetched, how many images, which failed.
2. **Sheets.** `python run.py sheets`. Note the sheet count in `sheets/`.
3. **Visual pass.** Read each `sheet_*.png` WITH its sidecar `sheet_*.json` side by side. For each image worth anything, note: number → what is visually happening (palette, register, composition, materiality, styling, typography), and which existing or candidate code it evidences. Cite images ONLY by sidecar number; resolve to URLs when writing evidence.
4. **Code pass.** Update or create `codes_<need>.json` per the codebook's update rules: append evidence to existing codes, move status with justification, propose new codes only on multi-source evidence, retire with cause. `image_refs` must be LIVE HOTLINKS (publisher URLs from the sidecar), credited, `referrerpolicy=no-referrer` — never cached files.

## Gap check, then Round 2 — targeted search

5. **Count coverage.** Target per code: **~20 high-quality evocative images, each from a DIFFERENT source** (source = publication/institution, not article). Most codes will be short after round 1; that is expected.
6. **Search for candidates.** For each under-covered code, use WebSearch (NEVER crawl; searching is the AI's job, fetching is the scraper's) to find recent article URLs likely to carry fitting imagery. Search on the code's visual registers and subject matter, not its name. Prefer sources NOT already represented in that code's evidence, to satisfy the different-source rule. Collect candidate article URLs into `urls_<need>_round2.txt` (one per line, `#` comments fine).
7. **Scrape round 2.** `python run.py scrape --urls urls_<need>_round2.txt --need "<Need>"` then `python run.py sheets --input output/<the new file>.json`. The image cache manifest extends, so new sheets contain only new imagery.
8. **Second analysis pass.** Repeat steps 3-4 on the new sheets. Add to the codes. If a code still can't reach ~20 distinct-source images after a genuine round 2, record what it has and note the shortfall in the code's `notes` — do NOT pad with weak or near-duplicate imagery. Thin honest evidence beats bulked evidence.

## Close out

9. **Verify hotlinks.** Spot-check a sample of `image_refs` URLs render (broken links self-hide in the preview panel, but dead-on-arrival links mean a bad URL was copied).
10. **Clean.** `python run.py clean` — the cache and sheets are temporary analysis artifacts (copyright rule). Confirm `git status` shows no images staged.
11. **Preview + gate.** Build the preview panel from the codes JSON (see `codes_preview_template.html` at project root). The user reviews before anything scales or deploys.

## Known constraints

Bot-hostile sources (the Met, Pitchfork, Thingtesting, paywalled newsletters) will fail the scraper; cover those few manually with browser screenshots if their imagery matters to a code, or skip. Newsletter-tier sources carry the ARGUMENT in text; magazines, galleries, and museums carry the IMAGERY (pilot learning) — weight round-2 searches accordingly.

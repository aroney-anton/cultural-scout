# Semiotic enrichment — visual-source wave (2026-07-09)

Purpose: push each existing code toward 15-20 images by scraping a set of image-rich
fashion/photography sources brought in **specifically for the semiotic/coding stage**
(not the monthly cultural harvest, not sources.yaml). URL-fed only — no crawling.

## Fetchability verdicts (all 17 live and usable)

| Source | Domain | Verdict | Notes / URL pattern |
|---|---|---|---|
| Highsnobiety | highsnobiety.com | GREEN | `/p/<slug>/`; some pieces "Sponsored" but real editorial photography |
| Hypebeast | hypebeast.com | GREEN | `/YYYY/M/<slug>`; very image-rich, captioned |
| SSENSE editorial | ssense.com/en-us/editorial | **YELLOW** | JS-rendered, **needs Playwright**; URLs search-confirmed only, verify per-article at scrape |
| Sabukaru | sabukaru.online | GREEN* | `/articles/<slug>`; text clean but **images lazy-load — Playwright advisable** |
| Perfect Magazine | theperfectmagazine.com | GREEN | `/features/<slug>` (slugs carry random suffixes); NOT perfectnumber.com |
| i-D | i-d.co | GREEN | `/article/<slug>/`; cleanest CDN images (media.i-d.co) |
| Interview Magazine | interviewmagazine.com | GREEN | `/<category>/<slug>`; full-res wp-content images |
| Document Journal | documentjournal.com | **YELLOW** | **Homepage/listings HIJACKED (darknet spam) — direct article URLs only**; images via JS slideshow (Playwright); fresh-URL discovery degraded. Re-verify health before leaning on it. |
| SHOWstudio | showstudio.com | **YELLOW** | JS-rendered, **needs Playwright**; imagery is mostly fashion-film stills |
| Foam | foam.org | GREEN | image-rich surface is exhibition pages `/events/<slug>` (announcement-exception) |
| Phroom | phroomplatform.com | GREEN | `/<artist-slug>/`; NOT phroom.com; clean hotlink full-res JPGs; archive skews 2018-21, lean on GETXO 2025 lane |
| Aperture | aperture.org | GREEN | `/editorial/<slug>/`; richest tagged photo-essays |
| Der Greif | dergreif.org | GREEN | `/artist-feature/`, `/guest-room/`, `/article/`; Guest Room pages = 20-40 image grids |
| Fisheye | fisheyemagazine.fr | GREEN | `/article/<slug>/` (+ `/en/article/`); images off fisheyeimmersive.com CDN |
| British Journal of Photography | 1854.photography | GREEN | `/YYYY/MM/<slug>/`; captioned hotlinks |
| Unthinking Photography | unthinking.photography | GREEN | `/articles/<slug>`; the Naming-the-Machine specialist (AI/algorithm critique) |
| PHmuseum | phmuseum.com | GREEN | `/news/<slug>` features; images off img.phmuseum.com |

\* Sabukaru text fetches via plain WebFetch but images lazy-load.

## URL files (feed to the scraper, one run per need)

```
python run.py scrape --urls urls_certified_human_semiotic_2026_07_09.txt   --need "Certified Human"
python run.py scrape --urls urls_naming_the_machine_semiotic_2026_07_09.txt --need "Naming the Machine"
python run.py scrape --urls urls_self-authorship_semiotic_2026_07_09.txt    --need "Self-Authorship"
python run.py scrape --urls urls_appetite_semiotic_2026_07_09.txt           --need "Appetite"
python run.py scrape --urls urls_settling_accounts_semiotic_2026_07_09.txt  --need "Settling Accounts"
```

Each file is grouped by `#`-commented code headers with a source/why note above every URL.
The scraper ignores comment/blank lines and reads only the bare URL lines (116 total).
Because SSENSE + SHOWstudio + Document need Playwright, run with `playwright install chromium`
done, and expect thinner yield from those three.

## URL counts by need / code (incl. round-2 gap-fill, 2026-07-09)

- **Certified Human — 42**: provenance-ledger 4, countable-labor 1, unretouched-witness 21, slop-repainted-slow **11** (gap-fill), analog-sanctuary 5
- **Naming the Machine — 23**: receipts-as-image 3, seams-showing-dossier 4, rigging-in-shot **11** (2 + 9 gap-fill), icon-assembly-line 5
- **Self-Authorship — 42**: author-among-the-work 12, self-as-the-work 15, heritage-re-signed 6, remix-self 3, against-the-algorithm 6
- **Appetite — 39**: prescription-pleasure **9** (gap-fill), the-defiant-feast **8** (gap-fill), the-aphrodisiac-table **10** (gap-fill), flesh-as-form 3, dark-cornucopia 2, toy-hunger 7
- **Settling Accounts — 25**: restaged-verdict **9** (1 + 8 gap-fill), canon-corrected 5, stitched-testimony 4, inheritance-reactivated 7

**Total: 171 URLs.** Every code now has enough distinct-source candidates to reach the
~15-20 image target (allowing for the codebook's per-source cap of 3 image_refs and one
count per source, plus some fetch attrition on YELLOW/Playwright pages).

## Round-2 gap-fill (2026-07-09) — the six codes that came up thin

The first wave's 17 sources are style + photography publications, so six codes were thin or
empty. A targeted WebSearch pass (reaching outside the 17, into the right lanes) filled them,
appended to the relevant files under `# --- round-2 gap-fill ... ---` headers:

- **slop-repainted-slow** — Sam McKinniss (paintings of viral JPEGs) + Erin M. Riley
  (tapestries of screenshots) anchor it: ARTnews, Wallpaper, Frieze, Dazed, W, Galerie, 4Columns, Artnet.
- **rigging-in-shot** — Magnum (conventions/Olympics/Super Bowl as image-machines) + Dazed backstage.
- **restaged-verdict** — Getty *Photographic Reenactment*, Carrie Mae Weems, Arles 2025, Hoda Afshar.
- **prescription-pleasure** — the food/beauty lane: Jessica DeFino, Gastronomica, 032c Ozempic, SCMP/China TCM-bars.
- **the-defiant-feast** — Hyperallergic eating-as-resistance, Wallpaper "To Have a Mouth", Duane Hanson, FAD women-artists-food.
- **the-aphrodisiac-table** — Chris Antemann "Forbidden Fruit" (dense body of work), Dalí cookbook, erotic-surrealism shows.

One RED source was dropped (culturedmag.com — blocks WebFetch). YELLOW/Playwright sources are
tagged `[Playwright]` inline (Magnum, 032c, SCMP, gallery JS pages, GATA, Richard Saltoun).

## Scope note

These 17 are **semiotic-stage-only** image sources. **DECISION (Michael, 2026-07-09):** they
are now recorded in `sources.yaml` under a dedicated SEMIOTIC-ONLY section, each flagged
`semiotic_only: true` (a `photography` category was added for the 8 photo publications). They
are still kept OUT of provenance.json and out of the monthly harvest / signal-tagging /
corpus.json / need-share pulse — the flag is what enforces that (Phase 0 harvest skips
`semiotic_only: true`, per the 2026-07-09 CLAUDE.md header block). The distinctiveness gate
does NOT apply at the coding stage: all content from all listed sources is in scope for imagery.
If any of them is ever wanted as a real editorial signal source, that's a separate decision
(distinctiveness-gate check + a provenance.json entry).

# Cultural Thought-Starter System — Project Playbook

## What this is
A 3-layer cultural intelligence pipeline. Harvests editorial content from a curated source list (Layer 1), tags it against Jonny's substrates — Connection / Coping / Agency / Vitality / Status / unsettled (Layer 2), and generates testable thought starters for a target category (Layer 3).

Canonical spec: `/Users/michaelaroney/Downloads/cultural-thought-starter-system-design-v1_1.md`

## SCOPE (locked 2026-06-25)
This project is SOLELY a cultural-discovery instrument. The bake-off (Round 4, `corpus_vs_openweb_bakeoff.md`) tested the corpus on B2B security, semis, policy, SaaS, and energy questions and it lost 4-0-1: its discovery edge is real but bounded to its cultural milieu (food, beauty, fashion, art, internet culture). Therefore: source expansion into non-cultural / B2B / policy / analyst / trade / hard-tech / energy domains is explicitly REJECTED. Do not add or propose such sources, even when a brief seems to ask for them; the corpus's job is to surface below-radar cultural signal, and open web + a strong model already do the off-domain work better. Keep the monthly harvest cadence so the pulse chart and need-share drift stay measurable over time.

Prior system (Innovation Pressure) failed by building all five layers before validating any one of them; compounded errors made output unusable. **This system has explicit validation gates between phases. Do not progress past a phase until its gate passes.**

## Run mode
Anthropic API credits are unavailable on the user's account. The `harvest.py` script and the (future) tag.py / generate.py scripts are written assuming API access — they're the eventual automated form. Until credits become available, **Claude Code performs each layer interactively in-session**, using its own `WebSearch` / `WebFetch` / native generation, writing the same JSON / Markdown outputs the scripts would produce. Same schemas, same files, same validation gates — just human-triggered rather than cron-driven.

If API credits become available later, switch to running the `.py` scripts directly. No code rewrite needed.

## Project layout
```
sources.yaml               # editorial source list — do not silently change
harvest.py                 # Layer 1 script (Anthropic API + web_search). Not runnable until credits available.
signals*.json              # Layer 1 output (raw harvest, one archived file per run)
tagged_signals*.json       # Layer 2 output (need + metadata, one file per run)
corpus.json                # merged/deduped corpus (build artifact) + int8 embeddings
embed.py                   # int8 embedding pass (degrades per-signal when HF hosts unreachable)
scout.py                   # CLI relevance search over the corpus
brief_<category>.md        # Layer 3 output

# --- front end (build chain: corpus -> site -> globe) ---
build_corpus.py            # merge tagged runs -> corpus.json (also runs build_site.py at the end)
build_site.py              # inline corpus into site/index.html (Search + Vital Signs); copies aux pages into site/
build_geology.py           # bake the Explore globe's GEO from corpus.json -> site/discover-geology.html
site/template.html         # SOURCE for Search + Vital Signs (edit this, NOT site/index.html)
mockup_discover_geology.html   # SOURCE for the Explore geology globe (edit this, NOT site/discover-geology.html)
mockup_discover_universe.html  # SOURCE for the "see the whole universe" constellation (copied to site/discover-universe.html)
geology_codes.json         # curated semiotic codes for the globe (persist across rebuilds)
vital_signs.json / provenance.json / receipts.json  # Vital Signs + provenance + methodology data
site/                      # deployable build artifact (index.html + discover-geology.html + discover-universe.html)
publish.sh                 # build_corpus.py + wrangler deploy site/ to Cloudflare Pages

.venv/                     # Python env: anthropic + PyYAML
requirements.txt
README.md                  # newcomer orientation (points here)
CLAUDE.md                  # this file
```

## EXPLORE = GEOLOGY GLOBE, + "SEE THE WHOLE UNIVERSE" TOGGLE (2026-07-02)
The Explore tab is no longer the suns-and-planets constellation by default. It is now a **geological cultural sphere** (a globe whose continents are the needs, width = need share). Both the globe and the recovered old constellation are reachable; the globe is the default.

**Architecture (three views, one site):** `site/index.html` (built from `site/template.html`) hosts Search / Explore / Vital Signs. The Explore view is an `<iframe>` holding one of two pages:
- **`site/discover-geology.html`** — the globe. SOURCE = `mockup_discover_geology.html`; **baked from corpus.json every build by `build_geology.py`** (per-need counts/pct + lexical clusters regenerate; taxonomy copy in `build_geology.py`'s NEED_META carried forward; curated semiotic codes persist in `geology_codes.json`, diffable for a future velocity card). This is the DEFAULT Explore view (`window.__initExplore` lazy-loads it).
- **`site/discover-universe.html`** — the recovered constellation ("see the whole universe"). SOURCE = `mockup_discover_universe.html`; static, copied into `site/` by `build_site.py`.

**GLOBE SEARCH-RECONSTITUTION (Task 3, done 2026-07-02).** Typing in the globe's `#geoq` box re-forms the sphere: matched signals are grouped into the SAME semantic themes the Search tab produces, each theme a territory tinted by its dominant need, clicking one opens the callout in `_cluster` mode ("Theme · X% of matches", look-&-feel hidden, real click-through article links). Key symbols in `mockup_discover_geology.html`: module-scope `addOcean`/`makeShard`/`makeBedrock` + generalized `layout(list, poleKey)` (lays out needs OR clusters; `unsettled` at the pole in needs mode, both poles neutral in query mode), `reconstitute(q)`, `restoreNeeds()`, `searchAPI()` (bridges to `window.parent.__scoreAll/__clusterSignals/DATA`), `dominantNeed()`, `setModeMeta()`. `buildLabels` clears `#labels` first; `buildLegend` builds from the live `territories` array; territory items are `t.item` (a need OR a cluster). Verified via `node --check` + `build_geology.py`; the WebGL render path itself was not runtime-verified (no browser in the Cowork build env).

**"SEE THE WHOLE UNIVERSE" TOGGLE (Task 4, 2026-07-02).** A link under the globe masthead description → `window.parent.__enterUniverse()` (in `template.html`) swaps the geology iframe for the universe iframe (lazy `src`); `window.parent.__exitUniverse()` (and a "← Back to the sphere" link inside the universe page) returns. Each view keeps its OWN search (globe reconstitution vs the constellation's `#exq` query gravity), by design.
- The old constellation code was NOT in git (the geology swap replaced `__initExplore` before the repo existed). It was **recovered from the pre-swap Cloudflare snapshot `https://0874143d.cultural-scout.pages.dev/#explore`** (its 3rd inline `<script>` = the module: `__initExplore`/`enterPlanet`/`buildInterior`/query-gravity/3D fly-in).
- `mockup_discover_universe.html` is a **standalone iframe page**: it carries the snapshot's own Explore markup (`#view-explore`, `#panel`) + styles + the module verbatim, and a **shim mirrors the parent's globals** (`window.parent.DATA/NEEDS/NEED_LIGHT/RUNS/__scoreAll/__clusterSignals`) onto its own window so the module runs unmodified. A hidden `#q` covers the module's `#q` reads. So it always reflects the live corpus, no data duplication, no build injection.
- **Recovery caveat for future work:** the Cowork browser tool's content scanner refuses to exfiltrate that module (flags it as query-string/base64 data), so the universe page had to be assembled in Claude Code (which can `curl` the snapshot). If it ever needs re-recovering, do it there.

**SEMANTIC-RANGE MATRIX / "DIVERGENCE SURFACE" (Task 5, 2026-07-02).** Each need's callout (the deep stratum, `#t-range`) now shows a small non-interactive inline-SVG scatter of the theme's internal semantic range. The need's signals are broken into the SAME lexical clusters as the universe/search view (cosine k-means, `kFor(n)` = 2–5 by size, TF-IDF labels) and plotted on the need's TWO DOMINANT PCA directions. Crucially the axes are NOT the raw cluster terms — they are **hand-interpreted bipolar labels** in `semantic_axes.json` (a deliberate rigor-for-legibility trade, Michael's call 2026-07-02: distil each axis to something as simple as "exclusive↔inclusive"). Each theme gets its OWN two axes.
- Files: **`build_semantic_range.py`** — `svgs_by_need(colors)` -> `{need: SVG}` (imported by build_geology.py, which injects `needs[].range`); `--poles "<need>"` dumps the signals at each pole for interpretation; `--preview "<need>"` writes one SVG. **`semantic_axes.json`** — the curated axes, persists across rebuilds like `geology_codes.json`. `mockup_discover_geology.html` renders `nd.range` in the callout's deep stratum (needs mode only; hidden for query-themes). New runtime dep: **numpy** (added to requirements.txt; build_geology degrades gracefully to no-range if it's missing).
- The interpreted axes (x = PC1 low→high, y = PC2 low→high): Naming the Machine [Political↔Economic / Infrastructure↔Spectacle]; Settling Accounts [Aesthetic↔Historical / Judgment↔Heritage]; Self-Authorship [Artist↔Algorithm / Roots↔Fame]; Certified Human [Object↔Discourse / Craft↔Slop]; Kinship [Intimate↔Institutional / Collaboration↔Courtship]; Appetite [Diet↔Desire / Food↔Form]; Ballast [Sanctuary↔Survival / Comfort↔Defiance]; unsettled [Object↔Narrative / Art↔Tech].
- **RECOMPUTE EACH HARVEST (required):** PCA sign/structure shifts as the corpus grows, so the labels can go stale or flip. After tagging, for each need run `python build_semantic_range.py --poles "<need>"`, re-read the pole signals, update the label pairs in `semantic_axes.json` (bump `_generated_against`), then rebuild. Cluster geometry regenerates automatically from corpus.json each build; only the axis *labels* are the manual step. PC variance is inherently low (~5–9%) — the axes are directional summaries; the cluster separation is the trustworthy read. WebGL render path not runtime-verified in the Cowork build env.

**GITHUB (Task 10, 2026-07-02).** Project is now a git repo pushed to a private GitHub `cultural-scout` (rollback point). `.emb_cache.npz` is intentionally tracked (expensive to regenerate on the firewalled build machine); `.venv/`, `__pycache__/`, `.wrangler/` are ignored. Normal flow now: `git add -A && git commit && git push`.

## Monthly run procedure
When the user says something like "run the monthly cultural harvest" or "activate the cultural thought starter system":

### Phase 0: Layer 1 — Harvest
For each source in `sources.yaml` where `fetchable` is not `false`:
1. `WebSearch` scoped to the source's domain. Use 1-3 queries per source — vary by date range or content type if needed. Bias toward recent profiles, criticism, essays, interviews, features. Drop announcements, listicles, sponsored posts, and product roundups UNLESS the source is fundamentally a product-roundup publication (Strategist, Thingtesting).
2. For each item kept: title, full article URL (not homepage), publication date (YYYY-MM-DD if known, else best estimate flagged), 1-3 sentence specific summary.
3. Dedup by URL.

**Distinctiveness gate (the primary keep-criterion, added 2026-06-25).** The bake-off (Rounds 3-4) settled what this corpus is for: it is a DISCOVERY engine, and its only durable edge over open web search is the below-radar layer open search buries. So the keep-test is distinctiveness, NOT volume and NOT mere competence. Keep a signal only if it carries one of: a named coinage (QTBAT, tasteslop, the "Botox Psyop" were the irreplaceable layer in Round 3), a single-writer observation or argument that isn't the dominant discourse, or a reframe that open web search would not surface near the top. If a competent strategist with a search engine would find the same item in five minutes, DROP IT, even from a strong source. Most corpus signals already go unused downstream, so erring toward dropping the easily-findable costs almost nothing and sharpens what remains. The old worry was thin coverage; the real risk is dilution by findable-but-undistinctive items.

**Summary quality bar.** Specific and grounded. "A profile of a Brooklyn-based ceramicist who makes funeral urns shaped like household objects" is good. "An article about contemporary art" is not. If the search snippet doesn't give enough to write a specific summary, drop the item. A summary that could describe a generic trend-deck slide is a sign the underlying item probably fails the distinctiveness gate too.

**Output schema** (`signals.json`):
```json
{
  "harvest_date": "YYYY-MM-DD",
  "model": "claude-code:WebSearch",
  "date_range_days": 90,
  "sources_harvested": ["..."],
  "per_source_counts": {"source_name": 12},
  "signals": [
    {"id": "{slug}_{YYYY_MM_DD}_{NNN}", "source": "...", "title": "...", "url": "...", "date": "...", "summary": "..."}
  ]
}
```

**Validation gate (user inspects before Phase 1):**
- Summaries specific, not generic.
- Every kept item passes the distinctiveness gate above (coinage, single-writer observation, or buried reframe). Findable-but-undistinctive items should already be gone.
- Items actually within last 30-90 days. Older items mean the source's recent-content surface is wrong.
- As many distinctive items as the source yields, quality over count. There is no density target. A strong source might give two keepers or twelve; both are fine. A near-zero return usually means the URL/method is wrong, not that the bar is too high; ~80 means dedup is broken. Do NOT pad a source's count with competent-but-findable items to hit a number.
- Failure to pass = fix sources.yaml or harvest method, re-run, re-inspect. Do NOT proceed.

### Phase 1: Layer 2 — Tag (DO NOT BUILD UNTIL PHASE 0 GATE PASSES)
Per Layer 2 spec in v1.1 doc. Output: `tagged_signals.json`. Validation gate: do substrate tags feel correct, do forward-looking flags select genuinely interesting items, no source dominating one substrate.

**Distinctiveness carries into tagging.** Anything that slipped past Phase 0 but is on re-read just competent-and-findable should be dropped at the tagging step, not tagged. Tagging is the second chance to enforce the distinctiveness gate, not a rubber stamp.

**Theme-gravity balance gate (added 2026-06-25).** The corpus has a known theme-gravity problem: Rounds 1-2 of the bake-off showed it reaches for the same template (provenance / made-by-humans / anti-AI / friction-as-proof) across unrelated questions, which narrows the aperture on open reasoning. Counter it at the tagging step.
- **Soft per-need ceiling ~20% of a run's kept signals.** When a need crosses roughly 20% of the run, tighten its keep-bar: that need now only takes items that are clearly distinctive AND unambiguously that need, not items that merely lean toward it. The ceiling is a discipline trigger, not a hard cap; the point is to stop one need swallowing the run.
- **Naming the Machine specifically.** It sits at ~23-24% corpus-wide and is genre-flattered by the source mix (Zitron/Lorenz/JSTOR/system-diagnosis sources feed it). Keep an item under Naming the Machine ONLY if the payload IS the unmasking, the article's actual work is exposing how a system/machine/incentive operates. Merely being tech-adjacent, AI-mentioning, or platform-set is not enough; tag those to the need the human stakes actually sit in.
- **The provenance / anti-AI / humanness cluster (Certified Human and its neighbours).** Same discipline. The bake-off named this the corpus's most over-used frame. Keep an item here only if made-by-humans / verifiable-provenance / friction-as-proof is the genuine center of gravity, not a reflexive tag for anything craft-shaped or anti-AI in tone.
- After tagging, eyeball the per-need shares (build_corpus.py --stats now prints them with an over-20% warning) and re-balance before the corpus rebuild if any need is bloated.

### Phase 2: Layer 3 — Generate (DO NOT BUILD UNTIL PHASE 1 GATE PASSES)
Per Layer 3 spec in v1.1 doc. Output: `brief_<category>.md`. Validation gate: would these thought starters change the next brief the strategist wrote?

### Phase 3: Hardening (optional, post-validation)
Previous-run cache for month-over-month signal drift. UI is unnecessary; markdown is sufficient.

## PULSE + RECEIPTS + PROVENANCE + DIGEST (added 2026-06-12, whitespace-report Tier 1 build)
Built from the category-landscape research (report in that session's outputs): the category's whitespace is VERIFIABILITY, not earliness — these four features productize the one-strike discipline. Site keeps THREE tabs (Search / Explore / Vital Signs); Receipts is NOT a tab (user call 2026-06-12: "doesn't need a whole tab") — it is a **small footer at the bottom of the Search tab** (one-strike line + "Methodology & scorecard →") that opens a **modal**; old #receipts deep-links still open it.
- **PULSE CHART (Search tab headline):** need-share per harvest, every need as a colored line (unsettled dashed), end-labels with latest %, per-point tooltips, "Copy data" button that emits shares WITH run caveats. Data = `need_history` in corpus.json, computed by build_corpus.py from each run's OWN tagged file (not the deduped corpus). **GATED: renders only at 3+ harvest runs** (two points are a line, not a signal — the gate is in the template, don't remove it). **RUN_NOTES dict at the top of build_corpus.py** holds dated intake-change caveats that render under the chart (2026-06-11 entry exists: source expansion); add a note whenever intake changes for non-cultural reasons (harvest task step 6 covers this).
- **RECEIPTS (footer + modal):** public methodology + accountability content rendered from **`receipts.json`** (intro, 6 principles incl. the one-strike rule, grading_method, scorecard). Scorecard entries schema: {title, called, graded, verdict: matured|building|faded|wrong, what_happened}. Currently honestly EMPTY; **inaugural grading at the Q3 2026 indicator refresh** — at each quarterly refresh, re-read a sample of past tier-core signals, grade them, append entries (published as made, never edited after the fact). NEVER grade the scorecard in the unsupervised monthly task.
- **PROVENANCE BLOCK (top of Field Guide):** editorial-intake breakdown (discipline x region bars + summary line citing Klein's META Trends 10-cities finding). Data = **`provenance.json`** (name → {region, independent}); sources.yaml stays canonical and UNTOUCHED per house rule. Region = editorial center of gravity, best effort; uncertain → "Online (unplaced)" (12 currently) — never guess a region. When sources are added to sources.yaml, add matching provenance.json entries.
- **MONTHLY DIGEST (Michael ONLY, in refinement):** harvest task step 9 creates a GMAIL DRAFT (create_draft, never send) to aroney@sylvain.co — "5 signals that would change your next brief" + pulse delta with caveats + state-of-play line. Sample/format agreed 2026-06-12 (in that session's transcript). Do NOT widen distribution without Michael's explicit approval.
- build_site.py now also injects NEEDHIST + RECEIPTS markers and joins provenance.json regions onto SOURCES. Smoke-tested via jsdom 2026-06-12 (pulse 8 series, receipts render, prov render, #receipts deep-link, search/vitals regressions clean). Deploy = ./publish.sh as always (NOT yet deployed as of the build).

## IMAGE SCRAPER + CONTACT-SHEET ANALYSIS (2026-07-02)
The `image_scraper/` subsystem replaces the pilot's expensive collection method (Fable driving browser screenshots per article) with free scripted extraction. **Decision (Michael 2026-07-02):** collection is scripted; analysis stays with Fable reading 12-up contact sheets (one look covers 12 images). Sonnet/Haiku delegation for the visual read was considered and rejected.
- **URL-FED EXTRACTOR, NOT A CRAWLER (hard design rule).** Input = article URLs from corpus.json filtered by `--need` (round 1) or a `--urls file.txt` of WebSearch-found URLs (round 2). No homepage crawling, no per-site CSS selector configs — corpus.json already IS the themed article list. Do not resurrect the crawler idea.
- **Files:** `image_scraper/run.py` (CLI: `scrape` / `sheets` / `clean`; corpus selection ordered core→forward-looking→recent per the codebook sampling bias; seen_urls.json cross-run dedup ledger with `--force`), `extractor.py` (httpx+trafilatura static fetch with retries, Playwright fallback for JS pages, paywall detection that records failed and NEVER defeats walls, per-domain rate limit, junk-image filtering, srcset highest-res picking, caption+context capture, variant-aware image dedup), `sheets.py` (temp cache with 2MB/image cap + numbered 12-up contact sheets + per-sheet sidecar JSON mapping number → image URL/article/source/alt/caption — the sidecar is how visual readings trace back to sources). `README.md` = plain-English ops; **`SEMIOTIC_IMAGE_HARVEST.md`** = the two-round orchestration playbook (scrape → sheets → Fable codes per SEMIOTIC_CODEBOOK.md → WebSearch gap-fill toward ~20 distinct-source images per code → round-2 scrape → clean).
- **COPYRIGHT RULE AMENDED (Michael 2026-07-02):** downloading images to `image_scraper/.cache/` is now ALLOWED for analysis only — temporary artifact, deleted by `run.py clean`, never committed (root `.gitignore` blocks `.cache/`, `sheets/`, `output/`, `logs/`, `seen_urls.json`), never in `site/` or deliverables. Publishing is UNCHANGED: codes reference imagery only as live hotlinks (the existing `image_refs` mechanism). Stress-tested 2026-07-02: US hotlinking safe (server test); EU embedding murkier — the existing re-assess-before-client-facing-deploy flag covers it; paywalled sources are skipped, never defeated.
- **Verified 2026-07-02:** 34/34 offline tests pass (`image_scraper/tests/run_tests.py` — extraction/srcset/caption/junk-filter/dedup fixtures, paywall + Playwright-fallback decisions, corpus selection incl. --days/--run/homepage-skip, contact-sheet builder with generated placeholders). One real bug found+fixed in review: same photo at different resolutions (srcset-upgraded vs plain src) now dedupes via variant tracking. NOT live-tested against real publishers (build-env network is firewalled) — first real run is on Michael's machine: `cd image_scraper && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install chromium && python run.py scrape --need "Certified Human"`.
- **FIRST LIVE RUN 2026-07-02 (Certified Human round 1):** 40/40 URLs fetched (static 34, playwright 6), **1064 images extracted, 0 hard `failed`** — better than predicted. No code changes needed; setup + both commands ran clean on Python 3.9.6. Fetch-method learnings, all worth encoding for future rounds:
  - **`dezeen.com` is playwright-REQUIRED**: static 403s every time (3/3 articles), Playwright fallback recovers cleanly (~10 imgs each). Mark it like the ArtReview/Juxtapoz JS-tier.
  - **The Met did NOT hard-fail** as the bot-challenge notes predicted — Playwright returned a real title + 1 image (thin, but not `failed`). Still low-yield; browser-screenshot fallback remains better for Met imagery.
  - **Paywalled newsletters (snaxshot, thehunger) did NOT trip `failed`** — static returned 1–2 public preview/og images each. The scraper takes the freely-served preview image, which is NOT defeating the wall; just expect thin yield, not a failure log.
  - **Newsletter/Substack tier stays text-heavy, 1–2 imgs each** (honest-broker, samkriss, kneelingbus, robhorning, maxread, kylechayka, embedded, usermag, aliciakennedy) — confirms the pilot note "newsletters carry the ARGUMENT, magazines/galleries carry the IMAGERY."
  - **`popmatters.com` body still image-free** (Playwright, 0 imgs) — confirms the 2026-06-12 note.
  - **`arts.ac.uk` CSM whats-on URL is stale/dead**: static 403 → Playwright hit a "Page Not Found" page, 0 imgs. Corpus URL likely expired (`/whats-on/csm-shows-2026`).
  - **NEW PATTERN — gallery / grad-show pages flood the corpus.** `1granary.com`'s CSM BA Fashion 2026 page dumped its **entire 853-photo runway gallery** (all unique full-res, correctly passing the junk filter) = 80% of the whole run's 1064 images. There is no per-article cap in the (locked) extractor; for round 1 it was capped MANUALLY to 15 representative photos by trimming that article in a COPY of the output JSON (`output/*_capped.json`), leaving extractor.py untouched. **If gallery-flood recurs in round 2, add a `--max-per-article` flag to `run.py sheets` rather than hand-trimming.** Image-rich non-gallery sources this run: radii 25, sightunseen/thisiscolossal/impulse 18, culturedmag 17, sixthtone 11, hyperallergic 9.
  - **Sheets:** built from the capped input (226 imgs) → 192 cached / 30 skipped (broken/oversized/hostile — normal) → **16 contact sheets** in `image_scraper/sheets/`. Sheets kept (no `clean`) for the separate analysis/coding session. Note: one 1granary photo tripped Pillow's `DecompressionBombWarning` (144MP) — warning only, handled fine.

## SEMIOTIC CODES — pilot (2026-06-12, Certified Human)
Goal: per-need look-and-feel codes, lightly updated each run, trajectory over time; eventual "Explore look & feel" fly-in per need-sun. **Pilot only so far — gate not yet passed.**
- **`SEMIOTIC_CODEBOOK.md`** is the discipline doc: code definition, residual/dominant/emergent status (Williams), STABLE-ID update rules (append evidence / move status / propose / retire — never rewrite), evidence standards. READ IT before any coding work.
- **`codes_certified_human.json`** — 5 codes (provenance-ledger, countable-labor, unretouched-witness dominant; slop-repainted-slow emergent; analog-sanctuary residual) from 83 images / 27 articles / 14 texts across all 3 runs. Method: 2 visual passes via Claude-in-Chrome screenshots (batch 2 run adversarially vs batch 1 candidates) + 1 verbal pass via web_fetch.
- **COPYRIGHT RULE (hard):** never store or copy harvested images into project files. Codes render as derived artifacts (swatches, descriptors, ≤15-word attributed quotes, evidence links) PLUS **hotlinked evidence collages** (user call 2026-06-12: palette alone "nowhere near useful enough"): `image_refs` in the codes JSON are live embeds from the publishers' own servers, credited, click-through, `referrerpolicy=no-referrer`, broken links self-hide. Acceptable for internal gate review; RE-ASSESS before any public/client-facing deploy. Image viewing for analysis: contact sheets via `image_scraper/` (temp-cache amendment 2026-07-02, see section above); browser screenshots remain the fallback for bot-hostile sources.
- **`codes_preview_certified_human.html`** — flat prototype panel (built from codes_preview_template.html + the JSON; NOT deployed, not in site/). **GATE PASSED 2026-06-12** ("this is good for now"); scale to the other 7 needs deferred to a later session.
- **3D FLY-IN (built 2026-06-12, Certified Human only):** build_site.py auto-discovers `codes_*.json` → CODES marker keyed by need. In Explore: need-suns with codes get an "Explore look & feel →" button in their theme panel → camera dives into the sun → warp overlay → interior scene at INT_C(0,-640,0): core sun + one "code moon" per code (colored via codeColor() saturation pick from its observed palette) with palette-swatch satellites orbiting it; click a moon → full code board in the side panel (hotlinked collage, swatches, registers, quotes, tensions, execution, evidence, trajectory). Esc/back button exits. Deep link: `#explore&lookfeel=Certified%20Human`. Key module symbols: enterPlanet/exitPlanet/buildInterior/animateInterior/codeAt/openCodePanel, window.__enterPlanet, flyPhase/interior state; constellation hidden via setConstellationVisible. When new codes_<need>.json files are added, the button appears automatically. Syntax-checked + jsdom-regressed 2026-06-12; WebGL path verified live post-deploy.
- Image fetch learnings: backrow.net hard-gates some posts; snaxshot/thehunger paid-gate; avclub lazy-load fails; popmatters body is image-free. Newsletter tier carries the ARGUMENT in text, magazines/gallery blogs carry the IMAGERY.

## VITAL SIGNS — third site tab (added 2026-06-11)
The site now has THREE tabs: Search / Explore / **Vital Signs** (#vitals). Vital Signs is the "cockpit to the telescope": a macro instrument panel of **17 indicator tiles** (Edelman Trust, Gallup emotions + institutions, Pew trust-in-gov, World Happiness, US-position, WUI, Michigan sentiment, OECD CPI + unemployment, Eurostat ESI, Purdue CFDAS food, HDI, SPI, WVS trust, ESS trust, Eurobarometer mental health) + a **98-source Field Guide** (annotated armory: datasets/think-tanks/consulting/tools, gated flags). Deliberately SOBER — no universe metaphor here (full rationale in the 2026-06-11 session's hard-edge-corpus-thinking.md): evidence needs trust-affect, not wonder.
- Data lives in **`vital_signs.json`** (indicators + fieldguide + pulled date), injected by build_site.py via the VITALS marker. UI: sparkline tiles (when series data exists), per-tile cadence chip + "as of" date, click → citation card with verbatim source quote + deck-ready citation + copy button; local filter input (matches names/measures/synonyms, also filters the Field Guide); Copy for AI emits values WITH citations.
- **ACCURACY IS ONE-STRIKE.** Tiles show verbatim values with source quotes; anything not verified directly carries confidence:"low" and renders a "verify" badge (currently: wui — Q1 2026 only in unparseable xlsx; cfdas_food — Jan 2026 latest retrievable). NEVER write a value into vital_signs.json that wasn't read from a fetched source; when in doubt, null value + low confidence.
- **REFRESH PROCEDURE** (user-triggered, ~quarterly, or when a flagship release drops): re-run the 3-lane indicator pull (trust/emotion, econ/uncertainty, development/values — agent prompts in session 2026-06-11), validate verbatim values, update vital_signs.json, python3 build_site.py, deploy. Monthly cadences (Michigan, OECD CPI/unemployment, ESI) go stale fastest. NOT yet part of the scheduled monthly harvest task — fold in only with the one-strike rule embedded.
- **STATE-OF-PLAY BRIEF (added 2026-06-11):** `vital_signs.json.world_summary` {updated, text} renders at the top of the Field Guide ("The state of play · according to the sources"). REPLACED each monthly scheduled run (step 5 of the monthly-cultural-harvest task): synthesized from current indicator values (no re-pulling) + the month's strongest macro-relevant harvest signals; 2-3 sober paragraphs ending in a one-line strategist's read.
- **PULL HISTORY (added 2026-06-11):** every indicator carries `pull_history` [{pulled, value}]. On refresh, APPEND the new {pulled, value} — never overwrite the array. Tiles whose value differs between the two latest pulls render a blue "changed" chip; the detail card lists the last 6 pulls. 2026-06-11 user edits: cfdas_food tile removed; Kantar BrandZ + Purdue CFDAS removed from the field guide (16 tiles, 96 field guide sources now).

## HARVEST RUN 2026-06-11 — new-source expansion run, corpus 400 → 713
First harvest of the 54 expansion sources, window 2026-04-10..2026-06-11. **317 harvested → 313 kept** (4 drops: listicles/digests) → `tagged_signals_2026_06_11.json` (tagged directly into 7-need taxonomy + legacy substrate, per-signal novelty/cross notes, strict forward gate: 135 forward, 80 core). Raw harvest archived as `signals_2026_06_11_new_sources.json`. 51/54 sources productive; verified-quiet in window (NOT fetch failures): ageofrevolutions.com, ageofinvention.xyz, theconvivialsociety.substack.com.
- **Fetch-method learnings for next run:** Substack /archive pages often serve stale caches — the JSON API (`/api/v1/archive?sort=new`) is authoritative (this is how jessicadefino was confirmed ACTIVE through June, clearing the pause suspicion; neverworns works via `/archive?sort=new`). historyworkshop.org.uk blocks direct fetch — harvested via its Bluesky feed API. daily.jstor.org works via WordPress REST API (`?categories=4&_embed`). radii.co /article/ index empty — use homepage + per-article fetches. shesabeast.co /archive empty — use homepage. beehiiv archives (aliciakennedy) only render ~10 newest posts — per-article fetch for older. artreview.com category pages are Gatsby JS — use landing-page modules + search.
- **Corpus after merge: 713 signals, 3 runs.** Need distribution: Naming the Machine 24%, Settling Accounts 22%, Self-Authorship 12%, Certified Human 12%, Kinship 11%, Appetite 7%, Ballast 7%, unsettled 4%. **THE PREDICTED SKEW HAPPENED:** Naming the Machine rose 18%→24% (Zitron/Lorenz/JSTOR/system-diagnosis sources feed it, as flagged). Watch next run; if it keeps climbing, tighten its tagging gate (payload must BE the unmasking) or consider splitting it.
- New-run category mix is healthily non-US: global 89 + history 50 = 44% of the new signals.

## MUSEUM WAVE 2026-06-22 — list grew 118 → 131 (NEW `museum` category)
User added 13 art INSTITUTIONS (not editorial publications) for the institutional-VALIDATION signal (what the art world is canonizing), a more VISUAL register than the newsletter tier, and deliberate non-Western coverage. New primary category **`museum`**. Because institutions ≠ publications, each museum entry carries TWO harvest targets: `recent_url` (editorial arm — magazine/essays) AND a new **`exhibitions_url`** field (current + upcoming shows). Full per-entry harvest rules live in the "MUSEUM WAVE 2026-06-22" header block inside sources.yaml; provenance.json got 12 matching entries (all `independent:false`; regions US/UK/Europe/Australia/Latin America/Hong Kong/MENA/Southeast Asia/Africa).
- **The 8 named:** the-met, whitney, moma (NYC); tate-modern, tate-britain (London — share the Tate Etc. editorial, deduped by URL); centre-pompidou (Paris, has an EN edition); white-rabbit (Sydney, EXHIBITION-ONLY, Chinese contemporary); masp (São Paulo — the exhibition pages ARE the editorial, 450-500 words curatorial prose each).
- **The 5 suggested adds (Claude's picks + Serpentine, user-approved 2026-06-22 — non-Western balance + one tech-art lane):** mplus (Hong Kong), sharjah-art-foundation (UAE), national-gallery-singapore, zeitz-mocaa (Cape Town), serpentine (London — Art + Ideas / Future Art Ecosystems). Documented runner-up if more wanted: Singapore Art Museum/SAM (sharper contemporary editorial).
- **HARVEST-RULE EXCEPTION (important):** exhibition/programming pages ARE announcements — and that is the point (a show going up at the Met/Tate/M+ IS the validation signal). Treat them like the Strategist/Thingtesting exception: the announcement is the editorial product. Capture title/venue/date-range/artists/curatorial framing; skip pure logistics (hours, ticketing, galas).
- **Fetchability (verified 2026-06-22):** GREEN = whitney, tate-modern, tate-britain, centre-pompidou, mplus, sharjah, ngs, zeitz, serpentine. YELLOW = moma (www 403s + magazine bodies JS-rendered → use press.moma.org + domain-scoped search), masp (masp.org.br vs masp.com.br cross-host redirect hazard → pin to /en/, follow redirects). RED = the-met (Vercel bot-challenge 429, dead press subdomain, NO fallback → search-grounding only, same as nymag/eater). White Rabbit: correct domain is whiterabbitCOLLECTION.org (whiterabbitGALLERIES.org is an unrelated Ohio community center — do NOT harvest it).
- **NEXT MONTHLY RUN must:** (1) add a RUN_NOTES entry in build_corpus.py when museums first ingest (non-cultural intake change → caveat renders under the pulse chart); (2) add parallel agent(s) for the museum category (workload grew); (3) apply the announcement-exception above; (4) tag `need` as usual — expect museums to feed Certified Human (material/visual authenticity), Settling Accounts (decolonial/restitution shows), and Naming the Machine (art×tech). Site/corpus NOT yet rebuilt — museums carry 0 signals until the first harvest; `python build_corpus.py` + `./publish.sh` will surface them in the Field Guide.

## HARVEST RUN 2026-06-22 — first museum-wave ingest, corpus 713 → 849
Window **2026-06-01..2026-06-22** (per user steer: the 06-11 run was effectively just the history/expansion sources, so the bulk of the list was last harvested at the 06-01 monthly run — used the wider window; museum **exhibition** arms are window-exempt, capturing current/upcoming shows per the museum-wave rules). Run triggered manually by Michael (not the last Friday; he asked to run it anyway), explicitly against the latest list incl. the 13 museum additions.
- **162 raw harvested → 158 unique (URL dedup) → 155 kept after tagging** (3 dropped as non-signals: 2 event-logistics / branding-credit items, 1 out-of-window promo). Raw archived `signals_2026_06_22.json`; tagged `tagged_signals_2026_06_22.json` (tagging_date 2026-06-22). 11 lanes.
- **Museum lane (NEW) = 31 signals across all 13 institutions.** Exhibition arms carried it (announcement-exception applied); editorial arms (Met Perspectives, M+/MoMA Magazine, Tate Etc) thinner/older. Fetchability confirmed: the-met RED (search-grounding only, as predicted), moma via press.moma.org, all others GREEN. Museum need mix skewed Settling Accounts (9) + Certified Human (6) + Kinship (4) as predicted; only 2 Naming the Machine.
- **Need distribution THIS run:** Settling Accounts 22%, Naming the Machine 19%, Certified Human 15%, unsettled 13%, Self-Authorship 12%, Kinship 11%, Appetite 5%, Ballast 3%.
- **Corpus after merge: 849 signals, 4 runs, 131 sources.** Corpus need dist: Naming the Machine 23%, Settling Accounts 22%, Certified Human 12%, Self-Authorship 12%, Kinship 11%, Appetite 7%, Ballast 6%, unsettled 6.1%.
- **THE NtM SKEW EASED:** Naming the Machine fell 31% (06-11 run) → 19% this run as the museum/global/consumer lanes diluted it; corpus NtM 24% → 23%. Still near the ceiling — keep the tagging gate tight (payload must BE the unmasking).
- **WATCH — unsettled spiked to 13% this run** (corpus-wide still 6.1%, gate OK). Driver is the **more-than-human / ecology cluster** the taxonomy flagged as the candidate category 8: Whitney Biennial 'interspecies kinships', CSM 'more-than-human future', M+ Zheng Mahler, NGS 'When Art Meets Nature', plus a few pure film/album reviews. If it keeps growing next run, promote ecology to need #8 rather than letting unsettled bloat.
- **Verified-quiet in window (NOT fetch failures):** jessicadefino (PAUSED since Mar 29), readmax (moved to Patreon mid-May), robhorning (migrating off Substack), etymology, internetanthropologists, default.blog, kneelingbus, escapethealgorithm, ageofrevolutions, ageofinvention, theconvivialsociety (partial), 032c, apartamento, thehunger, virginiasolesmith, shesabeast, late-review, sixthtone, chineseconsumers, mekongreview, readcommunique, avenuesofamericas, natashastagg, neverworns, family.style, unconditionalmagazine, pattaclothing.
- **Fetch-method confirmations:** artreview per-article pages work (category pages JS-render empty, as noted); juxtapoz JS-rendered (couldn't confirm in-window dates → 0); RISD Grad Show 2026 ran May 21-30 (pre-window) — real grad URL is risdgrad.show for future runs. Subagent caveat this run: the Substack `/api/v1/archive?sort=new` JSON endpoint is NOT directly reachable inside subagents (WebFetch URL-provenance rule) — workaround was domain-scoped WebSearch to discover URLs, then WebFetch to confirm `article:published_time`.
- **sources.yaml: NO fetchability changes** — nothing confirmed dead this run (artforecast.substack.com is stale at Dec 2025 but on a slow cadence, left as-is per house rule).
- **Execution note:** the org monthly spend cap interrupted the parallel agents twice mid-run. The museum lane and the chunk-4/5 tagging were completed directly by the main session as a fallback; entertainment/design_school/intellectual lanes and chunks 1-3 tagging were agent-produced before the cap. Output schema identical.

### ADDENDUM 2026-06-26 — Paris Review + NER late-added to the 06-22 run (corpus 849 → 858)
Michael added two literary sources (theparisreview.org, nereview.com — both `intellectual`, see sources.yaml + provenance.json entries) and asked to harvest just those two and FOLD them into the 2026-06-22 run rather than open a new run (keeps run count at 4, need_history clean). Interactive harvest (no API), via WebFetch of the PR Daily index + NER homepage.
- **PR: 6 surfaced → 5 kept** (dropped the "Announcing Our Summer Issue" letter as an announcement per the new PR harvest rule). Keepers: Carver "Mudder/Lawyer/Prince" (Appetite), Tao Lin "Taiwan English" (unsettled), Williams "Three Horses" (unsettled, more-than-human cluster), Prakash "Drinking Movies" (Ballast), Piette "Making of a Poem" (Self-Authorship).
- **NER: kept 6** (dropped the reading roundup, the alumni-reading event, and an undistinctive "memory/intimacy" Behind-the-Byline per the distinctiveness gate). Keepers: Khouri "Speaking Our Palestine" (Settling Accounts), Lobato "Brazilian Badlands" editor's note (Self-Authorship — tagged here NOT Settling Accounts under the near-ceiling discipline, since the framing is living self-definition not mourning), Oswald "Writer's Notebook" (Self-Authorship), Lee "Behind the Byline" (Appetite — mukbang/AYCE), **plus the 2 creative pieces Michael asked to keep (2026-06-26), overriding the default fiction/poetry drop:** Silver "The Children's Museum" (fiction → unsettled; self mythologized around a near-kidnapping) and Cruz "The Riddle of the Modern World" (poetry, after Frank Stanford → Ballast; mortality/illness in a pastoral dream-register). NER dates are `(approx)` (issue-level, no per-article date on page). NB house default still drops fiction/poetry; this was an explicit per-source override for NER, not a policy change.
- **11 added → tagged_signals_2026_06_22.json now 166, raw signals_2026_06_22.json 169; corpus 860, 133 sources.** New-signal need mix deliberately steered AWAY from the two over-ceiling needs: Self-Authorship 3, unsettled 3, Appetite 2, Ballast 2, Settling Accounts 1, Naming the Machine 0, Certified Human 0.
- **EMBEDDINGS / Tier-2 caveat (important for next run):** this machine has NO embedding backend and the HF model hosts are firewalled, so the 11 new signals could NOT be embedded. Rather than fabricate vectors (forbidden) or drop the whole corpus's vectors, **embed.py was changed to degrade PER SIGNAL**: it now keeps every signal already in `.emb_cache.npz` (849) and lets only brand-new uncached signals ship WITHOUT a `vec` (assembly uses `have = signals with a cached vec`; PCA/meta computed over that subset; a `skipped` count is logged). Site rebuilt WITH vectors (849 vec'd, 11 vec-less; ~1236 KB). Consequence: the 11 new signals are fully searchable and show as cards, but are excluded from Explore/Search semantic CLUSTERING until embedded. **TO FINISH:** run `python3 build_corpus.py --require-embeddings` (or a plain `build_corpus.py`) on a Hugging-Face-reachable machine; it will embed the 11 from cache-miss and they'll join clustering. jsdom after the change: clustering still returns ≥2 themes, `__clusterSignals` is crash-safe when the matched set includes vec-less signals, PR/NER signals are findable; the only "failing" assertions are the two expected artifacts (unsorted-input label compare; partition test, which now under-counts precisely because vec-less matches are correctly excluded). NOT deployed.

## SOURCE EXPANSION 2026-06-10 — list grew 64 → 118
54 new sources added in one wave (user explicitly chose volume over phased adoption). Two NEW categories: **history** (9 sources — how established historical narratives are being reconceived; deliberately upstream of the Settling Accounts need) and **global** (13 sources — culture written from inside non-Western regions; The Juggernaut lane). Remainder spread across consumer/internet/entertainment/fashion/embodied/intellectual/art. All verified active-in-2026 by four research agents (most via direct archive fetch); full research notes in the session's harvest-source-candidates.md.
**Implications for the next monthly run:**
- Harvest workload roughly doubles — plan more parallel category agents (8 → ~14) or a longer run.
- Per-entry HARVEST RULES are in each source's note in sources.yaml (essays-not-roundups for dailies, Ghost/beehiiv pagination checks, JS-fetch workarounds, paywall caveats for thejuggernaut.com headline-level harvesting, scoping rules for milleworld/jstor).
- First run with new sources = treat as a validation batch: expect several fetchability corrections, same as Batches 1-3.
- WATCH CORPUS BALANCE: Naming the Machine is already genre-flattered (18%); Zitron/Lorenz/JSTOR feed it further. Also watch US-newsletter-voice share vs the new global/history lanes; check `python build_corpus.py --stats` distribution after tagging.

## Source list status (as of 2026-04-28, after Batches 1+2+3)
- 47 sources total; **40 fetchable** after small-batch validation across three batches.
- 7 marked `fetchable: false`:
  - `heroine_mag (instagram)` — Instagram crawl blocked.
  - `notes_on_beauty_ (instagram)` — Instagram crawl blocked.
  - `thisismold.com` — DEFUNCT, ceased publication 2025-06-20.
  - `holiday-magazine.com` — print-only portfolio site, no dated online articles.
  - `pitchfork.com` — HARD BLOCKED at user-agent level by Anthropic's web tooling. **Outlier: other 4 entertainment sources tested (Variety/Slate/AV Club/IndieWire) all fetch cleanly.**
  - `thingtesting.com` — 403 to WebFetch; WebSearch surfaces only brand directory.
  - `dailydot.com` — flagged but not unfetchable: technically works but content register fails quality bar (clickbait, not analysis).
- URL fixes applied: `etymologynerd.com` → `etymology.substack.com`; `pinupmagazine.org` → `pinuphome.com`; `vittles.substack.com` → `vittlesmagazine.com`; `pratt.edu` recent_url → `/prattfolio/`.
- 6 sources still flagged `recent_url_uncertain: true`: `impulsemagazine.com`, `unconditionalmagazine.com`, `letiquette.com`, `readafm.com`, `slate.com` (works but very broad), plus the two remaining design schools (CSM, RISD).
- **Pitchfork-style block test resolved:** Variety, Slate, AV Club, IndieWire all worked. The block is per-publisher opt-in, not a sweeping entertainment-sources issue. Pitchfork is the outlier.

## Current phase
**2026-06-09: Front-end rebuilt — retrieval is now the Cultural Scout (free-text quizzing over a merged multi-run corpus), NOT substrate-pool sorting. See "Retrieval — the Cultural Scout" below. Both runs (2026-04-29 + 2026-06-01, 391 unique signals) are merged into `corpus.json`. Phase 0 + Phase 1 remain complete and stored; Phase 2 generation is reached THROUGH the Scout once the user names an area/category.**

### 2026-06-01 run summary
- **Phase 0 (harvest):** 214 in-window signals across 45 productive sources → `signals.json` (prior run archived to `signals_2026_04_29_run.json`). Big jump from April's 129/14 because the source list grew (the 2026-04-29 + 2026-05-26 additions got their first real harvest). 8 parallel category agents via WebSearch/WebFetch.
- **sources.yaml updates applied this run:** eater.com, documentjournal.com, whetstonemagazine.com, fieldmeridians(.org), letiquette.com, readafm.com → `fetchable:false`; cakezine.org repointed to cakezine.substack.com (domain hijacked); pinuphome.com → pinupmagazine.org/articles; dirt.fyi + garbageday.email uncertain flags cleared; aeon.co confirmed + 429/search-only note added.
- **Phase 1 (Layer 2 tagging):** Two-pass, tiered. A **strict** forward-looking gate kept 89 (`tier:"core"` in `tagged_signals.json`). A **soft** breadth gate then recovered 120 of the 125 strict-drops (`tier:"extended"`), leaving only 5 true non-signals. Total **209 kept**. Prior tagged output archived to `tagged_signals_2026_04_29.json`.
- **Why two tiers (user instruction 2026-06-01):** user wanted MORE not less — the extended tier enriches the corpus to evolve the underlying substrate framework over time. `forward_looking` is flagged honestly per item (134 true); `tier=="core"` is the high-signal pool for generation.
- **Pools:** Connection 27, Coping 32, Agency 26, Vitality 18, Status 22, unsettled 84. (Pool rule: high/medium confidence → its substrate; unsettled OR low-confidence → unsettled pool, per v1.1 spec. The large unsettled pool is intended.)

### Retrieval — the Cultural Scout (replaces pool-sorting, 2026-06-09)
The front-end is no longer "pick a substrate pool and read a sorted list." It is the
**Cultural Scout**: a search agent that holds **every harvest run merged into one
corpus** and that the user **quizzes in plain language** for signals in their specific
area (a theme, tension, brand problem, audience, or category). Substrate tags are kept
as **metadata** on each signal — useful color when presenting a hit — but they are no
longer the way in. The way in is the user's question.

- Invoke via the **`/cultural-scout`** skill (registered at `~/.claude/skills/cultural-scout/SKILL.md`).
- **`build_corpus.py`** — merges every `tagged_signals*.json` (auto-discovered, deduped
  by URL, run provenance per signal) into **`corpus.json`**. Re-run after each new monthly
  tag: `python build_corpus.py --stats`.
- **`scout.py "<free text>"`** — ranks the whole corpus by relevance to the query; surfaces
  candidates the Scout then judges semantically. `--full` for novelty/cross notes, `--limit N`,
  `--json` to pipe hits into Phase 2 generation, `--browse` for an overview.
- **`fetch.py` is retired** → `fetch.py.deprecated`. Pool/tier/substrate flag-filtering was
  the old front door; do not resurrect it as the primary path. (Substrate data still lives on
  every signal in `corpus.json` if ever needed.)

After scouting, Phase 2 (Layer 3) generation is unchanged: feed the Scout's selected hits
(`scout.py … --json`) into generation, output `brief_<category>.md`.

### Suns-and-planets constellation (2026-06-10, later same day)
The Explore view is now a solar-system metaphor. Each of the 8 needs (7 + unsettled, which moved OUT of the centre to its own direction) has a glowing sun sphere (SphereGeometry + additive-blend glow sprite from a canvas radial-gradient texture) with its name floating above it; signals are planets in slow continuous orbit around their need-sun (per-need axis + speed, rendered position = anchor + offset rotated by time*speed, eased by lerp 0.07 per frame; labels reposition every other frame). **The centre belongs to the search sun**: typing a query births a warm-white sun at the origin (scale eases in/out), labelled with the query text; matched signals leave their need-suns and take up ranked orbit around it (golden spiral r11-42, speed .06), lexical neighbours ring it (r52-110, speed .008), need-suns dim to 12% while a query is live. Clearing the query kills the search sun and every planet drifts home.
- **Wonder pass (same day):** entrance dolly (camera starts at z470, eases to z210, cancelled by touch), idle auto-rotate (speed .22, off on interaction, resumes after 9s still), three parallax starfield layers (replaces single bg layer), 7 faint nebula glow sprites at r300-560 (opacity .05), suns now use a custom fresnel ShaderMaterial (limb-darkened orb, hot core, rim tint; opacity/color via uniforms uOpacity/uColor — NOT material.opacity/.color), sun glows breathe (±4.5% scale, per-sun phase), per-star brightness variance (.84-1.14 lum), star twinkle via aSeed attribute + uTime uniform in dofMat, and a shooting star streaking the deep field every 16-44s (additive Line trail). All deterministic except the meteor.
- **Delight bundle (same day):** constellation lines (additive LineSegments, max 80, sketch-in via opacity lerp, coloured to the focus), birth pulse ring (camera-facing RingGeometry, 1.1s, only on sun birth not query refinement), atmosphere tint (fog + clearColor lerp 7% toward focus colour, eases back on release), stars+suns fade in from black over 1.6s on first load, latest-run signals twinkle ~80% stronger (aFresh attribute), click flash sprite on star selection, Escape closes panel then releases focus, and a "Copy link to this view" button under the Explore search field. Theme focus is now deep-linkable: `#explore&need=Kinship` (syncHash reads window.__focusedTheme; restored at module init from __initialHash).
- **Sun interactions (added same day):** suns are clickable (screen-space hit test `sunAt()`, 24px radius) → side panel opens with the theme's one-liner + description from `NEED_DESC` (sourced from NEED_TAXONOMY.md — keep in sync if taxonomy definitions change) + signal count + "Pull into orbit →" button. **Legend rows are clickable too**: clicking a theme runs the same focus choreography as a search (shared `focusOn()`), with the newborn centre sun taking the THEME's colour and members ranked by tier/fit_confidence/forward_looking; click the same theme again (or type a query) to release. Orbit speeds slowed 25% per user preference: need orbits .034+.03*rr(), focus orbit .045, ring .006.

### Query gravity in the Explore view (2026-06-10)
The constellation now reorganizes around a free-text topic — NO LLM involved. The Search tab's scorer is exposed as `window.__scoreAll`; a search field in the Explore view (`#exq`) scores all signals, then matched stars ABANDON their need-anchor positions and assemble into a relevance-ranked golden-spiral cluster at the centre (best match at the core ~r6, weakest at the shell ~r40; needs anchors sit at R=64). Non-matching stars are NOT static: each gets a graded lexical adjacency to the topic (IDF-weighted overlap with the matched set's distinctive vocabulary, sharpened with pow 2) and re-sorts radially — true neighbours ring the cluster at ~r52 with a faint glow (hoverable above aff 0.25, a discovery zone for "near the topic but didn't match your words"), the unrelated recede to ~r110 near-dark. Need anchor titles hide while a query is active and return on clear; matched labels are never distance-culled. Known limit: with very few matches the topic vocabulary is thin and ring neighbours get loosely thematic — the proper fix is Tier 2 build-time embeddings. Animation is a per-frame lerp in `frame()` (`animating` flag). Explore and Search inputs stay in sync, and the hash now encodes view+query: `#q=…`, `#explore`, or `#explore&q=…` (note: `window.__initialHash` is stashed before the search view's first render, which would otherwise rewrite an `#explore&q=…` link before the tab code reads it). Tier 2 if ever wanted: build-time embeddings for semantic layout / "make this star the sun" — see conversation 2026-06-10. Tier 3 (live LLM naming ad-hoc clusters) deliberately rejected: needs a key-holding Worker, and Copy for AI already covers synthesis.

### Explore semantic-cluster planets (2026-06-26, Tier-2 follow-on)
When a free-text query is active in the Explore (3D constellation) view, the matched planets are now grouped into the SAME emergent semantic clusters the Search tab's "Themes the corpus found" strip produces, expressed spatially: each theme gets its own small cluster-sun ringed around the central query sun, its member planets orbit that cluster-sun, and a floating keyword label (the cluster's TF-IDF label) hovers above it. This reuses the build-time int8 embeddings clustering with NO model/LLM/key/worker on the page (the clustering, k-means, and TF-IDF labels are all the existing Search-tab code).
- **New window symbol:** `window.__clusterSignals(list, q)` — exposed from the SEARCH IIFE next to `window.__scoreAll`. Takes the matched signal objects + raw query string, returns the Search tab's labeled clusters `[{members, central, keywords}]` (sorted by size) or `null` when vectors are absent (`HASVEC` false) or there are too few matches to cluster. Internally calls the existing `clusterSignals(list, terms(q))`. The Search tab's own clustering/themes strip is untouched.
- **Explore integration (the `__initExplore` module):** `applyQuery` now calls `__clusterSignals(idx.map(i=>DATA[i]), q)` (idx is relevance-sorted, so cluster assignment + labels match the Search tab exactly — verified). `focusOn(idx,label,colorHex,countMsg,clusters)` gained a 5th `clusters` arg: when `clusters.length>=2` it lays each cluster's members in a small golden-spiral around a per-cluster centroid (`clusterDir()` fibonacci-sphere direction × `CLUSTER_R=36`), else it falls back to the original single relevance golden-spiral. A reusable pool of `MAXCLUST=6` cluster-suns + glows + HTML labels (`clustSuns/clustGlows/clustLabels/clustAnchor/clustAxis/clustScale`, `activeClusters` count) is created once near the search-sun setup; `idxOf` maps signal object → DATA index (both IIFEs share `window.DATA`). Cluster-sun colour = the cluster's dominant-need colour (`clusterColor()`), so theme colour still reads as meaning. `frame()` eases the cluster-suns in/out, breathes their glow, and projects their keyword labels each frame; `release()` sets `activeClusters=0` to dismiss them.
- **Graceful degradation (all preserved):** no vectors, or a query with too few matches to cluster (<2 clusters), falls back to the existing single relevance spiral. Theme/legend focus (`applyTheme`), query gravity, search-sun birth, deep links (`#explore&q=`, `#explore&need=`, `#explore&lookfeel=`), the 3D look-&-feel fly-in, and the Search + Vital Signs tabs are all unchanged. The Search-tab need-mix filter and the `wordMatch`/`INFLECT` "rest"-doesn't-match-"restores" stemming fix are untouched.
- **Verification (2026-06-26):** `python3 build_site.py` rebuilds clean (~1199 KB, vectors present). Both inlined script blocks pass `node --check`. jsdom: 20/21 Search-tab assertions pass (themes strip, theme-chip filter + "theme: N of M" count, show-all-themes clear, need-mix, `#q=` hash restore, bounded "rest" hit count); the exposed `__clusterSignals` returns ≥2 labeled clusters that partition the matched set, and with a relevance-sorted input its labels match the Search-tab theme chips EXACTLY (e.g. "food" → "appetite · restaurant · industry" + "recipe · church · consoles"). **WebGL gap:** the 3D cluster-sun spheres + floating labels could NOT be runtime-verified — jsdom can't render Three.js/WebGL, and the Chrome extension here is blocked from `file://` URLs, so the constellation render path (the new `focusOn` cluster branch + `frame()` cluster block) was only syntax-checked, not visually confirmed. NOT deployed (`./publish.sh` is Michael's call).

### NEW PRIMARY TAXONOMY — the 7 needs (2026-06-10)
The substrate framework (Connection/Coping/Agency/Vitality/Status) is now **legacy metadata**. The primary per-signal tag is `need`, one of: **Certified Human, Kinship, Settling Accounts, Self-Authorship, Appetite, Ballast, Naming the Machine**, plus a deliberately small `unsettled` residue. Derived by 5 independent analyst agents (inductive/motivational/dialectical/semiotic/strategist postures) who converged on the same structure; full definitions, tie-break rules, and adoption rationale in **`NEED_TAXONOMY.md`** (analyst reports in `NEED_TAXONOMY_APPENDIX.md`).
- All 400 corpus signals re-tagged 2026-06-10 (4 parallel tagging agents using NEED_TAXONOMY.md definitions + tie-breaks). Distribution: Settling Accounts 19%, Naming the Machine 18%, Self-Authorship 14%, Kinship 13%, Certified Human 12%, Ballast 10%, Appetite 8%, unsettled 7%.
- `need` lives in the **tagged_signals*.json source files** (so it survives corpus rebuilds), flows through build_corpus.py FIELDS and build_site.py KEEP, and is a searchable field (weight 1) in scout.py + site.
- The site (cards, constellation anchors, legend, panel, Copy for AI) runs on `need`; `recommended_substrate` is retained per-signal as legacy metadata only.
- **Future Phase 1 tagging runs must tag `need` directly** using NEED_TAXONOMY.md (keep tagging substrate too if cheap, for continuity). Watch items flagged by the analysts: Naming the Machine may be genre-flattered by the source mix (18% full-corpus vs 14% in the eval sample); Appetite partly rides the GLP-1 news cycle; the small more-than-human/ecology cluster (~2-3%) becomes category 8 if it grows; Status's disappearance should be socialized with Jonny before anyone assumes it.

### Site + corpus overhaul (2026-06-10, audit-driven)
Search and data fixes applied after a full audit. Corpus is now **400 signals** (was 391):
- **Dedup fix** (`build_corpus.py`): merge key is now URL + same-ish title (exact/prefix/token-containment match via `same_article()`), recovering 8 032c + 1 Patta records that shared root URLs, while still merging cross-run retitles (Apartamento/Impulse/Drift cases verified).
- **Category backfill**: all 204 April-run signals got categories from sources.yaml (was null, which skewed ranking toward June signals).
- **Search rewrite** (`scout.py` + `site/template.html`, kept in sync — edit both):
  word-boundary matching with ≥4-char prefix stemming (no more "men"→"women" substring noise: 172 false hits → 4 real), 2-letter whitelist (ai/uk/us/tv/vr — "AI" went 0→33 hits), curated SYNONYMS map (~36 entries, synonyms score 0.5x; grow it freely, mirror in both files), tier=="core" boost 1.2x replacing the forward_looking boost (81% flagged = no signal), gentle recency tilt (0.92x per run older than latest).
- **Site UX** (`site/template.html`): shareable URLs (#q=… and #explore, restored on load), empty-query default shows 8 freshest latest-run signals, Copy for AI now includes novelty_note + cross_substrate_notes, "(approx)" dates render as ~YYYY-MM, "Show more" extends past 40 results, esc() hardened for quotes, far constellation labels culled below 0.2 opacity.
- Verified via jsdom smoke tests (default state, search, hash restore, show-more, explore deep-link). Deploy = `./publish.sh` as always.
- Not done (needs user's Cloudflare dashboard): Cloudflare Web Analytics beacon in template.html.
- Next tagging run: consider tightening `forward_looking` at the tagging step itself (reserve for genuinely forward signals).

### Standalone website (for sharing with the team, added 2026-06-09)
For teammates who don't use Claude Code (some use Codex/ChatGPT), there is a **standalone
search site** — no skill, no API, no login, runs entirely in-browser:
- `site/template.html` — design/markup (edit this to change look or behaviour).
- `build_site.py` — inlines the corpus into `site/index.html` (one self-contained ~340KB
  file; ranking logic is a direct JS port of `scout.py`). Has a **Copy for AI** button so
  ChatGPT/Claude users can paste results in for synthesis.
- `build_corpus.py` auto-runs `build_site.py` at the end, so **one command** —
  `python build_corpus.py` — refreshes both the corpus and the site after a new run.
- Deploy `site/` to any static host. The owner is the sole maintainer: teammates only ever
  view the deployed file; nothing they do changes the corpus. To update: re-run the harvest/
  tag, `python build_corpus.py`, redeploy `site/`.

### Phase 0 (Layer 1 harvest) — COMPLETE
- Attempted: 19 sources across 3 batches.
- Working at full density (≥8 items): 11 sources — elephant.art (12), thedriftmag.com (11), etymology.substack.com (10), pratt.edu (9), variety.com (8), slate.com (10), avclub.com (10), indiewire.com (11), 032c.com (15), family.style (12), vittlesmagazine.com (10).
- Working below density target: 3 sources — pinuphome.com (4), internetanthropologists.substack.com (2), polyesterzine.com (5).
- Hard fails / dropped: 5 sources (holiday-magazine.com, thisismold.com, pitchfork.com, thingtesting.com, dailydot.com).
- **Total signals harvested: 129 across 14 sources.** Output: `signals.json`.
- 21 sources from the original list remain untested — see CLAUDE.md history. User chose to proceed without harvesting them; can revisit if Phase 2 hits corpus-thinness.

### Phase 1 (Layer 2 tagging) — COMPLETE
- 129 input → 116 kept, 13 dropped (~10% drop rate). Drops were fiction, listicles, recipe-without-framing, pure aesthetic critiques, event coverage, archive republishes.
- Pool counts: Status 35, Coping 23, Connection 19, Agency 17, unsettled 12, Vitality 10.
- Output: `tagged_signals.json` — full per-signal records with substrate hint, fit_confidence, cross_substrate_notes, novelty_note. Pool memberships in `pools` object.
- Status is overweight (~30%); reflects source mix, not a bias to fix.
- **Unsettled pool (12) is loaded with the strongest cross-cutting signals.** Christelle Oyiri (rupture as generative), Maya Man (internet-as-air), the etymology brainrot-Buddhism / human-infohazards / symbiotic-virality cluster, Slate's critic-recantation-as-genre, Vittles food-and-kink. Per the doc these are the most generative for thought-starter generation.
- User skipped a separate Phase 1 gate per their instruction 2026-04-28 — proceeding directly to Phase 2 once category context is received.

### Phase 2 (Layer 3 generation) — COMPLETE 2026-04-29
- Target category: Nike, Fitness/Sports — repositioning to pure performance / victory platform away from apparel/style.
- Audience: deeply performance-oriented non-professional athletes (marathon runners, team-sport players, training-for-games segment).
- Conventions disrupted: tech cues, trail/outdoor metaphors, category fragmentation.
- Output: `brief_nike_performance.md` — 30 thought-starters across 6 sections.

### Phase 2 validation (same-day, 2026-04-29) — VALIDATED
User reviewed 14 of 30 thought-starters. Result: **11 wins, 3 explicit losses.**

**Wins (validated as insightful, would change the next brief):**
- Coping — Broken-athlete line
- Agency — What you do that your coach wouldn't approve of
- Status — Aspiration without snobbishness
- Vitality — Glitch as part of the glamour
- Status — Un-iconic narrative
- Coping — Anti-vibe visual register
- Coping — Time-relationship as deliverable (validated in strangeness-preserved form)
- Vitality — Home ground / gear loyal to place (validated in strangeness-preserved form)
- Status — Amateur sport as ART (validated in strangeness-preserved form)
- Unsettled — Kink-of-the-practice taxonomy (originally "Want vocabulary, not spec sheet"; validated in strangeness-preserved form)
- Unsettled — Modification IS the marketing (originally "Authorial relinquishment as the move"; validated in strangeness-preserved form)

**Losses:**
- Unsettled — Air, not place (gobbly goop — too metaphorical, requires a second leap to act on)
- Agency — Reinvention as identity-replacement (re-read failed: poetic but didn't ring true to lived experience)
- Unsettled — Inoculation as satire (re-read failed: tactically precarious; sharp diagnosis ≠ risky brand action)

**Validation lessons (saved in user memory `feedback_thought_starter_register.md`):**
1. Strangeness-preserved register beats both clean operational tidy AND direct-disruption-brief alignment when curating "strongest moves."
2. Strangeness must surface a SUPPRESSED TRUTH grounded in lived experience, not a literary reframe.
3. Sharp diagnosis can pair with un-clever execution; risky brand actions are not insightful by virtue of being weird.

System validated end-to-end. The 5 strangeness-preserved re-reads are now in `brief_nike_performance.md` in place of the originals, marked with `(validated 2026-04-29 in strangeness-preserved form)`.

### Phase 3 (Hardening) — OPTIONAL, NOT YET STARTED
Per design doc: previous-run cache for month-over-month signal drift, optional UI. Not pursued unless user requests.

## Resume instructions for next session
1. CD into this directory and invoke Claude Code from here so this CLAUDE.md auto-loads.
2. Confirm files are intact: `sources.yaml`, `signals.json` (129 signals), `tagged_signals.json` (116 kept), `harvest.py`, `requirements.txt`, `.venv/`.
3. The user will provide category context. Run Phase 2 generation interactively (not via API, per ongoing credits constraint), output to `brief_<category>.md`.
4. Phase 2 validation gate (per doc): "Would these thought starters change the next brief you wrote?" If yes, system is validated. If not, iterate on the generation prompt.
5. Open issues to address eventually (low priority): backfill 032c article URLs (currently all 15 share the magazine root URL); test untested sources if corpus thinness becomes a problem at Phase 2.

## Substrate coverage (post-Batch-3)
- **Coping:** strong. Drift welfare/ESOP/Germany pieces, etymology brainrot cluster, Slate Michael Jackson coverage, AV Club musical-biopics-vs-truth essay, elephant Tuori, 032c After Woman / David Lynch.
- **Agency:** strong. Drift welfare-fraud + Slam Frank + DHS images, etymology Polymarket + infohazards, indiewire Pete Ohs + music biopic supply, AV Club Animal Farm.
- **Connection:** improved by Batch 3. Vittles Patrick (siblings food language) + Queensway Market + Ridley Road, 032c Frost Children siblinghood, family.style In Situ, polyester MARO band-with-besties.
- **Vitality:** dramatically improved by Batch 3. 032c Christelle Oyiri "all life comes from rupture" + Ulrike Ottinger genre filmmaking + Maya Man + Kim Petras, vittles Eat This Not That kink/food, family.style Yovanovitch+Clemente wanderlust, polyester Culture Slut dancefloor.
- **Status:** improved but still room to grow. 032c Saunders aspiration-vs-snobbishness, family.style Wearstler×H&M + Lucia Eames × nanimarquina, polyester Samara Weaving emo, variety Disney-CEO-AI franchise question.

## Known issues to address before Phase 1
1. **032c URL extraction.** Homepage doesn't expose individual article URLs. All 15 032c items in signals.json carry the magazine root URL with a `url_note` flag. Phase 2 generation needs unique citable URLs — either backfill via title-based search before Phase 2, or accept that 032c signals can be summarized but not directly cited.
2. **Low-confidence summaries.** Items dated `YYYY-MM (approx)` are based on listing-page snippets, not full article reads. The `(approx)` flag is the canonical mark of "summary inferred." For Phase 2 generation quality, these should ideally be re-confirmed via per-article reads if any are selected as basis for thought-starters.
3. **Pitchfork loss.** Editorial loss in entertainment, since Pitchfork was the primary music-criticism source on the list. The other 4 entertainment sources cover film/TV but no one is filling the music-criticism slot.

## Implementation note
Several sources don't render publication dates on their listing pages (elephant.art, prattfolio, pinuphome.com, polyesterzine, family.style, most 032c). For these, dates marked as "YYYY-MM (approx)" mean "based on listing order and verified-recent context," not visible on the page. User confirmed dates within "vicinity of 90 days" is fine.

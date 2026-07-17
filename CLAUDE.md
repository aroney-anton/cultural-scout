# Culture Scout — Project Playbook

## What this is
A 3-layer cultural intelligence pipeline. Harvests editorial content from a curated source list (Layer 1), tags it against a 7-need taxonomy (Layer 2), and generates testable thought starters for a target category (Layer 3). The corpus surfaces through a browser front-end: **Search** (free-text relevance + emergent theme clustering), **Explore** (a geological "cultural sphere" globe, with a "see the whole universe" constellation toggle), and **Vital Signs** (macro indicator panel + source field guide).

Canonical spec: `/Users/michaelaroney/Downloads/cultural-thought-starter-system-design-v1_1.md`
**Full dated history and decision record: `DECISIONS.md`** (this playbook holds only the standing rules and procedures). Retired docs live in `archive/`.

## SCOPE (locked 2026-06-25)
This project is SOLELY a cultural-discovery instrument. The bake-off (`archive/corpus_vs_openweb_bakeoff.md`) tested the corpus on B2B security, semis, policy, SaaS, and energy questions and it lost 4-0-1: its discovery edge is real but bounded to its cultural milieu (food, beauty, fashion, art, internet culture). Therefore: source expansion into non-cultural / B2B / policy / analyst / trade / hard-tech / energy domains is explicitly REJECTED. Do not add or propose such sources, even when a brief seems to ask for them. Keep the monthly harvest cadence so need-share drift stays measurable over time.

The prior system (Innovation Pressure) failed by building all five layers before validating any one of them. **This system has explicit validation gates between phases. Do not progress past a phase until its gate passes.**

## Run mode
Anthropic API credits are unavailable. The `.py` harvest/tag scripts are the eventual automated form; until credits exist, **Claude performs each layer interactively in-session** using WebSearch / WebFetch / native generation, writing the same JSON/Markdown outputs, same schemas, same validation gates. If credits become available, switch to the scripts — no rewrite needed.

## Project layout (post-cleanup 2026-07-17)
```
CLAUDE.md                  this playbook (standing rules only)
DECISIONS.md               append-only dated decision record (full history)
README.md                  newcomer orientation
NEED_TAXONOMY.md           the 7-need taxonomy: definitions + tie-breaks
SEMIOTIC_CODEBOOK.md       semiotic coding discipline — READ before any coding work
sources.yaml               canonical source list — do not silently change
provenance.json            per-source region/independence (update when sources.yaml grows)
harvest.py                 Layer 1 script (needs API credits; interactive runs replace it)
tagged_signals_<date>.json Layer 2 output, one per run — LIVE build inputs, stay at root
corpus.json                merged/deduped corpus + int8 embeddings (build artifact)
.emb_cache.npz             embedding cache — tracked in git (expensive to regenerate)
embed.py                   int8 embedding pass (degrades per-signal when HF unreachable)
scout.py                   CLI relevance search over the corpus
build_corpus.py            merge tagged runs -> corpus.json, then site + globe (one command)
build_site.py              inline corpus into site/index.html; copies aux pages
build_geology.py           bake the Explore globe from corpus.json
build_semantic_range.py    per-need semantic-range scatter (axes in semantic_axes.json)
semantic_axes.json         hand-interpreted bipolar axis labels — recompute each harvest
geology_codes.json         curated semiotic codes for the globe (persists across rebuilds)
vital_signs.json           Vital Signs indicators + field guide (one-strike accuracy rule)
receipts.json              methodology + scorecard (footer modal; scorecard graded quarterly)
codes_<need>.json          semiotic codes per need
codes_preview_*.html       flat preview panels (latest set only) + codes_preview_template.html
site/template.html         SOURCE for Search + Vital Signs (edit this, NOT site/index.html)
mockup_discover_geology.html   SOURCE for the Explore globe (NOT site/discover-geology.html)
mockup_discover_universe.html  SOURCE for the constellation (copied to site/)
mockup_lookfeel_*.html     look & feel pages (copied to site/)
site/                      deployable build artifact — never hand-edit
publish.sh                 build + wrangler deploy to Cloudflare Pages (cultural-scout.pages.dev)
image_scraper/             semiotic image subsystem (own README + playbook docs)
archive/                   retired docs + harvest_runs/ (raw signals_<date>.json per run)
briefs/                    Layer 3 outputs (brief_<category>.md)
```
Git: the root is a repo pushed to private GitHub `cultural-scout` (rollback point). Normal flow: `git add -A && git commit && git push`.

## Taxonomy
Primary per-signal tag is `need`: **Certified Human, Kinship, Settling Accounts, Self-Authorship, Appetite, Ballast, Naming the Machine**, plus a small `unsettled` residue. Definitions and tie-breaks in `NEED_TAXONOMY.md` (keep NEED_DESC in the site in sync). The old substrate framework (Connection/Coping/Agency/Vitality/Status) is legacy metadata only.

Display names in the Explore/Search views are single verbs (display-only; canonical keys unchanged): Naming the Machine -> Dismantle, Settling Accounts -> Reclaim, Self-Authorship -> Author, Certified Human -> Encounter, Kinship -> Convene, Appetite -> Feel, Ballast -> Fortify. The old canonical name renders as a small byline in callouts.

Watch items: Naming the Machine is genre-flattered by the source mix (sits ~23% corpus-wide, near the ceiling); the more-than-human/ecology cluster inside `unsettled` becomes need #8 if it keeps growing; Status's disappearance should be socialized with Jonny before anyone assumes it.

## Monthly run procedure
Trigger: "run the monthly cultural harvest" or similar.

### Phase 0: Harvest
For each source in `sources.yaml` where `fetchable` is not `false` AND `semiotic_only` is not `true`:
1. WebSearch scoped to the source's domain, 1-3 queries. Bias toward recent profiles, criticism, essays, interviews, features. Drop announcements, listicles, sponsored posts, product roundups UNLESS the source is fundamentally a product-roundup publication (Strategist, Thingtesting).
2. For each item kept: title, full article URL (not homepage), publication date (YYYY-MM-DD or best estimate flagged `(approx)`), 1-3 sentence specific summary.
3. Dedup by URL.

**Distinctiveness gate (the primary keep-criterion).** The corpus is a DISCOVERY engine; its only durable edge is the below-radar layer open search buries. Keep a signal only if it carries: a named coinage, a single-writer observation/argument that isn't the dominant discourse, or a reframe open search would not surface near the top. If a competent strategist with a search engine would find it in five minutes, DROP IT, even from a strong source. The real risk is dilution by findable-but-undistinctive items, not thin coverage.

**Summary quality bar.** Specific and grounded ("a Brooklyn ceramicist who makes funeral urns shaped like household objects", not "an article about contemporary art"). If the snippet can't support a specific summary, drop the item.

**Museum exception.** Museum entries carry `recent_url` (editorial arm) AND `exhibitions_url`. Exhibition/programming pages ARE announcements and that is the point — a show going up at the Met/Tate/M+ IS the validation signal. Capture title/venue/date-range/artists/curatorial framing; skip logistics. Per-entry harvest rules live in sources.yaml's museum-wave header block.

**Fiction/poetry default drop** (per-source overrides possible — NER has one, see DECISIONS.md 2026-06-26).

**Output schema** (`signals_<date>.json`, archived to `archive/harvest_runs/` once tagged):
```json
{"harvest_date": "YYYY-MM-DD", "model": "claude-code:WebSearch", "date_range_days": 90,
 "sources_harvested": ["..."], "per_source_counts": {"source": 12},
 "signals": [{"id": "{slug}_{YYYY_MM_DD}_{NNN}", "source": "...", "title": "...",
              "url": "...", "date": "...", "summary": "..."}]}
```

**Validation gate (user inspects before Phase 1):** summaries specific; every item passes the distinctiveness gate; items within 30-90 days; quality over count (no density target — near-zero usually means wrong URL/method, ~80 means broken dedup; never pad). Failure = fix and re-run. Do NOT proceed.

**Fetch-method notes** (per-source quirks, JS-rendered pages, Substack JSON API, blocked domains) accumulate in sources.yaml entry notes and DECISIONS.md run summaries — check both before harvesting a tricky source.

### Phase 1: Tag (only after Phase 0 gate passes)
Per Layer 2 spec. Tag `need` directly using NEED_TAXONOMY.md (keep substrate too if cheap). Output: `tagged_signals_<date>.json` at root.

- **Distinctiveness carries into tagging** — anything that slipped Phase 0 gets dropped here, not tagged. Tagging is the second enforcement of the gate, not a rubber stamp.
- **Theme-gravity balance gate.** Soft per-need ceiling ~20% of a run's kept signals; past it, that need only takes items clearly distinctive AND unambiguously that need. **Naming the Machine:** keep ONLY if the payload IS the unmasking (the article's work is exposing how a system/incentive operates); tech-adjacent or AI-mentioning is not enough. **Certified Human / the provenance-anti-AI cluster:** keep only if made-by-humans / provenance / friction-as-proof is the genuine center of gravity, not a reflexive tag for anything craft-shaped.
- After tagging: `python build_corpus.py --stats` prints per-need shares with an over-20% warning; re-balance before rebuild if bloated.
- **Gate:** tags feel correct; forward-looking flags select genuinely interesting items; no source dominating one need.

### Phase 2: Generate (only after Phase 1 gate passes)
Per Layer 3 spec, reached through the Scout: `scout.py "<free text>" --json` extracts relevant hits, generation produces `briefs/brief_<category>.md`. **Gate:** would these thought starters change the next brief the strategist wrote?

**Validated register lessons (2026-04-29):** strangeness-preserved register beats both clean-operational and disruption-brief alignment; strangeness must surface a SUPPRESSED TRUTH grounded in lived experience, not a literary reframe; sharp diagnosis can pair with un-clever execution — risky brand actions are not insightful by virtue of being weird.

### Post-run steps
1. `python build_corpus.py --stats` (now chains site + globe builds — one command).
2. **Recompute semantic axes (required each harvest):** per need, `python build_semantic_range.py --poles "<need>"`, re-read pole signals, update label pairs in `semantic_axes.json` (bump `_generated_against`), rebuild. PCA variance is inherently low (~5-9%); axes are directional summaries.
3. Add a RUN_NOTES entry in build_corpus.py whenever intake changed for non-cultural reasons.
4. Update `vital_signs.json.world_summary` (state-of-play brief): 2-3 sober paragraphs from current indicator values (no re-pulling) + the month's strongest macro-relevant signals, ending in a one-line strategist's read.
5. **Monthly digest (Michael ONLY):** GMAIL DRAFT (create_draft, never send) to aroney@sylvain.co — "5 signals that would change your next brief" + share deltas with caveats + state-of-play line. Do NOT widen distribution without explicit approval.
6. Deploy = `./publish.sh` (Michael's call).
7. Move the raw `signals_<date>.json` into `archive/harvest_runs/` — the raw harvest text is a longitudinal record, never deleted (Michael 2026-07-17).

## Standing rules
- **sources.yaml is canonical** — never silently change it. Every source addition needs: fetchability verified, a distinctiveness-fit note, and a matching provenance.json entry ({region, independent}; uncertain region = "Online (unplaced)", never guess).
- **`semiotic_only: true` sources** (17 image-rich fashion/photography sources) are an image pool for the codebook stage ONLY: never harvested, never tagged, never in corpus.json or provenance.json. They feed the scraper URL-first (WebSearch the domain per code, then `run.py scrape --urls`), never crawled. The distinctiveness gate does NOT apply to semiotic/codebook coding — the coding stage wants evocative code-fitting imagery, and ALL sources' content is in scope there. (Full detail: DECISIONS.md 2026-07-09.)
- **Copyright (images):** never store or copy harvested images into project files, site/, or deliverables. Codes render as derived artifacts (swatches, descriptors, ≤15-word attributed quotes, evidence links) plus hotlinked evidence collages (`image_refs`, live embeds from publishers' servers, credited, `referrerpolicy=no-referrer`). Downloading to `image_scraper/.cache/` is allowed for analysis only — deleted by `run.py clean`, never committed. EU embedding is murkier than US hotlinking — re-assess before any client-facing deploy. Paywalls are never defeated.
- **Image/sheet retention (2026-07-17):** contact-sheet archives in `image_scraper/sheets_archive/` are kept INDEFINITELY (longitudinal record). `run.py clean` archives sheets and deletes only the raw .cache/; pruning old archives is opt-in via `clean --prune`. All of it stays local-only and gitignored.
- **One-strike accuracy (Vital Signs):** tiles show verbatim values with source quotes; anything not verified directly carries confidence:"low" + a "verify" badge. NEVER write a value not read from a fetched source; when in doubt, null + low confidence. On refresh, APPEND to `pull_history`, never overwrite. Refresh is user-triggered (~quarterly); NOT part of the monthly task.
- **Receipts scorecard:** graded only at quarterly indicator refreshes (inaugural: Q3 2026), published as made, never edited after the fact. NEVER graded in an unsupervised run.
- **Edit sources, not build artifacts:** site/ is generated. Search/Vitals changes go in site/template.html; globe changes in mockup_discover_geology.html; constellation in mockup_discover_universe.html. Scout ranking logic lives in BOTH scout.py and template.html — keep in sync, including the SYNONYMS map.
- **Embeddings degrade per-signal** (embed.py keeps cached vectors, new signals ship vec-less when HF hosts are unreachable; they're searchable but excluded from clustering until embedded on a HF-reachable machine via `build_corpus.py --require-embeddings`). NEVER fabricate vectors.
- **Image scraper is a URL-fed extractor, NOT a crawler** — input is corpus URLs (`--need`) or a `--urls` file. Do not resurrect the crawler idea. Caps: `--max-per-article 15`, `--target-images 250`. Ops: `image_scraper/README.md`; orchestration: `image_scraper/SEMIOTIC_IMAGE_HARVEST.md`.
- **Semiotic codes discipline:** READ `SEMIOTIC_CODEBOOK.md` before any coding work. Stable IDs — append evidence / move status / propose / retire, never rewrite. Codes are per-need `codes_<need>.json`; build_site.py auto-discovers them for the 3D look-&-feel fly-in. Needs coded so far: Certified Human, Naming the Machine, Self-Authorship, Settling Accounts, Appetite (pilots; scale-out gates with Michael).
- **Pulse chart is removed** from the Search tab (2026-07-07) but `need_history` computation stays in build_corpus.py — inert, don't rip out the data pipeline. Recoverable from git if wanted.
- **WebGL caveat:** the globe/constellation render paths can't be visually verified in this build env — syntax-check inlined scripts with `node --check` after every rebuild.
- **Work in small batches** — pause and check in often (Michael's standing preference).

## Architecture notes (what talks to what)
- `build_corpus.py` merges every root `tagged_signals*.json` (run id = each file's own `tagging_date`), dedups by URL + same-ish title, chains `build_site.py` and the globe build. One command: `python build_corpus.py`.
- The Explore tab is an iframe: `site/discover-geology.html` (default, baked from corpus each build) with a toggle to `site/discover-universe.html` (constellation; static copy, mirrors parent globals via a shim). Each keeps its own search. Key bridges: `window.__scoreAll`, `window.__clusterSignals`, `window.parent.DATA`; globe search-reconstitution re-forms the sphere around a query's semantic themes.
- Deep links: `#q=…`, `#explore`, `#explore&q=…`, `#explore&need=…`, `#explore&lookfeel=…`, `#receipts`.
- Site data injections (build_site.py markers): corpus, NEEDHIST, RECEIPTS, VITALS, CODES, provenance-joined SOURCES.

## Current status (2026-07-17)
Corpus: 860 signals, 4 runs, 160 sources. System validated end-to-end (Nike brief, 2026-04-29). Semiotic codes piloted for 5 of 7 needs. Next direction: topic-pointed repackaging — see `AUDIT_AND_REPACKAGING_PLAN_2026_07_17.md` Part 3. All dated history: `DECISIONS.md`.

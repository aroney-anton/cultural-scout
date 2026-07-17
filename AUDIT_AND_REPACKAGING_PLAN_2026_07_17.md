# Audit + Repackaging Plan — 2026-07-17

Three parts: (1) folder audit, (2) cleanup + workflow simplification recommendations, (3) plan for the topic-pointed repackaging. Nothing here has been executed — this is the proposal.

---

## Part 1 — Audit

The root has ~80 items. Git is clean (98 tracked files). The mess is not disorder so much as accumulation: every run, pilot, and prototype left artifacts at the root, and nothing has ever been swept. Findings, ordered by how much confusion each causes:

**1. `cultural-scout/` is a stale full duplicate of the entire project (9.6M).** It has its own `.git` and is frozen at July 2 — corpus, codes, everything 11 days behind the root. Anyone (human or agent) opening the folder sees two copies of the project and can't tell which is live. The root IS the live repo; this nested copy serves no current purpose.

**2. `CLAUDE.md` is 85K and is the single biggest complexity driver.** It has become an append-only changelog wearing a playbook's clothes. Every session loads all 85K of history (June harvest notes, per-source fetch quirks, byline CSS changes) before any work starts. The durable playbook content — scope, run procedure, gates, layout — is maybe 15K of it.

**3. Eleven `codes_preview_*.html` files, mostly superseded versions.** Five needs × multiple dated versions. Only the `_2026_07_13` set (plus the template) is current; the other 6 are stale duplicates already in git history.

**4. Working files stranded at the root.** `urls_*_round2.txt` (×3) and `GAP_REPORT_*` (×2) belong to the image-scraper workflow — image_scraper/ has its own copies of the same file types. Six `_semrange_*` scratch previews from the July 2 semantic-range prototype. `prompt_self_authorship_codes.md` is a one-off session prompt.

**5. Inconsistent run-file naming.** `signals.json` is actually the 2026-06-01 run; `signals_2026_04.json` and `signals_2026_04_29_run.json` overlap; `tagged_signals.json` is the 06-01 tagged output. The dated convention (`*_YYYY_MM_DD.json`) only starts at June 11. build_corpus.py auto-discovers `tagged_signals*.json`, so undated names still work, but the history is hard to read.

**6. Stale docs.** `HOW_TO_USE.md` (Apr 29) still describes the dead 5-substrate taxonomy and a 14-source list — actively misleading. `TIER2_EMBEDDINGS_BUILD_2026_06_26.md` is a session note. `NEED_TAXONOMY_APPENDIX.md` (44K analyst reports) and `corpus_vs_openweb_bakeoff.md` are decision records worth keeping but not root-level reading.

**7. image_scraper is 592M, ~135M of it redundant.** `sheets_archive/` (232M) is the sanctioned 6-month archive. But `.cache_ch_backup/` (78M) violates the "cache deleted on clean" rule (predates the archive convention), and `sheets_ch_backup/` (26M) + `sheets_round1/` (32M) hold imagery the archive convention now covers. Two separate `.venv`s (root 205M + scraper 223M) — heavy but both gitignored and functional; low priority.

**8. Redundant scripts.** `publish_mockup.sh` is a subset of `publish.sh` from before the globe was the default Explore view. `fetch.py.deprecated` is already retired and in git history.

**9. Outputs mixed with machinery.** `brief_nike_performance.md` and `brief_aarp_future_forwarding.md` (deliverables) sit beside build scripts.

---

## Part 2 — Recommended cleanup + workflow simplification

### Cleanup (light-touch, deliberately)

A full re-plumb into `pipeline/`, `data/`, `frontend/` folders would mean touching paths in every build script for cosmetic gain — and Part 3 will reorganize data around topics anyway. So: sweep the clutter, split the playbook, leave the build chain's file paths alone.

**Delete outright** (all in git history or explicitly disposable):
- `cultural-scout/` nested duplicate (confirm nothing unique first — a 5-minute diff)
- 6 stale `codes_preview_*` versions (keep `_2026_07_13` set + template)
- `_semrange_*` (×6), `prompt_self_authorship_codes.md`, `fetch.py.deprecated`, `publish_mockup.sh`, `.DS_Store` files
- `image_scraper/.cache_ch_backup/`, `sheets_ch_backup/`, `sheets_round1/` → fold anything wanted into `sheets_archive/` first (~135M recovered)

**Move into an `archive/` folder** (kept, out of the way):
- `HOW_TO_USE.md` (stale — rewrite later or fold into README)
- `NEED_TAXONOMY_APPENDIX.md`, `corpus_vs_openweb_bakeoff.md`, `TIER2_EMBEDDINGS_BUILD_2026_06_26.md`
- Root `GAP_REPORT_*` and `urls_*_round2.txt` → `image_scraper/` or `archive/`
- `brief_*.md` → `briefs/`

**Rename for consistency:** `signals.json` → `signals_2026_06_01.json`, `tagged_signals.json` → `tagged_signals_2026_06_01.json`, `signals_2026_04.json`/`signals_2026_04_29_run.json` → reconcile to one dated file. (Verify build_corpus.py discovery still picks them up; it globs `tagged_signals*.json` so renames are safe.)

**Split CLAUDE.md** — the highest-value single change:
- `CLAUDE.md` → lean playbook (~15K): scope lock, taxonomy, run procedure + gates, project layout, run mode, standing rules (copyright, one-strike, distinctiveness gate, theme-gravity ceilings)
- `DECISIONS.md` → the dated changelog entries, append-only as before
- Result: every future session starts from the rules, not the history; history stays greppable

### Workflow simplification

- **One build command.** `build_corpus.py` already chains `build_site.py`; fold `build_geology.py` into that chain so corpus → globe → site is one invocation. `publish.sh` then covers build+deploy fully.
- **Retire dead weight in the site pipeline:** NEEDHIST/pulse computation is inert (chart removed 2026-07-07); receipts scorecard is empty until Q3. Neither needs work now, but neither should constrain Part 3.
- **The monthly harvest stays as-is** (scope lock: keep the cadence so drift stays measurable). The semiotic image workflow stays as-is — it already got its retention/cap discipline in July.

---

## Part 3 — Plan: point the instrument at a topic

### The reframe

Today the system documents all of culture, then you search it. The ask: give it a topic ("running", "hair", "third places", a client category) and have the whole instrument — universe, needs/themes, codes — rebuild around that topic.

The good news: roughly half the machinery already does this. The globe's search-reconstitution (`reconstitute(q)`) already re-forms the sphere around a query's semantic themes. `scout.py --json` already extracts a topic-relevant corpus subset. The clustering, need-tinting, and callout machinery are all query-capable. What's missing is (a) a topic-scoped *harvest* to fill the corpus's gaps on a specific subject, (b) topic-scoped *codes*, and (c) *packaging* — a persistent per-topic artifact rather than an ephemeral in-browser query.

### Architecture: a "topic run" produces `topics/<slug>/`

```
topics/running/
  topic.yaml                 topic definition: name, brief, category context, date
  topic_signals.json         corpus subset + fresh topical mini-harvest, tagged
  codes_<need>.json          ≤2 codes per active need (needs with no real signal are dropped)
  site/index.html            self-contained topic site: globe + themes + codes
```

Data layers per topic:
1. **Corpus subset** — `scout.py` pulls everything relevant from the living 860-signal corpus. Free, instant, carries the below-radar edge.
2. **Topical mini-harvest** — an interactive WebSearch pass scoped to the topic: the existing source list first, then open web. Same distinctiveness gate, applied topic-locally. These signals live in the topic folder; they only merge into the main corpus if they'd pass the normal gates AND are in-milieu (keeps the scope lock intact — a topic harvest is ephemeral, not a source expansion).
3. **Needs + themes** — keep the 7-need taxonomy as the lens (comparability across topics, and the codes machinery is need-keyed), but per-topic: shares recomputed, empty needs dropped from the globe, theme clusters (the existing k-means/TF-IDF) provide the topic-specific structure inside each need.
4. **Codes** — image_scraper `--urls` mode fed from the topic signal set, capped at 2 codes per need (your call — matches reality: a narrow topic won't sustain 5). Same codebook discipline, same copyright rules.
5. **Vital signs** — opt-in only. Include a small panel only when 2–3 macro indicators map cleanly to the topic (e.g. food-price sentiment for a food topic); otherwise omit the tab entirely. Never auto-generated.

### Build phases (with gates, per house rule)

**Phase A — Parameterize the build chain.** New `build_topic.py`: takes a topic signal set, emits a full mini-site into `topics/<slug>/site/` (globe baked from the subset via a parameterized build_geology, per-topic need shares, no Vital Signs tab by default — build_site made conditional). No new harvesting yet — corpus subset only.
*Gate:* point it at a topic the corpus covers well (e.g. "food and desire") — does the topic globe read true against what you know is in the corpus?

**Phase B — Topical mini-harvest procedure.** A written procedure (interactive, like the monthly run): scout the corpus, identify gaps, WebSearch the source list + open web scoped to the topic, distinctiveness gate applied, tag, merge into `topic_signals.json`.
*Gate:* signal quality on one real topic — same inspection standard as Phase 0.

**Phase C — Topic codes.** Run the semiotic workflow per active need at topic scope, max 2 codes each, using the existing scraper/sheets/codebook machinery unchanged.
*Gate:* you review the codes, same as the need pilots.

**Phase D — Package as one command.** A `/culture-lens <topic>` skill (or a documented run procedure) that walks A→C interactively and deploys to `cultural-scout.pages.dev/t/<slug>/`. Topic runs are repeatable: re-run after the next monthly harvest and the topic picks up fresh corpus signal.

### Decisions needed from you before Phase A

1. **Corpus + fresh harvest, or corpus-only for v1?** Recommend corpus-only for Phase A (cheapest test of the concept), fresh harvest added in Phase B.
2. **Fixed 7-need lens vs re-derived per topic?** Recommend fixed (argued above), but if a topic's unsettled pool dominates, that's the signal to hand-name a topic-local theme.
3. **What's the first test topic?** Should be one the corpus is genuinely strong on — food, beauty, fashion, internet culture lanes.
4. **Do the codes previews / lookfeel mockups become the code-display surface inside topic sites**, or does the globe's existing callout carry codes? (Affects how much front-end work Phase A includes.)

### Sequencing

Cleanup first (it's a morning's work and makes everything after easier), CLAUDE.md split with it, then Phase A. Each phase is a separate session batch with your review between — matching how this project has always avoided the Innovation Pressure failure mode.

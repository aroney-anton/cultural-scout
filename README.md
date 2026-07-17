# Culture Scout — Cultural Thought-Starter System

A three-layer cultural intelligence pipeline. It harvests editorial content from a curated source list, tags each signal against a needs taxonomy (Certified Human, Kinship, Settling Accounts, Self-Authorship, Appetite, Ballast, Naming the Machine, plus an `unsettled` residue), and surfaces the corpus through a browser front-end: a **Search** tab (free-text relevance + emergent theme clustering), an **Explore** tab (a geological "cultural sphere" globe), and a **Vital Signs** tab (macro indicator panel + source field guide).

This is a cultural-discovery instrument. Its edge is surfacing below-radar cultural signal in food, beauty, fashion, art, and internet culture. It is deliberately **not** a B2B / policy / hard-tech research tool (see the scope note in `CLAUDE.md`).

## Start here

- **`CLAUDE.md`** — the canonical project playbook: scope, run procedure, validation gates, standing rules. Read this first.
- **`DECISIONS.md`** — the append-only dated decision record and change log (the full history).
- **`NEED_TAXONOMY.md`** — the 7-need taxonomy definitions and tie-break rules.

## Pipeline at a glance

```
sources.yaml                     curated editorial source list (canonical — do not silently change)
   │  harvest (interactive WebSearch/WebFetch, or harvest.py when API credits exist)
   ▼
signals_<date>.json              raw harvested signals (one per run; archived to archive/harvest_runs/)
   │  tag against the need taxonomy
   ▼
tagged_signals_<date>.json       per-signal need + metadata (one file per run)
   │  build_corpus.py            merge every tagged run, dedup by URL
   ▼
corpus.json                      the merged, deduped corpus (+ int8 embeddings via embed.py)
   │  build_site.py  ─ inlines corpus into the Search/Vitals site
   │  build_geology.py ─ bakes the Explore globe's GEO object from corpus.json
   ▼
site/index.html                  self-contained Search + Vital Signs site
site/discover-geology.html       the Explore globe (embedded as an iframe by index.html)
```

## Common commands

```bash
# rebuild everything (corpus → index.html → globe) after a new tagged run
python3 build_corpus.py            # chains build_site.py + build_geology.py

# rebuild just the Explore globe from the current corpus
python3 build_geology.py

# deploy the site to Cloudflare Pages (same URL every time)
./publish.sh                       # one-time prereq: `wrangler login`
```

## Layout

| Path | Role |
|------|------|
| `sources.yaml` | canonical editorial source list |
| `archive/harvest_runs/signals*.json` | raw harvest output, per run (longitudinal record — never deleted) |
| `tagged_signals*.json` | tagged output, per run (carries `need` + metadata) |
| `corpus.json` | merged/deduped corpus (build artifact) |
| `build_corpus.py` / `build_site.py` / `build_geology.py` | build chain |
| `embed.py` | int8 embedding pass (degrades per-signal when HF hosts unreachable) |
| `scout.py` | CLI relevance search over the corpus |
| `site/template.html` | Search + Vital Signs markup/logic (edit this, not index.html) |
| `mockup_discover_geology.html` | Explore globe template (edit this, not discover-geology.html) |
| `geology_codes.json` | curated semiotic codes for the globe (persist across rebuilds) |
| `vital_signs.json` / `provenance.json` / `receipts.json` | Vital Signs + provenance + methodology data |
| `NEED_TAXONOMY*.md`, `SEMIOTIC_CODEBOOK.md` | taxonomy + coding discipline docs |
| `briefs/brief_*.md` | Layer 3 generated thought-starter briefs |
| `archive/` | retired docs + raw harvest runs |

## Build artifacts vs. source

`corpus.json` and `site/*.html` are generated — regenerate them with the build chain rather than hand-editing. `.emb_cache.npz` is the embedding cache; it is tracked in git because it is expensive to regenerate (the embedding model hosts are firewalled on the build machine).

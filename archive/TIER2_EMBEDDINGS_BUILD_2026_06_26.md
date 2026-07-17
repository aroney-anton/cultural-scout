# Tier-2 build-time embeddings + in-browser semantic clustering

Scheduled task, 2026-06-26. Status: **code complete and plumbing-verified; the one-time
embedding backfill could NOT run in this environment and must be run where Hugging Face is
reachable.** No half-build was shipped. The live `corpus.json` and `site/index.html` are
untouched.

## The blocker (why no vectors yet)
The Cowork sandbox proxy allows PyPI and `github.com` HTML only. Every model-weight host is
firewalled: `huggingface.co`, `storage.googleapis.com`, AWS S3, and `codeload` /
`raw.githubusercontent.com` / `release-assets.githubusercontent.com` all return 000/403.
`fastembed` and `sentence-transformers` install fine, but the bge-small / gte-small / MiniLM
ONNX weights cannot be downloaded here. Per the task's own instruction ("if the model cannot
be downloaded, STOP and report rather than shipping a half-build"), I did not fabricate or ship
vectors. The embedding step degrades gracefully and the corpus still builds without them.

## What was built (all landed, all safe)
- **`embed.py`** (new). Offline embedding + PCA + int8 quantization.
  - Embeds `title + summary` per signal with `BAAI/bge-small-en-v1.5` (384-dim) via
    sentence-transformers, falling back to `fastembed` (same ONNX weights, no torch).
  - Raw float vectors cached by text-hash in `.emb_cache.npz`, so monthly runs embed only the
    NEW signals (incremental). First run backfills all ~849.
  - L2-normalize -> PCA to 128 dims -> int8 quantize (single global scale). Each signal gets
    `vec` = base64(int8[128]). PCA mean/components + scale stored as `corpus.json.embedding`
    (base64 float32) for reconstruction; NOT shipped to the site.
- **`build_corpus.py`**. Calls `embed.embed()` before writing the corpus. Graceful by default
  (missing model = warning, builds without vectors, monthly harvest never breaks); new
  `--require-embeddings` flag makes the backfill hard-stop instead of shipping partial.
- **`build_site.py`**. `vec` added to `KEEP`; a null `vec` is dropped so the vector-less site
  isn't bloated. The PCA matrix stays out of the site by design (the browser only needs the
  int8 vectors; the global scale cancels in cosine).
- **`site/template.html`**. In-browser clustering, NO model/key/worker on the page:
  - Decodes int8 vectors, runs deterministic spherical k-means (rank-seeded init, k = 2-5 by
    result-set size, cosine on the int8 vectors).
  - "Themes the corpus found" strip above results: one chip per cluster, labeled by TF-IDF
    distinctive keywords (cluster vs the rest of the matched set) + the most-central signal's
    title as hover. Clicking a chip filters results to that cluster; "show all themes" clears.
  - Labels are keyword-only. No runtime LLM naming (coined naming stays the Copy-for-AI job).
  - Coexists with the prior need-mix / dominant-need filter (untouched). Hidden in the default
    state and whenever vectors are absent.
  - The optional Explore semantic-neighbor swap was deliberately SKIPPED to avoid risk to the
    constellation (stretch goal, not required).

## Size
Synthetic-vector test build vs vector-less build, same new template:
**+152 KB** added to the inlined site (1190 KB vs 1038 KB). Under the ~200 KB target.
(128 int8 dims = 172 base64 chars/signal x 849 signals.)

## Verification (jsdom, 18/18 passed)
Tested against a synthetic-vector build (need-correlated vectors) and a vector-less build,
neither of which touched the live files:
- default state shows cards, themes hidden;
- a search renders the themes strip with >=2 labeled cluster chips;
- clicking a chip filters to the cluster (e.g. 29 of 92), count text shows "theme: N of M",
  active state + "show all themes" clear control behave;
- need-mix chips render and exclude correctly alongside clustering;
- `#q=...` hash restore works;
- the vector-less site degrades cleanly: search and need-mix work, themes strip stays hidden.

**Cluster quality note:** the jsdom run used SYNTHETIC vectors, so it validates the full
pipeline (decode -> k-means -> TF-IDF labels -> chip filter) but NOT real semantic coherence.
Genuine cluster quality can only be judged after the real backfill. Expect the keyword labels
to be the weakest link (TF-IDF on short title+summary text is serviceable but blunt); the
LBLSTOP generic-word list is the dial to tune once real labels are visible.

## To complete (one command, on a Hugging-Face-reachable machine)
```
cd cultural-thought-starter
pip install sentence-transformers --break-system-packages   # or: pip install fastembed
python3 build_corpus.py --require-embeddings                 # backfills ~849, refreshes corpus.json + site/index.html
```
This embeds everyone once (caching for future runs), rebuilds `corpus.json` with `embedding`
metadata, and rebuilds `site/index.html` with both the vectors and the (currently dormant)
clustering UI live. Then eyeball a few searches for cluster coherence, tune `LBLSTOP` if labels
are noisy, and deploy with `./publish.sh` (Michael's call - not deployed by this task).
Monthly runs afterward stay one command (`python3 build_corpus.py`): only new signals embed.
```
```

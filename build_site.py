#!/usr/bin/env python3
"""Render the standalone Cultural Scout website from corpus.json.

Produces a SINGLE self-contained file — `site/index.html` — with the whole
corpus inlined, so it works by double-click, as an email attachment, or on any
static host (Netlify / Cloudflare Pages / Vercel / GitHub Pages). No server, no
API, no login. Search runs entirely in the browser, mirroring scout.py ranking.

    python build_site.py        # writes site/index.html

Monthly update: re-run build_corpus.py (folds in the new run), then this. The
site is just a view of the corpus — only whoever runs these scripts can change
what the team sees.
"""
import json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus.json")
SOURCES_YAML = os.path.join(HERE, "sources.yaml")
VITALS = os.path.join(HERE, "vital_signs.json")   # indicators + field guide (Vital Signs tab)
RECEIPTS = os.path.join(HERE, "receipts.json")    # methodology + self-graded scorecard (Receipts tab)
PROVENANCE = os.path.join(HERE, "provenance.json")  # region/independence metadata per editorial source
TEMPLATE = os.path.join(HERE, "site", "template.html")
OUT = os.path.join(HERE, "site", "index.html")

# Only the fields the page actually shows / searches — keeps the file lean.
# `vec` is the base64 int8 embedding (128 dims, ~172 chars/signal) used for the
# in-browser semantic clustering of search results. It's present only after a
# build that had the local embedding model available; absent, the clustering
# strip just stays hidden. The PCA matrix in corpus.json is NOT inlined — the
# browser only needs the per-signal int8 vectors (cosine cancels the scale).
KEEP = ["source", "category", "title", "url", "date", "summary",
        "forward_looking", "recommended_substrate", "fit_confidence",
        "novelty_note", "cross_substrate_notes", "tier", "need",
        "_runs", "_first_seen", "vec"]


def inject(html, marker, value):
    start, end = f"/*__{marker}__*/", "/*__END__*/"
    i = html.index(start) + len(start)
    j = html.index(end, i)
    return html[:i] + value + html[j:]


def parse_sources(path):
    """Light parser for sources.yaml (system python has no PyYAML). Pulls the
    editorial source list — name / category / base_url / fetchable — out of the
    `sources:` block."""
    if not os.path.exists(path):
        return []
    out, cur, in_block = [], None, False
    for raw in open(path):
        s = raw.rstrip("\n")
        if s.strip() == "sources:":
            in_block = True
            continue
        if not in_block:
            continue
        if s and not s[0].isspace() and not s.strip().startswith("#"):
            break  # dedent out of the sources block
        m = re.match(r"\s*-\s*name:\s*(.+)", s)
        if m:
            if cur:
                out.append(cur)
            cur = {"name": m.group(1).strip().strip('"'), "category": None,
                   "base_url": None, "fetchable": True}
            continue
        if cur is None:
            continue
        for key in ("category", "base_url"):
            mm = re.match(rf"\s+{key}:\s*(.+)", s)
            if mm:
                cur[key] = mm.group(1).strip().strip('"')
        if re.match(r"\s+fetchable:\s*false", s):
            cur["fetchable"] = False
    if cur:
        out.append(cur)
    return out


def main():
    if not os.path.exists(CORPUS):
        sys.exit("corpus.json not found — run: python build_corpus.py")
    if not os.path.exists(TEMPLATE):
        sys.exit("site/template.html not found.")

    data = json.load(open(CORPUS))
    signals = [{k: s.get(k) for k in KEEP if not (k == "vec" and not s.get(k))}
               for s in data["signals"]]
    runs = data.get("runs", [])
    built = max(runs) if runs else ""

    sources = parse_sources(SOURCES_YAML)

    # Join best-effort provenance metadata (region, independence) onto each
    # editorial source. sources.yaml stays canonical and untouched.
    if os.path.exists(PROVENANCE):
        prov = json.load(open(PROVENANCE)).get("regions", {})
        for s in sources:
            p = prov.get(s["name"], {})
            s["region"] = p.get("region")
            s["independent"] = p.get("independent")

    vitals = {"pulled": "", "indicators": [], "fieldguide": []}
    if os.path.exists(VITALS):
        vitals = json.load(open(VITALS))

    receipts = {}
    if os.path.exists(RECEIPTS):
        receipts = json.load(open(RECEIPTS))

    # Semiotic codes: auto-discover codes_<need>.json files (pilot: certified
    # human). Keyed by need name; the Explore view shows "Explore look & feel"
    # only for needs present here. image_refs are hotlinks, never stored.
    import glob as _glob
    codes = {}
    for f in sorted(_glob.glob(os.path.join(HERE, "codes_*.json"))):
        try:
            c = json.load(open(f))
            if c.get("need") and c.get("codes"):
                codes[c["need"]] = c
        except Exception:
            pass

    need_history = data.get("need_history", [])

    html = open(TEMPLATE).read()
    html = inject(html, "DATA", json.dumps(signals, ensure_ascii=False))
    html = inject(html, "RUNS", json.dumps(runs))
    html = inject(html, "BUILT", json.dumps(built))
    html = inject(html, "SOURCES", json.dumps(sources, ensure_ascii=False))
    html = inject(html, "VITALS", json.dumps(vitals, ensure_ascii=False))
    html = inject(html, "NEEDHIST", json.dumps(need_history, ensure_ascii=False))
    html = inject(html, "RECEIPTS", json.dumps(receipts, ensure_ascii=False))
    html = inject(html, "CODES", json.dumps(codes, ensure_ascii=False))

    with open(OUT, "w") as f:
        f.write(html)
    kb = round(len(html.encode("utf-8")) / 1024)
    print(f"Wrote {OUT}: {len(signals)} signals, {len(runs)} runs, {len(sources)} sources, ~{kb} KB single file.")
    print("Open it: double-click site/index.html, or deploy the site/ folder to any static host.")

    # "See the whole universe" — the recovered constellation view is a static,
    # self-contained page (it mirrors the parent's DATA/scorer via window.parent),
    # so it just gets copied into site/ rather than data-injected.
    universe = os.path.join(HERE, "mockup_discover_universe.html")
    if os.path.exists(universe):
        shutil.copy(universe, os.path.join(HERE, "site", "discover-universe.html"))
        print("  Copied universe view -> site/discover-universe.html")
    else:
        print("  [universe] NOTE: mockup_discover_universe.html not present yet — universe toggle will 404 until it's added.")

    # Also re-bake the geology globe (Explore view) from the same corpus so it
    # never drifts stale behind the Search tab. Degrades gracefully if absent.
    geo_builder = os.path.join(HERE, "build_geology.py")
    if os.path.exists(geo_builder):
        try:
            import build_geology
            build_geology.build(log=lambda m: print(" ", m))
        except Exception as e:
            print("  [geology] WARNING: globe rebuild skipped:", e)


if __name__ == "__main__":
    main()

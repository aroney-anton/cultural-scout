#!/usr/bin/env python3
"""Bake the geology globe's GEO object from the live corpus.

The Explore view (the geological cultural sphere) is a standalone page,
`mockup_discover_geology.html`, whose data used to be a hand-frozen `GEO`
snapshot. This regenerates GEO from corpus.json on every rebuild so the globe
stays in sync with the Search tab instead of drifting stale.

What regenerates from the corpus each build:
  - per-need signal counts, percentages, and the corpus total
  - the lexical clusters inside each need (k-means over the int8 embeddings,
    TF-IDF labels from titles+summaries) — the same spirit as the Search tab's
    "themes the corpus found" clustering, baked at build time.

What is carried forward (NOT re-derived per build):
  - per-need colour / one-liner / body  -> NEED_META below (the taxonomy copy)
  - curated semiotic `code` blocks       -> geology_codes.json (Michael's
    monthly hand-coding; persists between rebuilds, diffed by the velocity card)

Output: site/discover-geology.html (template = mockup_discover_geology.html,
with a /*__GEO__*/ ... /*__END__*/ marker around the GEO literal).

    python build_geology.py            # writes site/discover-geology.html
build_site.py also calls build() at the end, so `python build_corpus.py`
refreshes corpus -> index.html -> the globe in one shot.
"""
import base64, json, math, os, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus.json")
TEMPLATE = os.path.join(HERE, "mockup_discover_geology.html")
OUT = os.path.join(HERE, "site", "discover-geology.html")
CODES = os.path.join(HERE, "geology_codes.json")

# Taxonomy copy (colour / one-liner / body). Lifted from NEED_TAXONOMY.md, kept
# here so the globe's look is stable across rebuilds. Order is irrelevant —
# needs are emitted largest-first.
NEED_META = {
    "Naming the Machine": {"color": "#d671a8",
        "one": "Show me the machinery acting on me, in words I can repeat.",
        "body": "The need to see the systems acting on you, named plainly: illegitimate power, wage theft, attention and prediction markets, algorithmic management, supply-chain unmaskings. Comprehension as the precondition of agency."},
    "Settling Accounts": {"color": "#a884d6",
        "one": "See the record corrected, and the losses properly held.",
        "body": "The need for a past that has been fairly judged and properly mourned: recantations, canon recovery, restitution, legacy wars, archive rescue, grief given durable form. The single largest engine in this corpus."},
    "Self-Authorship": {"color": "#5b86d6",
        "one": "I write me, not the platform, the estate, or the algorithm.",
        "body": "The need to be the author, not the authored: reclaimed identities, careers rewritten, gender as practice, refusal of brand-ness, and the right to illegibility. Recognition without becoming what recognition demands."},
    "Certified Human": {"color": "#d9a84e",
        "one": "Prove to me a person made this and meant it.",
        "body": "The need to trust that what you perceive and consume is real, traceable, and made by a person who meant it. Provenance claims, anti-slop criticism, durational handcraft, labor-time as content, sincerity as method."},
    "Kinship": {"color": "#3f9d96",
        "one": "Build me the structures that put me in a room with my people.",
        "body": "The need for unmediated bodily togetherness, now deliberately built rather than assumed: gatherings, scenes, markets, mutual aid, mentorship, plus the diagnoses of togetherness failing. Togetherness has become infrastructure."},
    "Appetite": {"color": "#e0654a",
        "one": "Let me actually want things, in my actual body.",
        "body": "The need to feel your own wanting, hunger, pleasure, intensity, against pharmaceutical, algorithmic, and managerial suppression. The smallest theme but the most consistently startling."},
    "Ballast": {"color": "#7fb069",
        "one": "Help me hold the weight and keep moving.",
        "body": "The need to stay emotionally upright inside ongoing collapse: doom as register, grief externalized into form, comedy and calm as civic medicine, refuge aesthetics. Not solving the unbearable, metabolizing it."},
    "unsettled": {"color": "#8f9092",
        "one": "The honest residue.",
        "body": "Signals processing no single need the taxonomy can see: pure formal play, craft-for-craft's-sake, and the emerging more-than-human cluster that may become an eighth need if it grows."},
}
DEFAULT_META = {"color": "#8f9092", "one": "", "body": ""}

CLUSTERS_PER_NEED = 3
ITEMS_PER_CLUSTER = 6
LABEL_TERMS = 3

STOP = set("""the a an and or of to in on for with from at by as is are was were be been being
it its this that these those they them their our your my his her he she we you i me
not no but so if then than too very just only also about into over under out up down off
new now more most some any all one two three what who how why when where which while
has have had do does did can could would should will may might must s t re ve ll d m
your you'll i'm don't it's that's there here their they're we're""".split())


def tokenize(text):
    return [w for w in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(w) >= 3 and w not in STOP]


def decode_vec(b64):
    if not b64:
        return None
    arr = [float(x) for x in base64.b64decode(b64)]
    # bytes are unsigned 0..255; int8 was stored, so map back to signed
    return [x - 256 if x > 127 else x for x in arr]


def normalize(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def kmeans(vectors, k, iters=25, seed=12345):
    """Tiny deterministic cosine k-means (vectors pre-normalized => dot = cos)."""
    n = len(vectors)
    if n == 0:
        return []
    k = min(k, n)
    # deterministic spread-out init: pick farthest-first
    centroids = [vectors[0]]
    while len(centroids) < k:
        best_i, best_d = 0, -1
        for i, v in enumerate(vectors):
            d = min(1 - dot(v, c) for c in centroids)
            if d > best_d:
                best_d, best_i = d, i
        centroids.append(vectors[best_i])
    assign = [0] * n
    for _ in range(iters):
        changed = False
        for i, v in enumerate(vectors):
            a = max(range(len(centroids)), key=lambda c: dot(v, centroids[c]))
            if a != assign[i]:
                assign[i] = a
                changed = True
        new = []
        for c in range(len(centroids)):
            members = [vectors[i] for i in range(n) if assign[i] == c]
            if members:
                dim = len(members[0])
                mean = [sum(m[j] for m in members) / len(members) for j in range(dim)]
                new.append(normalize(mean))
            else:
                new.append(centroids[c])
        centroids = new
        if not changed:
            break
    return assign, centroids


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def label_cluster(members, df, ndocs):
    """Top TF-IDF terms across the cluster's titles+summaries."""
    tf = Counter()
    for s in members:
        for w in set(tokenize((s.get("title") or "") + " " + (s.get("summary") or ""))):
            tf[w] += 1
    scored = []
    for w, f in tf.items():
        idf = math.log((ndocs + 1) / (df.get(w, 0) + 1)) + 1
        scored.append((f * idf, f, w))
    scored.sort(reverse=True)
    terms = [w for _, _, w in scored[:LABEL_TERMS]] or ["signals"]
    return " · ".join(terms)


def build_need(name, sigs, df, ndocs, code):
    meta = NEED_META.get(name, DEFAULT_META)
    n = len(sigs)
    vecd = [(s, normalize(v)) for s in sigs for v in [decode_vec(s.get("vec"))] if v]
    clusters = []
    if len(vecd) >= 2:
        vectors = [v for _, v in vecd]
        assign, centroids = kmeans(vectors, CLUSTERS_PER_NEED)
        groups = {}
        for (s, v), a in zip(vecd, assign):
            groups.setdefault(a, []).append((s, v))
        # order clusters largest-first
        for a in sorted(groups, key=lambda a: -len(groups[a])):
            members = groups[a]
            c = centroids[a]
            members.sort(key=lambda sv: -dot(sv[1], c))  # nearest centroid first
            items = [{"t": s.get("title") or "", "s": s.get("source") or ""}
                     for s, _ in members[:ITEMS_PER_CLUSTER]]
            clusters.append({"label": label_cluster([s for s, _ in members], df, ndocs),
                             "items": items})
    elif sigs:
        clusters.append({"label": label_cluster(sigs, df, ndocs),
                         "items": [{"t": s.get("title") or "", "s": s.get("source") or ""}
                                   for s in sigs[:ITEMS_PER_CLUSTER]]})
    return {"key": name, "n": n, "color": meta["color"],
            "one": meta["one"], "body": meta["body"], "code": code,
            "clusters": clusters}


def compute_geo():
    data = json.load(open(CORPUS))
    signals = data["signals"]
    total = len(signals)
    codes = {}
    if os.path.exists(CODES):
        codes = {k: v for k, v in json.load(open(CODES)).items() if not k.startswith("_")}

    by_need = {}
    for s in signals:
        by_need.setdefault(s.get("need") or "unsettled", []).append(s)

    # document frequency for TF-IDF, over the whole corpus
    df = Counter()
    for s in signals:
        for w in set(tokenize((s.get("title") or "") + " " + (s.get("summary") or ""))):
            df[w] += 1

    needs = []
    for name in sorted(by_need, key=lambda k: -len(by_need[k])):
        nd = build_need(name, by_need[name], df, total, codes.get(name))
        nd["pct"] = round(nd["n"] / total * 100, 1) if total else 0
        needs.append(nd)
    return {"needs": needs, "total": total}


def inject(html, value):
    start, end = "/*__GEO__*/", "/*__END__*/"
    i = html.index(start) + len(start)
    j = html.index(end, i)
    return html[:i] + value + html[j:]


def build(log=print):
    if not os.path.exists(TEMPLATE):
        raise SystemExit("template not found: " + TEMPLATE)
    geo = compute_geo()
    html = open(TEMPLATE).read()
    if "/*__GEO__*/" not in html:
        raise SystemExit("template is missing the /*__GEO__*/ marker around `const GEO = ...`")
    html = inject(html, json.dumps(geo, ensure_ascii=False))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    log("Wrote %s: %d needs, %d signals total." %
        (OUT, len(geo["needs"]), geo["total"]))
    return geo


if __name__ == "__main__":
    build()

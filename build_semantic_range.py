#!/usr/bin/env python3
"""Per-need semantic-range matrix ("Divergence Surface") for the geology globe.

For each need, break its signals into the same lexical clusters the universe/
search view uses (cosine k-means over the int8 embeddings, TF-IDF labels), then
find the need's two dominant semantic directions (PCA on its embeddings) and plot
each cluster on that plane. The axes are NOT the raw cluster terms: they are
hand-interpreted bipolar labels in `semantic_axes.json` (read the poles with
`--poles`, then name each axis). Emits one inline SVG per need, injected into the
globe callout by build_geology.py. Recompute each harvest (re-interpret axes when
the corpus shifts — see semantic_axes.json._note).

    python build_semantic_range.py --poles "Naming the Machine"   # dump poles to interpret
    python build_semantic_range.py --preview "Appetite"           # write one SVG to _semrange_<need>.svg
    python build_semantic_range.py                                # summary of all needs

Imported by build_geology.py: svgs_by_need(colors) -> {need: svg_string}.
"""
import base64, json, math, os, re, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus.json")
AXES = os.path.join(HERE, "semantic_axes.json")

# fallback need colours (mirrors build_geology.NEED_META); build_geology passes its own
NEED_COLORS = {
    "Naming the Machine": "#d671a8", "Settling Accounts": "#a884d6",
    "Self-Authorship": "#5b86d6", "Certified Human": "#d9a84e",
    "Kinship": "#3f9d96", "Appetite": "#e0654a", "Ballast": "#7fb069",
    "unsettled": "#8f9092",
}

STOP = set("""the a an and or of to in on for with from at by as is are was were be been being
it its this that these those they them their our your my his her he she we you i me
not no but so if then than too very just only also about into over under out up down off
new now more most some any all one two three what who how why when where which while
has have had do does did can could would should will may might must s t re ve ll d m""".split())

CLUSTER_LABEL_TERMS = 2


def tok(t):
    return [w for w in re.split(r"[^a-z0-9]+", (t or "").lower())
            if len(w) >= 3 and w not in STOP]


def decode(b64):
    arr = list(base64.b64decode(b64))
    return np.array([x - 256 if x > 127 else x for x in arr], dtype=float)


def kFor(n):
    return 0 if n < 8 else 2 if n <= 15 else 3 if n <= 30 else 4 if n <= 60 else 5


def kmeans(X, k, iters=25):
    cent = [X[0]]
    while len(cent) < k:
        dd = np.min([1 - X @ c for c in cent], axis=0)
        cent.append(X[int(np.argmax(dd))])
    C = np.vstack(cent)
    assign = np.full(len(X), -1)
    for _ in range(iters):
        a = np.argmax(X @ C.T, axis=1)
        if (a == assign).all():
            break
        assign = a
        for c in range(k):
            m = X[assign == c]
            if len(m):
                v = m.sum(0)
                C[c] = v / (np.linalg.norm(v) + 1e-9)
    return assign


def analyze(sigs):
    """-> (proj nx2, assign, ndocs, df). Empty-safe."""
    n = len(sigs)
    V = np.vstack([decode(s["vec"]) for s in sigs])
    Vn = V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
    k = kFor(n)
    assign = kmeans(Vn, k) if k else np.zeros(n, dtype=int)
    Vc = V - V.mean(0)
    _, S, Wt = np.linalg.svd(Vc, full_matrices=False)
    proj = Vc @ Wt[:2].T
    df = Counter()
    for s in sigs:
        for w in set(tok((s.get("title") or "") + " " + (s.get("summary") or ""))):
            df[w] += 1
    return proj, assign, n, df, (S[:2] ** 2 / (S ** 2).sum()) * 100


def label(sigs, idxs, df, n):
    tf = Counter()
    for i in idxs:
        for w in set(tok((sigs[i].get("title") or "") + " " + (sigs[i].get("summary") or ""))):
            tf[w] += 1
    sc = sorted(((f * (math.log((n + 1) / (df[w] + 1)) + 1), w) for w, f in tf.items()), reverse=True)
    return " · ".join(w for _, w in sc[:CLUSTER_LABEL_TERMS]) or "signals"


def clusters_for(sigs):
    proj, assign, n, df, ve = analyze(sigs)
    out = []
    for c in sorted(set(assign), key=lambda c: -int((assign == c).sum())):
        idxs = [i for i in range(n) if assign[i] == c]
        if not idxs:
            continue
        xy = proj[idxs].mean(0)
        out.append({"x": float(xy[0]), "y": float(xy[1]),
                    "n": len(idxs), "label": label(sigs, idxs, df, n)})
    return out, n, ve


def _esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def emit_svg(need, clusters, axes, n, color):
    W, H = 580, 440
    ML, MR, MT, MB = 78, 78, 48, 56
    cx0, cy0 = ML + (W - ML - MR) / 2, MT + (H - MT - MB) / 2
    halfW, halfH = (W - ML - MR) / 2, (H - MT - MB) / 2
    rad = lambda c: min(30.0, 9.0 + math.sqrt(c["n"]) * 3.0)
    maxr = max((rad(c) for c in clusters), default=12)
    mx = sum(c["x"] for c in clusters) / len(clusters) if clusters else 0
    my = sum(c["y"] for c in clusters) / len(clusters) if clusters else 0
    spanx = max((abs(c["x"] - mx) for c in clusters), default=1) or 1
    spany = max((abs(c["y"] - my) for c in clusters), default=1) or 1
    sx = (halfW - maxr - 10) / spanx
    sy = (halfH - maxr - 22) / spany   # extra top/bottom room for labels
    ax = axes.get(need, {"x": ["", ""], "y": ["", ""]})
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="Helvetica Neue,Helvetica,Arial,sans-serif" role="img" '
         f'aria-label="Semantic range within {_esc(need)}">']
    # axes cross
    p.append(f'<line x1="{ML}" y1="{cy0:.1f}" x2="{W-MR}" y2="{cy0:.1f}" stroke="rgba(255,255,255,.13)"/>')
    p.append(f'<line x1="{cx0:.1f}" y1="{MT}" x2="{cx0:.1f}" y2="{H-MB}" stroke="rgba(255,255,255,.13)"/>')
    # pole labels
    p.append(f'<text x="{ML-8}" y="{cy0+4:.1f}" fill="#cfc8ba" font-size="12" text-anchor="end">{_esc(ax["x"][0])}</text>')
    p.append(f'<text x="{W-MR+8}" y="{cy0+4:.1f}" fill="#cfc8ba" font-size="12">{_esc(ax["x"][1])}</text>')
    p.append(f'<text x="{cx0:.1f}" y="{MT-14}" fill="#cfc8ba" font-size="12" text-anchor="middle">{_esc(ax["y"][1])}</text>')
    p.append(f'<text x="{cx0:.1f}" y="{H-MB+26}" fill="#cfc8ba" font-size="12" text-anchor="middle">{_esc(ax["y"][0])}</text>')
    # bubbles
    for c in clusters:
        X = cx0 + (c["x"] - mx) * sx
        Y = cy0 - (c["y"] - my) * sy       # PC2 high -> top
        r = rad(c)
        p.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r:.1f}" fill="{color}" fill-opacity=".48" stroke="{color}" stroke-opacity=".9"/>')
        lab = c["label"]
        if len(lab) > 26:
            lab = lab[:25] + "…"
        ly = Y - r - 6 if Y - r - 6 > MT + 4 else Y + r + 14
        p.append(f'<text x="{X:.1f}" y="{ly:.1f}" fill="#ece7dd" font-size="10.5" text-anchor="middle">{_esc(lab)} <tspan fill="#8e887d">({c["n"]})</tspan></text>')
    p.append(f'<text x="{cx0:.1f}" y="{H-14}" fill="#6f6a61" font-size="9.5" text-anchor="middle">'
             f'lexical clusters across the theme’s two dominant axes · {n} signals · recomputed each harvest</text>')
    p.append("</svg>")
    return "".join(p)


def svgs_by_need(colors=None):
    colors = colors or NEED_COLORS
    data = json.load(open(CORPUS))
    axes = json.load(open(AXES)).get("needs", {}) if os.path.exists(AXES) else {}
    by = {}
    for s in data["signals"]:
        if s.get("vec"):
            by.setdefault(s.get("need") or "unsettled", []).append(s)
    out = {}
    for need, sigs in by.items():
        if len(sigs) < 2:
            continue
        clusters, n, _ = clusters_for(sigs)
        out[need] = emit_svg(need, clusters, axes, n, colors.get(need, "#8f9092"))
    return out


def _load_need(need):
    data = json.load(open(CORPUS))
    return [s for s in data["signals"] if s.get("need") == need and s.get("vec")]


def _dump_poles(need):
    sigs = _load_need(need)
    proj, _, n, _, ve = analyze(sigs)
    for ax in range(2):
        o = np.argsort(proj[:, ax])
        print(f"\n=== PC{ax+1} ({ve[ax]:.0f}% var) — NEGATIVE pole ===")
        for i in o[:7]:
            print("  -", (sigs[i]["title"] or "")[:88], "|", sigs[i].get("source"))
        print(f"--- PC{ax+1} — POSITIVE pole ---")
        for i in o[-7:]:
            print("  +", (sigs[i]["title"] or "")[:88], "|", sigs[i].get("source"))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--poles":
        _dump_poles(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "--preview":
        need = sys.argv[2]
        axes = json.load(open(AXES)).get("needs", {})
        clusters, n, ve = clusters_for(_load_need(need))
        svg = emit_svg(need, clusters, axes, n, NEED_COLORS.get(need, "#8f9092"))
        outp = os.path.join(HERE, "_semrange_" + re.sub(r"[^a-z0-9]+", "_", need.lower()) + ".svg")
        open(outp, "w").write(svg)
        print("wrote", outp, "| PC var:", [round(x, 1) for x in ve])
    else:
        for need, svg in svgs_by_need().items():
            print(f"{need}: {len(svg)} chars")

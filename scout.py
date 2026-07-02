#!/usr/bin/env python3
"""Cultural Scout retrieval — quiz the whole multi-run corpus by free text.

This is the scout's eyes. You ask in plain language about an AREA — a theme, a
tension, a brand problem, a category, a feeling — and it surfaces the most
relevant signals across every harvest run, ranked by relevance. No substrate
pools as a front door; substrate is shown as metadata only.

    python scout.py "masculinity and food"
    python scout.py "AI grief mourning the dead" --full
    python scout.py "nostalgia, aspiration, quiet luxury" --limit 40
    python scout.py "running marathon endurance" --json > hits.json
    python scout.py --browse              # corpus overview, no query

Ranking is keyword density across title/summary/novelty/cross-notes/category/
source, lightly boosted for forward_looking and for appearing in multiple runs.
It surfaces CANDIDATES; the scout (Claude) does the semantic judgement on top.
"""
import argparse, json, os, re, sys, textwrap
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus.json")

STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
        "is", "are", "as", "at", "by", "it", "its", "about", "into", "that",
        "this", "what", "do", "you", "have", "any", "signals", "signal"}

# 2-letter terms that are real queries, not noise (matched as whole words only)
SHORT_OK = {"ai", "uk", "us", "tv", "vr"}

# field -> weight
WEIGHTS = {"title": 3.0, "summary": 2.0, "novelty_note": 2.0,
           "cross_substrate_notes": 1.0, "category": 2.0, "source": 1.0,
           "recommended_substrate": 1.0, "need": 1.0}

# ---- query expansion -------------------------------------------------------
# Curated synonym map tuned to cultural-strategy vocabulary. Expanded terms
# score at half the weight of the term the user actually typed. Grow this
# freely — one entry per line, keep it boring and literal.
# NOTE: mirrored in site/template.html (window-side SYNONYMS). Keep in sync.
SYNONYMS = {
    "ai":          ["artificial", "intelligence", "algorithm", "algorithmic", "chatbot", "llm", "machine"],
    "beauty":      ["aesthetic", "cosmetic", "skincare", "grooming", "makeup"],
    "wellness":    ["health", "wellbeing", "therapy", "healing", "mindfulness"],
    "sport":       ["athlete", "athletic", "fitness", "running", "gym", "training"],
    "money":       ["wealth", "financial", "economic", "income", "class", "capitalism"],
    "masculinity": ["men", "male", "manhood", "masculine"],
    "men":         ["masculinity", "male", "manhood"],
    "femininity":  ["women", "female", "womanhood", "feminine", "girlhood"],
    "women":       ["femininity", "female", "womanhood"],
    "intimacy":    ["closeness", "tenderness", "romance", "desire", "eroticism"],
    "community":   ["belonging", "collective", "gathering", "communal"],
    "nostalgia":   ["retro", "vintage", "longing", "memory", "archival"],
    "luxury":      ["premium", "opulence", "wealth", "aspirational"],
    "food":        ["culinary", "eating", "restaurant", "cooking", "cuisine", "dining"],
    "fashion":     ["clothing", "apparel", "garment", "style", "dress"],
    "internet":    ["online", "digital", "platform", "virality", "meme"],
    "work":        ["labor", "labour", "career", "workplace", "job", "hustle"],
    "identity":    ["selfhood", "persona", "self"],
    "ritual":      ["ceremony", "practice", "tradition", "rite"],
    "authenticity": ["authentic", "sincerity", "genuine"],
    "queer":       ["lgbtq", "gay", "lesbian", "trans", "drag"],
    "aging":       ["age", "aged", "older", "elder", "elderly", "longevity"],
    "craft":       ["handmade", "artisan", "craftsmanship", "maker"],
    "celebrity":   ["fame", "stardom", "influencer", "parasocial"],
    "music":       ["song", "album", "pop", "sound", "sonic"],
    "film":        ["cinema", "movie", "documentary", "director"],
    "home":        ["domestic", "interior", "household", "dwelling"],
    "body":        ["embodied", "physical", "flesh", "corporeal"],
    "death":       ["grief", "mourning", "mortality", "funeral"],
    "grief":       ["death", "mourning", "loss"],
    "technology":  ["digital", "device", "software", "tech"],
    "spirituality": ["religion", "sacred", "faith", "mysticism", "astrology"],
    "status":      ["prestige", "taste", "distinction", "aspiration"],
    "loneliness":  ["isolation", "alone", "solitude", "disconnection"],
    "slowness":    ["slow", "leisure", "rest", "idleness"],
}


def load():
    if not os.path.exists(CORPUS):
        sys.exit("corpus.json not found — run: python build_corpus.py")
    with open(CORPUS) as f:
        return json.load(f)


def terms(q):
    raw = [t for t in re.split(r"[^a-z0-9]+", q.lower()) if t and t not in STOP]
    return [t for t in raw if len(t) > 2 or t in SHORT_OK]


def expand(ts):
    """[(term, weight, parent)] — typed terms at 1.0, synonyms at 0.5."""
    out = []
    for t in ts:
        out.append((t, 1.0, t))
        for syn in SYNONYMS.get(t, []):
            out.append((syn, 0.5, t))
    return out


# Inflectional endings (plural/tense/gerund/comparative) longer than 2 chars
# that are still a valid stem match. 1-2 char tails (s, es, ed, d, ly...) are
# always allowed; longer tails must be one of these. NOTE: mirrored in
# site/template.html (INFLECT). Keep the two in sync.
INFLECT = {"ing", "ings", "ers", "ier", "iest", "ied", "ling"}


def _stem_ok(longer, shorter):
    suf = longer[len(shorter):]
    return len(suf) <= 2 or suf in INFLECT


def word_match(word, term):
    """Word-boundary matching with cheap symmetric stemming. A prefix match is
    accepted only when the extra letters form a real inflectional ending, NOT an
    arbitrary longer word: 'rest' matches 'rests/rested/resting' but NOT
    'restores/restaurant'; 'ritual' still matches 'rituals'. Stem must be >=4
    chars; short whitelisted terms (ai, uk...) match exact-only."""
    if word == term:
        return True
    if term in SHORT_OK:
        return False
    if len(term) >= 4 and word.startswith(term):
        return _stem_ok(word, term)
    if len(word) >= 4 and term.startswith(word):
        return _stem_ok(term, word)
    return False


def field_words(sig, field, _cache={}):
    key = (id(sig), field)
    if key not in _cache:
        _cache[key] = re.findall(r"[a-z0-9]+", str(sig.get(field) or "").lower())
    return _cache[key]


def score(sig, ts, runs):
    expanded = expand(ts)
    sc = 0.0
    hit_parents = set()
    for field, w in WEIGHTS.items():
        words = field_words(sig, field)
        if not words:
            continue
        for term, tw, parent in expanded:
            n = sum(1 for word in words if word_match(word, term))
            if n:
                sc += w * tw * n
                hit_parents.add(parent)
    if not sc:
        return 0.0
    # reward breadth of distinct TYPED query terms matched (synonyms count
    # toward the term they expand)
    sc *= (1 + 0.5 * (len(hit_parents) - 1))
    # core tier is the strict forward-looking gate — boost it. (forward_looking
    # itself is on 81% of signals, so it distinguishes nothing; no boost.)
    if sig.get("tier") == "core":
        sc *= 1.2
    if len(sig.get("_runs", [])) > 1:
        sc *= 1.1
    # gentle recency tilt: 0.92x per run older than the latest harvest
    if runs:
        first = sig.get("_first_seen")
        idx = runs.index(first) if first in runs else len(runs) - 1
        sc *= 0.92 ** (len(runs) - 1 - idx)
    return sc


def browse(data):
    print(f"Corpus: {data['total_signals']} unique signals across runs "
          f"{', '.join(data['runs'])}.")
    needs = Counter(s.get("need") or "untagged" for s in data["signals"])
    subs = Counter(s.get("recommended_substrate") for s in data["signals"])
    cats = Counter(s.get("category") or "untagged" for s in data["signals"])
    fwd = sum(1 for s in data["signals"] if s.get("forward_looking"))
    print(f"forward_looking: {fwd}\n")
    print("need (primary taxonomy, 2026-06):", dict(needs))
    print("substrate (legacy metadata):", dict(subs))
    print("category:", dict(cats))
    print("\nQuiz the scout with free text, e.g.:")
    print('  python scout.py "longing for slowness, anti-optimization"')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="free-text area of interest")
    ap.add_argument("--limit", type=int, default=25, help="max hits (default 25)")
    ap.add_argument("--full", action="store_true", help="show novelty + cross-substrate notes")
    ap.add_argument("--json", action="store_true", help="emit hits as JSON for generation")
    ap.add_argument("--browse", action="store_true", help="corpus overview, no query")
    ap.add_argument("--exclude-need", action="append", default=[], metavar="NEED",
                    help="drop a need from the results (repeatable) — mirrors the site's "
                         "filter-against-the-dominant-need dial. Pure post-filter, no ranking change.")
    args = ap.parse_args()

    data = load()

    if args.browse or not args.query:
        browse(data)
        return

    q = " ".join(args.query)
    ts = terms(q)
    if not ts:
        sys.exit("Query had no searchable terms.")

    drop = {n.lower() for n in args.exclude_need}
    scored = [(score(s, ts, data.get("runs", [])), s) for s in data["signals"]]
    scored = [(sc, s) for sc, s in scored if sc > 0
              and (s.get("need") or "unsettled").lower() not in drop]
    scored.sort(key=lambda x: (-x[0], -(len(x[1].get("_runs", [])))))
    hits = scored[:args.limit]

    if args.json:
        json.dump([s for _, s in hits], sys.stdout, indent=2, ensure_ascii=False)
        return

    print(f'"{q}"  →  {len(scored)} relevant, showing top {len(hits)} '
          f'(terms: {", ".join(ts)})\n')
    for sc, s in hits:
        runs = "+".join(r[5:] for r in s.get("_runs", []))  # MM-DD per run
        fl = "→fwd" if s.get("forward_looking") else "    "
        cat = s.get("category") or "—"
        print(f"[{sc:5.1f}] {s.get('need') or s.get('recommended_substrate','?')}/{s.get('fit_confidence','?')} "
              f"{fl}  {cat:<12} {s['source']} · {s['date']}  runs:{runs}")
        print(f"        {s['title']}")
        print(f"        {textwrap.shorten(s['summary'], 220)}")
        if args.full:
            if s.get("novelty_note"):
                print(f"        novelty: {s['novelty_note']}")
            if s.get("cross_substrate_notes"):
                print(f"        cross:   {s['cross_substrate_notes']}")
        print(f"        {s['url']}\n")


if __name__ == "__main__":
    main()

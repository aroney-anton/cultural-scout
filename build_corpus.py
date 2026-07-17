#!/usr/bin/env python3
"""Merge every tagged run into one corpus the Cultural Scout loads.

Auto-discovers every `tagged_signals*.json` in this directory, reads each
file's own `tagging_date` as the run id (filename-independent), normalizes the
schema across runs, dedupes by URL across runs, and records per-signal run
provenance. Re-runnable: drop a new run's tagged file in the dir and re-run.

    python build_corpus.py            # writes corpus.json
    python build_corpus.py --stats    # also print a summary

This replaces the old pool-sorting front door. The corpus keeps substrate tags
as metadata, but retrieval is now free-text quizzing via scout.py — not pools.
"""
import argparse, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "corpus.json")

# Per-run methodological notes surfaced next to the need-distribution chart.
# Add a dated note whenever a run's intake changed in a way that shifts the
# distribution for non-cultural reasons (new sources, dropped sources, etc.).
RUN_NOTES = {
    "2026-06-11": "source set expanded this run; share shifts partly reflect intake change, not culture moving",
    "2026-06-22": "13 art institutions (new 'museum' category) ingested for the first time this run; some share shifts (esp. Settling Accounts, Certified Human) reflect that intake change, not culture moving",
}

# Canonical per-signal fields. April run lacks `category` and `tier`; we backfill.
FIELDS = ["id", "source", "category", "title", "url", "date", "summary",
          "forward_looking", "recommended_substrate", "fit_confidence",
          "cross_substrate_notes", "novelty_note", "tier", "need"]


def norm_url(u):
    return (u or "").strip().rstrip("/").lower()


def norm_title(t):
    """Normalized title for the merge key, so distinct articles that share a
    homepage-level URL (e.g. the April 032c root-URL items) are NOT collapsed."""
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def same_article(t1, t2):
    """Same URL + 'same-ish' title = same article. Harvests retitle slightly
    between runs ('Without Exception' vs 'Without Exception: The Photography
    of Mao Ishikawa'), so match on exact, prefix, or token containment."""
    a, b = norm_title(t1), norm_title(t2)
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    wa, wb = set(a.split()), set(b.split())
    if not wa or not wb:
        return False
    return wa <= wb or wb <= wa


def load_runs():
    files = sorted(glob.glob(os.path.join(HERE, "tagged_signals*.json")))
    runs = []
    for f in files:
        with open(f) as fh:
            d = json.load(fh)
        run_date = d.get("tagging_date") or os.path.basename(f)
        runs.append({"file": os.path.basename(f), "run_date": run_date,
                     "signals": d.get("signals", [])})
    # oldest -> newest, so newer run records win on merge
    runs.sort(key=lambda r: r["run_date"])
    return runs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stats", action="store_true", help="print a summary after building")
    ap.add_argument("--require-embeddings", action="store_true",
                    help="hard-stop if the local embedding model is unavailable "
                         "(used by the one-off backfill so it never ships a half-build); "
                         "by default the embedding step degrades gracefully and the "
                         "corpus still builds without vectors")
    args = ap.parse_args()

    runs = load_runs()
    if not runs:
        sys.exit("No tagged_signals*.json files found in " + HERE)

    # url -> list of records. Same URL + same-ish title merges (run provenance
    # kept); distinct articles stuck with a shared root URL stay distinct.
    merged = {}
    for run in runs:
        rd = run["run_date"]
        for s in run["signals"]:
            key = norm_url(s.get("url")) or s.get("id")
            rec = {k: s.get(k) for k in FIELDS}
            rec.setdefault("category", None)
            rec.setdefault("tier", None)
            group = merged.setdefault(key, [])
            prev = next((p for p in group
                         if same_article(p.get("title"), rec.get("title"))), None)
            if prev is not None:
                # newer run wins on content (runs are oldest->newest); keep run history
                rec["_runs"] = sorted(set(prev["_runs"]) | {rd})
                rec["_first_seen"] = prev["_first_seen"]
                # don't lose a category/tier the newer run might be missing
                rec["category"] = rec["category"] or prev.get("category")
                rec["tier"] = rec["tier"] or prev.get("tier")
                group[group.index(prev)] = rec
            else:
                rec["_runs"] = [rd]
                rec["_first_seen"] = rd
                group.append(rec)

    signals = [rec for group in merged.values() for rec in group]
    signals.sort(key=lambda s: (s.get("_first_seen") or "", s.get("source") or ""))

    # Need distribution per run, computed from each run's OWN signals (not the
    # deduped corpus) so every harvest is an honest snapshot of that month's
    # intake. Feeds the site's need-distribution-over-time chart, which the
    # template only renders once 3+ runs exist (two points are a line, not a
    # signal).
    from collections import Counter
    need_history = []
    for run in runs:
        needs = Counter(s.get("need") or "unsettled" for s in run["signals"])
        need_history.append({
            "run": run["run_date"],
            "n": len(run["signals"]),
            "needs": dict(needs),
            "note": RUN_NOTES.get(run["run_date"], ""),
        })

    # Tier-2 build-time embeddings (offline, local model). Attaches a base64
    # int8 `vec` to each signal and returns PCA/scale metadata. Incremental:
    # only NEW signals are embedded (raw float cache in .emb_cache.npz). Degrades
    # gracefully when the model isn't available, unless --require-embeddings.
    embedding_meta = None
    try:
        import embed as _embed
        embedding_meta = _embed.embed(signals, require=args.require_embeddings,
                                      log=lambda m: print("  [embed]", m))
    except SystemExit:
        raise
    except Exception as e:
        if args.require_embeddings:
            sys.exit("STOP: embedding step failed: %s" % e)
        print("  [embed] WARNING: embedding step errored, continuing without vectors:", e)

    out = {
        "generated_from": [{"file": r["file"], "run_date": r["run_date"],
                            "signals": len(r["signals"])} for r in runs],
        "runs": [r["run_date"] for r in runs],
        "need_history": need_history,
        "total_signals": len(signals),
        "signals": signals,
    }
    if embedding_meta:
        out["embedding"] = embedding_meta
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(f"Wrote {OUT}: {len(signals)} unique signals across {len(runs)} run(s).")
    for r in out["generated_from"]:
        print(f"  {r['run_date']}  {r['file']:<40} {r['signals']:>4} signals")

    # Also refresh the standalone website if its builder is present, so one
    # command keeps corpus.json and the shareable site/index.html in sync.
    # (build_site.py itself chains build_geology.py, so this one call keeps
    # the Explore globe in sync too — verified 2026-07-17.)
    site_builder = os.path.join(HERE, "build_site.py")
    if os.path.exists(site_builder):
        import subprocess
        print()
        subprocess.run([sys.executable, site_builder], check=False)

    if args.stats:
        from collections import Counter
        subs = Counter(s.get("recommended_substrate") for s in signals)
        cats = Counter(s.get("category") for s in signals)
        multi = sum(1 for s in signals if len(s["_runs"]) > 1)
        fwd = sum(1 for s in signals if s.get("forward_looking"))
        print(f"\nappeared in >1 run: {multi}   forward_looking: {fwd}")
        print("substrate:", dict(subs))
        print("category:", dict(cats))
        print("\nneed distribution per run (share of that run's signals):")
        for h in need_history:
            shares = {k: f"{v/h['n']*100:.0f}%" for k, v in
                      sorted(h["needs"].items(), key=lambda kv: -kv[1])}
            note = f"   [{h['note']}]" if h.get("note") else ""
            print(f"  {h['run']} (n={h['n']}): {shares}{note}")

        # Balance report: corpus-wide need share + theme-gravity warning.
        # Any need over CEILING is genre-flattering the corpus and its tagging
        # gate should tighten (see the Phase 1 theme-gravity gate in CLAUDE.md).
        CEILING = 0.20
        need_counts = Counter(s.get("need") or "unsettled" for s in signals)
        total = len(signals) or 1
        print("\nbalance report — need share of the whole corpus "
              f"(ceiling {CEILING*100:.0f}%):")
        over = []
        for need, c in sorted(need_counts.items(), key=lambda kv: -kv[1]):
            share = c / total
            flag = "  <-- OVER CEILING" if share > CEILING else ""
            if share > CEILING:
                over.append((need, share))
            print(f"  {need:<22} {c:>4}  {share*100:5.1f}%{flag}")
        if over:
            names = ", ".join(f"{n} ({s*100:.0f}%)" for n, s in over)
            print(f"\n  WARNING: {len(over)} need(s) over the {CEILING*100:.0f}% "
                  f"ceiling: {names}.")
            print("  Tighten these needs' tagging gate next run (payload must BE "
                  "the need, not merely adjacent). See CLAUDE.md theme-gravity gate.")
        else:
            print(f"\n  OK: no need exceeds the {CEILING*100:.0f}% ceiling.")


if __name__ == "__main__":
    main()

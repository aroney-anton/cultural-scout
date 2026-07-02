#!/usr/bin/env python3
"""Offline (build-time) embeddings + PCA + int8 quantization for the corpus.

TIER 2. This is the ONLY place a model is used, and it runs LOCALLY at build
time. The shipped site carries the resulting int8 vectors and runs NO model, key,
or worker on the page. The project is solely a cultural-discovery instrument.

Pipeline (fixed, per the build-time-embeddings task):
  1. Embed each signal from its title + summary with a local sentence-transformer
     (BAAI/bge-small-en-v1.5, 384-dim). No external API, no key. Falls back to
     fastembed (the SAME bge-small ONNX weights, no torch) when sentence-
     transformers / torch is not installed.
  2. Cache the raw float vectors keyed by a hash of the embedded text in
     `.emb_cache.npz`, so monthly runs only embed the NEW signals (incremental).
     The first run backfills the whole corpus.
  3. L2-normalize the floats -> PCA-reduce to 128 dims -> int8-quantize with one
     global scale.
  4. Each signal gets `vec` = base64(int8[128]). The PCA mean/components + scale
     are returned as build metadata (stored in corpus.json) so the float vectors
     can be reconstructed if ever needed. The PCA matrix is NOT shipped to the
     site: the browser only needs the per-signal int8 vectors for cosine
     clustering (the global scale cancels in cosine, so it isn't needed either).

Graceful degradation: if neither library is importable, or the model can't be
downloaded/run, embed() returns None and the corpus builds WITHOUT vectors (the
site's clustering strip simply stays hidden). Pass require=True to turn that into
a hard stop instead (used by the one-off backfill so it never ships a half-build).

Cosine similarity on the int8 vectors approximates cosine on the original
embeddings closely enough for clustering: the global scale cancels, and PCA keeps
the dominant directions. Reconstruction fidelity is not the goal; cluster shape is.
"""
import base64
import hashlib
import os
import sys

MODEL_NAME = "BAAI/bge-small-en-v1.5"
PCA_DIM = 128
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".emb_cache.npz")


def _text(s):
    """The text we embed: title + summary, the two human-meaningful fields."""
    return ((s.get("title") or "").strip() + " . " + (s.get("summary") or "").strip()).strip()


def _h(t):
    return hashlib.sha1(t.encode("utf-8")).hexdigest()


def _loader():
    """Return (encode_fn, source_label) or (None, reason).

    encode_fn(list[str]) -> np.ndarray[float32, (n, 384)]. Prefer the named tool
    (sentence-transformers); fall back to fastembed, which runs the same ONNX
    weights without torch. Model download happens on first use of either.
    """
    import numpy as np
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(MODEL_NAME)

        def enc(texts):
            return np.asarray(
                m.encode(list(texts), batch_size=64, show_progress_bar=False,
                         normalize_embeddings=False),
                dtype="float32")
        return enc, "sentence-transformers:" + MODEL_NAME
    except Exception as e1:
        try:
            # fastembed talks to HF over httpx; the sandbox's socks ALL_PROXY
            # 403s, so prefer the plain HTTP proxy if one is set.
            os.environ.pop("ALL_PROXY", None)
            os.environ.pop("all_proxy", None)
            from fastembed import TextEmbedding
            m = TextEmbedding(MODEL_NAME)

            def enc(texts):
                return np.asarray(list(m.embed(list(texts))), dtype="float32")
            return enc, "fastembed:" + MODEL_NAME
        except Exception as e2:
            return None, ("no embedding backend (sentence-transformers: %s; "
                          "fastembed: %s)" % (e1, e2))


def _load_cache():
    import numpy as np
    if not os.path.exists(CACHE):
        return {}
    try:
        z = np.load(CACHE, allow_pickle=False)
        H, V = z["h"], z["v"]
        return {str(H[i]): V[i].astype("float32") for i in range(len(H))}
    except Exception:
        return {}


def _save_cache(cache):
    import numpy as np
    hs = list(cache.keys())
    np.savez(CACHE, h=np.array(hs), v=np.stack([cache[h] for h in hs]).astype("float32"))


def _b64f32(arr):
    import numpy as np
    return base64.b64encode(np.asarray(arr, dtype="float32").tobytes()).decode("ascii")


def embed(signals, require=False, log=print):
    """Attach base64 int8 `vec` to each signal in place. Returns build metadata
    dict, or None if embeddings were skipped (and not required)."""
    try:
        import numpy as np
    except Exception as e:
        msg = "numpy unavailable: %s" % e
        if require:
            sys.exit("STOP: " + msg)
        log("WARNING: " + msg + " - corpus built WITHOUT vectors.")
        return None

    cache = _load_cache()
    for s in signals:
        s["__h"] = _h(_text(s))
    missing = sorted({s["__h"] for s in signals if s["__h"] not in cache})

    src = "cache"
    if missing:
        enc, src = _loader()
        if enc is None:
            # No backend reachable. Instead of dropping vectors for the WHOLE
            # corpus (which would disable the site's clustering), degrade per
            # signal: keep every signal already in the cache and let only the
            # brand-new ones ship without a vec (the site drops null vecs and
            # simply excludes them from clustering until the next embed on a
            # model-reachable machine). require=True still hard-stops.
            if require:
                sys.exit("STOP: " + src)
            cached_n = sum(1 for s in signals if s["__h"] in cache)
            if not cached_n:
                log("WARNING: " + src + " - corpus built WITHOUT vectors.")
                for s in signals:
                    s.pop("__h", None)
                return None
            log("WARNING: " + src + " - embedding the %d cached signal(s) from cache; "
                "%d new signal(s) ship WITHOUT a vec until the next embed on a "
                "model-reachable machine." % (cached_n, len(missing)))
            enc = None  # fall through to cache-only assembly below
        if enc is not None:
            h2t = {}
            for s in signals:
                if s["__h"] in cache or s["__h"] in h2t:
                    continue
                h2t[s["__h"]] = _text(s)
            hs = list(h2t)
            try:
                vecs = enc([h2t[h] for h in hs])
            except Exception as e:
                msg = "model could not embed (download/network blocked?): %s" % e
                if require:
                    sys.exit("STOP: " + msg)
                log("WARNING: " + msg + " - corpus built WITHOUT vectors.")
                for s in signals:
                    s.pop("__h", None)
                return None
            for h, v in zip(hs, vecs):
                cache[h] = np.asarray(v, dtype="float32")
            _save_cache(cache)
            log("embedded %d new text(s) via %s; cache now holds %d" % (len(hs), src, len(cache)))
    else:
        log("all %d signals already embedded (incremental cache hit)" % len(signals))

    # assemble only signals we have a cached vector for; any others (brand-new
    # signals harvested while the model backend was unreachable) ship without a
    # vec and are simply excluded from clustering until the next embed run.
    have = [s for s in signals if s["__h"] in cache]
    skipped = len(signals) - len(have)
    M = np.stack([cache[s["__h"]] for s in have]).astype("float32")
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    M = M / norms

    # PCA via SVD (centered)
    mean = M.mean(axis=0)
    Mc = M - mean
    k = min(PCA_DIM, Mc.shape[0], Mc.shape[1])
    _, _, Vt = np.linalg.svd(Mc, full_matrices=False)
    comps = Vt[:k]                  # (k, raw_dim)
    P = Mc @ comps.T               # (N, k)

    # int8 quantize with a single global scale (cosine-preserving on the client)
    scale = float(np.abs(P).max()) / 127.0
    if scale == 0:
        scale = 1.0
    Q = np.clip(np.rint(P / scale), -127, 127).astype("int8")

    for i, s in enumerate(have):
        s["vec"] = base64.b64encode(Q[i].tobytes()).decode("ascii")
    for s in signals:
        s.pop("__h", None)
    if skipped:
        log("NOTE: %d signal(s) shipped without a vec (not yet embedded)" % skipped)

    meta = {
        "model": src,
        "raw_dim": int(M.shape[1]),
        "dim": int(k),
        "scale": scale,
        "comp_shape": [int(k), int(M.shape[1])],
        "pca_mean_b64": _b64f32(mean),
        "pca_components_b64": _b64f32(comps.reshape(-1)),
        "count": len(have),
    }
    log("vectors: %d signals x %d int8 dims, scale=%.6f" % (len(have), k, scale))
    return meta


if __name__ == "__main__":
    import json
    corpus = os.path.join(HERE, "corpus.json")
    d = json.load(open(corpus))
    meta = embed(d["signals"], require=True)
    d["embedding"] = meta
    json.dump(d, open(corpus, "w"), indent=2, ensure_ascii=False)
    print("backfilled corpus.json with %d-dim int8 vectors." % meta["dim"])

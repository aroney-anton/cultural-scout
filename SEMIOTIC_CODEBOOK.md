# SEMIOTIC CODEBOOK — discipline for need-level code derivation
*Created 2026-06-12 (Certified Human pilot). Sibling to NEED_TAXONOMY.md: that file defines WHAT the needs are; this file defines how their LOOK, FEEL, and LANGUAGE are coded.*

## What a code is
A **code** is a recurring, nameable signifying pattern through which a need is currently expressed in culture — a stable bundle of visual choices (palette, material, composition, casting, typography) and verbal choices (lexicon, metaphor, register) that different, independent cultural actors keep reaching for. A code must be:
- **Specific enough to brief from.** A designer or writer reading the code could execute in it tomorrow.
- **Broad enough to recur.** Found in ≥4 independent sources across ≥2 corpus categories. One photographer's style is a signature, not a code.
- **Anchored to the need.** The code is how the need signifies, not just an aesthetic that co-occurs with it.

3-6 codes per need. More than 6 means you are cataloguing executions; fewer than 3 means the need is under-evidenced — gather more before coding.

## Status taxonomy (Raymond Williams — same frame Klein uses to audit trend reports)
- **residual** — formed in the past, still actively signifying. Often what clients default to; flag it so they know.
- **dominant** — the current mainstream expression. Safe, legible, increasingly invisible.
- **emergent** — new meanings and practices still being formed. The brief-changing register. Tag honestly: most material is NOT emergent (the corpus's whole critique of the category).

Each code carries one status per run. Status changes across runs ARE the semiotic trajectory — they are findings, record them with justification.

## Update rules (the stability discipline — what "lightly update" means, enforced)
Codes have **stable slug IDs** that never change once coined. Per run, an updater may ONLY:
1. **Append evidence** to an existing code (new signals/images that express it).
2. **Move status** (residual/dominant/emergent) with a written justification in `history`.
3. **Propose a new code** — only if ≥4 independent sources in THIS run's intake demand it.
4. **Retire a code** — set `retired: <run>` with justification; never delete the record.
Descriptions are never rewritten wholesale. Wording edits beyond evidence/status require a human-supervised session (same boundary as indicator pulls). Every change appends to the code's `history` array: {run, change, note}. APPEND, never overwrite.

## Evidence standards (one-strike, visual edition)
- Every visual claim (palette, texture, composition) must be traceable to cited article imagery — each code's `evidence` array links the articles whose images ground it.
- **NEVER store or republish harvested images.** Analysis is reading; republishing is reproduction. Codes render as DERIVED ARTIFACTS only: palette swatches, texture/composition descriptors, lexicon chips, short attributed quotes (≤15 words, linked).
- Verbal evidence: quotes verbatim from the article, attributed, linked. No paraphrase presented as quote.
- Palette hexes are observational approximations from imagery, labeled as such ("observed palette"), never claimed as brand-spec values.

## Image sampling protocol (per run, per need)
- Sample signals ranked: tier core first, then forward_looking, then recency; bias to visually rich categories (art, fashion, embodied, design, global).
- View article pages in the browser; observe per distinct image: subject, setting, palette (3-5 dominant colors, approx hex), light, texture/material, composition/framing, typography if present, human presence and casting, craft/process markers, tech markers, overall register.
- Target 60-80 images for initial coding of a need; ~25-40 for a monthly maintenance pass. STOP early if codes have clearly separated (fidelity over volume); push to the top of the range if they haven't.

## Output schema — codes_<need_slug>.json
```json
{
  "need": "Certified Human",
  "updated": "YYYY-MM-DD",
  "runs_covered": ["..."],
  "images_observed": 0,
  "codes": [
    {
      "id": "stable-slug",
      "name": "Human-readable name",
      "status": "residual|dominant|emergent",
      "one_liner": "The code in one sentence.",
      "definition": "2-4 sentences: what the pattern is and how it signifies the need.",
      "visual": {
        "palette": [{"hex": "#aabbcc", "name": "descriptor"}],
        "materials_textures": ["..."],
        "composition": ["..."],
        "typography": ["..."],
        "casting_setting": ["..."]
      },
      "verbal": {
        "lexicon": ["..."],
        "metaphors": ["..."],
        "register": "...",
        "sample_phrases": [{"quote": "≤15 words, verbatim", "source": "...", "url": "..."}]
      },
      "tensions": "What this code defines itself against.",
      "execution_notes": "How a client team uses or misuses this code.",
      "evidence": [{"signal_id": "...", "source": "...", "url": "...", "note": "what the imagery/text showed"}],
      "confidence": "high|medium|low",
      "first_coded": "YYYY-MM-DD",
      "history": [{"run": "YYYY-MM-DD", "change": "coined|evidence|status|retired", "note": "..."}]
    }
  ]
}
```

## Validation gate (house rule)
A need's codes pass only if the answer to "would these change a client execution?" is yes — reviewed by Michael before the system scales past the pilot need or into UI work.

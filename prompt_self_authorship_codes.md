Run the semiotic-codes pilot for the "Self-Authorship" need, following the same process used for Certified Human (see CLAUDE.md, section "SEMIOTIC CODES — pilot" and "IMAGE SCRAPER + CONTACT-SHEET ANALYSIS"). Read SEMIOTIC_CODEBOOK.md and codes_certified_human.json first as the reference pattern before doing anything else.

Steps:

1. Round 1 scrape. Pull Self-Authorship article URLs from corpus.json and run the scraper:
   cd image_scraper && python run.py scrape --need "Self-Authorship"
   Respect the existing caps (--max-per-article 15, --target-images 250) and the URL-fed design rule, do not crawl homepages or add new sources.

2. Build contact sheets:
   python run.py sheets
   Keep the sidecar JSON mapping so every visual reading traces back to its source article.

3. Visual coding pass. Read the contact sheets and, using SEMIOTIC_CODEBOOK.md's discipline (dominant/residual/emergent status, evidence standards, STABLE-ID rules), draft candidate codes for Self-Authorship the way codes_certified_human.json did for its need: aim for 4-6 codes with clear register descriptions, palette/visual descriptors, and short attributed quotes (max 15 words) as evidence.

4. Gap-fill with WebSearch toward roughly 20 distinct-source images per code where the round 1 pool is thin on a candidate code.

5. Round 2 scrape against any newly found URLs (--urls file.txt), then re-run sheets.

6. Write codes_self-authorship.json in the same schema as codes_certified_human.json (id, status, description, palette, quotes, image_refs as hotlinks only, evidence links, trajectory). Do NOT store or copy any images into the project, image_refs must be live hotlinks to the publishers' own servers with referrerpolicy=no-referrer, credited, click-through.

7. Run image_scraper/run.py clean to delete the temp cache once coding is done.

8. Report back: how many articles/images went into the pool, the resulting codes with one-line rationale each, and any sources that were bot-hostile, paywalled, or otherwise thin (same as the dezeen/Met/newsletter learnings logged for Certified Human) so CLAUDE.md can be updated.

Do not touch sources.yaml, do not deploy, do not grade the Receipts scorecard. This is a pilot pass, gate it the same way Certified Human was gated before any scale-out to other needs.

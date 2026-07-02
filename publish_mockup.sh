#!/usr/bin/env bash
# One command to publish the geological Discover globe (and its look & feel page).
# The Discover globe is now BUILT from the live corpus (build_geology.py bakes GEO
# from corpus.json into site/discover-geology.html) instead of copying a frozen
# snapshot — so it stays in sync with the Search tab. The look & feel page is still
# a static copy. Does NOT rebuild the corpus itself (run build_corpus.py for that).
#   Live: https://cultural-scout.pages.dev/discover-geology.html
set -e
cd "$(dirname "$0")"
python3 build_geology.py
cp mockup_lookfeel_certified_human.html site/mockup_lookfeel_certified_human.html
echo "▸ Deploying mockup to Cloudflare Pages…"
wrangler pages deploy site --project-name cultural-scout --branch main --commit-dirty=true
echo "✓ Live: https://cultural-scout.pages.dev/discover-geology.html"

#!/usr/bin/env bash
# Publish the Cultural Scout site to Cloudflare Pages — SAME URL every time.
# Monthly flow: after a new run is tagged, just run this (or say "update the live site").
#   1. rebuilds corpus.json + site/index.html from every tagged run
#   2. deploys site/ to the cultural-scout Pages project
# One-time prerequisite: `wrangler login` (browser click), done once.
set -e
cd "$(dirname "$0")"

echo "▸ Rebuilding corpus + site…"
python3 build_corpus.py

echo "▸ Deploying to Cloudflare Pages…"
# --branch main pins this to PRODUCTION. Wrangler always prints a hashed
# per-deployment URL (e.g. 942dded0.cultural-scout.pages.dev) — that's just a
# permanent snapshot of this one deploy. The team URL never changes.
wrangler pages deploy site --project-name cultural-scout --branch main --commit-dirty=true

echo "✓ Live. Share this one: https://cultural-scout.pages.dev  (ignore the hashed URL above — it's a per-deploy snapshot)"

#!/usr/bin/env python3
"""Layer 1: Harvest. Pulls 8-15 recent items per source via Anthropic web_search,
scoped per source. Outputs signals.json. No tagging, no classification, no opinion."""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml
from anthropic import Anthropic

MODEL = "claude-opus-4-7"
SCRIPT_DIR = Path(__file__).resolve().parent
SOURCES_PATH = SCRIPT_DIR / "sources.yaml"
DEFAULT_OUTPUT = SCRIPT_DIR / "signals.json"


def load_config():
    with open(SOURCES_PATH) as f:
        return yaml.safe_load(f)


def domain_of(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc.lower()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def harvest_source(client: Anthropic, source: dict, date_range_days: int,
                   items_min: int, items_max: int) -> tuple[list[dict], object]:
    name = source["name"]
    category = source["category"]
    note = source.get("note", "")
    base_url = source["base_url"]
    recent_url = source.get("recent_url", base_url)
    domain = domain_of(base_url)

    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=date_range_days)

    prompt = f"""You are harvesting recent editorial content from a single curated cultural source.

SOURCE
  Name: {name}
  Category: {category}
  Editorial note: {note}
  Recent-content URL: {recent_url}
  Domain (web_search is restricted to this): {domain}

TASK
  Find {items_min}-{items_max} recent items published on this source on or after {cutoff.isoformat()}. Today is {today.isoformat()}.
  Use the web_search tool. You may make 1-4 search calls if needed (e.g. searching different time slices, different sections, or different content types).
  Prefer items that are profiles, criticism, essays, interviews, or features. Avoid pure announcements, listicles, sponsored posts, and product roundups, UNLESS the source is fundamentally a product-roundup publication (e.g. The Strategist, Thingtesting), in which case those ARE the editorial product.

QUALITY BAR FOR SUMMARIES
  Summaries must be specific and grounded. Bad: "An article about contemporary art." Good: "A profile of a Brooklyn-based ceramicist who makes funeral urns shaped like household objects."
  If the search snippet doesn't give you enough to write a specific summary, drop the item rather than write a generic one.

OUTPUT
  After your searches, your FINAL message must be ONLY a JSON object — no prose, no markdown fences, nothing else. Schema:

  {{
    "items": [
      {{
        "title": "actual article title",
        "url": "actual article URL (not the homepage)",
        "date": "YYYY-MM-DD if known, else YYYY-MM, else best estimate with note",
        "summary": "1-3 sentences, specific and grounded"
      }}
    ],
    "notes": "optional: any caveats about this harvest (e.g. 'site appears to surface evergreen content on homepage', 'only found 4 items meeting recency bar')"
  }}

RULES
  - Do not invent items. If you cannot find {items_min} items meeting the recency bar, return however many you found and note it.
  - URLs must be the actual article URLs.
  - Be honest about dates. If the publication date is not visible, give your best estimate and flag it in the date field (e.g. "2026-03 (estimated, no visible pub date)").
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5,
            "allowed_domains": [domain],
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    final_text = "\n".join(text_blocks).strip()
    final_text = re.sub(r"^```(?:json)?\s*", "", final_text)
    final_text = re.sub(r"\s*```$", "", final_text)

    try:
        data = json.loads(final_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", final_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError as e:
                print(f"    [WARN] could not parse JSON: {e}", file=sys.stderr)
                print(f"    raw: {final_text[:400]}", file=sys.stderr)
                return [], response.usage
        else:
            print(f"    [WARN] no JSON in output. raw: {final_text[:400]}", file=sys.stderr)
            return [], response.usage

    items = data.get("items", []) or []
    notes = data.get("notes")
    if notes:
        print(f"    note: {notes}")
    return items, response.usage


def make_id(source_name: str, date_str: str, counter: int) -> str:
    src_slug = slugify(source_name)[:32]
    date_clean = re.sub(r"[^0-9]", "_", date_str)[:10] or "undated"
    return f"{src_slug}_{date_clean}_{counter:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", nargs="+",
                    help="Run only the named sources (exact match against sources[].name).")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--include-uncertain", action="store_true",
                    help="Include sources with recent_url_uncertain: true (default: include).")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(2)

    config = load_config()
    h = config.get("harvest", {})
    date_range_days = h.get("date_range_days", 90)
    items_min = h.get("items_per_source_min", 8)
    items_max = h.get("items_per_source_max", 15)

    fetchable = [s for s in config["sources"] if s.get("fetchable", True)]

    if args.subset:
        wanted = set(args.subset)
        sources = [s for s in fetchable if s["name"] in wanted]
        missing = wanted - {s["name"] for s in sources}
        if missing:
            print(f"[WARN] Subset names not found in sources.yaml: {sorted(missing)}",
                  file=sys.stderr)
    else:
        sources = fetchable

    if not sources:
        print("No sources to harvest.", file=sys.stderr)
        sys.exit(1)

    skipped_unfetchable = [s["name"] for s in config["sources"]
                           if not s.get("fetchable", True)]
    if skipped_unfetchable and not args.subset:
        print(f"Skipped (fetchable: false): {skipped_unfetchable}")

    client = Anthropic()
    all_signals: list[dict] = []
    seen_urls: set[str] = set()
    per_source_counts: dict[str, int] = {}
    usage_in = 0
    usage_out = 0

    print(f"\nHarvesting {len(sources)} source(s) via {MODEL}")
    print(f"Recency cutoff: last {date_range_days} days. Target: {items_min}-{items_max} per source.\n")

    for src in sources:
        name = src["name"]
        flag = " [recent_url_uncertain]" if src.get("recent_url_uncertain") else ""
        print(f"  • {name}{flag}")
        try:
            items, usage = harvest_source(client, src, date_range_days, items_min, items_max)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            per_source_counts[name] = 0
            continue

        usage_in += getattr(usage, "input_tokens", 0)
        usage_out += getattr(usage, "output_tokens", 0)

        kept = 0
        for i, item in enumerate(items, 1):
            url = (item.get("url") or "").strip()
            if not url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            sid = make_id(name, item.get("date", ""), i)
            all_signals.append({
                "id": sid,
                "source": name,
                "title": (item.get("title") or "").strip(),
                "url": url,
                "date": (item.get("date") or "").strip(),
                "summary": (item.get("summary") or "").strip(),
            })
            kept += 1
        per_source_counts[name] = kept
        print(f"    → {kept} items")

    output = {
        "harvest_date": datetime.now(timezone.utc).date().isoformat(),
        "model": MODEL,
        "date_range_days": date_range_days,
        "sources_harvested": [s["name"] for s in sources],
        "per_source_counts": per_source_counts,
        "signals": all_signals,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(all_signals)} signals across {len(sources)} sources → {args.output}")
    print(f"Tokens: {usage_in:,} input, {usage_out:,} output")
    low = [n for n, c in per_source_counts.items() if c < items_min]
    if low:
        print(f"Below target ({items_min}): {low}")


if __name__ == "__main__":
    main()

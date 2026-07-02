"""
sheets.py — turns a scrape-output JSON into numbered contact sheets.

Two steps, both driven by `run.py sheets`:

  1. DOWNLOAD: pull each extracted image URL into a local temp cache
     (image_scraper/.cache/). Max ~2MB per image; anything that fails to
     download or isn't a real image is skipped silently (logged at debug
     level). A manifest.json in the cache maps each cached file back to
     its image URL, article URL, source, alt text, and caption.

  2. COMPOSITE: lay the cached images out on PNG grids of 12 thumbnails
     (3 across x 4 down, each cell ~400px wide, aspect ratio preserved),
     with a bold index number stamped on every cell. Sheets land in
     image_scraper/sheets/ alongside a sidecar JSON per sheet that maps
     each index number to the image's full metadata. The sidecar is how
     the AI's visual readings get traced back to their sources.

COPYRIGHT (hard rule, from CLAUDE.md): everything this module writes is a
TEMPORARY ANALYSIS ARTIFACT. The cache and the sheets must never be
committed to git, never copied into site/, and never shipped in any
deliverable. `run.py clean` deletes them. Published semiotic codes
reference imagery ONLY as live hotlinks to the publishers' own servers.
"""

import hashlib
import io
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont

from extractor import BROWSER_HEADERS

log = logging.getLogger("image_scraper")

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

MAX_IMAGE_BYTES = 2 * 1024 * 1024   # ~2MB cap per downloaded image
DOWNLOAD_TIMEOUT = 20               # seconds per image

SHEET_COLS = 3                      # thumbnails across
SHEET_ROWS = 4                      # thumbnails down  (3 x 4 = 12 per sheet)
CELL_WIDTH = 400                    # each cell is ~400px wide
CELL_HEIGHT = 400                   # ...and up to 400px tall (aspect preserved)
CELL_PADDING = 10                   # breathing room inside each cell
SHEET_BG = (24, 24, 26)             # near-black background; photos read best on it
INDEX_BG = (255, 200, 40)           # amber tag behind the index number
INDEX_FG = (10, 10, 10)             # near-black number on the amber tag

# File extensions we trust for the cache filename; anything else gets .img
KNOWN_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}


# ---------------------------------------------------------------------------
# Step 1 — download images into the temp cache
# ---------------------------------------------------------------------------

def _cache_filename(image_url):
    """A short, stable, filesystem-safe name for a cached image: the first 16
    hex characters of the URL's SHA-1 hash plus the original extension."""
    stem = hashlib.sha1(image_url.encode("utf-8")).hexdigest()[:16]
    ext = Path(urlparse(image_url).path).suffix.lower()
    if ext not in KNOWN_EXTS:
        ext = ".img"
    return stem + ext


def _download_one(image_url, dest_path, rate_limiter):
    """Fetch one image, streaming, aborting past the ~2MB cap. Returns True
    on success. Any failure is silent (debug-logged) per the design brief —
    a broken image link should never slow the run down."""
    try:
        rate_limiter.wait(image_url)
        with httpx.stream("GET", image_url, headers=BROWSER_HEADERS,
                          timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as resp:
            if resp.status_code != 200:
                log.debug("    image HTTP %s: %s", resp.status_code, image_url[:120])
                return False
            declared = resp.headers.get("content-length")
            if declared and int(declared) > MAX_IMAGE_BYTES:
                log.debug("    image over 2MB (declared): %s", image_url[:120])
                return False
            buf = io.BytesIO()
            for chunk in resp.iter_bytes():
                buf.write(chunk)
                if buf.tell() > MAX_IMAGE_BYTES:
                    log.debug("    image over 2MB (streamed): %s", image_url[:120])
                    return False
            data = buf.getvalue()

        # Make sure what we downloaded actually opens as an image — some
        # sites answer image URLs with HTML error pages.
        Image.open(io.BytesIO(data)).verify()

        dest_path.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001 — skip failures silently
        log.debug("    image download failed (%s): %s", exc, image_url[:120])
        return False


def download_images(scrape_output, cache_dir, rate_limiter):
    """Walk every article in a scrape-output dict and download its images
    into cache_dir. Writes/extends cache_dir/manifest.json.

    The manifest preserves ARTICLE ORDER (Python dicts keep insertion
    order), so the contact sheets later read in the same order the
    articles were scraped. Returns the manifest dict.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "manifest.json"

    # Extend an existing manifest so a second scrape round adds to the pool.
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception:  # noqa: BLE001 — a corrupt manifest just starts fresh
            log.warning("  cache manifest was unreadable — starting a fresh one")

    downloaded = skipped = 0
    for article in scrape_output.get("articles", []):
        for img in article.get("images", []):
            fname = _cache_filename(img["url"])
            if fname in manifest and (cache_dir / fname).exists():
                continue  # already cached in an earlier round
            if _download_one(img["url"], cache_dir / fname, rate_limiter):
                manifest[fname] = {
                    "image_url": img["url"],
                    "article_url": article["url"],
                    "source": article.get("site", ""),
                    "need": article.get("need", ""),
                    "title": article.get("title", ""),
                    "alt": img.get("alt", ""),
                    "caption": img.get("caption", ""),
                    "context": img.get("context", ""),
                }
                downloaded += 1
            else:
                skipped += 1

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    log.info("Image cache: %d downloaded, %d skipped (failures are normal — "
             "broken links, oversized files, hostile hosts)", downloaded, skipped)
    return manifest


# ---------------------------------------------------------------------------
# Step 2 — composite the cache into numbered contact sheets
# ---------------------------------------------------------------------------

def _load_bold_font(size=42):
    """Find a bold font for the index numbers. Tries the fonts that ship
    with macOS and most Linux boxes; falls back to Pillow's built-in."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",                      # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",        # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",     # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def _paste_cell(sheet, draw, image_path, index_number, col, row, font):
    """Place one thumbnail into its grid cell, centered, aspect preserved,
    and stamp the bold index number in the top-left corner of the cell."""
    x0 = col * CELL_WIDTH
    y0 = row * CELL_HEIGHT

    try:
        with Image.open(image_path) as im:
            im = im.convert("RGB")
            im.thumbnail((CELL_WIDTH - 2 * CELL_PADDING,
                          CELL_HEIGHT - 2 * CELL_PADDING))
            # Center the thumbnail inside its cell.
            px = x0 + (CELL_WIDTH - im.width) // 2
            py = y0 + (CELL_HEIGHT - im.height) // 2
            sheet.paste(im, (px, py))
    except Exception as exc:  # noqa: BLE001
        # Unreadable file: leave the cell dark but still number it, so the
        # sidecar's numbering never drifts out of sync with the grid.
        log.debug("    could not render %s: %s", image_path, exc)

    # The amber index tag — the AI cites images by this number.
    label = str(index_number)
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 10
    draw.rectangle([x0 + 6, y0 + 6, x0 + 6 + tw + 2 * pad, y0 + 6 + th + 2 * pad],
                   fill=INDEX_BG)
    draw.text((x0 + 6 + pad - bbox[0], y0 + 6 + pad - bbox[1]), label,
              fill=INDEX_FG, font=font)


def build_contact_sheets(manifest, cache_dir, sheets_dir, run_label="run"):
    """Composite every cached image into numbered contact sheets.

    Numbering is GLOBAL and continuous across sheets (sheet 1 holds images
    1-12, sheet 2 holds 13-24, ...) so 'image 17' is unambiguous no matter
    which sheet it sits on. Each sheet gets a sidecar JSON mapping its
    numbers to full metadata. Returns the list of sheet paths written.
    """
    cache_dir, sheets_dir = Path(cache_dir), Path(sheets_dir)
    sheets_dir.mkdir(parents=True, exist_ok=True)
    font = _load_bold_font()

    # Manifest order = article order = the order the AI should read in.
    entries = [(fname, meta) for fname, meta in manifest.items()
               if (cache_dir / fname).exists()]
    if not entries:
        log.warning("No cached images to composite — did the download step run?")
        return []

    per_sheet = SHEET_COLS * SHEET_ROWS
    written = []

    for sheet_num, start in enumerate(range(0, len(entries), per_sheet), start=1):
        batch = entries[start:start + per_sheet]
        sheet = Image.new("RGB", (SHEET_COLS * CELL_WIDTH, SHEET_ROWS * CELL_HEIGHT),
                          SHEET_BG)
        draw = ImageDraw.Draw(sheet)
        sidecar = {}

        for slot, (fname, meta) in enumerate(batch):
            global_index = start + slot + 1          # 1-based, global
            col, row = slot % SHEET_COLS, slot // SHEET_COLS
            _paste_cell(sheet, draw, cache_dir / fname, global_index, col, row, font)
            sidecar[str(global_index)] = meta        # full metadata per number

        base = f"sheet_{run_label}_{sheet_num:03d}"
        png_path = sheets_dir / f"{base}.png"
        sheet.save(png_path, "PNG")
        (sheets_dir / f"{base}.json").write_text(
            json.dumps(sidecar, indent=2, ensure_ascii=False))
        written.append(png_path)
        log.info("  wrote %s (images %d-%d) + sidecar", png_path.name,
                 start + 1, start + len(batch))

    return written

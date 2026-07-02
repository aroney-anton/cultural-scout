"""
extractor.py — the heart of the image scraper.

Given ONE article URL, this module fetches the page and pulls out everything
the semiotic-coding step downstream needs:

  * article metadata  — title, author, date, tags (via trafilatura)
  * article text      — the first ~1500 characters of readable body text
  * every meaningful image — its URL (highest-resolution version available),
    alt text, caption, and a short "context" snippet (the paragraph of text
    that immediately precedes the image in the article)

It knows two ways to fetch a page:

  1. STATIC fetch (httpx) — fast, polite, works for most editorial sites.
     Retries up to 3 times with a growing pause between attempts.
  2. PLAYWRIGHT fallback (a real headless Chromium browser) — used
     automatically ONLY when the static fetch comes back with no readable
     article text or no images, which usually means the site builds its
     pages with JavaScript. If Playwright isn't installed, we just log
     that and move on.

HARD RULES (from the project owner, see CLAUDE.md "SEMIOTIC CODES"):
  * We never try to defeat paywalls, login walls, or bot challenges.
    If a page looks walled off, we record fetch_method="failed" and move on.
  * We respect a per-domain rate limit (default: one request every 2 seconds
    per domain) so we are a polite visitor, never a hammering bot.
"""

import logging
import re
import time
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

log = logging.getLogger("image_scraper")

# ---------------------------------------------------------------------------
# Settings — tweak here if a value ever needs changing.
# ---------------------------------------------------------------------------

# Headers that make our requests look like a normal desktop browser.
# Many editorial sites serve stripped-down or blocked pages to obvious bots.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

FETCH_TIMEOUT_SECONDS = 25       # give slow magazine sites a fair chance
STATIC_RETRIES = 3               # attempts for the static (httpx) fetch
RETRY_BACKOFF_SECONDS = 2        # 2s, then 4s, then 6s between attempts

TEXT_EXCERPT_CHARS = 1500        # how much article text we keep per article
CONTEXT_SNIPPET_CHARS = 200      # how much preceding-paragraph text per image
MIN_IMAGE_DIMENSION = 200        # images declaring width/height below this are junk

# If the static fetch produced less readable text than this, we assume the
# page is JavaScript-rendered and try the Playwright fallback.
MIN_TEXT_FOR_STATIC_SUCCESS = 200

# --- Junk-image filters -----------------------------------------------------
# Substrings that mark an image URL as furniture (logos, icons, tracking
# pixels, avatars) rather than editorial imagery. Checked case-insensitively.
JUNK_URL_HINTS = [
    "logo", "icon", "favicon", "sprite", "avatar", "gravatar",
    "tracking", "pixel", "spacer", "blank.", "placeholder",
    "1x1", "badge", "button", "/ads/", "/ad/", "advert",
    "emoji", "loading.gif", "spinner",
]

# Domains that only ever serve ads or analytics beacons, never editorial images.
AD_DOMAINS = [
    "doubleclick.net", "googlesyndication.com", "google-analytics.com",
    "googletagmanager.com", "facebook.com", "facebook.net",
    "amazon-adsystem.com", "scorecardresearch.com", "quantserve.com",
    "adnxs.com", "criteo.com", "outbrain.com", "taboola.com",
    "chartbeat.com", "parsely.com", "bat.bing.com",
]

# Phrases that reliably signal a paywall or login wall. Only checked when the
# page yielded very little article text (so a review that merely *mentions*
# subscriptions is not misread as walled).
PAYWALL_HINTS = [
    "subscribe to continue", "subscribe to read", "subscription required",
    "sign in to continue", "log in to continue", "create a free account",
    "already a subscriber", "this article is for subscribers",
    "become a member to read", "unlock this article", "meter has expired",
    "enable javascript and cookies to continue",  # common bot-challenge text
    "verify you are human", "checking your browser",
]

# CSS class-name fragments that usually mark a caption element sitting next
# to an image (used when there is no proper <figcaption>).
CAPTION_CLASS_RE = re.compile(
    r"caption|credit|cutline|wp-caption-text|image-desc", re.I
)


# ---------------------------------------------------------------------------
# Per-domain rate limiter — one polite knock every N seconds per site.
# ---------------------------------------------------------------------------

class RateLimiter:
    """Remembers when we last talked to each domain and sleeps if we are
    coming back too soon. Shared by the article fetcher AND the image
    downloader so the whole tool stays polite."""

    def __init__(self, seconds_between=2.0):
        self.seconds_between = seconds_between
        self._last_hit = {}  # domain -> unix time of our last request

    def wait(self, url):
        domain = urlparse(url).netloc.lower()
        last = self._last_hit.get(domain)
        if last is not None:
            elapsed = time.time() - last
            if elapsed < self.seconds_between:
                time.sleep(self.seconds_between - elapsed)
        self._last_hit[domain] = time.time()


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_static(url, rate_limiter, timeout=FETCH_TIMEOUT_SECONDS):
    """Fetch a page with httpx, retrying up to STATIC_RETRIES times.

    Returns the HTML text, or None if every attempt failed.
    403/404/401/402 responses are NOT retried — they mean 'go away' or
    'not here', and retrying would just be rude.
    """
    for attempt in range(1, STATIC_RETRIES + 1):
        rate_limiter.wait(url)
        try:
            resp = httpx.get(
                url,
                headers=BROWSER_HEADERS,
                timeout=timeout,
                follow_redirects=True,
            )
            if resp.status_code in (401, 402, 403, 404, 410, 451):
                log.warning("  %s returned HTTP %s — not retrying", url, resp.status_code)
                return None
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"server error {resp.status_code}", request=resp.request, response=resp
                )
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype and "xml" not in ctype:
                log.warning("  %s is not an HTML page (%s) — skipping", url, ctype)
                return None
            return resp.text
        except Exception as exc:  # noqa: BLE001 — one bad article never kills a run
            log.warning("  static fetch attempt %d/%d failed for %s: %s",
                        attempt, STATIC_RETRIES, url, exc)
            if attempt < STATIC_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    return None


def fetch_playwright(url, rate_limiter, timeout=35):
    """Fetch a page with a real headless Chromium browser (Playwright).

    Used only as a fallback for JavaScript-rendered pages. Scrolls a little
    so lazy-loaded images actually load. Returns HTML, or None on any
    failure (including Playwright simply not being installed).
    """
    try:
        from playwright.sync_api import sync_playwright  # imported lazily on purpose
    except ImportError:
        log.warning("  Playwright is not installed — cannot use the browser "
                    "fallback. Run: pip install playwright && playwright install chromium")
        return None

    rate_limiter.wait(url)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=BROWSER_HEADERS["User-Agent"])
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                # Give scripts a moment, then scroll to wake lazy-loaded images.
                page.wait_for_timeout(2500)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                page.wait_for_timeout(1200)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)
                return page.content()
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("  Playwright fetch failed for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _pick_from_srcset(srcset_value):
    """A srcset attribute lists several sizes of the same image, e.g.
    'photo-400.jpg 400w, photo-1200.jpg 1200w'. We want the sharpest
    (largest) one for the contact sheets. Returns a URL or None."""
    best_url, best_score = None, -1.0
    for candidate in srcset_value.split(","):
        parts = candidate.strip().split()
        if not parts:
            continue
        cand_url = parts[0]
        score = 0.0
        if len(parts) > 1:
            descriptor = parts[1].lower()
            try:
                if descriptor.endswith("w"):
                    score = float(descriptor[:-1])          # width in pixels
                elif descriptor.endswith("x"):
                    score = float(descriptor[:-1]) * 1000   # density; 2x beats 1x
            except ValueError:
                score = 0.0
        if score > best_score:
            best_url, best_score = cand_url, score
    return best_url


def _parse_dimension(value):
    """Turn a width/height attribute like '640', '640px', or '100%' into a
    number of pixels, or None if we can't tell."""
    if not value:
        return None
    value = str(value).strip().lower().replace("px", "")
    if value.endswith("%") or not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _looks_like_junk(img_url, img_tag):
    """Decide whether an image is page furniture rather than editorial
    imagery. Returns a short reason string if junk, or None if it's a keeper."""
    low = img_url.lower()
    path = urlparse(low).path

    # Vector graphics are almost always logos/icons in article pages.
    if path.endswith(".svg"):
        return "svg"

    # Inline data: URIs are placeholders or pixels, never real photography.
    if low.startswith("data:"):
        return "data-uri"

    # Ad / analytics hosts never serve editorial images.
    domain = urlparse(low).netloc
    for ad in AD_DOMAINS:
        if domain.endswith(ad):
            return "ad-domain"

    # Filename / path hints: logo, icon, avatar, pixel, sprite ...
    for hint in JUNK_URL_HINTS:
        if hint in low:
            return f"junk-hint:{hint}"

    # Declared dimensions under ~200px = thumbnails, icons, tracking pixels.
    width = _parse_dimension(img_tag.get("width"))
    height = _parse_dimension(img_tag.get("height"))
    if (width is not None and width < MIN_IMAGE_DIMENSION) or \
       (height is not None and height < MIN_IMAGE_DIMENSION):
        return f"too-small:{width}x{height}"

    return None


def _find_caption(img_tag):
    """Find the human-written caption for an image, trying in order:
      1. a <figcaption> inside the same <figure>
      2. a nearby element whose class name says 'caption'/'credit'
      3. the image's own title attribute
    Returns '' when there is no caption."""
    figure = img_tag.find_parent("figure")
    if figure is not None:
        figcaption = figure.find("figcaption")
        if figcaption is not None:
            return figcaption.get_text(" ", strip=True)

    # Look at the image's siblings (and its parent's siblings) for a
    # caption-classed element — common on WordPress and custom CMSs.
    for anchor in (img_tag, img_tag.parent):
        if anchor is None:
            continue
        sibling = anchor.find_next_sibling()
        hops = 0
        while sibling is not None and hops < 3:
            classes = " ".join(sibling.get("class", [])) if hasattr(sibling, "get") else ""
            if classes and CAPTION_CLASS_RE.search(classes):
                return sibling.get_text(" ", strip=True)
            sibling = sibling.find_next_sibling()
            hops += 1

    return (img_tag.get("title") or "").strip()


def _find_context(img_tag):
    """Grab the nearest paragraph of text BEFORE the image — the sentence the
    writer was in the middle of when they placed this picture. Truncated to
    ~200 characters so the JSON stays light."""
    for p in img_tag.find_all_previous("p"):
        text = p.get_text(" ", strip=True)
        if len(text) > 30:  # skip stubs like bylines and share buttons
            return text[:CONTEXT_SNIPPET_CHARS]
    return ""


def extract_images(html, base_url):
    """Walk the page in document order and return the list of meaningful
    images: [{url, alt, caption, context}, ...]. Junk (logos, pixels, ads,
    tiny images, duplicates) is filtered out; ordering follows the article."""
    soup = BeautifulSoup(html, "html.parser")

    # Drop whole regions that never contain editorial imagery.
    for tag in soup.find_all(["nav", "header", "footer", "aside"]):
        tag.decompose()

    images, seen_urls = [], set()

    for img in soup.find_all("img"):
        # --- gather EVERY URL variant this image is known by -------------
        # The same photo often appears under several URLs (a 400px src, a
        # 1600px srcset candidate, a lazy-load data-src ...). We pick the
        # sharpest one to keep, but remember ALL of them for dedup — so the
        # same photo referenced twice in a page (e.g. once through a
        # <picture> upgrade and once as a plain <img src>) is only kept once.
        variants = []   # every URL this image is reachable under
        raw_url = None  # the best (highest-res) one, what we actually keep

        # A <picture> wrapper may carry higher-res candidates in <source> tags.
        picture = img.find_parent("picture")
        if picture is not None:
            for source in picture.find_all("source"):
                srcset = source.get("srcset") or source.get("data-srcset")
                if srcset:
                    for candidate in srcset.split(","):
                        parts = candidate.strip().split()
                        if parts:
                            variants.append(parts[0])
                    if not raw_url:
                        raw_url = _pick_from_srcset(srcset)

        # The img's own srcset is next best.
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            for candidate in srcset.split(","):
                parts = candidate.strip().split()
                if parts:
                    variants.append(parts[0])
            if not raw_url:
                raw_url = _pick_from_srcset(srcset)

        # Then plain src — including the lazy-load variants many sites use.
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            value = img.get(attr)
            if value:
                variants.append(value)
                if not raw_url:
                    raw_url = value

        if not raw_url:
            continue
        raw_url = raw_url.strip()
        if raw_url.startswith("data:"):
            continue  # inline placeholder, not a real image

        full_url = urljoin(base_url, raw_url)
        variant_urls = {urljoin(base_url, v.strip()) for v in variants
                        if v and not v.strip().startswith("data:")}
        variant_urls.add(full_url)

        # --- filter junk and duplicates ----------------------------------
        reason = _looks_like_junk(full_url, img)
        if reason:
            log.debug("    dropped image (%s): %s", reason, full_url[:120])
            continue
        if variant_urls & seen_urls:
            continue  # any variant of this photo was already kept
        seen_urls.update(variant_urls)

        images.append({
            "url": full_url,
            "alt": (img.get("alt") or "").strip(),
            "caption": _find_caption(img),
            "context": _find_context(img),
        })

    return images


def extract_article_fields(html, url):
    """Use trafilatura to pull clean metadata + body text out of raw HTML.
    Returns (title, date, author, tags, text_excerpt). Fields that can't be
    determined come back empty rather than crashing."""
    title, date, author, tags, text = "", "", "", [], ""

    try:
        meta = trafilatura.extract_metadata(html, default_url=url)
        if meta is not None:
            title = meta.title or ""
            date = meta.date or ""
            author = meta.author or ""
            tags = list(meta.tags) if meta.tags else []
    except Exception as exc:  # noqa: BLE001
        log.debug("    metadata extraction hiccup for %s: %s", url, exc)

    try:
        body = trafilatura.extract(html, url=url, include_comments=False,
                                   include_tables=False)
        if body:
            text = body.strip()[:TEXT_EXCERPT_CHARS]
    except Exception as exc:  # noqa: BLE001
        log.debug("    text extraction hiccup for %s: %s", url, exc)

    return title, date, author, tags, text


def looks_paywalled(html, text):
    """True when the page is clearly a paywall / login wall / bot challenge.
    Only fires when the extracted article text is nearly empty, so an essay
    that merely *mentions* subscribing is never misread as walled."""
    if len(text) >= 400:
        return False
    page_text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()
    return any(hint in page_text for hint in PAYWALL_HINTS)


def needs_playwright(text, images):
    """The decision rule for falling back to the real browser: the static
    fetch is considered a dud when it produced almost no readable text OR
    zero usable images (both are hallmarks of JavaScript-rendered pages)."""
    return len(text) < MIN_TEXT_FOR_STATIC_SUCCESS or len(images) == 0


# ---------------------------------------------------------------------------
# The one public entry point: scrape a single article.
# ---------------------------------------------------------------------------

def scrape_article(url, rate_limiter, signal_meta=None, allow_playwright=True):
    """Fetch one article URL and return the full per-article record used in
    the output JSON. Never raises — a failure comes back as a record with
    fetch_method='failed' so one bad article can't kill the run.

    signal_meta (optional) carries corpus fields for this URL:
      {"signal_id": ..., "source": ..., "need": ..., "date": ...}
    """
    signal_meta = signal_meta or {}
    domain = urlparse(url).netloc.lower().removeprefix("www.")

    record = {
        "site": signal_meta.get("source") or domain,
        "url": url,
        "title": "",
        "date": signal_meta.get("date") or "",
        "author": "",
        "tags": [],
        "text": "",
        "signal_id": signal_meta.get("signal_id"),
        "need": signal_meta.get("need") or "",
        "fetch_method": "failed",
        "images": [],
    }

    # ---- round 1: static fetch ------------------------------------------
    html = fetch_static(url, rate_limiter)
    if html:
        title, date, author, tags, text = extract_article_fields(html, url)
        images = extract_images(html, url)

        if looks_paywalled(html, text):
            log.warning("  PAYWALL/BOT-WALL detected at %s — recording as failed "
                        "(house rule: never attempt to defeat walls)", url)
            return record  # fetch_method stays 'failed'

        if not needs_playwright(text, images):
            record.update(fetch_method="static", title=title or record["title"],
                          author=author, tags=tags, text=text, images=images)
            if date:
                record["date"] = date
            return record

        log.info("  static fetch looked JS-rendered (text=%d chars, images=%d) "
                 "— trying Playwright fallback", len(text), len(images))
    else:
        log.info("  static fetch failed outright — trying Playwright fallback")
        title = date = author = text = ""
        tags, images = [], []

    # ---- round 2: Playwright fallback -------------------------------------
    if allow_playwright:
        pw_html = fetch_playwright(url, rate_limiter)
        if pw_html:
            pw_title, pw_date, pw_author, pw_tags, pw_text = \
                extract_article_fields(pw_html, url)
            pw_images = extract_images(pw_html, url)

            if looks_paywalled(pw_html, pw_text):
                log.warning("  PAYWALL/BOT-WALL detected (browser fetch) at %s "
                            "— recording as failed", url)
                return record

            if pw_text or pw_images:
                record.update(fetch_method="playwright",
                              title=pw_title or title or record["title"],
                              author=pw_author or author,
                              tags=pw_tags or tags,
                              text=pw_text or text,
                              images=pw_images or images)
                if pw_date or date:
                    record["date"] = pw_date or date
                return record

    # ---- both roads failed, but keep whatever crumbs the static pass got --
    if html and (text or images):
        record.update(fetch_method="static", title=title, author=author,
                      tags=tags, text=text, images=images)
        if date:
            record["date"] = date
        return record

    log.warning("  FAILED: %s (no usable content by any method — if this is a "
                "known-hostile source like the-met or pitchfork, cover it "
                "manually with browser screenshots)", url)
    return record

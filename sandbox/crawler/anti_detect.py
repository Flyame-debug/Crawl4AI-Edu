"""Automatic anti-crawl / encryption detection for fetched pages.

Provides ``analyze_anti_crawl(url, html, status_code)`` — inspects HTTP
status and page content for signals that the target site is behind a
WAF, CAPTCHA, or JavaScript challenge.

Usage::

    from crawler.anti_detect import analyze_anti_crawl

    result = analyze_anti_crawl("https://example.com", html, 403)
    if result["has_encryption"]:
        logger.warning("Anti-crawl detected: %s", result["message"])
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — anti-crawl signal patterns
# ---------------------------------------------------------------------------

# HTTP status codes commonly returned by WAF / rate-limit layers.
_ANTI_CRAWL_STATUSES: frozenset[int] = frozenset({403, 429, 503})

# Content fingerprints that suggest a challenge page was served (status 200
# but the actual content is not the expected page).
_CONTENT_SIGNALS: list[tuple[str, str]] = [
    # (pattern, label)
    (r"Just a moment\.\.\.", "Cloudflare 'Just a moment' interstitial"),
    (r"Checking your browser", "Cloudflare browser check"),
    (r"Access\s*Denied", "Access Denied message"),
    (r"access\s*denied", "Access Denied message (lowercase)"),
    (r"<title>\s*Attention Required!?\s*</title>", "Cloudflare Attention Required"),
    (r"cf-challenge-run", "Cloudflare challenge script"),
    (r"cf-turnstile", "Cloudflare Turnstile widget"),
    (r"g-recaptcha", "Google reCAPTCHA widget"),
    (r"h-captcha", "hCaptcha widget"),
    (r"captcha", "Generic CAPTCHA reference"),
    (r"验证码", "Chinese CAPTCHA reference"),
    (r"请启用[JJ]ava[Ss]cript", "JavaScript required prompt"),
    (r"Please enable JavaScript", "JavaScript required prompt (English)"),
    (r"您的浏览器不支持", "Browser not supported prompt"),
    (r"request has been blocked", "WAF block message"),
    (r"IP.*blocked", "IP block message"),
]

# JavaScript patterns that suggest heavy obfuscation (anti-bot measures).
_OBFUSCATION_PATTERNS: list[tuple[str, str]] = [
    (r"\beval\s*\(.*unescape", "eval+unescape obfuscation"),
    (r"_cf_chl", "Cloudflare challenge variable"),
    (r"challenge-platform", "Cloudflare challenge platform"),
    (r"__cf_chl", "Cloudflare challenge cookie (double underscore)"),
    (r"setTimeout\s*\(\s*function\s*\(\s*\)\s*\{[^}]*location\s*=\s*['\"]http",
     "JavaScript redirect via setTimeout"),
    (r'document\.cookie\s*=\s*"[^"]*=[^"]*;\s*path=/[^"]*;\s*window\.location',
     "Cookie-set + redirect pattern"),
    (r"window\.location\s*=\s*document\.location", "Location reassignment"),
    (r"fromCharCode|String\.fromCharCode", "String.fromCharCode obfuscation"),
    (r"\\x[0-9a-fA-F]{2,}", "Hex-encoded strings in JS"),
    (r"atob\s*\(.*\)", "Base64 decode in JS (atob)"),
    (r"fingerprint", "Browser fingerprinting reference"),
    (r"navigator\.(webdriver|plugins|hardwareConcurrency)", "Bot detection via navigator"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_anti_crawl(
    url: str,
    html: str | None,
    status_code: int,
) -> dict[str, Any]:
    """Detect anti-crawl measures from HTTP status and HTML content.

    Args:
        url: The page URL being analyzed.
        html: Raw HTML content of the page (may be ``None`` when the
            fetch failed and no body was captured).
        status_code: The HTTP status code returned by the server (use
            0 for connection-level failures).

    Returns:
        A dict with keys:
        - ``has_encryption`` (*bool*): ``True`` when anti-crawl signals
          are detected.
        - ``suggest_render`` (*bool*): ``True`` when a JavaScript
          challenge or obfuscation suggests rendering may bypass it.
        - ``message`` (*str*): Human-readable summary of what was found,
          or ``"No anti-crawl signals detected."`` when clean.
    """
    reasons: list[str] = []
    suggest_render: bool = False

    # 1. Status-code check -------------------------------------------------
    if status_code in _ANTI_CRAWL_STATUSES:
        labels: dict[int, str] = {
            (403,): "HTTP 403 Forbidden — access blocked by server or WAF",
            (429,): "HTTP 429 Too Many Requests — rate-limited by server",
            (503,): "HTTP 503 Service Unavailable — possibly blocked temporarily",
        }
        for codes, label in labels.items():
            if status_code in codes:
                reasons.append(label)
                suggest_render = True
                break

    # 2. Content signal check (only when we have HTML) --------------------
    if html:
        html_lower: str = html.lower()
        for pattern, label in _CONTENT_SIGNALS:
            if re.search(pattern, html, re.IGNORECASE):
                reasons.append(label)
                suggest_render = True
                # Continue scanning — collect all matching signals.

        # 3. Obfuscation check (script tags only) -------------------------
        _check_js_obfuscation(html, reasons)

    # 4. Build result -----------------------------------------------------
    has_encryption: bool = len(reasons) > 0
    message: str = (
        "; ".join(reasons) if reasons else "No anti-crawl signals detected."
    )

    result: dict[str, Any] = {
        "has_encryption": has_encryption,
        "suggest_render": suggest_render,
        "message": message,
    }

    if has_encryption:
        logger.warning(
            "Anti-crawl signals detected for %s (status=%d): %s",
            url, status_code, message,
        )
    else:
        logger.debug("No anti-crawl signals for %s (status=%d).", url, status_code)

    return result


# ---------------------------------------------------------------------------
# Internal: JavaScript obfuscation scanner
# ---------------------------------------------------------------------------


def _check_js_obfuscation(html: str, reasons: list[str]) -> None:
    """Scan ``<script>`` blocks in *html* for obfuscation patterns and
    append matching labels to *reasons*."""
    # Extract script content blocks.
    script_blocks: list[str] = re.findall(
        r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE,
    )
    if not script_blocks:
        return

    combined_js: str = "\n".join(script_blocks)

    # Count total script length for an aggregate "suspicious volume" check.
    total_js_len: int = len(combined_js)

    for pattern, label in _OBFUSCATION_PATTERNS:
        if re.search(pattern, combined_js, re.IGNORECASE):
            reasons.append(label)
            # Stop early if we already have enough signals.
            if len([r for r in reasons if "Cloudflare" in r or "eval" in r or "obfuscation" in r]) >= 3:
                break

    # Heuristic: >50KB of inline JS is suspicious for a non-SPA.
    if total_js_len > 50_000 and not any("obfuscation" in r for r in reasons):
        reasons.append(
            f"Large inline JS volume ({total_js_len // 1000}KB) — possible challenge or SPA"
        )


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("Test 1: Cloudflare challenge HTML (fake)")
    print("=" * 60)
    cf_html = """
    <html><head><title>Just a moment...</title></head>
    <body>
      <script>var _cf_chl_opt={cType:"managed"};eval(function(p,a,c,k,e,d){})</script>
      <p>Checking your browser before accessing the site.</p>
    </body></html>
    """
    r1 = analyze_anti_crawl("https://blocked.example.com", cf_html, 200)
    print(f"  has_encryption: {r1['has_encryption']}")
    print(f"  suggest_render: {r1['suggest_render']}")
    print(f"  message: {r1['message']}")

    print()
    print("=" * 60)
    print("Test 2: HTTP 403 with no HTML")
    print("=" * 60)
    r2 = analyze_anti_crawl("https://forbidden.example.com", None, 403)
    print(f"  has_encryption: {r2['has_encryption']}")
    print(f"  suggest_render: {r2['suggest_render']}")
    print(f"  message: {r2['message']}")

    print()
    print("=" * 60)
    print("Test 3: Clean page (no signals)")
    print("=" * 60)
    clean_html = """
    <html><head><title>师资队伍</title></head>
    <body><div class="teacher"><span class="name">张三</span></div></body>
    </html>
    """
    r3 = analyze_anti_crawl("https://normal.example.com", clean_html, 200)
    print(f"  has_encryption: {r3['has_encryption']}")
    print(f"  suggest_render: {r3['suggest_render']}")
    print(f"  message: {r3['message']}")

    print()
    print("anti_detect.py — smoke test passed.")

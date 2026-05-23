"""Probe e-commerce platform policy pages.

Methods:
  html_multi — scrape a list of known static HTML policy articles
  rss        — parse Google News RSS for policy news about the platform
  html       — single URL HTML fallback
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import feedparser
from bs4 import BeautifulSoup
from utils import (
    fetch_html,
    load_sources,
    make_record,
    parse_page_title,
    save_outputs,
)

POLICY_KEYWORDS = ["policy", "fee", "category", "jewelry", "jewellery",
                   "compliance", "seller", "announcement", "rule",
                   "guideline", "prohibited", "restrict", "commission"]

MAX_RSS_ENTRIES = 15


def _probe_html_multi(src: dict) -> tuple[list[dict], list[dict]]:
    platform = src["platform"]
    market = src["market"]
    urls = src.get("urls", [])
    raw_all, normalized = [], []

    for url in urls:
        html, err = fetch_html(url)
        if err:
            raw_all.append({"url": url, "html_length": 0})
            normalized.append(make_record("platform_policy", market, platform, url,
                                          status="failed", error=err))
            print(f"    [failed] {url[-50:]} → {err}")
            continue

        soup = BeautifulSoup(html, "lxml")
        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else ""

        # Extract main article body text
        body_el = soup.find("article") or soup.find("main") or soup.find("div", class_=lambda c: c and "content" in c.lower())
        body_text = body_el.get_text(separator=" ", strip=True) if body_el else soup.get_text(separator=" ", strip=True)
        summary = body_text[:400] if body_text else None

        raw_all.append({"url": url, "html_length": len(html), "title": title_text})
        normalized.append(make_record(
            "platform_policy", market, platform, url,
            title=title_text,
            summary=summary,
        ))
        print(f"    [ok] {title_text[:60]}")

    return raw_all, normalized


def _probe_rss(src: dict) -> tuple[list[dict], list[dict]]:
    platform = src["platform"]
    market = src["market"]
    url = src["url"]
    raw_all, normalized = [], []

    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        raw_all.append({"source": src, "entry_count": 0})
        normalized.append(make_record("platform_policy", market, platform, url,
                                      status="failed",
                                      error=f"feedparser bozo: {feed.bozo_exception}"))
        return raw_all, normalized

    entries = feed.entries[:MAX_RSS_ENTRIES]
    raw_entries = []
    for e in entries:
        title = e.get("title", "")
        link = e.get("link", url)
        summary = e.get("summary", "") or ""
        published = e.get("published", "") or ""
        source_name = e.get("source", {}).get("title", platform) if hasattr(e.get("source", {}), "get") else platform

        raw_entries.append({"title": title, "url": link, "published": published})
        normalized.append(make_record(
            "platform_policy", market, platform, link,
            title=title,
            summary=summary[:300] if summary else None,
            published_at=published,
            extra={"media_source": source_name},
        ))
        print(f"    [rss] {title[:65]}")

    raw_all.append({"source": src, "entry_count": len(entries), "entries": raw_entries})
    return raw_all, normalized


def _probe_html_single(src: dict) -> tuple[list[dict], list[dict]]:
    platform = src["platform"]
    market = src["market"]
    url = src["url"]

    html, err = fetch_html(url)
    if err:
        return [{"source": src, "html_length": 0}], [
            make_record("platform_policy", market, platform, url, status="failed", error=err)
        ]

    title = parse_page_title(html)
    raw = [{"source": src, "html_length": len(html), "page_title": title}]
    rec = make_record("platform_policy", market, platform, url, title=title,
                      error="no matching links found" if not title else None)
    return raw, [rec]


def probe_platform_policy() -> list[dict]:
    sources = load_sources().get("platform_policy", [])
    raw_all, normalized = [], []

    for src in sources:
        platform = src["platform"]
        method = src.get("method", "html")
        print(f"  → [{method.upper()}] {platform}")

        if method == "html_multi":
            raws, recs = _probe_html_multi(src)
        elif method == "rss":
            raws, recs = _probe_rss(src)
        else:
            raws, recs = _probe_html_single(src)

        raw_all.extend(raws)
        normalized.extend(recs)

        ok = sum(1 for r in recs if r["status"] == "success")
        print(f"    total={len(recs)} success={ok}")

    save_outputs("platform_policy", raw_all, normalized)
    return normalized


if __name__ == "__main__":
    print("=== probe_platform_policy ===")
    results = probe_platform_policy()
    ok = sum(1 for r in results if r["status"] == "success")
    print(f"Done: {ok}/{len(results)} success")

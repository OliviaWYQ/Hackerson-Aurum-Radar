"""Probe news sources for gold jewellery mentions.

Supports two methods (configured per-source in sources.yaml):
  rss  — parse via feedparser, returns real article titles/links/dates
  html — fallback HTML keyword link extraction
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import feedparser
from utils import (
    extract_links_by_keywords,
    fetch_html,
    load_sources,
    make_record,
    parse_page_title,
    save_outputs,
)

NEWS_KEYWORDS = ["gold", "jewellery", "jewelry", "luxury", "collection",
                 "store", "campaign", "precious", "retail", "diamond"]

MAX_ENTRIES_PER_FEED = 20


def _probe_rss(src: dict) -> tuple[dict, list[dict]]:
    name = src["name"]
    market = src["market"]
    url = src["url"]

    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        raw = {"source": src, "entry_count": 0, "entries": []}
        rec = make_record("news", market, name, url, status="failed",
                          error=f"feedparser bozo: {feed.bozo_exception}")
        return raw, [rec]

    entries = feed.entries[:MAX_ENTRIES_PER_FEED]
    raw_entries = []
    normalized = []

    for e in entries:
        title = e.get("title", "")
        link = e.get("link", url)
        summary = e.get("summary", "") or ""
        published = e.get("published", "") or ""

        src_obj = e.get("source", {})
        source_name = src_obj.get("title", name) if isinstance(src_obj, dict) else name

        raw_entries.append({
            "title": title,
            "url": link,
            "published": published,
            "source": source_name,
        })
        normalized.append(make_record(
            "news", market, name, link,
            title=title,
            summary=summary[:300] if summary else None,
            published_at=published,
            extra={"media_source": source_name},
        ))

    raw = {"source": src, "entry_count": len(entries), "entries": raw_entries}
    return raw, normalized


def _probe_html(src: dict) -> tuple[dict, list[dict]]:
    name = src["name"]
    market = src["market"]
    url = src["url"]

    html, err = fetch_html(url)
    if err:
        raw = {"source": src, "html_length": 0, "links": []}
        return raw, [make_record("news", market, name, url, status="failed", error=err)]

    title = parse_page_title(html)
    links = extract_links_by_keywords(html, url, NEWS_KEYWORDS)
    raw = {"source": src, "html_length": len(html), "page_title": title, "links": links}

    if links:
        recs = [make_record("news", market, name, lnk["url"], title=lnk["text"] or title)
                for lnk in links[:10]]
    else:
        recs = [make_record("news", market, name, url, title=title,
                            error="no matching links found")]
    return raw, recs


def probe_news() -> list[dict]:
    sources = load_sources().get("news", [])
    raw_all, normalized = [], []

    for src in sources:
        name = src["name"]
        method = src.get("method", "html")
        print(f"  → [{method.upper()}] {name}")

        if method == "rss":
            raw, recs = _probe_rss(src)
        else:
            raw, recs = _probe_html(src)

        raw_all.append(raw)
        normalized.extend(recs)

        ok = sum(1 for r in recs if r["status"] == "success")
        print(f"    [{recs[0]['status'] if recs else 'empty'}] records={len(recs)}  success={ok}")
        if recs and recs[0]["status"] == "success":
            print(f"    sample: {recs[0].get('title','')[:70]}")

    save_outputs("news", raw_all, normalized)
    return normalized


if __name__ == "__main__":
    print("=== probe_news ===")
    results = probe_news()
    ok = sum(1 for r in results if r["status"] == "success")
    print(f"Done: {ok}/{len(results)} success")

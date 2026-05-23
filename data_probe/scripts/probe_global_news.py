"""Multi-market Google News RSS probe.

Iterates `markets × keywords` and pulls Google News RSS for each
combination. Uses feedparser (urllib under the hood) which already
works on this machine's LibreSSL + proxy setup.

Driven by:
  config/sources.yaml: global_news section
  config/markets.yaml: hl/gl/ceid per market
  config/keywords.yaml: market_topics + brands
"""
from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))

import feedparser  # noqa: E402
from utils import (  # noqa: E402
    detect_entities,
    load_keywords,
    load_markets,
    load_sources,
    make_intelligence_record,
    primary_language,
    save_jsonl,
    strip_html,
)


def _build_url(template: str, query: str, market_cfg: dict) -> str:
    gn = market_cfg.get("google_news", {})
    return template.format(
        query=urllib.parse.quote_plus(query),
        hl=gn.get("hl", "en-US"),
        gl=gn.get("gl", "US"),
        ceid=gn.get("ceid", "US:en"),
    )


def _select_queries(kw: dict, market_name: str, groups: list[str], cap: int) -> list[str]:
    """Build combined queries: <kw> <market_name>, e.g. 'gold price Japan'."""
    queries: list[str] = []
    for g in groups:
        for term in kw.get(g, []):
            queries.append(f"{term} {market_name}")
            if len(queries) >= cap:
                return queries
    return queries


def probe_global_news() -> list[dict]:
    cfg = load_sources().get("global_news") or {}
    if not cfg.get("enabled", True):
        print("  [skip] global_news disabled in sources.yaml")
        return []

    template = cfg.get("url_template")
    market_codes = cfg.get("markets", [])
    groups = cfg.get("query_keyword_groups", ["market_topics"])
    max_q = int(cfg.get("max_queries_per_market", 5))
    max_entries = int(cfg.get("max_entries_per_feed", 15))

    markets_cfg = load_markets()
    kw = load_keywords()

    raw_records: list[dict] = []
    normalized: list[dict] = []
    fetched_count = failed_count = 0

    for code in market_codes:
        m = markets_cfg.get(code) or {}
        if not m:
            continue
        market_name = m.get("name", code)
        lang = primary_language(code, markets_cfg)
        queries = _select_queries(kw, market_name, groups, max_q)
        print(f"  → [{code}] {market_name}: {len(queries)} query(ies)")

        for q in queries:
            url = _build_url(template, q, m)
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                failed_count += 1
                print(f"    [failed] {q} → {feed.bozo_exception}")
                continue

            entries = feed.entries[:max_entries]
            fetched_count += len(entries)

            for e in entries:
                title = e.get("title", "") or ""
                link = e.get("link", "") or url
                published = e.get("published", "") or ""
                # GN RSS summary field contains HTML (<a>/<font> tags) — strip to plain text
                summary = strip_html((e.get("summary", "") or ""))[:500]

                src_obj = e.get("source", {})
                if isinstance(src_obj, dict):
                    media_source = src_obj.get("title", "")
                    source_domain = urlparse(src_obj.get("href", "")).netloc
                else:
                    media_source = ""
                    source_domain = ""

                ent = detect_entities(title + " " + summary, kw)
                raw_records.append({
                    "market": code,
                    "query": q,
                    "title": title,
                    "url": link,
                    "published": published,
                    "media_source": media_source,
                    "source_domain": source_domain,
                })
                normalized.append(make_intelligence_record(
                    source_id="google_news_rss",
                    source_name="Google News RSS",
                    source_type="news",
                    market=code,
                    language=lang,
                    title=title,
                    url=link,
                    published_at=published,
                    author_or_account=media_source,
                    summary=summary,
                    keywords=[q] + ent["keywords"],
                    brands=ent["brands"],
                    products=ent["products"],
                    locations=[market_name],
                    signal_type="competition" if ent["brands"] else "consumer_behavior",
                    impact_direction="watch",
                    evidence_level="media",
                    confidence=0.5 if ent["brands"] or ent["products"] else 0.3,
                ))

            print(f"    [ok] '{q[:50]}' → {len(entries)} entries")

    info = save_jsonl("google_news_rss", normalized, raw=raw_records)
    print(f"  source_name        : Google News RSS (multi-market)")
    print(f"  fetched_count      : {fetched_count}")
    print(f"  normalized_count   : {len(normalized)}")
    print(f"  saved_path         : {info['normalized_path']}")
    print(f"  failed_count       : {failed_count}")
    return normalized


if __name__ == "__main__":
    print("=== probe_global_news ===")
    results = probe_global_news()
    print(f"Done: {len(results)} records")

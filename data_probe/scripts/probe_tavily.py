"""Tavily Search probe — cross-market intelligence queries.

Ported from agent/sources.py:collect_tavily, with the cache layer ported
into utils.py (no cross-module import). Skips gracefully when:
  - TAVILY_API_KEY is not set
  - tavily-python is not installed
"""
from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (  # noqa: E402
    detect_entities,
    load_keywords,
    load_markets,
    load_sources,
    make_intelligence_record,
    primary_language,
    save_jsonl,
    tavily_cache_get,
    tavily_cache_set,
)


def _build_queries(cfg: dict, markets_cfg: dict, kw: dict) -> list[tuple[str, str]]:
    """Return list of (query_string, market_code)."""
    templates: list[str] = cfg.get("query_templates") or []
    market_codes: list[str] = cfg.get("markets") or list(markets_cfg.keys())
    cap = int(cfg.get("max_queries_per_market", 4))

    out: list[tuple[str, str]] = []
    for code in market_codes:
        m = markets_cfg.get(code) or {}
        if not m:
            continue
        market_name = m.get("name", code)
        bucket: list[str] = []
        seeds = list(itertools.chain(
            (("market_topic", t) for t in kw.get("market_topics", [])),
            (("brand", b) for b in kw.get("brands", [])),
        ))
        for kind, term in seeds:
            for tmpl in templates:
                try:
                    q = tmpl.format(market_topic=term, brand=term, market_name=market_name)
                except KeyError:
                    continue
                if (kind == "brand") != ("{brand}" in tmpl):
                    continue
                bucket.append(q)
                if len(bucket) >= cap:
                    break
            if len(bucket) >= cap:
                break
        out.extend((q, code) for q in bucket[:cap])
    return out


def probe_tavily() -> list[dict]:
    cfg = load_sources().get("tavily") or {}
    if not cfg.get("enabled", True):
        print("  [skip] tavily disabled in sources.yaml")
        return []

    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        print("  [skip] TAVILY_API_KEY not set — install tavily-python and add key to .env to enable")
        return []

    try:
        from tavily import TavilyClient
    except ImportError:
        print("  [skip] tavily-python not installed — run `pip install tavily-python`")
        return []

    client = TavilyClient(api_key=key)
    markets_cfg = load_markets()
    kw = load_keywords()
    queries = _build_queries(cfg, markets_cfg, kw)
    max_results = int(cfg.get("max_results_per_query", 5))
    topic = cfg.get("topic", "news")
    days = int(cfg.get("days", 7))

    raw_records: list[dict] = []
    normalized: list[dict] = []
    fetched = failed = cache_hits = api_calls = 0

    for q, code in queries:
        cached = tavily_cache_get(q)
        if cached is not None:
            cache_hits += 1
            results = cached
        else:
            try:
                res = client.search(query=q, max_results=max_results, topic=topic, days=days)
                results = [
                    {
                        "title": r.get("title", ""),
                        "summary": (r.get("content", "") or "")[:1000],
                        "url": r.get("url", ""),
                        "published_at": r.get("published_date", "") or "",
                    }
                    for r in res.get("results", []) or []
                ]
                tavily_cache_set(q, results)
                api_calls += 1
            except Exception as e:
                failed += 1
                print(f"    [failed] '{q[:50]}' → {e}")
                continue

        fetched += len(results)
        lang = primary_language(code, markets_cfg)
        market_name = (markets_cfg.get(code) or {}).get("name", code)
        for r in results:
            title = r["title"]
            summary = r["summary"]
            ent = detect_entities(title + " " + summary, kw)
            raw_records.append({"market": code, "query": q, **r})
            normalized.append(make_intelligence_record(
                source_id="tavily",
                source_name="Tavily Search",
                source_type="news",
                market=code,
                language=lang,
                title=title,
                url=r["url"],
                published_at=r["published_at"],
                summary=summary,
                keywords=[q] + ent["keywords"],
                brands=ent["brands"],
                products=ent["products"],
                locations=[market_name],
                signal_type="competition" if ent["brands"] else "consumer_behavior",
                impact_direction="watch",
                evidence_level="third_party_report",
                confidence=0.5 if ent["brands"] or ent["products"] else 0.3,
            ))

    info = save_jsonl("tavily", normalized, raw=raw_records)
    print(f"  source_name        : Tavily Search")
    print(f"  fetched_count      : {fetched}")
    print(f"  normalized_count   : {len(normalized)}")
    print(f"  saved_path         : {info['normalized_path']}")
    print(f"  failed_count       : {failed}")
    print(f"  api_calls / cache  : {api_calls} call(s), {cache_hits} cache hit(s)")
    return normalized


if __name__ == "__main__":
    print("=== probe_tavily ===")
    results = probe_tavily()
    print(f"Done: {len(results)} records")

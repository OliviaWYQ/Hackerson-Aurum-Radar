"""GDELT 2.0 DOC API probe — free global news stream.

API:   https://api.gdeltproject.org/api/v2/doc/doc
Mode:  ArtList (article list)
Auth:  none

GDELT public endpoint rate-limits aggressively (HTTP 429) and the local
LibreSSL stack sees occasional handshake EOF; we add a small delay
between queries and rely on fetch_json's built-in retry.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (  # noqa: E402
    detect_entities,
    fetch_json,
    load_keywords,
    load_sources,
    make_intelligence_record,
    primary_language,
    load_markets,
    save_jsonl,
)

GDELT_UA = "Mozilla/5.0 (compatible; AurumRadar/0.1; +https://github.com/leon)"
INTER_QUERY_SLEEP_SEC = 1.2  # avoid GDELT 429


def _query_gdelt(api_url: str, query: str, max_records: int = 50) -> tuple[list[dict], str | None]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "sort": "DateDesc",
    }
    data, err = fetch_json(api_url, params=params, ua=GDELT_UA)
    if err:
        return [], err
    if not isinstance(data, dict):
        return [], f"unexpected_payload:{type(data).__name__}"
    return data.get("articles", []) or [], None


def probe_gdelt() -> list[dict]:
    cfg = load_sources().get("gdelt") or {}
    if not cfg.get("enabled", True):
        print("  [skip] gdelt disabled in sources.yaml")
        return []

    api_url = cfg.get("api_url") or "https://api.gdeltproject.org/api/v2/doc/doc"
    queries_by_market: dict[str, list[str]] = cfg.get("queries") or {}
    markets_cfg = load_markets()
    kw = load_keywords()
    max_records = int(cfg.get("max_records", 50))

    raw_records: list[dict] = []
    normalized: list[dict] = []
    fetched_count = failed_count = 0

    for market_code, queries in queries_by_market.items():
        lang = primary_language(market_code, markets_cfg)
        print(f"  → [{market_code}] {len(queries)} query(ies)")
        for q in queries:
            articles, err = _query_gdelt(api_url, q, max_records=max_records)
            time.sleep(INTER_QUERY_SLEEP_SEC)
            if err:
                failed_count += 1
                print(f"    [failed] '{q}' → {err}")
                normalized.append(make_intelligence_record(
                    source_id="gdelt_doc",
                    source_name="GDELT 2.0 DOC API",
                    source_type="news",
                    market=market_code,
                    language=lang,
                    title=f"[failed query] {q}",
                    summary=err,
                    signal_type="competition",
                    impact_direction="watch",
                    confidence=0.0,
                ))
                continue

            fetched_count += len(articles)
            print(f"    [ok] '{q[:50]}' → {len(articles)} articles")

            for art in articles:
                title = art.get("title", "") or ""
                url = art.get("url", "") or ""
                published = art.get("seendate", "") or ""
                domain = art.get("domain", "") or ""
                ent = detect_entities(title, kw)
                raw_records.append({
                    "market": market_code,
                    "query": q,
                    "title": title,
                    "url": url,
                    "domain": domain,
                    "seendate": published,
                    "language": art.get("language", lang),
                })
                normalized.append(make_intelligence_record(
                    source_id="gdelt_doc",
                    source_name="GDELT 2.0 DOC API",
                    source_type="news",
                    market=market_code,
                    language=art.get("language", lang),
                    title=title,
                    url=url,
                    published_at=published,
                    author_or_account=domain,
                    summary="",
                    keywords=[q] + ent["keywords"],
                    brands=ent["brands"],
                    products=ent["products"],
                    signal_type="competition" if ent["brands"] else "macro",
                    impact_direction="watch",
                    evidence_level="media",
                    confidence=0.4 if ent["brands"] or ent["products"] else 0.2,
                ))

    info = save_jsonl("gdelt_doc", normalized, raw=raw_records)
    print(f"  source_name        : GDELT 2.0 DOC API")
    print(f"  fetched_count      : {fetched_count}")
    print(f"  normalized_count   : {len(normalized)}")
    print(f"  saved_path         : {info['normalized_path']}")
    print(f"  failed_count       : {failed_count}")
    return normalized


if __name__ == "__main__":
    print("=== probe_gdelt ===")
    results = probe_gdelt()
    ok = sum(1 for r in results if not r["title"].startswith("[failed"))
    print(f"Done: {ok}/{len(results)} records")

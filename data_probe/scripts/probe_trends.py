"""Optional Google Trends probe — only runs when pytrends is installed.

pytrends is unofficial and often rate-limited; use for demo-grade signals
only. Skips gracefully when:
  - pytrends is not installed
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (  # noqa: E402
    load_keywords,
    load_markets,
    make_intelligence_record,
    save_jsonl,
)


def probe_trends() -> list[dict]:
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("  [skip] pytrends not installed — run `pip install pytrends`")
        return []

    kw = load_keywords()
    markets = load_markets()

    seed_terms = (kw.get("products", []) or [])[:3] + (kw.get("brands", []) or [])[:2]
    if not seed_terms:
        seed_terms = ["jewelry"]

    pt = TrendReq(hl="en-US", tz=0)

    raw: list[dict] = []
    normalized: list[dict] = []
    failed = 0

    for code, m in markets.items():
        gl = m.get("google_news", {}).get("gl", code)
        try:
            pt.build_payload(seed_terms, timeframe="now 7-d", geo=gl)
            df = pt.interest_over_time()
            if df is None or df.empty:
                continue
            for term in seed_terms:
                if term not in df.columns:
                    continue
                series = df[term].astype(int).tolist()
                avg = sum(series) / max(1, len(series))
                raw.append({"market": code, "geo": gl, "term": term, "series": series, "avg": avg})
                normalized.append(make_intelligence_record(
                    source_id="google_trends",
                    source_name="Google Trends (pytrends)",
                    source_type="trend",
                    market=code,
                    language="en",
                    title=f"Trend: {term} ({code})",
                    summary=f"7-day avg interest = {avg:.1f}/100; series={series}",
                    keywords=[term],
                    products=[term] if term in (kw.get("products", []) or []) else [],
                    brands=[term] if term in (kw.get("brands", []) or []) else [],
                    signal_type="product_trend",
                    impact_direction="watch",
                    evidence_level="third_party_report",
                    confidence=0.3,
                ))
            print(f"  [ok] {code} ({gl}) → {len([t for t in seed_terms if t in df.columns])} term(s)")
        except Exception as e:
            failed += 1
            print(f"  [failed] {code} ({gl}) → {e}")

    info = save_jsonl("google_trends", normalized, raw=raw)
    print(f"  source_name        : Google Trends (pytrends)")
    print(f"  normalized_count   : {len(normalized)}")
    print(f"  saved_path         : {info['normalized_path']}")
    print(f"  failed_count       : {failed}")
    return normalized


if __name__ == "__main__":
    print("=== probe_trends ===")
    results = probe_trends()
    print(f"Done: {len(results)} records")

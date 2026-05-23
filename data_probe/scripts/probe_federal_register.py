"""US Federal Register regulation probe.

Public API:
  https://www.federalregister.gov/api/v1/articles.json

Queries are pulled from keywords.yaml:regulation_terms.
Single-keyword failures yield a `failed` record but never crash.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (  # noqa: E402
    detect_entities,
    fetch_json,
    load_keywords,
    load_sources,
    make_intelligence_record,
    save_jsonl,
)

FR_UA = "Mozilla/5.0 (compatible; AurumRadar/0.1; +mailto:research@aurum)"


def _query_fr(api_url: str, term: str, per_page: int = 20) -> tuple[list[dict], str | None]:
    params = {
        "conditions[term]": term,
        "order": "newest",
        "per_page": str(per_page),
        "fields[]": [
            "title", "abstract", "html_url", "publication_date",
            "type", "agencies", "document_number",
        ],
    }
    data, err = fetch_json(api_url, params=params, ua=FR_UA)
    if err:
        return [], err
    if not isinstance(data, dict):
        return [], f"unexpected_payload:{type(data).__name__}"
    return data.get("results", []) or [], None


def probe_federal_register() -> list[dict]:
    cfg = load_sources().get("federal_register") or {}
    if not cfg.get("enabled", True):
        print("  [skip] federal_register disabled in sources.yaml")
        return []

    api_url = cfg.get("api_url") or "https://www.federalregister.gov/api/v1/articles.json"
    per_page = int(cfg.get("per_page", 20))
    kw = load_keywords()
    terms: list[str] = kw.get("regulation_terms", []) or []

    raw_records: list[dict] = []
    normalized: list[dict] = []
    fetched_count = failed_count = 0

    for term in terms:
        results, err = _query_fr(api_url, term, per_page=per_page)
        if err:
            failed_count += 1
            print(f"  [failed] '{term}' → {err}")
            normalized.append(make_intelligence_record(
                source_id="federal_register",
                source_name="US Federal Register",
                source_type="regulation",
                market="US",
                language="en",
                title=f"[failed query] {term}",
                summary=err,
                signal_type="regulation",
                impact_direction="watch",
                evidence_level="official",
                confidence=0.0,
            ))
            continue

        fetched_count += len(results)
        print(f"  [ok] '{term}' → {len(results)} articles")

        for r in results:
            title = r.get("title", "") or ""
            abstract = (r.get("abstract", "") or "")[:1000]
            url = r.get("html_url", "") or ""
            published = r.get("publication_date", "") or ""
            agencies = r.get("agencies", []) or []
            agency_names = [a.get("name", "") for a in agencies if isinstance(a, dict)]
            ent = detect_entities(title + " " + abstract, kw)

            raw_records.append({
                "term": term,
                "title": title,
                "url": url,
                "publication_date": published,
                "document_number": r.get("document_number", ""),
                "type": r.get("type", ""),
                "agencies": agency_names,
            })
            normalized.append(make_intelligence_record(
                source_id="federal_register",
                source_name="US Federal Register",
                source_type="regulation",
                market="US",
                language="en",
                title=title,
                url=url,
                published_at=published,
                author_or_account=", ".join(agency_names),
                raw_text=abstract,
                summary=abstract[:500],
                keywords=[term] + ent["keywords"],
                brands=ent["brands"],
                products=ent["products"],
                signal_type="regulation",
                impact_direction="watch",
                evidence_level="official",
                confidence=0.7,
            ))

    info = save_jsonl("federal_register", normalized, raw=raw_records)
    print(f"  source_name        : US Federal Register")
    print(f"  fetched_count      : {fetched_count}")
    print(f"  normalized_count   : {len(normalized)}")
    print(f"  saved_path         : {info['normalized_path']}")
    print(f"  failed_count       : {failed_count}")
    return normalized


if __name__ == "__main__":
    print("=== probe_federal_register ===")
    results = probe_federal_register()
    print(f"Done: {len(results)} records")

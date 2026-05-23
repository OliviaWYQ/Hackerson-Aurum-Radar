"""Probe competitor brand websites for product / campaign signals."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    extract_links_by_keywords,
    fetch_html,
    load_sources,
    make_record,
    parse_page_title,
    save_outputs,
)

COMPETITOR_KEYWORDS = ["new", "collection", "store", "campaign", "jewelry",
                       "jewellery", "press", "news", "launch", "event"]


def probe_competitors() -> list[dict]:
    sources = load_sources().get("competitors", [])
    raw_all, normalized = [], []

    for src in sources:
        brand = src["brand"]
        market = src["market"]
        url = src["url"]
        print(f"  → {brand} ({market}) {url}")

        html, err = fetch_html(url)
        if err:
            rec = make_record("competitor", market, brand, url, status="failed", error=err)
            raw_all.append({"source": src, "html_length": 0, "links": []})
            normalized.append(rec)
            print(f"    [failed] {err}")
            continue

        title = parse_page_title(html)
        links = extract_links_by_keywords(html, url, COMPETITOR_KEYWORDS)

        raw_all.append({"source": src, "html_length": len(html), "page_title": title, "links": links})

        if links:
            for link in links[:10]:
                rec = make_record(
                    "competitor", market, brand, link["url"],
                    title=link["text"] or title,
                )
                normalized.append(rec)
        else:
            rec = make_record("competitor", market, brand, url, title=title)
            normalized.append(rec)

        print(f"    [ok] page_title='{title}' links_found={len(links)}")

    save_outputs("competitor", raw_all, normalized)
    return normalized


if __name__ == "__main__":
    print("=== probe_competitors ===")
    results = probe_competitors()
    ok = sum(1 for r in results if r["status"] == "success")
    print(f"Done: {ok}/{len(results)} success")

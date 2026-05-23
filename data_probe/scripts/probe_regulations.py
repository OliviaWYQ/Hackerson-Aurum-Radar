"""Probe government/regulatory websites for jewellery-related rules."""
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

REGULATION_KEYWORDS = ["gold", "jewellery", "jewelry", "precious metal",
                       "import", "customs", "consumer", "advertising",
                       "licence", "license", "regulation", "act"]


def probe_regulations() -> list[dict]:
    sources = load_sources().get("regulations", [])
    raw_all, normalized = [], []

    for src in sources:
        name = src["name"]
        market = src["market"]
        url = src["url"]
        print(f"  → {name} ({market}) {url}")

        html, err = fetch_html(url)
        if err:
            rec = make_record("regulation", market, name, url, status="failed", error=err)
            raw_all.append({"source": src, "html_length": 0, "links": []})
            normalized.append(rec)
            print(f"    [failed] {err}")
            continue

        title = parse_page_title(html)
        links = extract_links_by_keywords(html, url, REGULATION_KEYWORDS)

        raw_all.append({"source": src, "html_length": len(html), "page_title": title, "links": links})

        if links:
            for link in links[:10]:
                rec = make_record(
                    "regulation", market, name, link["url"],
                    title=link["text"] or title,
                )
                normalized.append(rec)
        else:
            rec = make_record("regulation", market, name, url, title=title)
            normalized.append(rec)

        print(f"    [ok] page_title='{title}' links_found={len(links)}")

    save_outputs("regulation", raw_all, normalized)
    return normalized


if __name__ == "__main__":
    print("=== probe_regulations ===")
    results = probe_regulations()
    ok = sum(1 for r in results if r["status"] == "success")
    print(f"Done: {ok}/{len(results)} success")

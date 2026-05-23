"""Generate a human-readable crawl snapshot from all JSONL files in output/normalized/.

Writes:
  output/CRAWL_SNAPSHOT_{YYYYMMDD}.md  — counts + samples per source_id × market
  output/CRAWL_SNAPSHOT_{YYYYMMDD}/   — all jsonl copied + raw HTML snapshots

Run: python scripts/snapshot_crawl.py
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import OUTPUT_NORMALIZED, OUTPUT_RAW, ROOT  # noqa: E402

MAX_SAMPLES_PER_BUCKET = 3
SUMMARY_FIELDS = ["source_id", "source_name", "source_type", "market", "language",
                  "title", "url", "published_at", "signal_type", "evidence_level",
                  "confidence", "entities", "keywords"]


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def fmt_field(v) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if v is None:
        return ""
    s = str(v)
    return s[:200] + ("..." if len(s) > 200 else "")


def render_sample(rec: dict) -> str:
    lines = []
    for k in SUMMARY_FIELDS:
        if k in rec:
            lines.append(f"    - **{k}**: {fmt_field(rec[k])}")
    return "\n".join(lines)


def main() -> None:
    date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
    snap_dir = ROOT / "output" / f"CRAWL_SNAPSHOT_{date_slug}"
    snap_dir.mkdir(parents=True, exist_ok=True)
    md_path = ROOT / "output" / f"CRAWL_SNAPSHOT_{date_slug}.md"

    jsonl_files = sorted(OUTPUT_NORMALIZED.glob("*.jsonl"))
    json_files = sorted(OUTPUT_NORMALIZED.glob("*.json"))
    html_snaps = sorted(OUTPUT_RAW.glob("*.html"))

    md = []
    md.append(f"# Aurum Radar — Crawl Snapshot {date_slug}")
    md.append("")
    md.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    md.append("")
    md.append(f"- JSONL files: **{len(jsonl_files)}**")
    md.append(f"- Legacy JSON files (SG MVP probes): **{len(json_files)}**")
    md.append(f"- Raw HTML snapshots (parse_failed): **{len(html_snaps)}**")
    md.append("")
    md.append("---")
    md.append("")

    grand_total = 0
    grand_failed = 0
    md.append("## Per-source overview")
    md.append("")
    md.append("| source_id | type | total | success | failed | markets |")
    md.append("|---|---|---|---|---|---|")

    per_source: list[tuple[str, list[dict]]] = []
    for jf in jsonl_files:
        recs = load_jsonl(jf)
        source_id = jf.stem.rsplit("_", 1)[0]
        per_source.append((source_id, recs))

        failed = sum(1 for r in recs if (r.get("title") or "").startswith("[failed"))
        success = len(recs) - failed
        markets = sorted(set(r.get("market", "") for r in recs))
        md.append(f"| `{source_id}` | {recs[0].get('source_type','?') if recs else '?'} | {len(recs)} | {success} | {failed} | {', '.join(markets) or '-'} |")
        grand_total += len(recs)
        grand_failed += failed

    md.append("")
    md.append(f"**Grand total**: {grand_total} records, {grand_failed} failed placeholders.")
    md.append("")

    # ----- per-source detail sections -----
    for source_id, recs in per_source:
        md.append("---")
        md.append("")
        md.append(f"## {source_id}  ({len(recs)} records)")
        md.append("")

        # Breakdown by market
        by_market: Counter = Counter(r.get("market", "") for r in recs)
        md.append("**By market**: " + ", ".join(f"{m}={c}" for m, c in by_market.most_common()))
        md.append("")

        # Breakdown by signal_type
        by_sig: Counter = Counter(r.get("signal_type") or "(none)" for r in recs)
        md.append("**By signal_type**: " + ", ".join(f"{s}={c}" for s, c in by_sig.most_common()))
        md.append("")

        # Entity hits
        brand_hits: Counter = Counter()
        product_hits: Counter = Counter()
        for r in recs:
            ent = r.get("entities") or {}
            for b in ent.get("brands", []) or []:
                brand_hits[b] += 1
            for p in ent.get("products", []) or []:
                product_hits[p] += 1
        if brand_hits:
            md.append("**Brand hits**: " + ", ".join(f"{b}={c}" for b, c in brand_hits.most_common(10)))
            md.append("")
        if product_hits:
            md.append("**Product hits**: " + ", ".join(f"{p}={c}" for p, c in product_hits.most_common(10)))
            md.append("")

        # Samples — up to N per market
        md.append("### Samples")
        md.append("")
        by_market_recs: dict[str, list[dict]] = defaultdict(list)
        for r in recs:
            if (r.get("title") or "").startswith("[failed"):
                continue
            by_market_recs[r.get("market", "?")].append(r)

        for market, lst in sorted(by_market_recs.items()):
            md.append(f"#### Market {market}  ({len(lst)} records)")
            md.append("")
            for r in lst[:MAX_SAMPLES_PER_BUCKET]:
                md.append(f"- **{(r.get('title') or '')[:160]}**")
                md.append(f"  - url: {r.get('url', '')}")
                if r.get("published_at"):
                    md.append(f"  - published_at: {r.get('published_at')}")
                if r.get("author_or_account"):
                    md.append(f"  - author/agency: {r.get('author_or_account')}")
                if r.get("summary"):
                    md.append(f"  - summary: {(r.get('summary') or '')[:300].strip()}")
                ent = r.get("entities") or {}
                if ent.get("brands") or ent.get("products"):
                    md.append(f"  - entities: {json.dumps(ent, ensure_ascii=False)}")
                md.append("")

        # Failures
        failed_recs = [r for r in recs if (r.get("title") or "").startswith("[failed")]
        if failed_recs:
            md.append("### Failed queries")
            md.append("")
            for r in failed_recs[:10]:
                md.append(f"- {r.get('title')} — {r.get('summary', '')[:200]}")
            if len(failed_recs) > 10:
                md.append(f"- ... and {len(failed_recs) - 10} more")
            md.append("")

    # ----- legacy json files (SG MVP probes) -----
    if json_files:
        md.append("---")
        md.append("")
        md.append("## Legacy SG probe outputs (output/normalized/*.json)")
        md.append("")
        for jf in json_files[-10:]:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    md.append(f"- `{jf.name}` — {len(data)} records")
                else:
                    md.append(f"- `{jf.name}` — (non-list)")
            except Exception as e:
                md.append(f"- `{jf.name}` — read error: {e}")
        md.append("")

    # ----- raw html snapshots -----
    if html_snaps:
        md.append("## Raw HTML snapshots (parse_failed)")
        md.append("")
        for h in html_snaps:
            md.append(f"- `{h.relative_to(ROOT)}` — {h.stat().st_size} bytes")
        md.append("")

    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"  [saved] markdown → {md_path.relative_to(ROOT)}")

    # ----- copy all crawled artifacts into one dated folder -----
    copied = 0
    for jf in jsonl_files:
        shutil.copy2(jf, snap_dir / jf.name)
        copied += 1
    if html_snaps:
        (snap_dir / "raw_html").mkdir(exist_ok=True)
        for h in html_snaps:
            shutil.copy2(h, snap_dir / "raw_html" / h.name)
            copied += 1
    print(f"  [saved] archive  → {snap_dir.relative_to(ROOT)}/  ({copied} files)")
    print(f"\n  Open: {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

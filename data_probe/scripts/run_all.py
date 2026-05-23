"""Run probes sequentially and emit a summary report.

Modes:
  (default)         Run SG-market probes only (news/competitors/...)
  --global          Append the 4 global intelligence probes
  --include reddit,trends   Add opt-in probes (need creds/libs)
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import ROOT, now_iso, timestamp_slug  # noqa: E402

LOCAL_PROBES = [
    ("news",            "probe_news",             "probe_news"),
    ("competitor",      "probe_competitors",      "probe_competitors"),
    ("platform_policy", "probe_platform_policy",  "probe_platform_policy"),
    ("regulation",      "probe_regulations",      "probe_regulations"),
    ("market_data",     "probe_market_data",      "probe_market_data"),
    ("mall",            "probe_malls",            "probe_malls"),
]

GLOBAL_PROBES = [
    ("gdelt",            "probe_gdelt",            "probe_gdelt"),
    ("global_news",      "probe_global_news",      "probe_global_news"),
    ("federal_register", "probe_federal_register", "probe_federal_register"),
    ("tavily",           "probe_tavily",           "probe_tavily"),
]

OPTIONAL_PROBES = {
    "reddit": ("reddit",        "probe_reddit",  "probe_reddit"),
    "trends": ("google_trends", "probe_trends",  "probe_trends"),
}


def run_probe(module_name: str, fn_name: str) -> list[dict]:
    import importlib
    mod = importlib.import_module(module_name)
    fn = getattr(mod, fn_name)
    return fn()


def build_summary(all_results: dict[str, list[dict]]) -> dict:
    total = failed = skipped = 0
    by_type = {}

    for source_type, records in all_results.items():
        s = sum(1 for r in records if r.get("status") == "success" or (not r.get("status") and not (r.get("title") or "").startswith("[failed")))
        f = sum(1 for r in records if r.get("status") == "failed" or (r.get("title") or "").startswith("[failed"))
        k = sum(1 for r in records if r.get("status") == "skipped")
        total += s + f + k
        failed += f
        skipped += k
        by_type[source_type] = {
            "success": s, "failed": f, "skipped": k, "total": len(records),
        }

    return {
        "run_at": now_iso(),
        "total_records": total,
        "success_count": total - failed - skipped,
        "failed_count": failed,
        "skipped_count": skipped,
        "by_source_type": by_type,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--global", dest="run_global", action="store_true",
                        help="Append the 5 global intelligence probes (PRD 爬虫2)")
    parser.add_argument("--include", default="",
                        help="Comma-separated opt-in probes: reddit,trends")
    parser.add_argument("--only-global", action="store_true",
                        help="Run only the global probes (skip the SG MVP probes)")
    args = parser.parse_args()

    probes = []
    if not args.only_global:
        probes.extend(LOCAL_PROBES)
    if args.run_global or args.only_global:
        probes.extend(GLOBAL_PROBES)
    for inc in [x.strip() for x in args.include.split(",") if x.strip()]:
        if inc in OPTIONAL_PROBES:
            probes.append(OPTIONAL_PROBES[inc])
        else:
            print(f"  [warn] unknown --include option: {inc}")

    print("=" * 60)
    print("Aurum Radar — Data Probe Run")
    print(f"Started: {now_iso()}")
    print(f"Probes : {[p[0] for p in probes]}")
    print("=" * 60)

    all_results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    for source_type, module_name, fn_name in probes:
        print(f"\n[{source_type.upper()}]")
        try:
            records = run_probe(module_name, fn_name)
            all_results[source_type] = records
        except Exception:
            tb = traceback.format_exc()
            print(f"  [ERROR] probe crashed:\n{tb}")
            errors[source_type] = tb
            all_results[source_type] = []

    summary = build_summary(all_results)
    if errors:
        summary["probe_errors"] = {k: v.splitlines()[-1] for k, v in errors.items()}

    summary_path = ROOT / "output" / f"summary_{timestamp_slug()}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total records : {summary['total_records']}")
    print(f"  Success       : {summary['success_count']}")
    print(f"  Failed        : {summary['failed_count']}")
    print(f"  Skipped       : {summary['skipped_count']}")
    print()
    for stype, counts in summary["by_source_type"].items():
        print(f"  {stype:<28} success={counts['success']:<4} failed={counts['failed']:<3} skipped={counts['skipped']}")
    print(f"\nSummary saved → {summary_path.relative_to(ROOT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

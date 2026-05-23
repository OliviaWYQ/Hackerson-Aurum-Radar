"""Run the Agent flow + strategic intelligence council on documents already
in RDS ``raw_documents``, persist results per market, and print the
inferred reports.

Usage (from backend/)::

    # Single market
    python -m scripts.run_council --market SG --since 30d

    # Multiple markets (comma-separated)
    python -m scripts.run_council --market SG,TH,JP --since 30d

    # Auto-discover all markets with enough docs in the window
    python -m scripts.run_council --all-markets --min-docs 10

    # Skip the QA evaluation agent (cheaper)
    python -m scripts.run_council --all-markets --no-evaluation

Reads raw_documents directly from RDS (data_probe should have already
populated it via ``scripts.ingest_crawl_data``). For each selected market:

  extract → score → forecast → brief        (pipeline stages 3-6, persisted)
  council {market}                          (§17: 5 experts → CSO)
                                              → council_reports + action_items
  evaluation                                (QA pass, optional)

Stages ingest + clean are skipped — the docs are already cleaned and have
a ``content_hash`` row in the DB, so we feed Stage 3 directly and pre-fill
the hash → id map so Stage 4 can link ``intelligence_events.raw_document_id``.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

from app.database import repository
from app.database.session import SessionLocal
from app.services.council import derive_actions, normalize_department_actions, run_council
from app.services.evaluation import run_evaluation
from app.services.pipeline import run_pipeline
from app.services.taxonomy import (
    DEFAULT_WINDOW_DAYS,
    MIN_DOCS_PER_MARKET,
    display_name_for,
)


def _parse_since(value: str | None) -> datetime | None:
    """Parse --since: ISO date / datetime, or ``Nd`` shorthand (e.g. ``30d``)."""
    if not value:
        return None
    if value.endswith("d") and value[:-1].isdigit():
        return datetime.now(timezone.utc) - timedelta(days=int(value[:-1]))
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _print_council(r: dict) -> None:
    print("\n" + "=" * 72)
    print(f"智囊团决策报告 —— {r.get('market', '')}（{r.get('time_window', '')}）")
    print("=" * 72)
    print(f"\n【总体结论】\n{r.get('council_summary', '')}")

    conf = r.get("confidence", {}) or {}
    print(f"\n【整体置信度】{conf.get('level', '?')}  score={conf.get('score', '?')}")
    if conf.get("rationale"):
        print(f"  {conf.get('rationale', '')}")

    print("\n【关键信号】")
    for s in r.get("key_signals", []):
        print(f"  · {s.get('signal', '')}  证据 {s.get('evidence_ids', [])}")

    print("\n【机会】")
    for o in r.get("opportunities", []):
        print(f"  + {o.get('title', '')}（{o.get('category', '')}，conf {o.get('confidence', '?')}）")
    print("\n【风险】")
    for x in r.get("risks", []):
        print(f"  - [{x.get('severity', '?')}] {x.get('title', '')}")
    print("\n【需关注】")
    for w in r.get("watch_items", []):
        print(f"  ? {w.get('item', '')}")

    opts = r.get("strategic_options", {}) or {}
    for key, label in [("upper_strategy", "上策"), ("middle_strategy", "中策"), ("lower_strategy", "下策")]:
        s = opts.get(key, {})
        if not s:
            continue
        print(f"\n【{label}】{s.get('name', '')}")
        print(f"  兵法依据：{s.get('classical_basis', '')}")
        print(f"  打法：{s.get('description', '')}")

    print("\n【部门行动】")
    for team, items in normalize_department_actions(r.get("department_actions")).items():
        for a in items or []:
            print(f"  [{team}|{a.get('priority', '')}] {a.get('action', '')}")

    disagreements = r.get("expert_disagreements", [])
    if disagreements:
        print("\n【专家分歧】")
        for d in disagreements:
            print(f"  · {d.get('topic', '')} → {d.get('council_resolution', '')}")

    print(f"\n落库行动项：{r.get('_derived_action_count', 0)} 条")
    print("=" * 72)


def _print_evaluation(r: dict) -> None:
    print("\n" + "=" * 72)
    print(f"评估报告 —— {r.get('market')}  总体质量分 {r.get('overall_quality_score', '?')}/100")
    print("=" * 72)
    rule = r.get("rule_checks", {})
    print(f"  引用完整率 {rule.get('citation_completeness')}   "
          f"可回溯率 {rule.get('traceability_rate')}")
    print(f"  来源可信度分布 {rule.get('credibility_distribution')}")
    print(f"  证据落地通过率 {r.get('grounding_pass_rate')}   "
          f"可信度匹配率 {r.get('credibility_match_rate')}")
    sl = r.get("council_logic") or {}
    print(f"  决策逻辑审查：{sl.get('logic_verdict', '-')}")
    for issue in sl.get("issues", []):
        print(f"    - 问题：{issue}")
    hr = r.get("human_review_list", [])
    print(f"  需人工复核 {len(hr)} 项：")
    for it in hr[:8]:
        print(f"    [事件{it.get('event_id')}] {it.get('issue', '')}")
    print("=" * 72)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run agent pipeline + council on raw_documents from RDS"
    )
    p.add_argument(
        "--market",
        default=None,
        help="Market code(s), comma-separated. ISO-3166 alpha-2 (SG/TH/JP/...). "
        "Mutually exclusive with --all-markets.",
    )
    p.add_argument(
        "--all-markets",
        action="store_true",
        help=f"Auto-discover markets in RDS with ≥ --min-docs documents in the window.",
    )
    p.add_argument(
        "--min-docs",
        type=int,
        default=MIN_DOCS_PER_MARKET,
        help=f"Min raw_documents in window to consider a market (default: {MIN_DOCS_PER_MARKET})",
    )
    p.add_argument(
        "--since",
        default=f"{DEFAULT_WINDOW_DAYS}d",
        help=f"ISO date / datetime, or Nd shorthand (default: {DEFAULT_WINDOW_DAYS}d). Filters published_at.",
    )
    p.add_argument("--until", default=None, help="Upper bound on published_at (optional)")
    p.add_argument("--limit", type=int, default=None, help="Max docs per market to load")
    p.add_argument(
        "--no-evaluation",
        action="store_true",
        help="Skip the QA evaluation agent",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Parallel markets (default 1 = serial). 4 is a safe value for "
        "DashScope qwen-plus + qwen-max; higher may hit LLM rate limits.",
    )
    p.add_argument(
        "--output",
        default="council_output.json",
        help="Where to dump the full council + evaluation JSON (markets nested)",
    )
    args = p.parse_args()
    if args.market and args.all_markets:
        p.error("--market and --all-markets are mutually exclusive")
    if not args.market and not args.all_markets:
        args.all_markets = True  # default to auto-discovery
    return args


def _resolve_markets(args: argparse.Namespace, since: datetime | None, until: datetime | None) -> list[str]:
    """Decide which market codes to process."""
    if args.market:
        return [m.strip() for m in args.market.split(",") if m.strip()]

    # --all-markets: auto-discover from RDS
    db = SessionLocal()
    try:
        rows = repository.list_markets_with_docs(
            db, since=since, until=until, min_docs=args.min_docs
        )
    finally:
        db.close()
    print(
        f"== 自动发现 {len(rows)} 个市场（≥ {args.min_docs} 篇，{args.since} 内）=="
    )
    for m, c in rows:
        print(f"   {m:8} {display_name_for(m):8} {c} 篇")
    print()
    return [m for m, _ in rows]


def _run_one_market(market: str, since, until, limit, *, run_eval: bool) -> tuple[dict, dict | None]:
    """Run the full per-market flow; return (council_report, evaluation_or_none)."""
    db = SessionLocal()
    try:
        docs, hash_id_map = repository.list_raw_documents(
            db, market=market, since=since, until=until, limit=limit
        )
    finally:
        db.close()

    if not docs:
        print(f"!! {market}: 窗口内无文档，跳过。")
        return {}, None

    print(f"\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(f">>>>>  {market} {display_name_for(market)} — {len(docs)} 篇 raw_documents")
    print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    result = run_pipeline(
        markets=[market],
        seed_documents=docs,
        prefilled_hash_id_map=hash_id_map,
        stages=["extract", "score", "forecast", "brief"],
        trigger_type="manual",
        persist=True,
    )
    for s in result.stages:
        print(f"  {s.stage.value:9} {s.status.value:8} rows={s.rows_affected}"
              + (f"  ERROR: {s.error_message}" if s.error_message else ""))

    print(f"\n== 战略情报智囊团（§17，{market}）==")
    db = SessionLocal()
    evaluation: dict | None = None
    try:
        report = run_council(db, market)
        repository.save_council_report(db, market, report)
        actions = derive_actions(market, report)
        report["_derived_action_count"] = repository.save_actions(db, actions)
        _print_council(report)
        if run_eval:
            print(f"\n== 评估 Agent：QA 复核（{market}）==")
            evaluation = run_evaluation(db, market, council_report=report)
            _print_evaluation(evaluation)
    finally:
        db.close()
    return report, evaluation


def _run_one_market_buffered(
    market: str, since, until, limit, *, run_eval: bool
) -> tuple[dict, dict | None, str, str | None]:
    """Run one market with stdout captured into a string buffer.

    Returns ``(report, evaluation, captured_output, error_message)``. Used
    by the concurrent path so that each market's printed output appears
    as a coherent block instead of interleaving across threads. Loguru
    progress lines still go to stderr in real time.
    """
    buf = io.StringIO()
    err_msg: str | None = None
    report: dict = {}
    evaluation: dict | None = None
    with redirect_stdout(buf):
        try:
            report, evaluation = _run_one_market(
                market, since, until, limit, run_eval=run_eval
            )
        except Exception as exc:  # noqa: BLE001 - reported via err_msg
            err_msg = str(exc)
            print(f"!! {market}: failed — {exc}")
    return report, evaluation, buf.getvalue(), err_msg


def main() -> None:
    args = _parse_args()
    since = _parse_since(args.since)
    until = _parse_since(args.until)

    markets = _resolve_markets(args, since, until)
    if not markets:
        print(f"!! 没有市场达到 --min-docs={args.min_docs} 的门槛，无事可做。")
        return

    concurrency = max(1, args.concurrency)
    all_results: dict[str, dict] = {}
    failures: list[tuple[str, str]] = []

    if concurrency == 1:
        # Serial path — keep the original live-print behavior
        for market in markets:
            try:
                report, evaluation = _run_one_market(
                    market, since, until, args.limit,
                    run_eval=not args.no_evaluation,
                )
            except Exception as exc:  # noqa: BLE001 - one market must not abort others
                print(f"!! {market}: failed — {exc}")
                failures.append((market, str(exc)))
                continue
            if report:
                all_results[market] = {"council": report, "evaluation": evaluation}
    else:
        # Concurrent path — buffer each market's stdout, flush on completion
        print(f"== 并发跑 {len(markets)} 个市场，concurrency={concurrency} ==\n")
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = {
                ex.submit(
                    _run_one_market_buffered,
                    m, since, until, args.limit,
                    run_eval=not args.no_evaluation,
                ): m
                for m in markets
            }
            for fut in as_completed(futures):
                market = futures[fut]
                report, evaluation, captured, err = fut.result()
                # Flush this market's full output as a block
                sys.stdout.write(captured)
                sys.stdout.flush()
                if err:
                    failures.append((market, err))
                elif report:
                    all_results[market] = {"council": report, "evaluation": evaluation}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n所有市场决策报告已写入 backend/{args.output}")
    print(f"成功 {len(all_results)} 个市场，失败 {len(failures)} 个")
    for m, err in failures:
        print(f"  FAIL {m}: {err}")


if __name__ == "__main__":
    main()

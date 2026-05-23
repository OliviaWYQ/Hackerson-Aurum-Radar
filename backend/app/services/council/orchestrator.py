"""Council orchestrator — pipeline stage 7 «行动» (architecture.md §17).

Runs the jewelry intelligence council for one market: five experts analyse the
intelligence_batch in parallel, then the chief strategy officer synthesises a
decision report. The caller persists the report to council_reports and derives
action_items via app.services.council.actions.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from loguru import logger
from sqlalchemy.orm import Session

from app.services.council import adapter, loader
from app.services.llm import get_llm

_SYSTEM = (
    "你是珠宝海外市场战略情报智囊团的成员，严格遵循给定的 Skill 定义文件工作，"
    "只输出单个 JSON 对象，不要 markdown 代码围栏。"
)

_MILITARY_ID = "military_strategist"


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _military_knowledge() -> str:
    """The three knowledge sources injected for the 兵法谋士 expert (§17.4)."""
    return (
        "## 兵法策略库（strategy_library.json —— 计策匹配唯一允许引用的清单）\n"
        + _dump(loader.load_strategy_library())
        + "\n\n## 孙子兵法 skill —— SKILL.md\n"
        + loader.load_knowledge("sunzi-strategy/SKILL.md")
        + "\n\n## 孙子兵法 skill —— 13 条原则库（references/principles.md）\n"
        + loader.load_knowledge("sunzi-strategy/references/principles.md")
        + "\n\n## 毛选 skill —— SKILL.md\n"
        + loader.load_knowledge("maoxuan/SKILL.md")
    )


def _run_expert(expert: dict, batch: dict, snapshot: dict) -> tuple[str, dict | None]:
    """Run one analysis expert. Returns (expert_id, output | None on failure).

    A single expert failing must not abort the council (architecture.md §17.8).
    """
    user = (
        f"# 你的专家 Skill 定义\n{expert['content']}\n\n"
        f"# 本市场研判背景（market_snapshot）\n{_dump(snapshot)}\n\n"
        f"# 本轮情报批次（intelligence_batch）\n{_dump(batch)}\n\n"
    )
    if expert["id"] == _MILITARY_ID:
        user += f"# 谋略知识源（你的分析透镜与计策清单）\n{_military_knowledge()}\n\n"
    user += (
        "# 任务\n"
        "1. 只在你的 Scope 范围内分析，超范围的转 questions_for_experts。\n"
        "2. 按你的 Analysis Framework 逐条处理情报，每个判断绑定 evidence_ids。\n"
        "3. 证据不足（单一来源 / 未验证社媒 / 单时间点）置信度不得高于 medium。\n"
        "4. 严格按你的 Output Contract 输出单个 JSON 对象。"
    )
    try:
        out = get_llm().chat_json(system=_SYSTEM, user=user, temperature=0.4)
        return expert["id"], out
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, see §17.8
        logger.warning(f"[council] expert {expert['id']} failed: {exc}")
        return expert["id"], None


def run_council(db: Session, market: str) -> dict:
    """Run the council for one market; return the decision report (§17.6)."""
    llm = get_llm()
    if not llm.is_configured:
        raise RuntimeError("DASHSCOPE_API_KEY not configured — the council needs the LLM")

    batch = adapter.build_batch(db, market)
    if not batch["items"]:
        raise RuntimeError(
            f"No intelligence_events for {market} — run the main pipeline first"
        )
    snapshot = adapter.market_snapshot_context(db, market)
    experts = loader.analysis_experts()
    logger.info(
        f"[council] {market}: {len(batch['items'])} items, {len(experts)} experts"
    )

    # warm the LLM client before the thread pool to avoid a first-call race
    _ = llm.client

    # stage 1 — experts analyse the same batch in parallel, blind to each other
    with ThreadPoolExecutor(max_workers=max(1, len(experts))) as pool:
        results = list(pool.map(lambda e: _run_expert(e, batch, snapshot), experts))
    expert_outputs = {eid: out for eid, out in results if out is not None}
    failed = [eid for eid, out in results if out is None]
    if not expert_outputs:
        raise RuntimeError(f"All council experts failed for {market}")
    logger.info(
        f"[council] {market}: {len(expert_outputs)} experts ok, failed={failed or 'none'}"
    )

    # stage 2 — chief strategy officer synthesises the decision report
    cso = loader.synthesis_expert()
    ratio = adapter.primary_source_ratio(batch)
    user = (
        f"# 总参谋 Skill 定义\n{cso['content']}\n\n"
        f"# 综合指令\n{loader.load_prompt('synthesis_prompt')}\n\n"
        f"# 原始情报批次\n{_dump(batch)}\n\n"
        f"# 五位专家的输出\n{_dump(expert_outputs)}\n\n"
        f"# 一手来源占比\n{ratio}\n"
    )
    if failed:
        user += (
            f"\n# 注意：以下专家调用失败，缺失其视角，整体置信度需下调一档：{failed}\n"
        )
    user += (
        "\n# 任务\n严格按 output_schema.json 输出单个 JSON 决策报告，含字段："
        "council_summary / market / time_window / key_signals / opportunities / risks / "
        "watch_items / strategic_options（每策含 classical_basis）/ department_actions / "
        "evidence_chain / expert_disagreements / confidence / next_observation_points。"
    )
    report = llm.chat_json(system=_SYSTEM, user=user, temperature=0.4)
    if not isinstance(report, dict):
        raise RuntimeError(f"Council synthesis returned a non-object report for {market}")

    # ensure the identity fields downstream code (actions / API) relies on
    report.setdefault("market", market)
    report.setdefault("time_window", batch["batch_meta"].get("time_window", ""))
    report["expert_analyses"] = expert_outputs
    logger.info(f"[council] {market}: decision report ready")
    return report

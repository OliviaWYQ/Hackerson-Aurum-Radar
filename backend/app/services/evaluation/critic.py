"""LLM critic for the evaluation agent — evidence grounding & logic review.

Model tiering (architecture.md §12): per-event grounding is a light, repetitive
task → qwen-flash; the holistic strategy logic review is complex → qwen-max.
"""
from __future__ import annotations

import json

from loguru import logger

from app.core.config import settings
from app.services.llm import get_llm

_SYS = "你是珠宝战略情报的质量审查员，严格、挑剔，只输出 JSON。"


def critique_event(event: dict, source_excerpt: str) -> dict:
    """Per-event grounding & credibility check — light task (qwen-flash)."""
    user = f"""事件（Agent 抽取的结果）：
{json.dumps(event, ensure_ascii=False, indent=2)}

来源原文节选：
{(source_excerpt or "（无正文）")[:1500]}

审查：
1. business_impact 是否能从原文与摘要合理推出？有无夸大或无依据的臆测？
2. 该事件来源可信度为 {event.get('credibility_level', 'unknown')}，
   其 confidence / priority 是否与来源可信度匹配（低可信来源不应给高确信）？
输出 JSON：
{{"verdict": "grounded|overstated|unsupported",
  "credibility_ok": true,
  "issue": "若有问题简述，没有则空字符串"}}"""
    try:
        return get_llm().chat_json(
            system=_SYS, user=user,
            model=settings.DASHSCOPE_MODEL_LIGHT, temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"event critique failed: {exc}")
        return {"verdict": "unknown", "credibility_ok": None, "issue": str(exc)[:80]}


def critique_council(council_report: dict) -> dict:
    """Holistic logic review of the council decision report — complex task (qwen-max)."""
    payload = {
        "council_summary": council_report.get("council_summary"),
        "key_signals": council_report.get("key_signals"),
        "opportunities": council_report.get("opportunities"),
        "risks": council_report.get("risks"),
        "strategic_options": council_report.get("strategic_options"),
        "expert_disagreements": council_report.get("expert_disagreements"),
        "confidence": council_report.get("confidence"),
    }
    user = f"""智囊团决策报告：
{json.dumps(payload, ensure_ascii=False, indent=2)}

审查决策报告的逻辑链是否自洽：
1. council_summary 是否给出明确判断方向，还是泛泛而谈？
2. opportunities / risks 是否都绑定了证据（evidence_ids）？有无与情报矛盾的结论？
3. 上中下三策是否层次清晰、与 council_summary 的推荐一致？三策之间有无矛盾？
4. department_actions 行动是否具体可执行，还是空话？
5. confidence 是否与证据强度匹配（证据稀薄却给 high 即为问题）？
输出 JSON：
{{"logic_verdict": "sound|minor_issues|flawed",
  "issues": ["..."],
  "strengths": ["..."]}}"""
    try:
        return get_llm().chat_json(
            system=_SYS, user=user,
            model=settings.DASHSCOPE_MODEL_REASONING, temperature=0.3,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"council critique failed: {exc}")
        return {"logic_verdict": "unknown", "issues": [str(exc)[:80]], "strengths": []}

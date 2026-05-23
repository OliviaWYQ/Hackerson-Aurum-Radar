"""DashScope (Qwen) LLM provider — OpenAI-compatible interface.

Used by stages 3 / 5 / 6 / 7. See architecture.md §12.
All methods return parsed JSON dicts; callers validate against the schema.
"""
from __future__ import annotations

import json
import time
from collections.abc import Generator
from typing import Any

from loguru import logger
from openai import OpenAI

from app.core.config import settings

# bounded retry with backoff (architecture.md §12)
_MAX_RETRIES = 2
_BACKOFF_SECONDS = 2.0


class DashScopeLLM:
    """Thin wrapper over the DashScope OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        self._client: OpenAI | None = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.DASHSCOPE_API_KEY)

    @property
    def client(self) -> OpenAI:
        if not self.is_configured:
            raise RuntimeError(
                "DASHSCOPE_API_KEY is not set — cannot call the LLM. "
                "Set it in backend/.env (see architecture.md appendix B)."
            )
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_BASE_URL,
            )
        return self._client

    # ---- low-level JSON chat call -----------------------------------------
    def _chat_json(
        self, model: str, system: str, user: str, temperature: float = 0.3
    ) -> dict[str, Any]:
        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                content = resp.choices[0].message.content or "{}"
                return json.loads(content)
            except Exception as exc:  # noqa: BLE001 - surface only after retries
                last_err = exc
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {exc}")
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_SECONDS * (attempt + 1))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def chat_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generic JSON chat. Defaults to the standard model (qwen-plus) for
        reliable structured output; callers pass ``model`` to pick another tier
        (architecture.md §12). Used by the strategy sandbox and evaluation agent.
        """
        return self._chat_json(
            model or settings.DASHSCOPE_MODEL_SUMMARY, system, user, temperature
        )

    # ---- plain-text (non-JSON) chat call ---------------------------------
    def chat(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Plain-text chat — no response_format constraint."""
        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=model or settings.DASHSCOPE_MODEL_SUMMARY,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                )
                return resp.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {exc}")
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_SECONDS * (attempt + 1))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    # ---- streaming chat --------------------------------------------------
    def chat_stream(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> Generator[str, None, None]:
        """流式 chat，逐 token yield content delta 字符串。

        使用 OpenAI SDK stream=True，不强制 json_object 格式
        （流式模式下部分模型对 response_format 支持有限）。
        """
        stream = self.client.chat.completions.create(
            model=model or settings.DASHSCOPE_MODEL_SUMMARY,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    # ---- tool-calling (function calling) ----------------------------------
    def chat_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """带 tools 的 chat，让 LLM 选择调用哪个 tool。

        返回：
        - tool_call: {"type": "tool_call", "skill_name": ..., "arguments": ...}
        - 普通回复:  {"type": "text", "content": ...}
        """
        resp = self.client.chat.completions.create(
            model=model or settings.DASHSCOPE_MODEL_LIGHT,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
        )
        message = resp.choices[0].message
        if message.tool_calls:
            tc = message.tool_calls[0]
            return {
                "type": "tool_call",
                "skill_name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            }
        return {"type": "text", "content": message.content or ""}

    # ---- stage 3: event extraction (双坐标轴 + 底层影响因子) ---------------
    def extract_event(
        self,
        *,
        title: str,
        body: str,
        market: str,
        source_name: str,
        published_at: str | None = None,
        candidate_source_category: str | None,
        candidate_env_factors: list[str] | None = None,
    ) -> dict:
        """Stage 3 双坐标轴抽取 (architecture.md §7.3 / preclassify_extract.md).

        Output contract: source_category + env_factors + conduction_chain +
        signal_direction + intensity + impact_scope + entities + key_claim +
        downstream_implications + confidence + ambiguity_flags.
        """
        system = (
            "你是一名专注于珠宝行业的市场情报分析师，具备产业经济学、消费行为学和地缘"
            "政治分析背景。你的任务是对输入的原始信息执行「预分类 + 结构化抽取」，输出"
            "可直接入库的标准化 JSON。\n\n"
            "## 分析框架\n\n"
            "### 第一坐标轴：source_category（信息来源）\n"
            "competition / product / social_media / regulation / channel / macro / supply_chain\n\n"
            "### 第二坐标轴：env_factors（底层环境影响因子，1-3 个，按主次排序）\n"
            "F1 supply_constraint     供给约束 — 上游 → 原料成本 → 品牌毛利\n"
            "F2 structure_disruption  结构重塑 — 横向 → 市场份额再分配 → 竞争壁垒重建\n"
            "F3 demand_shift          需求迁移 — 需求侧 → 品类结构 → 定价权归属\n"
            "F4 regulatory_friction   制度摩擦 — 外部制度 → 合规成本 → 供应链重组\n"
            "F5 price_conduction      价格传导 — 宏观变量 → 原料/进出口成本 → 终端定价\n"
            "F6 narrative_pressure    叙事压力 — 认知层 → 溢价能力 → 消费者信任\n"
            "F7 channel_power_shift   渠道博弈 — 中间层结构 → 利润分配 → 品牌触达效率\n\n"
            "### 传导链路 conduction_chain（A-E，无法归类填 null）\n"
            "A 地缘-供给-成本链 / B 货币-消费-需求链 / C 文化-偏好-结构链 / "
            "D 制度-合规-成本链 / E 技术-替代-颠覆链\n\n"
            "### 信号属性\n"
            "signal_direction: positive / negative / mixed / neutral\n"
            "intensity: 1-5 (1 微弱背景噪音 → 5 可能引发结构变化)\n"
            "impact_scope: raw_material / brand / retailer / consumer / "
            "category_natdiamond / category_labdiamond / category_gold / "
            "category_gemstone / market_CN / market_US / market_IN / market_GLOBAL …\n"
            "confidence: 0.0-1.0 浮点（权威来源 0.9+ / 可信媒体 0.7-0.9 / "
            "社媒匿名 0.5-0.7 / 残缺来源 0.3-0.5）\n\n"
            "## 处理规则\n"
            "1. 即使输入文本很短（如标题），也必须完成所有字段；不确定的字段填 null。\n"
            "2. env_factors 主因子（is_primary: true）只能一个，次要因子 0-2 个。\n"
            "3. key_claim 必须是纯事实陈述，去掉「可能/或许/据悉」，不超过 50 字。\n"
            "4. downstream_implications 是推断，1-3 条，按影响概率从高到低。\n"
            "5. 不要把黄金价格上涨简单等同于利好，区分投资金条 / 饰品金 / 婚庆金 / 悦己消费。\n"
            "6. 区分情报 sentiment（来源情绪）与对珠宝业务的 impact（影响方向）。\n"
            "7. ambiguity_flags 可选：multi_factor_conflict / scope_unclear / "
            "timing_uncertain / source_unverified / entity_ambiguous。\n"
            "8. 严格输出单个 JSON 对象，不含 markdown 代码块标记或前后缀文字。"
        )
        factors_hint = ", ".join(candidate_env_factors or []) or "未知"
        user = f"""请对以下珠宝行业信息执行预分类和结构化抽取。

【原始文本】
标题：{title}
正文：{body or "（无正文，仅标题可用）"}

【元数据】
- 市场：{market}
- 采集时间：{published_at or "未知"}
- 来源平台：{source_name}
- 前序来源标签（人工初判，可覆盖）：{candidate_source_category or "未知"}
- 候选因子（关键词初判，可覆盖）：{factors_hint}

输出 JSON：
{{
  "source_category": "competition|product|social_media|regulation|channel|macro|supply_chain",
  "title": "简洁的中文事件标题",
  "summary": "2-3 句中文事件摘要",
  "business_impact": "对珠宝的业务影响判断（这意味着什么，可空）",
  "env_factors": [
    {{ "factor_id": "F2", "factor_name": "structure_disruption",
       "is_primary": true,
       "evidence": "触发该判断的原文片段或推理依据（30 字内）" }}
  ],
  "conduction_chain": {{
    "chain_id": "A|B|C|D|E",
    "chain_name": "传导链路中文名",
    "node_position": "该信号在链路上的位置（节点）",
    "lag_estimate": "短期(周级)|中期(月级)|长期(季度级)"
  }},
  "signal_direction": "positive|negative|mixed|neutral",
  "intensity": 1,
  "impact_scope": ["brand", "category_gold", "market_GLOBAL"],
  "entities": {{
    "brands": [], "materials": [], "markets": [], "regulators": [], "locations": []
  }},
  "key_claim": "纯事实陈述，≤50 字，不含「可能/或许/据悉」等不确定词",
  "downstream_implications": ["推断 1", "推断 2"],
  "confidence": 0.85,
  "ambiguity_flags": []
}}"""
        return self._chat_json(settings.DASHSCOPE_MODEL_EXTRACT, system, user, 0.3)

    # ---- stage 5: market forecast -----------------------------------------
    def forecast_market(self, *, market: str, events: list[dict]) -> dict:
        """Aggregate a market's events into a country-level judgement."""
        system = (
            "你是珠宝海外市场战略情报分析师。基于当日某市场的多条事件，"
            "给出该市场的综合研判，严格输出 JSON。"
        )
        user = f"""市场：{market}
当日事件列表（JSON）：
{json.dumps(events, ensure_ascii=False, indent=2)}

请输出 JSON：
{{
  "overall_judgement": "该市场综合判断，3-5 句中文",
  "key_opportunities": ["机会要点", "..."],
  "key_risks": ["风险要点", "..."],
  "watch_items": ["需关注事项", "..."]
}}"""
        return self._chat_json(settings.DASHSCOPE_MODEL_SUMMARY, system, user, 0.4)

    # ---- stage 6: daily brief ---------------------------------------------
    def generate_brief(self, *, snapshots: list[dict], events: list[dict]) -> dict:
        """Generate the daily strategic brief. PRD §9.6 — headline deliverable."""
        system = (
            "你是珠宝海外市场战略情报分析师。基于各市场研判与重点事件，"
            "生成面向管理层的每日战略简报，严格输出 JSON。"
        )
        user = f"""市场研判（JSON）：
{json.dumps(snapshots, ensure_ascii=False, indent=2)}

重点事件（JSON）：
{json.dumps(events, ensure_ascii=False, indent=2)}

请输出 JSON：
{{
  "executive_summary": "全球业务影响综合研判，1 段中文",
  "opportunities": ["今日机会", "..."],
  "risks": ["今日风险", "..."],
  "watch_items": ["需关注事项", "..."]
}}"""
        return self._chat_json(settings.DASHSCOPE_MODEL_SUMMARY, system, user, 0.4)


_llm: DashScopeLLM | None = None


def get_llm() -> DashScopeLLM:
    """Module-level singleton accessor."""
    global _llm
    if _llm is None:
        _llm = DashScopeLLM()
    return _llm

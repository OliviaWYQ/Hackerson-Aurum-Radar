from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent

_SKILL_DIR = (
    Path(__file__).resolve().parent.parent.parent / ".skills" / "intelligence-correlation-analysis"
)


def _build_sse_chunk(
    completion_id: str,
    delta: dict[str, Any],
    finish_reason: str | None = None,
    session_id: str | None = None,
) -> str:
    chunk: dict[str, Any] = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "agent",
        "choices": [
            {"index": 0, "delta": delta, "finish_reason": finish_reason}
        ],
    }
    if session_id is not None:
        chunk["session_id"] = session_id
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


class IntelligenceCorrelationAgent(BaseAgent):
    """情报关联分析 Agent — 封装 intelligence-correlation-analysis skill。

    职责：从 messages 提取事件 ID → 调用 /events/batch 获取事件 →
         读 SKILL.md 提示词 → 流式调 LLM → 返回结果。
    """

    @property
    def agent_type(self) -> str:
        return "correlation_analysis"

    def can_handle(self, query: dict[str, Any]) -> bool:
        return query.get("type") == self.agent_type

    # ---- 事件获取 ----

    @staticmethod
    def _extract_event_ids(messages: list[dict[str, str]] | None) -> list[int]:
        """从 messages 中提取用户提到的事件 ID。

        支持格式：
        - 纯数字: "1, 2, 3" 或 "1 2 3"
        - 带 # 前缀: "#1, #2"
        - 中英文混排: "分析事件 1、2、3 的关联"
        """
        if not messages:
            return []
        user_text = " ".join(
            m.get("content", "") for m in messages if m.get("role") == "user"
        )
        if not user_text:
            return []
        # 匹配 #数字、纯数字（1-6位，避免匹配年份等）
        ids = re.findall(r"#?(\d{1,6})", user_text)
        seen: set[int] = set()
        result: list[int] = []
        for raw in ids:
            eid = int(raw)
            if eid not in seen:
                seen.add(eid)
                result.append(eid)
        return result

    @staticmethod
    def _fetch_events_batch(event_ids: list[int]) -> list[dict[str, Any]]:
        """调用内部 /api/events/batch 接口获取事件数据。"""
        base_url = "http://127.0.0.1:8000"
        resp = httpx.post(
            f"{base_url}/api/events/batch",
            json={"ids": event_ids},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])

    @staticmethod
    def _map_event_to_item(event: dict[str, Any]) -> dict[str, Any]:
        """将 /events/batch 返回的事件映射为 input_schema.json 中的 item 格式。"""
        item: dict[str, Any] = {
            "event_id": str(event.get("event_id")),
            "collected_at": event.get("created_at") or event.get("published_at"),
            "source_category": event.get("source_category"),
            "env_factors": event.get("env_factors", []),
            "impact_scope": event.get("impact_scope", []),
            "signal_direction": event.get("signal_direction"),
            "intensity": event.get("intensity"),
            "confidence": event.get("confidence"),
        }
        if event.get("market"):
            item["market"] = event["market"]
        if event.get("region"):
            item["region"] = event["region"]
        if event.get("key_claim"):
            item["key_claim"] = event["key_claim"]
        if event.get("summary"):
            item["event_summary"] = event["summary"]
        if event.get("conduction_chain"):
            item["conduction_chain"] = event["conduction_chain"]
        if event.get("source_url"):
            item["source_url"] = event["source_url"]
        if event.get("published_at"):
            item["published_at"] = event["published_at"]
        if event.get("source_name"):
            item["source_name"] = event["source_name"]

        return item

    @staticmethod
    def _build_input_data(
        events: list[dict[str, Any]], query: dict[str, Any],
    ) -> dict[str, Any]:
        """将事件列表构造为 input_schema.json 要求的格式。"""
        items = [IntelligenceCorrelationAgent._map_event_to_item(e) for e in events]
        markets = {e.get("market") for e in events if e.get("market")}
        created_ats = [e.get("created_at") for e in events if e.get("created_at")]
        time_window = query.get("time_window")
        if not time_window and created_ats:
            dates_sorted = sorted(created_ats)
            time_window = {"start": dates_sorted[0][:10], "end": dates_sorted[-1][:10]}
        return {
            "batch_meta": {
                "market": query.get("market") or (next(iter(markets)) if markets else "UNKNOWN"),
                "time_window": time_window or {"start": "2026-01-01", "end": "2026-12-31"},
                "item_count": len(items),
            },
            "items": items,
        }

    # ---- 提示词构建 ----

    @staticmethod
    def _build_prompts(input_data: dict[str, Any], query: dict[str, Any]) -> tuple[str, str]:
        """读取 SKILL.md 提示词 + input/output schema，构造 system/user prompt。"""
        skill_md_text = _SKILL_DIR.joinpath("SKILL.md").read_text(encoding="utf-8")
        parts = skill_md_text.split("---", 2)
        skill_body = parts[2].strip() if len(parts) >= 3 else skill_md_text

        refs_dir = _SKILL_DIR / "references"
        output_schema = None
        input_schema = None
        if refs_dir.joinpath("output_schema.json").exists():
            output_schema = json.loads(refs_dir.joinpath("output_schema.json").read_text(encoding="utf-8"))
        if refs_dir.joinpath("input_schema.json").exists():
            input_schema = json.loads(refs_dir.joinpath("input_schema.json").read_text(encoding="utf-8"))

        # system prompt = skill body + 纯文本输出覆盖指令
        system = skill_body + (
            "\n\n---\n\n## 输出格式覆盖（优先级最高，覆盖以上所有 JSON 输出规则）\n"
            "请以**纯文本**形式输出分析报告。不要输出任何 JSON、代码块或结构化标记。\n"
            "使用自然语言段落描述分析结果，可用标题和列表辅助排版，"
            "但不得输出 JSON 对象或数组。"
        )

        # user prompt = 用户消息 + input schema + input data
        user_parts: list[str] = []
        messages = query.get("messages")
        if messages:
            user_contents = [
                m["content"] for m in messages if m.get("role") == "user" and m.get("content")
            ]
            if user_contents:
                user_parts.append("## 用户指令\n" + "\n".join(user_contents))
        if input_schema:
            user_parts.append(
                "## 输入数据格式\n" + json.dumps(input_schema, ensure_ascii=False, indent=2)
            )
        user_parts.append(
            "## 输入数据\n" + json.dumps(input_data, ensure_ascii=False, indent=2)
        )
        user = "\n\n".join(user_parts)

        return system, user

    # ---- 同步执行 ----

    def run(self, query: dict[str, Any], db: Session) -> dict[str, Any]:
        from app.services.llm import get_llm

        event_ids = self._extract_event_ids(query.get("messages"))
        if len(event_ids) < 3:
            raise ValueError(
                f"关联分析至少需要 3 条事件 ID，当前提取到 {len(event_ids)} 条"
            )

        events = self._fetch_events_batch(event_ids)
        if len(events) < 3:
            raise ValueError(
                f"关联分析至少需要 3 条事件，查询到 {len(events)} 条"
            )

        input_data = self._build_input_data(events, query)
        system, user = self._build_prompts(input_data, query)

        logger.info(f"[correlation_agent] running with {len(input_data['items'])} events")
        logger.debug(f"[correlation_agent] system prompt:\n{system}")
        logger.debug(f"[correlation_agent] user prompt:\n{user}")
        text = get_llm().chat(system=system, user=user, temperature=0.4)

        return {
            "agent_type": self.agent_type,
            "input_event_count": len(input_data["items"]),
            "content": text,
        }

    # ---- 流式执行 ----

    def stream(self, query: dict[str, Any], db: Session) -> Generator[str, None, None]:
        """流式执行：提取事件 ID → /events/batch 获取 → 读提示词 → 流式调 LLM → yield SSE。"""
        from app.services.llm import get_llm

        # 1. 从 messages 提取事件 ID
        event_ids = self._extract_event_ids(query.get("messages"))
        if len(event_ids) < 3:
            error = f"关联分析至少需要 3 条事件 ID，当前提取到 {len(event_ids)} 条"
            yield _build_sse_chunk(
                "agent-error",
                {"content": json.dumps({"error": error}, ensure_ascii=False)},
                finish_reason="stop",
            )
            yield "data: [DONE]\n\n"
            return

        # 2. 调用 /events/batch 获取事件
        try:
            events = self._fetch_events_batch(event_ids)
        except Exception as exc:
            error = f"获取事件数据失败: {exc}"
            yield _build_sse_chunk(
                "agent-error",
                {"content": json.dumps({"error": error}, ensure_ascii=False)},
                finish_reason="stop",
            )
            yield "data: [DONE]\n\n"
            return

        if len(events) < 3:
            error = f"关联分析至少需要 3 条事件，查询到 {len(events)} 条"
            yield _build_sse_chunk(
                "agent-error",
                {"content": json.dumps({"error": error}, ensure_ascii=False)},
                finish_reason="stop",
            )
            yield "data: [DONE]\n\n"
            return

        # 3. 构造提示词
        input_data = self._build_input_data(events, query)
        system, user = self._build_prompts(input_data, query)

        completion_id = f"agent-{uuid.uuid4().hex[:12]}"

        # 4) role chunk
        yield _build_sse_chunk(completion_id, {"role": "assistant"})

        # 5) 流式输出 LLM token
        logger.info(f"[correlation_agent] streaming with {len(input_data['items'])} events")
        logger.debug(f"[correlation_agent] system prompt:\n{system}")
        logger.debug(f"[correlation_agent] user prompt:\n{user}")
        llm = get_llm()
        for token in llm.chat_stream(system=system, user=user, temperature=0.4):
            yield _build_sse_chunk(completion_id, {"content": token})

        # 6) stop chunk
        yield _build_sse_chunk(completion_id, {}, finish_reason="stop")
        yield "data: [DONE]\n\n"

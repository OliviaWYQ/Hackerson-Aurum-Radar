from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent


class AgentRouter:
    """Agent 路由器 — 按 query.type 确定性分发到匹配的 Agent。"""

    def __init__(self) -> None:
        self._agents: list[BaseAgent] = []
        self._type_map: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents.append(agent)
        self._type_map[agent.agent_type] = agent
        logger.info(f"[agents] registered agent: {agent.agent_type}")

    def dispatch(self, query: dict[str, Any], db: Session) -> dict[str, Any]:
        """按 query.type 路由到对应 Agent，找不到返回 400 提示。"""
        agent_type = query.get("type")
        if not agent_type:
            raise ValueError("query 必须包含 type 字段")

        agent = self._type_map.get(agent_type)
        if agent is None:
            raise ValueError(
                f"未找到 type={agent_type} 对应的 Agent，"
                f"可用类型: {list(self._type_map.keys())}"
            )

        logger.info(f"[agents] dispatching to agent: {agent.agent_type}")
        return agent.run(query, db)

    def list_agents(self) -> list[dict[str, str]]:
        return [
            {"agent_type": a.agent_type, "class": type(a).__name__}
            for a in self._agents
        ]


_router: AgentRouter | None = None


def get_agent_router() -> AgentRouter:
    global _router
    if _router is None:
        _router = AgentRouter()
    return _router

from __future__ import annotations

import abc
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session


class BaseAgent(abc.ABC):
    """Agent 基类 — Agent 封装 Skill，负责 DB 查询、输入构造、结果持久化。

    子类实现 can_handle 判断是否处理该 query，run 执行具体逻辑。
    路由层按 type 字段直接匹配，无需 LLM。
    """

    @property
    @abc.abstractmethod
    def agent_type(self) -> str:
        """Agent 类型标识，对应 query 中的 type 字段。"""

    @abc.abstractmethod
    def can_handle(self, query: dict[str, Any]) -> bool:
        """判断是否处理该 query。默认实现直接匹配 type 字段。"""

    @abc.abstractmethod
    def run(self, query: dict[str, Any], db: Session) -> dict[str, Any]:
        """执行 Agent 逻辑：构造输入 → 调用 Skill → 处理结果。"""

    @abc.abstractmethod
    def stream(self, query: dict[str, Any], db: Session) -> Generator[str, None, None]:
        """流式执行 Agent 逻辑：构造输入 → 读 Skill 提示词 → 流式调用 LLM → yield SSE 行。"""

from __future__ import annotations

from typing import Any

from loguru import logger
from stevedore import ExtensionManager

from app.services.skills.base import SkillPlugin


class SkillRegistry:
    """通过 stevedore 发现、加载和缓存 skill 插件。"""

    NAMESPACE = "aurum_radar.skills"

    def __init__(self) -> None:
        self._manager: ExtensionManager | None = None
        self._skills: dict[str, SkillPlugin] = {}

    def init(self) -> None:
        """启动时调用：扫描 entry_points，加载所有 skill 插件。"""
        self._manager = ExtensionManager(
            namespace=self.NAMESPACE,
            invoke_on_load=True,
            propagate_map_exceptions=True,
        )
        for ext in self._manager:
            plugin: SkillPlugin = ext.obj
            self._skills[ext.name] = plugin
            logger.info(f"[skills] loaded plugin: {ext.name} v{plugin.version}")
        logger.info(f"[skills] registry initialized: {len(self._skills)} plugins")

    def list_skills(self) -> list[dict[str, str]]:
        return [
            {"name": p.name, "description": p.description, "version": p.version}
            for p in self._skills.values()
        ]

    def get_skill(self, name: str) -> SkillPlugin | None:
        return self._skills.get(name)

    def run_skill(self, name: str, input_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        plugin = self._skills.get(name)
        if plugin is None:
            raise KeyError(f"Skill not found: {name}")
        return plugin.run(input_data, **kwargs)

    def list_tool_definitions(self) -> list[dict[str, Any]]:
        """返回所有 skill 的 OpenAI tool 定义列表。"""
        return [p.get_tool_definition() for p in self._skills.values()]

    def route(self, user_message: str, **kwargs: Any) -> dict[str, Any]:
        """用 LLM function calling 自动路由到正确的 skill。"""
        from app.services.llm import get_llm

        tools = self.list_tool_definitions()
        llm = get_llm()
        result = llm.chat_with_tools(
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
            **kwargs,
        )
        if result["type"] == "tool_call":
            return {
                "type": "skill_matched",
                "skill": result["skill_name"],
                "output": self.run_skill(result["skill_name"], result["arguments"]),
            }
        return {"type": "no_skill_matched", "content": result["content"]}


_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry

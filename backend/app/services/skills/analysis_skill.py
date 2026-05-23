from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.skills.base import SkillPlugin


class AnalysisSkill(SkillPlugin):
    """通用单次分析 skill 适配器。

    子类只需设置 _skill_dir 指向含 SKILL.md 的目录。
    run() 会加载 SKILL.md body 作为 system prompt，
    拼接 input_schema / output_schema，调用 LLM 返回结果。
    """

    _skill_dir: Path | None = None
    _name: str | None = None
    _description: str | None = None
    _version: str | None = None
    _skill_md_cache: str | None = None
    _references_cache: dict | None = None
    _examples_cache: dict | None = None

    def __init__(self) -> None:
        if self._skill_dir is None:
            raise ValueError(f"{type(self).__name__} must set _skill_dir")
        self._parse_metadata()

    def _parse_metadata(self) -> None:
        text = self._skill_dir.joinpath("SKILL.md").read_text(encoding="utf-8")
        meta = self._parse_frontmatter(text)
        self._name = meta.get("name", self._skill_dir.name)
        self._description = meta.get("description", "")
        self._version = meta.get("version", "0.0.0")

    @property
    def name(self) -> str:
        return self._name  # type: ignore[return-value]

    @property
    def description(self) -> str:
        return self._description  # type: ignore[return-value]

    @property
    def version(self) -> str:
        return self._version  # type: ignore[return-value]

    def run(self, input_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        from app.services.llm import get_llm

        skill_body = self.load_skill_md()
        refs = self.load_references()
        output_schema = refs.get("output_schema.json")
        input_schema = refs.get("input_schema.json")

        system = self._build_system_prompt(skill_body, output_schema)
        user = self._build_user_prompt(input_data, input_schema)

        model = kwargs.get("model")
        temperature = kwargs.get("temperature", 0.4)
        return get_llm().chat_json(
            system=system, user=user, model=model, temperature=temperature,
        )

    def _build_system_prompt(self, skill_body: str, output_schema: dict | None) -> str:
        prompt = skill_body
        if output_schema:
            prompt += (
                "\n\n## 输出格式\n严格输出符合以下 Schema 的 JSON：\n"
                + json.dumps(output_schema, ensure_ascii=False, indent=2)
            )
        prompt += "\n\n严格输出单个 JSON 对象，不要 markdown 代码围栏。"
        return prompt

    def _build_user_prompt(
        self, input_data: dict[str, Any], input_schema: dict | None,
    ) -> str:
        parts: list[str] = []
        if input_schema:
            parts.append(
                "## 输入数据格式\n"
                + json.dumps(input_schema, ensure_ascii=False, indent=2),
            )
        parts.append(
            "## 输入数据\n"
            + json.dumps(input_data, ensure_ascii=False, indent=2),
        )
        return "\n\n".join(parts)

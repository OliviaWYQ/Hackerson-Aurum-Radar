from __future__ import annotations

import abc
import json
from pathlib import Path
from typing import Any


class SkillPlugin(abc.ABC):
    """所有 Aurum-Radar skill 插件的抽象基类。

    子类必须设置 _skill_dir 指向 skill 目录（含 SKILL.md），
    并实现 name / description / version / run 属性和方法。
    """

    _skill_dir: Path | None = None

    # ---- 子类必须实现 ----

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """技能唯一标识（来自 SKILL.md frontmatter）。"""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """技能描述。"""

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """技能版本。"""

    @abc.abstractmethod
    def run(self, input_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """执行技能，接收结构化输入，返回结构化输出。"""

    # ---- 懒加载辅助 ----

    def load_skill_md(self) -> str:
        """读取 SKILL.md body（frontmatter 之后的部分），首次调用后缓存。"""
        if not hasattr(self, "_skill_md_cache") or self._skill_md_cache is None:
            self._skill_md_cache = self._read_skill_md_body()
        return self._skill_md_cache

    def load_references(self) -> dict[str, str | dict]:
        """读取 references/ 下所有文件，首次调用后缓存。"""
        if not hasattr(self, "_references_cache") or self._references_cache is None:
            self._references_cache = self._load_dir("references")
        return self._references_cache

    def load_examples(self) -> dict[str, str | dict]:
        """读取 examples/ 下所有文件，首次调用后缓存。"""
        if not hasattr(self, "_examples_cache") or self._examples_cache is None:
            self._examples_cache = self._load_dir("examples")
        return self._examples_cache

    def get_tool_definition(self) -> dict[str, Any]:
        """返回 OpenAI function calling 格式的 tool 定义。"""
        from app.services.skills.schema_converter import convert_schema

        refs = self.load_references()
        input_schema = refs.get("input_schema.json", {})
        parameters = convert_schema(input_schema)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }

    # ---- 内部方法 ----

    def _read_skill_md_body(self) -> str:
        text = self._skill_dir.joinpath("SKILL.md").read_text(encoding="utf-8")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                return text[end + 4:].lstrip("\n")
        return text

    def _load_dir(self, subdir: str) -> dict[str, str | dict]:
        result: dict[str, str | dict] = {}
        dir_path = self._skill_dir / subdir
        if not dir_path.is_dir():
            return result
        for path in sorted(dir_path.rglob("*")):
            if path.is_file():
                rel = path.relative_to(dir_path)
                content = path.read_text(encoding="utf-8")
                if path.suffix == ".json":
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        pass
                result[str(rel)] = content
        return result

    @staticmethod
    def _parse_frontmatter(text: str) -> dict[str, str]:
        """解析 SKILL.md 顶部的简单 YAML frontmatter。"""
        if not text.startswith("---"):
            return {}
        end = text.find("\n---", 3)
        if end == -1:
            return {}
        meta: dict[str, str] = {}
        for line in text[3:end].splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        return meta

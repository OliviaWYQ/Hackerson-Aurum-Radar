"""JSON Schema (Draft-07) → OpenAI function parameters 转换器。

剥离 OpenAI function calling 不支持的键（$schema, title, description 等），
展平 oneOf/anyOf，递归处理嵌套 properties，产出 {type, properties, required} 格式。
"""
from __future__ import annotations

from typing import Any

# OpenAI function parameters 不支持的顶层键
_STRIP_KEYS = {"$schema", "title", "$comment", "default", "examples"}


def convert_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """将 JSON Schema 转为 OpenAI function parameters 兼容格式。"""
    result: dict[str, Any] = {}
    _convert_node(schema, result)
    return result


def _convert_node(src: dict[str, Any], dst: dict[str, Any]) -> None:
    """递归转换单个 schema 节点。"""
    # 处理 oneOf / anyOf：取第一个选项合并到当前节点
    if "oneOf" in src:
        first = src["oneOf"][0]
        if isinstance(first, dict):
            merged = {k: v for k, v in src.items() if k != "oneOf"}
            merged.update(first)
            src = merged
    elif "anyOf" in src:
        first = src["anyOf"][0]
        if isinstance(first, dict):
            merged = {k: v for k, v in src.items() if k != "anyOf"}
            merged.update(first)
            src = merged

    for key, value in src.items():
        if key in _STRIP_KEYS:
            continue

        if key == "properties" and isinstance(value, dict):
            dst["properties"] = {k: _convert_value(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            dst["items"] = _convert_value(value)
        elif key == "required" and isinstance(value, list):
            dst["required"] = value
        elif key in ("type", "format", "minimum", "maximum", "minLength",
                      "maxLength", "minItems", "maxItems", "enum",
                      "description"):
            dst[key] = value
        # 忽略 $ref, $defs, allOf, additionalProperties 等不兼容键

    if "type" not in dst:
        dst["type"] = "object"


def _convert_value(node: dict[str, Any]) -> dict[str, Any]:
    """转换单个属性值节点。"""
    result: dict[str, Any] = {}
    _convert_node(node, result)
    return result

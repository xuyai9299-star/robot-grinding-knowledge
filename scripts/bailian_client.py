# -*- coding: utf-8 -*-
"""
阿里云百炼（DashScope）生成中文摘要与关键词。
文档: https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from config import DASHSCOPE_MODEL


def _api_key() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")


def is_llm_enabled() -> bool:
    if os.getenv("SKIP_LLM", "").lower() in ("1", "true", "yes"):
        return False
    return bool(_api_key())


def enrich_with_llm(paper: dict[str, Any]) -> dict[str, Any]:
    """
    调用千问生成 summary_zh 与 keywords。
    无 API Key 时：仅用标题/摘要前 200 字作 summary_zh，keywords 为空列表。
    """
    if not is_llm_enabled():
        abstract = (paper.get("abstract") or "")[:400]
        title = paper.get("title") or ""
        paper["summary_zh"] = abstract or f"（待补充摘要）{title[:120]}"
        paper.setdefault("keywords", [])
        return paper

    try:
        from dashscope import Generation
    except ImportError as e:
        raise RuntimeError("请安装: pip install dashscope") from e

    title = paper.get("title", "")
    abstract = paper.get("abstract", "")[:3000]
    prompt = f"""你是磨削领域文献助手。根据以下英文论文信息，输出 JSON（不要 markdown 代码块）：
{{
  "summary_zh": "200字以内中文摘要",
  "keywords": ["6个以内中文关键词"]
}}

Title: {title}
Abstract: {abstract or "(无摘要)"}
"""

    response = Generation.call(
        api_key=_api_key(),
        model=os.getenv("DASHSCOPE_MODEL", DASHSCOPE_MODEL),
        messages=[
            {"role": "system", "content": "只输出合法 JSON 对象。"},
            {"role": "user", "content": prompt},
        ],
        result_format="message",
    )

    status = getattr(response, "status_code", 200)
    if status != 200:
        code = getattr(response, "code", "")
        msg = getattr(response, "message", str(response))
        raise RuntimeError(f"DashScope 调用失败 [{status}]: {code} {msg}")

    try:
        text = response.output.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as e:
        raise RuntimeError(f"DashScope 返回格式异常: {response}") from e
    data = _parse_json_from_text(text)
    paper["summary_zh"] = data.get("summary_zh") or ""
    kws = data.get("keywords") or []
    if isinstance(kws, str):
        kws = [k.strip() for k in re.split(r"[,，、]", kws) if k.strip()]
    paper["keywords"] = kws[:8]
    return paper


def _parse_json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return {}

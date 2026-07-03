# -*- coding: utf-8 -*-
"""解析 Zotero 导出的 CSV（中英列名兼容）。"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

TITLE_KEYS = ("Title", "标题", "title")
AUTHOR_KEYS = ("Author", "作者", "authors")
YEAR_KEYS = ("Publication Year", "Year", "年份", "year")
VENUE_KEYS = ("Publication Title", "Journal", "期刊", "venue")
DOI_KEYS = ("DOI", "doi")
URL_KEYS = ("Url", "URL", "url")
ABSTRACT_KEYS = ("Abstract Note", "Abstract", "摘要", "abstract")
SCHOOL_KEYS = ("School", "学校", "school", "Manual Tags")


def _pick(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for k in keys:
        if k in row and row[k] and str(row[k]).strip():
            return str(row[k]).strip()
    return ""


def _school_from_filename(path: Path) -> str:
    name = path.stem.lower()
    if "华中" in name or "武大" in name:
        return "华中武大"
    if "西北" in name or "西工大" in name:
        return "西北工大"
    if "重大" in name or "重庆" in name:
        return "重庆大学"
    return "未标注"


def _normalize_doi(doi: str) -> str:
    doi = doi.strip().lower()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return doi


def parse_zotero_csv(path: Path) -> list[dict[str, Any]]:
    """返回尚未分配 id 的论文字典列表。"""
    default_school = _school_from_filename(path)
    papers: list[dict[str, Any]] = []

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return papers
        for row in reader:
            title = _pick(row, TITLE_KEYS)
            if not title:
                continue
            school = _pick(row, SCHOOL_KEYS) or default_school
            papers.append(
                {
                    "school": school,
                    "title": title,
                    "authors": _pick(row, AUTHOR_KEYS),
                    "year": _pick(row, YEAR_KEYS),
                    "venue": _pick(row, VENUE_KEYS),
                    "doi": _normalize_doi(_pick(row, DOI_KEYS)),
                    "url": _pick(row, URL_KEYS),
                    "abstract": _pick(row, ABSTRACT_KEYS),
                    "language": "en",
                }
            )
    return papers


def dedupe_key(paper: dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").strip()
    if doi:
        return f"doi:{doi}"
    title = re.sub(r"\s+", " ", (paper.get("title") or "").lower().strip())
    return f"title:{title}"

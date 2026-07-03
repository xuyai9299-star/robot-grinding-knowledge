# -*- coding: utf-8 -*-
"""项目路径与百炼（DashScope）配置。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

MASTER_JSON = ROOT / "papers_enriched_updated.json"
CLASSIFIED_JSON = ROOT / "papers_classified.json"
MINDMAP_STATS_JSON = ROOT / "mindmap_stats.json"
PAPERS_INDEX_JSON = ROOT / "papers_index.json"
CATEGORY_INDEX_JSON = ROOT / "category_index.json"
MINDMAPS_FIVE_JSON = ROOT / "mindmaps_five.json"
FREEMIND_MM = ROOT / "机器人柔性磨削知识库_五维.mm"
OUTLINE_HTML = ROOT / "outline.html"
NEW_PAPERS_DIR = ROOT / "new_papers"
ARCHIVE_DIR = ROOT / "archive"

# 百炼 / DashScope：见 https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
DASHSCOPE_MODEL = "qwen-plus"  # 可改为 qwen-turbo 以节省额度
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

TAXONOMY_VERSION = "1.0"
KB_ROOT_TITLE = "机器人柔性磨削知识库"

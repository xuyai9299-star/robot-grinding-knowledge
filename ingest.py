# -*- coding: utf-8 -*-
"""
增量入库入口（本地 / GitHub Actions 均可运行）。

用法:
  python ingest.py                    # 处理 new_papers/*.csv
  python ingest.py --rebuild-only     # 仅根据现有 master 重算分类与导出
  SKIP_LLM=1 python ingest.py         # 不调用百炼，仅规则分类

环境变量:
  DASHSCOPE_API_KEY  阿里云百炼 API Key（与 BAILIAN_API_KEY 二选一）
  SKIP_LLM=1         跳过 LLM
  DASHSCOPE_MODEL    默认 qwen-plus
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import ARCHIVE_DIR, MASTER_JSON, NEW_PAPERS_DIR
from scripts.bailian_client import enrich_with_llm, is_llm_enabled
from scripts.build_outputs import load_master, rebuild_all, save_master
from scripts.taxonomy import enrich_paper_record
from scripts.zotero_parser import dedupe_key, parse_zotero_csv


def _existing_keys(papers: list[dict]) -> set[str]:
    return {dedupe_key(p) for p in papers}


def _next_id(papers: list[dict]) -> int:
    if not papers:
        return 1
    return max(int(p["id"]) for p in papers) + 1


def ingest_new_csvs(papers: list[dict]) -> tuple[list[dict], list[str]]:
    NEW_PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    keys = _existing_keys(papers)
    logs: list[str] = []
    next_id = _next_id(papers)

    csv_files = sorted(NEW_PAPERS_DIR.glob("*.csv"))
    if not csv_files:
        logs.append("new_papers/ 下没有待处理的 CSV，跳过入库。")
        return papers, logs

    for csv_path in csv_files:
        rows = parse_zotero_csv(csv_path)
        added = 0
        skipped = 0
        for row in rows:
            key = dedupe_key(row)
            if key in keys:
                skipped += 1
                continue
            row["id"] = next_id
            next_id += 1

            try:
                enrich_with_llm(row)
            except Exception as e:
                logs.append(f"  [WARN] LLM 失败 id={row['id']}: {e}")
                row.setdefault("summary_zh", (row.get("abstract") or "")[:300])
                row.setdefault("keywords", [])

            enrich_paper_record(row, classification_source="auto")
            papers.append(row)
            keys.add(key)
            added += 1

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = ARCHIVE_DIR / f"{csv_path.stem}_{stamp}.csv"
        shutil.move(str(csv_path), str(dest))
        logs.append(f"已处理 {csv_path.name}: 新增 {added} 篇, 跳过重复 {skipped} 篇 → 归档 {dest.name}")

    return papers, logs


def main() -> int:
    parser = argparse.ArgumentParser(description="机器人柔性磨削知识库 — 增量入库")
    parser.add_argument("--rebuild-only", action="store_true", help="不读 new_papers，仅重算导出")
    parser.add_argument(
        "--reclassify-all",
        action="store_true",
        help="强制按关键词重新分类（会覆盖已有 hierarchy，慎用）",
    )
    args = parser.parse_args()

    if not MASTER_JSON.exists():
        print(f"错误: 找不到 {MASTER_JSON}")
        print("请先将 papers_enriched_updated.json 放在仓库根目录。")
        return 1

    papers = load_master()
    print(f"当前库内论文: {len(papers)} 篇")
    print(f"百炼 LLM: {'开启' if is_llm_enabled() else '关闭（无 Key 或 SKIP_LLM=1）'}")

    logs: list[str] = []
    if not args.rebuild_only:
        papers, logs = ingest_new_csvs(papers)
        save_master(papers)
        for line in logs:
            print(line)

    if args.reclassify_all:
        from scripts.taxonomy import enrich_paper_record

        for p in papers:
            enrich_paper_record(p, classification_source="auto", force_reclassify=True)
        save_master(papers)

    n, _ = rebuild_all(papers, save_master_file=not args.rebuild_only)
    print(f"完成。共 {n} 篇 → papers_classified.json / mindmap_stats.json 已更新。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

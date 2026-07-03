# -*- coding: utf-8 -*-
"""精简 mindmaps_five.json：去除 categories 内嵌的论文详情（已在 papers_index.json 中）。
   将原 1.3MB 文件减至 ~30KB，配合 papers_index.json 使用。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def slim(input_path: Path, output_path: Path) -> tuple[int, int]:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    original_size = input_path.stat().st_size

    for dim in data.get("dimensions", []):
        for cat in dim.get("categories", []):
            # 移除冗余的 papers 详情数组，仅保留 paper_ids
            if "papers" in cat:
                del cat["papers"]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    new_size = output_path.stat().st_size
    return original_size, new_size


def main() -> int:
    src = ROOT / "mindmaps_five.json"
    dst = ROOT / "web" / "mindmaps_five.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    orig, slimmed = slim(src, dst)
    print(f"原始: {orig / 1024:.0f} KB  →  精简: {slimmed / 1024:.0f} KB  (减少 {(1 - slimmed / orig) * 100:.0f}%)")
    print(f"输出: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""若本地缺少主数据，从 GitHub raw 下载。"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import CLASSIFIED_JSON, MASTER_JSON

RAW_BASE = "https://raw.githubusercontent.com/xuyai9299-star/robot-grinding-knowledge/main"


def download(url: str, dest: Path) -> None:
    print(f"下载 {url} -> {dest}")
    with urllib.request.urlopen(url, timeout=120) as resp:
        dest.write_bytes(resp.read())


def main() -> int:
    MASTER_JSON.parent.mkdir(parents=True, exist_ok=True)
    if not MASTER_JSON.exists():
        download(f"{RAW_BASE}/papers_enriched_updated.json", MASTER_JSON)
    else:
        print(f"已存在: {MASTER_JSON}")
    if not CLASSIFIED_JSON.exists():
        download(f"{RAW_BASE}/papers_classified.json", CLASSIFIED_JSON)
    else:
        print(f"已存在: {CLASSIFIED_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

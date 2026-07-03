# -*- coding: utf-8 -*-
"""一键重建全部数据：知识库 + 会议 + 复制到 web/"""
import subprocess, sys, shutil, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WEB = ROOT / "web"

STEPS = [
    ("重建知识库 JSON", [sys.executable, str(ROOT / "ingest.py"), "--rebuild-only"]),
    ("重建会议/时间轴", [sys.executable, str(SCRIPTS / "build_conferences.py")]),
]

SYNC_FILES = [
    "papers_index.json", "papers_classified.json", "mindmap_stats.json",
    "mindmaps_five.json", "outline.html", "机器人柔性磨削知识库_五维.mm",
    "index.html", "radial.html", "radial.js", "galaxy.html", "galaxy.js",
    "mindmaps.html", "mindmaps.js", "d3_mindmap.html", "timeline.html",
    "vis-network.min.js", "echarts.min.js", "three.min.js", "d3.min.js", "styles.css",
]

SYNC_DIRS = ["conferences"]


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, env={**__import__("os").environ, "SKIP_LLM": "1"})


def main():
    t0 = time.time()
    print("=" * 60)
    print("  机器人磨削知识库 — 一键重建")
    print(f"  论文来源: papers_enriched_updated.json")
    print("=" * 60)

    # Step 1-2: 重建数据
    for i, (name, cmd) in enumerate(STEPS, 1):
        print(f"\n[{i}/{len(STEPS)+1}] {name}...")
        result = run(cmd)
        if result.returncode != 0:
            print(f"  FAIL: {result.stderr[-200:]}")
            return 1
        out = result.stdout.strip().split("\n")
        for line in out[-3:]:
            print(f"  {line.strip()}")
        print("  [OK]")

    # Step 3: 复制到 web/
    print(f"\n[{len(STEPS)+1}/{len(STEPS)+1}] 同步文件到 web/...")
    copied = 0
    for f in SYNC_FILES:
        src = ROOT / f
        dst = WEB / f
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
    for d in SYNC_DIRS:
        src = ROOT / d
        dst = WEB / d
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied += 1
    print(f"  [OK] Synced {copied} files/dirs")

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  ALL DONE in {elapsed:.1f}s")
    print(f"  启动预览: py -3 -m http.server 8080")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    sys.exit(main())

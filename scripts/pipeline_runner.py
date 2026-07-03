# -*- coding: utf-8 -*-
"""
全自动知识库更新管线引擎。
每一步通过 yield 事件字典报告进度，供 SSE 推送到前端。

步骤：
  1. OpenAlex 爬取 → 2. LLM 相关性判断/摘要/关键词 →
  3. 去重合并 → 4. 五维自动分类 → 5. 重建前端数据文件 → 6. 同步到 web/

用法：
  runner = PipelineRunner(api_key="...")
  for event in runner.run():
      print(event)  # 或通过 SSE 发送
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import MASTER_JSON, PAPERS_INDEX_JSON, MINDMAP_STATS_JSON
from scripts.taxonomy import enrich_paper_record

# ── OpenAlex 搜索词 ──────────────────────────────────
SEARCH_QUERIES = [
    "robotic belt grinding",
    "robot abrasive belt grinding",
    "robotic grinding force control",
    "belt grinding surface integrity",
    "robotic polishing blade",
    "robot-assisted grinding",
    "abrasive belt grinding aero-engine",
    "robotic grinding trajectory planning",
    "belt grinding material removal",
    "flexible grinding robot",
    "robotic grinding surface roughness",
    "robot belt polishing",
    "grinding robot path planning",
    "robotic grinding nickel alloy",
    "belt grinding residual stress",
    "robotic compliant grinding",
    "abrasive belt grinding monitoring",
    "robot grinding turbine blade",
    "belt grinding optimization",
    "robotic grinding calibration",
]

HEADERS = {"User-Agent": "RobotGrindingKB/2.0 (mailto:research@example.com)"}


class PipelineRunner:
    """全自动知识库更新管线（生成器模式）。"""

    def __init__(self, api_key: str | None = None, max_crawl_per_query: int = 30):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
        self.max_crawl = max_crawl_per_query
        self._new_papers: list[dict] = []
        self._rejected: list[dict] = []
        self._total_existing = 0

    # ── helpers ──────────────────────────────────────
    def _emit(self, step: str, status: str, **kw) -> dict:
        return {"step": step, "status": status, "ts": time.time(), **kw}

    def _api_get(self, url: str) -> dict | None:
        time.sleep(0.3)
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5)
                return self._api_get(url)
            return None
        except Exception:
            return None

    # ── Step 1: OpenAlex 爬取 ─────────────────────────
    def _crawl_openalex(self) -> Iterator[dict]:
        yield self._emit("crawl", "start", message="开始爬取 OpenAlex…", queries=len(SEARCH_QUERIES))
        all_raw: list[dict] = []

        for qi, query in enumerate(SEARCH_QUERIES):
            yield self._emit("crawl", "progress",
                             message=f"搜索 ({qi+1}/{len(SEARCH_QUERIES)}): {query}",
                             current_query=query, query_index=qi + 1, total_queries=len(SEARCH_QUERIES))
            page = 1
            collected = 0
            while collected < self.max_crawl:
                params = urllib.parse.urlencode({
                    "search": query, "per_page": 25, "page": page,
                    "filter": "type:article",
                })
                data = self._api_get(f"https://api.openalex.org/works?{params}")
                if not data:
                    break
                results = data.get("results") or []
                if not results:
                    break
                for item in results:
                    doi = (item.get("doi") or "").replace("https://doi.org/", "")
                    title = item.get("title", "")
                    if not title:
                        continue
                    year = item.get("publication_year")
                    venue = (item.get("primary_location") or {}).get("source") or {}
                    authors_raw = item.get("authorships") or []
                    authors = "; ".join(
                        (a.get("author") or {}).get("display_name", "")
                        for a in authors_raw[:8]
                    )
                    abstract = ""
                    ab = item.get("abstract_inverted_index")
                    if ab and isinstance(ab, dict):
                        max_idx = max(max(v) for v in ab.values()) if ab else 0
                        words = [""] * (max_idx + 1)
                        for word, positions in ab.items():
                            for pos in positions:
                                if pos < len(words):
                                    words[pos] = word
                        abstract = " ".join(words)
                    all_raw.append({
                        "title": title,
                        "year": str(year) if year else "",
                        "authors": authors,
                        "doi": doi,
                        "url": f"https://doi.org/{doi}" if doi else "",
                        "venue": venue.get("display_name", "") if venue else "",
                        "abstract": abstract[:500] if abstract else "",
                        "openalex_id": item.get("id", ""),
                        "cited_by_count": item.get("cited_by_count", 0),
                        "type": item.get("type", "article"),
                    })
                    collected += 1
                page += 1
            yield self._emit("crawl", "progress",
                             message=f"  ├ 获取 {collected} 篇 · 累计 {len(all_raw)} 篇",
                             current_query=query, collected=collected, total_collected=len(all_raw))

        # 去重
        yield self._emit("crawl", "progress", message=f"去重前: {len(all_raw)} 篇 → 去重中…")
        seen_doi, seen_title = set(), set()
        unique = []
        for p in all_raw:
            d = (p.get("doi") or "").lower().strip()
            t = (p.get("title") or "").lower().strip()[:80]
            if d and d in seen_doi:
                continue
            if t in seen_title:
                continue
            if d:
                seen_doi.add(d)
            seen_title.add(t)
            unique.append(p)
        self._raw_crawled = unique
        yield self._emit("crawl", "done",
                         message=f"爬取完成 · 去重后 {len(unique)} 篇新论文",
                         total_crawled=len(unique),
                         papers=[{"title": p["title"][:80], "year": p["year"], "doi": p["doi"]}
                                 for p in unique[:20]])

    # ── Step 2: LLM 相关性判断 + 摘要/关键词 ──────────
    def _llm_process(self) -> Iterator[dict]:
        papers = self._raw_crawled
        if not papers:
            yield self._emit("llm", "skip", message="无新论文，跳过 LLM 处理")
            return

        has_llm = bool(self.api_key) and os.getenv("SKIP_LLM", "").lower() not in ("1", "true", "yes")
        yield self._emit("llm", "start",
                         message=f"LLM 处理 {len(papers)} 篇论文…",
                         llm_enabled=has_llm, total=len(papers))

        for i, paper in enumerate(papers):
            if has_llm:
                try:
                    result = self._call_llm(paper)
                except Exception as e:
                    yield self._emit("llm", "progress",
                                     message=f"  ⚠ #{i+1} LLM 调用失败: {e}，使用规则兜底",
                                     index=i + 1, total=len(papers),
                                     title=paper["title"][:60], error=str(e))
                    result = self._llm_fallback(paper)
            else:
                result = self._llm_fallback(paper)

            paper["summary_zh"] = result.get("summary_zh", "")
            paper["keywords"] = result.get("keywords", [])
            paper["relevance"] = result.get("relevance", 3)

            status_icon = "✅" if paper["relevance"] >= 3 else "❌"
            yield self._emit("llm", "progress",
                             message=f"  {status_icon} #{i+1}/{len(papers)}: {paper['title'][:60]}",
                             index=i + 1, total=len(papers),
                             title=paper["title"][:80],
                             relevance=paper["relevance"],
                             summary=paper["summary_zh"][:100],
                             keywords=paper["keywords"],
                             accepted=paper["relevance"] >= 3)

        accepted = [p for p in papers if p.get("relevance", 3) >= 3]
        rejected = [p for p in papers if p.get("relevance", 3) < 3]
        self._accepted = accepted
        self._rejected = rejected
        yield self._emit("llm", "done",
                         message=f"LLM 处理完成 · 通过 {len(accepted)} 篇 · 拒绝 {len(rejected)} 篇",
                         accepted_count=len(accepted), rejected_count=len(rejected),
                         accepted=[{"title": p["title"][:80], "relevance": p["relevance"]}
                                   for p in accepted[:20]],
                         rejected_preview=[{"title": p["title"][:80], "relevance": p["relevance"]}
                                           for p in rejected[:10]])

    def _call_llm(self, paper: dict) -> dict:
        """调用百炼千问：一次性返回相关性+摘要+关键词。"""
        from dashscope import Generation

        title = paper.get("title", "")
        abstract = paper.get("abstract", "")[:3000]
        prompt = f"""你是机器人磨削领域的专家文献助手。评估以下论文是否与机器人磨削/抛光相关。

论文标题: {title}
论文摘要: {abstract or "(无摘要)"}

请输出 JSON（不要 markdown 代码块）：
{{
  "relevance": 1-5的整数（5=高度相关，1=完全无关。与机器人磨削/抛光、砂带磨削、磨削力控制、表面质量等相关的论文给高分；纯医学手术、纯地质钻探等不相关的给低分）,
  "summary_zh": "150字以内中文摘要（仅当relevance>=3时认真写，否则写'不相关'）",
  "keywords": ["5个以内中文关键词"]
}}"""
        response = Generation.call(
            api_key=self.api_key,
            model=os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
            messages=[
                {"role": "system", "content": "只输出合法 JSON 对象，不要 markdown 代码块。"},
                {"role": "user", "content": prompt},
            ],
            result_format="message",
        )
        status = getattr(response, "status_code", 200)
        if status != 200:
            raise RuntimeError(f"API {status}: {getattr(response, 'message', '')}")
        text = response.output.choices[0].message.content
        data = self._parse_json(text)
        return {
            "relevance": int(data.get("relevance", 3)),
            "summary_zh": data.get("summary_zh", ""),
            "keywords": self._normalize_keywords(data.get("keywords", [])),
        }

    def _llm_fallback(self, paper: dict) -> dict:
        """无 LLM 时的规则兜底：用英文摘要作中文摘要占位，关键词为空。"""
        abstract = paper.get("abstract", "")[:300]
        return {
            "relevance": 3,  # 默认通过
            "summary_zh": abstract or f"（待补充摘要）{paper.get('title','')[:100]}",
            "keywords": [],
        }

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return {}
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _normalize_keywords(kws) -> list[str]:
        if isinstance(kws, str):
            kws = [k.strip() for k in re.split(r"[,，、]", kws) if k.strip()]
        return (kws or [])[:6]

    # ── Step 3: 去重合并 ─────────────────────────────
    def _merge(self) -> Iterator[dict]:
        accepted = self._accepted
        if not accepted:
            yield self._emit("merge", "skip", message="无通过筛选的论文，跳过合并")
            return

        yield self._emit("merge", "start", message=f"合并 {len(accepted)} 篇论文到知识库…")

        # 加载现有
        with open(MASTER_JSON, "r", encoding="utf-8") as f:
            existing = json.load(f)
        self._total_existing = len(existing)
        yield self._emit("merge", "progress",
                         message=f"现有知识库: {len(existing)} 篇论文",
                         existing_count=len(existing))

        # 去重 key
        existing_dois = set()
        existing_titles = set()
        for p in existing:
            d = (p.get("doi") or "").lower().strip()
            t = (p.get("title") or p.get("title_en") or "").lower().strip()[:80]
            if d:
                existing_dois.add(d)
            if t:
                existing_titles.add(t)

        max_id = max((int(p.get("id", 0)) for p in existing), default=0)
        new_papers = []
        skipped_dup = 0
        for p in accepted:
            d = (p.get("doi") or "").lower().strip()
            t = (p.get("title") or "").lower().strip()[:80]
            if d and d in existing_dois:
                skipped_dup += 1
                continue
            if t in existing_titles:
                skipped_dup += 1
                continue
            max_id += 1
            new_papers.append({
                "id": max_id,
                "title": p["title"],
                "title_en": p["title"],
                "year": p.get("year", ""),
                "authors": p.get("authors", ""),
                "doi": p.get("doi", ""),
                "url": p.get("url", ""),
                "venue": p.get("venue", ""),
                "abstract": p.get("abstract", ""),
                "school": "",
                "keywords": p.get("keywords", []),
                "keywords_zh": p.get("keywords", []),
                "summary_zh": p.get("summary_zh", ""),
                "hierarchy_tags": [],
                "mindmap_path": "",
            })

        self._new_papers = new_papers
        yield self._emit("merge", "done",
                         message=f"合并完成 · 新增 {len(new_papers)} 篇 · 跳过重复 {skipped_dup} 篇",
                         new_count=len(new_papers), skipped_duplicates=skipped_dup,
                         new_papers=[{"id": p["id"], "title": p["title"][:80], "year": p["year"]}
                                     for p in new_papers[:30]])

    # ── Step 4: 自动分类 ──────────────────────────────
    def _classify(self) -> Iterator[dict]:
        if not self._new_papers:
            yield self._emit("classify", "skip", message="无新论文，跳过分类")
            return

        yield self._emit("classify", "start",
                         message=f"五维自动分类 {len(self._new_papers)} 篇论文…",
                         total=len(self._new_papers))

        for i, paper in enumerate(self._new_papers):
            enrich_paper_record(paper, classification_source="auto")
            tags = paper.get("hierarchy_tags", [])
            path = paper.get("mindmap_path", "")
            yield self._emit("classify", "progress",
                             message=f"  📂 #{paper['id']}: {paper['title'][:50]} → {path or '未分类'}",
                             index=i + 1, total=len(self._new_papers),
                             paper_id=paper["id"],
                             title=paper["title"][:60],
                             tags=tags, path=path)

        yield self._emit("classify", "done",
                         message=f"分类完成 · {len(self._new_papers)} 篇已标注五维标签",
                         classified_count=len(self._new_papers))

    # ── Step 5: 重建前端数据 ──────────────────────────
    def _rebuild(self) -> Iterator[dict]:
        yield self._emit("rebuild", "start", message="重建前端数据文件…")

        # 加载完整 papers
        with open(MASTER_JSON, "r", encoding="utf-8") as f:
            existing = json.load(f)

        # 追加新论文
        all_papers = existing + self._new_papers

        # 保存 master
        with open(MASTER_JSON, "w", encoding="utf-8") as f:
            json.dump(all_papers, f, ensure_ascii=False, indent=2)
        yield self._emit("rebuild", "progress",
                         message=f"  ✅ 保存 {MASTER_JSON.name} ({len(all_papers)} 篇)")

        # 保存新增列表
        newly_path = ROOT / "newly_crawled.json"
        with open(newly_path, "w", encoding="utf-8") as f:
            json.dump(self._new_papers, f, ensure_ascii=False, indent=2)
        yield self._emit("rebuild", "progress",
                         message=f"  ✅ 保存 newly_crawled.json ({len(self._new_papers)} 篇)")

        # 运行 build_outputs
        from scripts.build_outputs import rebuild_all
        rebuild_all(all_papers, save_master_file=False)
        yield self._emit("rebuild", "progress",
                         message="  ✅ 重建 papers_index.json / classified.json / mindmap_stats.json / mindmaps_five.json / outline.html / .mm")

        # 同步到 web/
        import shutil
        SYNC_FILES = [
            "papers_index.json", "papers_classified.json", "mindmap_stats.json",
            "mindmaps_five.json", "outline.html", "机器人柔性磨削知识库_五维.mm",
        ]
        web_dir = ROOT / "web"
        copied = 0
        for fname in SYNC_FILES:
            src = ROOT / fname
            dst = web_dir / fname
            if src.exists():
                shutil.copy2(src, dst)
                copied += 1
        yield self._emit("rebuild", "progress",
                         message=f"  ✅ 同步 {copied} 个文件到 web/")

        yield self._emit("rebuild", "done",
                         message=f"重建完成 · 知识库总计 {len(all_papers)} 篇论文",
                         total_papers=len(all_papers),
                         new_papers_count=len(self._new_papers))

    # ── 主流程 ────────────────────────────────────────
    def run(self) -> Iterator[dict]:
        """主管线（生成器），每一步 yield 进度事件。"""
        t0 = time.time()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        yield self._emit("init", "start",
                         message=f"🚀 知识库自动更新管线启动 · {timestamp}",
                         timestamp=timestamp)

        # Step 1: 爬取
        yield from self._crawl_openalex()

        # Step 2: LLM 处理（相关性判断 + 摘要 + 关键词）
        yield from self._llm_process()

        # Step 3: 去重合并
        yield from self._merge()

        # Step 4: 自动分类
        yield from self._classify()

        # Step 5: 重建前端数据
        yield from self._rebuild()

        elapsed = time.time() - t0
        total = self._total_existing + len(self._new_papers)
        yield self._emit("done", "complete",
                         message=f"🎉 全部完成！新增 {len(self._new_papers)} 篇（拒绝 {len(self._rejected)} 篇无关论文），知识库总计 {total} 篇 · 耗时 {elapsed:.1f}s",
                         new_papers=len(self._new_papers),
                         rejected=len(self._rejected),
                         total_papers=total,
                         elapsed_seconds=round(elapsed, 1),
                         new_titles=[p["title"][:80] for p in self._new_papers[:20]],
                         rejected_titles=[p["title"][:80] for p in self._rejected[:10]])


# ── CLI 入口 ────────────────────────────────────────
if __name__ == "__main__":
    runner = PipelineRunner()
    for event in runner.run():
        icon = {"start": "⏳", "progress": "  ", "done": "✅", "complete": "🎉", "skip": "⏭️"}.get(event["status"], "")
        print(f"{icon} [{event['step']}] {event.get('message', '')}")

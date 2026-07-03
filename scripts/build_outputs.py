# -*- coding: utf-8 -*-
"""从 master JSON 生成前端所需的分类、索引与导图统计。"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (
    CATEGORY_INDEX_JSON,
    CLASSIFIED_JSON,
    FREEMIND_MM,
    KB_ROOT_TITLE,
    MASTER_JSON,
    MINDMAPS_FIVE_JSON,
    MINDMAP_STATS_JSON,
    OUTLINE_HTML,
    PAPERS_INDEX_JSON,
    TAXONOMY_VERSION,
)
from scripts.taxonomy import enrich_paper_record


def load_master(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or MASTER_JSON
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_master(papers: list[dict[str, Any]], path: Path | None = None) -> None:
    path = path or MASTER_JSON
    with path.open("w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)


def build_papers_index(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """按 ID 索引，供网页点击后展示详情与外链。"""
    by_id: dict[str, dict[str, Any]] = {}
    for p in papers:
        kws = p.get("keywords_flat") or p.get("keywords") or []
        by_id[str(p["id"])] = {
            "id": p["id"],
            "title": p.get("title", ""),
            "school": p.get("school", ""),
            "authors": p.get("authors", ""),
            "year": p.get("year", ""),
            "venue": p.get("venue", ""),
            "doi": p.get("doi", ""),
            "url": p.get("url", ""),
            "summary_zh": p.get("summary_zh", ""),
            "keywords": kws,
            "mindmap_path": p.get("mindmap_path", ""),
            "hierarchy_tags": p.get("hierarchy_tags", []),
            "hierarchy": p.get("hierarchy", {}),
            "classification_source": p.get("classification_source", ""),
        }
    return {"total": len(papers), "by_id": by_id}


def build_category_index(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """分类 → 论文 ID 列表（支持多标签）。"""
    by_path: dict[str, list[int]] = defaultdict(list)
    by_domain: dict[str, list[int]] = defaultdict(list)
    by_method: dict[str, list[int]] = defaultdict(list)
    by_topic: dict[str, list[int]] = defaultdict(list)
    by_application: dict[str, list[int]] = defaultdict(list)
    by_material: dict[str, list[int]] = defaultdict(list)

    for p in papers:
        pid = int(p["id"])
        h = p.get("hierarchy") or {}
        path = p.get("mindmap_path") or ""
        if path:
            by_path[path].append(pid)
        for x in h.get("process_domain") or []:
            if pid not in by_domain[x]:
                by_domain[x].append(pid)
        for x in h.get("process_method") or []:
            if pid not in by_method[x]:
                by_method[x].append(pid)
        for x in h.get("research_topic") or []:
            if pid not in by_topic[x]:
                by_topic[x].append(pid)
        for x in h.get("application") or []:
            if pid not in by_application[x]:
                by_application[x].append(pid)
        for x in h.get("material") or []:
            if pid not in by_material[x]:
                by_material[x].append(pid)

    def _sort(d: dict[str, list[int]]) -> dict[str, list[int]]:
        return {k: sorted(v) for k, v in sorted(d.items())}

    return {
        "by_mindmap_path": _sort(by_path),
        "by_process_domain": _sort(by_domain),
        "by_process_method": _sort(by_method),
        "by_research_topic": _sort(by_topic),
        "by_application": _sort(by_application),
        "by_material": _sort(by_material),
    }


def _aggregate_ids(children: list[dict]) -> list[int]:
    ids: list[int] = []
    for c in children:
        if c.get("paper_ids"):
            for i in c["paper_ids"]:
                if i not in ids:
                    ids.append(i)
        if c.get("children"):
            for i in _aggregate_ids(c["children"]):
                if i not in ids:
                    ids.append(i)
    return sorted(ids)


def build_mindmap_stats(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """工艺树：论文可挂在多个 L3（多研究主题）。"""
    tree: dict[str, dict[str, dict[str, list[int]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for p in papers:
        pid = int(p["id"])
        h = p.get("hierarchy") or {}
        l1_list = h.get("process_domain") or ["跨领域研究"]
        l2_list = h.get("process_method") or [""]
        l3_list = h.get("research_topic") or ["综合研究"]

        if not h.get("process_method"):
            l2_list = ["通用工艺"]

        for l1 in l1_list:
            for l2 in l2_list:
                l2 = l2 or "通用工艺"
                for l3 in l3_list:
                    if pid not in tree[l1][l2][l3]:
                        tree[l1][l2][l3].append(pid)

    nodes = []
    for l1, l2_map in sorted(tree.items()):
        l1_children = []
        for l2, l3_map in sorted(l2_map.items()):
            l2_children = []
            for l3, ids in sorted(l3_map.items()):
                l2_children.append(
                    {
                        "name": l3,
                        "count": len(ids),
                        "paper_ids": sorted(ids),
                        "path": f"{l1} > {l2} > {l3}",
                    }
                )
            l2_node = {
                "name": l2,
                "count": sum(c["count"] for c in l2_children),
                "children": l2_children,
                "paper_ids": _aggregate_ids(l2_children),
            }
            l1_children.append(l2_node)
        l1_node = {
            "name": l1,
            "count": sum(c["count"] for c in l1_children),
            "children": l1_children,
            "paper_ids": _aggregate_ids(l1_children),
        }
        nodes.append(l1_node)

    app_map: dict[str, list[int]] = defaultdict(list)
    mat_map: dict[str, list[int]] = defaultdict(list)
    for p in papers:
        pid = int(p["id"])
        h = p.get("hierarchy") or {}
        for a in h.get("application") or []:
            if pid not in app_map[a]:
                app_map[a].append(pid)
        for m in h.get("material") or []:
            if pid not in mat_map[m]:
                mat_map[m].append(pid)

    return {
        "root": f"{KB_ROOT_TITLE} ({len(papers)}篇)",
        "total_papers": len(papers),
        "process_tree": nodes,
        "application": [
            {"name": k, "count": len(v), "paper_ids": sorted(v)}
            for k, v in sorted(app_map.items(), key=lambda x: -len(x[1]))
        ],
        "material": [
            {"name": k, "count": len(v), "paper_ids": sorted(v)}
            for k, v in sorted(mat_map.items(), key=lambda x: -len(x[1]))
        ],
    }


DIMENSIONS: list[tuple[str, str]] = [
    ("process_domain", "L1 工艺领域"),
    ("process_method", "L2 工艺方式"),
    ("research_topic", "L3 研究主题"),
    ("application", "L4 应用场景"),
    ("material", "L5 加工材料"),
]


def _paper_link(p: dict[str, Any]) -> str:
    url = (p.get("url") or "").strip()
    if url:
        return url
    doi = (p.get("doi") or "").strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    if doi:
        return f"https://doi.org/{doi}"
    return ""


def build_mindmaps_five(papers: list[dict[str, Any]], stats: dict[str, Any]) -> dict[str, Any]:
    """五维思维导图数据：每维下分类 → 论文列表（含链接与关键词）。"""
    from scripts.taxonomy import TAXONOMY

    def _match_text(text, terms):
        """检查文本是否匹配分类词"""
        t = text.lower()
        for term in terms:
            if term.lower() in t:
                return True
        return False

    def _fallback_hierarchy(paper):
        """对没有 hierarchy 的论文，从标题+摘要+venue 提取分类"""
        text = " ".join([
            paper.get("title_en", ""), paper.get("title", ""),
            paper.get("abstract", ""), paper.get("summary_zh", ""),
            paper.get("venue", ""),
        ])
        result = {}
        for level, cats in TAXONOMY.items():
            matched = []
            for cat, terms in cats.items():
                if _match_text(text, terms):
                    matched.append(cat)
            result[level] = matched
        return result

    by_id = {int(p["id"]): p for p in papers}
    dimensions = []

    # 预分类：补全没有 hierarchy 的论文
    for p in papers:
        h = p.get("hierarchy") or {}
        if not h or all(not v for v in h.values()):
            p["hierarchy"] = _fallback_hierarchy(p)

    for key, label in DIMENSIONS:
        cat_map: dict[str, list[int]] = defaultdict(list)
        for p in papers:
            pid = int(p["id"])
            tags = (p.get("hierarchy") or {}).get(key) or []
            if not tags:
                if pid not in cat_map["其他"]:
                    cat_map["其他"].append(pid)
            else:
                for t in tags:
                    if pid not in cat_map[t]:
                        cat_map[t].append(pid)

        categories = []
        for name, ids in sorted(cat_map.items(), key=lambda x: (-len(x[1]), x[0])):
            sorted_ids = sorted(ids)
            # 不再内嵌 papers 详情（已在 papers_index.json 中），节省 ~97% 体积
            categories.append(
                {
                    "name": name,
                    "count": len(sorted_ids),
                    "paper_ids": sorted_ids,
                }
            )
        dimensions.append({"id": key, "label": label, "categories": categories})

    return {
        "title": KB_ROOT_TITLE,
        "total_papers": len(papers),
        "dimensions": dimensions,
        "process_tree": stats.get("process_tree", []),
    }


def export_freemind_mm(papers: list[dict[str, Any]], stats: dict[str, Any], path: Path) -> None:
    """导出 FreeMind .mm：论文节点带 LINK 超链接，关键词为子节点。"""
    import xml.etree.ElementTree as ET

    by_id = {int(p["id"]): p for p in papers}
    map_el = ET.Element("map", version="1.0.1")
    root = ET.SubElement(map_el, "node", TEXT=f"{KB_ROOT_TITLE} ({len(papers)}篇)")

    for key, label in DIMENSIONS:
        branch = ET.SubElement(root, "node", TEXT=label)
        cat_map: dict[str, list[int]] = defaultdict(list)
        for p in papers:
            pid = int(p["id"])
            for t in (p.get("hierarchy") or {}).get(key) or ["其他"]:
                if pid not in cat_map[t]:
                    cat_map[t].append(pid)
        for cat_name, ids in sorted(cat_map.items(), key=lambda x: (-len(x[1]), x[0])):
            cat_node = ET.SubElement(branch, "node", TEXT=f"{cat_name} ({len(ids)})")
            for pid in sorted(ids):
                p = by_id.get(pid)
                if not p:
                    continue
                link = _paper_link(p)
                short = (p.get("title") or "")[:70]
                attrs: dict[str, str] = {"TEXT": f"#{pid} {short}"}
                if link:
                    attrs["LINK"] = link
                paper_node = ET.SubElement(cat_node, "node", **attrs)
                kws = "、".join((p.get("keywords_flat") or p.get("keywords") or [])[:8])
                if kws:
                    ET.SubElement(paper_node, "node", TEXT=f"关键词: {kws}")
                if p.get("summary_zh"):
                    ET.SubElement(
                        paper_node,
                        "node",
                        TEXT=f"摘要: {(p.get('summary_zh') or '')[:120]}…",
                    )

    proc_branch = ET.SubElement(root, "node", TEXT="工艺层级 L1→L2→L3")
    for l1 in stats.get("process_tree") or []:
        n1 = ET.SubElement(proc_branch, "node", TEXT=f"{l1['name']} ({l1['count']})")
        for l2 in l1.get("children") or []:
            n2 = ET.SubElement(n1, "node", TEXT=f"{l2['name']} ({l2['count']})")
            for l3 in l2.get("children") or []:
                n3 = ET.SubElement(n2, "node", TEXT=f"{l3['name']} ({l3['count']})")
                for pid in l3.get("paper_ids") or []:
                    p = by_id.get(pid)
                    if not p:
                        continue
                    link = _paper_link(p)
                    attrs = {"TEXT": f"#{pid} {(p.get('title') or '')[:50]}"}
                    if link:
                        attrs["LINK"] = link
                    pn = ET.SubElement(n3, "node", **attrs)
                    kws = "、".join((p.get("keywords_flat") or p.get("keywords") or [])[:6])
                    if kws:
                        ET.SubElement(pn, "node", TEXT=f"关键词: {kws}")

    tree = ET.ElementTree(map_el)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def export_outline_html(mindmaps_five: dict[str, Any], papers: list[dict[str, Any]], path: Path) -> None:
    """生成纯 HTML 大纲页：分类下每篇论文为超链接（不依赖 JS 导图库）。"""
    by_id: dict[int, dict[str, Any]] = {int(p["id"]): p for p in papers}

    def _esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace('"', "&quot;")
        )

    parts = [
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>",
        f"<title>{mindmaps_five['title']} — 五维大纲</title>",
        "<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'/>",
        "<style>body{background:#f8fafc}.cat{margin:1rem 0}.paper{margin:.35rem 0 .35rem 1rem;font-size:.9rem}"
        ".kw{color:#64748b;font-size:.8rem}</style></head><body>",
        "<div class='container py-4'>",
        f"<h1>{mindmaps_five['title']}</h1>",
        "<p class='text-muted'>五维分类 · 每篇论文为可点击原文链接 · "
        "<a href='index.html'>返回检索页</a> · <a href='mindmaps.html'>交互导图</a></p>",
    ]

    for dim in mindmaps_five["dimensions"]:
        parts.append(f"<section class='mb-4'><h2 class='h4 border-bottom pb-2'>{dim['label']}</h2>")
        for cat in dim["categories"]:
            parts.append(f"<div class='cat'><h3 class='h6'>{cat['name']} <span class='badge text-bg-secondary'>{cat['count']}</span></h3><ul class='list-unstyled'>")
            for pid in cat.get("paper_ids") or []:
                pap = by_id.get(int(pid))
                if not pap:
                    parts.append(f"<li class='paper'>#{pid}</li>")
                    continue
                link = pap.get("url") or ""
                title = _esc(pap.get("title_en") or pap.get("title") or "")
                kws = _esc("、".join(pap.get("keywords_zh") or pap.get("keywords") or []))
                if link:
                    parts.append(
                        f"<li class='paper'><a href='{_esc(link)}' target='_blank' rel='noopener'>"
                        f"#{pid} {title[:100]}</a>"
                        f"<span class='text-muted'> ({_esc(pap.get('school',''))} {pap.get('year','')})</span>"
                    )
                else:
                    parts.append(
                        f"<li class='paper'>#{pid} {title[:100]} "
                        f"<span class='text-muted'>(无链接)</span>"
                    )
                if kws:
                    parts.append(f"<div class='kw'>关键词: {kws}</div>")
                parts.append("</li>")
            parts.append("</ul></div>")
        parts.append("</section>")

    parts.append("<section class='mb-4'><h2 class='h4'>工艺层级 L1→L2→L3</h2>")
    for l1 in mindmaps_five.get("process_tree") or []:
        parts.append(f"<details class='mb-2'><summary><strong>{l1['name']}</strong> ({l1['count']})</summary>")
        for l2 in l1.get("children") or []:
            parts.append(f"<details class='ms-3'><summary>{l2['name']} ({l2['count']})</summary>")
            for l3 in l2.get("children") or []:
                parts.append(f"<h4 class='h6 ms-3 mt-2'>{l3['name']} ({l3['count']})</h4><ul>")
                for pid in l3.get("paper_ids") or []:
                    pap = by_id.get(int(pid))
                    if not pap:
                        parts.append(f"<li>#{pid}</li>")
                        continue
                    link = pap.get("url") or ""
                    t = _esc(pap.get("title_en") or "")[:80]
                    if link:
                        parts.append(
                            f"<li><a href='{_esc(link)}' target='_blank' rel='noopener'>#{pid} {t}</a></li>"
                        )
                    else:
                        parts.append(f"<li>#{pid} {t}</li>")
                parts.append("</ul>")
            parts.append("</details>")
        parts.append("</details>")
    parts.append("</section></div></body></html>")

    path.write_text("\n".join(parts), encoding="utf-8")


def build_classified_payload(papers: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for p in papers:
        h = p.get("hierarchy") or {}
        items.append(
            {
                "id": p["id"],
                "title": p.get("title", ""),
                "school": p.get("school", ""),
                "authors": p.get("authors", ""),
                "mindmap_path": p.get("mindmap_path", ""),
                "hierarchy": h,
                "hierarchy_tags": p.get("hierarchy_tags", []),
                "keywords_flat": p.get("keywords_flat", p.get("keywords", [])),
                "classification_source": p.get("classification_source", "auto"),
                "summary_zh": p.get("summary_zh", ""),
                "year": p.get("year", ""),
                "venue": p.get("venue", ""),
                "doi": p.get("doi", ""),
                "url": p.get("url", ""),
            }
        )
    return {
        "root": KB_ROOT_TITLE,
        "total_papers": len(papers),
        "taxonomy_version": TAXONOMY_VERSION,
        "dimensions": {
            "process_hierarchy": "工艺领域 > 工艺方式 > 研究主题",
            "application": "应用场景（独立筛选维度）",
            "material": "加工材料（独立筛选维度）",
        },
        "papers": items,
    }


def rebuild_all(
    papers: list[dict[str, Any]] | None = None,
    *,
    save_master_file: bool = True,
) -> tuple[int, int]:
    if papers is None:
        papers = load_master()

    for p in papers:
        src = p.get("classification_source", "auto")
        enrich_paper_record(p, classification_source=src, force_reclassify=False)

    if save_master_file:
        save_master(papers)

    classified = build_classified_payload(papers)
    with CLASSIFIED_JSON.open("w", encoding="utf-8") as f:
        json.dump(classified, f, ensure_ascii=False, indent=2)

    index = build_papers_index(papers)
    with PAPERS_INDEX_JSON.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    cat_index = build_category_index(papers)
    with CATEGORY_INDEX_JSON.open("w", encoding="utf-8") as f:
        json.dump(cat_index, f, ensure_ascii=False, indent=2)

    stats = build_mindmap_stats(papers)
    with MINDMAP_STATS_JSON.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    mindmaps5 = build_mindmaps_five(papers, stats)
    with MINDMAPS_FIVE_JSON.open("w", encoding="utf-8") as f:
        json.dump(mindmaps5, f, ensure_ascii=False, indent=2)

    export_freemind_mm(papers, stats, FREEMIND_MM)
    export_outline_html(mindmaps5, papers, OUTLINE_HTML)

    return len(papers), len(classified["papers"])


if __name__ == "__main__":
    n, _ = rebuild_all()
    print(
        f"已更新: {MASTER_JSON.name}, {CLASSIFIED_JSON.name}, "
        f"{PAPERS_INDEX_JSON.name}, {CATEGORY_INDEX_JSON.name}, {MINDMAP_STATS_JSON.name}, "
        f"{MINDMAPS_FIVE_JSON.name}, {FREEMIND_MM.name}, {OUTLINE_HTML.name}（共 {n} 篇）"
    )

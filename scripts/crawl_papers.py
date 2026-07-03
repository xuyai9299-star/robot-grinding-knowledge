# -*- coding: utf-8 -*-
"""通过 OpenAlex API 爬取机器人磨削相关论文，补全知识库（免费无限制）"""
import json, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://api.openalex.org"

# 搜索查询
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

HEADERS = {"User-Agent": "RobotGrindingKB/1.0 (mailto:research@example.com)"}


def api_get(url):
    """GET 请求"""
    time.sleep(0.3)  # 温和限流，避免429
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  限流，等5秒..."); time.sleep(5)
            return api_get(url)
        print(f"  HTTP {e.code}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def search_openalex(query, max_results=200):
    """搜索 OpenAlex，返回论文列表"""
    all_papers = []
    page = 1
    while len(all_papers) < max_results:
        params = urllib.parse.urlencode({
            "search": query,
            "per_page": 50,
            "page": page,
            "filter": "type:article",
        })
        url = f"{API_BASE}/works?{params}"
        data = api_get(url)
        if not data:
            break

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            doi = (item.get("doi") or "").replace("https://doi.org/", "")
            title = item.get("title", "")
            year = item.get("publication_year")
            venue = (item.get("primary_location") or {}).get("source") or {}
            venue_name = venue.get("display_name", "") if venue else ""
            authors_raw = item.get("authorships") or []
            authors = "; ".join(
                (a.get("author") or {}).get("display_name", "")
                for a in authors_raw[:8]
            )
            # 摘要
            abstract = ""
            ab = item.get("abstract_inverted_index")
            if ab:
                # OpenAlex 的摘要格式是倒排索引，需要还原
                words = [""] * max(max(v) for v in ab.values()) if ab else 0
                for word, positions in ab.items():
                    for pos in positions:
                        if pos < len(words):
                            words[pos] = word
                abstract = " ".join(words)

            all_papers.append({
                "title": title or "",
                "year": str(year) if year else "",
                "authors": authors,
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else "",
                "venue": venue_name,
                "abstract": abstract[:500] if abstract else "",
                "openalex_id": item.get("id", ""),
                "cited_by_count": item.get("cited_by_count", 0),
                "type": item.get("type", "article"),
            })

        page += 1
        if page % 4 == 0:
            print(f"  page {page}, collected {len(all_papers)}...")

    return all_papers


def deduplicate(papers):
    """按 DOI 和标题去重"""
    seen_doi = set()
    seen_title = set()
    unique = []
    for p in papers:
        doi = (p.get("doi") or "").lower().strip()
        title = (p.get("title") or "").lower().strip()[:80]
        if not title:
            continue
        if doi and doi in seen_doi:
            continue
        if title in seen_title:
            continue
        if doi:
            seen_doi.add(doi)
        seen_title.add(title)
        unique.append(p)
    return unique


def main():
    print("=" * 50)
    print("机器人磨削论文爬取器 (OpenAlex API)")
    print("=" * 50)

    all_papers = []
    for query in SEARCH_QUERIES:
        print(f"\n搜索: '{query}'")
        papers = search_openalex(query, max_results=100)
        print(f"  获取 {len(papers)} 篇")
        all_papers.extend(papers)
        if len(all_papers) >= 800:
            print("  已达800篇上限")
            break

    # 去重
    print(f"\n=== 去重前: {len(all_papers)} 篇 ===")
    all_papers = deduplicate(all_papers)
    print(f"=== 去重后: {len(all_papers)} 篇 ===")

    # 加载现有论文
    existing_path = ROOT / "papers_enriched_updated.json"
    existing = []
    if existing_path.exists():
        with open(existing_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    print(f"现有论文: {len(existing)} 篇")

    max_id = max((p.get("id", 0) for p in existing if isinstance(p.get("id"), int)), default=0)

    # 过滤重复
    existing_dois = set()
    existing_titles = set()
    for p in existing:
        doi = (p.get("doi") or "").lower().strip()
        title = (p.get("title") or p.get("title_en") or "").lower().strip()[:80]
        if doi:
            existing_dois.add(doi)
        if title:
            existing_titles.add(title)

    new_papers = []
    for p in all_papers:
        doi = (p.get("doi") or "").lower().strip()
        title = (p.get("title") or "").lower().strip()[:80]
        if doi and doi in existing_dois:
            continue
        if title in existing_titles:
            continue
        max_id += 1
        new_papers.append({
            "id": max_id,
            "title": p["title"],
            "title_en": p["title"],
            "year": p["year"],
            "authors": p["authors"],
            "doi": p["doi"],
            "url": p["url"],
            "venue": p["venue"],
            "abstract": p["abstract"],
            "school": "",
            "keywords": [],
            "keywords_zh": [],
            "summary_zh": "",
            "hierarchy_tags": [],
            "mindmap_path": "",
        })

    print(f"新增论文: {len(new_papers)} 篇")
    print(f"合并后总计: {len(existing) + len(new_papers)} 篇")

    # 保存
    all = existing + new_papers
    with open(existing_path, "w", encoding="utf-8") as f:
        json.dump(all, f, ensure_ascii=False, indent=2)

    with open(ROOT / "newly_crawled.json", "w", encoding="utf-8") as f:
        json.dump(new_papers, f, ensure_ascii=False, indent=2)

    print(f"\n已保存: {existing_path}")
    print(f"新增列表: newly_crawled.json")

    # 预览
    print("\n=== 新增论文预览 (前15篇) ===")
    for p in new_papers[:15]:
        print(f"  #{p['id']} [{p['year']}] {p['title'][:70]}")
        if p['venue']:
            if p.get('venue'): print(f"        Venue: {p['venue'][:60]}")

    return len(new_papers)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""补全论文缺失数据：OpenAlex API（摘要）+ Crossref（作者），每10篇输出进度"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "papers_enriched_updated.json"
H = {"User-Agent": "RobotGrindingKB/1.0 (mailto:research@example.com)"}

def log(msg):
    print(msg, flush=True)

def openalex_by_doi(doi):
    """OpenAlex 查论文"""
    url = f"https://api.openalex.org/works/doi:{urllib.request.quote(doi)}"
    time.sleep(0.15)
    req = urllib.request.Request(url, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except:
        return None

def extract_openalex(data):
    """从 OpenAlex 数据提取"""
    if not data: return {}
    ab = data.get("abstract_inverted_index")
    abstract = ""
    if ab:
        words = [""] * (max(max(v) for v in ab.values()) + 1)
        for word, pos in ab.items():
            for p in pos:
                if p < len(words): words[p] = word
        abstract = " ".join(words)[:600]

    authors = "; ".join(
        (a.get("author") or {}).get("display_name", "")
        for a in (data.get("authorships") or [])[:6]
    )
    year = data.get("publication_year", "")
    return {"abstract": abstract, "authors": authors, "year": str(year) if year else ""}

def main():
    log("Enriching papers via OpenAlex...")
    with open(SRC, "r", encoding="utf-8") as f:
        papers = json.load(f)
    total = len(papers)
    log(f"Total: {total} papers")

    enriched = 0
    for i, p in enumerate(papers):
        doi = (p.get("doi") or "").strip()
        if not doi:
            continue

        has_abs = bool((p.get("abstract") or "").strip())
        has_auth = bool((p.get("authors") or "").strip())
        has_year = bool(str(p.get("year", "")).strip())

        if has_abs and has_auth and has_year:
            continue  # already complete

        data = openalex_by_doi(doi)
        meta = extract_openalex(data)

        changed = False
        if not has_abs and meta.get("abstract"):
            p["abstract"] = meta["abstract"]; changed = True
        if not has_auth and meta.get("authors"):
            p["authors"] = meta["authors"]; changed = True
        if not has_year and meta.get("year"):
            p["year"] = meta["year"]; changed = True

        if changed:
            enriched += 1

        if (i + 1) % 50 == 0:
            log(f"  {i+1}/{total} processed, {enriched} enriched")

    # Save
    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    # Final stats
    new = [p for p in papers if p.get("id", 0) > 172]
    no_abs = sum(1 for p in new if not (p.get("abstract") or "").strip())
    no_auth = sum(1 for p in new if not (p.get("authors") or "").strip())
    log(f"\nDone! Enriched: {enriched}")
    log(f"Remaining - NoAbs: {no_abs}, NoAuth: {no_auth}")
    log(f"Saved: {SRC}")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""输出实验结果为 JSON + 简单 HTML 表格片段"""
import json, sys, re, math, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ===== 复用 experiment_retrieval.py 的逻辑 =====
from scripts.experiment_retrieval import (
    load_papers, build_text, get_category, tokenize, bm25_score,
    run_experiment, TEST_QUESTIONS
)
from scripts.taxonomy import TAXONOMY

TAX = TAXONOMY
category_keywords = {}
for level, cats in TAX.items():
    for cat, terms in cats.items():
        category_keywords[cat] = set(t.lower() for t in terms)

def structured_strategy(pid, p, qt, doc_texts, all_tokens, pbi):
    l1, l2, l3 = get_category(p)
    base = bm25_score(qt, tokenize(doc_texts[pid]), all_tokens)
    bonus = 0.0
    query_text = " ".join(qt)
    for cat in [l1, l2, l3]:
        if cat and cat != "其他":
            for kw in category_keywords.get(cat, set()):
                if kw in query_text:
                    bonus += 0.5
    return base + bonus

def hybrid_strategy(pid, p, qt, doc_texts, all_tokens, pbi):
    base = bm25_score(qt, tokenize(doc_texts[pid]), all_tokens)
    l1, l2, l3 = get_category(p)
    bonus = 0.0
    query_text = " ".join(qt)
    for cat in [l1, l2, l3]:
        if cat and cat != "其他":
            for kw in category_keywords.get(cat, set()):
                if kw in query_text:
                    bonus += 0.8
    abstract = (p.get("summary_zh") or p.get("abstract") or "").lower()
    for t in qt:
        if len(t) >= 2 and t in abstract:
            bonus += 0.3
    return base * (1 + bonus)

def naive_strategy(pid, p, qt, doc_texts, all_tokens, pbi):
    return bm25_score(qt, tokenize(doc_texts[pid]), all_tokens)

def main():
    print("Running experiment...", flush=True)
    papers_by_id = load_papers()

    results = {}
    strategies = [
        ("naive", "朴素BM25（全文检索）", naive_strategy),
        ("structured", "结构化（分类过滤+BM25）", structured_strategy),
        ("hybrid", "混合（分类+摘要加权）", hybrid_strategy),
    ]

    for key, name, func in strategies:
        print(f"  {name}...", flush=True)
        t0 = time.time()
        res = run_experiment(key, func, papers_by_id)
        results[key] = {"name": name, "results": res, "time": time.time() - t0}

    # 汇总
    summary = {}
    for key, data in results.items():
        res = data["results"]
        summary[key] = {
            "name": data["name"],
            "recall5": sum(r["recall5"] for r in res) / len(res),
            "recall10": sum(r["recall10"] for r in res) / len(res),
            "mrr": sum(r["mrr"] for r in res) / len(res),
            "time": data["time"],
        }

    # 按类型
    by_type = defaultdict(dict)
    for key, data in results.items():
        for qtype in ["工艺查询", "材料对比", "趋势分析", "定义解释"]:
            type_res = [r for r in data["results"] if r["type"] == qtype]
            if type_res:
                by_type[qtype][key] = sum(r["recall5"] for r in type_res) / len(type_res)

    # 改善
    naive_r5 = summary["naive"]["recall5"]
    hybrid_r5 = summary["hybrid"]["recall5"]
    improvement = (hybrid_r5 - naive_r5) / max(naive_r5, 0.001) * 100

    output = {
        "summary": summary,
        "by_type": {k: dict(v) for k, v in by_type.items()},
        "improvement": round(improvement, 1),
        "naive_r5": round(naive_r5 * 100, 1),
        "hybrid_r5": round(hybrid_r5 * 100, 1),
    }

    with open(ROOT / "experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: experiment_results.json")
    print(f"Naive: {naive_r5:.1%} -> Hybrid: {hybrid_r5:.1%} (+{improvement:.0f}%)")

if __name__ == "__main__":
    main()

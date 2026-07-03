# -*- coding: utf-8 -*-
"""RAG 检索策略对比实验：朴素 vs 结构化 vs 混合（PPT素材用）"""
import json, time, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys; sys.path.insert(0, str(ROOT))

# ========== 20 个测试问题 + 预期相关论文 ID ==========
# 格式：(问题, 预期匹配论文ID列表, 类型)
TEST_QUESTIONS = [
    ("钛合金叶片磨削如何控制表面粗糙度？", [7, 8, 9, 13, 15, 24, 187],
     "工艺查询"),
    ("砂带磨损监测有哪些方法？", [41, 42, 43, 44, 45, 90, 105],
     "工艺查询"),
    ("机器人磨削力控制策略有哪些？", [12, 16, 20, 22, 26, 54, 71, 139],
     "工艺查询"),
    ("航空发动机叶片的磨削路径如何规划？", [34, 51, 64, 74, 81, 88, 99, 109, 147],
     "工艺查询"),
    ("高温合金Inconel 718磨削用什么参数？", [42, 43, 44, 79, 92, 95, 96, 112],
     "材料对比"),
    ("钛合金TC4和TC17磨削有什么区别？", [6, 15, 16, 33, 38, 47, 48, 50],
     "材料对比"),
    ("陶瓷复合材料如何磨削？", [11, 17, 21, 30, 31, 100, 118, 119, 120],
     "材料对比"),
    ("磨削后残余应力如何预测？", [38, 45, 46, 48, 51, 52, 75, 77, 78, 100],
     "工艺查询"),
    ("数字孪生在磨削中有哪些应用？", [30, 36, 69, 73, 85, 152],
     "趋势分析"),
    ("深度学习在磨削中的应用有哪些？", [34, 36, 40, 42, 46, 60, 61, 69, 91],
     "趋势分析"),
    ("机器人磨抛系统的标定方法有哪些？", [2, 3, 4, 5, 14, 18, 19, 32, 35, 44, 45],
     "工艺查询"),
    ("砂带磨削的有限元仿真怎么做？", [9, 11, 12, 31, 34, 36, 40, 46, 60, 68],
     "工艺查询"),
    ("磨削过程的声发射监测如何实现？", [15, 72, 83, 84, 89, 90, 130],
     "工艺查询"),
    ("增材修复叶片的磨削工艺？", [18, 32, 51, 67, 144],
     "趋势分析"),
    ("柔顺控制与阻抗控制有什么区别？", [7, 12, 13, 20, 22, 26, 27, 28, 29],
     "定义解释"),
    ("什么是材料去除率？如何提高？", [1, 6, 7, 9, 12, 16, 17, 31, 40, 48, 55],
     "定义解释"),
    ("不锈钢叶片磨削参数优化", [52, 53, 59, 73, 141, 159, 162, 165],
     "工艺查询"),
    ("机器人磨削中的弹性接触如何建模？", [9, 11, 12, 17, 31, 34, 35, 40, 46, 58],
     "定义解释"),
    ("近五年磨削领域的研究热点有哪些？", [6, 15, 30, 31, 34, 36, 40, 42, 46, 69,
      73, 85, 90, 152, 171, 172],
     "趋势分析"),
    ("薄壁件机器人磨削如何防止变形？", [7, 8, 16, 54, 55, 63, 78, 80, 101],
     "工艺查询"),
]


def load_papers():
    with open(ROOT / "papers_enriched_updated.json", "r", encoding="utf-8") as f:
        papers = json.load(f)
    return {int(p["id"]): p for p in papers}


def build_text(p):
    """构建论文的检索文本"""
    parts = [
        p.get("title", ""),
        p.get("title_en", ""),
        p.get("abstract", ""),
        p.get("summary_zh", ""),
        " ".join(p.get("keywords", []) or []),
        " ".join(p.get("keywords_zh", []) or []),
        p.get("venue", ""),
        p.get("mindmap_path", ""),
    ]
    return " ".join(parts)


def get_category(p):
    """获取论文的 L1-L3 分类路径"""
    h = p.get("hierarchy") or {}
    l1 = (h.get("process_domain") or ["其他"])[0]
    l2 = (h.get("process_method") or ["其他"])[0]
    l3 = (h.get("research_topic") or ["其他"])[0]
    return l1, l2, l3


def tokenize(text):
    """简单分词：中文按字，英文按空格"""
    text = text.lower()
    # 英文词
    en_words = re.findall(r"[a-z0-9]+", text)
    # 中文按 bigram
    cn_chars = re.findall(r"[一-鿿]", text)
    cn_bigrams = ["".join(cn_chars[i:i+2]) for i in range(len(cn_chars)-1)]
    return set(en_words + cn_bigrams + cn_chars)


def bm25_score(query_tokens, doc_tokens, all_docs_tokens, k1=1.5, b=0.75):
    """简化 BM25"""
    import math
    N = len(all_docs_tokens)
    avgdl = sum(len(d) for d in all_docs_tokens) / max(N, 1)
    dl = len(doc_tokens)
    score = 0.0
    for t in query_tokens:
        df = sum(1 for d in all_docs_tokens if t in d)
        if df == 0:
            continue
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        tf = sum(1 for tt in doc_tokens if tt == t)
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score


def run_experiment(strategy_name, strategy_func, papers_by_id):
    """运行一种检索策略，返回 Recall@K"""
    # 预计算所有文档的 tokens
    doc_texts = {}
    doc_tokens_list = []
    for pid, p in papers_by_id.items():
        text = build_text(p)
        doc_texts[pid] = text
        doc_tokens_list.append(tokenize(text))

    all_doc_tokens = doc_tokens_list

    results = []
    for question, expected_ids, qtype in TEST_QUESTIONS:
        expected = set(expected_ids)
        query_tokens = tokenize(question)

        # 根据策略计算每个文档的分数
        scores = {}
        for pid, p in papers_by_id.items():
            score = strategy_func(pid, p, query_tokens, doc_texts, all_doc_tokens, papers_by_id)
            scores[pid] = score

        # 按分数排序，取 Top-K
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top5 = [pid for pid, s in ranked[:5]]
        top10 = [pid for pid, s in ranked[:10]]

        recall5 = len(set(top5) & expected) / max(len(expected), 1)
        recall10 = len(set(top10) & expected) / max(len(expected), 1)
        mrr = 0.0
        for i, (pid, s) in enumerate(ranked):
            if pid in expected:
                mrr = 1.0 / (i + 1)
                break

        results.append({
            "question": question[:30],
            "type": qtype,
            "recall5": recall5,
            "recall10": recall10,
            "mrr": mrr,
            "expected": len(expected),
            "found5": len(set(top5) & expected),
            "top5_ids": top5,
        })

    return results


def main():
    print("=" * 70)
    print("RAG 检索策略对比实验")
    print("=" * 70)

    papers_by_id = load_papers()
    print(f"论文总数: {len(papers_by_id)}")

    # ========== 策略 1：朴素 BM25（全文检索）==========
    print("\n[1/3] 朴素 BM25 全文检索...")
    t0 = time.time()

    def naive_strategy(pid, p, qt, doc_texts, all_tokens, pbi):
        return bm25_score(qt, tokenize(doc_texts[pid]), all_tokens)

    naive_results = run_experiment("朴素BM25", naive_strategy, papers_by_id)
    print(f"  耗时: {time.time()-t0:.1f}s")

    # ========== 策略 2：结构化检索（先按分类过滤，再 BM25）==========
    print("[2/3] 结构化检索（分类过滤 + BM25）...")
    t0 = time.time()

    from scripts.taxonomy import TAXONOMY as TAX
    category_keywords = {}
    for level, cats in TAX.items():
        for cat, terms in cats.items():
            category_keywords[cat] = set(t.lower() for t in terms)

    def structured_strategy(pid, p, qt, doc_texts, all_tokens, pbi):
        l1, l2, l3 = get_category(p)
        base = bm25_score(qt, tokenize(doc_texts[pid]), all_tokens)
        # 分类加成：如果查询词命中了论文的分类标签，加分
        bonus = 0.0
        query_text = " ".join(qt)
        for cat in [l1, l2, l3]:
            if cat and cat != "其他":
                cat_kw = category_keywords.get(cat, set())
                for kw in cat_kw:
                    if kw in query_text:
                        bonus += 0.5
        return base + bonus

    structured_results = run_experiment("结构化", structured_strategy, papers_by_id)
    print(f"  耗时: {time.time()-t0:.1f}s")

    # ========== 策略 3：混合检索（分类过滤 + 摘要加权）==========
    print("[3/3] 混合检索（分类+摘要加权）...")
    t0 = time.time()

    def hybrid_strategy(pid, p, qt, doc_texts, all_tokens, pbi):
        base = bm25_score(qt, tokenize(doc_texts[pid]), all_tokens)
        l1, l2, l3 = get_category(p)
        bonus = 0.0
        query_text = " ".join(qt)
        for cat in [l1, l2, l3]:
            if cat and cat != "其他":
                for kw in category_keywords.get(cat, set()):
                    if kw in query_text:
                        bonus += 0.8  # 更高权重
        # 摘要命中加分
        abstract = (p.get("summary_zh") or p.get("abstract") or "").lower()
        for t in qt:
            if len(t) >= 2 and t in abstract:
                bonus += 0.3
        return base * (1 + bonus)

    hybrid_results = run_experiment("混合", hybrid_strategy, papers_by_id)
    print(f"  耗时: {time.time()-t0:.1f}s")

    # ========== 汇总表格 ==========
    print("\n" + "=" * 70)
    print("实验结果汇总")
    print("=" * 70)

    all_strategies = [
        ("朴素BM25（全文检索）", naive_results),
        ("结构化（分类过滤+BM25）", structured_results),
        ("混合（分类+摘要加权）", hybrid_results),
    ]

    print(f"\n{'策略':<28} {'Recall@5':>9} {'Recall@10':>9} {'MRR':>6}")
    print("-" * 55)
    for name, res in all_strategies:
        avg_r5 = sum(r["recall5"] for r in res) / len(res)
        avg_r10 = sum(r["recall10"] for r in res) / len(res)
        avg_mrr = sum(r["mrr"] for r in res) / len(res)
        print(f"{name:<28} {avg_r5:>8.1%} {avg_r10:>8.1%} {avg_mrr:>6.3f}")

    # ========== 按问题类型分析 ==========
    print(f"\n{'按问题类型':-^55}")
    qtypes = defaultdict(list)
    for name, res in all_strategies:
        for r in res:
            qtypes[r["type"]].append((name, r))

    print(f"{'类型':<12} {'策略':<28} {'Recall@5':>9}")
    print("-" * 52)
    for qtype in ["工艺查询", "材料对比", "趋势分析", "定义解释"]:
        for name, res in all_strategies:
            type_res = [r for r in res if r["type"] == qtype]
            if type_res:
                avg = sum(r["recall5"] for r in type_res) / len(type_res)
                print(f"{qtype:<12} {name:<28} {avg:>8.1%}")

    # ========== 改善幅度 ==========
    print(f"\n{'改善幅度':-^55}")
    naive_avg = sum(r["recall5"] for r in naive_results) / len(naive_results)
    hybrid_avg = sum(r["recall5"] for r in hybrid_results) / len(hybrid_results)
    improvement = (hybrid_avg - naive_avg) / max(naive_avg, 0.001) * 100
    print(f"  朴素BM25 → 混合检索: Recall@5 提升 {improvement:+.0f}%")
    print(f"  朴素: {naive_avg:.1%} → 混合: {hybrid_avg:.1%}")

    print("\n[DONE] Experiment complete. Data ready for PPT.")


if __name__ == "__main__":
    main()

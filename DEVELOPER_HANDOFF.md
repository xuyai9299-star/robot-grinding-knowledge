# 🔧 RAG 检索策略 — 开发者交接文档

> 写给负责接入大模型/前端对话系统的同学
> 2025 年 6 月 · D:\robot-grinding-knowledge

---

## 一、你现在要做什么

把"混合检索策略"从实验代码变成真实 RAG 系统的检索层。

**简单来说**：用户问一个问题 → 你调用百炼 embedding API 把它变成向量 → 去向量数据库里找最相关的论文 → 把论文内容拼成 prompt → 让百炼 qwen-plus 生成回答。

---

## 二、数据在哪

| 文件 | 路径 | 说明 |
|------|------|------|
| 论文全集 | `papers_enriched_updated.json` | 1247篇，含 title/abstract/keywords/DOI/hierarchy |
| 五维分类 | 每篇论文的 `hierarchy` 字段 | `{"process_domain":["机器人磨削/抛光"],"process_method":["砂带/带式磨削"],...}` |
| 论文索引 | `papers_index.json` | 前端用的，by_id 格式 |
| 会议数据 | `conferences/conferences.json` | 期刊/会议 + 论文列表 |
| 实验脚本 | `scripts/experiment_retrieval.py` | BM25 模拟实验（参考检索逻辑） |

## 三、检索策略（你要实现的）

### 流程图

```
用户提问: "钛合金叶片磨削如何控制表面粗糙度？"
    │
    ▼
┌─────────────────────────────────────┐
│ Step 1: Embedding 向量化             │
│ 调用百炼 text-embedding-v3           │
│ 输入: 用户问题                       │
│ 输出: 1024 维向量                    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 2: 向量检索 (ChromaDB)          │
│ 在向量库中找 Top-20 篇最相似论文      │
│ 返回: 20 篇论文的 metadata            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 3: 结构化重排序（核心优化！）      │
│ 对这 20 篇论文：                      │
│  - 检查 hierarchy 标签是否匹配问题类型  │
│  - 摘要命中问题关键词的论文 +0.8 权重   │
│  - 重新排序 → Top-5                    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 4: Prompt 拼接 + 生成           │
│ 把 Top-5 论文的 title+abstract 拼接   │
│ 用 prompt 模板包装                    │
│ 调用百炼 qwen-plus 生成最终回答       │
└─────────────────────────────────────┘
```

### Step 3 的伪代码

```python
def rerank_with_hierarchy(query, top20_papers):
    """混合检索重排序"""
    scores = []
    for paper in top20_papers:
        base_score = paper.vector_similarity  # 向量相似度
        
        # 提取查询关键词
        query_keywords = extract_keywords(query)
        hierarchy = paper["hierarchy"]
        abstract = paper.get("abstract", "") or paper.get("summary_zh", "")
        
        bonus = 0.0
        # 分类匹配加分
        for level in ["process_domain", "process_method", "research_topic"]:
            for tag in hierarchy.get(level, []):
                if any(kw in tag for kw in query_keywords):
                    bonus += 0.8
        
        # 摘要命中加分
        for kw in query_keywords:
            if kw in abstract:
                bonus += 0.3
        
        final_score = base_score * (1 + bonus)
        scores.append((paper, final_score))
    
    # 按最终分数排序
    scores.sort(key=lambda x: -x[1])
    return [p for p, s in scores[:5]]
```

---

## 四、API 调用示例（百炼）

### Embedding

```python
from dashscope import TextEmbedding

def get_embedding(text):
    resp = TextEmbedding.call(
        model="text-embedding-v3",
        input=text,
        api_key="YOUR_DASHSCOPE_API_KEY"
    )
    return resp.output["embeddings"][0]["embedding"]  # 1024维
```

### 生成回答

```python
from dashscope import Generation

def generate_answer(prompt):
    resp = Generation.call(
        model="qwen-plus",
        prompt=prompt,
        api_key="YOUR_DASHSCOPE_API_KEY"
    )
    return resp.output["text"]
```

---

## 五、现有实验结果（供参考）

| 策略 | Recall@5 | MRR |
|------|----------|-----|
| 纯向量检索（无重排） | ~10% (预估) | ~0.39 |
| 向量 + 结构化重排 | ~14% (预估) | ~0.51 |
| **提升幅度** | **+29%** | **+30%** |

> 注：上述数据来自 BM25 模拟实验。真实 embedding 环境下绝对数值会更高（预估 30-60%），但相对改善趋势一致。
> 完整实验页面：`experiment.html`

---

## 六、你需要的文件清单

```
D:\robot-grinding-knowledge\
├── papers_enriched_updated.json   ← 核心：1247篇论文 + hierarchy标签
├── papers_index.json              ← 前端用索引
├── scripts/
│   ├── taxonomy.py                ← 五维分类规则（TAXONOMY dict）
│   ├── experiment_retrieval.py    ← 实验代码（参考 BM25 + rerank 逻辑）
│   └── rag_engine.py              ← 即将创建：真实 RAG 引擎
├── experiment.html                ← 实验结果展示页
└── experiment_results.json        ← 实验结果数据
```

---

## 七、有问题找我

- 五维分类标签怎么用 → 看 `taxonomy.py` 里的 `TAXONOMY` 字典
- 怎么提取查询关键词 → 看 `experiment_retrieval.py` 里的 `tokenize()` 函数
- 论文数据格式 → 看 `papers_enriched_updated.json` 任意一条

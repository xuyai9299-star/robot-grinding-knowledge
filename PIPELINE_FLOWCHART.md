# 机器人柔性磨削知识库 — 全流程自动更新管线

> 从数据采集到前端可视化的完整自动化管线 · 2025年6月

---

## 一、总览流程图

```mermaid
flowchart TB
    subgraph TRIGGER["🎯 触发方式"]
        A1["🖱️ 网页按钮点击<br/>「开始自动更新」"]
        A2["📁 放入 new_papers/*.csv<br/>（Zotero导出）"]
        A3["⏰ GitHub Actions<br/>定时任务（可选）"]
    end

    A1 -->|"POST /api/pipeline/run"| SERVER
    A2 -->|"python ingest.py"| INGEST
    A3 -->|"ingest.yml"| INGEST

    subgraph SERVER["🌐 Flask 管线服务器 (pipeline_server.py :8765)"]
        S1["接收 POST 请求"]
        S2["启动后台线程"]
        S3["SSE 实时推送到前端"]
        S1 --> S2 --> S3
    end

    S2 --> RUNNER

    subgraph RUNNER["⚙️ PipelineRunner (pipeline_runner.py)"]
        direction TB
        
        subgraph STEP1["📡 Step 1: OpenAlex 爬取"]
            C1["遍历 20 组搜索关键词"]
            C2["调用 OpenAlex REST API<br/>api.openalex.org/works"]
            C3["还原倒排索引摘要<br/>(abstract_inverted_index → 文本)"]
            C4["DOI + 标题双重去重"]
            C1 --> C2 --> C3 --> C4
        end

        C4 --> STEP2

        subgraph STEP2["🤖 Step 2: 百炼千问 LLM 处理"]
            D1{"DASHSCOPE_API_KEY<br/>是否配置？"}
            D2["构造 Prompt：<br/>标题+摘要 → 千问"]
            D3["千问返回 JSON：<br/>{relevance, summary_zh, keywords}"]
            D4["规则兜底：<br/>摘要前300字作中文摘要<br/>relevance 默认=3"]
            D5{"relevance ≥ 3？"}
            D6["✅ 通过筛选"]
            D7["❌ 拒绝（不相关）"]

            D1 -->|✅ 是| D2 --> D3 --> D5
            D1 -->|❌ 否| D4 --> D5
            D5 -->|≥3| D6
            D5 -->|<3| D7
        end

        D6 --> STEP3
        D7 --> REJECTED["🗑️ 拒绝列表<br/>（记录日志）"]

        subgraph STEP3["🔗 Step 3: 去重合并"]
            E1["加载现有知识库<br/>papers_enriched_updated.json"]
            E2["DOI + 标题双重比对"]
            E3["分配新 ID（自增）"]
            E4["合并到主数据集"]
            E1 --> E2 --> E3 --> E4
        end

        E4 --> STEP4

        subgraph STEP4["🏷️ Step 4: 五维自动分类"]
            F1["遍历每篇新论文"]
            F2["关键词匹配 taxonomy.py<br/>五层分类规则（中英双语）"]
            F3{"关键词匹配命中？"}
            F4["标题+摘要+venue<br/>文本回退匹配"]
            F5["生成 hierarchy_tags<br/>+ mindmap_path"]
            F1 --> F2 --> F3
            F3 -->|命中| F5
            F3 -->|未命中| F4 --> F5
        end

        F5 --> STEP5

        subgraph STEP5["📦 Step 5: 重建前端数据"]
            G1["保存 papers_enriched_updated.json"]
            G2["build_papers_index()<br/>→ papers_index.json"]
            G3["build_mindmap_stats()<br/>→ mindmap_stats.json"]
            G4["build_mindmaps_five()<br/>→ mindmaps_five.json"]
            G5["build_category_index()<br/>→ category_index.json"]
            G6["build_classified_payload()<br/>→ papers_classified.json"]
            G7["export_freemind_mm()<br/>→ 五维.mm (FreeMind)"]
            G8["export_outline_html()<br/>→ outline.html"]
            G9["同步所有 JSON/HTML 到 web/"]
            G1 --> G2 & G3 & G4 & G5 & G6 & G7 & G8
            G2 & G3 & G4 & G5 & G6 & G7 & G8 --> G9
        end

        G9 --> DONE
    end

    subgraph FRONTEND["🖥️ 前端可视化 (web/)"]
        H1["index.html<br/>知识导航主页"]
        H2["search.html<br/>高级检索（三栏）"]
        H3["d3_mindmap.html<br/>D3径向树"]
        H4["mindmaps.html<br/>vis-network层级导图"]
        H5["radial.html<br/>ECharts径向树"]
        H6["galaxy.html<br/>3D知识星系"]
        H7["conferences/<br/>会议期刊生态"]
        H8["timeline.html<br/>研究时间轴"]
        H9["experiment.html<br/>检索实验数据"]
    end

    DONE["🎉 完成！<br/>新增 N 篇 · 拒绝 M 篇<br/>总计 X 篇"]
    DONE -->|"papers_index.json<br/>mindmap_stats.json<br/>..."| FRONTEND

    subgraph INGEST["📥 增量入库 (ingest.py)"]
        I1["解析 Zotero CSV"]
        I2["LLM 生成摘要+关键词"]
        I3["自动分类"]
        I4["去重合并 → rebuild_all()"]
        I1 --> I2 --> I3 --> I4
    end

    I4 --> FRONTEND

    DONE -->|"SSE 推送结果"| UI["📱 网页实时显示<br/>新增论文列表<br/>拒绝论文列表<br/>更新统计"]

    style TRIGGER fill:#1e3a5f,stroke:#4cc9f0,color:#fff
    style SERVER fill:#1a1a2e,stroke:#7b5cfc,color:#fff
    style RUNNER fill:#0d1b33,stroke:#06d6a0,color:#fff
    style STEP1 fill:#162447,stroke:#4cc9f0,color:#fff
    style STEP2 fill:#162447,stroke:#a78bfa,color:#fff
    style STEP3 fill:#162447,stroke:#ffd166,color:#fff
    style STEP4 fill:#162447,stroke:#ff6b6b,color:#fff
    style STEP5 fill:#162447,stroke:#06d6a0,color:#fff
    style FRONTEND fill:#1e3a5f,stroke:#fbbf24,color:#fff
    style INGEST fill:#1e3a5f,stroke:#f472b6,color:#fff
```

---

## 二、LLM 决策逻辑详解

```mermaid
flowchart LR
    PAPER["📄 英文论文<br/>Title + Abstract"] --> PROMPT["构造 Prompt"]
    PROMPT --> QWEN["🦾 千问 qwen-plus<br/>（百炼 DashScope）"]
    QWEN --> JSON["返回 JSON"]
    JSON --> PARSE["解析"]
    PARSE --> REL{"relevance<br/>评分 1-5"}
    REL -->|"≥ 3 分"| ACCEPT["✅ 接受<br/>生成中文摘要<br/>+ 关键词"]
    REL -->|"< 3 分"| REJECT["❌ 拒绝<br/>记录原因"]
    ACCEPT --> CLASSIFY["进入五维分类"]
    REJECT --> LOG["记录到 rejected 列表<br/>前端显示原因"]

    subgraph PROMPT_DETAIL["Prompt 设计"]
        P1["System: 你是机器人磨削领域专家文献助手"]
        P2["要求输出 JSON: relevance + summary_zh + keywords"]
        P3["评分标准: 5=高度相关（机器人磨削/力控制/表面质量）<br/>1=完全无关（纯医学/纯地质）"]
    end
```

---

## 三、数据流全景

```mermaid
flowchart LR
    subgraph SOURCES["数据源"]
        ZOT["Zotero 文献库<br/>（华中科大·西北工大·重庆大学）<br/>172篇基础数据"]
        OA["OpenAlex API<br/>2.5亿+ 学术作品<br/>免费无限制"]
    end

    ZOT -->|"zotero_parser.py<br/>CSV解析"| RAW["📋 原始论文<br/>title/authors/year/doi/abstract"]
    OA -->|"crawl_papers.py<br/>20组关键词搜索"| RAW

    RAW --> ENRICH["enrich_papers.py<br/>OpenAlex DOI补全<br/>缺失摘要+作者"]
    ENRICH --> MASTER["💾 papers_enriched_updated.json<br/>主数据库（1247+篇）"]

    MASTER --> TAX["taxonomy.py<br/>五维分类引擎"]
    TAX -->|"hierarchy 标签"| MASTER2["💾 分类后的主数据库"]

    MASTER2 --> BUILD["build_outputs.py<br/>rebuild_all()"]
    BUILD --> WEB["📦 web/ 目录<br/>8个JSON + 10个HTML"]

    WEB --> CDN["🚀 部署<br/>GitHub Pages / 本地服务器"]

    NEW["🆕 新论文（CSV/API）"] -->|"pipeline_runner.py"| LLM["🤖 千问筛选"]
    LLM -->|"通过"| MASTER
    LLM -->|"拒绝"| TRASH["🗑️ 不相关"]
```

---

## 四、文件对应关系

| 管线步骤 | Python 脚本 | 输入 | 输出 |
|---------|------------|------|------|
| Zotero解析 | `scripts/zotero_parser.py` | `new_papers/*.csv` | 论文字典列表 |
| OpenAlex爬取 | `scripts/crawl_papers.py` | API查询 | `newly_crawled.json` |
| 元数据补全 | `scripts/enrich_papers.py` | DOI → OpenAlex | 补全的摘要/作者/年份 |
| LLM摘要+筛选 | `scripts/bailian_client.py` | 标题+摘要 → 千问 | summary_zh + keywords + relevance |
| 五维分类 | `scripts/taxonomy.py` | 论文关键词/文本 | hierarchy 五层标签 |
| 重建前端数据 | `scripts/build_outputs.py` | 主JSON | 8个前端数据文件 |
| 一键重建 | `scripts/rebuild_all.py` | 主JSON | 全部输出 + 同步到 web/ |
| **全自动管线** | **`scripts/pipeline_runner.py`** | OpenAlex API | 全流程 + 进度事件 |
| **Web 服务器** | **`pipeline_server.py`** | HTTP请求 | SSE流 + 静态文件 |
| 增量入库 | `ingest.py` | new_papers/*.csv | 更新主JSON + 重建 |

---

## 五、启动方式

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置百炼 API Key（可选，不设则用规则兜底）
set DASHSCOPE_API_KEY=sk-your-key-here

# 3. 启动管线服务器
py -3 pipeline_server.py

# 4. 打开浏览器
# http://localhost:8765
# 滚动到页面底部 → 点击「🚀 开始自动更新」

# 5. 或者命令行直接运行管线
py -3 -m scripts.pipeline_runner
```

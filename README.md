# 机器人柔性磨削知识库

基于 172+ 篇论文的结构化知识库：**增量入库（Python）** + **静态网页检索（GitHub Pages）** + **阿里云百炼（千问）** 生成中文摘要与关键词。

仓库地址：[xuyai9299-star/robot-grinding-knowledge](https://github.com/xuyai9299-star/robot-grinding-knowledge)

---

## 你能做什么

| 能力 | 说明 |
|------|------|
| 增量入库 | 把 Zotero 导出的 CSV 放进 `new_papers/`，运行 `ingest.py` 或 push 触发 Actions |
| 自动分类 | 五级 taxonomy → `hierarchy_tags` / `mindmap_path` |
| 百炼摘要 | 有 `DASHSCOPE_API_KEY` 时自动生成 `summary_zh` 与 `keywords` |
| 网页检索 | `web/` 部署到 GitHub Pages，读最新 JSON，无需 Flask 常开 |

---

## 快速开始（本地）

### 1. 安装

```powershell
cd robot-grinding-knowledge
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置百炼 API Key

在 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 创建 API Key，并设为环境变量：

```powershell
$env:DASHSCOPE_API_KEY = "sk-你的密钥"
```

说明见官方文档：[首次调用千问 API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)

不配置 Key 也可运行（仅合并 CSV + 规则分类，不生成中文摘要）：

```powershell
$env:SKIP_LLM = "1"
```

### 3. 确保主数据存在

根目录需有 `papers_enriched_updated.json`（仓库已含 172 篇）。若缺失，从 GitHub 拉取：

```powershell
py -3 scripts/bootstrap_data.py
```

### 4. 重算分类与导出（不增加新论文）

```powershell
py -3 ingest.py --rebuild-only
```

生成/更新：

- `papers_classified.json` — 前端检索用（含 url/doi）
- `papers_index.json` — **按 ID 查论文详情与原文链接**
- `category_index.json` — 分类 → 论文 ID 映射
- `mindmap_stats.json` — 思维导图树（**每个节点含 paper_ids**）

### 6. 本地预览新版网页（三层：分类 → 列表 → 详情+链接）

```powershell
cd robot-grinding-knowledge
py -3 ingest.py --rebuild-only
py -3 -m http.server 8080
```

浏览器打开 <http://127.0.0.1:8080>（根目录 `index.html`，不是 web/ 子目录）

### 5. 本地预览网页

```powershell
cd web
py -3 -m http.server 8080
```

浏览器打开：<http://127.0.0.1:8080>

---

## 新增论文工作流

1. Zotero 选中文献 → 导出 CSV（列名与 `Title` / `DOI` / `Abstract Note` 等兼容即可）
2. 复制到 `new_papers/`，例如 `new_papers/重庆大学_2026.csv`
3. 运行：

```powershell
$env:DASHSCOPE_API_KEY = "sk-xxx"
py -3 ingest.py
```

4. 处理完的 CSV 会自动移到 `archive/`
5. 提交 JSON 变更并 push 到 GitHub

---

## GitHub Actions（云端自动入库）

### Secrets（必配一项）

在仓库 **Settings → Secrets and variables → Actions** 添加：

| 名称 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 百炼 API Key |

未配置时 Workflow 会自动 `SKIP_LLM=1`，只做分类合并。

### 触发方式

- 向 `new_papers/` 提交 CSV 后 push
- 或在 Actions 页手动 **Run workflow**

### 开启 GitHub Pages

1. **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**
2. push 后访问：`https://xuyai9299-star.github.io/robot-grinding-knowledge/`

（由 `.github/workflows/pages.yml` 部署 `web/` + JSON）

---

## 目录结构

```
robot-grinding-knowledge/
├── ingest.py                 # 入库入口
├── config.py
├── requirements.txt
├── papers_enriched_updated.json   # 主数据（全字段）
├── papers_classified.json         # 前端 API 切片
├── mindmap_stats.json             # 导图统计（ingest 生成）
├── scripts/
│   ├── taxonomy.py           # 五级分类规则
│   ├── zotero_parser.py      # CSV 解析
│   ├── bailian_client.py     # 百炼 / DashScope
│   ├── build_outputs.py      # 导出 classified + mindmap
│   └── bootstrap_data.py     # 从 GitHub 拉取主数据
├── new_papers/               # 待入库 CSV
├── archive/                  # 已处理 CSV
├── web/                      # 静态检索站
└── .github/workflows/
    ├── ingest.yml
    └── pages.yml
```

---

## 与旧方案的区别

| 旧仓库状态 | 现在 |
|------------|------|
| `ingest.py` 只有伪代码 | 可运行的完整流水线 |
| 依赖 OpenAI | 改为 **阿里云百炼 DashScope**（`dashscope` SDK） |
| 无前端 | 提供 `web/` + Pages 部署 |
| 无导图统计 | `mindmap_stats.json` 随 ingest 更新 |

---

## 后续扩展（未实现）

- 网页内 AI 问答 + 会话级动态思维导图（需后端或 Serverless + 百炼）
- Neo4j 图谱与 ingest 联动

---

## 许可

研究/教学用途；论文元数据版权归原作者。

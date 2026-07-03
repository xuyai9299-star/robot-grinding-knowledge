# -*- coding: utf-8 -*-
"""
知识库更新 API 服务器（Flask + SSE）。
启动: py -3 pipeline_server.py  或  python pipeline_server.py
端口: 8765
"""
from __future__ import annotations

import json
import os
import sys
import time
import queue
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from flask import Flask, Response, request, jsonify, send_from_directory
except ImportError:
    print("需要安装 Flask: pip install flask")
    sys.exit(1)

from scripts.pipeline_runner import PipelineRunner

app = Flask(__name__, static_folder=str(ROOT / "web"), static_url_path="")

# ── SSE 事件队列 ─────────────────────────────────────
_event_queues: list[queue.Queue] = []
_pipeline_running = threading.Lock()


def _broadcast(event: dict) -> None:
    """向所有连接的 SSE 客户端发送事件。"""
    data = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    dead = []
    for q in _event_queues:
        try:
            q.put_nowait(data)
        except Exception:
            dead.append(q)
    for q in dead:
        if q in _event_queues:
            _event_queues.remove(q)


# ── 路由 ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(ROOT / "web"), "index.html")


@app.route("/dashboard")
@app.route("/dashboard/")
def dashboard():
    return send_from_directory(str(ROOT / "web" / "dashboard"), "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(str(ROOT / "web"), path)


@app.route("/api/stats")
def api_stats():
    """返回知识库当前统计。"""
    master = ROOT / "papers_enriched_updated.json"
    papers_count = 0
    if master.exists():
        with open(master, "r", encoding="utf-8") as f:
            papers_count = len(json.load(f))
    conf_path = ROOT / "conferences" / "conferences.json"
    venues_count = 0
    if conf_path.exists():
        with open(conf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            venues_count = data.get("total_conferences", 0) + data.get("total_journals", 0)

    return jsonify({
        "total_papers": papers_count,
        "total_venues": venues_count,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.localtime(master.stat().st_mtime) if master.exists() else 0),
    })


@app.route("/api/pipeline/run", methods=["POST"])
def api_pipeline_run():
    """启动知识库更新管线（异步）。"""
    if _pipeline_running.locked():
        return jsonify({"ok": False, "error": "已有更新任务在运行中，请稍后再试"}), 409

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
    has_llm = bool(api_key) and os.getenv("SKIP_LLM", "").lower() not in ("1", "true", "yes")

    def _run():
        with _pipeline_running:
            try:
                runner = PipelineRunner(api_key=api_key)
                for event in runner.run():
                    _broadcast(event)
            except Exception as e:
                _broadcast({
                    "step": "error", "status": "error",
                    "message": f"管线异常: {e}",
                    "error": str(e),
                    "ts": time.time(),
                })
            finally:
                _broadcast({
                    "step": "shutdown", "status": "complete",
                    "message": "服务端管线线程结束",
                    "ts": time.time(),
                })

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "管线已启动", "llm_enabled": has_llm})


@app.route("/api/pipeline/stream")
def api_pipeline_stream():
    """SSE 端点：实时推送管线进度。"""
    def generate():
        q: queue.Queue = queue.Queue()
        _event_queues.append(q)
        try:
            # 发送初始连接确认
            yield f"data: {json.dumps({'step': 'connected', 'status': 'ok', 'message': 'SSE 已连接', 'ts': time.time()}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    data = q.get(timeout=30)
                    yield data
                except queue.Empty:
                    # 发送心跳
                    yield f"data: {json.dumps({'step': 'heartbeat', 'status': 'ok', 'ts': time.time()}, ensure_ascii=False)}\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in _event_queues:
                _event_queues.remove(q)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no",
                             "Access-Control-Allow-Origin": "*"})


@app.route("/api/pipeline/status")
def api_pipeline_status():
    """查询管线是否在运行。"""
    return jsonify({"running": _pipeline_running.locked()})


@app.route("/api/search", methods=["POST"])
def api_search():
    """AI 搜索：ChromaDB 向量检索 → 五维分类重排序 → 千问生成回答（带引用）。

    检索流程：
    1. 查询 → text-embedding-v3 → 1024维向量
    2. ChromaDB 余弦相似度检索 Top-20
    3. 五维分类加成 + 摘要命中加权 → 重排序 → Top-3
    4. Top-3 论文拼接 → 千问 qwen-plus 生成回答（带[#ID]引用）

    若 ChromaDB 不可用，回退到关键词匹配模式。
    """
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"ok": False, "error": "请输入搜索内容"}), 400

    api_key = data.get("api_key") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY") or ""

    # Step 1: 加载论文主数据
    master_path = ROOT / "papers_enriched_updated.json"
    if not master_path.exists():
        return jsonify({"ok": False, "error": "知识库数据不存在，请先构建知识库"}), 500

    with open(master_path, "r", encoding="utf-8") as f:
        all_papers = json.load(f)

    # 建立 ID 索引
    papers_by_id = {}
    for p in all_papers:
        papers_by_id[int(p.get("id", 0))] = p

    # Step 2: 向量检索 (ChromaDB) 或回退到关键词
    retrieval_mode = "keyword"
    collection = None
    vector_candidates = []  # list of (paper_id, similarity_score)

    try:
        import chromadb
        chroma_path = str(ROOT / "chroma_db")
        if not Path(chroma_path).exists():
            chroma_path = str(ROOT)  # 尝试根目录

        client = chromadb.PersistentClient(path=chroma_path)
        collections = client.list_collections()
        col_names = [c.name for c in collections]
        collection = None
        for name in ["robot_grinding_papers", "grinding_papers", "papers"]:
            if name in col_names:
                collection = client.get_collection(name)
                break
        if collection is None and col_names:
            collection = client.get_collection(col_names[0])

        if collection is not None and collection.count() > 0:
            # 有向量库 → embedding 检索
            retrieval_mode = "vector"
            has_llm_key = bool(api_key)
            if has_llm_key:
                try:
                    from dashscope import TextEmbedding
                    emb_resp = TextEmbedding.call(
                        model="text-embedding-v3",
                        input=query[:6000],
                        api_key=api_key,
                    )
                    if emb_resp.status_code == 200:
                        query_emb = emb_resp.output["embeddings"][0]["embedding"]
                        chroma_results = collection.query(
                            query_embeddings=[query_emb],
                            n_results=20,
                            include=["metadatas", "distances"],
                        )
                        ids_list = chroma_results.get("ids", [[]])[0]
                        dists = chroma_results.get("distances", [[]])[0]
                        metas = chroma_results.get("metadatas", [[]])[0]
                        for cid, dist, meta in zip(ids_list, dists, metas):
                            pid_str = cid.replace("paper_", "")
                            try:
                                pid = int(pid_str)
                            except ValueError:
                                continue
                            sim = 1.0 / (1.0 + dist) if dist is not None else 0.5
                            vector_candidates.append((pid, sim, meta))
                except Exception:
                    pass  # embedding 失败 → 回退关键词
    except Exception:
        pass  # ChromaDB 不可用 → 回退关键词

    # Step 3: 候选论文打分（向量相似度 + 五维分类加成 + 摘要加权）
    qlower = query.lower()
    query_words = [w for w in qlower.split() if len(w) >= 2]

    try:
        from scripts.taxonomy import TAXONOMY as TAX
        category_keywords = {}
        for level, cats in TAX.items():
            for cat, terms in cats.items():
                category_keywords[cat] = set(t.lower() for t in terms)
    except Exception:
        category_keywords = {}

    scored = []

    if retrieval_mode == "vector" and vector_candidates:
        # 从向量候选出发，加分类加成
        for pid, sim, meta in vector_candidates:
            p = papers_by_id.get(pid)
            if not p:
                continue
            bonus = 0.0
            h = p.get("hierarchy") or {}
            for level in ["process_domain", "process_method", "research_topic"]:
                for tag in h.get(level) or []:
                    if tag and tag != "其他":
                        cat_kw = category_keywords.get(tag, set())
                        for kw in cat_kw:
                            if kw in qlower:
                                bonus += 0.8
                                break
            # 摘要命中
            summary = (p.get("summary_zh") or "").lower()
            abstract = (p.get("abstract") or "").lower()
            for w in query_words:
                if w in summary or w in abstract:
                    bonus += 0.3
            final_score = sim * (1.0 + bonus)
            scored.append((final_score, sim, bonus, p))
    else:
        # 关键词模式（回退）
        for p in all_papers:
            score = 0.0
            title = (p.get("title") or "").lower()
            abstract = (p.get("abstract") or "").lower()
            summary = (p.get("summary_zh") or "").lower()
            kws = " ".join((p.get("keywords") or []) + (p.get("keywords_zh") or [])).lower()
            for word in query_words:
                if word in title: score += 5
                if word in kws: score += 3
                if word in abstract: score += 1
                if word in summary: score += 2
            if qlower in title: score += 10
            if qlower in abstract: score += 4
            if qlower in summary: score += 5
            if score <= 0:
                continue
            bonus = 0.0
            h = p.get("hierarchy") or {}
            for level in ["process_domain", "process_method", "research_topic"]:
                for tag in h.get(level) or []:
                    if tag and tag != "其他":
                        cat_kw = category_keywords.get(tag, set())
                        for kw in cat_kw:
                            if kw in qlower:
                                bonus += 0.8
                                break
            for w in query_words:
                if w in summary or w in abstract:
                    bonus += 0.3
            final_score = score * (1.0 + bonus)
            scored.append((final_score, score, bonus, p))

    scored.sort(key=lambda x: -x[0])

    # Step 4: Top-3 送 LLM
    top_papers = [(final_score, paper) for final_score, _raw, _bonus, paper in scored[:3]]

    if not top_papers:
        return jsonify({
            "ok": True,
            "answer": '未找到与「' + query + '」相关的论文。请尝试其他关键词，如【砂带磨削】【力控制】【表面质量】等。',
            "papers": [],
            "total_searched": len(all_papers),
            "mode": retrieval_mode,
        })

    context_parts = []
    citations = []
    for i, (score, p) in enumerate(top_papers):
        pid = p.get("id", "?")
        title = p.get("title", "")[:120]
        abstract = (p.get("summary_zh") or p.get("abstract") or "")[:300]
        context_parts.append(f"[#{pid}] {title}\n摘要: {abstract}")
        citations.append({
            "id": pid,
            "title": title,
            "year": p.get("year", ""),
            "authors": (p.get("authors") or "")[:80],
            "doi": p.get("doi", ""),
            "url": p.get("url", ""),
            "keywords": (p.get("keywords_zh") or p.get("keywords") or [])[:5],
        })

    context = "\n\n".join(context_parts)

    # Step 5: 千问生成回答
    answer = None
    has_llm = bool(api_key)
    if has_llm:
        try:
            from dashscope import Generation
            prompt = f"""你是机器人柔性磨削领域的专家助手。根据以下论文信息回答用户问题。

用户问题: {query}

相关论文:
{context}

请基于以上论文信息回答问题。要求：
1. 回答中标注引用来源，格式为 [#论文ID]
2. 如果论文信息不足以完整回答，请诚实说明
3. 回答控制在 300 字以内
4. 使用中文回答"""
            resp = Generation.call(
                api_key=api_key,
                model=os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
                messages=[
                    {"role": "system", "content": "你是机器人磨削领域专家。基于提供的论文信息回答问题，标注引用来源。"},
                    {"role": "user", "content": prompt},
                ],
                result_format="message",
            )
            if getattr(resp, "status_code", 200) == 200:
                answer = resp.output.choices[0].message.content
        except Exception as e:
            answer = f"（AI 生成失败: {e}）\n\n以下是检索到的相关论文信息：\n{context}"

    if not answer:
        answer = "以下是检索到的相关论文信息：\n\n" + context

    return jsonify({
        "ok": True,
        "answer": answer,
        "papers": citations,
        "total_searched": len(all_papers),
        "mode": retrieval_mode,
        "vector_count": collection.count() if (retrieval_mode == "vector" and collection is not None) else 0,
        "llm_used": has_llm and answer is not None and "AI 生成失败" not in str(answer),
    })


# ── 启动 ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    # Force UTF-8 for Windows terminal
    sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 56)
    print("  RGKB Pipeline Server")
    print(f"  Static: {ROOT / 'web'}")
    print(f"  URL:    http://localhost:8765")
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_API_KEY")
    print(f"  LLM:    {'[OK] DashScope configured' if api_key else '[!] No API key (rule-based fallback)'}")
    print(f"  Search: ChromaDB vector + taxonomy rerank -> qwen-plus")
    print("=" * 56)
    app.run(host="0.0.0.0", port=8765, debug=False, threaded=True)

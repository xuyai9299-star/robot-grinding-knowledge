# -*- coding: utf-8 -*-
"""
P0-1: Build Vector Database for RAG System
- Embed 1247 papers using Alibaba Bailian text-embedding-v3
- Store in ChromaDB (file-based, exportable)
- Output: chroma_db/ directory (can be zipped and shared)
"""
import json, sys, time, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("[ERROR] chromadb not installed. Run: py -3 -m pip install chromadb")
    sys.exit(1)

try:
    from dashscope import TextEmbedding
except ImportError:
    print("[ERROR] dashscope not installed. Run: py -3 -m pip install dashscope")
    sys.exit(1)


def build_chunk(paper):
    """Build a searchable text chunk from paper metadata"""
    parts = []
    title = paper.get("title_en") or paper.get("title", "")
    if title: parts.append(f"Title: {title.strip()}")

    kws = paper.get("keywords_zh") or paper.get("keywords") or []
    if kws: parts.append(f"Keywords: {', '.join(kws[:8])}")

    abstract = paper.get("summary_zh") or paper.get("abstract") or ""
    if abstract: parts.append(f"Abstract: {abstract.strip()[:500]}")

    path = paper.get("mindmap_path") or ""
    if path: parts.append(f"Classification: {path}")

    authors = paper.get("authors", "")
    if authors: parts.append(f"Authors: {authors[:120]}")

    year = paper.get("year", "")
    if year: parts.append(f"Year: {year}")

    return "\n".join(parts)


def get_embedding(text, api_key=None):
    """Call Bailian text-embedding-v3"""
    key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
    if not key:
        raise RuntimeError("DASHSCOPE_API_KEY not set. Set environment variable or pass api_key param.")

    resp = TextEmbedding.call(
        model="text-embedding-v3",
        input=text[:6000],  # max 6K chars per chunk
        api_key=key,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Embedding API error {resp.status_code}: {resp.message}")

    return resp.output["embeddings"][0]["embedding"]


def main():
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("=" * 60)
        print("  VECTOR DATABASE BUILDER")
        print("=" * 60)
        print()
        print("  [!] DASHSCOPE_API_KEY not found in environment.")
        print()
        api_key = input("  Enter your Bailian API Key: ").strip()
        if not api_key:
            print("  [ERROR] API Key required. Abort.")
            return 1
        os.environ["DASHSCOPE_API_KEY"] = api_key

    print()
    print("=" * 60)
    print("  VECTOR DATABASE BUILDER")
    print("  Embedding: Bailian text-embedding-v3 (1024-dim)")
    print("  Storage:   ChromaDB (file-based)")
    print("=" * 60)
    print()

    # Load papers
    data_path = ROOT / "papers_enriched_updated.json"
    print(f"[1/4] Loading papers from {data_path.name}...", end=" ", flush=True)
    with open(data_path, "r", encoding="utf-8") as f:
        papers = json.load(f)
    print(f"DONE ({len(papers)} papers)")

    # Filter: only papers with usable text
    valid = []
    for p in papers:
        chunk = build_chunk(p)
        if len(chunk) > 30:  # must have some content
            valid.append((p, chunk))
    print(f"       Valid papers (with text): {len(valid)}")

    # Init ChromaDB
    db_path = str(ROOT / "chroma_db")
    print(f"\n[2/4] Initializing ChromaDB at {db_path}...", end=" ", flush=True)
    client = chromadb.PersistentClient(path=db_path)

    # Create or get collection
    collection_name = "robot_grinding_papers"
    # Delete if exists to rebuild fresh
    try:
        client.delete_collection(collection_name)
    except:
        pass
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": "Robot flexible grinding papers - 1247 papers", "hnsw:space": "cosine"},
    )
    print("DONE")

    # Embed and insert (batched)
    batch_size = 10
    total = len(valid)
    print(f"\n[3/4] Embedding {total} papers (batch size: {batch_size})...")
    print(f"       Estimated time: ~{total * 0.5 / 60:.0f} min (API rate ~2 req/s)")
    print()

    embedded = 0
    failed = 0

    for i in range(0, total, batch_size):
        batch = valid[i:i + batch_size]
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for p, chunk in batch:
            pid = str(p.get("id", i))
            ids.append(f"paper_{pid}")
            documents.append(chunk)

            # Metadata for filtering
            metadatas.append({
                "paper_id": int(p.get("id", 0)),
                "title": (p.get("title_en") or p.get("title", ""))[:200],
                "year": str(p.get("year", "")),
                "doi": p.get("doi", ""),
                "venue": (p.get("venue") or "")[:100],
                "hierarchy_path": p.get("mindmap_path", ""),
            })

            # Get embedding
            try:
                emb = get_embedding(chunk, api_key)
                embeddings.append(emb)
            except Exception as e:
                print(f"  [!] Failed embedding paper {pid}: {e}")
                failed += 1
                # Use zero vector as fallback
                embeddings.append([0.0] * 1024)

            time.sleep(0.4)  # Rate limit: ~2-3 req/s

        # Batch insert
        try:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            embedded += len(batch)
        except Exception as e:
            print(f"  [!] Batch insert failed: {e}")
            failed += len(batch)

        # Progress
        pct = (embedded / total) * 100
        bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
        print(f"\r  [{bar}] {pct:.0f}% | {embedded}/{total} embedded | {failed} failed", end="", flush=True)

    print()
    print(f"\n[4/4] Saving... DONE")
    print()

    # Summary
    count = collection.count()
    print("=" * 60)
    print("  BUILD COMPLETE")
    print("=" * 60)
    print(f"  Papers embedded:  {count}")
    print(f"  Failed:           {failed}")
    print(f"  Database path:    {db_path}")
    print(f"  Database size:    ~{os.path.getsize(db_path + '/chroma.sqlite3') / 1024 / 1024:.1f} MB (SQLite)")
    print()
    print("  [EXPORT] To share with developer:")
    print(f"    Zip the folder: {db_path}")
    print("    Developer loads with:")
    print(f'    client = chromadb.PersistentClient(path="chroma_db")')
    print(f'    collection = client.get_collection("robot_grinding_papers")')
    print("=" * 60)

    # Test query
    print()
    print("  [TEST] Running sample query: 'titanium blade grinding surface roughness'")
    results = collection.query(query_texts=["titanium blade grinding surface roughness"], n_results=3)
    for i, (doc_id, dist, meta) in enumerate(zip(
        results["ids"][0], results["distances"][0], results["metadatas"][0]
    )):
        print(f"    #{i+1}: {meta.get('title','?')[:60]} (dist: {dist:.3f})")

    return 0


if __name__ == "__main__":
    sys.exit(main())

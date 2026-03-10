from datetime import datetime
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer



DB_DIR = Path(__file__).parent / "chroma_db"
COLLECTION = "log_chunks"
MODEL = "all-MiniLM-L6-v2"

_embedder = None
_collection = None


def _get_collection():
    global _embedder, _collection
    if _collection is None:
        print("  Loading embedding model...")
        _embedder = SentenceTransformer(MODEL)
        client = chromadb.PersistentClient(path=str(DB_DIR))
        _collection = client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection, _embedder


def upsert(chunks: list) -> int:
    if not chunks:
        return 0
    collection, embedder = _get_collection()
    texts = [c.content for c in chunks]
    vectors = embedder.encode(texts, show_progress_bar=False).tolist()
    collection.upsert(
        ids=[c.chunk_id for c in chunks],
        embeddings=vectors,
        documents=texts,
        metadatas=[{
            "timestamp":      c.timestamp.isoformat(),
            "timestamp_unix": int(c.timestamp.timestamp()),
            "severity":       c.severity,
            "service":        c.service,
            "file_name":      c.file_name,
            "line_start":     c.line_start,
            "line_end":       c.line_end,
        } for c in chunks],
    )
    return len(chunks)


def query(
    text,
    n=10,
    severity=None,
    service=None,
    file_name=None,
    since=None,
    until=None,
):
    collection, embedder = _get_collection()
    if collection.count() == 0:
        return []

    conditions = []
    if severity:
        conditions.append({"severity": {"$in": severity}})
    if service:
        conditions.append({"service": {"$eq": service}})
    if file_name:
        conditions.append({"file_name": {"$eq": file_name}})
    if since:
        conditions.append({"timestamp_unix": {"$gte": int(since.timestamp())}})
    if until:
        conditions.append({"timestamp_unix": {"$lte": int(until.timestamp())}})

    where = None
    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    vector = embedder.encode(text).tolist()
    results = collection.query(
        query_embeddings=[vector],
        n_results=min(n, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({"content": doc, "metadata": meta, "score": round(1 - dist, 4)})
    return sorted(output, key=lambda x: x["score"], reverse=True)


def stats() -> dict:
    collection, _ = _get_collection()
    return {"total_chunks": collection.count(), "db_dir": str(DB_DIR)}
import json
import faiss
import numpy as np
from app.config import INDEX_PATH, CHUNKS_PATH, RAG_TOP_K
from app.services.embedding_service import encode

_index: faiss.IndexFlatIP | None = None
_chunks: list[str] = []


def load_index():
    global _index, _chunks
    if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
        return
    _index = faiss.read_index(str(INDEX_PATH))
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        _chunks = json.load(f)


def search(query: str, top_k: int = RAG_TOP_K) -> list[str]:
    if _index is None or not _chunks:
        return []
    query_emb = encode([query])
    scores, indices = _index.search(query_emb, top_k)
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(_chunks) and scores[0][i] > 0.3:
            results.append(_chunks[idx])
    return results

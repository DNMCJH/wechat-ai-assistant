import json
import numpy as np
from pathlib import Path
from typing import Optional
from app.config import DATA_DIR, FAQ_THRESHOLD
from app.services.embedding_service import encode

_faq_data: list[dict] = []
_faq_embeddings: np.ndarray | None = None


def load_faq():
    global _faq_data, _faq_embeddings
    faq_path = DATA_DIR / "faq.json"
    if not faq_path.exists():
        return
    with open(faq_path, "r", encoding="utf-8") as f:
        _faq_data = json.load(f)
    if _faq_data:
        questions = [item["question"] for item in _faq_data]
        _faq_embeddings = encode(questions)


def match(query: str) -> Optional[str]:
    if not _faq_data or _faq_embeddings is None:
        return None
    query_emb = encode([query])
    scores = np.dot(_faq_embeddings, query_emb.T).flatten()
    best_idx = int(np.argmax(scores))
    if scores[best_idx] >= FAQ_THRESHOLD:
        return _faq_data[best_idx]["answer"]
    return None

import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def encode(texts: list[str]) -> np.ndarray:
    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return np.array(embeddings, dtype=np.float32)

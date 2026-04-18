import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import faiss
import numpy as np
from pathlib import Path
from app.services.embedding_service import encode
from app.config import DATA_DIR, INDEX_PATH, CHUNKS_PATH

CHUNK_SIZE = 200
CHUNK_OVERLAP = 50


def split_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


def main():
    doc_dir = DATA_DIR / "documents"
    if not doc_dir.exists():
        print("No documents directory found.")
        return

    all_chunks = []
    for fpath in sorted(doc_dir.glob("*.txt")):
        text = fpath.read_text(encoding="utf-8")
        chunks = split_text(text)
        print(f"  {fpath.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    if not all_chunks:
        print("No text chunks found.")
        return

    print(f"\nTotal chunks: {len(all_chunks)}")
    print("Encoding...")
    embeddings = encode(all_chunks)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Index saved: {INDEX_PATH}")
    print(f"Chunks saved: {CHUNKS_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()

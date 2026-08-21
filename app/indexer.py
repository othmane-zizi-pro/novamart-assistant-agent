"""Build and load the embedding index for the policy corpus.

The index is a local JSON cache keyed by a content hash per chunk, so re-running
after editing one document only re-embeds the chunks that changed. Run with:

    python -m app.indexer
"""

import hashlib
import json

import numpy as np
from google.genai import types

from app.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, INDEX_DIR
from app.genai_client import call_with_backoff, get_client
from app.kb import Chunk, load_chunks

INDEX_PATH = INDEX_DIR / "embeddings.json"
BATCH_SIZE = 20


def _content_hash(chunk: Chunk) -> str:
    return hashlib.sha256(chunk.embedding_text().encode()).hexdigest()[:16]


def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    client = get_client()
    result = call_with_backoff(
        lambda: client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIMENSIONS,
                task_type=task_type,
            ),
        )
    )
    return [e.values for e in result.embeddings]


def _normalize(vector: list[float]) -> list[float]:
    array = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    if norm == 0:
        return array.tolist()
    return (array / norm).tolist()


def embed_query(text: str) -> np.ndarray:
    [vector] = _embed_batch([text], task_type="RETRIEVAL_QUERY")
    return np.asarray(_normalize(vector), dtype=np.float32)


def build_index() -> dict[str, list[float]]:
    chunks = load_chunks()
    cached: dict[str, dict] = {}
    if INDEX_PATH.exists():
        stored = json.loads(INDEX_PATH.read_text())
        if stored.get("model") == EMBEDDING_MODEL and stored.get("dimensions") == (
            EMBEDDING_DIMENSIONS
        ):
            cached = {entry["chunk_id"]: entry for entry in stored["chunks"]}

    entries: list[dict] = []
    to_embed: list[Chunk] = []
    for chunk in chunks:
        digest = _content_hash(chunk)
        hit = cached.get(chunk.chunk_id)
        if hit and hit["hash"] == digest:
            entries.append(hit)
        else:
            to_embed.append(chunk)

    for start in range(0, len(to_embed), BATCH_SIZE):
        batch = to_embed[start : start + BATCH_SIZE]
        vectors = _embed_batch([c.embedding_text() for c in batch], task_type="RETRIEVAL_DOCUMENT")
        for chunk, vector in zip(batch, vectors, strict=True):
            entries.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "hash": _content_hash(chunk),
                    "embedding": _normalize(vector),
                }
            )

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(
            {
                "model": EMBEDDING_MODEL,
                "dimensions": EMBEDDING_DIMENSIONS,
                "chunks": entries,
            }
        )
    )
    return {entry["chunk_id"]: entry["embedding"] for entry in entries}


def load_index() -> dict[str, np.ndarray]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError("embedding index missing; run `make index` first")
    stored = json.loads(INDEX_PATH.read_text())
    return {
        entry["chunk_id"]: np.asarray(entry["embedding"], dtype=np.float32)
        for entry in stored["chunks"]
    }


if __name__ == "__main__":
    index = build_index()
    print(f"indexed {len(index)} chunks -> {INDEX_PATH}")

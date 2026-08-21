"""Hermetic retrieval tests: BM25 is exercised for real, embeddings are faked.

The fake embedder hashes tokens into a fixed vocabulary space, so vector
similarity behaves like exact-vocabulary overlap. That keeps the hybrid path
executable offline; semantic paraphrase quality is measured by the live eval
suite instead.
"""

import hashlib

import numpy as np

from app.kb import load_chunks
from app.search import Bm25, SearchIndex, tokenize

VOCAB_DIMENSIONS = 512


def _stable_hash(token: str) -> int:
    return int.from_bytes(hashlib.md5(token.encode()).digest()[:4], "big")


def fake_embed(text: str) -> np.ndarray:
    vector = np.zeros(VOCAB_DIMENSIONS, dtype=np.float32)
    for token in tokenize(text):
        vector[_stable_hash(token) % VOCAB_DIMENSIONS] += 1.0
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def build_fake_index() -> SearchIndex:
    chunks = load_chunks()
    embeddings = {c.chunk_id: fake_embed(c.embedding_text()) for c in chunks}
    return SearchIndex(chunks, embeddings, fake_embed)


def test_bm25_ranks_exact_vocabulary() -> None:
    documents = [tokenize(t) for t in ("the restocking fee", "gift cards", "price match")]
    scores = Bm25(documents).scores(tokenize("restocking fee"))
    assert scores.argmax() == 0


def test_restocking_query_surfaces_both_sides_of_the_seam() -> None:
    # The corpus deliberately overlaps here: returns charge a restocking fee on
    # opened electronics, even exchanges waive it. Retrieval must surface both.
    results = build_fake_index().search("what is the restocking fee for opened electronics")
    top_ids = [r.chunk.chunk_id for r in results[:3]]
    assert "returns-policy#electronics" in top_ids
    assert "exchanges#even-exchanges" in top_ids


def test_warranty_query_hits_warranty_doc() -> None:
    results = build_fake_index().search("NovaCare accidental damage claim")
    assert results[0].chunk.doc_id == "warranty-claims"


def test_order_status_query_hits_shipping_doc() -> None:
    results = build_fake_index().search("order stuck in processing status address change")
    assert results[0].chunk.doc_id == "shipping-orders"


def test_top_k_bounds_results() -> None:
    results = build_fake_index().search("returns", top_k=3)
    assert len(results) == 3

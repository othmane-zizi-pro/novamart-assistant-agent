"""Hybrid search over the policy corpus: BM25 blended with embedding similarity.

BM25 catches exact vocabulary (order numbers, "NovaCare", "restocking fee");
embeddings catch paraphrase ("get my money back" never says "refund"). Each
signal is min-max normalized per query, then blended. Run ad hoc with:

    python -m app.search "can I return an opened laptop"
"""

import math
import re
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.kb import Chunk, load_chunks

BM25_K1 = 1.5
BM25_B = 0.75
VECTOR_WEIGHT = 0.5
TOP_K = 5


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class Bm25:
    """Okapi BM25 over the chunk texts, small enough to hold fully in memory."""

    def __init__(self, documents: list[list[str]]):
        self.doc_freqs = [Counter(doc) for doc in documents]
        self.doc_lens = [len(doc) for doc in documents]
        self.avg_len = sum(self.doc_lens) / len(documents) if documents else 0.0
        term_doc_count: Counter[str] = Counter()
        for freqs in self.doc_freqs:
            term_doc_count.update(freqs.keys())
        n = len(documents)
        self.idf = {
            term: math.log(1 + (n - count + 0.5) / (count + 0.5))
            for term, count in term_doc_count.items()
        }

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        result = np.zeros(len(self.doc_freqs), dtype=np.float32)
        for term in query_tokens:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, freqs in enumerate(self.doc_freqs):
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                norm = 1 - BM25_B + BM25_B * self.doc_lens[i] / self.avg_len
                result[i] += idf * tf * (BM25_K1 + 1) / (tf + BM25_K1 * norm)
        return result


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float
    bm25_score: float
    vector_score: float


def _min_max(scores: np.ndarray) -> np.ndarray:
    span = scores.max() - scores.min()
    if span == 0:
        return np.zeros_like(scores)
    return (scores - scores.min()) / span


class SearchIndex:
    """Holds chunks, their embeddings, and a query embedder.

    The embedder is injected so tests can run hermetically with a fake, and the
    agent and eval share one instance.
    """

    def __init__(
        self,
        chunks: list[Chunk],
        embeddings: dict[str, np.ndarray],
        embed_query: Callable[[str], np.ndarray],
    ):
        self.chunks = chunks
        self.embed_query = embed_query
        self.bm25 = Bm25([tokenize(c.embedding_text()) for c in chunks])
        self.matrix = np.stack([embeddings[c.chunk_id] for c in chunks])

    def search(self, query: str, top_k: int = TOP_K) -> list[SearchResult]:
        bm25_raw = self.bm25.scores(tokenize(query))
        vector_raw = self.matrix @ self.embed_query(query)
        blended = (1 - VECTOR_WEIGHT) * _min_max(bm25_raw) + VECTOR_WEIGHT * _min_max(vector_raw)
        order = np.argsort(blended)[::-1][:top_k]
        return [
            SearchResult(
                chunk=self.chunks[i],
                score=float(blended[i]),
                bm25_score=float(bm25_raw[i]),
                vector_score=float(vector_raw[i]),
            )
            for i in order
        ]


def load_search_index() -> SearchIndex:
    from app.indexer import embed_query, load_index

    return SearchIndex(load_chunks(), load_index(), embed_query)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "can I return an opened laptop"
    for result in load_search_index().search(query):
        print(
            f"{result.score:.3f}  (bm25 {result.bm25_score:.2f} / vec {result.vector_score:.2f})"
            f"  {result.chunk.chunk_id}"
        )
        print(f"       {result.chunk.text[:120]}...")

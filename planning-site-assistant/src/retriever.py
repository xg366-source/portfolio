"""BM25 retriever (pure stdlib).

Why BM25 as the baseline instead of jumping straight to embeddings:
it is reproducible with zero API keys, and the evaluation harness can show
exactly what an embedding backend improves. Swap `BM25Index` for a vector
index behind the same `search()` interface to run that comparison.
Tokenisation mixes word tokens with CJK character bigrams so Chinese
queries match Chinese documents without a segmenter dependency.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from ingest import Chunk


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    cjk = re.findall(r"[一-鿿]+", text)
    for run in cjk:
        tokens.extend(run)                      # unigrams
        tokens.extend(run[i:i + 2] for i in range(len(run) - 1))  # bigrams
    return tokens


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(c.text)) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(len(self.lengths), 1)
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        if not q:
            return []
        scored = []
        for chunk, counts, length in zip(self.chunks, self.docs, self.lengths):
            score = 0.0
            for term in set(q):
                f = counts.get(term, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * length / self.avg_len)
                score += self.idf.get(term, 0.0) * f * (self.k1 + 1) / denom
            if score > 0:
                scored.append((chunk, round(score, 3)))
        return sorted(scored, key=lambda x: -x[1])[:top_k]

    @staticmethod
    def term_coverage(query: str, chunk: Chunk) -> float:
        """Share of distinct query terms present in the chunk (refusal signal)."""
        q = set(tokenize(query))
        if not q:
            return 0.0
        return len(q & set(tokenize(chunk.text))) / len(q)

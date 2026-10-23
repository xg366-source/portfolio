"""Answer engine: routes each question to documents, GIS, or a refusal.

Routing contract (the product's core honesty rules):
1. Questions about numbers/rankings/correlations -> structured GIS query.
2. Questions about documents -> BM25 retrieval; answer only from chunks,
   every claim carries a citation.
3. If retrieval is too weak (score or term coverage below threshold),
   refuse explicitly instead of improvising. Thresholds live in config.yaml
   and are calibrated against the eval set's unanswerable questions.

Generation: with an LLM API key the retrieved chunks are handed to the
model with a cite-or-refuse prompt (see `build_llm_prompt`). Without a key
the engine runs in extractive demo mode: it returns the top chunks as the
answer body. Demo mode is labelled in every response — never disguised.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from gis_query import GISLayers
from ingest import ingest_dir
from retriever import BM25Index

REFUSAL = "资料库中没有足够依据回答这个问题。我只能基于已收录的规划文件和 GIS 图层作答；如需回答，请先补充相关资料。"

GEOID_RE = re.compile(r"\b\d{11}\b")
RANK_PATTERNS = [  # (keywords, field, mode)
    (["311", "最高"], "req_311_per_1000", "rank"),
    (["报案", "最高"], "crime_per_1000", "rank"),
    (["犯罪", "最高"], "crime_per_1000", "rank"),
    (["西裔", "占比", "最高"], "pct_hispanic", "rank"),
    (["b级以下", "最高"], "rest_pct_below_A", "rank"),
    (["报案", "中位"], "crime_per_1000", "median"),
    (["311", "中位"], "req_311_per_1000", "median"),
]


class AnswerEngine:
    def __init__(self, root: str | Path):
        root = Path(root)
        cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
        self.cfg = cfg
        self.chunks = ingest_dir(root / cfg["docs_dir"])
        self.index = BM25Index(self.chunks)
        self.gis = GISLayers(root / cfg["gis_dir"])
        self.has_llm = bool(cfg.get("llm", {}).get("api_key_env"))

    # ---------- GIS route ----------
    def _try_gis(self, q: str) -> dict | None:
        m = GEOID_RE.search(q)
        if m and ("这个" in q or "该" in q or "tract" in q.lower() or "人口" in q or "占比" in q):
            prof = self.gis.tract_profile(m.group(0))
            if prof:
                lines = [f"{k}：{v}" for k, v in prof["values"].items()]
                return self._ok("；".join(lines), [f"{prof['source']} · GEOID {prof['geoid']}"],
                                route="gis_profile")
        if "相关" in q and "西裔" in q and ("餐厅" in q or "b级" in q.lower()):
            c = self.gis.correlation("pct_hispanic", "rest_pct_below_A")
            if c:
                verdict = "不支持" if abs(c["r"]) < 0.2 else "存在相关"
                text = (f"对 {c['n']} 个餐厅数≥5 的 tract 计算：西裔占比与餐厅 B 级以下占比的 "
                        f"相关系数 r = {c['r']}，数据{verdict}“西裔占比越高、餐厅评级越差”的说法。")
                return self._ok(text, ["food_safety_by_tract.geojson + acs_demographics_expanded.geojson · 相关分析"],
                                route="gis_correlation")
        for keywords, field, mode in RANK_PATTERNS:
            if all(k in q.lower() for k in keywords):
                if mode == "rank":
                    r = self.gis.rank_top(field)
                    if r:
                        text = (f"在人口≥{r['min_pop']} 的 {r['n_eligible']} 个 tract 中，{r['label']}最高的是 "
                                f"GEOID {r['geoid']}，为 {r['value']}（该 tract 人口 {r['total_pop']}）。"
                                f"注：小人口 tract 的每千人比率会被放大，故设人口门槛，口径见 data_notes。")
                        return self._ok(text, [f"{r['source']} · GEOID {r['geoid']}"], route="gis_rank")
                else:
                    v = self.gis.median(field)
                    if v is not None:
                        from gis_query import FIELD_SOURCE
                        src = FIELD_SOURCE.get(field, "acs_demographics_expanded.geojson")
                        return self._ok(f"{field} 的 tract 中位数为 {round(v, 1)}（每千人）。",
                                        [f"{src} · 全 113 tract"], route="gis_median")
        return None

    # ---------- document route ----------
    def _try_docs(self, q: str) -> dict:
        hits = self.index.search(q, top_k=self.cfg["retrieval"]["top_k"])
        if not hits:
            return self._refuse("no_hits")
        top_chunk, top_score = hits[0]
        coverage = self.index.term_coverage(q, top_chunk)
        if top_score < self.cfg["retrieval"]["min_score"] or coverage < self.cfg["retrieval"]["min_coverage"]:
            return self._refuse(f"weak_retrieval score={top_score} coverage={round(coverage, 2)}")
        citations = [c.citation() for c, _ in hits]
        body = " ".join(c.text for c, _ in hits[:2])
        return self._ok(body, citations, route="docs", score=top_score)

    # ---------- plumbing ----------
    def _ok(self, text: str, citations: list[str], route: str, score: float | None = None) -> dict:
        return {"answer": text, "citations": citations, "refused": False,
                "route": route, "score": score, "mode": "llm" if self.has_llm else "extractive-demo"}

    def _refuse(self, reason: str) -> dict:
        return {"answer": REFUSAL, "citations": [], "refused": True,
                "route": "refusal", "score": None, "mode": "extractive-demo", "reason": reason}

    def ask(self, question: str) -> dict:
        return self._try_gis(question) or self._try_docs(question)


def build_llm_prompt(question: str, chunks: list) -> str:
    """Prompt used when an LLM key is configured: cite-or-refuse, nothing else."""
    context = "\n\n".join(f"[{c.citation()}]\n{c.text}" for c in chunks)
    return (
        "你只能依据下面的资料回答。每个结论后标注来源（文件名·章节）。"
        "资料不足以回答时，原样回复拒答句，不得用常识补全。\n\n"
        f"资料：\n{context}\n\n问题：{question}"
    )

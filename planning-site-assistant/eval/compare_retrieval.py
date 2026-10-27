"""BM25 vs TF-IDF retrieval comparison on the 40-question eval set.

Scope, stated plainly so the result is not over-read:
- Only the DOCUMENT route is compared. GIS questions are answered by
  structured query by design (numbers never go through retrieval), so they
  are excluded here; the end-to-end 40-question run stays in run_eval.py.
- Ranking quality is compared threshold-free (Recall@5, Recall@1, MRR@5),
  because BM25 scores and cosine scores live on different scales and sharing
  one refusal threshold would rig the comparison.
- Refusal behaviour is reported separately: top-1 score distributions for
  answerable vs unanswerable questions, and whether a cosine threshold can
  separate them at all. Any threshold calibrated here is fitted on the eval
  set itself and must be validated on held-out questions before shipping.

Usage: python3 eval/compare_retrieval.py [--out eval/compare_results.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
import yaml  # noqa: E402
from ingest import ingest_dir  # noqa: E402
from retriever import BM25Index, TFIDFIndex  # noqa: E402

DOC_SOURCES = ("site_overview", "data_notes")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "eval" / "compare_results.json"))
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    chunks = ingest_dir(ROOT / cfg["docs_dir"])
    indexes = {"bm25": BM25Index(chunks), "tfidf": TFIDFIndex(chunks)}
    print(f"chunks: {len(chunks)}")

    questions = [json.loads(line) for line in
                 (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    doc_qs = [q for q in questions
              if q["answerable"] and q["expected_source"] in DOC_SOURCES]
    ref_qs = [q for q in questions if not q["answerable"]]
    print(f"doc-route answerable: {len(doc_qs)}, unanswerable: {len(ref_qs)}")

    rows, per_cat = [], {}
    for q in doc_qs:
        row = {"id": q["id"], "category": q["category"]}
        for name, idx in indexes.items():
            hits = idx.search(q["question"], top_k=5)
            cits = [c.citation() for c, _ in hits]
            r5 = any(q["expected_source"] in c for c in cits)
            r1 = bool(cits) and q["expected_source"] in cits[0]
            mrr = 0.0
            for rank, c in enumerate(cits, 1):
                if q["expected_source"] in c:
                    mrr = 1.0 / rank
                    break
            row[name] = {"recall@5": r5, "recall@1": r1, "mrr": round(mrr, 3),
                         "top1_score": hits[0][1] if hits else 0.0,
                         "top1_citation": cits[0] if cits else None}
            cat = per_cat.setdefault(q["category"], {}).setdefault(
                name, {"n": 0, "r5": 0, "r1": 0, "mrr": 0.0})
            cat["n"] += 1
            cat["r5"] += r5
            cat["r1"] += r1
            cat["mrr"] += mrr
        row["agree"] = row["bm25"]["recall@5"] == row["tfidf"]["recall@5"]
        rows.append(row)
        flag = "" if row["agree"] else "  <-- DIVERGES"
        print(f"{q['id']:8s} bm25 R@5={int(row['bm25']['recall@5'])} "
              f"tfidf R@5={int(row['tfidf']['recall@5'])} "
              f"bm25 top1={row['bm25']['top1_score']} tfidf top1={row['tfidf']['top1_score']}{flag}")

    def agg(name: str) -> dict:
        n = len(doc_qs)
        return {"n": n,
                "recall@5": round(sum(r[name]["recall@5"] for r in rows) / n, 3),
                "recall@1": round(sum(r[name]["recall@1"] for r in rows) / n, 3),
                "mrr@5": round(sum(r[name]["mrr"] for r in rows) / n, 3)}

    metrics = {name: agg(name) for name in indexes}
    metrics["per_category"] = {
        cat: {name: {"n": v["n"], "recall@5": round(v["r5"] / v["n"], 3),
                     "recall@1": round(v["r1"] / v["n"], 3),
                     "mrr@5": round(v["mrr"] / v["n"], 3)}
              for name, v in cats.items()}
        for cat, cats in per_cat.items()}

    # Refusal-side score distributions (top-1 score, answerable vs not).
    dist = {}
    for label, qs in (("answerable_doc", doc_qs), ("unanswerable", ref_qs)):
        for name, idx in indexes.items():
            scores = []
            for q in qs:
                hits = idx.search(q["question"], top_k=1)
                scores.append(hits[0][1] if hits else 0.0)
            scores.sort()
            dist[f"{name}_{label}"] = {
                "min": scores[0] if scores else 0.0,
                "median": scores[len(scores) // 2] if scores else 0.0,
                "max": scores[-1] if scores else 0.0,
                "all": scores}
    metrics["top1_score_distributions"] = dist
    divergences = [r["id"] for r in rows if not r["agree"]]
    metrics["divergent_questions"] = divergences

    print("\n== retrieval metrics (doc route only) ==")
    print(json.dumps(metrics, ensure_ascii=False, indent=1))
    Path(args.out).write_text(json.dumps({"metrics": metrics, "rows": rows},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()

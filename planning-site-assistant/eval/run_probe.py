"""Probe set runner: paraphrased questions, same ranking metrics as the main
comparison. The probe set is NOT part of the headline 40-question metrics:
it exists to test whether BM25 and TF-IDF diverge once questions stop using
the documents' own wording. A tie here is also a finding (see selection report).

Also runs the end-to-end TF-IDF check: AnswerEngine with the TF-IDF index
swapped in and a cosine refusal threshold of 0.22 (midpoint between the
unanswerable max 0.169 and answerable min 0.286 measured on the eval set;
fitted on the eval set, so it needs held-out validation before shipping).

Usage: python3 eval/run_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
import yaml  # noqa: E402
from answer import AnswerEngine  # noqa: E402
from ingest import ingest_dir  # noqa: E402
from retriever import BM25Index, TFIDFIndex  # noqa: E402


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    chunks = ingest_dir(ROOT / cfg["docs_dir"])
    indexes = {"bm25": BM25Index(chunks), "tfidf": TFIDFIndex(chunks)}
    probes = [json.loads(line) for line in
              (ROOT / "eval" / "probe_questions.jsonl").read_text(encoding="utf-8").splitlines()]
    print("== probe ranking (10 paraphrased questions) ==")
    for name, idx in indexes.items():
        r5 = r1 = mrr = 0
        for q in probes:
            hits = idx.search(q["question"], top_k=5)
            cits = [c.citation() for c, _ in hits]
            r5 += any(q["expected_source"] in c for c in cits)
            r1 += bool(cits) and q["expected_source"] in cits[0]
            for rank, c in enumerate(cits, 1):
                if q["expected_source"] in c:
                    mrr += 1.0 / rank
                    break
        n = len(probes)
        print(f"{name}: Recall@5={r5 / n:.2f} Recall@1={r1 / n:.2f} MRR@5={mrr / n:.3f}")

    print("\n== end-to-end TF-IDF check (cosine threshold 0.22, all 40 questions) ==")
    engine = AnswerEngine(ROOT)
    engine.index = TFIDFIndex(engine.chunks)
    engine.cfg["retrieval"]["min_score"] = 0.22
    questions = [json.loads(line) for line in
                 (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    verdicts = {}
    for q in questions:
        res = engine.ask(q["question"])
        if q["answerable"]:
            if res["refused"]:
                v = "OVER_REFUSED"
            else:
                hit = any(q["expected_source"] in c for c in res["citations"])
                ok = q.get("must_contain", "") in res["answer"] if q.get("must_contain") else True
                v = "PASS" if hit and ok else "FAIL"
        else:
            v = "PASS" if res["refused"] else "HALLUCINATION_RISK"
        verdicts[v] = verdicts.get(v, 0) + 1
        if v != "PASS":
            print(f"{q['id']:8s} {v} route={res['route']}")
    print(verdicts)


if __name__ == "__main__":
    main()

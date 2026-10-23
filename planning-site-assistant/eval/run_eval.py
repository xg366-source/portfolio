"""Run the eval set against the answer engine and report the 5 core metrics.

Metrics (retrieval/generation split, so failures are attributable):
- recall@5          : expected source among citations (answerable doc/gis questions)
- answer_contains   : expected key value present in the answer text
- refusal_accuracy  : unanswerable questions correctly refused
- over_refusal      : answerable questions wrongly refused
- hallucination     : answered an unanswerable question (proxy; human check still needed)

Usage: python3 eval/run_eval.py [--out eval/results.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from answer import AnswerEngine  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "eval" / "results.json"))
    args = ap.parse_args()

    engine = AnswerEngine(ROOT)
    rows, agg = [], {"recall": 0, "recall_n": 0, "contains": 0, "contains_n": 0,
                     "refused_ok": 0, "refused_n": 0, "over_refused": 0, "answered_n": 0}
    for line in (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        res = engine.ask(q["question"])
        row = {"id": q["id"], "category": q["category"], "refused": res["refused"], "route": res["route"]}
        if q["answerable"]:
            agg["answered_n"] += 1
            if res["refused"]:
                agg["over_refused"] += 1
                row["verdict"] = "OVER_REFUSED"
            else:
                agg["recall_n"] += 1
                hit = any(q["expected_source"] in c for c in res["citations"])
                agg["recall"] += hit
                row["recall_hit"] = hit
                if q.get("must_contain"):
                    agg["contains_n"] += 1
                    ok = q["must_contain"] in res["answer"]
                    agg["contains"] += ok
                    row["contains_ok"] = ok
                row["verdict"] = "PASS" if hit and row.get("contains_ok", True) else "FAIL"
        else:
            agg["refused_n"] += 1
            agg["refused_ok"] += res["refused"]
            row["verdict"] = "PASS" if res["refused"] else "HALLUCINATION_RISK"
        rows.append(row)
        print(f"{row['id']:8s} {row['category']:16s} {row['verdict']}")

    metrics = {
        "recall_at_k": round(agg["recall"] / agg["recall_n"], 3) if agg["recall_n"] else None,
        "answer_contains_rate": round(agg["contains"] / agg["contains_n"], 3) if agg["contains_n"] else None,
        "refusal_accuracy": round(agg["refused_ok"] / agg["refused_n"], 3) if agg["refused_n"] else None,
        "over_refusal_rate": round(agg["over_refused"] / agg["answered_n"], 3) if agg["answered_n"] else None,
        "hallucination_risk_questions": agg["refused_n"] - agg["refused_ok"],
    }
    print("\n== metrics ==")
    print(json.dumps(metrics, ensure_ascii=False, indent=1))
    Path(args.out).write_text(json.dumps({"metrics": metrics, "rows": rows},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()

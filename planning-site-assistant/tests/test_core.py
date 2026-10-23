"""Core behaviour tests: GIS guardrails, citation, refusal.
Run: python3 -m pytest tests/ -q   (or: python3 tests/test_core.py)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from answer import AnswerEngine  # noqa: E402

engine = AnswerEngine(ROOT)


def test_rank_excludes_tiny_tract():
    # The raw per-1000 leader is a 344-person tract; the guardrail must win.
    r = engine.gis.rank_top("req_311_per_1000")
    assert r["geoid"] == "36081028500", r
    assert r["total_pop"] >= 2000


def test_tract_profile_cites_source():
    prof = engine.gis.tract_profile("36081024300")
    assert prof and prof["values"]["西裔/拉丁裔占比(%)"] == 45.0


def test_doc_answer_has_citation():
    res = engine.ask("餐厅卫生评级 A 级的分数标准是什么？")
    assert not res["refused"] and res["citations"]


def test_unanswerable_is_refused():
    res = engine.ask("上海静安区的人口密度是多少？")
    assert res["refused"] and res["citations"] == []


def test_correlation_verdict_is_honest():
    res = engine.ask("西裔占比高的区域，餐厅B级以下占比也更高吗？两者相关吗？")
    assert "不支持" in res["answer"]  # r ~= 0.06 in the real data


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)

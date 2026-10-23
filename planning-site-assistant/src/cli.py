"""Command-line demo — no server, no API key needed.

Usage: python3 src/cli.py "311投诉最高的tract是哪个？"
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from answer import AnswerEngine  # noqa: E402

if __name__ == "__main__":
    engine = AnswerEngine(Path(__file__).parent.parent)
    q = sys.argv[1] if len(sys.argv) > 1 else "研究范围总人口是多少？"
    print(json.dumps(engine.ask(q), ensure_ascii=False, indent=1))

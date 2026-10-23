"""HTTP API: POST /ask, GET /tract/<geoid>, static web + GIS files.

Run:  uvicorn app:app --app-dir src --port 8000   (from repo root)
Then open http://localhost:8000/ for the map interface.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).parent.parent

from answer import AnswerEngine  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

engine = AnswerEngine(ROOT)
app = FastAPI(title="Planning Site Assistant")


class AskBody(BaseModel):
    question: str


@app.post("/ask")
def ask(body: AskBody):
    return engine.ask(body.question)


@app.get("/tract/{geoid}")
def tract(geoid: str):
    prof = engine.gis.tract_profile(geoid)
    return prof if prof else JSONResponse({"error": "unknown GEOID"}, status_code=404)


app.mount("/data/gis", StaticFiles(directory=ROOT / "data" / "gis"), name="gis")
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")

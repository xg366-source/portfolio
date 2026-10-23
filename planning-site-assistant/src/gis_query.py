"""Structured GIS queries over census-tract GeoJSON layers.

Design rule: numbers never go through the LLM or vector search.
Anything countable is computed here from the layer attributes and returned
with the layer + GEOID as its citation.

Method guardrail (learned from the data itself): per-capita rankings use
MIN_POP = 2000 by default. The raw top of req_311_per_1000 is a 344-person
tract whose rate explodes purely from its tiny denominator — reporting it
as "the worst area" would be a methodology error, so the threshold and the
reason are part of the answer.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

MIN_POP = 2000
MIN_REST_N = 10  # minimum restaurants before a tract's grade share is meaningful

LAYERS = {
    "demographics": "acs_demographics_expanded.geojson",
    "requests_311": "311_by_tract_2026ytd.geojson",
    "crime": "crime_by_tract_2026ytd.geojson",
    "food_safety": "food_safety_by_tract.geojson",
}

FIELD_SOURCE = {  # citations must name the layer that actually owns the field
    "req_311_per_1000": "311_by_tract_2026ytd.geojson",
    "crime_per_1000": "crime_by_tract_2026ytd.geojson",
    "crime_total": "crime_by_tract_2026ytd.geojson",
    "rest_pct_below_A": "food_safety_by_tract.geojson",
    "rest_n": "food_safety_by_tract.geojson",
}

FIELD_LABELS = {
    "total_pop": "总人口", "pct_hispanic": "西裔/拉丁裔占比(%)", "pct_asian": "亚裔占比(%)",
    "req_311_per_1000": "311投诉(每千人)", "crime_per_1000": "报案数(每千人)",
    "crime_total": "报案总数", "rest_pct_below_A": "餐厅B级以下占比(%)", "rest_n": "餐厅数",
}


class GISLayers:
    def __init__(self, gis_dir: str | Path):
        self.by_geoid: dict[str, dict] = {}
        self.source_of: dict[str, str] = {}
        for layer, fname in LAYERS.items():
            path = Path(gis_dir) / fname
            if not path.exists():
                continue
            for feat in json.loads(path.read_text(encoding="utf-8"))["features"]:
                p = feat["properties"]
                geoid = p["GEOID"]
                self.by_geoid.setdefault(geoid, {}).update(
                    {k: v for k, v in p.items() if v is not None})
                self.source_of.setdefault(geoid, fname)

    def tract_profile(self, geoid: str) -> dict | None:
        p = self.by_geoid.get(geoid)
        if p is None:
            return None
        return {"geoid": geoid, "source": self.source_of[geoid],
                "values": {FIELD_LABELS.get(k, k): v for k, v in p.items() if k != "GEOID"}}

    def _eligible(self, field: str, min_pop: int) -> list[dict]:
        rows = [p for p in self.by_geoid.values()
                if p.get(field) is not None and p.get("total_pop", 0) >= min_pop]
        if field == "rest_pct_below_A":
            rows = [p for p in rows if (p.get("rest_n") or 0) >= MIN_REST_N]
        return rows

    def rank_top(self, field: str, min_pop: int = MIN_POP) -> dict | None:
        rows = self._eligible(field, min_pop)
        if not rows:
            return None
        top = max(rows, key=lambda p: p[field])
        return {"field": field, "label": FIELD_LABELS.get(field, field),
                "geoid": top["GEOID"], "value": top[field], "total_pop": top["total_pop"],
                "n_eligible": len(rows), "min_pop": min_pop,
                "source": FIELD_SOURCE.get(field, self.source_of[top["GEOID"]])}

    def median(self, field: str) -> float | None:
        vals = sorted(p[field] for p in self.by_geoid.values() if p.get(field) is not None)
        if not vals:
            return None
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    def correlation(self, field_a: str, field_b: str, min_rest_n: int = 5) -> dict | None:
        pairs = []
        for p in self.by_geoid.values():
            a, b = p.get(field_a), p.get(field_b)
            if a is None or b is None:
                continue
            if field_b == "rest_pct_below_A" and (p.get("rest_n") or 0) < min_rest_n:
                continue
            pairs.append((a, b))
        if len(pairs) < 10:
            return None
        ma = sum(x for x, _ in pairs) / len(pairs)
        mb = sum(y for _, y in pairs) / len(pairs)
        cov = sum((x - ma) * (y - mb) for x, y in pairs)
        va = sum((x - ma) ** 2 for x, _ in pairs)
        vb = sum((y - mb) ** 2 for _, y in pairs)
        r = cov / math.sqrt(va * vb) if va and vb else 0.0
        return {"field_a": field_a, "field_b": field_b, "r": round(r, 3), "n": len(pairs)}

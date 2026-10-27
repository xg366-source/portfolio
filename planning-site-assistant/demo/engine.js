/* Planning Site Assistant — static-site answer engine (no server, no API key).
   A faithful JavaScript port of src/answer.py + src/retriever.py +
   src/gis_query.py: same tokenizer (latin words + CJK chars/bigrams), same
   BM25 parameters (k1=1.5, b=0.75), same thresholds (score>=2.0 and
   coverage>=0.30), same GIS guardrails (ranking min_pop=2000, restaurant
   share min_n=10, correlation min_rest_n=5), same refusal text.
   Number formatting mirrors Python's float repr (45.0 stays "45.0") so the
   40-question eval answers match the Python engine verbatim.
   Pure logic, no DOM: usable in the browser and under node for testing. */
(function (root) {
  'use strict';

  function tokenize(text) {
    text = text.toLowerCase();
    const tokens = [];
    const latin = text.match(/[a-z0-9]+/g);
    if (latin) tokens.push(...latin);
    const runs = text.match(/[\u4e00-\u9fff]+/g) || [];
    for (const run of runs) {
      const chars = [...run];
      tokens.push(...chars);
      for (let i = 0; i < chars.length - 1; i++) tokens.push(chars[i] + chars[i + 1]);
    }
    return tokens;
  }

  function counter(tokens) {
    const c = new Map();
    for (const t of tokens) c.set(t, (c.get(t) || 0) + 1);
    return c;
  }

  function termCoverage(query, chunkText) {
    const q = new Set(tokenize(query));
    if (!q.size) return 0;
    const d = new Set(tokenize(chunkText));
    let hit = 0;
    q.forEach(t => { if (d.has(t)) hit++; });
    return hit / q.size;
  }

  // Python float repr for numbers: 45.0 -> "45.0", 4811 -> "4811".
  function pyFloat(v) {
    if (typeof v !== 'number') return String(v);
    const s = String(v);
    return (s.includes('.') || s.includes('e') || s.includes('E')) ? s : s + '.0';
  }
  function pyNum(v, isFloat) { return isFloat ? pyFloat(v) : String(v); }

  class BM25Index {
    constructor(chunks, k1 = 1.5, b = 0.75) {
      this.chunks = chunks;
      this.k1 = k1; this.b = b;
      this.docs = chunks.map(c => counter(tokenize(c.text)));
      this.lengths = this.docs.map(d => [...d.values()].reduce((a, x) => a + x, 0));
      this.avgLen = this.lengths.reduce((a, x) => a + x, 0) / Math.max(this.lengths.length, 1);
      const df = new Map();
      for (const d of this.docs) d.forEach((_, t) => df.set(t, (df.get(t) || 0) + 1));
      const n = chunks.length;
      this.idf = new Map();
      df.forEach((c, t) => this.idf.set(t, Math.log(1 + (n - c + 0.5) / (c + 0.5))));
    }
    search(query, topK = 5) {
      const q = tokenize(query);
      if (!q.length) return [];
      const qSet = [...new Set(q)];
      const scored = [];
      this.chunks.forEach((chunk, i) => {
        const counts = this.docs[i];
        const len = this.lengths[i];
        let score = 0;
        for (const term of qSet) {
          const f = counts.get(term) || 0;
          if (!f) continue;
          const denom = f + this.k1 * (1 - this.b + this.b * len / this.avgLen);
          score += (this.idf.get(term) || 0) * f * (this.k1 + 1) / denom;
        }
        if (score > 0) scored.push({ chunk, score: Math.round(score * 1000) / 1000 });
      });
      scored.sort((a, b) => b.score - a.score);
      return scored.slice(0, topK);
    }
  }

  const MIN_POP = 2000;
  const MIN_REST_N = 10;
  const LAYERS = {
    demographics: 'acs_demographics_expanded.geojson',
    requests_311: '311_by_tract_2026ytd.geojson',
    crime: 'crime_by_tract_2026ytd.geojson',
    food_safety: 'food_safety_by_tract.geojson',
  };
  const FIELD_SOURCE = {
    req_311_per_1000: '311_by_tract_2026ytd.geojson',
    crime_per_1000: 'crime_by_tract_2026ytd.geojson',
    crime_total: 'crime_by_tract_2026ytd.geojson',
    rest_pct_below_A: 'food_safety_by_tract.geojson',
    rest_n: 'food_safety_by_tract.geojson',
  };
  const FIELD_LABELS = {
    total_pop: '总人口', pct_hispanic: '西裔/拉丁裔占比(%)', pct_asian: '亚裔占比(%)',
    req_311_per_1000: '311投诉(每千人)', crime_per_1000: '报案数(每千人)',
    crime_total: '报案总数', rest_pct_below_A: '餐厅B级以下占比(%)', rest_n: '餐厅数',
  };
  const FLOAT_FIELDS = new Set(['pct_hispanic', 'pct_asian', 'req_311_per_1000',
    'crime_per_1000', 'rest_pct_below_A']);

  class GISLayers {
    // geojsons: { layerName: parsed FeatureCollection }
    constructor(geojsons) {
      this.byGeoid = {};
      this.sourceOf = {};
      for (const [layer, fname] of Object.entries(LAYERS)) {
        const gj = geojsons[layer];
        if (!gj) continue;
        for (const feat of gj.features) {
          const p = feat.properties;
          const geoid = p.GEOID;
          if (!this.byGeoid[geoid]) this.byGeoid[geoid] = {};
          for (const [k, v] of Object.entries(p)) {
            if (v !== null && v !== undefined) this.byGeoid[geoid][k] = v;
          }
          if (!(geoid in this.sourceOf)) this.sourceOf[geoid] = fname;
        }
      }
    }
    tractProfile(geoid) {
      const p = this.byGeoid[geoid];
      if (!p) return null;
      const values = {};
      for (const [k, v] of Object.entries(p)) {
        if (k === 'GEOID') continue;
        values[FIELD_LABELS[k] || k] = pyNum(v, FLOAT_FIELDS.has(k));
      }
      return { geoid, source: this.sourceOf[geoid], values };
    }
    _eligible(field, minPop) {
      let rows = Object.values(this.byGeoid).filter(
        p => p[field] !== undefined && p[field] !== null && (p.total_pop || 0) >= minPop);
      if (field === 'rest_pct_below_A') rows = rows.filter(p => (p.rest_n || 0) >= MIN_REST_N);
      return rows;
    }
    rankTop(field, minPop = MIN_POP) {
      const rows = this._eligible(field, minPop);
      if (!rows.length) return null;
      let top = rows[0];
      for (const r of rows) if (r[field] > top[field]) top = r;
      return { field, label: FIELD_LABELS[field] || field, geoid: top.GEOID,
        value: top[field], total_pop: top.total_pop, n_eligible: rows.length,
        min_pop: minPop, source: FIELD_SOURCE[field] || this.sourceOf[top.GEOID] };
    }
    median(field) {
      const vals = Object.values(this.byGeoid)
        .map(p => p[field]).filter(v => v !== undefined && v !== null).sort((a, b) => a - b);
      if (!vals.length) return null;
      const mid = Math.floor(vals.length / 2);
      return vals.length % 2 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
    }
    correlation(fieldA, fieldB, minRestN = 5) {
      const pairs = [];
      for (const p of Object.values(this.byGeoid)) {
        const a = p[fieldA], b = p[fieldB];
        if (a === undefined || a === null || b === undefined || b === null) continue;
        if (fieldB === 'rest_pct_below_A' && (p.rest_n || 0) < minRestN) continue;
        pairs.push([a, b]);
      }
      if (pairs.length < 10) return null;
      const ma = pairs.reduce((s, x) => s + x[0], 0) / pairs.length;
      const mb = pairs.reduce((s, x) => s + x[1], 0) / pairs.length;
      let cov = 0, va = 0, vb = 0;
      for (const [x, y] of pairs) { cov += (x - ma) * (y - mb); va += (x - ma) ** 2; vb += (y - mb) ** 2; }
      const r = (va && vb) ? cov / Math.sqrt(va * vb) : 0;
      return { field_a: fieldA, field_b: fieldB, r: Math.round(r * 1000) / 1000, n: pairs.length };
    }
  }

  const REFUSAL = '资料库中没有足够依据回答这个问题。我只能基于已收录的规划文件和 GIS 图层作答；如需回答，请先补充相关资料。';
  const GEOID_RE = /\d{11}/;
  const RANK_PATTERNS = [
    [['311', '最高'], 'req_311_per_1000', 'rank'],
    [['报案', '最高'], 'crime_per_1000', 'rank'],
    [['犯罪', '最高'], 'crime_per_1000', 'rank'],
    [['西裔', '占比', '最高'], 'pct_hispanic', 'rank'],
    [['b级以下', '最高'], 'rest_pct_below_A', 'rank'],
    [['报案', '中位'], 'crime_per_1000', 'median'],
    [['311', '中位'], 'req_311_per_1000', 'median'],
  ];

  class AnswerEngine {
    constructor(chunks, geojsons, opts = {}) {
      this.chunks = chunks;
      this.index = new BM25Index(chunks);
      this.gis = new GISLayers(geojsons);
      this.topK = opts.topK || 5;
      this.minScore = opts.minScore !== undefined ? opts.minScore : 2.0;
      this.minCoverage = opts.minCoverage !== undefined ? opts.minCoverage : 0.30;
    }
    _ok(text, citations, route, score) {
      return { answer: text, citations, refused: false, route, score: score ?? null,
        mode: 'extractive-demo' };
    }
    _refuse(reason) {
      return { answer: REFUSAL, citations: [], refused: true, route: 'refusal',
        score: null, mode: 'extractive-demo', reason };
    }
    _tryGis(q) {
      const m = q.match(GEOID_RE);
      const qLower = q.toLowerCase();
      if (m && (q.includes('这个') || q.includes('该') || qLower.includes('tract') ||
          q.includes('人口') || q.includes('占比'))) {
        const prof = this.gis.tractProfile(m[0]);
        if (prof) {
          const lines = Object.entries(prof.values).map(([k, v]) => `${k}：${v}`);
          return this._ok(lines.join('；'), [`${prof.source} · GEOID ${prof.geoid}`], 'gis_profile');
        }
      }
      if (q.includes('相关') && q.includes('西裔') && (q.includes('餐厅') || qLower.includes('b级'))) {
        const c = this.gis.correlation('pct_hispanic', 'rest_pct_below_A');
        if (c) {
          const verdict = Math.abs(c.r) < 0.2 ? '不支持' : '存在相关';
          const text = `对 ${c.n} 个餐厅数≥5 的 tract 计算：西裔占比与餐厅 B 级以下占比的相关系数 r = ${pyFloat(c.r)}，数据${verdict}“西裔占比越高、餐厅评级越差”的说法。`;
          return this._ok(text,
            ['food_safety_by_tract.geojson + acs_demographics_expanded.geojson · 相关分析'],
            'gis_correlation');
        }
      }
      for (const [keywords, field, mode] of RANK_PATTERNS) {
        if (!keywords.every(k => qLower.includes(k))) continue;
        if (mode === 'rank') {
          const r = this.gis.rankTop(field);
          if (r) {
            const text = `在人口≥${r.min_pop} 的 ${r.n_eligible} 个 tract 中，${r.label}最高的是 GEOID ${r.geoid}，为 ${pyNum(r.value, true)}（该 tract 人口 ${r.total_pop}）。注：小人口 tract 的每千人比率会被放大，故设人口门槛，口径见 data_notes。`;
            return this._ok(text, [`${r.source} · GEOID ${r.geoid}`], 'gis_rank');
          }
        } else {
          const v = this.gis.median(field);
          if (v !== null && v !== undefined) {
            const src = FIELD_SOURCE[field] || 'acs_demographics_expanded.geojson';
            const rounded = Math.round(v * 10) / 10;
            return this._ok(`${field} 的 tract 中位数为 ${pyFloat(rounded)}（每千人）。`,
              [`${src} · 全 113 tract`], 'gis_median');
          }
        }
      }
      return null;
    }
    _tryDocs(q) {
      const hits = this.index.search(q, this.topK);
      if (!hits.length) return this._refuse('no_hits');
      const top = hits[0];
      const coverage = termCoverage(q, top.chunk.text);
      if (top.score < this.minScore || coverage < this.minCoverage) {
        return this._refuse(`weak_retrieval score=${top.score} coverage=${Math.round(coverage * 100) / 100}`);
      }
      const citations = hits.map(h => `${h.chunk.doc} · ${h.chunk.section}`);
      const body = hits.slice(0, 2).map(h => h.chunk.text).join(' ');
      return this._ok(body, citations, 'docs', top.score);
    }
    ask(question) {
      return this._tryGis(question) || this._tryDocs(question);
    }
  }

  const api = { tokenize, termCoverage, BM25Index, GISLayers, AnswerEngine,
    REFUSAL, FIELD_LABELS, LAYERS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SiteAssistant = api;
})(typeof window !== 'undefined' ? window : globalThis);

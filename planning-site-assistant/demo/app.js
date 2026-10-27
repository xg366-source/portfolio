/* UI wiring for the static demo: loads data, builds the engine, draws the
   Leaflet choropleth and renders the Q&A log. No server calls at all. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const FILES = window.SiteAssistant.LAYERS;
  const FIELD_NAMES = {
    pct_hispanic: '西裔占比(%)', req_311_per_1000: '311投诉(每千人)',
    crime_per_1000: '报案数(每千人)', rest_pct_below_A: '餐厅B级以下占比(%)',
  };

  const map = L.map('map').setView([40.755, -73.885], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    { attribution: '© OpenStreetMap contributors' }).addTo(map);

  let engine = null, layerGroup = null, geoCache = {};
  const logEl = $('log');

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function addMsg(html, cls) {
    const div = document.createElement('div');
    div.className = 'msg ' + (cls || '');
    div.innerHTML = html;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function colorFor(v, max) {
    const t = max ? (v || 0) / max : 0;
    return `rgba(228,87,46,${(0.15 + 0.65 * t).toFixed(2)})`;
  }

  async function draw(field) {
    const gj = geoCache[field] || await (await fetch('data/' + FILES[
      field === 'pct_hispanic' ? 'demographics'
      : field === 'req_311_per_1000' ? 'requests_311'
      : field === 'crime_per_1000' ? 'crime'
      : 'food_safety')).json();
    geoCache[field] = gj;
    const vals = gj.features.map(f => f.properties[field]).filter(v => v != null);
    const max = Math.max(...vals);
    if (layerGroup) layerGroup.remove();
    layerGroup = L.geoJSON(gj, {
      style: f => ({ color: '#666', weight: 0.5,
        fillColor: colorFor(f.properties[field], max), fillOpacity: 1 }),
      onEachFeature: (f, l) => l.bindPopup(
        `GEOID ${f.properties.GEOID}<br>${FIELD_NAMES[field]}：${f.properties[field] ?? '—'}`),
    }).addTo(map);
  }

  function ask(q) {
    if (!engine) { addMsg('数据还在加载，稍等一下再问。', 'refused'); return; }
    if (!q) return;
    addMsg(`<b>问：</b>${esc(q)}`);
    const res = engine.ask(q);
    const cites = res.citations.length
      ? `<div class="cite">来源：${esc(res.citations.join('；'))}</div>` : '';
    const meta = `<div class="cite">路线：${res.route} · 抽取式演示模式（无 LLM key，直接返回检索原文 + 引用）</div>`;
    addMsg(`${esc(res.answer)}${cites}${meta}`, res.refused ? 'refused' : '');
    const m = q.match(/\d{11}/);
    if (m && layerGroup) layerGroup.eachLayer(l => {
      if (l.feature.properties.GEOID === m[0]) { l.openPopup(); map.fitBounds(l.getBounds()); }
    });
  }

  async function init() {
    try {
      const chunks = await (await fetch('data/chunks.json')).json();
      const geojsons = {};
      for (const [layer, fname] of Object.entries(FILES)) {
        geojsons[layer] = await (await fetch('data/' + fname)).json();
      }
      engine = new window.SiteAssistant.AnswerEngine(chunks, geojsons);
      geoCache = {
        pct_hispanic: geojsons.demographics, req_311_per_1000: geojsons.requests_311,
        crime_per_1000: geojsons.crime, rest_pct_below_A: geojsons.food_safety,
      };
      $('send').disabled = false;
      $('status').textContent = '已加载：2 份规划文件（7 个引用块）+ 4 个 GIS 图层（113 个 tract），全部在浏览器本地运行。';
      draw('pct_hispanic');
      addMsg('你好，我是这个基地的问答助手。试试下面这些问题，或者直接输入你自己的问题——资料库外的事我会明确说不知道。');
    } catch (e) {
      $('status').textContent = '数据加载失败：' + e.message;
    }
  }

  $('send').onclick = () => { const v = $('q').value.trim(); $('q').value = ''; ask(v); };
  $('q').onkeydown = e => { if (e.key === 'Enter') $('send').click(); };
  $('layer').onchange = e => draw(e.target.value);
  document.querySelectorAll('[data-q]').forEach(b =>
    b.onclick = () => ask(b.getAttribute('data-q')));
  init();
})();

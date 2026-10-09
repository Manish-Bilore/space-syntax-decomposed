/* Space Syntax, decomposed: interactive dashboard.
   Data: dashboard/data/index.json + <site>.json (scripts/14_export_web.py).
   Values are percentile ranks 0-99 within each site (-1 = missing). */
(function () {
  "use strict";

  const DATA = "dashboard/data/";
  // sequential ramp (validated blue); on dark backgrounds it runs dark to light so high values glow
  const SEQ_LIGHT = ["#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"];
  const SEQ_DARK = ["#1a3556", "#1c5cab", "#2a78d6", "#5598e7", "#9ec5f4"];
  const SEQ_W = [0.6, 0.9, 1.3, 1.9, 2.8];
  const DIV7 = ["#104281", "#2a78d6", "#9ec5f4", "#c9c8c3", "#f2b8b5", "#e34948", "#a32a2a"];
  const DIV7_DARK = ["#5598e7", "#2a78d6", "#1c5cab", "#48484a", "#8f2a2a", "#e34948", "#ff8a80"];
  const DIV_W = [2.6, 1.7, 1.0, 0.45, 1.0, 1.7, 2.6];
  const TILES = {
    // Esri Light / Dark Gray Canvas (no API key; attribution required)
    light: ["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"],
    dark: ["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"],
  };
  const BASE_ATTR = "Basemap © Esri, HERE, Garmin, © OpenStreetMap contributors · Streets © OpenStreetMap contributors (ODbL)";
  const BASE_OP = () => (dark ? 0.85 : 0.9);
  const MEASURES = [
    { id: "S0_harmonic", label: "S0 · junction graph, metric harmonic", fam: "closeness", r: true },
    { id: "S1_harmonic", label: "S1 · segment graph, metric harmonic", fam: "closeness", r: true },
    { id: "S1_hillier", label: "S1 · segment graph, metric NC²/TD", fam: "closeness", r: true },
    { id: "S2_hillier", label: "S2 · angular NC²/TD (cityseer)", fam: "closeness", r: true },
    { id: "S3_integration", label: "S3 · angular integration (depthmapX)", fam: "closeness", r: true },
    { id: "S3_nain", label: "S3 · NAIN", fam: "closeness", r: true },
    { id: "S0_betweenness", label: "S0 · junction graph, metric betweenness", fam: "betweenness", r: true },
    { id: "S1_betweenness", label: "S1 · segment graph, metric betweenness", fam: "betweenness", r: true },
    { id: "S2_betweenness", label: "S2 · angular betweenness (cityseer)", fam: "betweenness", r: true },
    { id: "S3_choice", label: "S3 · angular choice (depthmapX)", fam: "betweenness", r: true },
    { id: "S3_nach", label: "S3 · NACH", fam: "betweenness", r: true },
    { id: "S4_connectivity", label: "S4 · axial connectivity", fam: "axial", r: false },
    { id: "S4_integration_hh_Rn", label: "S4 · axial integration, radius n", fam: "axial", r: false },
    { id: "S4_integration_hh_R3", label: "S4 · axial integration, radius 3", fam: "axial", r: false },
    { id: "S4_choice_Rn", label: "S4 · axial choice, radius n", fam: "axial", r: false },
    { id: "S4_choice_R3", label: "S4 · axial choice, radius 3", fam: "axial", r: false },
  ];
  const PRESETS = [
    ["", "None"],
    ["S0_harmonic|S1_harmonic", "Junction vs segment (closeness)"],
    ["S1_harmonic|S1_hillier", "Harmonic vs NC²/TD"],
    ["S1_hillier|S2_hillier", "Metric vs angular (closeness)"],
    ["S2_hillier|S3_integration", "cityseer vs depthmapX (closeness)"],
    ["S3_integration|S3_nain", "NC²/TD vs NAIN"],
    ["S1_harmonic|S3_nain", "End to end: metric closeness vs NAIN"],
    ["S1_betweenness|S2_betweenness", "Metric vs angular (betweenness)"],
    ["S2_betweenness|S3_choice", "cityseer vs depthmapX (betweenness)"],
    ["S3_choice|S3_nach", "Choice vs NACH"],
    ["S1_betweenness|S3_nach", "End to end: metric betweenness vs NACH"],
    ["S4_choice_Rn|S3_nach", "Axial choice vs NACH"],
    ["S4_integration_hh_R3|S3_nain", "Axial integration R3 vs NAIN"],
  ];
  const byId = Object.fromEntries(MEASURES.map((m) => [m.id, m]));
  const $ = (s) => document.querySelector(s);
  const state = { site: null, a: "S3_nain", b: "S1_harmonic", mode: "one", r: 800 };
  const cache = {};
  let index, map, cur, dark = false, ready = false;

  const isDark = () => document.body.classList.contains("quarto-dark");
  const seq = () => (dark ? SEQ_DARK : SEQ_LIGHT);
  const div = () => (dark ? DIV7_DARK : DIV7);
  const key = (id, r) => (byId[id].r ? `${id}_${r}` : id);
  const values = (id) => (cur ? cur.doc.measures[key(id, state.r)] || null : null);
  const short = (id) => byId[id].label.replace(/^S\d · /, "").replace(/\s*\(.*\)/, "") + (byId[id].r ? ` · R${state.r}` : "");
  const status = (msg) => { const s = $("#dash-status"); if (!msg) { s.hidden = true; return; }
    s.hidden = false; s.querySelector("span").textContent = msg; };

  function decode(doc) {
    const q = doc.meta.q;
    const feats = doc.lines.map((parts, i) => {
      const coords = parts.map((d) => {
        const out = []; let x = 0, y = 0;
        for (let k = 0; k < d.length; k += 2) { x += d[k]; y += d[k + 1]; out.push([x / q, y / q]); }
        return out;
      });
      return { type: "Feature", id: i, properties: { i, c: -1 },
        geometry: coords.length === 1 ? { type: "LineString", coordinates: coords[0] }
                                      : { type: "MultiLineString", coordinates: coords } };
    });
    return { type: "FeatureCollection", features: feats };
  }

  async function loadSite(site) {
    if (!cache[site]) {
      status("Loading " + index.sites.find((s) => s.site === site).label + "…");
      const doc = await (await fetch(DATA + site + ".json")).json();
      cache[site] = { doc, fc: decode(doc) };
    }
    status(null);
    return cache[site];
  }

  // ---------------------------------------------------------------- statistics and classes
  function rankCorr(a, b) {
    const xs = [], ys = [];
    for (let i = 0; i < a.length; i++) if (a[i] >= 0 && b[i] >= 0) { xs.push(a[i]); ys.push(b[i]); }
    const n = xs.length; if (n < 3) return [NaN, n];
    const rank = (v) => { const o = v.map((x, i) => [x, i]).sort((p, q) => p[0] - q[0]);
      const r = new Array(n); let i = 0;
      while (i < n) { let j = i; while (j + 1 < n && o[j + 1][0] === o[i][0]) j++;
        for (let k = i; k <= j; k++) r[o[k][1]] = (i + j) / 2; i = j + 1; } return r; };
    const rx = rank(xs), ry = rank(ys), m = (n - 1) / 2;
    let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) { const dx = rx[i] - m, dy = ry[i] - m; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; }
    return [sxy / Math.sqrt(sxx * syy), n];
  }

  function classify() {
    const A = values(state.a), B = state.mode === "compare" ? values(state.b) : null;
    for (const f of cur.fc.features) {
      const i = f.id; let c = -1;
      if (A && A[i] >= 0) {
        if (!B) c = Math.min(4, Math.floor(A[i] / 20));
        else if (B[i] >= 0) {
          const d = A[i] - B[i];
          c = 10 + (d <= -50 ? 0 : d <= -25 ? 1 : d < -10 ? 2 : d <= 10 ? 3 : d < 25 ? 4 : d < 50 ? 5 : 6);
        }
      }
      f.properties.c = c;
    }
  }

  // ---------------------------------------------------------------- map
  function colorExpr() {
    const e = ["match", ["get", "c"]];
    seq().forEach((col, k) => e.push(k, col));
    div().forEach((col, k) => e.push(10 + k, col));
    e.push(dark ? "#3a3a3c" : "#e6e5e1"); return e;
  }
  function widthExpr(scale) {
    const e = ["match", ["get", "c"]];
    SEQ_W.forEach((w, k) => e.push(k, w * scale));
    DIV_W.forEach((w, k) => e.push(10 + k, w * scale));
    e.push(0.3 * scale); return e;
  }
  const zoomWidth = (f = 1) => ["interpolate", ["exponential", 1.6], ["zoom"], 10, widthExpr(0.45 * f), 14, widthExpr(1.1 * f), 17, widthExpr(2.4 * f)];

  function initMap() {
    map = new maplibregl.Map({
      container: "dash-map", attributionControl: { compact: true },
      style: { version: 8, sources: {
          base: { type: "raster", tileSize: 256, maxzoom: 16, tiles: TILES[dark ? "dark" : "light"],
            attribution: BASE_ATTR } },
        layers: [{ id: "bg", type: "background", paint: { "background-color": dark ? "#000000" : "#fbfbfd" } },
                 { id: "base", type: "raster", source: "base", paint: { "raster-opacity": BASE_OP() } }] },
      center: [0, 0], zoom: 1, dragRotate: false, pitchWithRotate: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");
    map.on("load", () => {
      map.addSource("streets", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "streets", type: "line", source: "streets",
        layout: { "line-cap": "round", "line-join": "round",
                  "line-sort-key": ["case", [">=", ["get", "c"], 10], ["abs", ["-", ["get", "c"], 13]], ["get", "c"]] },
        paint: { "line-color": colorExpr(), "line-width": zoomWidth() } });
      map.addLayer({ id: "hover", type: "line", source: "streets", filter: ["==", ["id"], -1],
        layout: { "line-cap": "round" },
        paint: { "line-color": "#ff9f0a", "line-width": ["interpolate", ["linear"], ["zoom"], 10, 3, 17, 9], "line-opacity": 0.9 } });
      map.addSource("windows", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "windows", type: "line", source: "windows",
        paint: { "line-color": "#e34948", "line-width": 1.5, "line-dasharray": [3, 2] } });
      ready = true;
      if (isDark() !== dark) applyTheme();
      setSite(state.site, true);
    });
    const tip = $("#dash-tip");
    map.on("mousemove", "streets", (e) => {
      const i = e.features[0].id;
      map.setFilter("hover", ["==", ["id"], i]);
      const A = values(state.a), B = values(state.b);
      const fmt = (v) => (v == null || v < 0 ? "n/a" : `<span class="v">${v}</span>th percentile`);
      let h = `<b>${short(state.a)}</b><br>${fmt(A && A[i])}`;
      if (state.mode === "compare") h += `<br><b>${short(state.b)}</b><br>${fmt(B && B[i])}`;
      tip.innerHTML = h; tip.style.display = "block";
      const W = map.getContainer().clientWidth;
      tip.style.left = Math.min(e.point.x + 14, W - 240) + "px"; tip.style.top = e.point.y + 14 + "px";
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "streets", () => { tip.style.display = "none"; map.setFilter("hover", ["==", ["id"], -1]); map.getCanvas().style.cursor = ""; });
  }

  function applyTheme() {
    dark = isDark();
    if (!map || !ready) return;
    map.setPaintProperty("bg", "background-color", dark ? "#000000" : "#fbfbfd");
    
    const vis = map.getLayoutProperty("base", "visibility") || "visible";
    map.removeLayer("base"); map.removeSource("base");
    map.addSource("base", { type: "raster", tileSize: 256, maxzoom: 16, tiles: TILES[dark ? "dark" : "light"],
      attribution: BASE_ATTR });
    map.addLayer({ id: "base", type: "raster", source: "base", layout: { visibility: vis },
      paint: { "raster-opacity": BASE_OP() } }, "streets");
    map.setPaintProperty("streets", "line-color", colorExpr());
    if (cur) { legend(); scatter(); agreementChart(); }
  }

  // ---------------------------------------------------------------- panels
  function legend() {
    const el = $("#dash-legend");
    if (state.mode === "one") {
      el.innerHTML = `<div class="lg-title">${short(state.a)}</div>
        <div class="lg-bar">${seq().map((c) => `<i style="background:${c}"></i>`).join("")}</div>
        <div class="lg-ends"><span>low percentile</span><span>high</span></div>`;
    } else {
      el.innerHTML = `<div class="lg-title">A − B: ${short(state.a)} minus ${short(state.b)}</div>
        <div class="lg-bar">${div().map((c) => `<i style="background:${c}"></i>`).join("")}</div>
        <div class="lg-ends"><span>B ranks higher</span><span>agree</span><span>A ranks higher</span></div>`;
    }
  }

  function scatter() {
    const cv = $("#dash-scatter"), ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height, P = 8;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = dark ? "#1c1c1e" : "#f5f5f7"; ctx.fillRect(0, 0, W, H);
    const A = values(state.a), B = values(state.mode === "compare" ? state.b : state.b);
    const out = $("#dash-rho");
    if (!A || !B) { out.innerHTML = `<span class="muted">Not available for this study area.</span>`; return; }
    const N = 40, grid = new Float32Array(N * N); let max = 0;
    for (let i = 0; i < A.length; i++) if (A[i] >= 0 && B[i] >= 0) {
      const gx = Math.min(N - 1, Math.floor(B[i] * N / 100)), gy = Math.min(N - 1, Math.floor(A[i] * N / 100));
      const v = ++grid[gy * N + gx]; if (v > max) max = v;
    }
    const accent = dark ? [41, 151, 255] : [0, 113, 227];
    const cw = (W - 2 * P) / N, ch = (H - 2 * P) / N;
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const v = grid[y * N + x]; if (!v) continue;
      ctx.fillStyle = `rgba(${accent.join(",")},${(0.08 + 0.92 * Math.sqrt(v / max)).toFixed(3)})`;
      ctx.beginPath(); ctx.roundRect(P + x * cw + 1, H - P - (y + 1) * ch + 1, cw - 2, ch - 2, 3); ctx.fill();
    }
    ctx.strokeStyle = dark ? "rgba(255,255,255,.35)" : "rgba(0,0,0,.25)"; ctx.setLineDash([6, 6]); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(P, H - P); ctx.lineTo(W - P, P); ctx.stroke(); ctx.setLineDash([]);
    const [rho, n] = rankCorr(A, B);
    out.innerHTML = `<b>ρ ${rho.toFixed(2)}</b><span class="muted">Spearman, ${n.toLocaleString()} streets</span>
      <div class="ab"><span class="k">A</span>${short(state.a)}</div><div class="ab"><span class="k">B</span>${short(state.b)}</div>`;
  }

  function agreementChart() {
    const el = $("#dash-agree");
    const fam = byId[state.a].fam === "axial" ? byId[state.b].fam : byId[state.a].fam;
    const rows = (cur.doc.tables.agreement || []).filter((r) => r.family === fam);
    if (!rows.length || fam === "axial") { el.innerHTML = "<p class='muted small'>Pick a closeness or betweenness measure.</p>"; return; }
    const steps = [...new Set(rows.map((r) => r.step))];
    const radii = [...new Set(rows.map((r) => r.radius))].sort((a, b) => a - b);
    const W = 340, H = 190, L = 28, R = 26, T = 10, B = 22;
    const x = (r) => L + (radii.indexOf(r) / Math.max(1, radii.length - 1)) * (W - L - R);
    const y = (v) => T + (1 - (v + 0.2) / 1.2) * (H - T - B);
    const pal = ["#0071e3", "#ff9f0a", "#30d158", "#bf5af2", "#ff375f", "#8e8e93"];
    const sel = `${state.a}|${state.b}`;
    let s = `<svg viewBox="0 0 ${W} ${H}" class="agree-svg" role="img" aria-label="Rank agreement by radius">`;
    [0, 0.5, 1].forEach((v) => { s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${L - 6}" y="${y(v) + 3}" text-anchor="end">${v}</text>`; });
    radii.forEach((r) => { s += `<text x="${x(r)}" y="${H - 6}" text-anchor="middle">${r} m</text>`; });
    let leg = "";
    steps.forEach((st, k) => {
      const pts = radii.map((r) => rows.find((q) => q.step === st && q.radius === r)).filter(Boolean);
      const pair = pts.length ? pts[0].a.replace(/_\d+$/, "") + "|" + pts[0].b.replace(/_\d+$/, "") : "";
      const on = pair === sel && state.mode === "compare";
      const dim = state.mode === "compare" && !on;
      const col = pal[k % pal.length];
      s += `<polyline fill="none" stroke="${col}" stroke-width="${on ? 3.4 : 1.8}" stroke-linejoin="round" opacity="${dim ? 0.3 : 1}" points="${pts.map((p) => x(p.radius) + "," + y(p.spearman)).join(" ")}"/>`;
      pts.forEach((p) => { s += `<circle cx="${x(p.radius)}" cy="${y(p.spearman)}" r="${on ? 4 : 2.6}" fill="${col}" opacity="${dim ? 0.3 : 1}"><title>${st}, R${p.radius}: ρ ${p.spearman.toFixed(2)}</title></circle>`; });
      leg += `<div class="agree-leg ${on ? "on" : ""}"><i style="background:${col}"></i>${st.replace(/^[^:]*: /, "").replace(/ -> /g, " vs ").replace(/ to /g, " vs ").replace(/NC\^2/g, "NC²")}</div>`;
    });
    el.innerHTML = s + `</svg><div class="agree-legs">${leg}</div><div class="muted small" style="margin-top:6px">Spearman ρ between adjacent rungs, ${fam}.</div>`;
  }

  function windowsPanel() {
    const el = $("#dash-windows");
    const ws = cur.doc.meta.windows || [];
    const stats = (index.windows || []).filter((w) => w.site === state.site);
    el.innerHTML = ws.map((w) => {
      const st = stats.find((s) => s.window === w.key);
      const info = st ? `${st.streets.toLocaleString()} streets · ${st.network_km_per_km2.toFixed(1)} km/km²` : "";
      return `<button class="pill window" data-k="${w.key}">${w.name.split(",")[0]}${info ? `<small>${info}</small>` : ""}</button>`;
    }).join("") + `<button class="pill" data-k="__all">Whole area</button>`;
    el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const k = b.dataset.k;
      const bb = k === "__all" ? cur.doc.meta.bounds : ws.find((w) => w.key === k).bounds;
      map.fitBounds([[bb[0], bb[1]], [bb[2], bb[3]]], { padding: 24, duration: 900 });
    }));
    map.getSource("windows").setData({ type: "FeatureCollection", features: ws.map((w) => {
      const [a, b, c, d] = w.bounds;
      return { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[a, b], [c, b], [c, d], [a, d], [a, b]] } };
    }) });
  }

  function header() {
    const m = cur.doc.meta;
    const name = m.label.replace(/\s*\(.*\)/, ""), net = (m.label.match(/\((.*)\)/) || [])[1];
    $("#dash-head").innerHTML = `<span class="t">${name}</span>` + (net ? `<span class="chip">${net}</span>` : "") +
      `<span class="chip">${m.streets.toLocaleString()} streets</span><span class="chip">${m.km_per_km2} km/km²</span>`;
  }

  function syncControls() {
    document.querySelectorAll("#dash-mode button").forEach((b) => b.classList.toggle("on", b.dataset.v === state.mode));
    $("#dash-b-row").hidden = state.mode !== "compare";
    $("#dash-a-label").textContent = state.mode === "compare" ? "Measure A" : "Measure";
    const radial = byId[state.a].r || (state.mode === "compare" && byId[state.b].r);
    document.querySelectorAll("#dash-radius button").forEach((b) => { b.classList.toggle("on", +b.dataset.v === state.r); b.disabled = !radial; });
    $("#dash-a").value = state.a; $("#dash-b").value = state.b;
  }

  function redraw() {
    if (!cur) return;
    classify();
    map.getSource("streets").setData(cur.fc);
    syncControls(); legend(); scatter(); agreementChart();
  }

  async function setSite(site, fit) {
    state.site = site;
    cur = await loadSite(site);
    const radii = cur.doc.meta.radii;
    if (!radii.includes(state.r)) state.r = radii.includes(800) ? 800 : radii[0];
    $("#dash-radius").innerHTML = radii.map((r) => `<button role="tab" data-v="${r}">${r}</button>`).join("");
    $("#dash-radius").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { state.r = +b.dataset.v; redraw(); }));
    header(); windowsPanel(); redraw();
    if (fit) { const b = cur.doc.meta.bounds; map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 24, duration: 0 }); }
  }

  // ---------------------------------------------------------------- controls
  function options(sel, val) {
    const groups = { closeness: "Closeness family", betweenness: "Betweenness family", axial: "Axial lines (S4, no radius)" };
    sel.innerHTML = Object.entries(groups).map(([g, lab]) => `<optgroup label="${lab}">` +
      MEASURES.filter((m) => m.fam === g).map((m) => `<option value="${m.id}" ${m.id === val ? "selected" : ""}>${m.label}</option>`).join("") + "</optgroup>").join("");
  }

  async function start() {
    dark = isDark();
    index = await (await fetch(DATA + "index.json")).json();
    const ss = $("#dash-site");
    ss.innerHTML = index.sites.map((s) => `<option value="${s.site}">${s.label}</option>`).join("");
    state.site = index.sites[0].site;
    options($("#dash-a"), state.a); options($("#dash-b"), state.b);
    $("#dash-preset").innerHTML = PRESETS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
    ss.addEventListener("change", () => setSite(ss.value, true));
    $("#dash-a").addEventListener("change", (e) => { state.a = e.target.value; $("#dash-preset").value = ""; redraw(); });
    $("#dash-b").addEventListener("change", (e) => { state.b = e.target.value; $("#dash-preset").value = ""; redraw(); });
    document.querySelectorAll("#dash-mode button").forEach((b) => b.addEventListener("click", () => { state.mode = b.dataset.v; redraw(); }));
    $("#dash-preset").addEventListener("change", (e) => {
      if (!e.target.value) return;
      const [a, b] = e.target.value.split("|");
      Object.assign(state, { a, b, mode: "compare" }); redraw();
    });
    $("#dash-base").addEventListener("change", (e) => map.setLayoutProperty("base", "visibility", e.target.checked ? "visible" : "none"));
    new MutationObserver(() => { if (isDark() !== dark) applyTheme(); }).observe(document.body, { attributes: true, attributeFilter: ["class"] });
    initMap();
  }

  document.addEventListener("DOMContentLoaded", () => start().catch((err) => {
    status("Could not load the dashboard data (" + err.message + "). Serve the site over http, e.g. quarto preview.");
    document.querySelector("#dash-status .spin").remove();
  }));
})();

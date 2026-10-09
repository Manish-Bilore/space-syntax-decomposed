/* Space Syntax, decomposed: interactive dashboard.
   Data: dashboard/data/index.json + <site>.json (scripts/14_export_web.py).
   Values are percentile ranks 0-99 within each site (-1 = missing). */
(function () {
  "use strict";

  const DATA = "dashboard/data/";
  const SEQ5 = ["#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"];
  const SEQ_W = [0.6, 0.9, 1.3, 1.9, 2.8];
  const DIV7 = ["#104281", "#2a78d6", "#9ec5f4", "#c9c8c3", "#f2b8b5", "#e34948", "#a32a2a"];
  const DIV_W = [2.6, 1.7, 1.0, 0.5, 1.0, 1.7, 2.6];
  const MEASURES = [
    { id: "S0_harmonic", label: "S0 junction graph, metric harmonic closeness", fam: "closeness", r: true },
    { id: "S1_harmonic", label: "S1 segment graph, metric harmonic closeness", fam: "closeness", r: true },
    { id: "S1_hillier", label: "S1 segment graph, metric NC²/TD", fam: "closeness", r: true },
    { id: "S2_hillier", label: "S2 angular NC²/TD (cityseer)", fam: "closeness", r: true },
    { id: "S3_integration", label: "S3 angular integration (depthmapX)", fam: "closeness", r: true },
    { id: "S3_nain", label: "S3 NAIN", fam: "closeness", r: true },
    { id: "S0_betweenness", label: "S0 junction graph, metric betweenness", fam: "betweenness", r: true },
    { id: "S1_betweenness", label: "S1 segment graph, metric betweenness", fam: "betweenness", r: true },
    { id: "S2_betweenness", label: "S2 angular betweenness (cityseer)", fam: "betweenness", r: true },
    { id: "S3_choice", label: "S3 angular choice (depthmapX)", fam: "betweenness", r: true },
    { id: "S3_nach", label: "S3 NACH", fam: "betweenness", r: true },
    { id: "S4_connectivity", label: "S4 axial connectivity", fam: "axial", r: false },
    { id: "S4_integration_hh_Rn", label: "S4 axial integration HH, radius n", fam: "axial", r: false },
    { id: "S4_integration_hh_R3", label: "S4 axial integration HH, radius 3", fam: "axial", r: false },
    { id: "S4_choice_Rn", label: "S4 axial choice, radius n", fam: "axial", r: false },
    { id: "S4_choice_R3", label: "S4 axial choice, radius 3", fam: "axial", r: false },
  ];
  const PRESETS = [
    ["", "Pick a comparison…"],
    ["S0_harmonic|S1_harmonic", "Representation: junction vs segment (closeness)"],
    ["S1_harmonic|S1_hillier", "Closeness form: harmonic vs NC²/TD"],
    ["S1_hillier|S2_hillier", "Cost: metric vs angular (closeness)"],
    ["S2_hillier|S3_integration", "Engine: cityseer vs depthmapX (closeness)"],
    ["S3_integration|S3_nain", "Normalisation: NC²/TD vs NAIN"],
    ["S1_harmonic|S3_nain", "End to end: metric harmonic vs NAIN"],
    ["S1_betweenness|S2_betweenness", "Cost: metric vs angular (betweenness)"],
    ["S2_betweenness|S3_choice", "Engine: cityseer vs depthmapX (betweenness)"],
    ["S3_choice|S3_nach", "Normalisation: choice vs NACH"],
    ["S1_betweenness|S3_nach", "End to end: metric betweenness vs NACH"],
    ["S4_choice_Rn|S3_nach", "Axial choice vs angular NACH"],
    ["S4_integration_hh_R3|S3_nain", "Axial integration R3 vs NAIN"],
  ];
  const byId = Object.fromEntries(MEASURES.map((m) => [m.id, m]));
  const $ = (s) => document.querySelector(s);
  const state = { site: null, a: "S3_nain", b: "S1_harmonic", mode: "one", r: 800, basemap: true };
  const cache = {};
  let index, map, fc, cur;

  function key(id, r) { return byId[id].r ? `${id}_${r}` : id; }
  function values(id) { return cur.doc.measures[key(id, state.r)] || null; }

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
      $("#dash-status").textContent = "loading " + site + "…";
      const doc = await (await fetch(DATA + site + ".json")).json();
      cache[site] = { doc, fc: decode(doc) };
      $("#dash-status").textContent = "";
    }
    return cache[site];
  }

  // ---------------------------------------------------------------- classes and statistics
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
    const feats = cur.fc.features;
    for (let i = 0; i < feats.length; i++) {
      let c = -1;
      if (A && A[i] >= 0) {
        if (!B) c = Math.min(4, Math.floor(A[i] / 20));
        else if (B[i] >= 0) {
          const d = A[i] - B[i];
          c = 10 + (d <= -50 ? 0 : d <= -25 ? 1 : d < -10 ? 2 : d <= 10 ? 3 : d < 25 ? 4 : d < 50 ? 5 : 6);
        }
      }
      feats[i].properties.c = c;
    }
  }

  // ---------------------------------------------------------------- map
  function colorExpr() {
    const e = ["match", ["get", "c"]];
    SEQ5.forEach((col, k) => e.push(k, col));
    DIV7.forEach((col, k) => e.push(10 + k, col));
    e.push("#e6e5e1"); return e;
  }
  function widthExpr(scale) {
    const e = ["match", ["get", "c"]];
    SEQ_W.forEach((w, k) => e.push(k, w * scale));
    DIV_W.forEach((w, k) => e.push(10 + k, w * scale));
    e.push(0.3 * scale); return e;
  }
  function sortExpr() { // strongest classes on top
    return ["case", [">=", ["get", "c"], 10], ["abs", ["-", ["get", "c"], 13]], ["get", "c"]];
  }

  function initMap() {
    map = new maplibregl.Map({
      container: "dash-map", attributionControl: { compact: true },
      style: { version: 8, sources: {
          base: { type: "raster", tileSize: 256, maxzoom: 19,
            tiles: ["https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                    "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"],
            attribution: "© OpenStreetMap contributors © CARTO" } },
        layers: [{ id: "bg", type: "background", paint: { "background-color": "#fcfcfb" } },
                 { id: "base", type: "raster", source: "base", paint: { "raster-opacity": 0.55 } }] },
      center: [0, 0], zoom: 1, maxPitch: 0, dragRotate: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.on("load", () => {
      map.addSource("streets", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "streets", type: "line", source: "streets",
        layout: { "line-cap": "round", "line-join": "round", "line-sort-key": sortExpr() },
        paint: { "line-color": colorExpr(),
          "line-width": ["interpolate", ["exponential", 1.6], ["zoom"], 10, widthExpr(0.45), 14, widthExpr(1.1), 17, widthExpr(2.4)] } });
      map.addSource("windows", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "windows", type: "line", source: "windows",
        paint: { "line-color": "#e34948", "line-width": 1.5, "line-dasharray": [3, 2] } });
      setSite(state.site, true);
    });
    const tip = $("#dash-tip");
    map.on("mousemove", "streets", (e) => {
      const i = e.features[0].properties.i;
      const A = values(state.a), B = values(state.b);
      const fmt = (v) => (v == null || v < 0 ? "n/a" : v + "th pct");
      let h = `<b>${byId[state.a].label}</b>: ${fmt(A && A[i])}`;
      if (state.mode === "compare") h += `<br><b>${byId[state.b].label}</b>: ${fmt(B && B[i])}`;
      tip.innerHTML = h; tip.style.display = "block";
      tip.style.left = e.point.x + 14 + "px"; tip.style.top = e.point.y + 14 + "px";
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "streets", () => { tip.style.display = "none"; map.getCanvas().style.cursor = ""; });
  }

  // ---------------------------------------------------------------- panels
  function legend() {
    const el = $("#dash-legend");
    if (state.mode === "one") {
      el.innerHTML = `<div class="lg-title">Percentile within ${cur.doc.meta.label}</div>` +
        SEQ5.map((c, k) => `<span class="lg-item"><i style="background:${c};height:${2 + k}px"></i>${["0–20", "20–40", "40–60", "60–80", "80–100"][k]}</span>`).join("");
    } else {
      const lab = ["B ≫ A", "", "", "agree ±10", "", "", "A ≫ B"];
      el.innerHTML = `<div class="lg-title">Percentile A minus B (A: ${short(state.a)}, B: ${short(state.b)})</div>` +
        DIV7.map((c, k) => `<span class="lg-item"><i style="background:${c};height:${k === 3 ? 2 : 4}px"></i>${lab[k]}</span>`).join("");
    }
  }
  function short(id) { const m = byId[id]; return m.label.replace(/\s*\(.*\)/, "") + (m.r ? ` R${state.r}` : ""); }

  function scatter() {
    const cv = $("#dash-scatter"), ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height, P = 34;
    ctx.clearRect(0, 0, W, H);
    const A = values(state.a), B = values(state.b);
    const out = $("#dash-rho");
    if (!A || !B) { out.textContent = "not available for this site"; return; }
    const N = 50, grid = new Float32Array(N * N); let max = 0;
    for (let i = 0; i < A.length; i++) if (A[i] >= 0 && B[i] >= 0) {
      const gx = Math.min(N - 1, Math.floor(B[i] / 2)), gy = Math.min(N - 1, Math.floor(A[i] / 2));
      const v = ++grid[gy * N + gx]; if (v > max) max = v;
    }
    const cw = (W - P - 8) / N, ch = (H - P - 8) / N;
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const v = grid[y * N + x]; if (!v) continue;
      const t = Math.sqrt(v / max), k = Math.min(4, Math.floor(t * 5));
      ctx.fillStyle = SEQ5[k]; ctx.fillRect(P + x * cw, H - P - (y + 1) * ch, cw + 0.5, ch + 0.5);
    }
    ctx.strokeStyle = "#a3a29c"; ctx.strokeRect(P, 8, W - P - 8, H - P - 8);
    ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(P, H - P); ctx.lineTo(W - 8, 8); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#52514e"; ctx.font = "11px system-ui, sans-serif";
    ctx.fillText("B percentile", W / 2 - 30, H - 10);
    ctx.save(); ctx.translate(12, H / 2 + 30); ctx.rotate(-Math.PI / 2); ctx.fillText("A percentile", 0, 0); ctx.restore();
    const [rho, n] = rankCorr(A, B);
    out.innerHTML = `Spearman ρ = <b>${rho.toFixed(2)}</b> over ${n.toLocaleString()} streets`;
  }

  function agreementChart() {
    const el = $("#dash-agree");
    const fam = byId[state.a].fam === "axial" ? byId[state.b].fam : byId[state.a].fam;
    const rows = (cur.doc.tables.agreement || []).filter((r) => r.family === fam);
    if (!rows.length) { el.innerHTML = "<p class='muted'>No agreement table for this site.</p>"; return; }
    const steps = [...new Set(rows.map((r) => r.step))];
    const radii = [...new Set(rows.map((r) => r.radius))].sort((a, b) => a - b);
    const W = 340, H = 210, L = 34, R = 10, T = 10, B = 26;
    const x = (r) => L + (radii.indexOf(r) / Math.max(1, radii.length - 1)) * (W - L - R);
    const y = (v) => T + (1 - (v + 0.2) / 1.2) * (H - T - B);
    const pal = ["#2a78d6", "#eb6834", "#1baf7a", "#8b5cf6", "#d4a106", "#52514e"];
    const sel = `${state.a}_|${state.b}_`;
    let s = `<svg viewBox="0 0 ${W} ${H}" class="agree-svg" role="img" aria-label="Rank agreement by radius">`;
    [0, 0.5, 1].forEach((v) => { s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`; });
    radii.forEach((r) => { s += `<text x="${x(r)}" y="${H - 8}" text-anchor="middle">${r}</text>`; });
    let leg = "";
    steps.forEach((st, k) => {
      const pts = radii.map((r) => rows.find((q) => q.step === st && q.radius === r)).filter(Boolean);
      const on = pts.length && (pts[0].a + "|" + pts[0].b).replace(/_\d+/g, "_") === sel;
      const col = pal[k % pal.length];
      s += `<polyline fill="none" stroke="${col}" stroke-width="${on ? 3.2 : 1.6}" opacity="${on || state.mode === "one" ? 1 : 0.45}" points="${pts.map((p) => x(p.radius) + "," + y(p.spearman)).join(" ")}"/>`;
      pts.forEach((p) => { s += `<circle cx="${x(p.radius)}" cy="${y(p.spearman)}" r="${on ? 3.5 : 2.5}" fill="${col}"><title>${st}, R${p.radius}: ρ ${p.spearman.toFixed(2)}</title></circle>`; });
      leg += `<div class="agree-leg"><i style="background:${col}"></i>${st.replace(/^[^:]*: /, "").replace(/ -> /g, " to ").replace(/NC\^2/g, "NC²")}</div>`;
    });
    s += `</svg>`;
    el.innerHTML = `<div class="muted small">Spearman ρ between adjacent rungs, ${fam}, by radius (m)</div>` + s + leg;
  }

  function windowsPanel() {
    const el = $("#dash-windows");
    const ws = cur.doc.meta.windows || [];
    const stats = (index.windows || []).filter((w) => w.site === state.site);
    el.innerHTML = ws.map((w) => {
      const st = stats.find((s) => s.window === w.key);
      const info = st ? `${st.streets.toLocaleString()} streets · ${st.network_km_per_km2.toFixed(1)} km/km² · median ${Math.round(st.median_street_m)} m` : "";
      return `<button class="win-btn" data-k="${w.key}">${w.name}</button><div class="muted small">${info}</div>`;
    }).join("") + `<button class="win-btn ghost" data-k="__all">Whole study area</button>`;
    el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const k = b.dataset.k;
      const bb = k === "__all" ? cur.doc.meta.bounds : ws.find((w) => w.key === k).bounds;
      map.fitBounds([[bb[0], bb[1]], [bb[2], bb[3]]], { padding: 20, duration: 900 });
    }));
    map.getSource("windows").setData({ type: "FeatureCollection", features: ws.map((w) => {
      const [a, b, c, d] = w.bounds;
      return { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[a, b], [c, b], [c, d], [a, d], [a, b]] } };
    }) });
  }

  function header() {
    const m = cur.doc.meta;
    $("#dash-head").innerHTML = `<b>${m.label}</b> · ${m.streets.toLocaleString()} interior streets · ${m.km.toLocaleString()} km · ${m.km_per_km2} km/km²`;
  }

  function redraw() {
    classify();
    map.getSource("streets").setData(cur.fc);
    legend(); scatter(); agreementChart();
    $("#dash-b-row").style.display = state.mode === "compare" ? "" : "none";
    $("#dash-radius-row").style.opacity = byId[state.a].r || (state.mode === "compare" && byId[state.b].r) ? 1 : 0.4;
  }

  async function setSite(site, fit) {
    state.site = site;
    cur = await loadSite(site);
    const radii = cur.doc.meta.radii;
    const rs = $("#dash-radius");
    rs.innerHTML = radii.map((r) => `<option ${r === state.r ? "selected" : ""}>${r}</option>`).join("");
    if (!radii.includes(state.r)) state.r = radii.includes(800) ? 800 : radii[0];
    rs.value = state.r;
    header(); windowsPanel(); redraw();
    if (fit) { const b = cur.doc.meta.bounds; map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 20, duration: 0 }); }
  }

  // ---------------------------------------------------------------- controls
  function options(sel, val) {
    const groups = { closeness: "Closeness family", betweenness: "Betweenness family", axial: "Axial (S4, radius-free)" };
    sel.innerHTML = Object.entries(groups).map(([g, lab]) => `<optgroup label="${lab}">` +
      MEASURES.filter((m) => m.fam === g).map((m) => `<option value="${m.id}" ${m.id === val ? "selected" : ""}>${m.label}</option>`).join("") + "</optgroup>").join("");
  }

  async function start() {
    index = await (await fetch(DATA + "index.json")).json();
    const ss = $("#dash-site");
    ss.innerHTML = index.sites.map((s) => `<option value="${s.site}">${s.label}</option>`).join("");
    state.site = index.sites[0].site;
    options($("#dash-a"), state.a); options($("#dash-b"), state.b);
    $("#dash-preset").innerHTML = PRESETS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
    ss.addEventListener("change", () => setSite(ss.value, true));
    $("#dash-a").addEventListener("change", (e) => { state.a = e.target.value; redraw(); });
    $("#dash-b").addEventListener("change", (e) => { state.b = e.target.value; redraw(); });
    $("#dash-radius").addEventListener("change", (e) => { state.r = +e.target.value; redraw(); });
    document.querySelectorAll("input[name=dash-mode]").forEach((r) => r.addEventListener("change", (e) => { state.mode = e.target.value; redraw(); }));
    $("#dash-preset").addEventListener("change", (e) => {
      if (!e.target.value) return;
      const [a, b] = e.target.value.split("|");
      state.a = a; state.b = b; state.mode = "compare";
      $("#dash-a").value = a; $("#dash-b").value = b;
      document.querySelector("input[name=dash-mode][value=compare]").checked = true;
      redraw();
    });
    $("#dash-base").addEventListener("change", (e) => map.setLayoutProperty("base", "visibility", e.target.checked ? "visible" : "none"));
    initMap();
  }

  document.addEventListener("DOMContentLoaded", () => start().catch((err) => {
    $("#dash-status").textContent = "Could not load dashboard data: " + err.message +
      ". Run scripts/14_export_web.py and serve the site over http (quarto preview).";
  }));
})();

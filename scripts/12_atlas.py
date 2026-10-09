"""Map atlas: every spatial output of Phase 0-1 as small-multiple maps, plus an index (atlas.md).

    python scripts/12_atlas.py                                   # defaults below
    python scripts/12_atlas.py --sites copenhagen_c10dp mumbai_island_c10dp --radius 800
    python scripts/12_atlas.py --dpi 110 --out docs/atlas        # lighter copy for the website

Reads only files already written by 01-11 (no network access, no depthmapX). Missing inputs are
skipped with a note, so it can be rerun as more results arrive.

Per site (interior streets; classes are quintiles WITHIN each panel: values are not comparable
across panels, ranks are):
  a01 context              network, interior, boundary, zoom windows
  a02 ladder closeness     S0 harmonic -> S1 harmonic -> S1 NC²/TD -> S2 angular -> S3 integration -> NAIN
  a03 ladder betweenness   S0 -> S1 -> S2 -> S3 choice -> NACH -> S4 axial choice
  a04/a05 steps            where each single design choice reorders streets
  a06/a07 radii            NAIN / NACH at every radius
  a08 S4 axial lines       connectivity, integration HH Rn / R3, choice
  a09 S4 vs angular        where the generated line map and the angular segment map disagree
  a10 zoom                 one 3 x 3 km window, six measures (Indre By; Colaba; Dharavi)
  a11 cleaning             raw vs cleaned network in each window (if both ladders exist)
  a12 tiles                per-tile rank agreement (WP1), if tiles_<size>.gpkg exists
Across sites:
  a13 windows              Indre By | Colaba | Dharavi at the same scale, measure by measure
Barnsbury (if the WP4 validation folders exist):
  b01 hand-drawn vs generated axial maps;  b02 coverage of the hand-drawn map by OSM

Every map panel has a north arrow and a scale bar. Writes reports/atlas/<fig>.png (+ .svg with
--svg), reports/atlas/atlas.md and reports/atlas/windows.csv.
"""
from __future__ import annotations

import argparse
import textwrap
import traceback
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402
from shapely.geometry import LineString, box  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# palette shared with 03_figures.py (validated: sequential blue ramp, blue/red diverging, grey mid)
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#a3a29c", "#e6e5e1"
SEQ5 = ["#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
SEQ_W = [0.18, 0.28, 0.42, 0.65, 1.0]
DIV7 = ["#104281", "#2a78d6", "#9ec5f4", "#c9c8c3", "#f2b8b5", "#e34948", "#a32a2a"]
DIV_EDGES = [-0.5, -0.25, -0.1, 0.1, 0.25, 0.5]
DIV_W = {0: 0.15, 1: 0.35, 2: 0.6, 3: 0.95}
ACCENT = "#e34948"

LABEL = {"copenhagen": "Copenhagen + Frederiksberg", "mumbai_island": "Mumbai City District",
         "barnsbury": "Barnsbury, London"}
# zoom windows per city: key -> (name, lon, lat, half-width m)
WINDOWS = {
    "copenhagen": {"indre_by": ("Indre By, Copenhagen", 12.5790, 55.6800, 1500)},
    "mumbai_island": {"colaba": ("Colaba, Mumbai", 72.8200, 18.9120, 1500),
                      "dharavi": ("Dharavi, Mumbai", 72.8550, 19.0400, 1500)},
    "barnsbury": {"core": ("Barnsbury core", -0.1100, 51.5400, 1500)},
}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 8.5, "axes.edgecolor": MUTED, "text.color": INK, "axes.labelcolor": INK2,
    "axes.titleweight": "bold", "axes.titlesize": 9.5, "axes.titlelocation": "left",
    "axes.titlepad": 5, "axes.labelsize": 7.5,
})

INDEX: list[tuple[str, str, str]] = []   # (file, title, caption)
WINDOW_ROWS: list[dict] = []
OPTS = {"svg": False, "dpi": 200}


def city_of(site: str) -> str:
    for k in LABEL:
        if site.startswith(k):
            return k
    return site


def cleaning_of(site: str) -> str:
    s = site.split("_")[-1]
    return {"c0": "raw network", "c10dp": "cleaned 10 m", "c10d": "10 m destubbed",
            "c20": "20 m consolidation"}.get(s, "")


def save(fig, out: Path, name: str, title: str, caption: str) -> None:
    fig.savefig(out / f"{name}.png", dpi=OPTS["dpi"])
    if OPTS["svg"]:
        fig.savefig(out / f"{name}.svg")
    plt.close(fig)
    INDEX.append((f"{name}.png", title, caption))
    print(f"  {name}.png")


# ------------------------------------------------------------------ drawing primitives
def _segs(geoms):
    out = []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "LineString" and not p.is_empty:
                out.append(np.asarray(p.coords)[:, :2])
    return out


def draw_quintiles(ax, gdf, values, colors=SEQ5, widths=SEQ_W, scale=1.0):
    v = pd.Series(np.asarray(values, float))
    ok = np.isfinite(v.to_numpy())
    cls = np.full(len(v), -1)
    r = v[ok].rank(pct=True, method="average").to_numpy()
    cls[ok] = np.clip(np.floor(r * 5 - 1e-9), 0, 4).astype(int)
    geoms = gdf.geometry.to_numpy()
    if (~ok).any():
        ax.add_collection(LineCollection(_segs(geoms[~ok]), colors=GRID, linewidths=0.15))
    for c in range(5):          # high classes drawn last, on top
        m = cls == c
        if m.any():
            ax.add_collection(LineCollection(_segs(geoms[m]), colors=colors[c],
                                             linewidths=widths[c] * scale, capstyle="round"))


def draw_divergence(ax, gdf, a, b, scale=1.0):
    """Percentile rank of a minus b; agreement thin grey, disagreement thick blue/red."""
    ra = pd.Series(np.asarray(a, float)).rank(pct=True).to_numpy()
    rb = pd.Series(np.asarray(b, float)).rank(pct=True).to_numpy()
    d = ra - rb
    ok = np.isfinite(d)
    cls = np.digitize(d, DIV_EDGES)
    strength = np.abs(cls - 3)
    geoms = gdf.geometry.to_numpy()
    for s in range(4):
        for c in range(7):
            m = ok & (cls == c) & (strength == s)
            if m.any():
                ax.add_collection(LineCollection(_segs(geoms[m]), colors=DIV7[c],
                                                 linewidths=DIV_W[s] * scale, capstyle="round"))
    x, y = np.asarray(a, float), np.asarray(b, float)
    k = np.isfinite(x) & np.isfinite(y)
    return pd.Series(x[k]).corr(pd.Series(y[k]), method="spearman") if k.sum() > 2 else np.nan


def north_arrow(ax, x=0.965, y0=0.012, size=0.07):
    """Small arrow in the bottom-right strip, beside the scale bar, clear of the data."""
    ax.annotate("", xy=(x, y0 + size), xytext=(x, y0), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>,head_width=0.3,head_length=0.55", color=INK,
                                lw=1.0, shrinkA=0, shrinkB=0), zorder=10)
    ax.text(x - 0.022, y0 + size * 0.75, "N", transform=ax.transAxes, ha="right", va="center",
            fontsize=7.5, fontweight="bold", color=INK, zorder=10)


def scale_bar(ax, bounds, km=None):
    x0, y0, x1, y1 = bounds
    w = x1 - x0
    if km is None:
        km = next(k for k in (0.1, 0.25, 0.5, 1, 2, 5, 10, 20) if k * 1000 >= w / 6)
    L = km * 1000
    pad = 0.03 * max(w, y1 - y0)
    sx, sy = x0 + pad * 0.3, y0 - 2.2 * pad
    ax.plot([sx, sx + L], [sy, sy], color=INK, lw=2.2, solid_capstyle="butt", zorder=10)
    ax.plot([sx, sx + L / 2], [sy, sy], color=SURFACE, lw=0.9, solid_capstyle="butt", zorder=11)
    for xx in (sx, sx + L / 2, sx + L):
        ax.plot([xx, xx], [sy - pad * 0.18, sy + pad * 0.18], color=INK, lw=0.8, zorder=11)
    ax.text(sx + L + pad * 0.3, sy, f"{km:g} km", va="center", ha="left", fontsize=7,
            color=INK2, zorder=11)


def map_panel(ax, bounds, title, sub="", bnd=None, km=None, title_chars=48):
    """Equal-aspect map frame: title above, subtitle below, north arrow and scale bar inside."""
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    pad = 0.03 * max(w, h)
    ax.set_xlim(x0 - pad, x1 + pad)
    ax.set_ylim(y0 - 4.5 * pad, y1 + 1.0 * pad)
    if bnd is not None:
        bnd.boundary.plot(ax=ax, color=MUTED, lw=0.5, zorder=0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("\n".join(w for part in title.split("\n")
                            for w in textwrap.wrap(part, title_chars)) if title else "")
    ax.set_ylabel("")
    if sub:
        ax.set_xlabel("\n".join(textwrap.wrap(sub, int(title_chars * 1.2))), labelpad=3,
                      loc="left", color=INK2)
    north_arrow(ax)
    scale_bar(ax, bounds, km)


def figure_grid(n, bounds, ncols=3, panel_h=4.0, min_w=2.9, max_w=6.5):
    """Constrained-layout grid sized to the data aspect; panels never narrower than min_w."""
    x0, y0, x1, y1 = bounds
    asp = (x1 - x0) / max(y1 - y0, 1)
    pw = float(np.clip(panel_h * asp, min_w, max_w))
    ph = float(np.clip(pw / max(asp, 1e-6), 2.5, panel_h * 1.6))
    ncols = max(1, min(ncols, n))
    nrows = int(np.ceil(n / ncols))
    fig = plt.figure(figsize=(ncols * pw + 0.6, nrows * (ph + 1.0) + 1.6), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.12, h_pad=0.15, wspace=0.06, hspace=0.06)
    axes = fig.subplots(nrows, ncols, squeeze=False).ravel()
    for ax in axes[n:]:
        ax.set_axis_off()
    chars = int(max(26, pw * 11))
    return fig, axes[:n], chars


def _legend(fig, handles, title, ncol):
    try:
        fig.legend(handles=handles, loc="outside lower center", ncol=ncol, frameon=False,
                   title=title, fontsize=7.5, title_fontsize=8, columnspacing=1.6)
    except ValueError:  # matplotlib < 3.7: no "outside" placement
        fig.legend(handles=handles, loc="lower center", ncol=ncol, frameon=False, title=title,
                   fontsize=7.5, title_fontsize=8)


def legend_quintiles(fig, label="Quintile within each panel"):
    h = [Line2D([0], [0], color=SEQ5[i], lw=[1, 1.4, 1.8, 2.4, 3][i],
                label=["lowest 20%", "20–40%", "40–60%", "60–80%", "highest 20%"][i]) for i in range(5)]
    _legend(fig, h, label, 5)


def legend_divergence(fig, left, right):
    labels = [f"{left} ranks higher", "", "", "agree (±10 pts)", "", "", f"{right} ranks higher"]
    h = [Line2D([0], [0], color=DIV7[i], lw=2.2, label=labels[i] or " ") for i in range(7)]
    _legend(fig, h, "Percentile-rank difference", 7)


def finish(fig, title):
    fig.suptitle(title, x=0.01, ha="left", fontsize=11.5, fontweight="bold")


# ------------------------------------------------------------------ data
def load_site(site: str):
    d = ROOT / "data" / site
    lad = gpd.read_file(d / "ladder.gpkg", layer="ladder")
    bnd = gpd.read_file(d / "network.gpkg", layer="boundary")
    ax_path = d / "axial" / "axial.gpkg"
    axl = None
    if ax_path.exists():
        st = gpd.read_file(ax_path, layer="streets").drop(columns=["geometry", "interior"],
                                                           errors="ignore")
        lad = lad.merge(st, on="seg_id", how="left")
        axl = gpd.read_file(ax_path, layer="axial")
    return lad, bnd, axl


def windows_of(site, crs):
    """[(key, name, box)] for the site's city, in the site CRS."""
    out = []
    for key, (name, lon, lat, hw) in WINDOWS.get(city_of(site), {}).items():
        p = gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs=4326).to_crs(crs).iloc[0]
        out.append((key, name, box(p.x - hw, p.y - hw, p.x + hw, p.y + hw)))
    return out


def clip(gdf, bx):
    sub = gdf[gdf.intersects(bx)].copy()
    sub["geometry"] = sub.geometry.intersection(bx)
    return sub[~sub.geometry.is_empty]


def title_of(site):
    return f"{LABEL.get(city_of(site), site)} ({cleaning_of(site)})" if cleaning_of(site) else \
        LABEL.get(city_of(site), site)


# ------------------------------------------------------------------ figures per site
def a01_context(site, lad, bnd, out):
    inner = lad[lad.interior.astype(bool)]
    wins = windows_of(site, lad.crs)
    b = lad.total_bounds
    for _, _, bx in wins:   # extent includes the zoom windows
        b = [min(b[0], bx.bounds[0]), min(b[1], bx.bounds[1]), max(b[2], bx.bounds[2]),
             max(b[3], bx.bounds[3])]
    fig, axes, chars = figure_grid(1, b, ncols=1, panel_h=7, max_w=9)
    ax = axes[0]
    ax.add_collection(LineCollection(_segs(lad.geometry), colors=MUTED, linewidths=0.15))
    ax.add_collection(LineCollection(_segs(inner.geometry), colors=SEQ5[3], linewidths=0.3))
    for _, name, bx in wins:
        x0, y0, x1, y1 = bx.bounds
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=ACCENT, lw=1.3, zorder=8))
        ax.annotate(name.split(",")[0], xy=(x1, y1), xytext=(6, 4), textcoords="offset points",
                    color=DIV7[6], fontsize=8, fontweight="bold", zorder=9)
    area = bnd.area.iloc[0] / 1e6
    km = inner.length.sum() / 1000
    map_panel(ax, b, title_of(site),
              f"{len(inner):,} interior streets · {km:,.0f} km · {km / area:.1f} km per km². "
              f"Blue: analysed and reported. Grey: 2 km buffer, context only. Red: zoom windows.",
              bnd, title_chars=chars * 2)
    save(fig, out, f"a01_context_{site}", f"Study network: {title_of(site)}",
         f"Interior streets (blue) are analysed and reported; buffer streets (grey) only give them "
         f"a full catchment. {len(inner):,} interior streets, {km:,.0f} km, {km / area:.1f} km per "
         f"km². Red squares: the 3 × 3 km zoom windows.")


LADDER = {
    "closeness": [("S0_harmonic", "S0 · junction graph, metric harmonic"),
                  ("S1_harmonic", "S1 · segment graph, metric harmonic"),
                  ("S1_hillier", "S1 · segment graph, metric NC²/TD"),
                  ("S2_hillier", "S2 · angular NC²/TD (cityseer)"),
                  ("S3_integration", "S3 · angular integration (depthmapX)"),
                  ("S3_nain", "S3 · NAIN (Space Syntax normalised)")],
    "betweenness": [("S0_betweenness", "S0 · junction graph, metric betweenness"),
                    ("S1_betweenness", "S1 · segment graph, metric betweenness"),
                    ("S2_betweenness", "S2 · angular betweenness (cityseer)"),
                    ("S3_choice", "S3 · angular choice (depthmapX)"),
                    ("S3_nach", "S3 · NACH (Space Syntax normalised)"),
                    ("S4_choice_Rn", "S4 · generated axial lines, choice Rn")],
}
STEPS = {
    "closeness": [("S0_harmonic", "S1_harmonic", "junction to segment"),
                  ("S1_harmonic", "S1_hillier", "harmonic to NC²/TD"),
                  ("S1_hillier", "S2_hillier", "metric to angular"),
                  ("S2_hillier", "S3_integration", "cityseer to depthmapX"),
                  ("S3_integration", "S3_nain", "NC²/TD to NAIN"),
                  ("S1_harmonic", "S3_nain", "end to end: metric harmonic vs NAIN")],
    "betweenness": [("S0_betweenness", "S1_betweenness", "junction to segment"),
                    ("S1_betweenness", "S2_betweenness", "metric to angular"),
                    ("S2_betweenness", "S3_choice", "cityseer to depthmapX"),
                    ("S3_choice", "S3_nach", "choice to NACH"),
                    ("S1_betweenness", "S3_nach", "end to end: metric betweenness vs NACH")],
}


def _col(lad, base, r):
    c = base if base.startswith("S4_") else f"{base}_{r}"
    return c if c in lad else None


def a02_ladder(site, lad, bnd, r, fam, out, num):
    inner = lad[lad.interior.astype(bool)]
    specs = [(c, t) for b, t in LADDER[fam] if (c := _col(inner, b, r))]
    fig, axes, chars = figure_grid(len(specs), inner.total_bounds)
    for ax, (c, t) in zip(axes, specs):
        draw_quintiles(ax, inner, inner[c])
        map_panel(ax, inner.total_bounds, t, f"column {c}", bnd, title_chars=chars)
    legend_quintiles(fig)
    finish(fig, f"{title_of(site)}: the {fam} ladder at R{r} m")
    save(fig, out, f"a0{num}_ladder_{fam}_{site}_{r}", f"Ladder maps, {fam}: {title_of(site)}, R{r} m",
         "The same streets under each rung of the ladder, one design choice changing per panel. "
         "Quintiles within each panel. S4 is radius n (whole map).")


def a04_steps(site, lad, bnd, r, fam, out, num):
    inner = lad[lad.interior.astype(bool)]
    specs = [(f"{a}_{r}", f"{b}_{r}", t) for a, b, t in STEPS[fam]
             if f"{a}_{r}" in inner and f"{b}_{r}" in inner]
    fig, axes, chars = figure_grid(len(specs), inner.total_bounds)
    rhos = []
    for ax, (a, b, t) in zip(axes, specs):
        rho = draw_divergence(ax, inner, inner[b], inner[a])
        rhos.append(f"{t}: ρ {rho:.2f}")
        map_panel(ax, inner.total_bounds, t, f"Spearman ρ = {rho:.2f}", bnd, title_chars=chars)
    legend_divergence(fig, "after the step", "before the step")
    finish(fig, f"{title_of(site)}: where each {fam} step reorders streets, R{r} m")
    save(fig, out, f"a0{num}_steps_{fam}_{site}_{r}", f"Step divergence, {fam}: {title_of(site)}, R{r} m",
         "Red: the street ranks higher after the step than before; blue: lower; thin grey: within "
         "10 percentile points. " + "; ".join(rhos) + ".")


def a06_radii(site, lad, bnd, meas, out, num):
    inner = lad[lad.interior.astype(bool)]
    radii = sorted(int(c.split("_")[-1]) for c in inner if c.startswith(f"S3_{meas}_"))
    if not radii:
        return
    fig, axes, chars = figure_grid(len(radii), inner.total_bounds, ncols=min(4, len(radii)))
    for ax, r in zip(axes, radii):
        draw_quintiles(ax, inner, inner[f"S3_{meas}_{r}"])
        map_panel(ax, inner.total_bounds, f"R{r} m", "", bnd, title_chars=chars)
    legend_quintiles(fig)
    name = {"nain": "NAIN (angular integration)", "nach": "NACH (angular choice)"}[meas]
    finish(fig, f"{title_of(site)}: {name} by radius")
    rho = inner[[f"S3_{meas}_{radii[0]}", f"S3_{meas}_{radii[-1]}"]].corr(method="spearman").iloc[0, 1]
    save(fig, out, f"a0{num}_radii_{meas}_{site}", f"{meas.upper()} by radius: {title_of(site)}",
         f"Local to city-wide structure. Rank correlation between R{radii[0]} and R{radii[-1]}: "
         f"ρ = {rho:.2f}.")


def a08_axial(site, axl, bnd, out):
    inner = axl[axl.interior.astype(bool)] if "interior" in axl else axl
    specs = [("connectivity", "Connectivity (lines crossed)"),
             ("integration_hh_Rn", "Integration HH, radius n"),
             ("integration_hh_R3", "Integration HH, radius 3"),
             ("choice_Rn", "Choice, radius n")]
    specs = [s for s in specs if s[0] in inner]
    fig, axes, chars = figure_grid(len(specs), inner.total_bounds, ncols=4)
    for ax, (c, t) in zip(axes, specs):
        draw_quintiles(ax, inner, inner[c], scale=1.3)
        map_panel(ax, inner.total_bounds, t, f"{len(inner):,} interior lines", bnd, title_chars=chars)
    legend_quintiles(fig)
    finish(fig, f"{title_of(site)}: S4 axial lines generated from centrelines")
    med = (inner.geometry.length).median()
    save(fig, out, f"a08_axial_{site}", f"S4 generated axial lines: {title_of(site)}",
         f"Natural streets straightened at 8 m and extended to cross (WP4). {len(inner):,} interior "
         f"lines, median drawn length {med:.0f} m. Not a hand-drawn axial map (see b01).")


def a09_axial_vs_angular(site, lad, bnd, out):
    inner = lad[lad.interior.astype(bool)]
    pairs = [("S4_integration_hh_R3", "S3_nain_800", "axial HH R3 vs NAIN R800"),
             ("S4_integration_hh_Rn", "S3_nain_2000", "axial HH Rn vs NAIN R2000"),
             ("S4_choice_Rn", "S3_nach_2000", "axial choice Rn vs NACH R2000")]
    pairs = [p for p in pairs if p[0] in inner and p[1] in inner]
    if not pairs:
        return
    fig, axes, chars = figure_grid(len(pairs), inner.total_bounds)
    rhos = []
    for ax, (a, b, t) in zip(axes, pairs):
        rho = draw_divergence(ax, inner, inner[a], inner[b])
        rhos.append(f"{t}: ρ {rho:.2f}")
        map_panel(ax, inner.total_bounds, t, f"Spearman ρ = {rho:.2f}", bnd, title_chars=chars)
    legend_divergence(fig, "axial", "angular")
    finish(fig, f"{title_of(site)}: generated axial lines vs angular segments")
    save(fig, out, f"a09_axial_vs_angular_{site}", f"S4 vs S3 divergence: {title_of(site)}",
         "Axial values carried to streets (length-weighted). " + "; ".join(rhos) + ".")


ZOOM_SPECS = [("S1_harmonic_{r}", "metric harmonic closeness R{r}"),
              ("S3_nain_{r}", "NAIN R{r}"),
              ("S3_nach_{r}", "NACH R{r}"),
              ("S1_betweenness_{r}", "metric betweenness R{r}"),
              ("S4_integration_hh_R3", "axial integration HH R3"),
              ("S4_choice_Rn", "axial choice Rn")]


def a10_zoom(site, lad, out, r):
    for key, name, bx in windows_of(site, lad.crs):
        sub = clip(lad, bx)
        if len(sub) < 20:
            continue
        specs = [(c.format(r=r), t.format(r=r)) for c, t in ZOOM_SPECS if c.format(r=r) in sub]
        fig, axes, chars = figure_grid(len(specs), bx.bounds, ncols=3, panel_h=4.4)
        for ax, (c, t) in zip(axes, specs):
            draw_quintiles(ax, sub, sub[c], scale=2.2)
            map_panel(ax, bx.bounds, t, "", km=0.5, title_chars=chars)
        legend_quintiles(fig, "Quintile within the window")
        finish(fig, f"{name}: the same streets under six measures ({cleaning_of(site)})")
        save(fig, out, f"a10_zoom_{key}_{site}", f"Zoom: {name} ({cleaning_of(site)})",
             f"3 × 3 km window, {len(sub):,} streets. Classes are re-ranked inside the window so "
             f"local contrasts are visible.")


def a11_cleaning(city, sites_avail, out, r):
    raw, clean = f"{city}_c0", f"{city}_c10dp"
    if raw not in sites_avail or clean not in sites_avail:
        return
    L = {s: gpd.read_file(ROOT / "data" / s / "ladder.gpkg", layer="ladder") for s in (raw, clean)}
    for key, name, bx in windows_of(clean, L[clean].crs):
        fig, axes, chars = figure_grid(4, bx.bounds, ncols=2, panel_h=4.6)
        k = 0
        for meas in ("nain", "nach"):
            for s in (raw, clean):
                sub = clip(L[s], bx)
                draw_quintiles(axes[k], sub, sub[f"S3_{meas}_{r}"], scale=2.2)
                map_panel(axes[k], bx.bounds, f"{meas.upper()} R{r}: {cleaning_of(s)}",
                          f"{len(sub):,} streets in the window", km=0.5, title_chars=chars)
                k += 1
        legend_quintiles(fig, "Quintile within the window")
        finish(fig, f"{name}: raw vs cleaned network")
        save(fig, out, f"a11_cleaning_{key}", f"Cleaning effect: {name}",
             "Same window and measure on raw OSM (0 m) and on the cleaned network (10 m "
             "consolidation, stubs removed, parallels merged; WP2/2b).")


def a12_tiles(site, bnd, out):
    f = next(iter(sorted((ROOT / "data" / site).glob("tiles_*.gpkg"))), None)
    if f is None:
        return
    t = gpd.read_file(f)
    cols = [c for c in t if c.startswith("rho_")] + ["network_km_per_km2"]
    cols = [c for c in cols if c in t]
    fig, axes, chars = figure_grid(len(cols), t.total_bounds, ncols=3)
    names = {"cost": "metric to angular", "norm": "normalisation (NAIN, NACH)",
             "e2e": "end to end", "engine": "cityseer to depthmapX",
             "repr": "junction to segment", "form": "harmonic to NC²/TD"}
    for ax, c in zip(axes, cols):
        v = t[c].to_numpy(float)
        if c.startswith("rho_"):
            k = c[4:].split("_")
            edges, title = [0.2, 0.4, 0.6, 0.8], f"{names.get(k[0], k[0])}, {' '.join(k[1:])}"
            sub = "Spearman ρ within each tile"
        else:
            edges, title = list(np.nanquantile(v, [0.2, 0.4, 0.6, 0.8])), "network km per km²"
            sub = "quintiles of density (not ρ)"
        cls = np.digitize(v, edges)
        t.plot(ax=ax, color=[SEQ5[k] if np.isfinite(x) else GRID for k, x in zip(cls, v)],
               edgecolor=SURFACE, linewidth=0.6)
        map_panel(ax, t.total_bounds, title, sub, bnd, title_chars=chars)
    h = [Patch(color=SEQ5[i], label=l) for i, l in
         enumerate(["ρ < 0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "≥ 0.8"])]
    _legend(fig, h, "Rank agreement within the tile", 5)
    finish(fig, f"{title_of(site)}: agreement by tile ({f.stem.replace('_', ' ')} m)")
    save(fig, out, f"a12_tiles_{site}", f"Per-tile agreement: {title_of(site)}",
         "Rank agreement of each ladder step recomputed inside equal-area tiles (WP1); last panel "
         "is network density.")


# ------------------------------------------------------------------ across sites
A13_ROWS = [("S3_nain_{r}", "NAIN R{r}", "q"), ("S3_nach_{r}", "NACH R{r}", "q"),
            ("S1_harmonic_{r}", "metric harmonic R{r}", "q"),
            ("S4_integration_hh_R3", "axial integration HH R3", "q"),
            (("S3_nain_{r}", "S1_harmonic_{r}"), "NAIN vs metric harmonic R{r}", "d")]


def a13_windows(sites, out, r):
    """Indre By | Colaba | Dharavi side by side, same window size and scale, measure by measure."""
    cols = []
    for s in sites:
        lad = gpd.read_file(ROOT / "data" / s / "ladder.gpkg", layer="ladder")
        ax_path = ROOT / "data" / s / "axial" / "axial.gpkg"
        if ax_path.exists():
            st = gpd.read_file(ax_path, layer="streets").drop(columns=["geometry", "interior"],
                                                               errors="ignore")
            lad = lad.merge(st, on="seg_id", how="left")
        for key, name, bx in windows_of(s, lad.crs):
            sub = clip(lad, bx)
            if len(sub) >= 20:
                cols.append((s, key, name, bx, sub))
    if len(cols) < 2:
        return
    rows = [(c if isinstance(c, tuple) else c, t.format(r=r), k) for c, t, k in A13_ROWS]
    rows = [(tuple(x.format(r=r) for x in c) if isinstance(c, tuple) else c.format(r=r), t, k)
            for c, t, k in rows]
    rows = [row for row in rows if all(
        all(x in sub for x in (row[0] if isinstance(row[0], tuple) else (row[0],)))
        for *_, sub in cols)]
    nr, nc = len(rows), len(cols)
    fig = plt.figure(figsize=(nc * 3.9 + 0.6, nr * 4.35 + 1.8), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.12, h_pad=0.15, wspace=0.05, hspace=0.06)
    axes = fig.subplots(nr, nc, squeeze=False)
    for j, (s, key, name, bx, sub) in enumerate(cols):
        area = bx.area / 1e6
        km = sub.length.sum() / 1000
        rec = {"site": s, "window": key, "name": name, "streets": len(sub),
               "streets_per_km2": len(sub) / area, "network_km_per_km2": km / area,
               "median_street_m": float(sub.length.median())}
        for i, (c, t, kind) in enumerate(rows):
            ax = axes[i, j]
            if kind == "q":
                draw_quintiles(ax, sub, sub[c], scale=2.0)
                sub_t = ""
            else:
                rho = draw_divergence(ax, sub, sub[c[0]], sub[c[1]], scale=1.8)
                rec[f"rho_{c[0]}_vs_{c[1]}"] = rho
                sub_t = f"ρ = {rho:.2f} within the window"
            head = f"{name}\n{t}" if i == 0 else t
            map_panel(ax, bx.bounds, head, sub_t, km=0.5, title_chars=40)
        x, y = sub[f"S3_nain_{r}"], sub[f"S3_nach_{r}"]
        rec["rho_nain_vs_nach"] = x.corr(y, method="spearman")
        WINDOW_ROWS.append(rec)
    legend_quintiles(fig, "Rows 1–4: quintile within each window · row 5: percentile-rank "
                          "difference (red: NAIN ranks higher, blue: metric ranks higher)")
    finish(fig, f"Three 3 × 3 km windows at the same scale, R{r} m")
    w = pd.DataFrame(WINDOW_ROWS)
    w.to_csv(out / "windows.csv", index=False)
    cap = "; ".join(f"{row['name']}: {row['streets']:,} streets, {row['network_km_per_km2']:.1f} "
                    f"km/km², median street {row['median_street_m']:.0f} m" for row in WINDOW_ROWS)
    save(fig, out, "a13_windows", "Indre By, Colaba and Dharavi compared",
         "Same window size, same scale, same measures; classes within each window. " + cap +
         ". Numbers in windows.csv.")


# ------------------------------------------------------------------ Barnsbury
def _dmx_lines(path: Path):
    m = pd.read_csv(path)
    g = [LineString([(a, b), (c, d)]) for a, b, c, d in m[["x1", "y1", "x2", "y2"]].values]
    return gpd.GeoDataFrame(m, geometry=g, crs=27700)


def b01_barnsbury(out):
    maps = [("hand-drawn reference", ROOT / "data/barnsbury_osm/dmx_reference/axial_map.csv"),
            ("generated, OSM walk network", ROOT / "data/barnsbury_osm/dmx_tol8/axial_map.csv"),
            ("generated, OSM streets only", ROOT / "data/barnsbury_streets/dmx_tol8/axial_map.csv")]
    maps = [(t, p) for t, p in maps if p.exists()]
    if len(maps) < 2:
        return
    G = {t: _dmx_lines(p) for t, p in maps}
    bounds = G[maps[0][0]].total_bounds
    fig, axes, chars = figure_grid(2 * len(maps), bounds, ncols=len(maps), panel_h=4.4)
    k = 0
    for col, lab in (("Integration [HH]", "integration HH Rn"), ("Choice", "choice Rn")):
        for t, _ in maps:
            g = G[t]
            v = g[col].where(g[col] != -1)
            draw_quintiles(axes[k], g, v, scale=1.4)
            map_panel(axes[k], bounds, f"{t}: {lab}", f"{len(g):,} lines", km=1, title_chars=chars)
            k += 1
    legend_quintiles(fig)
    finish(fig, "Barnsbury: hand-drawn axial map vs axial maps generated from OSM (tol 8 m)")
    save(fig, out, "b01_barnsbury_axial", "Barnsbury: hand-drawn vs generated axial maps",
         "Same extent, same depthmapX analysis. Rank agreement with the hand-drawn map on matched "
         "lines is ρ ≤ 0.28 for every measure (WP4).")


def b02_coverage(out):
    files = [("OSM walk network", ROOT / "data/barnsbury_osm/coverage_diag.gpkg"),
             ("OSM streets only", ROOT / "data/barnsbury_streets/coverage_diag.gpkg")]
    files = [(t, f) for t, f in files if f.exists()]
    if not files:
        return
    ref0 = gpd.read_file(files[0][1], layer="reference")
    fig, axes, chars = figure_grid(len(files), ref0.total_bounds, ncols=len(files), panel_h=5.2)
    pal = [DIV7[6], DIV7[5], DIV7[3], DIV7[1], DIV7[0]]
    for ax, (t, f) in zip(axes, files):
        ref = gpd.read_file(f, layer="reference")
        cl = gpd.read_file(f, layer="centrelines")
        ax.add_collection(LineCollection(_segs(cl.geometry), colors=GRID, linewidths=0.35))
        cls = np.digitize(ref.match_share.fillna(0).to_numpy(), [0.2, 0.4, 0.6, 0.8])
        for c in range(5):
            m = cls == c
            ax.add_collection(LineCollection(_segs(ref.geometry.to_numpy()[m]), colors=pal[c],
                                             linewidths=1.0))
        map_panel(ax, ref.total_bounds, t, f"mean share within 15 m: {ref.match_share.mean():.2f}",
                  km=1, title_chars=chars)
    h = [Line2D([0], [0], color=pal[i], lw=2.2, label=l) for i, l in
         enumerate(["< 20%", "20–40%", "40–60%", "60–80%", "≥ 80%"])]
    h.append(Line2D([0], [0], color=GRID, lw=2, label="OSM centrelines"))
    _legend(fig, h, "Share of each hand-drawn line within 15 m of an OSM centreline", 6)
    finish(fig, "Barnsbury: where hand-drawn axial lines and OSM centrelines part ways")
    save(fig, out, "b02_barnsbury_coverage", "Barnsbury: coverage of the hand-drawn map",
         "Red: hand-drawn lines far from any OSM centreline (paths through open space, lines cut "
         "across bends and squares); blue: lines that follow a street.")


# ------------------------------------------------------------------ index
def write_index(out: Path, skipped: list[str]) -> None:
    lines = ["# Map atlas", "",
             "Generated by `scripts/12_atlas.py` from the Phase 0–1 outputs. Maps show interior "
             "streets; classes are quintiles within each panel (ranks, not raw values, are "
             "comparable between panels and cities). Divergence maps show the percentile-rank "
             "difference between two measures: thin grey where they agree within 10 points. "
             "Street data © OpenStreetMap contributors (ODbL).", ""]
    for f, t, c in INDEX:
        lines += [f"## {t}", "", f"![{t}]({f})", "", c, ""]
    if skipped:
        lines += ["## Not produced", ""] + [f"- {s}" for s in skipped] + [""]
    (out / "atlas.md").write_text("\n".join(lines))
    print(f"wrote {out / 'atlas.md'} ({len(INDEX)} figures)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+",
                    default=["copenhagen_c10dp", "mumbai_island_c10dp", "copenhagen_c0",
                             "mumbai_island_c0"])
    ap.add_argument("--compare", nargs="+", default=None,
                    help="sites for the a13 window comparison (default: the c10dp sites)")
    ap.add_argument("--radius", type=int, default=800)
    ap.add_argument("--out", default=str(ROOT / "reports" / "atlas"))
    ap.add_argument("--svg", action="store_true")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--only", nargs="*", default=None, help="figure prefixes, e.g. a02 a10 b01")
    args = ap.parse_args()
    OPTS.update(svg=args.svg, dpi=args.dpi)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    want = (lambda p: args.only is None or p in args.only)
    skipped = []

    def run(tag, fn, *a):
        if not want(tag):
            return
        try:
            fn(*a)
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            skipped.append(f"{tag} {a[0] if a else ''}: {type(e).__name__}: {e}")
            traceback.print_exc(limit=2)

    avail = [s for s in args.sites if (ROOT / "data" / s / "ladder.gpkg").exists()]
    for s in args.sites:
        if s not in avail:
            skipped.append(f"{s}: no ladder.gpkg")
    r = args.radius
    for s in avail:
        print(f"[{s}]")
        lad, bnd, axl = load_site(s)
        run("a01", a01_context, s, lad, bnd, out)
        run("a02", a02_ladder, s, lad, bnd, r, "closeness", out, 2)
        run("a03", a02_ladder, s, lad, bnd, r, "betweenness", out, 3)
        run("a04", a04_steps, s, lad, bnd, r, "closeness", out, 4)
        run("a05", a04_steps, s, lad, bnd, r, "betweenness", out, 5)
        run("a06", a06_radii, s, lad, bnd, "nain", out, 6)
        run("a07", a06_radii, s, lad, bnd, "nach", out, 7)
        if axl is not None:
            run("a08", a08_axial, s, axl, bnd, out)
            run("a09", a09_axial_vs_angular, s, lad, bnd, out)
        run("a10", a10_zoom, s, lad, out, r)
        run("a12", a12_tiles, s, bnd, out)
    for city in sorted({city_of(s) for s in avail}):
        print(f"[{city} cleaning]")
        run("a11", a11_cleaning, city, avail, out, r)
    comp = args.compare or [s for s in avail if s.endswith("_c10dp")] or avail
    print(f"[windows: {', '.join(comp)}]")
    run("a13", a13_windows, comp, out, r)
    print("[barnsbury]")
    run("b01", b01_barnsbury, out)
    run("b02", b02_coverage, out)
    write_index(out, skipped)
    if skipped:
        print("skipped:\n  " + "\n  ".join(skipped))


if __name__ == "__main__":
    main()

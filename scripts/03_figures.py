"""Phase 0 figures from ladder.gpkg and agreement.csv.

    python scripts/03_figures.py --sites copenhagen mumbai_island --radius 800

Writes PNGs (and SVGs) to reports/phase0/figures/:
    fig1_ladder.png           rank agreement at each single-change step, both cities
    fig2_nach_<r>.png         S3 NACH (angular choice, SS-normalised), within-city quintiles
    fig3_nain_<r>.png         S3 NAIN (angular integration, SS-normalised), within-city quintiles
    fig4_divergence_<r>.png   where NAIN and metric closeness disagree (percentile difference)

Maps show interior segments only and classify WITHIN each city: raw values are not comparable
across cities, ranks are.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# palette (validated: categorical slots 1-2 pass CVD and contrast on #fcfcfb)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#a3a29c"
GRID = "#e6e5e1"
CITY = {"copenhagen": "#2a78d6", "mumbai_island": "#eb6834"}
LABEL = {"copenhagen": "Copenhagen + Frederiksberg", "mumbai_island": "Mumbai City District"}
SEQ5 = ["#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]          # blue 200..700
DIV7 = ["#104281", "#2a78d6", "#9ec5f4", "#c9c8c3", "#f2b8b5", "#e34948", "#a32a2a"]
DIV_EDGES = [-1.0, -0.5, -0.25, -0.1, 0.1, 0.25, 0.5, 1.0]

STEPS = {
    "closeness": [
        ("representation: junction -> segment", "Junction to segment"),
        ("closeness form: harmonic -> NC^2/TD", "Harmonic to NC²/TD"),
        ("cost: metric -> angular", "Metric to angular"),
        ("engine + straight pieces: cityseer -> depthmapX", "cityseer to depthmapX"),
        ("normalisation: NC^2/TD -> NAIN", "NC²/TD to NAIN"),
        ("end to end: S1 harmonic vs NAIN", "End to end"),
    ],
    "betweenness": [
        ("representation: junction -> segment", "Junction to segment"),
        ("cost: metric -> angular", "Metric to angular"),
        ("engine + straight pieces: cityseer -> depthmapX", "cityseer to depthmapX"),
        ("normalisation: choice -> NACH", "Choice to NACH"),
        ("end to end: S1 betweenness vs NACH", "End to end"),
    ],
}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "text.color": INK, "axes.titleweight": "bold", "axes.titlesize": 10,
})


def save(fig, out: Path, name: str) -> None:
    for ext in ("png", "svg"):
        fig.savefig(out / f"{name}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.png/.svg")


# ------------------------------------------------------------------ ladder chart
def fig_ladder(sites: list[str], radius: int, out: Path) -> None:
    tabs = {s: pd.read_csv(ROOT / "data" / s / "agreement.csv") for s in sites}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9), sharex=True)
    offs = np.linspace(-0.16, 0.16, len(sites))
    for ax, (fam, steps) in zip(axes, STEPS.items()):
        ys = np.arange(len(steps))[::-1]
        for (key, lab), y in zip(steps, ys):
            if key.startswith("end to end"):
                ax.axhspan(y - 0.45, y + 0.45, color=GRID, zorder=0, lw=0)
        for off, s in zip(offs, sites):
            t = tabs[s][tabs[s].family == fam]
            for (key, lab), y in zip(steps, ys):
                rows = t[t.step == key]
                if rows.empty:
                    continue
                lo, hi = rows.spearman.min(), rows.spearman.max()
                ax.plot([lo, hi], [y + off] * 2, color=CITY[s], lw=2, solid_capstyle="round",
                        alpha=0.45, zorder=2)
                v = rows.loc[rows.radius == radius, "spearman"]
                if len(v):
                    ax.scatter(v, [y + off], s=46, color=CITY[s], edgecolor=SURFACE,
                               linewidth=1.5, zorder=3)
        ax.set_yticks(ys, [lab for _, lab in steps])
        ax.set_xlim(-0.1, 1.02)
        ax.axvline(0, color=MUTED, lw=0.8, zorder=1)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_title(f"{fam.capitalize()} family", loc="left")
        ax.set_xlabel("Spearman ρ between adjacent rungs")
    handles = [Line2D([0], [0], marker="o", color=CITY[s], lw=2, alpha=0.9, markersize=6,
                      markeredgecolor=SURFACE, label=LABEL[s]) for s in sites]
    handles.append(Line2D([0], [0], color=MUTED, lw=2, alpha=0.6, label="bar: range over radii"))
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), frameon=False,
               bbox_to_anchor=(0.5, 0.94))
    fig.suptitle(f"Where Space Syntax and network analysis diverge (dot = {radius} m; "
                 "one design choice per row)", y=0.99, fontsize=11, fontweight="bold")
    save(fig, out, "fig1_ladder")


# ------------------------------------------------------------------ maps
def _load(site: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    lad = gpd.read_file(ROOT / "data" / site / "ladder.gpkg", layer="ladder")
    lad = lad[lad["interior"].astype(bool)].copy()
    bnd = gpd.read_file(ROOT / "data" / site / "network.gpkg", layer="boundary")
    return lad, bnd


def _lines(ax, gdf, classes, colors, widths):
    order = np.argsort(classes)  # draw high classes on top
    segs, cols, lws = [], [], []
    for i in order:
        c = classes[i]
        if c < 0:
            continue
        g = gdf.geometry.iloc[i]
        parts = getattr(g, "geoms", [g])
        for p in parts:
            segs.append(np.asarray(p.coords)[:, :2])
            cols.append(colors[c])
            lws.append(widths[c])
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=lws, capstyle="round"))


def _frame(ax, bnd, gdf, title, sub):
    """Set the extent from the data, then add boundary, scale bar and titles."""
    x0, y0, x1, y1 = gdf.total_bounds
    bx0, by0, bx1, by1 = bnd.total_bounds
    x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
    pad = 0.02 * max(x1 - x0, y1 - y0)
    ax.set_xlim(x0 - pad, x1 + pad)
    ax.set_ylim(y0 - 4 * pad, y1 + pad)  # room below the data for the scale bar
    bnd.boundary.plot(ax=ax, color=MUTED, lw=0.6, zorder=0)
    ax.set_aspect("equal")
    L = 2000
    sx, sy = x0, y0 - 3 * pad
    ax.plot([sx, sx + L], [sy, sy], color=INK, lw=2, solid_capstyle="butt", zorder=5)
    ax.text(sx + L + pad * 0.5, sy, "2 km", ha="left", va="center",
            color=INK2, fontsize=8, zorder=5)
    ax.set_axis_off()
    ax.set_title(f"{title}\n", loc="left")
    ax.text(0, 1.0, sub, transform=ax.transAxes, color=INK2, fontsize=8, va="bottom")


def _map_fig(sites):
    """Figure sized to the data's aspect ratios, one panel per site."""
    aspects = []
    for s in sites:
        b = gpd.read_file(ROOT / "data" / s / "network.gpkg", layer="boundary").total_bounds
        aspects.append((b[3] - b[1]) / max(b[2] - b[0], 1))
    h = 6.0
    widths = [h / a for a in aspects]
    fig, axes = plt.subplots(1, len(sites), figsize=(min(sum(widths), 16) + 0.5, h + 1.4),
                             gridspec_kw={"width_ratios": widths})
    return fig, np.atleast_1d(axes)


def _quintiles(v: pd.Series) -> np.ndarray:
    r = v.rank(pct=True, method="average")
    c = np.floor(r.to_numpy() * 5 - 1e-9).astype(float)
    c[~np.isfinite(v.to_numpy(float))] = -1
    return np.clip(c, -1, 4).astype(int)


def fig_measure(sites, radius, col, title, fname, out):
    fig, axes = _map_fig(sites)
    for ax, s in zip(axes, sites):
        lad, bnd = _load(s)
        c = f"S3_{col}_{radius}"
        cls = _quintiles(lad[c])
        _lines(ax, lad, cls, SEQ5, [0.25, 0.35, 0.5, 0.8, 1.2])
        _frame(ax, bnd, lad, LABEL[s], f"{len(lad):,} interior segments")
    handles = [Line2D([0], [0], color=SEQ5[i], lw=[1, 1.4, 1.8, 2.4, 3][i],
                      label=["lowest 20%", "20–40%", "40–60%", "60–80%", "highest 20%"][i])
               for i in range(5)]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False,
               title="Quintile within each city", bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f"{title}, R{radius} m (depthmapX, tulip-1024)", x=0.02, y=0.99, ha="left",
                 fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 0.92))
    save(fig, out, f"{fname}_{radius}")


def fig_divergence(sites, radius, out):
    fig, axes = _map_fig(sites)
    for ax, s in zip(axes, sites):
        lad, bnd = _load(s)
        a = lad[f"S3_nain_{radius}"].rank(pct=True)
        b = lad[f"S1_harmonic_{radius}"].rank(pct=True)
        d = (a - b).to_numpy()
        cls = np.digitize(d, DIV_EDGES[1:-1])
        cls[~np.isfinite(d)] = -1
        # neutral class drawn first and thin, so disagreement stands out
        order_cls = np.abs(cls - 3)  # 0 = agree ... 3 = strongest disagreement
        segs_cols = {k: DIV7[k] for k in range(7)}
        widths = {0: 0.25, 1: 0.45, 2: 0.7, 3: 1.0}
        segs, cols, lws = [], [], []
        for i in np.argsort(order_cls):
            if cls[i] < 0:
                continue
            g = lad.geometry.iloc[i]
            for p in getattr(g, "geoms", [g]):
                segs.append(np.asarray(p.coords)[:, :2])
                cols.append(segs_cols[cls[i]])
                lws.append(widths[order_cls[i]])
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=lws, capstyle="round"))
        rho = pd.Series(a).corr(pd.Series(b), method="spearman")
        _frame(ax, bnd, lad, LABEL[s], f"Spearman ρ = {rho:.2f} (interior segments)")
    labels = ["metric ≫ NAIN", "", "", "agree (±10 pts)", "", "", "NAIN ≫ metric"]
    handles = [Line2D([0], [0], color=DIV7[i], lw=2.4, label=labels[i] or " ") for i in range(7)]
    fig.legend(handles=handles, loc="lower center", ncol=7, frameon=False,
               title="Percentile rank: NAIN minus metric harmonic closeness",
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f"Where Space Syntax integration and metric closeness disagree, R{radius} m",
                 x=0.02, y=0.99, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 0.92))
    save(fig, out, f"fig4_divergence_{radius}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+", default=["copenhagen", "mumbai_island"])
    ap.add_argument("--radius", type=int, default=800)
    ap.add_argument("--out", default=str(ROOT / "reports" / "phase0" / "figures"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print("figures ->", out)
    fig_ladder(args.sites, args.radius, out)
    fig_measure(args.sites, args.radius, "nach", "Angular choice (NACH)", "fig2_nach", out)
    fig_measure(args.sites, args.radius, "nain", "Angular integration (NAIN)", "fig3_nain", out)
    fig_divergence(args.sites, args.radius, out)


if __name__ == "__main__":
    main()

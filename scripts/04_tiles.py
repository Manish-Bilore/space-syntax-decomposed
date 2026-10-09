"""Phase 1, WP1: equal-area tiles and catchment size.

    python scripts/04_tiles.py --sites copenhagen mumbai_island --tile 1000 --radius 800

Whole-city tables hide internal variation. This cuts each city into equal-area tiles and, per
tile, recomputes rank agreement for the key ladder steps, alongside the network's density
there. Question: does Space Syntax diverge more from metric analysis where the network is
denser, or sparser, and is that the same in both cities?

Also recovers catchment size (node count NC within the radius, in depthmapX straight pieces)
from the depthmapX run, so every measure can be read beside how many pieces it is computed over.

Needs data/<site>/ladder.gpkg, network.gpkg and depthmapx/segment_map.csv from 02_ladder.py.
Writes data/<site>/tiles_<tile>.gpkg / .csv and reports/phase1/figures/fig5_tiles_<tile>_<r>.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402
from shapely.geometry import box  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ssx.network.build import explode_straight  # noqa: E402

SURFACE, INK2, MUTED, GRID = "#fcfcfb", "#52514e", "#a3a29c", "#e6e5e1"
CITY = {"copenhagen": "#2a78d6", "mumbai_island": "#eb6834"}
LABEL = {"copenhagen": "Copenhagen + Frederiksberg", "mumbai_island": "Mumbai City District"}

STEPS = {
    "cost_closeness": ("S1_hillier", "S2_hillier", "Closeness: metric to angular"),
    "norm_closeness": ("S3_integration", "S3_nain", "Closeness: NC²/TD to NAIN"),
    "e2e_closeness": ("S1_harmonic", "S3_nain", "Closeness end to end"),
    "e2e_betweenness": ("S1_betweenness", "S3_nach", "Betweenness end to end"),
}


def catchment_size(site: str, seg: gpd.GeoDataFrame, radii: list[int]) -> pd.DataFrame:
    """NC (straight pieces within radius) per street, length-weighted over its pieces."""
    f = ROOT / "data" / site / "depthmapx" / "segment_map.csv"
    if not f.exists():
        print(f"  [{site}] no depthmapX output at {f}; skipping catchment size")
        return pd.DataFrame(index=seg.index)
    m = pd.read_csv(f)
    pieces = explode_straight(seg)
    mid_d = np.c_[(m.x1 + m.x2) / 2, (m.y1 + m.y2) / 2]
    mid_p = np.array([g.interpolate(0.5, normalized=True).coords[0] for g in pieces.geometry])
    dist, idx = cKDTree(mid_d).query(mid_p)
    ok = dist < 0.05
    w = pieces.geometry.length.to_numpy()
    out = {}
    for r in radii:
        col = f"T1024 Node Count R{r} metric"
        if col not in m:
            continue
        nc = np.where(ok, m[col].to_numpy()[idx], np.nan)
        d = pd.DataFrame({"p": pieces["parent_seg_id"].to_numpy(), "nc": nc, "w": w}).dropna()
        out[f"S3_nc_{r}"] = d.groupby("p").apply(lambda x: np.average(x.nc, weights=x.w))
    return pd.DataFrame(out).reindex(seg["seg_id"]).reset_index(drop=True)


def tiles_for(site: str, size: float, radius: int, min_n: int) -> gpd.GeoDataFrame:
    d = ROOT / "data" / site
    lad = gpd.read_file(d / "ladder.gpkg", layer="ladder")
    seg = gpd.read_file(d / "network.gpkg", layer="segments")
    bnd = gpd.read_file(d / "network.gpkg", layer="boundary")
    nc = catchment_size(site, seg, [radius])
    lad = pd.concat([lad.reset_index(drop=True), nc], axis=1)
    lad = gpd.GeoDataFrame(lad, geometry="geometry", crs=seg.crs)
    lad = lad[lad["interior"].astype(bool)].copy()

    mids = lad.geometry.interpolate(0.5, normalized=True)
    x0, y0, x1, y1 = bnd.total_bounds
    ix = np.floor((mids.x - x0) / size).astype(int)
    iy = np.floor((mids.y - y0) / size).astype(int)
    lad["tile"] = ix.astype(str) + "_" + iy.astype(str)
    poly = bnd.geometry.iloc[0]

    rows = []
    for t, g in lad.groupby("tile"):
        if len(g) < min_n:
            continue
        i, j = map(int, t.split("_"))
        cell = box(x0 + i * size, y0 + j * size, x0 + (i + 1) * size, y0 + (j + 1) * size)
        land_km2 = cell.intersection(poly).area / 1e6
        if land_km2 < 0.25 * (size / 1000) ** 2:
            continue  # mostly water or outside: density would be meaningless
        row = {"tile": t, "geometry": cell, "n_segments": len(g),
               "land_km2": land_km2, "seg_per_km2": len(g) / land_km2,
               "network_km_per_km2": g.geometry.length.sum() / 1000 / land_km2,
               "median_segment_m": g.geometry.length.median()}
        if f"S3_nc_{radius}" in g:
            row[f"median_nc_{radius}"] = g[f"S3_nc_{radius}"].median()
        for k, (a, b, _) in STEPS.items():
            ca, cb = f"{a}_{radius}", f"{b}_{radius}"
            if ca in g and cb in g:
                x, y = g[ca].to_numpy(float), g[cb].to_numpy(float)
                ok = np.isfinite(x) & np.isfinite(y)
                row[f"rho_{k}"] = spearmanr(x[ok], y[ok])[0] if ok.sum() >= min_n else np.nan
        rows.append(row)
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=seg.crs)


def figure(tabs: dict, size: int, radius: int, out: Path) -> None:
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.titleweight": "bold", "axes.titlesize": 10})
    keys = list(STEPS)
    fig, axes = plt.subplots(1, len(keys), figsize=(3.4 * len(keys), 3.6), sharey=True)
    for ax, k in zip(axes, keys):
        for s, t in tabs.items():
            col = f"rho_{k}"
            if col not in t:
                continue
            ax.scatter(t["seg_per_km2"], t[col], s=14, color=CITY.get(s, MUTED), alpha=0.7,
                       edgecolor=SURFACE, linewidth=0.5, label=LABEL.get(s, s))
        ax.set_title(STEPS[k][2], loc="left")
        ax.set_xlabel("segments per km² (tile)")
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_ylabel(f"Spearman ρ within tile, R{radius} m")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, markerscale=2,
               bbox_to_anchor=(0.5, 0.93))
    fig.suptitle(f"Does divergence track network density? {size / 1000:g} km tiles",
                 y=0.99, fontsize=11, fontweight="bold")
    for ext in ("png", "svg"):
        fig.savefig(out / f"fig5_tiles_{size}_{radius}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+", default=["copenhagen", "mumbai_island"])
    ap.add_argument("--tile", type=int, default=1000, help="tile side (m)")
    ap.add_argument("--radius", type=int, default=800)
    ap.add_argument("--min-n", type=int, default=50, help="minimum segments per tile")
    args = ap.parse_args()
    out = ROOT / "reports" / "phase1" / "figures"
    out.mkdir(parents=True, exist_ok=True)

    tabs = {}
    summary = []
    for s in args.sites:
        t = tiles_for(s, args.tile, args.radius, args.min_n)
        tabs[s] = t
        t.to_file(ROOT / "data" / s / f"tiles_{args.tile}.gpkg", driver="GPKG")
        t.drop(columns="geometry").to_csv(ROOT / "data" / s / f"tiles_{args.tile}.csv", index=False)
        for k in STEPS:
            c = f"rho_{k}"
            if c not in t:
                continue
            v = t[c].dropna()
            dens_r = spearmanr(t["seg_per_km2"], t[c], nan_policy="omit")[0]
            summary.append({"site": s, "step": STEPS[k][2], "tiles": len(v),
                            "rho_p10": v.quantile(0.1), "rho_median": v.median(),
                            "rho_p90": v.quantile(0.9), "corr_with_density": dens_r})
    sm = pd.DataFrame(summary)
    sm.to_csv(ROOT / "reports" / "phase1" / f"tiles_summary_{args.tile}_{args.radius}.csv",
              index=False)
    with pd.option_context("display.width", 160):
        print(sm.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    figure(tabs, args.tile, args.radius, out)
    print("wrote", out / f"fig5_tiles_{args.tile}_{args.radius}.png")


if __name__ == "__main__":
    main()

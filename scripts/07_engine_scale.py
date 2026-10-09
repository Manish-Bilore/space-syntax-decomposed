"""Phase 1, WP2c: does engine agreement depend on segment length relative to the radius?

    python scripts/07_engine_scale.py

Pools every network variant found in data/ (site, site_c0, site_c10d, site_c10dp, site_c20 ...)
and plots cityseer -> depthmapX rank agreement against (median interior segment length / radius).
Median length is read from each network.gpkg; data/median_segment_m.csv is a fallback.
Writes reports/phase1/wp2c_engine_scale.csv and figures/fig7_engine_scale.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#a3a29c", "#e6e5e1"
CITY = {"copenhagen": "#2a78d6", "mumbai_island": "#eb6834"}
LABEL = {"copenhagen": "Copenhagen + Frederiksberg", "mumbai_island": "Mumbai City District"}
STUBBED = ("", "_c20")  # variants consolidated without destubbing


def median_length(name: str, fallback: pd.Series | None) -> float | None:
    f = ROOT / "data" / name / "network.gpkg"
    if f.exists():
        import geopandas as gpd

        seg = gpd.read_file(f, layer="segments")
        return float(seg.loc[seg["interior"].astype(bool)].geometry.length.median())
    if fallback is not None and name in fallback.index:
        return float(fallback[name])
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+", default=["copenhagen", "mumbai_island"])
    args = ap.parse_args()
    fb = ROOT / "data" / "median_segment_m.csv"
    fallback = pd.read_csv(fb, index_col=0).iloc[:, 0] if fb.exists() else None

    rows = []
    for s in args.sites:
        for d in sorted((ROOT / "data").glob(f"{s}*")):
            suffix = d.name[len(s):]
            if not (d / "agreement.csv").exists() or "chord" in suffix or suffix in ("_a", "_b"):
                continue
            med = median_length(d.name, fallback)
            if med is None:
                continue
            t = pd.read_csv(d / "agreement.csv")
            t = t[t.step.str.startswith("engine")]
            for r in t.itertuples():
                rows.append({"site": s, "network": d.name, "stub_free": suffix not in STUBBED,
                             "family": r.family, "radius": r.radius, "median_segment_m": med,
                             "ratio": med / r.radius, "spearman": r.spearman})
    df = pd.DataFrame(rows)
    rep = ROOT / "reports" / "phase1"
    (rep / "figures").mkdir(parents=True, exist_ok=True)
    df.to_csv(rep / "wp2c_engine_scale.csv", index=False)

    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "text.color": INK, "axes.titleweight": "bold", "axes.titlesize": 10})
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.1), sharey=True)
    for ax, fam in zip(axes, ("closeness", "betweenness")):
        d = df[df.family == fam]
        for s in args.sites:
            for free in (False, True):
                p = d[(d.site == s) & (d.stub_free == free)]
                ax.scatter(p.ratio, p.spearman, s=42, zorder=3 if free else 2,
                           facecolor=CITY[s] if free else SURFACE, edgecolor=CITY[s],
                           linewidth=1.6)
        clean = d[d.stub_free]
        rc = spearmanr(clean.ratio, clean.spearman)[0] if len(clean) > 2 else float("nan")
        ax.set_title(f"{fam.capitalize()}", loc="left")
        ax.text(0.98, 0.95, f"stub-free networks: rank corr. {rc:.2f} (n = {len(clean)})",
                transform=ax.transAxes, ha="right", va="top", color=INK2, fontsize=8.5)
        ax.set_xscale("log")
        ax.set_xticks([0.02, 0.05, 0.1, 0.2, 0.3], ["0.02", "0.05", "0.1", "0.2", "0.3"])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlabel("median segment length ÷ radius")
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        print(f"{fam}: stub-free rank corr {rc:.2f} (n={len(clean)})")
    axes[0].set_ylabel("cityseer to depthmapX, Spearman ρ")
    h = [Line2D([0], [0], marker="o", ls="", ms=7, mfc=CITY[s], mec=CITY[s], label=LABEL[s])
         for s in args.sites]
    h += [Line2D([0], [0], marker="o", ls="", ms=7, mfc=INK2, mec=INK2, label="stub-free network"),
          Line2D([0], [0], marker="o", ls="", ms=7, mfc=SURFACE, mec=INK2, mew=1.6,
                 label="consolidated with stubs")]
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.legend(handles=h, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.94))
    fig.suptitle("Engine agreement falls as segments get long relative to the radius",
                 y=0.995, fontsize=11, fontweight="bold")
    for ext in ("png", "svg"):
        fig.savefig(rep / "figures" / f"fig7_engine_scale.{ext}", dpi=220, bbox_inches="tight")
    print("wrote", rep / "figures" / "fig7_engine_scale.png")


if __name__ == "__main__":
    main()

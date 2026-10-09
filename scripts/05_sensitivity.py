"""Phase 1, WP2: sensitivity of the ladder to junction consolidation.

    python scripts/05_sensitivity.py --sites copenhagen mumbai_island --levels 0 10 20

Reads data/<site>_c<level>/agreement.csv (the 10 m run is data/<site>/agreement.csv) and writes
    reports/phase1/wp2_sensitivity.csv          long table
    reports/phase1/wp2_sensitivity_tables.md    step x consolidation tables, per city
    reports/phase1/figures/fig6_consolidation_<r>.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#a3a29c", "#e6e5e1"
CITY = {"copenhagen": "#2a78d6", "mumbai_island": "#eb6834"}
LABEL = {"copenhagen": "Copenhagen + Frederiksberg", "mumbai_island": "Mumbai City District"}
SHORT = {
    "representation: junction -> segment": "Junction to segment",
    "closeness form: harmonic -> NC^2/TD": "Harmonic to NC²/TD",
    "cost: metric -> angular": "Metric to angular",
    "engine + straight pieces: cityseer -> depthmapX": "cityseer to depthmapX",
    "normalisation: NC^2/TD -> NAIN": "NC²/TD to NAIN",
    "normalisation: choice -> NACH": "Choice to NACH",
    "end to end: S1 harmonic vs NAIN": "End to end",
    "end to end: S1 betweenness vs NACH": "End to end",
}
DEFAULT_LEVEL = "10"  # consolidation used by the un-suffixed site folder


def load(sites, levels) -> pd.DataFrame:
    parts = []
    for s in sites:
        for lv in levels:
            f = ROOT / "data" / (s if lv == DEFAULT_LEVEL else f"{s}_c{lv}") / "agreement.csv"
            if not f.exists():
                print(f"  missing {f}")
                continue
            t = pd.read_csv(f)
            t["site"], t["consolidate_m"] = s, str(lv)
            parts.append(t)
    df = pd.concat(parts, ignore_index=True)
    df["consolidate_m"] = pd.Categorical(df["consolidate_m"], [str(v) for v in levels], ordered=True)
    return df


def tables_md(df: pd.DataFrame) -> str:
    out = []
    radii = sorted(df.radius.unique())
    for s in df.site.unique():
        for fam in ("closeness", "betweenness"):
            d = df[(df.site == s) & (df.family == fam)]
            levels = [lv for lv in d.consolidate_m.cat.categories if (d.consolidate_m == lv).any()]
            out += [f"### {LABEL.get(s, s)} — {fam}", "",
                    "ρ at " + " / ".join(f"{r}" for r in radii) + " m", "",
                    "| Step | " + " | ".join(f"{lv} m" for lv in levels) + " |",
                    "|---|" + "---|" * len(levels)]
            for step in d.step.drop_duplicates():
                cells = []
                for lv in levels:
                    v = d[(d.step == step) & (d.consolidate_m == lv)].set_index("radius").spearman
                    cells.append(" ".join(f"{v.get(r, float('nan')):.2f}".replace("0.", ".", 1)
                                          .replace("-.", "−.") for r in radii))
                out.append(f"| {SHORT.get(step, step)} | " + " | ".join(cells) + " |")
            out.append("")
    return "\n".join(out)


def figure(df: pd.DataFrame, radius: int, out: Path) -> None:
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "text.color": INK, "axes.titleweight": "bold", "axes.titlesize": 9.5})
    fams = [("closeness", list(df[df.family == "closeness"].step.drop_duplicates())),
            ("betweenness", list(df[df.family == "betweenness"].step.drop_duplicates()))]
    ncol = max(len(s) for _, s in fams)
    fig, axes = plt.subplots(2, ncol, figsize=(2.25 * ncol, 5.6), sharex=True, sharey=True)
    levels = list(df.consolidate_m.cat.categories)
    xs = list(range(len(levels)))
    for r, (fam, steps) in enumerate(fams):
        for c in range(ncol):
            ax = axes[r, c]
            if c >= len(steps):
                ax.set_visible(False)
                continue
            d = df[(df.family == fam) & (df.step == steps[c])]
            for s in d.site.unique():
                ds = d[d.site == s]
                band = ds.groupby("consolidate_m", observed=False).spearman.agg(["min", "max"]).reindex(levels)
                ax.fill_between(xs, band["min"].to_numpy(float), band["max"].to_numpy(float), color=CITY.get(s, MUTED),
                                alpha=0.14, lw=0)
                v = ds[ds.radius == radius].set_index("consolidate_m").spearman.reindex(levels)
                ax.plot(xs, v.to_numpy(float), color=CITY.get(s, MUTED), lw=2, marker="o", ms=5.5,
                        mec=SURFACE, mew=1.2, label=LABEL.get(s, s))
            ax.set_title(SHORT.get(steps[c], steps[c]), loc="left")
            ax.set_xticks(xs, levels)
            ax.set_ylim(-0.1, 1.02)
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.grid(axis="y", color=GRID, lw=0.8)
            ax.set_axisbelow(True)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            if c == 0:
                ax.set_ylabel(f"{fam.capitalize()}\nSpearman ρ")
            if r == 1 or c >= len(fams[1][1]):
                ax.set_xlabel("consolidation (m; d = destubbed)")
                ax.tick_params(labelbottom=True)
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.legend(h, lab, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.955))
    fig.suptitle(f"How much of the divergence is network cleaning? Line = {radius} m; "
                 "band = range over 400–2000 m", y=0.995, fontsize=11, fontweight="bold")
    for ext in ("png", "svg"):
        fig.savefig(out / f"fig6_consolidation_{radius}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+", default=["copenhagen", "mumbai_island"])
    ap.add_argument("--levels", nargs="+", default=["0", "10", "20"],
                    help="consolidation levels; variants such as 10d (destubbed) are accepted")
    ap.add_argument("--radius", type=int, default=800)
    args = ap.parse_args()
    rep = ROOT / "reports" / "phase1"
    (rep / "figures").mkdir(parents=True, exist_ok=True)
    df = load(args.sites, args.levels)
    df.to_csv(rep / "wp2_sensitivity.csv", index=False)
    (rep / "wp2_sensitivity_tables.md").write_text(tables_md(df))
    figure(df, args.radius, rep / "figures")
    print(tables_md(df))


if __name__ == "__main__":
    main()

"""Phase 1, WP3: nested extents — how much do Space Syntax values depend on where the map stops?

    export DEPTHMAPX=/path/to/depthmapXcli
    python scripts/08_nested.py                                   # Mumbai defaults, cleaned network
    python scripts/08_nested.py --boundary dharavi=dharavi.gpkg   # override any extent with a file
    python scripts/08_nested.py --boundary gnorth=R1234567        # ... or with an OSM relation id

The network is fetched ONCE for the largest extent plus buffer and cleaned (10 m consolidation,
destubbed, parallels merged, unless --consolidate 0). Each run is a subset of it: the streets whose
midpoint lies inside <extent> grown by <buffer>. Every run is analysed with depthmapX, and the
streets of the CORE extent (default Dharavi) are compared across runs.

Run spec "extent@buffer", e.g. dharavi@0 (map clipped at the boundary), dharavi@2000, island@2000.
The last run is the reference. Expectation to test:
  * radius-bounded measures stop changing once the buffer reaches the radius;
  * global (radius n) measures keep changing as the map grows, because they have no catchment.

Writes data/<name>/nested_results.csv and reports/phase1/figures/fig8_nested.png
Global measures on very large maps are slow; runs above --rn-max-pieces skip radius n.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ssx.network import build  # noqa: E402
from ssx.syntax.reference.depthmapx import street_measures  # noqa: E402

EXTENTS = {
    "dharavi": [["Dharavi, Mumbai, Maharashtra, India", "Dharavi, Mumbai",
                 {"suburb": "Dharavi", "city": "Mumbai", "country": "India"}]],
    "gnorth": [["G/North Ward, Mumbai, Maharashtra, India", "G/N Ward, Mumbai",
                "G North Ward, Mumbai", "G-North Ward, Mumbai", "Ward G/N, Mumbai",
                {"city_district": "G/North Ward", "city": "Mumbai", "country": "India"}]],
    "island": build.SITES["mumbai_island"].places,
    "greater": build.SITES["mumbai_island"].places + [[
        "Mumbai Suburban District, Maharashtra, India",
        {"county": "Mumbai Suburban", "state": "Maharashtra", "country": "India"}]],
}
LABEL = {"dharavi": "Dharavi", "gnorth": "G/North ward", "island": "Island city",
         "greater": "Greater Mumbai"}
DEFAULT_RUNS = ["dharavi@0", "dharavi@500", "dharavi@1000", "dharavi@2000", "dharavi@4000",
                "gnorth@2000", "island@2000"]
MIN_AREA_KM2 = {"dharavi": 0.5, "gnorth": 3.0, "island": 30.0, "greater": 200.0}
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#a3a29c", "#e6e5e1"
RADIUS_COLOURS = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # ordinal blue, light -> dark
GLOBAL_COLOUR = "#eb6834"


def parse_runs(specs):
    out = []
    for s in specs:
        ext, _, buf = s.partition("@")
        out.append((ext, float(buf or 0)))
    return out


def _candidates(name: str) -> list:
    out = []
    for entry in EXTENTS.get(name, []):
        out.extend(entry if isinstance(entry, list) else [entry])
    return out


def _valid(name, poly, core) -> str | None:
    """Reason the polygon is not acceptable, or None if it is."""
    area = poly.area / 1e6
    if area < MIN_AREA_KM2.get(name, 0.3):
        return f"area {area:.2f} km² below {MIN_AREA_KM2.get(name, 0.3)} km²"
    if core is not None and poly.intersection(core).area < 0.5 * core.area:
        return "does not contain the core extent"
    return None


def extent_polygon(name: str, override: str | None, crs: int, core=None):
    """Boundary polygon for an extent, or None if nothing acceptable was found.

    Multi-part extents (e.g. greater = island + suburban) are unions of their parts. A geocoded
    result is accepted only if it is large enough and contains the core; this rejects
    same-name places elsewhere (a 'North Bombay Society' for 'G/North Ward').
    """
    if override:
        cfg = build.SiteConfig(name=name, places=[override], crs=crs)
        poly = (build.boundary(cfg, override) if Path(override).exists()
                else build.boundary(cfg)).geometry.iloc[0]
        why = _valid(name, poly, core)
        if why:
            print(f"  WARNING: override for {name}: {why}; using it anyway")
        return poly
    parts = EXTENTS.get(name)
    if not parts:
        print(f"  {name}: unknown extent; pass --boundary {name}=<file or OSM id>")
        return None
    polys = []
    for entry in parts:
        cands = entry if isinstance(entry, list) else [entry]
        got = None
        for q in cands:
            try:
                g = build._geocode_one(q).to_crs(crs)
            except Exception as e:  # noqa: BLE001
                print(f"    {name}: {q!r} failed ({type(e).__name__})")
                continue
            p = unary_union(g.geometry)
            # single-part extents are checked fully here, so a wrong match falls through
            # to the next candidate; multi-part extents are checked as a union below
            why = (_valid(name, p, core if name != "dharavi" else None) if len(parts) == 1
                   else (None if p.area / 1e6 >= 0.3 else f"area {p.area / 1e6:.2f} km²"))
            if why:
                print(f"    {name}: {q!r} rejected ({why})")
                continue
            got = p
            break
        if got is None:
            polys = []
            break
        polys.append(got)
    if not polys:
        print(f"  {name}: no acceptable boundary; skipping. Pass --boundary {name}=<file or R<osm id>>")
        return None
    poly = unary_union(polys)
    why = _valid(name, poly, core if name != "dharavi" else None)
    if why:
        print(f"  {name}: geocoded boundary rejected ({why}); skipping. "
              f"Pass --boundary {name}=<file or R<osm id>>")
        return None
    return poly


def fetch(polys, runs, crs, consolidate, name):
    out = ROOT / "data" / name
    out.mkdir(parents=True, exist_ok=True)
    gpkg = out / "network.gpkg"
    if gpkg.exists():
        print(f"  reusing {gpkg}")
        return gpd.read_file(gpkg, layer="segments")
    big = unary_union([polys[e].buffer(b) for e, b in runs])
    cfg = build.SiteConfig(name=name, places=[], crs=crs, buffer_m=0,
                           consolidate_m=consolidate or None)
    bnd = gpd.GeoDataFrame(geometry=[big], crs=crs)
    print(f"  fetching OSM walk network over {big.area / 1e6:.0f} km² ...", flush=True)
    G = build.fetch_network(cfg, bnd)
    seg = build.graph_to_segments(G)
    if consolidate:
        seg = build.destub(seg, consolidate)
        seg, n = build.merge_parallels(seg, consolidate)
        print(f"  cleaned: destubbed, {n} parallel streets merged")
    seg.to_file(gpkg, layer="segments", driver="GPKG")
    return seg


def figure(res: pd.DataFrame, runs, out: Path, title: str) -> None:
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                         "savefig.facecolor": SURFACE, "font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "text.color": INK, "axes.titleweight": "bold", "axes.titlesize": 10})
    labels = [f"{LABEL.get(e, e)}\n+{b:.0f} m" for e, b in runs[:-1]]
    xs = np.arange(len(labels))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    radii = [r for r in res.radius.unique() if r != "n"]
    for ax, meas in zip(axes, ("nain", "nach")):
        for k, r in enumerate(radii + (["n"] if "n" in set(res.radius) else [])):
            d = res[(res.measure == meas) & (res.radius == r)].set_index("run").reindex(
                [f"{e}@{b:.0f}" for e, b in runs[:-1]])
            col = GLOBAL_COLOUR if r == "n" else RADIUS_COLOURS[min(k, len(RADIUS_COLOURS) - 1)]
            ax.plot(xs, d.spearman.to_numpy(float), color=col, lw=2, marker="o", ms=6,
                    mec=SURFACE, mew=1.2, label="radius n (global)" if r == "n" else f"R{r} m")
        ax.set_xticks(xs, labels, fontsize=8)
        ax.set_ylim(min(0.0, res.spearman.min() - 0.05), 1.02)
        ax.axhline(1, color=MUTED, lw=0.8)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_title(meas.upper(), loc="left")
    e, b = runs[-1]
    axes[0].set_ylabel(f"Spearman ρ vs {LABEL.get(e, e)} +{b:.0f} m\n(core streets only)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.legend(h, lab, loc="upper center", ncol=len(lab), frameon=False, bbox_to_anchor=(0.5, 0.94))
    fig.suptitle(title, y=0.995, fontsize=11, fontweight="bold")
    for ext in ("png", "svg"):
        fig.savefig(out / f"fig8_nested.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="mumbai_nested")
    ap.add_argument("--runs", nargs="+", default=DEFAULT_RUNS)
    ap.add_argument("--core", default="dharavi")
    ap.add_argument("--radii", nargs="+", default=["400", "800", "2000", "n"])
    ap.add_argument("--consolidate", type=float, default=10.0, help="0 = raw OSM topology")
    ap.add_argument("--boundary", action="append", default=[],
                    help="extent=file_or_osm_id; repeatable")
    ap.add_argument("--network", default=None, help="use this segments GeoPackage, skip OSM")
    ap.add_argument("--crs", type=int, default=32643)
    ap.add_argument("--rn-max-pieces", type=int, default=60000)
    ap.add_argument("--no-choice", action="store_true")
    ap.add_argument("--rerun", action="store_true",
                    help="ignore depthmapX output left by earlier runs and recompute everything")
    args = ap.parse_args()

    runs = parse_runs(args.runs)
    overrides = dict(b.split("=", 1) for b in args.boundary)
    names = sorted({e for e, _ in runs} - {args.core})
    print("extents:", ", ".join([args.core] + names), flush=True)
    core_poly = extent_polygon(args.core, overrides.get(args.core), args.crs)
    if core_poly is None:
        raise SystemExit(f"Core extent '{args.core}' has no boundary; pass --boundary.")
    polys = {args.core: core_poly}
    for n in names:
        p = extent_polygon(n, overrides.get(n), args.crs, core=core_poly)
        if p is not None:
            polys[n] = p
    dropped = [f"{e}@{b:.0f}" for e, b in runs if e not in polys]
    runs = [(e, b) for e, b in runs if e in polys]
    if dropped:
        print("  skipping runs:", ", ".join(dropped))
    if len(runs) < 2:
        raise SystemExit("Fewer than two runs left; nothing to compare.")
    for n, p in polys.items():
        print(f"  {n:10s} {p.area / 1e6:8.2f} km²")

    if args.network:
        seg = gpd.read_file(args.network, layer="segments")
    else:
        seg = fetch(polys, runs, args.crs, args.consolidate, args.name)
    seg = seg.to_crs(args.crs)
    mids = seg.geometry.interpolate(0.5, normalized=True)
    core_ids = set(seg.loc[mids.within(polys[args.core]), "seg_id"])
    print(f"network {len(seg)} streets; core '{args.core}' has {len(core_ids)} streets", flush=True)

    per_run = {}
    meta = []
    for e, b in runs:
        key = f"{e}@{b:.0f}"
        sub = seg[mids.within(polys[e].buffer(b))].copy()
        if sub.empty:
            print(f"  {key}: no streets inside; skipped")
            continue
        radii = list(args.radii)
        est_pieces = int(sum(len(g.coords) - 1 for g in sub.geometry))
        if "n" in radii and est_pieces > args.rn_max_pieces:
            radii.remove("n")
            print(f"  {key}: {est_pieces} pieces > --rn-max-pieces, skipping radius n")
        t = time.time()
        print(f"  {key}: {len(sub)} streets, ~{est_pieces} pieces, radii {radii} ...", flush=True)
        m = street_measures(sub, radii, ROOT / "data" / args.name / "runs" / key,
                            choice=not args.no_choice, reuse=not args.rerun)
        if m.attrs.get("matched_share", 1.0) < 0.99:
            print(f"    WARNING: only {m.attrs['matched_share']:.1%} of pieces matched; "
                  "rerun this extent with --rerun")
        per_run[key] = m
        meta.append({"run": key, "extent": e, "buffer_m": b, "streets": len(sub),
                     "pieces": m.attrs.get("pieces"), "seconds": round(time.time() - t)})
        print(f"    done in {time.time() - t:.0f}s", flush=True)

    runs = [(e, b) for e, b in runs if f"{e}@{b:.0f}" in per_run]
    ref_key = f"{runs[-1][0]}@{runs[-1][1]:.0f}"
    ref = per_run[ref_key]
    rows = []
    for key, m in per_run.items():
        if key == ref_key:
            continue
        ids = sorted(core_ids & set(m.index) & set(ref.index))
        for col in m.columns:
            meas, lab = col.rsplit("_", 1)
            if meas not in ("nain", "nach", "integration", "choice") or col not in ref:
                continue
            x, y = m.loc[ids, col].to_numpy(float), ref.loc[ids, col].to_numpy(float)
            ok = np.isfinite(x) & np.isfinite(y)
            rows.append({"run": key, "measure": meas,
                         "radius": "n" if lab == "Rn" else lab[1:], "n": int(ok.sum()),
                         "spearman": spearmanr(x[ok], y[ok])[0] if ok.sum() > 2 else np.nan,
                         "median_rel_change": float(np.median(np.abs(x[ok] - y[ok]) /
                                                              np.maximum(np.abs(y[ok]), 1e-12)))})
    res = pd.DataFrame(rows)
    d = ROOT / "data" / args.name
    res.to_csv(d / "nested_results.csv", index=False)
    pd.DataFrame(meta).to_csv(d / "nested_runs.csv", index=False)
    print(pd.DataFrame(meta).to_string(index=False))
    piv = res[res.measure.isin(["nain", "nach"])].pivot_table(
        index=["measure", "radius"], columns="run", values="spearman")
    piv = piv[[f"{e}@{b:.0f}" for e, b in runs[:-1] if f"{e}@{b:.0f}" in piv.columns]]
    with pd.option_context("display.width", 200):
        print(f"\nSpearman ρ against {ref_key}, {len(core_ids)} core streets:")
        print(piv.round(3).to_string())
    out = ROOT / "reports" / "phase1" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    figure(res, runs, out, f"How much do values for {LABEL.get(args.core, args.core)}'s streets "
                           "depend on where the map stops?")
    print("wrote", out / "fig8_nested.png")


if __name__ == "__main__":
    main()

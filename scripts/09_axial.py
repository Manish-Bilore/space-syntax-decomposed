"""S4 rung: approximate axial map from the street network, axial analysis, intelligibility, synergy.

    export DEPTHMAPX=/path/to/depthmapXcli
    python scripts/09_axial.py --site copenhagen_c10dp
    python scripts/09_axial.py --site mumbai_island_c10dp --tol 8 --angle 30

Axial lines are generated from the centrelines (ssx.syntax.axial_gen: natural streets by
every-best-fit, Douglas-Peucker at `--tol`, ends extended so lines meeting at a junction cross).
depthmapX treats them as an axial map as given (no fewest-line reduction) and computes
connectivity, integration [HH] Rn / R3 and choice Rn / R3.

Outputs in data/<site>/axial[<tag>]/:
    axial.gpkg          layer 'axial' (lines + measures), layer 'streets' (S4_* per street)
    summary.json        map size, line lengths, intelligibility, synergy (all and interior lines)
    agreement_axial.csv S4 vs the S1/S3 ladder columns per radius (interior streets), if
                        data/<site>/ladder.gpkg exists
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssx.compare.agreement import spearman_table  # noqa: E402
from ssx.syntax.axial_gen import axial_lines, transfer_to_streets  # noqa: E402
from ssx.syntax.reimpl.derived import intelligibility, synergy  # noqa: E402
from ssx.syntax.reimpl.topological import axial_analysis, axial_graph_from_lines  # noqa: E402

MEASURES = ["connectivity", "integration_hh_Rn", "integration_hh_R3", "choice_Rn", "choice_R3"]


def measure_axial(ax: gpd.GeoDataFrame, work: Path, engine: str) -> pd.DataFrame:
    if engine == "depthmapx":
        from ssx.syntax.reference import depthmapx as dmx

        dmx.VERBOSE = True
        m = dmx.axial_measures(ax, work, radii="n,3", choice=True)
        print(f"  depthmapX matched {m.attrs['matched_share']:.1%} of {len(ax)} lines")
        return m
    print("  using the Python reimplementation (slow beyond a few thousand lines)")
    G = axial_graph_from_lines(ax.geometry, tol=1e-6)
    return axial_analysis(G, radii=("n", 3), choice="split").reindex(range(len(ax)))


def derived(df: pd.DataFrame) -> dict:
    i = intelligibility(df)
    s = synergy(df)
    lc = np.log(df["connectivity"].clip(lower=1))
    il = intelligibility(df.assign(lc=lc), conn_col="lc")
    return {"n_lines": int(df["integration_hh_Rn"].notna().sum()),
            "intelligibility_r": i["r"], "intelligibility_r2": i["r2"],
            "intelligibility_logconn_r": il["r"],
            "synergy_r": s["r"], "synergy_r2": s["r2"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--tol", type=float, default=8.0, help="Douglas-Peucker tolerance (m)")
    ap.add_argument("--angle", type=float, default=30.0, help="max deflection to continue a stroke")
    ap.add_argument("--extend", type=float, default=None, help="line extension (m), default tol+1")
    ap.add_argument("--engine", choices=["depthmapx", "reimpl"],
                    default="depthmapx" if os.environ.get("DEPTHMAPX") else "reimpl")
    ap.add_argument("--tag", default="", help="suffix for the output folder")
    args = ap.parse_args()

    if args.engine == "depthmapx":
        from ssx.syntax.reference import depthmapx as dmx

        try:
            print(f"depthmapX: {dmx.check_binary()}")
        except FileNotFoundError as e:
            sys.exit(str(e))
    d = ROOT / "data" / args.site
    seg = gpd.read_file(d / "network.gpkg", layer="segments")
    bnd = gpd.read_file(d / "network.gpkg", layer="boundary")
    out = d / f"axial{args.tag}"
    out.mkdir(parents=True, exist_ok=True)
    print(f"[{args.site}] {len(seg)} streets; tol {args.tol} m, angle {args.angle} deg", flush=True)

    t = time.time()
    ax, lin = axial_lines(seg, tol=args.tol, angle_max=args.angle, extend=args.extend)
    n_strokes = int(ax.stroke_id.nunique())
    print(f"  {n_strokes} natural streets -> {len(ax)} axial lines "
          f"({ax.attrs.get('duplicates_merged', 0)} coincident duplicates merged) ({time.time() - t:.0f}s)")

    t = time.time()
    m = measure_axial(ax, out / "depthmapx", args.engine)
    print(f"  axial analysis done in {time.time() - t:.0f}s")
    ax = pd.concat([ax.reset_index(drop=True), m.reset_index(drop=True)], axis=1)
    ax = gpd.GeoDataFrame(ax, geometry="geometry", crs=seg.crs)

    # graph check: depthmapX's connections vs our intersection test on the same lines
    G = axial_graph_from_lines(ax.geometry, tol=1e-6)
    deg = np.array([G.degree(i) for i in range(len(ax))])
    conn_match = float(np.mean(deg[ax.connectivity.notna()] ==
                               ax.connectivity.dropna().to_numpy()))
    # interior lines: midpoint inside the unbuffered boundary
    ax["interior"] = ax.geometry.interpolate(0.5, normalized=True).within(bnd.geometry.iloc[0])
    gen_len = ax.geometry.length - 2 * (args.tol + 1.0 if args.extend is None else args.extend)

    summary = {
        "site": args.site, "tol_m": args.tol, "angle_deg": args.angle,
        "extend_m": args.tol + 1.0 if args.extend is None else args.extend,
        "streets": len(seg), "natural_streets": n_strokes, "axial_lines": len(ax),
        "interior_lines": int(ax.interior.sum()),
        "lines_per_street": len(ax) / len(seg),
        "median_line_m": float(gen_len.median()), "mean_line_m": float(gen_len.mean()),
        "mean_connectivity": float(ax.connectivity.mean()),
        "depthmapx_vs_shapely_connectivity_match": conn_match,
        "all": derived(ax), "interior": derived(ax[ax.interior]),
    }
    print(json.dumps(summary, indent=2))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    # carry back to streets
    vals = ax.set_index("axial_id")[MEASURES]
    st = transfer_to_streets(vals, lin, len(seg)).add_prefix("S4_")
    streets = pd.concat([seg[["seg_id", "interior", "geometry"]].reset_index(drop=True), st], axis=1)
    streets = gpd.GeoDataFrame(streets, geometry="geometry", crs=seg.crs)
    ax.to_file(out / "axial.gpkg", layer="axial", driver="GPKG")
    streets.to_file(out / "axial.gpkg", layer="streets", driver="GPKG")

    lad = d / "ladder.gpkg"
    if not lad.exists():
        print(f"  no {lad.name}: skipping agreement with the ladder")
        return
    L = gpd.read_file(lad, layer="ladder")
    df = L.merge(streets.drop(columns=["geometry", "interior"]), on="seg_id")
    radii = sorted({int(c.split("_")[-1]) for c in L.columns if c.startswith("S3_nain_")})
    rows, pairs = [], []
    steps = [("closeness", "axial global (HH Rn) vs angular NAIN", "S4_integration_hh_Rn", "S3_nain_{r}"),
             ("closeness", "axial local (HH R3) vs angular NAIN", "S4_integration_hh_R3", "S3_nain_{r}"),
             ("closeness", "axial global (HH Rn) vs metric harmonic", "S4_integration_hh_Rn", "S1_harmonic_{r}"),
             ("closeness", "axial connectivity vs angular NAIN", "S4_connectivity", "S3_nain_{r}"),
             ("betweenness", "axial choice Rn vs angular NACH", "S4_choice_Rn", "S3_nach_{r}"),
             ("betweenness", "axial choice R3 vs angular NACH", "S4_choice_R3", "S3_nach_{r}"),
             ("betweenness", "axial choice Rn vs metric betweenness", "S4_choice_Rn", "S1_betweenness_{r}")]
    for r in radii:
        for fam, step, a, b in steps:
            b = b.format(r=r)
            pairs.append((a, b))
            rows.append({"radius": r, "family": fam, "step": step, "a": a, "b": b})
    tab = spearman_table(df, pairs, mask=df["interior"].astype(bool))
    tab = pd.DataFrame(rows).merge(tab, on=["a", "b"])
    tab.to_csv(out / "agreement_axial.csv", index=False)
    with pd.option_context("display.width", 160):
        print(tab[["radius", "family", "step", "n", "spearman", "top10_overlap"]]
              .to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()

"""Run the S0-S3 decomposition ladder on a site's network and write agreement tables.

    export DEPTHMAPX=/path/to/depthmapXcli     # for S3 (recommended)
    python scripts/02_ladder.py --site copenhagen --radii 400 800 1200 2000

Ladder (one design choice changes per step):
    S0  primal graph, metric        node closeness/betweenness       cityseer centrality_shortest
    S1  segment (dual), metric      segment closeness/betweenness    cityseer centrality_shortest
    S2  segment, angular, raw       NC^2/TD ('hillier'), betweenness cityseer centrality_simplest
    S3  segment, angular, SS-normed NAIN, NACH (straight segments)   depthmapX tulip-1024
                                                                     (or our reimplementation)
Outputs in data/<site>/:
    ladder.gpkg        segments with every measure (interior flag kept)
    agreement.csv      Spearman rho and top-10% overlap between adjacent rungs, per radius
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssx.compare.agreement import spearman_table  # noqa: E402
from ssx.network.build import explode_straight  # noqa: E402
from ssx.syntax.reference import cityseer_adapter as csa  # noqa: E402


def s0_primal(seg: gpd.GeoDataFrame, radii: list[int]) -> pd.DataFrame:
    nodes = csa.primal_centrality(seg, radii)
    pts = np.c_[nodes.geometry.x, nodes.geometry.y]
    tree = cKDTree(pts)
    a = np.array([g.coords[0] for g in seg.geometry])
    b = np.array([g.coords[-1] for g in seg.geometry])
    ia, ib = tree.query(a)[1], tree.query(b)[1]
    out = pd.DataFrame(index=seg.index)
    for d in radii:
        for m in ("harmonic", "betweenness"):
            v = nodes[f"cc_{m}_{d}"].to_numpy()
            out[f"S0_{m}_{d}"] = 0.5 * (v[ia] + v[ib])  # segment = mean of its two junctions
    return out


def s1_s2(seg: gpd.GeoDataFrame, radii: list[int]) -> pd.DataFrame:
    cs = csa.segment_centrality(seg, radii, angular=True, metric=True)
    out = pd.DataFrame(index=seg["seg_id"])
    for d in radii:
        out[f"S1_harmonic_{d}"] = cs.get(f"cs_met_harmonic_{d}")
        out[f"S1_hillier_{d}"] = cs.get(f"cs_met_hillier_{d}")
        out[f"S1_betweenness_{d}"] = cs.get(f"cs_met_betweenness_{d}")
        out[f"S2_hillier_{d}"] = cs.get(f"cs_ang_hillier_{d}")
        out[f"S2_betweenness_{d}"] = cs.get(f"cs_ang_betweenness_{d}")
    print(f"  cityseer dropped {cs.attrs.get('segments_lost_in_cleaning', 0)} segments in cleaning")
    return out.reset_index(drop=True)


def chord_pieces(seg: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """One straight chord per street (first vertex -> last vertex). Control for curve explosion."""
    from shapely.geometry import LineString

    geoms = [LineString([g.coords[0], g.coords[-1]]) for g in seg.geometry]
    out = gpd.GeoDataFrame({"parent_seg_id": seg["seg_id"].to_numpy(), "piece": 0},
                           geometry=geoms, crs=seg.crs)
    out = out[out.geometry.length > 0.01].reset_index(drop=True)
    out.insert(0, "piece_id", np.arange(len(out)))
    return out


def s3_syntax(seg: gpd.GeoDataFrame, radii: list[int], work: Path, engine: str,
              geometry: str = "exploded") -> pd.DataFrame:
    pieces = explode_straight(seg) if geometry == "exploded" else chord_pieces(seg)
    work.mkdir(parents=True, exist_ok=True)
    print(f"  S3 ({geometry}): {len(seg)} streets -> {len(pieces)} straight pieces; engine {engine}; "
          f"radii {radii} (the largest radius with choice dominates the run time)", flush=True)
    if engine == "depthmapx":
        from ssx.syntax.reference import depthmapx as dmx

        dmx.VERBOSE = True
        csv = dmx.write_lines_csv(pieces, work / "pieces.csv")
        res = dmx.run_segment(csv, work, radii=",".join(map(str, radii)), radius_type="metric",
                              bins=1024, choice=True, via_axial=False)
        m = res.map
        # depthmapX may reorder or drop pieces: match back by midpoint
        mid_d = np.c_[(m.x1 + m.x2) / 2, (m.y1 + m.y2) / 2]
        mid_p = np.array([g.interpolate(0.5, normalized=True).coords[0] for g in pieces.geometry])
        dist, idx = cKDTree(mid_d).query(mid_p)
        ok = dist < 0.05
        res_df = pd.DataFrame(index=pieces.index)
        for d in radii:
            sfx = f" R{d} metric"
            nc = m[f"T1024 Node Count{sfx}"].to_numpy()[idx]
            td = m[f"T1024 Total Depth{sfx}"].to_numpy()[idx]
            ch = m[f"T1024 Choice{sfx}"].to_numpy()[idx]
            res_df[f"integration_{d}"] = np.where(ok & (td > 0), nc ** 2 / np.where(td > 0, td, 1), np.nan)
            res_df[f"nain_{d}"] = np.where(ok, nc ** 1.2 / (td + 2), np.nan)
            res_df[f"choice_{d}"] = np.where(ok, ch, np.nan)
            res_df[f"nach_{d}"] = np.where(ok, np.log(ch + 1) / np.log(td + 3), np.nan)
        print(f"  depthmapX matched {ok.mean():.1%} of {len(pieces)} straight pieces")
    else:
        from ssx.syntax.reimpl.angular import angular_analysis, segment_map_from_lines

        print("  using the Python reimplementation (slow on city-scale networks)")
        sm = segment_map_from_lines(pieces.geometry)
        a = angular_analysis(sm, radii=tuple(radii), bins=1024, choice=True)
        res_df = pd.DataFrame(index=pieces.index)
        for d in radii:
            for m in ("integration", "nain", "choice", "nach"):
                res_df[f"{m}_{d}"] = a[f"{m}_R{d}"]

    # pieces -> parent street: length-weighted mean (a representation choice; documented)
    res_df["w"] = pieces.geometry.length.to_numpy()
    res_df["parent"] = pieces["parent_seg_id"].to_numpy()
    out = {}
    for d in radii:
        for m in ("integration", "nain", "choice", "nach"):
            g = res_df.dropna(subset=[f"{m}_{d}"]).groupby("parent")
            out[f"S3_{m}_{d}"] = g.apply(lambda x: np.average(x[f"{m}_{d}"], weights=x["w"]))
    return pd.DataFrame(out).reindex(seg["seg_id"]).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--radii", type=int, nargs="+", default=[400, 800, 1200, 2000])
    ap.add_argument("--engine", choices=["depthmapx", "reimpl"],
                    default="depthmapx" if os.environ.get("DEPTHMAPX") else "reimpl")
    ap.add_argument("--skip-s3", action="store_true")
    ap.add_argument("--s3-geometry", choices=["exploded", "chord"], default="exploded",
                    help="exploded: curves split into straight pieces (standard); chord: one "
                         "straight line per street (control that isolates curve handling)")
    ap.add_argument("--tag", default="", help="suffix for output files, e.g. _chord")
    args = ap.parse_args()

    d = ROOT / "data" / args.site
    seg = gpd.read_file(d / "network.gpkg", layer="segments")
    print(f"[{args.site}] {len(seg)} segments, {int(seg.interior.sum())} interior; radii {args.radii}")

    parts = [seg]
    for name, fn in [("S0", lambda: s0_primal(seg, args.radii)),
                     ("S1+S2", lambda: s1_s2(seg, args.radii))]:
        t = time.time()
        parts.append(fn())
        print(f"  {name} done in {time.time() - t:.0f}s")
    if not args.skip_s3:
        t = time.time()
        parts.append(s3_syntax(seg, args.radii, d / f"depthmapx{args.tag}", args.engine,
                               args.s3_geometry))
        print(f"  S3 done in {time.time() - t:.0f}s")
    out = pd.concat([p.reset_index(drop=True) for p in parts], axis=1)
    out = gpd.GeoDataFrame(out, geometry="geometry", crs=seg.crs)
    out.to_file(d / f"ladder{args.tag}.gpkg", layer="ladder", driver="GPKG")

    # Each pair differs by ONE design choice; the label says which.
    pairs, labels = [], []
    for r in args.radii:
        steps = [
            ("closeness", "representation: junction -> segment", f"S0_harmonic_{r}", f"S1_harmonic_{r}"),
            ("closeness", "closeness form: harmonic -> NC^2/TD", f"S1_harmonic_{r}", f"S1_hillier_{r}"),
            ("closeness", "cost: metric -> angular", f"S1_hillier_{r}", f"S2_hillier_{r}"),
            ("closeness", "engine + straight pieces: cityseer -> depthmapX", f"S2_hillier_{r}", f"S3_integration_{r}"),
            ("closeness", "normalisation: NC^2/TD -> NAIN", f"S3_integration_{r}", f"S3_nain_{r}"),
            ("closeness", "end to end: S1 harmonic vs NAIN", f"S1_harmonic_{r}", f"S3_nain_{r}"),
            ("betweenness", "representation: junction -> segment", f"S0_betweenness_{r}", f"S1_betweenness_{r}"),
            ("betweenness", "cost: metric -> angular", f"S1_betweenness_{r}", f"S2_betweenness_{r}"),
            ("betweenness", "engine + straight pieces: cityseer -> depthmapX", f"S2_betweenness_{r}", f"S3_choice_{r}"),
            ("betweenness", "normalisation: choice -> NACH", f"S3_choice_{r}", f"S3_nach_{r}"),
            ("betweenness", "end to end: S1 betweenness vs NACH", f"S1_betweenness_{r}", f"S3_nach_{r}"),
        ]
        for fam, step, a, b in steps:
            pairs.append((a, b))
            labels.append({"radius": r, "family": fam, "step": step, "a": a, "b": b})
    tab = spearman_table(out, pairs, mask=out["interior"].astype(bool))
    tab = pd.DataFrame(labels).merge(tab, on=["a", "b"])
    tab.to_csv(d / f"agreement{args.tag}.csv", index=False)
    with pd.option_context("display.width", 160):
        print(tab[["radius", "family", "step", "n", "spearman", "top10_overlap"]]
              .to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()

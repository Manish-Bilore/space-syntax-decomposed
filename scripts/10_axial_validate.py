"""Validate generated axial maps against a hand-drawn reference axial map.

    export DEPTHMAPX=/path/to/depthmapXcli
    # OSM centrelines over the reference extent (needs internet), tolerance sweep:
    python scripts/10_axial_validate.py \
        --reference ~/depthmapX/testdata/barnsbury_extended1_axial.csv --crs 27700 --fetch
    # or any segments layer already on disk:
    python scripts/10_axial_validate.py --reference ref.csv --crs 27700 --network data/x/network.gpkg

The reference (Ref,x1,y1,x2,y2) and every generated map are run through depthmapX as axial
maps over the same extent, so edge effects are shared. Generated lines are matched to the
reference by sampling each reference line every `--step` m and taking the nearest generated
line within `--radius` m whose direction is within `--angle-match` degrees. Per reference
line, the generated value is the mean over its matched samples.

Reported per tolerance:
    lines, median length, mean connectivity, intelligibility, synergy   (both maps)
    recall      share of reference samples matched
    precision   share of generated line length within --radius of a reference line
    Spearman    reference vs generated, per measure, over reference lines >= 50% matched
Writes data/<name>/axial_validate.csv (and the fetched network, if --fetch).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from shapely.geometry import LineString
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssx.network import build  # noqa: E402
from ssx.syntax.axial_gen import axial_lines  # noqa: E402
from ssx.syntax.reference import depthmapx as dmx  # noqa: E402
from ssx.syntax.reimpl.derived import intelligibility, synergy  # noqa: E402

MEASURES = ["connectivity", "integration_hh_Rn", "integration_hh_R3", "choice_Rn", "choice_R3"]


def read_reference(path: str, crs: int) -> gpd.GeoDataFrame:
    df = pd.read_csv(path)
    g = [LineString([(a, b), (c, d)]) for a, b, c, d in df[["x1", "y1", "x2", "y2"]].to_numpy()]
    ref = gpd.GeoDataFrame({"ref_id": np.arange(len(g))}, geometry=g, crs=crs)
    return ref[ref.length > 0.01].reset_index(drop=True)


STREETS_FILTER = ('["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified|residential|'
                  'living_street|pedestrian|motorway_link|trunk_link|primary_link|secondary_link|'
                  'tertiary_link"]["area"!~"yes"]')


def fetch_osm(ref: gpd.GeoDataFrame, crs: int, consolidate: float, out: Path,
              osm_filter: str = "walk") -> gpd.GeoDataFrame:
    gpkg = out / "network.gpkg"
    if gpkg.exists():
        print(f"  reusing {gpkg}")
        return gpd.read_file(gpkg, layer="segments")
    hull = ref.union_all().convex_hull
    bnd = gpd.GeoDataFrame(geometry=[hull], crs=crs)
    cfg = build.SiteConfig(name=out.name, places=[], crs=crs, buffer_m=0.0,
                           consolidate_m=consolidate or None,
                           custom_filter=STREETS_FILTER if osm_filter == "streets" else None)
    seg = build.graph_to_segments(build.fetch_network(cfg, bnd))
    if consolidate:
        seg = build.destub(seg, consolidate)
        seg, n = build.merge_parallels(seg, consolidate)
        print(f"  cleaned at {consolidate} m: destubbed, {n} parallel streets merged")
    seg["interior"] = build.interior_mask(seg, bnd)
    out.mkdir(parents=True, exist_ok=True)
    seg.to_file(gpkg, layer="segments", driver="GPKG")
    bnd.to_file(gpkg, layer="boundary", driver="GPKG")
    return seg


def _unit(g: LineString) -> np.ndarray:
    (x1, y1), (x2, y2) = g.coords[0], g.coords[-1]
    v = np.array([x2 - x1, y2 - y1])
    return v / (np.linalg.norm(v) or 1.0)


def match(ref: gpd.GeoDataFrame, gen: gpd.GeoDataFrame, step: float, radius: float,
          angle: float) -> tuple[pd.DataFrame, float, float]:
    """Per reference line: mean of matched generated values and matched share."""
    gl = list(gen.geometry)
    tree = STRtree(gl)
    gu = np.array([_unit(g) for g in gl])
    cos_min = np.cos(np.radians(angle))
    rows = []
    n_s = n_hit = 0
    for rid, g in zip(ref.ref_id, ref.geometry):
        u = _unit(g)
        ts = np.arange(step / 2, g.length, step) if g.length > step else [g.length / 2]
        hits = []
        for t in ts:
            p = g.interpolate(t)
            cand = tree.query(p, predicate="dwithin", distance=radius)
            cand = [int(c) for c in cand if abs(gu[c] @ u) >= cos_min]
            n_s += 1
            if cand:
                n_hit += 1
                hits.append(min(cand, key=lambda c: gl[c].distance(p)))
        rec = {"ref_id": rid, "share": len(hits) / len(ts)}
        if hits:
            v = gen.iloc[hits]
            for m in MEASURES:
                rec[m] = float(np.nanmean(v[m].to_numpy(float)))
        rows.append(rec)
    # precision: generated length near any reference line (sampled the same way)
    rl = list(ref.geometry)
    rtree = STRtree(rl)
    p_s = p_hit = 0
    for g in gl:
        for t in (np.arange(step / 2, g.length, step) if g.length > step else [g.length / 2]):
            p_s += 1
            p_hit += len(rtree.query(g.interpolate(t), predicate="dwithin", distance=radius)) > 0
    return pd.DataFrame(rows), n_hit / max(n_s, 1), p_hit / max(p_s, 1)


def map_stats(df: pd.DataFrame, geoms, ext: float = 0.0) -> dict:
    L = np.array([g.length for g in geoms]) - 2 * ext
    return {"lines": int(df["integration_hh_Rn"].notna().sum()), "median_len_m": float(np.median(L)),
            "mean_connectivity": float(df["connectivity"].mean()),
            "intelligibility_r": intelligibility(df)["r"], "synergy_r": synergy(df)["r"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True, help="Ref,x1,y1,x2,y2 CSV of the reference map")
    ap.add_argument("--crs", type=int, required=True, help="projected CRS of the reference")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--fetch", action="store_true", help="OSM walk network over the reference hull")
    src.add_argument("--network", help="GeoPackage with a 'segments' layer (centrelines)")
    ap.add_argument("--consolidate", type=float, default=10.0, help="for --fetch; 0 = raw")
    ap.add_argument("--osm-filter", choices=["walk", "streets"], default="walk",
                    help="walk: osmnx walk network (footways, paths, service roads included); "
                         "streets: named-street classes only (no footway/path/service/steps), "
                         "closer to what a hand-drawn axial map covers")
    ap.add_argument("--overpass-url", default=None,
                    help="Overpass endpoint if the default is busy, e.g. "
                         "https://overpass.kumi.systems/api or https://overpass.private.coffee/api")
    ap.add_argument("--timeout", type=int, default=180, help="Overpass request timeout (s)")
    ap.add_argument("--name", default="barnsbury_osm", help="output folder under data/")
    ap.add_argument("--ref-shift", type=float, nargs=2, default=None, metavar=("DX", "DY"),
                    help="translate the reference by DX DY metres (from 11_axial_diag coverage)")
    ap.add_argument("--tols", type=float, nargs="+", default=[4, 8, 12, 16])
    ap.add_argument("--angle", type=float, default=30.0, help="stroke continuation angle")
    ap.add_argument("--step", type=float, default=10.0)
    ap.add_argument("--radius", type=float, default=15.0)
    ap.add_argument("--angle-match", type=float, default=30.0)
    args = ap.parse_args()
    try:
        print(f"depthmapX: {dmx.check_binary()}")
    except FileNotFoundError as e:
        sys.exit(str(e))

    args.reference = str(Path(args.reference).expanduser())
    out = ROOT / "data" / args.name
    out.mkdir(parents=True, exist_ok=True)
    ref = read_reference(args.reference, args.crs)
    if args.ref_shift:
        ref["geometry"] = ref.geometry.translate(*args.ref_shift)
        print(f"reference shifted by {args.ref_shift} m")
    if args.fetch:
        import osmnx as ox

        ox.settings.log_console = True          # shows Overpass slot waits / retries
        ox.settings.requests_timeout = args.timeout
        if args.overpass_url:
            ox.settings.overpass_url = args.overpass_url
        print(f"fetching OSM walk network over the reference hull "
              f"({ox.settings.overpass_url}, timeout {args.timeout}s) ...", flush=True)
    seg = (fetch_osm(ref, args.crs, args.consolidate, out, args.osm_filter) if args.fetch
           else gpd.read_file(args.network, layer="segments").to_crs(args.crs))
    # same extent for both maps: centrelines clipped to the reference hull
    hull = ref.union_all().convex_hull
    seg = seg[seg.geometry.intersects(hull)].copy()
    seg["geometry"] = seg.geometry.intersection(hull)
    seg = seg[seg.geometry.geom_type == "LineString"]
    seg = seg[seg.length > 0.01].reset_index(drop=True)
    print(f"reference {len(ref)} lines; centrelines {len(seg)} streets inside its hull")

    rm = dmx.axial_measures(ref, out / "dmx_reference")
    refm = pd.concat([ref, rm], axis=1)
    rows = [{"map": "reference", "tol_m": np.nan, **map_stats(rm, ref.geometry)}]
    for tol in args.tols:
        ax, _ = axial_lines(seg, tol=tol, angle_max=args.angle)
        gm = dmx.axial_measures(ax, out / f"dmx_tol{tol:g}")
        gen = pd.concat([ax.reset_index(drop=True), gm], axis=1)
        per, recall, precision = match(refm, gen, args.step, args.radius, args.angle_match)
        rec = {"map": "generated", "tol_m": tol, **map_stats(gm, ax.geometry, tol + 1.0),
               "recall": recall, "precision": precision}
        good = per[per.share >= 0.5].merge(refm[["ref_id"] + MEASURES], on="ref_id",
                                           suffixes=("_gen", "_ref"))
        rec["ref_lines_matched"] = len(good)
        for m in MEASURES:
            x, y = good[f"{m}_ref"].to_numpy(float), good[f"{m}_gen"].to_numpy(float)
            ok = np.isfinite(x) & np.isfinite(y)
            rec[f"rho_{m}"] = float(spearmanr(x[ok], y[ok])[0]) if ok.sum() > 2 else np.nan
        rows.append(rec)
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items()}))
    tab = pd.DataFrame(rows)
    tab.to_csv(out / "axial_validate.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(tab.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()

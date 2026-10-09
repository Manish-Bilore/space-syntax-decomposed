"""Fetch and clean the OSM walk network for a site.

    python scripts/01_fetch_network.py --site copenhagen
    python scripts/01_fetch_network.py --site mumbai_island

Writes data/<site>/network.gpkg with layers: segments, boundary, meta.
Needs internet access to Nominatim and Overpass (osmnx).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssx.network import build  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, choices=sorted(build.SITES))
    ap.add_argument("--buffer", type=float, default=None, help="override buffer (m)")
    ap.add_argument("--consolidate", type=float, default=None,
                    help="junction consolidation tolerance (m); 0 disables")
    ap.add_argument("--boundary", default=None,
                    help="vector file to use as the boundary instead of geocoding")
    ap.add_argument("--destub", action="store_true",
                    help="after consolidation, remove the stub pieces it appends at merged "
                         "junctions (see build.destub)")
    ap.add_argument("--merge-parallel", action="store_true",
                    help="after consolidation, keep one street where several join the same two "
                         "junctions within the consolidation tolerance (dual carriageways)")
    ap.add_argument("--name", default=None,
                    help="output folder name (default: site). Use for sensitivity variants, "
                         "e.g. --consolidate 0 --name copenhagen_c0")
    ap.add_argument("--osmid", default=None,
                    help="OSM relation id for the boundary, e.g. R1234567")
    args = ap.parse_args()

    cfg = build.SITES[args.site]
    if args.osmid:
        cfg.places = [args.osmid]
    if args.buffer is not None:
        cfg.buffer_m = args.buffer
    if args.consolidate is not None:
        cfg.consolidate_m = args.consolidate or None

    if args.name:
        cfg.name = args.name
    out = ROOT / "data" / cfg.name
    out.mkdir(parents=True, exist_ok=True)
    gpkg = out / "network.gpkg"

    print(f"[{cfg.name}] boundary ...", flush=True)
    bnd = build.boundary(cfg, args.boundary)
    print(f"[{cfg.name}] OSM {cfg.network_type} network (buffer {cfg.buffer_m:.0f} m) ...", flush=True)
    G = build.fetch_network(cfg, bnd)
    seg = build.graph_to_segments(G)
    before = build.stub_stats(seg)
    if args.destub and cfg.consolidate_m:
        seg = build.destub(seg, cfg.consolidate_m)
        cfg.notes.append(f"destubbed at {cfg.consolidate_m} m")
    merged = 0
    if args.merge_parallel and cfg.consolidate_m:
        seg, merged = build.merge_parallels(seg, cfg.consolidate_m)
        cfg.notes.append(f"parallel streets merged at {cfg.consolidate_m} m: {merged} dropped")
    after = build.stub_stats(seg)
    seg["interior"] = build.interior_mask(seg, bnd)
    summary = build.network_summary(seg, seg["interior"], float(bnd.area.iloc[0]) / 1e6)

    seg.to_file(gpkg, layer="segments", driver="GPKG")
    bnd.to_file(gpkg, layer="boundary", driver="GPKG")
    gpd.GeoDataFrame({"json": [build.meta_json(cfg, summary)]}, geometry=[None],
                     crs=seg.crs).to_file(gpkg, layer="meta", driver="GPKG")
    print(f"[{cfg.name}] wrote {gpkg}")
    for k, v in summary.items():
        print(f"  {k:28s} {v}")
    print(f"  {'stub_end_share':28s} {before['stub_end_share']:.1%}"
          + (f" -> {after['stub_end_share']:.1%} after destub" if args.destub else ""))
    if args.merge_parallel:
        print(f"  {'parallel_streets_merged':28s} {merged}")
    print(f"  {'stub_turn_deg_per_km':28s} {before['stub_turn_deg_per_km']}"
          + (f" -> {after['stub_turn_deg_per_km']}" if args.destub else ""))


if __name__ == "__main__":
    main()

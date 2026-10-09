"""Diagnostics for WP4 (no network access needed; uses files written by 09/10).

    # A. why does the OSM-generated map miss the reference? (offset, distance, line length, place)
    python scripts/11_axial_diag.py coverage \
        --reference ~/depthmapX/testdata/barnsbury_extended1_axial.csv --crs 27700 \
        --network data/barnsbury_osm/network.gpkg
    # B. where do depthmapX's axial connections differ from a plain geometric intersection test?
    python scripts/11_axial_diag.py connections --site copenhagen_c10dp

A writes data/<network folder>/coverage_diag.gpkg (reference lines with match share, centrelines)
for a visual check in QGIS. B writes data/<site>/axial/connection_diff.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssx.syntax.reimpl.topological import axial_graph_from_lines  # noqa: E402


def _sample(geoms, step):
    pts, own, dirs = [], [], []
    for i, g in enumerate(geoms):
        L = g.length
        if L <= 0:
            continue
        ts = np.arange(step / 2, L, step) if L > step else [L / 2]
        for t in ts:
            p = g.interpolate(t)
            q = g.interpolate(min(t + 1.0, L))
            r = g.interpolate(max(t - 1.0, 0))
            v = np.array([q.x - r.x, q.y - r.y])
            pts.append((p.x, p.y))
            own.append(i)
            dirs.append(v / (np.linalg.norm(v) or 1))
    return np.array(pts), np.array(own), np.array(dirs)


def coverage(args):
    df = pd.read_csv(Path(args.reference).expanduser())
    ref = gpd.GeoDataFrame(
        {"ref_id": np.arange(len(df))},
        geometry=[LineString([(a, b), (c, d)]) for a, b, c, d in df[["x1", "y1", "x2", "y2"]].values],
        crs=args.crs)
    seg = gpd.read_file(args.network, layer="segments").to_crs(args.crs)
    hull = ref.union_all().convex_hull
    seg = seg[seg.intersects(hull)]
    print(f"reference: {len(ref)} lines, {ref.length.sum() / 1e3:.1f} km; "
          f"centrelines in hull: {len(seg)}, {seg.length.sum() / 1e3:.1f} km "
          f"({seg.length.sum() / hull.area * 1e3:.1f} vs {ref.length.sum() / hull.area * 1e3:.1f} km/km2)")

    rp, rown, rdir = _sample(list(ref.geometry), 10.0)
    cp, _, cdir = _sample(list(seg.geometry), 2.0)
    tree = cKDTree(cp)

    # 1. offset scan (distance only, tight 5 m threshold so the peak is sharp): a datum or grid
    #    shift shows up as a peak away from (0, 0)
    def scan_at(grid, D=5.0):
        best = (0.0, 0.0, -1.0)
        for dx in grid:
            for dy in grid:
                r = np.isfinite(tree.query(rp + [dx, dy], distance_upper_bound=D)[0]).mean()
                if r > best[2] + 1e-9:
                    best = (dx, dy, r)
        return best
    r0 = np.isfinite(tree.query(rp, distance_upper_bound=5)[0]).mean()
    cx, cy, _ = scan_at(np.arange(-100, 101, 5.0))
    fine = np.arange(-6, 6.1, 1.0)
    best = (0, 0, -1)
    for dx in cx + fine:
        for dy in cy + fine:
            r = np.isfinite(tree.query(rp + [dx, dy], distance_upper_bound=5)[0]).mean()
            if r > best[2] + 1e-9:
                best = (dx, dy, r)
    print(f"\n1. offset scan (recall within 5 m): at (0,0) {r0:.3f}; "
          f"best at dx={best[0]:+.0f} dy={best[1]:+.0f} m: {best[2]:.3f}")
    if np.hypot(best[0], best[1]) > 3 and best[2] > r0 + 0.05:
        print("   -> systematic offset: shift the reference by (dx, dy) and rerun 10_axial_validate "
              "with --ref-shift DX DY")

    # 2. recall by distance threshold, with and without the direction test
    d1, _ = tree.query(rp, distance_upper_bound=100)
    print("\n2. share of reference samples with a centreline within D m")
    print("   D      any dir   within 30 deg")
    cmin = np.cos(np.radians(30))
    for D in (5, 10, 15, 25, 50, 100):
        anyd = (d1 <= D).mean()
        if D <= 50:
            nb = tree.query_ball_point(rp, D)
            ok = np.array([bool(n) and (np.abs(cdir[n] @ rdir[i]) >= cmin).any()
                           for i, n in enumerate(nb)])
            print(f"   {D:<6} {anyd:8.3f} {ok.mean():12.3f}")
        else:
            print(f"   {D:<6} {anyd:8.3f}")
    # 3. per reference line: matched share vs line length and position
    hit = d1 <= 15
    per = pd.DataFrame({"ref": rown, "hit": hit}).groupby("ref").hit.mean()
    ref["match_share"] = per.reindex(ref.ref_id).to_numpy()
    ref["length_m"] = ref.length
    ref["dist_to_centroid_m"] = ref.geometry.centroid.distance(hull.centroid)
    print("\n3. matched share by reference line length")
    print(ref.groupby(pd.cut(ref.length_m, [0, 50, 100, 200, 400, 1e5])).match_share
          .agg(["count", "mean"]).round(3).to_string())
    print("   by distance from the map centre")
    print(ref.groupby(pd.qcut(ref.dist_to_centroid_m, 4)).match_share
          .agg(["count", "mean"]).round(3).to_string())
    out = Path(args.network).parent / "coverage_diag.gpkg"
    ref.to_file(out, layer="reference", driver="GPKG")
    seg.to_file(out, layer="centrelines", driver="GPKG")
    print(f"\nwrote {out} (style 'reference' by match_share)")


def connections(args):
    d = ROOT / "data" / args.site / f"axial{args.tag}"
    ax = gpd.read_file(d / "axial.gpkg", layer="axial")
    w = d / "depthmapx"
    m = pd.read_csv(w / "axial_map.csv")
    c = pd.read_csv(w / "axial_conn.csv")
    # depthmapX Ref -> our row (midpoint match, as in depthmapx.axial_measures)
    cur = np.array([(g.coords[0][0], g.coords[0][1], g.coords[-1][0], g.coords[-1][1])
                    for g in ax.geometry])
    dist, idx = cKDTree(np.c_[(m.x1 + m.x2) / 2, (m.y1 + m.y2) / 2]).query(
        np.c_[(cur[:, 0] + cur[:, 2]) / 2, (cur[:, 1] + cur[:, 3]) / 2])
    # one depthmapX Ref can stand for several of our rows (depthmapX drops duplicate lines)
    ref2rows: dict = {}
    for i, k in enumerate(idx):
        if dist[i] < 0.05:
            ref2rows.setdefault(int(m.Ref.iloc[k]), []).append(i)
    E_d = {tuple(sorted((i, j))) for a, b in zip(c.refA, c.refB) if a != b
           for i in ref2rows.get(a, []) for j in ref2rows.get(b, []) if i != j}
    dups = sum(len(v) - 1 for v in ref2rows.values())
    print(f"lines: ours {len(ax)}, depthmapX {len(m)} (duplicates collapsed by depthmapX: {dups})")
    G = axial_graph_from_lines(ax.geometry, tol=1e-6)
    E_s = {tuple(sorted(e)) for e in G.edges()}
    only_d, only_s = E_d - E_s, E_s - E_d
    print(f"edges: depthmapX {len(E_d)}, geometric {len(E_s)}, both {len(E_d & E_s)}, "
          f"only depthmapX {len(only_d)}, only geometric {len(only_s)}")
    geoms = list(ax.geometry)
    sid = ax.stroke_id.to_numpy()
    from shapely.geometry import Point
    from shapely.strtree import STRtree
    tree = STRtree(geoms)

    def describe(pairs, label):
        rows = []
        for a, b in pairs:
            ga, gb = geoms[a], geoms[b]
            ua = np.subtract(ga.coords[-1], ga.coords[0])
            ub = np.subtract(gb.coords[-1], gb.coords[0])
            cos = abs(ua @ ub) / (np.linalg.norm(ua) * np.linalg.norm(ub))
            inter = ga.intersection(gb)
            pt = inter.representative_point() if not inter.is_empty else None
            de_a = min(pt.distance(Point(ga.coords[0])), pt.distance(Point(ga.coords[-1]))) if pt else np.nan
            de_b = min(pt.distance(Point(gb.coords[0])), pt.distance(Point(gb.coords[-1]))) if pt else np.nan
            n_through = len(tree.query(pt.buffer(0.01), predicate="intersects")) if pt else 0
            rows.append({"set": label, "a": a, "b": b, "x": pt.x if pt else np.nan,
                         "y": pt.y if pt else np.nan, "end_dist_a": de_a, "end_dist_b": de_b,
                         "lines_through_point": n_through,
                         "angle_deg": np.degrees(np.arccos(min(cos, 1))),
                         "same_stroke": sid[a] == sid[b], "gap_m": ga.distance(gb),
                         "overlap_type": inter.geom_type if not inter.is_empty else "none",
                         "len_a": ga.length, "len_b": gb.length})
        return pd.DataFrame(rows)

    t = pd.concat([describe(only_d, "only_depthmapx"), describe(only_s, "only_geometric")])
    if len(t):
        t["angle_class"] = pd.cut(t.angle_deg, [-0.1, 1, 5, 30, 90])
        print(t.groupby(["set", "same_stroke", "overlap_type", "angle_class"], observed=True)
              .size().rename("pairs").to_string())
        print(t.groupby("set")[["end_dist_a", "end_dist_b", "lines_through_point", "len_a", "len_b"]]
              .describe().T.round(2).to_string())
    t.to_csv(d / "connection_diff.csv", index=False)
    print(f"wrote {d / 'connection_diff.csv'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("coverage")
    a.add_argument("--reference", required=True)
    a.add_argument("--crs", type=int, required=True)
    a.add_argument("--network", required=True)
    b = sub.add_parser("connections")
    b.add_argument("--site", required=True)
    b.add_argument("--tag", default="")
    args = ap.parse_args()
    coverage(args) if args.cmd == "coverage" else connections(args)


if __name__ == "__main__":
    main()

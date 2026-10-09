"""Approximate axial maps from street centrelines.

A true axial map is the fewest set of longest straight lines that cover the open space and
make all its connections (Hillier & Hanson 1984); depthmapX derives it from building outlines.
That is not feasible at city scale, and building outlines are incomplete in informal areas.

This module follows the centreline route of Liu & Jiang (2012, "Defining and generating axial
lines from street center lines for better understanding of urban morphologies", IJGIS 26(8)):

1. **Natural streets (strokes).** At every junction, street ends are paired by "every best fit":
   all pairs whose deflection is <= `angle_max` are sorted by deflection and paired greedily,
   best first. Chains of paired streets form strokes.
2. **Straightening.** Each stroke is simplified with Douglas-Peucker at tolerance `tol` (about
   half a street width). Each straight piece of the simplified stroke is one axial line.
3. **Connection.** Lines are extended by `extend` metres at both ends so that lines meeting at a
   junction (or at a kink of the same stroke) cross, which is how axial connections are found.

Every axial line keeps its stroke and the interval of the stroke it covers, so axial values can
be carried back to the original streets with length weights (`transfer_to_streets`).

Known limits: lines can pick up spurious connections where an extension reaches a nearby
parallel street; grade separations (bridges, flyovers) are not unlinked; tol and angle_max change
the map and must be reported.
"""
from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString


def _same(a, b, atol: float = 1e-6) -> bool:
    # absolute test only: np.allclose's default rtol (1e-5) is ~5 m at UTM-sized coordinates
    return abs(a[0] - b[0]) <= atol and abs(a[1] - b[1]) <= atol


def _key(xy, q: float = 0.01):
    return (round(xy[0] / q), round(xy[1] / q))


def _end_dir(g: LineString, at_start: bool, probe: float) -> np.ndarray:
    """Unit vector pointing from the junction INTO the street, measured over `probe` metres."""
    L = g.length
    d = min(probe, L / 2) if L > 0 else 0
    if at_start:
        p0, p1 = g.interpolate(0), g.interpolate(d)
    else:
        p0, p1 = g.interpolate(L), g.interpolate(L - d)
    v = np.array([p1.x - p0.x, p1.y - p0.y])
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def deflection_deg(a: np.ndarray, b: np.ndarray) -> float:
    """Deflection when passing from one street into the other (0 = straight on)."""
    c = float(np.clip(a @ b, -1.0, 1.0))
    return 180.0 - math.degrees(math.acos(c))


def strokes(seg: gpd.GeoDataFrame, angle_max: float = 30.0, probe: float = 15.0):
    """Group streets into natural streets.

    Returns a list of strokes; each stroke is a list of (street_index, forward) in order.
    """
    geoms = list(seg.geometry)
    ends: dict = {}
    for i, g in enumerate(geoms):
        cs = g.coords
        ends.setdefault(_key(cs[0]), []).append((i, 0))
        ends.setdefault(_key(cs[-1]), []).append((i, 1))
    link: dict = {}
    for lst in ends.values():
        if len(lst) < 2:
            continue
        cand = []
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                (i, wi), (j, wj) = lst[a], lst[b]
                if i == j:
                    continue
                da = _end_dir(geoms[i], wi == 0, probe)
                db = _end_dir(geoms[j], wj == 0, probe)
                d = deflection_deg(da, db)
                if d <= angle_max:
                    cand.append((d, lst[a], lst[b]))
        cand.sort(key=lambda t: t[0])
        used: set = set()
        for _, x, y in cand:
            if x in used or y in used:
                continue
            link[x], link[y] = y, x
            used.update((x, y))

    seen = np.zeros(len(geoms), bool)
    out = []
    for i in range(len(geoms)):
        if seen[i]:
            continue
        seen[i] = True
        seq = [(i, True)]
        cur = (i, 1)                       # walk forward from the end of street i
        while cur in link:
            j, wj = link[cur]
            if seen[j]:
                break
            seen[j] = True
            seq.append((j, wj == 0))       # entered at its start -> traversed forward
            cur = (j, 1 - wj)
        cur = (i, 0)                       # walk backward from the start of street i
        while cur in link:
            j, wj = link[cur]
            if seen[j]:
                break
            seen[j] = True
            seq.insert(0, (j, wj == 1))    # j must END at the shared junction
            cur = (j, 1 - wj)
        out.append(seq)
    return out


def _stroke_geometry(geoms, seq):
    coords: list = []
    pieces = []  # (street index, start offset, end offset) along the stroke
    pos = 0.0
    for i, fwd in seq:
        cs = list(geoms[i].coords)
        if not fwd:
            cs = cs[::-1]
        if coords and _same(coords[-1], cs[0]):
            cs = cs[1:]
        coords.extend(cs)
        L = geoms[i].length
        pieces.append((i, pos, pos + L))
        pos += L
    return coords, pieces


def axial_lines(seg: gpd.GeoDataFrame, tol: float = 8.0, angle_max: float = 30.0,
                extend: float | None = None, probe: float = 15.0, min_length: float = 1.0):
    """Approximate axial map from street centrelines.

    Returns (axial, lineage):
      axial    GeoDataFrame: axial_id, stroke_id, s0, s1 (interval along the stroke), geometry
      lineage  DataFrame: street_index, axial_id, overlap_m  (for transfer_to_streets)
    """
    ext = tol + 1.0 if extend is None else extend
    geoms = list(seg.geometry)
    rows, lin = [], []
    aid = 0
    for sid, seq in enumerate(strokes(seg, angle_max, probe)):
        coords, pieces = _stroke_geometry(geoms, seq)
        if len(coords) < 2:
            continue
        cum = np.r_[0.0, np.cumsum(np.hypot(*np.diff(np.asarray(coords)[:, :2], axis=0).T))]
        simp = list(LineString(coords).simplify(tol, preserve_topology=False).coords)
        # Douglas-Peucker keeps a subset of the original vertices: locate them in order
        idx, k = [], 0
        for p in simp:
            while k < len(coords) and not _same(coords[k], p):
                k += 1
            idx.append(min(k, len(coords) - 1))
        made = []  # (aid, s0, s1) of this stroke's lines
        for a, b in zip(idx[:-1], idx[1:]):
            p, q = np.asarray(coords[a][:2]), np.asarray(coords[b][:2])
            L = np.linalg.norm(q - p)
            if L < min_length:
                continue
            u = (q - p) / L
            line = LineString([p - u * ext, q + u * ext])
            rows.append((aid, sid, cum[a], cum[b], line))
            made.append((aid, cum[a], cum[b]))
            aid += 1
        if not made:
            continue
        for i, c0, c1 in pieces:
            cover = [(a_, min(s1, c1) - max(s0, c0)) for a_, s0, s1 in made]
            cover = [(a_, ov) for a_, ov in cover if ov > 0]
            if not cover:
                # street lies wholly inside a dropped sub-min_length piece (or has zero length):
                # give it to the line nearest along the stroke
                mid = 0.5 * (c0 + c1)
                a_ = min(made, key=lambda t: max(t[1] - mid, mid - t[2], 0.0))[0]
                cover = [(a_, max(c1 - c0, 1e-3))]
            lin.extend((i, a_, ov) for a_, ov in cover)
    axial = gpd.GeoDataFrame(rows, columns=["axial_id", "stroke_id", "s0", "s1", "geometry"],
                             crs=seg.crs)
    lineage = pd.DataFrame(lin, columns=["street_index", "axial_id", "overlap_m"])
    # Coincident lines: streets duplicated in the network (e.g. multi-edges left by junction
    # consolidation) give identical axial lines. depthmapX silently drops all but one on import,
    # so its neighbours lose a connection there; keep one line and merge the lineage instead.
    key = [tuple(sorted(((round(g.coords[0][0], 3), round(g.coords[0][1], 3)),
                         (round(g.coords[-1][0], 3), round(g.coords[-1][1], 3)))))
           for g in axial.geometry]
    first: dict = {}
    remap = np.array([first.setdefault(k, i) for i, k in enumerate(key)])
    n_dup = int((remap != np.arange(len(remap))).sum())
    if n_dup:
        keep = np.unique(remap)
        new_id = -np.ones(len(remap), int)
        new_id[keep] = np.arange(len(keep))
        axial = axial.iloc[keep].reset_index(drop=True)
        axial["axial_id"] = np.arange(len(axial))
        lineage["axial_id"] = new_id[remap[lineage["axial_id"].to_numpy()]]
        lineage = lineage.groupby(["street_index", "axial_id"], as_index=False)["overlap_m"].sum()
    axial.attrs["duplicates_merged"] = n_dup
    return axial, lineage


def transfer_to_streets(values: pd.DataFrame, lineage: pd.DataFrame, n_streets: int) -> pd.DataFrame:
    """Length-weighted mean of axial values over the axial lines covering each street.

    `values` is indexed by axial_id. Returns a frame indexed 0..n_streets-1.
    """
    d = lineage.merge(values, left_on="axial_id", right_index=True, how="inner")
    cols = [c for c in values.columns]
    num = d[cols].multiply(d["overlap_m"], axis=0).groupby(d["street_index"]).sum()
    den = d.groupby("street_index")["overlap_m"].sum()
    return num.divide(den, axis=0).reindex(range(n_streets))

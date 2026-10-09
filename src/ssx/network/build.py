"""Street network construction: boundary -> OSM walk network -> cleaned segment table.

Every cleaning choice here changes Space Syntax results, so each one is a parameter with the
value used recorded in the output (gdf.attrs and the GeoPackage 'meta' layer).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString
from shapely.ops import unary_union


@dataclass
class SiteConfig:
    name: str
    places: list                      # each entry: a query, a list of fallback queries, a
                                      # structured dict, or an OSM id like "R123456";
                                      # resolved parts are unioned into the boundary
    crs: int                          # projected CRS in metres
    buffer_m: float = 2000.0          # >= largest radius analysed, to suppress edge effects
    network_type: str = "walk"
    consolidate_m: float | None = 10.0  # merge junction clusters (dual carriageways, offsets)
    custom_filter: str | None = None
    notes: list[str] = field(default_factory=list)


SITES = {
    "copenhagen": SiteConfig(
        name="copenhagen",
        places=["Københavns Kommune, Denmark", "Frederiksberg Kommune, Denmark"],
        crs=25832,
        notes=["Matched window to the Mumbai island city: similar extent, water-bounded."],
    ),
    "mumbai_island": SiteConfig(
        name="mumbai_island",
        places=[[
            "Mumbai City District, Maharashtra, India",
            {"county": "Mumbai City", "state": "Maharashtra", "country": "India"},
            "Mumbai City district",
            "Mumbai City, Maharashtra, India",
        ]],
        crs=32643,
        notes=["Mumbai City district (island city). Contains formal fabric and Dharavi.",
               "OSM under-maps informal lanes: results here are the 'without lanes' case."],
    ),
}


def _geocode_one(place) -> gpd.GeoDataFrame:
    """Resolve one boundary entry, trying fallbacks until Nominatim returns a polygon."""
    import osmnx as ox

    candidates = place if isinstance(place, list) else [place]
    errors = []
    for q in candidates:
        try:
            if isinstance(q, str) and q[:1] in "RWN" and q[1:].isdigit():
                g = ox.geocode_to_gdf(q, by_osmid=True)
            else:
                g = ox.geocode_to_gdf(q)
            if g.geom_type.isin(["Polygon", "MultiPolygon"]).all():
                print(f"  boundary: {q!r} -> {g['display_name'].iloc[0] if 'display_name' in g else 'ok'}")
                return g
            errors.append(f"{q!r}: not a polygon")
        except Exception as e:  # noqa: BLE001 - try the next fallback
            errors.append(f"{q!r}: {type(e).__name__}: {str(e)[:120]}")
    raise RuntimeError(
        "No boundary polygon found. Tried:\n  " + "\n  ".join(errors) +
        "\nFix: find the area on openstreetmap.org, copy its relation id and run with "
        "--osmid R<id>, or pass --boundary <file.gpkg/.geojson/.shp>.")


def boundary(cfg: SiteConfig, boundary_file: str | None = None) -> gpd.GeoDataFrame:
    if boundary_file:
        b = gpd.read_file(boundary_file)
        b = gpd.GeoDataFrame(geometry=[unary_union(b.geometry)], crs=b.crs)
        return b.to_crs(cfg.crs)
    parts = [_geocode_one(p) for p in cfg.places]
    b = gpd.GeoDataFrame(geometry=[unary_union(pd.concat(parts).geometry)], crs=parts[0].crs)
    return b.to_crs(cfg.crs)


def fetch_network(cfg: SiteConfig, bnd: gpd.GeoDataFrame):
    """OSM walk network inside the buffered boundary, projected and undirected."""
    import osmnx as ox

    poly = bnd.buffer(cfg.buffer_m).to_crs(4326).iloc[0]
    G = ox.graph_from_polygon(poly, network_type=cfg.network_type, simplify=True,
                              custom_filter=cfg.custom_filter, retain_all=False)
    G = ox.project_graph(G, to_crs=f"EPSG:{cfg.crs}")
    if cfg.consolidate_m:
        G = ox.consolidate_intersections(G, tolerance=cfg.consolidate_m, rebuild_graph=True,
                                         dead_ends=False)
    return ox.convert.to_undirected(G)


def graph_to_segments(G) -> gpd.GeoDataFrame:
    """One row per street edge (junction to junction), parallel duplicates dropped."""
    import osmnx as ox

    edges = ox.graph_to_gdfs(G, nodes=False).reset_index()
    edges = edges[edges.geometry.length > 0.01]
    key = edges.apply(lambda r: tuple(sorted((r["u"], r["v"]))) + (round(r.geometry.length, 1),),
                      axis=1)
    edges = edges.loc[~key.duplicated()].copy()
    keep = [c for c in ("u", "v", "highway", "name", "length") if c in edges]
    seg = edges[keep + ["geometry"]].copy()
    for c in ("highway", "name"):
        if c in seg:
            seg[c] = seg[c].astype(str)
    seg = seg.reset_index(drop=True)
    seg.insert(0, "seg_id", np.arange(len(seg)))
    return seg


def _turn_deg(a, b, c) -> float:
    v1 = np.subtract(b, a)
    v2 = np.subtract(c, b)
    n = np.linalg.norm(v1) * np.linalg.norm(v2)
    if n == 0:
        return 0.0
    return float(np.degrees(np.arccos(np.clip(np.dot(v1, v2) / n, -1.0, 1.0))))


def stub_stats(seg: gpd.GeoDataFrame, max_len: float = 10.0, min_turn: float = 30.0) -> dict:
    """How many street ends start with a short piece followed by a sharp turn.

    Junction consolidation (osmnx) keeps each street's original line and appends a straight
    stub from its old endpoint to the merged junction point. Read as straight pieces, a stub is
    a turn that does not exist on the ground. This counts them: an end is a 'stub end' when its
    first piece is <= max_len metres and the turn into the next piece is >= min_turn degrees.
    Raw OSM has some naturally, so compare the same thresholds across consolidation levels.
    """
    ends = stubs = 0
    angle_sum = 0.0
    for g in seg.geometry:
        cs = np.asarray(g.coords)[:, :2]
        if len(cs) < 3:
            ends += 2
            continue
        for a, b, c in ((cs[0], cs[1], cs[2]), (cs[-1], cs[-2], cs[-3])):
            ends += 1
            if np.hypot(*(b - a)) <= max_len:
                t = _turn_deg(a, b, c)
                if t >= min_turn:
                    stubs += 1
                    angle_sum += t
    n = len(seg)
    km = float(seg.geometry.length.sum()) / 1000
    pieces = int(sum(len(g.coords) - 1 for g in seg.geometry))
    return {"streets": n, "network_km": round(km, 1), "pieces": pieces,
            "pieces_per_street": round(pieces / n, 2), "pieces_per_km": round(pieces / km, 1),
            "stub_ends": stubs, "stub_end_share": round(stubs / max(ends, 1), 4),
            "stub_turn_deg_per_km": round(angle_sum / km, 1)}


def destub(seg: gpd.GeoDataFrame, tol: float) -> gpd.GeoDataFrame:
    """Remove consolidation stubs: drop the old endpoint vertex where an end piece is <= tol.

    The street then runs straight from the merged junction point to its next vertex. A 2-vertex
    street with a 4 m stub becomes a line skewed by ~2 degrees instead of carrying a 90-degree
    kink. Streets keep their junction endpoints, so connectivity is unchanged.
    """
    out = []
    for g in seg.geometry:
        cs = list(g.coords)
        if len(cs) > 2 and np.hypot(cs[1][0] - cs[0][0], cs[1][1] - cs[0][1]) <= tol:
            del cs[1]
        if len(cs) > 2 and np.hypot(cs[-2][0] - cs[-1][0], cs[-2][1] - cs[-1][1]) <= tol:
            del cs[-2]
        out.append(LineString(cs))
    res = seg.copy()
    res["geometry"] = out
    return res


def merge_parallels(seg: gpd.GeoDataFrame, tol: float) -> tuple[gpd.GeoDataFrame, int]:
    """Keep one street where several run between the same two junctions within `tol` of each other.

    After consolidation the two carriageways of a divided road (or a road and its separately
    mapped pavement) join the same pair of merged junctions. They are one street for walking
    analysis. Among streets sharing both junctions, the shortest is kept and any other whose
    Hausdorff distance to a kept one is <= tol is dropped. Returns (segments, number dropped).
    """
    if "u" not in seg or "v" not in seg:
        return seg, 0
    key = [tuple(sorted((a, b))) for a, b in zip(seg["u"], seg["v"])]
    drop = []
    groups: dict = {}
    for i, k in enumerate(key):
        if k[0] != k[1]:
            groups.setdefault(k, []).append(i)
    geoms = seg.geometry.to_numpy()
    for idx in groups.values():
        if len(idx) < 2:
            continue
        idx = sorted(idx, key=lambda i: geoms[i].length)
        kept = [idx[0]]
        for i in idx[1:]:
            if any(geoms[i].hausdorff_distance(geoms[j]) <= tol for j in kept):
                drop.append(i)
            else:
                kept.append(i)
    out = seg.drop(index=seg.index[drop]).reset_index(drop=True)
    out["seg_id"] = np.arange(len(out))
    return out, len(drop)


def interior_mask(seg: gpd.GeoDataFrame, bnd: gpd.GeoDataFrame) -> pd.Series:
    """True for segments whose midpoint lies inside the unbuffered boundary.

    Only interior segments are reported; the buffer exists so they see a full catchment.
    """
    mids = seg.geometry.interpolate(0.5, normalized=True)
    return mids.within(bnd.geometry.iloc[0])


def explode_straight(seg: gpd.GeoDataFrame, id_col: str = "seg_id") -> gpd.GeoDataFrame:
    """Split polylines into straight 2-point pieces (depthmapX segments are straight).

    A curved street becomes several segments with small turns between them. This is a
    representation choice in its own right and changes angular depth along curves.
    """
    rows = []
    for sid, g in zip(seg[id_col], seg.geometry):
        cs = list(g.coords)
        for k in range(len(cs) - 1):
            if cs[k] != cs[k + 1]:
                rows.append((sid, k, LineString([cs[k], cs[k + 1]])))
    out = gpd.GeoDataFrame(rows, columns=["parent_" + id_col, "piece", "geometry"], crs=seg.crs)
    out.insert(0, "piece_id", np.arange(len(out)))
    return out


def network_summary(seg: gpd.GeoDataFrame, interior: pd.Series, area_km2: float) -> dict:
    s = seg.loc[interior]
    return {
        "segments_interior": int(len(s)),
        "segments_total": int(len(seg)),
        "network_km_interior": round(float(s.geometry.length.sum()) / 1000, 1),
        "area_km2": round(area_km2, 1),
        "segment_density_per_km2": round(len(s) / area_km2, 1),
        "median_segment_m": round(float(s.geometry.length.median()), 1),
    }


def meta_json(cfg: SiteConfig, summary: dict) -> str:
    return json.dumps({"config": asdict(cfg), "summary": summary}, indent=2, ensure_ascii=False)

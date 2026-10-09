"""cityseer as a second reference engine, aligned back to our segment ids.

cityseer works on a primal graph (junctions = nodes, streets = edges) or its dual
(street segments = nodes, junction turns = edges). On the dual:
  * centrality_simplest  -> angular (least-angle) closeness / betweenness  ~ Space Syntax S2
  * centrality_shortest  -> metric closeness / betweenness on segments     ~ S1
and on the primal graph:
  * centrality_shortest  -> classic node-based metric centrality           ~ S0

Differences from depthmapX worth knowing (they are part of the comparison, not bugs):
  * the distance threshold is a network distance between dual node midpoints along the
    route used, measured by cityseer's own conventions;
  * 'hillier' = density^2 / farness, i.e. NC^2/TD, but density excludes the origin and
    farness is in cityseer's angular units;
  * graph cleaning merges parallel edges / tiny loops unless disabled.
Compare ranks, not raw values.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd


def _quiet():
    import logging
    logging.getLogger("cityseer").setLevel(logging.WARNING)


def build_graphs(segments: gpd.GeoDataFrame, id_col: str = "seg_id"):
    """Primal and dual cityseer graphs from a GeoDataFrame of segment LineStrings."""
    from cityseer.tools import graphs, io

    _quiet()
    seg = segments[[id_col, "geometry"]].copy()
    G = io.nx_from_generic_geopandas(seg)
    G_dual = graphs.nx_to_dual(G)
    return G, G_dual


def _dual_seg_ids(G, G_dual, nodes_gdf: gpd.GeoDataFrame, id_col: str) -> pd.Series:
    """Map each dual node back to the id carried by its primal edge."""
    ids = []
    for key in nodes_gdf.index:
        nd = G_dual.nodes[key]
        a, b = nd["primal_edge_node_a"], nd["primal_edge_node_b"]
        k = int(str(key).rsplit("_k", 1)[1])
        ids.append(G.edges[a, b, k].get(id_col, np.nan) if G.has_edge(a, b, k) else np.nan)
    return pd.Series(ids, index=nodes_gdf.index, name=id_col)


def segment_centrality(segments: gpd.GeoDataFrame, distances: list[int],
                       id_col: str = "seg_id", angular: bool = True,
                       metric: bool = True) -> pd.DataFrame:
    """Angular and/or metric centrality on the dual graph, one row per input segment id.

    Columns: cs_{kind}_{measure}_{d}, kind in {ang, met}, measure in
    {density, farness, harmonic, hillier, betweenness}.
    """
    from cityseer.metrics import networks
    from cityseer.tools import io

    G, G_dual = build_graphs(segments, id_col)
    nodes_gdf, _, ns = io.network_structure_from_nx(G_dual)
    base = nodes_gdf.copy()
    out = pd.DataFrame(index=nodes_gdf.index)
    out[id_col] = _dual_seg_ids(G, G_dual, nodes_gdf, id_col)

    if angular:
        r = networks.centrality_simplest(ns, base.copy(), distances=distances)
        for d in distances:
            for m in ("density", "farness", "harmonic", "hillier", "betweenness"):
                col = f"cc_{m}_{d}_ang"
                if col in r:
                    out[f"cs_ang_{m}_{d}"] = r[col]
    if metric:
        r = networks.centrality_shortest(ns, base.copy(), distances=distances)
        for d in distances:
            for m in ("density", "farness", "harmonic", "hillier", "betweenness"):
                col = f"cc_{m}_{d}"
                if col in r:
                    out[f"cs_met_{m}_{d}"] = r[col]
    out = out.dropna(subset=[id_col])
    out[id_col] = out[id_col].astype(int)
    lost = len(segments) - out[id_col].nunique()
    out.attrs["segments_lost_in_cleaning"] = int(lost)
    return out.groupby(id_col).first()


def primal_centrality(segments: gpd.GeoDataFrame, distances: list[int]) -> gpd.GeoDataFrame:
    """S0: metric centrality on primal junction nodes (classic network-science view)."""
    from cityseer.metrics import networks
    from cityseer.tools import io

    _quiet()
    G = io.nx_from_generic_geopandas(segments[["geometry"]].copy())
    nodes_gdf, _, ns = io.network_structure_from_nx(G)
    return networks.centrality_shortest(ns, nodes_gdf, distances=distances)

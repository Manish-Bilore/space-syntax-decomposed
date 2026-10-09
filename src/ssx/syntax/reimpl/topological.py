"""Topological (axial / convex) Space Syntax measures, reimplemented from first principles.

Input is an undirected graph whose nodes are spaces (axial lines, convex spaces) and whose
edges are adjacency (lines intersect / spaces share a boundary). Depth is counted in steps.

Every formula is written to match depthmapX (salalib/axialmodules/axialintegration.cpp and
genlib/pafmath.h) so values can be compared one-to-one:

    k   = node count, INCLUDING the root (depthmapX `node_count`)
    TD  = sum of step depths from root to every other node within radius
    MD  = TD / (k - 1)
    RA  = 2 (MD - 1) / (k - 2)
    D_k = 2 (k (log2((k + 2) / 3) - 1) + 1) / ((k - 1)(k - 2))     Hillier & Hanson diamond value
    RRA = RA / D_k
    Integration [HH] = 1 / RRA = D_k / RA

Radius r keeps nodes with depth <= r (depthmapX breaks when depth > radius).

Choice (betweenness) counts ORDERED pairs, i.e. each journey is counted in both directions,
as depthmapX does. Two variants:

    "split"  : Brandes. Where several shortest paths tie, credit is split equally.
               Deterministic; the expected-value version of choice.
    "random" : one shortest path per (origin, destination), chosen by depthmapX's procedure of
               expanding the frontier in random order. This is what depthmapX actually reports,
               so its axial choice is seed-dependent wherever paths tie.
"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import pandas as pd

RadiusT = int | str  # integer steps, or "n" for the whole system


def dvalue(k: float) -> float:
    """Hillier & Hanson D-value (Kruger 1989 form, as in depthmapX)."""
    return 2.0 * (k * (math.log2((k + 2.0) / 3.0) - 1.0) + 1.0) / ((k - 1.0) * (k - 2.0))


def pvalue(k: float) -> float:
    """P-value: RA of the root of a k-node 'pyramid'. Alternative normaliser (depthmapX)."""
    return 2.0 * (k - math.log2(k) - 1.0) / ((k - 1.0) * (k - 2.0))


def teklenburg(k: float, td: float) -> float:
    """Teklenburg integration, as corrected in depthmapX (31.01.11)."""
    return math.log(0.5 * (k - 2.0)) / math.log(td - k + 1.0)


def _cutoff(radius: RadiusT) -> int | None:
    return None if radius == "n" else int(radius)


def _label(radius: RadiusT) -> str:
    return "Rn" if radius == "n" else f"R{radius}"


@dataclass
class DepthProfile:
    """Result of one rooted BFS: the justified graph summarised."""

    root: object
    depths: dict  # node -> step depth (root at 0)
    levels: list[list] = field(default_factory=list)  # justified graph: nodes at each depth

    @property
    def node_count(self) -> int:
        return len(self.depths)

    @property
    def total_depth(self) -> int:
        return sum(self.depths.values())

    @property
    def max_depth(self) -> int:
        return max(self.depths.values())


def justified_graph(G: nx.Graph, root, radius: RadiusT = "n") -> DepthProfile:
    """Depth of every node from `root`, grouped by level (the 'justified graph')."""
    depths = nx.single_source_shortest_path_length(G, root, cutoff=_cutoff(radius))
    levels: list[list] = [[] for _ in range(max(depths.values()) + 1)]
    for n, d in depths.items():
        levels[d].append(n)
    return DepthProfile(root=root, depths=depths, levels=levels)


def integration_from_profile(k: int, td: float) -> dict[str, float]:
    """MD, RA, RRA, Integration [HH], [P-value], [Tekl] from node count and total depth.

    Returns NaN where depthmapX writes -1 (k <= 2, or MD <= 1 i.e. the root sees everything
    in one step and is 'infinitely' integrated).
    """
    nan = float("nan")
    out = dict(node_count=k, total_depth=td, mean_depth=nan, ra=nan, rra=nan,
               integration_hh=nan, integration_pv=nan, integration_tekl=nan)
    if k <= 1:
        return out
    md = td / (k - 1)
    out["mean_depth"] = md
    if k > 2 and md > 1.0:
        ra = 2.0 * (md - 1.0) / (k - 2)
        out["ra"] = ra
        out["rra"] = ra / dvalue(k)
        out["integration_hh"] = dvalue(k) / ra
        out["integration_pv"] = pvalue(k) / ra
        if td - k + 1 > 1:
            out["integration_tekl"] = teklenburg(k, td)
    return out


def control(G: nx.Graph) -> dict:
    """Control = sum over neighbours of 1 / neighbour's connectivity."""
    return {v: sum(1.0 / G.degree(u) for u in G.neighbors(v)) if G.degree(v) else float("nan")
            for v in G}


def controllability(G: nx.Graph) -> dict:
    """Connectivity / (nodes within 2 steps, excluding the root). depthmapX definition."""
    out = {}
    for v in G:
        if G.degree(v) == 0:
            out[v] = float("nan")
            continue
        within2 = nx.single_source_shortest_path_length(G, v, cutoff=2)
        out[v] = G.degree(v) / (len(within2) - 1)
    return out


def choice_split(G: nx.Graph, radius: RadiusT = "n") -> dict:
    """Brandes betweenness on step depth, ordered pairs, ties split equally, radius-bounded."""
    cutoff = _cutoff(radius)
    C = dict.fromkeys(G, 0.0)
    for s in G:
        # BFS with path counting
        S: list = []
        P: dict = {v: [] for v in G}
        sigma = dict.fromkeys(G, 0.0)
        dist = {s: 0}
        sigma[s] = 1.0
        Q = deque([s])
        while Q:
            v = Q.popleft()
            if cutoff is not None and dist[v] >= cutoff:
                S.append(v)
                continue
            S.append(v)
            for w in G.neighbors(v):
                if w not in dist:
                    dist[w] = dist[v] + 1
                    Q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    P[w].append(v)
        # dependency accumulation
        delta = dict.fromkeys(S, 0.0)
        for w in reversed(S):
            for v in P[w]:
                delta[v] += sigma[v] / sigma[w] * (1.0 + delta[w])
            if w != s:
                C[w] += delta[w]
    return C


def choice_random(G: nx.Graph, radius: RadiusT = "n", seed: int = 0) -> dict:
    """depthmapX-style choice: one BFS tree per root, frontier expanded in random order.

    For every node discovered at depth >= 2, +1 is added to each intermediate node on the
    tree path back to the root. Origins and destinations get nothing.
    """
    rng = random.Random(seed)
    cutoff = _cutoff(radius)
    C = dict.fromkeys(G, 0.0)
    for s in G:
        parent = {s: None}
        frontier = [s]
        depth = 1
        while frontier and (cutoff is None or depth <= cutoff):
            nxt = []
            pending = frontier[:]
            while pending:
                idx = rng.randrange(len(pending))
                v = pending.pop(idx)
                for w in G.neighbors(v):
                    if w in parent:
                        continue
                    parent[w] = v
                    nxt.append(w)
                    here = v
                    while here != s:
                        C[here] += 1.0
                        here = parent[here]
            frontier = nxt
            depth += 1
    return C


def axial_analysis(
    G: nx.Graph,
    radii: tuple[RadiusT, ...] = ("n", 3),
    choice: str | None = "split",
    seed: int = 0,
) -> pd.DataFrame:
    """Full axial/convex analysis. One row per node, columns suffixed by radius label.

    Column names mirror depthmapX where a counterpart exists.
    """
    rows: dict = {v: {"connectivity": G.degree(v)} for v in G}
    for v, c in control(G).items():
        rows[v]["control"] = c
    for v, c in controllability(G).items():
        rows[v]["controllability"] = c

    for r in radii:
        lab = _label(r)
        for v in G:
            prof = justified_graph(G, v, r)
            vals = integration_from_profile(prof.node_count, prof.total_depth)
            for key, val in vals.items():
                rows[v][f"{key}_{lab}"] = val
        if choice is not None:
            fn = choice_split if choice == "split" else (
                lambda g, rr: choice_random(g, rr, seed=seed))
            ch = fn(G, r)
            n_sys = G.number_of_nodes()
            for v in G:
                rows[v][f"choice_{lab}"] = ch[v]
                # depthmapX 'Choice [Norm]': ordered-pair count / ((n-1)(n-2)/2), n = node count
                # within radius of the node itself.
                k = rows[v][f"node_count_{lab}"] if r != "n" else n_sys
                rows[v][f"choice_norm_{lab}"] = (
                    ch[v] / ((k - 1) * (k - 2) / 2.0) if k > 2 else float("nan"))

    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def axial_graph_from_lines(lines, tol: float = 1e-6) -> nx.Graph:
    """Axial graph: one node per line, an edge where two lines intersect or touch.

    `lines` is a sequence of shapely LineStrings (node id = position in the sequence).
    Lines are buffered by `tol` so that endpoints landing on another line connect.
    """
    from shapely.strtree import STRtree

    lines = list(lines)
    tree = STRtree(lines)
    G = nx.Graph()
    G.add_nodes_from(range(len(lines)))
    for i, ln in enumerate(lines):
        for j in tree.query(ln.buffer(tol), predicate="intersects"):
            j = int(j)
            if j > i:
                G.add_edge(i, j)
    return G

"""Angular segment analysis (Turner 2007; Hillier & Iida 2005), reimplemented.

Representation
--------------
A segment map is a set of straight-ish segments joined at their ends. Moving from segment A
into segment B costs the turn angle between them, in units where 90 deg = 1 (so 0..2).
Walking straight on costs 0.

Search runs over DIRECTED states (segment, end it is heading towards). This matters: the cost
of leaving a segment depends on which end you leave by. The root is entered at depth 0 in both
directions. A segment's depth is the lower of its two directed depths.

Semantics follow depthmapX (salalib/segmmodules/segmtulip.cpp) and are checked against it:

  * Metric radius R: a segment is reached only if
        dist(root midpoint -> far end of the previous segment) + 0.5 * len(segment) <= R
    i.e. midpoint-to-midpoint distance measured ALONG THE LEAST-ANGLE ROUTE, not along the
    metric shortest path. A segment that is too far by the least-angle route can still be
    reached later by a costlier-but-shorter route; the search keeps it open for that.
  * Node count NC includes the root; total depth TD sums angular depths (root = 0).
  * Integration (depthmapX >= 10) = NC^2 / TD.
  * Ties in angular depth are broken by SHORTER metric distance first, then last-in-first-out
    (depthmapX keeps each bin sorted by metric depth, connector.h). This decides which of
    several equal-angle routes is 'the' route, and so affects choice and radius catchments.
  * Choice: one least-angle path per ordered (origin, destination) pair; +1 to every segment
    strictly between. Ordered pairs, i.e. both directions.
  * Tulip binning (optional): angle costs are quantised to integer bins exactly as depthmapX
    does for `-st tulip -stb B`. With bins=None costs stay continuous ('angular full').

Post-hoc normalisations (not computed by depthmapX itself; Hillier, Yang & Turner 2012):
    NAIN = NC^1.2 / (TD + 2)
    NACH = log(CH + 1) / log(TD + 3)
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class SegmentMap:
    """Segments plus directed connections.

    conns[(s, e)] lists (t, et, w): from the end `e` of segment `s` (0 = first coord, 1 = last)
    you can enter segment `t` through its end `et`, at turn cost `w` (90 deg = 1).
    """

    n: int
    lengths: np.ndarray
    conns: dict[tuple[int, int], list[tuple[int, int, float]]]
    midpoints: np.ndarray | None = None

    @property
    def n_connections(self) -> int:
        return sum(len(v) for v in self.conns.values())


def turn_cost(arrive_vec, depart_vec) -> float:
    """Angle between arrival direction and departure direction, 90 deg = 1."""
    a = np.asarray(arrive_vec, float)
    b = np.asarray(depart_vec, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    c = float(np.clip(a @ b / (na * nb), -1.0, 1.0))
    return math.degrees(math.acos(c)) / 90.0


def segment_map_from_lines(lines, snap: float = 1e-6) -> SegmentMap:
    """Build a segment map from LineStrings that meet at their ENDPOINTS.

    Crossings without a shared vertex are not connections (the caller must split first;
    depthmapX's axial->segment conversion does that splitting). Turn angles use the direction
    of the first/last vertex pair of each line.
    """
    lines = list(lines)
    n = len(lines)
    lengths = np.array([ln.length for ln in lines])
    key = lambda xy: (round(xy[0] / snap), round(xy[1] / snap))  # noqa: E731
    at_point: dict = {}
    ends = []
    for i, ln in enumerate(lines):
        cs = list(ln.coords)
        # end 0: point cs[0]; heading OUT of the segment through end 0 = cs[0] - cs[1]
        # end 1: point cs[-1]; heading out = cs[-1] - cs[-2]
        out0 = np.subtract(cs[0], cs[1])
        out1 = np.subtract(cs[-1], cs[-2])
        ends.append((out0, out1))
        at_point.setdefault(key(cs[0]), []).append((i, 0))
        at_point.setdefault(key(cs[-1]), []).append((i, 1))
    conns: dict = {(i, e): [] for i in range(n) for e in (0, 1)}
    for members in at_point.values():
        for (s, es) in members:
            arrive = ends[s][es]  # direction of travel when leaving s through end es
            for (t, et) in members:
                if t == s:
                    continue
                depart = -ends[t][et]  # entering t through et, heading into t
                conns[(s, es)].append((t, et, turn_cost(arrive, depart)))
    mids = np.array([ln.interpolate(0.5, normalized=True).coords[0] for ln in lines])
    return SegmentMap(n=n, lengths=lengths, conns=conns, midpoints=mids)


def segment_map_from_depthmapx(map_csv: str, conn_csv: str) -> SegmentMap:
    """Rebuild depthmapX's own segment graph from its CSV exports.

    `shapegraph-connections-csv` for a segment map gives rows (refA, refB, ss_weight, for_back,
    dir): from refA, leaving by its forward end (for_back=0, the line's t_end) or its back end
    (for_back=1, t_start), you enter refB in direction `dir` at angular cost `ss_weight`
    (90 deg = 1). dir=+1 means you travel towards refB's forward end, i.e. you came in through
    its back end. (salalib/axialmap.cpp, writeSegmentConnectionsAsPairsCSV.)
    End ids here: 1 = forward / t_end, 0 = back / t_start.
    """
    m = pd.read_csv(map_csv)
    c = pd.read_csv(conn_csv)
    n = len(m)
    ref_to_i = {r: i for i, r in enumerate(m["Ref"].to_numpy())}
    lengths = m["Segment Length"].to_numpy(float)
    conns: dict = {(i, e): [] for i in range(n) for e in (0, 1)}
    for a, b, w, fb, d in c[["refA", "refB", "ss_weight", "for_back", "dir"]].itertuples(index=False):
        s, t = ref_to_i[a], ref_to_i[b]
        es = 1 if fb == 0 else 0
        et = 0 if d == 1 else 1  # enter towards forward end => came in through end 0
        conns[(s, es)].append((t, et, float(w)))
    mids = np.c_[(m.x1 + m.x2) / 2, (m.y1 + m.y2) / 2]
    return SegmentMap(n=n, lengths=lengths, conns=conns, midpoints=mids)


def _tulip(w: float, bins: int | None) -> float:
    if bins is None:
        return w
    tb = bins // 2 + 1
    return float(math.floor(w * tb * 0.5))


def _tulip_scale(bins: int | None) -> float:
    if bins is None:
        return 1.0
    tb = bins // 2 + 1
    return (tb - 1) * 0.5


def angular_from_root(sm: SegmentMap, root: int, radius: float | None = None,
                      bins: int | None = None, return_best: bool = False):
    """Least-angle search from `root`.

    Returns (depth, pred_state, min_state):
      depth[i]      angular depth of segment i (inf if not reached), in 90-deg units
      pred_state    dict state -> predecessor state on the least-angle tree
      min_state[i]  the directed state giving segment i its depth
    With return_best=True a 4th value is returned: raw (unscaled) depth per directed state.
    """
    R = math.inf if radius is None else radius
    L = sm.lengths
    best: dict = {}
    pred: dict = {}
    metric_at: dict = {}
    heap: list = []
    cnt = 0
    for e in (0, 1):
        st = (root, e)
        heapq.heappush(heap, (0.0, 0.5 * L[root], -cnt, st, None))
        cnt += 1
    while heap:
        d, met, _, st, p = heapq.heappop(heap)
        if st in best:
            continue
        best[st] = d
        pred[st] = p
        metric_at[st] = met
        s, e = st
        for t, et, w in sm.conns[st]:
            nst = (t, 1 - et)  # entered through et, now heading to the other end
            if nst in best:
                continue
            if met + 0.5 * L[t] > R:
                continue
            heapq.heappush(heap, (d + _tulip(w, bins), met + L[t], -cnt, nst, st))
            cnt += 1
    depth = np.full(sm.n, np.inf)
    min_state: dict = {}
    for (s, e), d in best.items():
        if d < depth[s]:
            depth[s] = d
            min_state[s] = (s, e)
    depth = depth / _tulip_scale(bins)
    depth[root] = 0.0
    min_state[root] = (root, 0)
    pred[(root, 0)] = None
    pred[(root, 1)] = None
    if return_best:
        return depth, pred, min_state, best
    return depth, pred, min_state


def _accumulate_choice(ch: np.ndarray, root: int, pred: dict, min_state: dict) -> None:
    """Add this root's contribution to choice.

    Each reached segment is one destination, counted at its least-depth state. A segment gets
    +1 for every destination whose route passes through it, i.e. the number of destinations
    strictly below its state(s) in the least-angle tree. One reverse pass in settle order
    (dict order of `pred`) gives those subtree counts, so the cost is linear in the tree size
    rather than (destinations x route length).
    """
    sub = dict.fromkeys(pred, 0.0)
    for st in reversed(list(pred)):
        seg = st[0]
        own = 1.0 if (seg != root and min_state.get(seg) == st) else 0.0
        p = pred[st]
        if p is not None:
            sub[p] += sub[st] + own
        if seg != root:
            ch[seg] += sub[st]


def _accumulate_choice_depthmapx(ch: np.ndarray, root: int, pred: dict, best: dict) -> None:
    """depthmapX's exact choice rule (segmtulip.cpp), kept to explain its totals.

    Differences from the clean rule:
      * a destination is credited per DIRECTED state, so a segment whose two directed states
        both sit on routes is counted as a destination twice (once per approach);
      * walks start only from states that are leaves of the tree AND the lower-depth state of
        their segment (ties -> the 'back' state); subtrees that end only in non-minimal states
        are never walked.
    """
    children = {p for p in pred.values() if p is not None}
    covered: set = set()
    segs = sorted({s for s, _ in best})
    for j in segs:
        if j == root:
            continue
        a, b = (j, 1), (j, 0)  # depthmapX dir index 0 = heading forward = our end 1
        if a in best and b in best:
            st = a if best[a] < best[b] else b
        else:
            st = a if a in best else b
        if st in children:
            continue
        count = 0
        here = st
        while here is not None and here[0] != root:
            ch[here[0]] += count
            if here not in covered:
                count += 1
                covered.add(here)
            here = pred[here]


def angular_analysis(sm: SegmentMap, radii=(None,), bins: int | None = None,
                     choice: bool = True, choice_rule: str = "clean") -> pd.DataFrame:
    """NC, TD, integration, NAIN, (choice, NACH) per segment for each metric radius.

    radii: iterable of metres, None meaning radius n. Column suffix 'Rn' or 'R{int}'.
    choice_rule: "clean" counts each (origin, destination segment) once;
                 "depthmapx" reproduces depthmapX's per-direction counting.
    """
    cols: dict = {}
    for R in radii:
        lab = "Rn" if R is None else f"R{int(R)}"
        nc = np.zeros(sm.n)
        td = np.zeros(sm.n)
        ch = np.zeros(sm.n)
        for root in range(sm.n):
            depth, pred, min_state, best = angular_from_root(sm, root, R, bins, return_best=True)
            reached = np.isfinite(depth)
            nc[root] = reached.sum()
            td[root] = depth[reached].sum()
            if choice and choice_rule == "depthmapx":
                _accumulate_choice_depthmapx(ch, root, pred, best)
            elif choice:
                _accumulate_choice(ch, root, pred, min_state)
        with np.errstate(divide="ignore", invalid="ignore"):
            integ = np.where(td > 1e-9, nc ** 2 / td, np.nan)
            nain = nc ** 1.2 / (td + 2.0)
        cols[f"node_count_{lab}"] = nc
        cols[f"total_depth_{lab}"] = td
        cols[f"integration_{lab}"] = integ
        cols[f"nain_{lab}"] = nain
        if choice:
            cols[f"choice_{lab}"] = ch
            cols[f"nach_{lab}"] = np.log(ch + 1.0) / np.log(td + 3.0)
    return pd.DataFrame(cols)

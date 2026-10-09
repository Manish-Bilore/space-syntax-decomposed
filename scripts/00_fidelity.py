"""A1 fidelity check: our reimplementation vs depthmapX vs cityseer, on one map.

    export DEPTHMAPX=/path/to/depthmapXcli
    python scripts/00_fidelity.py --lines path/to/barnsbury_extended1_axial.csv --name barnsbury

`--lines` is a Ref,x1,y1,x2,y2 CSV (depthmapX's own test data ships Barnsbury, London).
The lines are run as an axial map and as a segment map (axial -> segment, depthmapX default).
Our code is fed depthmapX's exported connection lists, so any remaining difference is in the
measure definitions, not in graph construction. Writes reports/fidelity_<name>.md and CSVs.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssx.syntax.reference import depthmapx as dmx  # noqa: E402
from ssx.syntax.reimpl import topological as T  # noqa: E402
from ssx.syntax.reimpl.angular import angular_analysis, segment_map_from_depthmapx  # noqa: E402
from ssx.syntax.reimpl.derived import intelligibility, synergy  # noqa: E402


def _cmp(ours: np.ndarray, ref: np.ndarray, tol: float = 1e-5) -> dict:
    ref = np.where(ref == -1, np.nan, ref)
    ok = np.isfinite(ours) & np.isfinite(ref)
    rel = np.abs(ours[ok] - ref[ok]) / np.maximum(np.abs(ref[ok]), 1e-12)
    return {"n": int(ok.sum()), "share_within_tol": float(np.mean(rel <= tol)),
            "max_rel_err": float(rel.max()) if ok.any() else np.nan,
            "spearman": float(spearmanr(ours[ok], ref[ok])[0]) if ok.sum() > 2 else np.nan}


def axial_block(res: dmx.DmxResult) -> tuple[pd.DataFrame, dict]:
    m = res.map.set_index("Ref")
    G = nx.Graph()
    G.add_nodes_from(m.index)
    G.add_edges_from(zip(res.connections.refA, res.connections.refB))
    df = T.axial_analysis(G, radii=("n", 3), choice="split")
    V = list(df.index)
    pairs = [("connectivity", "Connectivity"), ("control", "Control"),
             ("controllability", "Controllability"), ("node_count_Rn", "Node Count"),
             ("total_depth_Rn", "Total Depth"), ("mean_depth_Rn", "Mean Depth"),
             ("ra_Rn", "RA"), ("rra_Rn", "RRA"), ("integration_hh_Rn", "Integration [HH]"),
             ("integration_pv_Rn", "Integration [P-value]"),
             ("integration_tekl_Rn", "Integration [Tekl]"),
             ("integration_hh_R3", "Integration [HH] R3"),
             ("choice_Rn", "Choice"), ("choice_R3", "Choice R3")]
    rows = []
    for a, b in pairs:
        r = _cmp(df[a].to_numpy(float), m[b].reindex(V).to_numpy(float))
        rows.append({"measure": b, **r})
    # depthmapX's own run-to-run variability in choice (random tie-breaking)
    r0 = T.choice_random(G, "n", seed=0)
    r1 = T.choice_random(G, "n", seed=1)
    extra = {
        "lines": len(V),
        "components": nx.number_connected_components(G),
        "choice_total_ours": float(df["choice_Rn"].sum()),
        "choice_total_dmx": float(m["Choice"].clip(lower=0).sum()),
        "choice_seed_to_seed_spearman": float(spearmanr([r0[v] for v in V], [r1[v] for v in V])[0]),
        "intelligibility": intelligibility(df), "synergy": synergy(df),
    }
    return pd.DataFrame(rows), extra


def segment_block(res: dmx.DmxResult, radii: list) -> tuple[pd.DataFrame, dict]:
    sm = segment_map_from_depthmapx(res.map_csv, res.conn_csv)
    m = res.map
    out = []
    timing = {}
    for R in radii:
        lab = "Rn" if R is None else f"R{R}"
        sfx = "" if R is None else f" R{R} metric"
        t = time.time()
        clean = angular_analysis(sm, radii=(R,), bins=1024, choice=True, choice_rule="clean")
        exact = angular_analysis(sm, radii=(R,), bins=1024, choice=True, choice_rule="depthmapx")
        timing[lab] = round(time.time() - t, 1)
        for ours, ref, name, src in [
            (clean[f"node_count_{lab}"], f"T1024 Node Count{sfx}", "Node Count", clean),
            (clean[f"total_depth_{lab}"], f"T1024 Total Depth{sfx}", "Total Depth", clean),
            (clean[f"integration_{lab}"], f"T1024 Integration{sfx}", "Integration", clean),
            (exact[f"choice_{lab}"], f"T1024 Choice{sfx}", "Choice (depthmapX rule)", exact),
            (clean[f"choice_{lab}"], f"T1024 Choice{sfx}", "Choice (clean rule)", clean),
        ]:
            r = _cmp(ours.to_numpy(float), m[ref].to_numpy(float))
            out.append({"radius": lab, "measure": name, **r})
        out.append({"radius": lab, "measure": "Choice total: clean / depthmapX",
                    "n": sm.n, "share_within_tol": np.nan, "max_rel_err": np.nan,
                    "spearman": float(clean[f"choice_{lab}"].sum() / m[f"T1024 Choice{sfx}"].sum())})
    return pd.DataFrame(out), {"segments": sm.n, "directed_connections": sm.n_connections,
                               "seconds_per_radius": timing}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", required=True)
    ap.add_argument("--name", default="map")
    ap.add_argument("--radii", nargs="+", default=["400", "800", "1200", "n"])
    args = ap.parse_args()
    radii = [None if r == "n" else int(r) for r in args.radii]

    work = ROOT / "reports" / f"work_{args.name}"
    rep = ROOT / "reports"
    rep.mkdir(exist_ok=True)
    print("depthmapX axial ...", flush=True)
    ax = dmx.run_axial(args.lines, work / "axial", radii="n,3")
    print("depthmapX segment ...", flush=True)
    sg = dmx.run_segment(args.lines, work / "segment",
                         radii=",".join("n" if r is None else str(r) for r in radii))
    print("reimplementation: axial ...", flush=True)
    ax_tab, ax_x = axial_block(ax)
    print("reimplementation: segment (this is the slow part) ...", flush=True)
    sg_tab, sg_x = segment_block(sg, radii)
    ax_tab.to_csv(rep / f"fidelity_{args.name}_axial.csv", index=False)
    sg_tab.to_csv(rep / f"fidelity_{args.name}_segment.csv", index=False)

    f = lambda v: f"{v:.6g}" if isinstance(v, float) else str(v)  # noqa: E731
    md = [f"# Fidelity report: {args.name}", "",
          "Our reimplementation vs depthmapX (reference). Our code is fed depthmapX's exported",
          "connection lists, so differences are in measure definitions, not graph construction.",
          "`share_within_tol` = share of features with relative error <= 1e-5.", "",
          f"## Axial map ({ax_x['lines']} lines, {ax_x['components']} components)", "",
          ax_tab.to_markdown(index=False, floatfmt=".6g"), "",
          f"- Choice total (sum over all lines): ours {f(ax_x['choice_total_ours'])}, "
          f"depthmapX {f(ax_x['choice_total_dmx'])}.",
          "- depthmapX breaks ties between equal-length routes at random, so its axial choice "
          f"varies between runs: two random-tie runs correlate at Spearman "
          f"{ax_x['choice_seed_to_seed_spearman']:.4f}. Ours splits ties equally (deterministic).",
          f"- Intelligibility r = {ax_x['intelligibility']['r']:.3f} "
          f"(r^2 = {ax_x['intelligibility']['r2']:.3f}); synergy r = {ax_x['synergy']['r']:.3f}.", "",
          f"## Segment map, angular tulip-1024 ({sg_x['segments']} segments)", "",
          sg_tab.to_markdown(index=False, floatfmt=".6g"), "",
          "- 'Choice (depthmapX rule)' reproduces depthmapX's per-direction counting; "
          "'clean rule' counts each origin-destination segment pair once. The total ratio row "
          "shows how much depthmapX's convention inflates choice.",
          f"- Reimplementation time per radius (s, both rules): {sg_x['seconds_per_radius']}", ""]
    (rep / f"fidelity_{args.name}.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()

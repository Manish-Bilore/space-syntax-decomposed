"""Parity with depthmapX on a small generated map. Skipped unless $DEPTHMAPX is set."""
import os

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from ssx.syntax.reimpl import topological as T
from ssx.syntax.reimpl.angular import angular_analysis, segment_map_from_depthmapx

pytestmark = pytest.mark.skipif(not os.environ.get("DEPTHMAPX"), reason="DEPTHMAPX not set")


@pytest.fixture(scope="module")
def jittered_grid(tmp_path_factory):
    """Axial-style lines: a 6x6 jittered grid of long lines plus two diagonals."""
    rng = np.random.default_rng(3)
    rows = []
    for i in range(6):
        y = i * 100 + rng.uniform(-8, 8)
        rows.append((-20, y, 520 + rng.uniform(-5, 5), y + rng.uniform(-10, 10)))
        x = i * 100 + rng.uniform(-8, 8)
        rows.append((x, -20, x + rng.uniform(-10, 10), 520 + rng.uniform(-5, 5)))
    rows += [(-10, -10, 510, 510), (-10, 510, 300, 200)]
    p = tmp_path_factory.mktemp("grid") / "lines.csv"
    df = pd.DataFrame(rows, columns=["x1", "y1", "x2", "y2"])
    df.insert(0, "Ref", range(len(df)))
    df.to_csv(p, index=False)
    return p


def test_axial_parity(jittered_grid, tmp_path):
    from ssx.syntax.reference import depthmapx as dmx

    res = dmx.run_axial(jittered_grid, tmp_path, radii="n,3")
    m = res.map.set_index("Ref")
    G = nx.Graph()
    G.add_nodes_from(m.index)
    G.add_edges_from(zip(res.connections.refA, res.connections.refB))
    df = T.axial_analysis(G, radii=("n", 3), choice="split")
    for ours, ref in [("integration_hh_Rn", "Integration [HH]"),
                      ("integration_hh_R3", "Integration [HH] R3"),
                      ("total_depth_Rn", "Total Depth"), ("control", "Control")]:
        r = m[ref].reindex(df.index).replace(-1, np.nan)
        ok = r.notna() & df[ours].notna()
        assert np.allclose(df.loc[ok, ours], r[ok], rtol=1e-5)
    assert df["choice_Rn"].sum() == pytest.approx(m["Choice"].clip(lower=0).sum())


def test_segment_parity(jittered_grid, tmp_path):
    from ssx.syntax.reference import depthmapx as dmx

    res = dmx.run_segment(jittered_grid, tmp_path, radii="n,150,300")
    sm = segment_map_from_depthmapx(res.map_csv, res.conn_csv)
    ours = angular_analysis(sm, radii=(None, 150, 300), bins=1024, choice=True,
                            choice_rule="depthmapx")
    m = res.map
    for R, sfx in [("Rn", ""), ("R150", " R150 metric"), ("R300", " R300 metric")]:
        assert (ours[f"node_count_{R}"].to_numpy() == m[f"T1024 Node Count{sfx}"].to_numpy()).all()
        assert np.allclose(ours[f"total_depth_{R}"], m[f"T1024 Total Depth{sfx}"], rtol=1e-5)
        assert np.allclose(ours[f"choice_{R}"], m[f"T1024 Choice{sfx}"], atol=0.5)

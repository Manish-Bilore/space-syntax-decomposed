import math

import networkx as nx
import pytest
from shapely.geometry import LineString

from fixtures import (CHAIN, CHAIN_EXPECTED, D, RING, RING_EXPECTED, STAR, STAR_EXPECTED)
from ssx.syntax.reimpl import topological as T
from ssx.syntax.reimpl.derived import intelligibility, synergy


def test_dvalue_formula():
    # D_k at k = 5 written out: 2(5(log2(7/3) - 1) + 1) / (4 * 3)
    assert T.dvalue(5) == pytest.approx(2 * (5 * (math.log2(7 / 3) - 1) + 1) / 12)
    assert T.dvalue(5) == pytest.approx(D(5))


@pytest.mark.parametrize("node", [0, 1, 2])
def test_chain_by_hand(node):
    df = T.axial_analysis(CHAIN, radii=("n",), choice="split")
    exp = CHAIN_EXPECTED[node]
    row = df.loc[node]
    assert row.total_depth_Rn == exp["total_depth"]
    assert row.mean_depth_Rn == pytest.approx(exp["mean_depth"])
    assert row.ra_Rn == pytest.approx(exp["ra"])
    assert row.integration_hh_Rn == pytest.approx(exp["integration_hh"])
    assert row.choice_Rn == pytest.approx(exp["choice"])
    assert row.control == pytest.approx(exp["control"])
    assert row.connectivity == exp["connectivity"]


def test_chain_symmetry():
    df = T.axial_analysis(CHAIN, radii=("n",), choice="split")
    assert df.loc[0].integration_hh_Rn == pytest.approx(df.loc[4].integration_hh_Rn)
    assert df.loc[1].choice_Rn == pytest.approx(df.loc[3].choice_Rn)


def test_star_hub_is_undefined_not_infinite():
    df = T.axial_analysis(STAR, radii=("n",), choice="split")
    assert df.loc[0].total_depth_Rn == STAR_EXPECTED[0]["total_depth"]
    assert math.isnan(df.loc[0].integration_hh_Rn)
    assert df.loc[1].ra_Rn == pytest.approx(STAR_EXPECTED[1]["ra"])
    assert df.loc[0].choice_Rn == pytest.approx(STAR_EXPECTED[0]["choice"])
    assert df.loc[1].choice_Rn == 0


def test_ring_ties_split():
    df = T.axial_analysis(RING, radii=("n",), choice="split")
    assert (df.total_depth_Rn == RING_EXPECTED["total_depth"]).all()
    assert df.choice_Rn.to_numpy() == pytest.approx([RING_EXPECTED["choice_split"]] * 6)


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_ring_ties_random_conserves_total(seed):
    ch = T.choice_random(RING, "n", seed=seed)
    assert sum(ch.values()) == RING_EXPECTED["choice_total"]


def test_choice_total_equals_sum_of_intermediate_steps():
    # Every ordered pair at depth d contributes d - 1 to the total, whatever the tie rule.
    G = nx.random_geometric_graph(60, 0.25, seed=4)
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    expected = sum(d - 1 for s, dd in nx.all_pairs_shortest_path_length(G)
                   for t, d in dd.items() if d >= 2)
    assert sum(T.choice_split(G).values()) == pytest.approx(expected)
    assert sum(T.choice_random(G, seed=9).values()) == pytest.approx(expected)


def test_split_choice_matches_networkx_betweenness():
    G = nx.random_geometric_graph(50, 0.3, seed=1)
    ours = T.choice_split(G)
    ref = nx.betweenness_centrality(G, normalized=False)  # unordered pairs
    for v in G:
        assert ours[v] == pytest.approx(2 * ref[v])


def test_local_radius_restricts_system():
    df = T.axial_analysis(CHAIN, radii=(1,), choice="split")
    # radius 1 from the centre line sees itself + 2 neighbours
    assert df.loc[2].node_count_R1 == 3
    assert df.loc[2].total_depth_R1 == 2
    # no line can lie between two others within radius 1
    assert (df.choice_R1 == 0).all()


def test_intelligibility_and_synergy_run():
    G = nx.random_geometric_graph(80, 0.2, seed=2)
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    df = T.axial_analysis(G, radii=("n", 3), choice=None)
    i = intelligibility(df)
    s = synergy(df)
    assert -1 <= i["r"] <= 1 and 0 <= s["r2"] <= 1


def test_axial_graph_from_lines_touching_and_crossing():
    lines = [LineString([(0, 0), (10, 0)]),     # 0
             LineString([(5, -5), (5, 5)]),      # 1 crosses 0
             LineString([(10, 0), (10, 10)]),    # 2 touches 0 at its end
             LineString([(20, 20), (30, 20)])]   # 3 isolated
    G = T.axial_graph_from_lines(lines)
    assert set(G.edges()) == {(0, 1), (0, 2)}
    assert G.degree(3) == 0

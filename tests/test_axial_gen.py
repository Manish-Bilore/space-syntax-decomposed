import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString

from ssx.syntax.axial_gen import axial_lines, strokes, transfer_to_streets
from ssx.syntax.reimpl.topological import axial_graph_from_lines


def gdf(lines):
    return gpd.GeoDataFrame({"seg_id": range(len(lines))}, geometry=lines, crs=32643)


def test_straight_street_split_at_junctions_is_one_line():
    # a straight E-W street cut into 3 pieces by two cross streets
    lines = [LineString([(0, 0), (100, 0)]), LineString([(100, 0), (200, 0)]),
             LineString([(200, 0), (300, 0)]),
             LineString([(100, -50), (100, 0)]), LineString([(100, 0), (100, 50)]),
             LineString([(200, -50), (200, 0)]), LineString([(200, 0), (200, 50)])]
    st = strokes(gdf(lines))
    assert sorted(len(s) for s in st) == [2, 2, 3]       # E-W stroke + two N-S strokes
    ax, lin = axial_lines(gdf(lines), tol=5)
    assert len(ax) == 3                                  # one straight line per stroke
    G = axial_graph_from_lines(ax.geometry)
    assert G.number_of_edges() == 2                      # E-W crosses both N-S lines


def test_gentle_kinks_are_absorbed_sharp_turn_is_not():
    # street with 2 m wobbles (absorbed at tol 5) and a 90 degree turn at the end
    lines = [LineString([(0, 0), (50, 2), (100, 0)]), LineString([(100, 0), (150, -2), (200, 0)]),
             LineString([(200, 0), (200, 100)])]
    ax, _ = axial_lines(gdf(lines), tol=5)
    assert len(ax) == 2
    G = axial_graph_from_lines(ax.geometry)
    assert nx.is_connected(G)


def test_curve_becomes_several_lines():
    t = np.linspace(0, np.pi / 2, 30)
    arc = LineString(np.c_[200 * np.cos(t), 200 * np.sin(t)])
    ax, _ = axial_lines(gdf([arc]), tol=5)
    assert len(ax) >= 4
    assert nx.is_connected(axial_graph_from_lines(ax.geometry))   # consecutive pieces connect


def test_t_junction_connects_after_extension():
    # side street ends 0.5 m short of the main street's simplified line
    lines = [LineString([(0, 0), (100, 3), (200, 0)]), LineString([(100, 3), (100, 80)])]
    ax, _ = axial_lines(gdf(lines), tol=5)
    assert nx.is_connected(axial_graph_from_lines(ax.geometry))


def test_lineage_and_transfer_weights():
    lines = [LineString([(0, 0), (100, 0)]), LineString([(100, 0), (300, 0)])]
    ax, lin = axial_lines(gdf(lines), tol=5)
    assert len(ax) == 1
    assert lin.groupby("street_index").overlap_m.sum().to_numpy() == pytest.approx([100, 200])
    vals = pd.DataFrame({"v": [7.0]}, index=ax.axial_id)
    out = transfer_to_streets(vals, lin, 2)
    assert out.v.tolist() == [7.0, 7.0]


def test_every_best_fit_prefers_straightest_continuation():
    # at the junction, A continues best into C (5 deg) not B (25 deg)
    a = LineString([(-100, 0), (0, 0)])
    b = LineString([(0, 0), (100 * np.cos(np.radians(25)), 100 * np.sin(np.radians(25)))])
    c = LineString([(0, 0), (100 * np.cos(np.radians(-5)), 100 * np.sin(np.radians(-5)))])
    st = strokes(gdf([a, b, c]), angle_max=30)
    paired = [s for s in st if len(s) == 2][0]
    assert {i for i, _ in paired} == {0, 2}


def test_large_coordinates_and_short_streets_keep_lineage():
    # UTM-sized coordinates: vertices 2 m apart must not be confused (np.allclose rtol pitfall),
    # and a 2 m street between two long ones must still receive a value
    x0, y0 = 500000.0, 2100000.0
    lines = [LineString([(x0, y0), (x0 + 100, y0)]), LineString([(x0 + 100, y0), (x0 + 102, y0)]),
             LineString([(x0 + 102, y0), (x0 + 200, y0 + 1)]),
             LineString([(x0 + 102, y0), (x0 + 102, y0 + 80)])]
    ax, lin = axial_lines(gdf(lines), tol=5)
    assert set(lin.street_index) == {0, 1, 2, 3}
    cov = lin.groupby("street_index").overlap_m.sum()
    assert cov[1] == pytest.approx(2.0, abs=1e-6)


def test_coincident_duplicate_streets_give_one_line():
    # the same street twice (multi-edge after consolidation) plus a cross street
    lines = [LineString([(0, 0), (100, 0)]), LineString([(0, 0), (100, 0)]),
             LineString([(50, -50), (50, 50)])]
    ax, lin = axial_lines(gdf(lines), tol=5)
    assert len(ax) == 2
    assert ax.axial_id.tolist() == [0, 1]
    assert set(lin.street_index) == {0, 1, 2}
    assert lin.axial_id.max() == 1

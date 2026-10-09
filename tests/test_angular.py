import numpy as np
import pytest

from fixtures import L_BEND, STRAIGHT_BRANCH, T_JUNCTION
from ssx.syntax.reimpl.angular import (angular_analysis, angular_from_root,
                                        segment_map_from_lines, turn_cost)


def test_turn_cost_units():
    assert turn_cost((1, 0), (1, 0)) == pytest.approx(0.0)     # straight on
    assert turn_cost((1, 0), (0, 1)) == pytest.approx(1.0)     # 90 deg
    assert turn_cost((1, 0), (1, 1)) == pytest.approx(0.5)     # 45 deg
    assert turn_cost((1, 0), (-1, 0)) == pytest.approx(2.0)    # U-turn


def test_l_bend():
    sm = segment_map_from_lines(L_BEND)
    df = angular_analysis(sm, radii=(None,), choice=False)
    assert (df.node_count_Rn == 2).all()
    assert df.total_depth_Rn.to_numpy() == pytest.approx([1.0, 1.0])
    assert df.integration_Rn.to_numpy() == pytest.approx([4.0, 4.0])


def test_straight_street_with_branch():
    sm = segment_map_from_lines(STRAIGHT_BRANCH)
    depth, _, _ = angular_from_root(sm, 0)
    assert depth == pytest.approx([0.0, 0.0, 0.0, 0.5])


def test_metric_radius_is_midpoint_to_midpoint_along_route():
    sm = segment_map_from_lines(T_JUNCTION)
    d100, _, _ = angular_from_root(sm, 0, radius=100)
    d300, _, _ = angular_from_root(sm, 0, radius=300)
    assert np.isfinite(d100).sum() == 2 and np.isfinite(d100[2])   # only the short turn
    assert np.isfinite(d300).sum() == 3


def test_tulip_binning_matches_continuous_on_right_angles():
    sm = segment_map_from_lines(L_BEND)
    a = angular_analysis(sm, radii=(None,), bins=1024, choice=False)
    b = angular_analysis(sm, radii=(None,), bins=None, choice=False)
    assert a.total_depth_Rn.to_numpy() == pytest.approx(b.total_depth_Rn.to_numpy())


def test_choice_on_straight_street():
    # A-B-C straight, D branching: B lies between A and {C, D}, and between C/D and A.
    sm = segment_map_from_lines(STRAIGHT_BRANCH)
    df = angular_analysis(sm, radii=(None,), choice=True)
    ch = df.choice_Rn.to_numpy()
    assert ch[1] == pytest.approx(4.0)   # A->C, A->D, C->A, D->A
    assert ch[0] == 0 and ch[2] == 0 and ch[3] == 0


def test_nain_nach_definitions():
    sm = segment_map_from_lines(STRAIGHT_BRANCH)
    df = angular_analysis(sm, radii=(None,), choice=True)
    nc, td, ch = df.node_count_Rn, df.total_depth_Rn, df.choice_Rn
    assert df.nain_Rn.to_numpy() == pytest.approx((nc ** 1.2 / (td + 2)).to_numpy())
    assert df.nach_Rn.to_numpy() == pytest.approx((np.log(ch + 1) / np.log(td + 3)).to_numpy())

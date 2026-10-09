"""Toy layouts with values worked out by hand.

Each fixture is small enough to verify on paper. The derivations are written out so the
fixtures double as learning material (see docs/learning/01_axial_by_hand.md).
"""
from __future__ import annotations

import math

import networkx as nx
from shapely.geometry import LineString


def D(k: float) -> float:
    return 2.0 * (k * (math.log2((k + 2.0) / 3.0) - 1.0) + 1.0) / ((k - 1.0) * (k - 2.0))


# --------------------------------------------------------------------------------------------
# CHAIN of 5 axial lines: 0 - 1 - 2 - 3 - 4   (k = 5)
#
#   line 0: depths to 1,2,3,4 = 1,2,3,4      TD = 10   MD = 10/4 = 2.5   RA = 2(1.5)/3 = 1.0
#   line 1: depths 1,1,2,3                   TD = 7    MD = 1.75         RA = 2(0.75)/3 = 0.5
#   line 2: depths 1,1,2,2                   TD = 6    MD = 1.5          RA = 2(0.5)/3  = 1/3
#
#   Integration[HH] = D_5 / RA.
#   Choice (ordered pairs, both directions):
#     line 1 is between 0 and {2,3,4}: 3 pairs x 2 directions = 6
#     line 2 is between {0,1} and {3,4}: 4 pairs x 2 = 8
#   Control: line 0 -> 1/deg(1) = 1/2;  line 1 -> 1/deg(0) + 1/deg(2) = 1 + 1/2 = 1.5;
#            line 2 -> 1/2 + 1/2 = 1.0
# --------------------------------------------------------------------------------------------
CHAIN = nx.path_graph(5)
CHAIN_EXPECTED = {
    0: dict(total_depth=10, mean_depth=2.5, ra=1.0, choice=0.0, control=0.5, connectivity=1),
    1: dict(total_depth=7, mean_depth=1.75, ra=0.5, choice=6.0, control=1.5, connectivity=2),
    2: dict(total_depth=6, mean_depth=1.5, ra=1 / 3, choice=8.0, control=1.0, connectivity=2),
}
for v in CHAIN_EXPECTED.values():
    v["integration_hh"] = D(5) / v["ra"]

# --------------------------------------------------------------------------------------------
# STAR: one long street (0) crossed by four short lanes (1..4)   (k = 5)
#
#   hub 0: every line at depth 1 -> TD = 4, MD = 1 -> RA = 0 -> 'infinitely integrated';
#          depthmapX writes -1, we write NaN.
#   spoke: hub at 1, three other spokes at 2 -> TD = 7, MD = 1.75, RA = 0.5
#   choice(hub) = C(4,2) pairs x 2 directions = 12;  spokes 0.
# --------------------------------------------------------------------------------------------
STAR = nx.star_graph(4)
STAR_EXPECTED = {
    0: dict(total_depth=4, mean_depth=1.0, ra=float("nan"), choice=12.0),
    1: dict(total_depth=7, mean_depth=1.75, ra=0.5, choice=0.0),
}

# --------------------------------------------------------------------------------------------
# RING of 6 lines: tests TIED shortest paths.
#   every line: depths 1,1,2,2,3 -> TD = 9, MD = 1.8
#   Choice, split ties (unordered, then x2):
#     pairs at distance 2 (6 of them) each pass through exactly one line -> +1 to that line
#     pairs at distance 3 (3 of them) have 2 routes of 2 intermediate lines each; each
#       intermediate line gets 1/2  -> 3 x 2 x 2 x 1/2 = 6 spread over 6 lines -> +1 each
#     unordered = 2 per line, ordered = 4 per line.
#   With depthmapX's random tie-breaking the per-line value varies but the total is 24.
# --------------------------------------------------------------------------------------------
RING = nx.cycle_graph(6)
RING_EXPECTED = dict(total_depth=9, mean_depth=1.8, choice_split=4.0, choice_total=24.0)


# --------------------------------------------------------------------------------------------
# SEGMENT fixtures (angular). Coordinates in metres.
#
# L-BEND: two 100 m segments meeting at a right angle.
#   from either: NC = 2, TD = 1 (one 90 deg turn) -> integration = NC^2/TD = 4
#
# STRAIGHT vs DOG-LEG: a 3-segment straight street A-B-C and a branch D leaving B's far end
# at 45 deg.
#   from A: B at 0 (straight), C at 0 (straight), D at 0.5 (45 deg)  -> TD = 0.5, NC = 4
# --------------------------------------------------------------------------------------------
L_BEND = [LineString([(0, 0), (100, 0)]), LineString([(100, 0), (100, 100)])]

STRAIGHT_BRANCH = [
    LineString([(0, 0), (100, 0)]),        # A
    LineString([(100, 0), (200, 0)]),      # B
    LineString([(200, 0), (300, 0)]),      # C
    LineString([(200, 0), (270.7106781, 70.7106781)]),  # D, 45 deg off B's far end
]

# T-JUNCTION used for metric-radius semantics: root R (100 m) ends at a junction; straight on
# is S (400 m), turning left is T (50 m).
#   midpoint(R) -> midpoint(S) along the route = 50 + 200 = 250 m
#   midpoint(R) -> midpoint(T)                 = 50 + 25  = 75 m
#   radius 100: only T is inside (plus R)  -> NC = 2
#   radius 300: both                         -> NC = 3
T_JUNCTION = [
    LineString([(0, 0), (100, 0)]),        # R
    LineString([(100, 0), (500, 0)]),      # S
    LineString([(100, 0), (100, 50)]),     # T
]

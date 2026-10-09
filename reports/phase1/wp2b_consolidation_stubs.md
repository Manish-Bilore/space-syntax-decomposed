# Phase 1, WP2b — why junction consolidation makes the engines disagree

WP2 found that cityseer and depthmapX agree at ρ 0.90–0.99 on raw OSM topology but only
0.5–0.9 after junction consolidation. This note identifies the mechanism on a synthetic
junction and sets up the test on real data.

## Mechanism (verified on a synthetic junction)

osmnx's `consolidate_intersections` merges nearby junction nodes into one point. It keeps each
street's original line and **appends a straight stub** from the street's old endpoint to the
merged point. Checked on a synthetic dual carriageway crossed by one street: every street
touching a merged junction gets a stub, and all geometries end exactly at the merged point.

The two engines read those stubs differently (origin: one arm of the dual carriageway):

| Network | cityseer: streets reached | cityseer: angular farness | depthmapX-style: pieces | depthmapX-style: total depth |
|---|---|---|---|---|
| Raw | 6 | 13.0 | 7 | 7.0 |
| Consolidated 10 m | 5 | 17.0 | 12 | 12.0 |
| Consolidated + stubs removed | 5 | 9.0 | 6 | 4.0 |

- **cityseer joins streets only at their end points.** After consolidation every route through
  the junction has to pass along the stubs, so its angular cost rises (mean cost per reached
  street +57% here) although the junction became simpler.
- **depthmapX joins pieces wherever end points coincide**, including the old shared vertex
  inside the stubs. Turn cost per piece is unchanged, but each stub counts as an extra piece:
  7 to 12. Node count, and so NC²/TD and NAIN, inflate around merged junctions.
- **With stubs removed**, both engines fall below the raw values, as they should when a dual
  carriageway is merged into one street.

So consolidation does not add one error; it perturbs the two engines in different directions,
which is what lowers their agreement.

This is one synthetic junction. It establishes the mechanism, not its size on real networks.

## Fix

`build.destub(seg, tol)` drops the old endpoint vertex wherever an end piece is ≤ the
consolidation tolerance, so the street runs straight from the merged point to its next
vertex. Connectivity is unchanged. Available as `01_fetch_network.py --destub`.

## Result on the real networks (8 Oct 2026)

![Consolidation sensitivity with the destubbed network](figures/fig6_consolidation_800.png)

### Stubs are common after consolidation

A stub end is a street end whose first piece is ≤ 10 m and turns ≥ 30° into the next piece.

| | Copenhagen 0 m | 10 m | 10 m destubbed | Mumbai 0 m | 10 m | 10 m destubbed |
|---|---|---|---|---|---|---|
| Stub ends (share of street ends) | 4.3% | 19.7% | 2.1% | 1.7% | 25.1% | 1.4% |
| Stub turning, degrees per km | 125 | 411 | 33 | 28 | 408 | 15 |
| Straight pieces | 204,494 | 165,123 | 128,922 | 49,504 | 45,678 | 35,765 |

At 10 m, one street end in four or five carries an artificial turn. Destubbing removes almost
all of them and 22% of the straight pieces in both cities. (The 20 m networks show fewer stubs
by this count, 8.5% and 16.3%, only because their stubs can be up to 20 m long and the count
stops at 10 m; rerun with `--max-len 20` for that row.)

### Destubbing recovers part of the engine agreement, not all

cityseer to depthmapX, ρ at 400 / 800 / 1200 / 2000 m:

| | 0 m | 10 m | 10 m destubbed | Gap recovered |
|---|---|---|---|---|
| Copenhagen, closeness | .92 .94 .96 .99 | .79 .84 .86 .90 | .83 .90 .93 .95 | 30 / 57 / 63 / 55% |
| Mumbai, closeness | .90 .93 .94 .95 | .67 .78 .82 .86 | .80 .89 .92 .95 | 56 / 73 / 87 / 97% |
| Copenhagen, betweenness | .90 .93 .94 .94 | .69 .73 .73 .73 | .73 .82 .83 .84 | 20 / 45 / 51 / 53% |
| Mumbai, betweenness | .85 .89 .92 .95 | .62 .67 .66 .67 | .69 .81 .85 .87 | 29 / 63 / 71 / 74% |

"Gap recovered" is the share of the difference between the 10 m and 0 m values that
destubbing closes.

- **The prediction was partly right.** Closeness agreement returns to 0.89–0.95 at 800 m and
  above, as predicted. At 400 m it reaches only 0.80–0.83, and betweenness stays at 0.69–0.87,
  short of the predicted 0.9.
- **Stubs are the largest single cause identified, about half the gap overall**: more in Mumbai
  than Copenhagen, and more at large radii than at 400 m.
- **cityseer's own angular values were contaminated.** Its metric to angular betweenness
  agreement rises from 0.70–0.81 to 0.81–0.90 in Mumbai and from 0.74–0.79 to 0.79–0.84 in
  Copenhagen once stubs are removed, as the synthetic test indicated.
- **The robust Phase 0 results are unchanged** on the destubbed network: NC²/TD to NAIN is 0.46
  and 0.49 at 400 m; end-to-end closeness at 400 m is −0.03 and 0.07.
- End-to-end betweenness recovers about a third (Copenhagen) to a half (Mumbai) of its gap.

### Duplicated carriageways are not the cause (tested, Mumbai)

After destubbing, cityseer discards 294 streets in Mumbai and 314 in Copenhagen during its own
cleaning: the two carriageways of divided roads become coincident lines. Hypothesis: depthmapX
keeps both and splits through-movement, which lowers betweenness agreement.

`--merge-parallel` keeps one street where several join the same two junctions within the
tolerance. In Mumbai it dropped 909 streets, and cityseer then discarded only 1. Engine
agreement did not move:

| Mumbai, cityseer to depthmapX | 10 m destubbed | + parallels merged |
|---|---|---|
| Closeness | .80 .89 .92 .95 | .79 .89 .92 .95 |
| Betweenness | .69 .81 .85 .87 | .68 .81 .85 .88 |

Copenhagen (8 Oct, 1,639 streets merged) gives the same answer: closeness .83 .90 .93 .95 to
.82 .90 .92 .95; betweenness .73 .82 .83 .84 to .73 .82 .84 .85.

**Hypothesis rejected.** Merging parallels is still worth keeping, because it makes both
engines analyse the same set of streets and improves the junction to segment rows (betweenness
.71 .69 .66 .62 to .77 .75 .73 .69). It does not explain the engine gap.

### What does explain the rest: segment length relative to the radius

![Engine agreement against segment length over radius](figures/fig7_engine_scale.png)

Pooling every stub-free network (0 m and destubbed 10 m in both cities, plus Mumbai with
parallels merged), cityseer to depthmapX agreement for closeness falls on one curve against
**median segment length ÷ radius**: rank correlation −0.96 over 20 points.

| Median segment ÷ radius | Closeness ρ (stub-free networks) |
|---|---|
| 0.01–0.04 | 0.94–0.99 |
| 0.05–0.11 | 0.89–0.93 |
| 0.15–0.18 | 0.80–0.83 |

- Consolidation lengthens segments (Mumbai median 43 to 71 m, Copenhagen 27 to 60 m). That alone
  moves each radius along the curve, so agreement at 400 m drops even with no artefact.
- This is the catchment-edge effect of nuance 9: the engines decide differently which segments
  fall inside a radius, and that matters more when each segment is a larger share of the radius.
  Phase 0 proposed it; WP2 wrongly demoted it; it is the second cause alongside stubs.
- Networks consolidated with stubs sit below the curve, by up to about 0.13.
- **Betweenness follows the same direction less tightly** (rank correlation −0.83). Copenhagen's
  destubbed network sits about 0.08 below its raw network at similar ratios. That part is still
  unexplained.

The 20 points come from five networks at four radii each, so they are not independent, and the
curve was found after looking at the data. A direct test: split long streets into short pieces
without changing geometry and check that agreement at 400 m rises.

## Baseline networks from here on

Two networks per city, and a finding is reported only if it holds on both:

| | Raw (0 m) | Cleaned (10 m, destubbed, parallels merged) |
|---|---|---|
| Copenhagen | 64,625 interior segments, median 27 m | 30,051, median 60 m |
| Mumbai island city | 16,987, median 43 m | 9,594, median 72 m |

Headline results on both baselines (ρ at 400 / 800 / 1200 / 2000 m):

| Step | Copenhagen raw | Copenhagen cleaned | Mumbai raw | Mumbai cleaned |
|---|---|---|---|---|
| NC²/TD to NAIN | .51 .60 .64 .71 | .49 .62 .68 .74 | .51 .66 .72 .79 | .43 .62 .72 .81 |
| Closeness end to end | −.04 −.02 .02 .17 | .07 .22 .31 .45 | .01 .16 .28 .35 | −.04 .23 .38 .53 |
| Betweenness end to end | .70 .76 .78 .79 | .60 .67 .69 .69 | .61 .69 .73 .77 | .44 .55 .61 .66 |
| Closeness metric to angular | .84 .77 .78 .84 | .80 .79 .82 .85 | .89 .87 .88 .89 | .89 .90 .92 .94 |

- Holds on both: NAIN is the largest closeness step at 400 m; closeness end to end is near zero
  at 400 m; metric to angular reorders Mumbai less than Copenhagen.
- Depends on the network: how far betweenness diverges end to end, and how fast closeness
  agreement recovers with radius.

## Working rules

- Do not use the plain 10 m network again. The cleaned network is 10 m consolidation with
  `--destub --merge-parallel`.
- Report findings only if they hold on both the raw (0 m) and the cleaned 10 m network.
- When comparing engines or radii, state the median segment length; agreement depends on
  segment length relative to the radius.
- Engine agreement below about 0.9 at a radius under ten segment lengths is expected and is not
  evidence of an error.

## Reproduce

```bash
python scripts/06_stub_diag.py
python scripts/01_fetch_network.py --site mumbai_island --consolidate 10 --destub --name mumbai_island_c10d
python scripts/02_ladder.py --site mumbai_island_c10d --radii 400 800 1200 2000
python scripts/01_fetch_network.py --site copenhagen --consolidate 10 --destub --name copenhagen_c10d
python scripts/02_ladder.py --site copenhagen_c10d --radii 400 800 1200 2000
python scripts/01_fetch_network.py --site mumbai_island --consolidate 10 --destub --merge-parallel --name mumbai_island_c10dp
python scripts/02_ladder.py --site mumbai_island_c10dp --radii 400 800 1200 2000
python scripts/05_sensitivity.py --levels 0 10 10d 10dp 20
python scripts/07_engine_scale.py
```

# Nuance catalogue

Findings from reimplementing Space Syntax measures and checking them against depthmapX
(source: `salalib/axialmodules/axialintegration.cpp`, `salalib/segmmodules/segmtulip.cpp`,
`salalib/connector.h`, `genlib/pafmath.h`) and against cityseer. Each entry says what the
convention is, where it is in the code, and why it matters for comparison.

Numbers marked *Barnsbury* come from `reports/fidelity_barnsbury.md` (depthmapX test data,
London: 1,100 axial lines, 5,459 segments).

## Axial (topological) analysis

1. **Node count includes the root.** `k` in MD, RA and the D-value is the number of lines
   *including* the line itself. RA = 2(MD − 1)/(k − 2). Getting this off by one shifts every
   integration value. *Barnsbury: all depth/integration columns match to ~1e-7.*
2. **Undefined rather than infinite.** If a line reaches everything in one step (MD = 1), RA = 0 and
   integration is undefined; depthmapX writes −1. Treat as missing, never as a large value.
3. **Local radius means depth ≤ r**, and the D-value uses the node count *within* the radius.
   R3 integration is therefore a different normalisation per line rather than a scaled-down Rn.
4. **Axial choice depends on a random seed.** depthmapX picks one shortest path per pair by
   expanding the BFS frontier in random order. Total choice is fixed (each ordered pair at depth
   d contributes d − 1), but its allocation across tied routes is not.
   *Barnsbury: two random-tie runs agree at Spearman ≈ 0.99; our split-tie version agrees with
   depthmapX at 0.996 and has identical total choice.*
5. **Choice counts both directions.** Values are ordered-pair counts (2× undirected
   betweenness). 'Choice [Norm]' divides by (k − 1)(k − 2)/2, mixing conventions.

## Angular segment analysis

6. **Directed search.** Leaving a segment costs a different turn depending on the end you leave
   by, so the search runs over (segment, direction) states. A segment's depth is the lower of its
   two directed depths.
7. **Tulip binning quantises angle.** `-stb 1024` rounds each turn down to 1/256 of 90°.
   *Barnsbury: radius-n total depth matches depthmapX exactly with binning, and differs by
   ~0.1% with continuous angles.*
8. **Ties are broken by metric distance.** Within one angular-depth bin, the metrically shorter
   route is expanded first (`connector.h`: bins sorted by `metricdepth`). This decides which of
   several equal-angle routes is "the" route. Without it, radius-limited node counts matched
   93–99%; with it, 100%.
9. **Metric radius is measured along the least-angle route**, midpoint to midpoint
   (root half-length + intermediate lengths + half of the target). A street 300 m away by the
   shortest walk can fall outside an 800 m angular catchment if the least-angle route to it is
   longer. Angular "R800" is not the same catchment as metric "800 m".
10. **Angular precision changes catchments.** Because of (8) and (9), switching from tulip-1024
    to continuous angles changes which segments fall inside a metric radius. *Barnsbury, 300
    sampled roots: node count changed for 20% of roots at R400, 47% at R800 and 53% at R1200
    (median total-depth change ~0.2%, worst ~39%), while radius-n depth changed by ~0.1% and
    node count not at all.* Bin count is a methodological parameter to report.
11. **Integration = NC²/TD** (depthmapX ≥ 10). NAIN and NACH are *not* computed by depthmapX;
    they are post-hoc (Hillier, Yang & Turner 2012): NAIN = NC^1.2/(TD + 2),
    NACH = log(CH + 1)/log(TD + 3). Check these constants against the paper before citing.
12. **depthmapX counts angular choice per direction.** A destination is credited once per
    directed state on the tree, so a segment approached from both ends can count twice; and walks
    start only from leaf states that are the segment's lower-depth state, so some branches are
    never walked. The two effects pull in opposite directions.
    *Barnsbury: depthmapX's total choice relative to a one-count-per-destination rule is −6.6%
    at R400, −2.4% at R800, +0.2% at R1200 and +11.2% at radius n. Reproducing its rule gives
    exact agreement for 99.1–100% of segments at every radius (residual from 32-bit float metric
    depths).* Ranks are almost unaffected (ρ > 0.999), so this matters for absolute values and
    for NACH rather than for which streets come out on top.

## Graph construction (before any measure)

13. **Axial to segment conversion splits at crossings and removes stubs** (`-crsl`, % of line
    length). Barnsbury's 1,100 lines become 5,459 segments, many a few metres long. Segment
    counts, and anything averaged per segment, depend on this.
14. **cityseer cleans the graph** (merges near-parallel edges within 1 m, drops zero-length
    edges and short self-loops). *Barnsbury: 33–38 of 5,459 segments disappear.* Report the loss.
15. **Curves.** depthmapX segments are straight; a curved OSM way must be exploded into
    straight pieces, which adds small turns along the curve. cityseer keeps the curve and handles
    bends internally. Results then have to be aggregated back to streets (we use a
    length-weighted mean), which is itself a choice.

## Ladder (S0 to S3) on real networks

Full tables: `reports/results_phase0.md` (Copenhagen + Frederiksberg, Mumbai City District,
OSM walk networks, radii 400–2000 m).

16. **No single step explains the SS-vs-network gap.** Angular cost, engine conventions and
    SS normalisation each reorder streets by similar amounts. End to end, metric closeness and
    NAIN are near-unrelated at 400 m (ρ ≈ 0 in both cities). The Barnsbury test map, with its
    axial stubs, had suggested betweenness was robust; on OSM data it is not (ρ 0.39–0.65).
17. **Normalisation is the largest single step for closeness**; the closeness formula
    (harmonic vs NC²/TD) is the smallest (ρ ≈ 0.98). The exponent on NC sets how much network
    density is rewarded.
18. **Engine disagreement shrinks with radius**, and does not go away when curves are
    replaced by chords. It is mostly produced by junction consolidation (nuance 22); catchment
    conventions (nuance 9) are secondary.
19. **Curve explosion inflates NAIN/NACH**, because NC and TD count straight pieces. Chords
    raise their agreement by 0.04–0.11 while leaving raw measures almost unchanged.
20. **OSM under-maps Mumbai's lanes**: 14.5 km of walk network per km² vs Copenhagen's 23.0,
    despite far denser built fabric. All Mumbai results are the "without informal lanes" case (Project 2).
21. **cityseer results at one radius depend on the other radii requested.** Deterministic run
    to run, but Mumbai S2 at 800 m changes when 1200/2000 m are in the same call (betweenness
    metric to angular ρ 0.791 vs 0.753). Report the radius set with every cityseer result.
22. **Junction consolidation is a design choice as large as angular cost.** Going from 0 to
    20 m changes Copenhagen's segment count 4.2× and drops cityseer–depthmapX agreement from
    0.90–0.99 to 0.54–0.92. NAIN's reordering and the near-zero end-to-end closeness agreement
    at 400 m survive every setting. Details: `reports/phase1/wp2_cleaning_sensitivity.md`.
23. **Compare cities by network length per km² rather than segment counts.** The Copenhagen : Mumbai
    segment-density ratio runs 1.5–2.6× with consolidation; the length ratio stays 1.57–1.58×.
24. **Consolidation appends stubs, and the engines read them differently.** osmnx keeps each
    street's line and adds a straight stub to the merged junction point. cityseer joins streets
    only at end points, so routes pass along the stubs and angular cost inflates; depthmapX joins
    pieces at any shared end point, so cost is unchanged but each stub is an extra piece in NC.
    Verified on a synthetic junction (`reports/phase1/wp2b_consolidation_stubs.md`).
25. **Within a city, places differ more than the two cities do.** Per-tile agreement spreads
    0.24–0.68 (p10–p90) against 0.06–0.10 between city medians, and tile density explains
    little of it (`reports/phase1/wp1_tiles.md`).
26. **Removing consolidation stubs recovers about half of the lost engine agreement** on the
    real networks (more in Mumbai, more at large radii). One street end in four or five carries
    a stub at 10 m. Divided roads left as two coincident streets are the next suspect.
27. **Engine agreement depends on segment length relative to the radius.** On stub-free
    networks, cityseer to depthmapX closeness agreement follows one curve against median segment
    ÷ radius (rank correlation −0.96, 20 points, both cities): about 0.95 at a ratio of 0.03,
    0.90 at 0.08, 0.80 at 0.18. Merging duplicated carriageways does not change it.
28. **Global integration of a settlement depends on where it sits in the map, more than on map
    size.** Against Greater Mumbai, a surround centred on Dharavi reproduces its global NAIN ranking
    at ρ 0.96 (1 km) to 0.99 (4 km); the island city, 4× larger but with Dharavi near its edge, gets
    0.83. Clipped at the settlement boundary: 0.53. Radius-bounded measures are exact once the
    surround reaches the radius. (`reports/phase1/wp3_nested_extents.md`)

## Axial maps (S4)

29. **A generated axial map differs from a fewest-line map.** Lines are built from centrelines (natural
    streets, Douglas-Peucker at tolerance `tol`, ends extended by `tol + 1` m so lines meeting at a
    junction cross). Line count is set by stroke curvature rather than by the fewest-line criterion, and
    depthmapX analyses the lines as given. Report `tol` and the stroke angle with every S4 result.
30. **Extension buys connections.** Ends must be extended for lines that meet at a junction to
    cross, but the extension also reaches nearby streets. *Barnsbury self-check: mean
    connectivity 4.00 in the reference, 4.14 at tol 4 m, 4.29 at tol 16 m, with the same lines.*
    Connectivity and choice degrade first (ρ 0.98 to 0.97 and 0.96 to 0.95); integration least.
31. **Intelligibility and synergy are properties of a line set**, computed over lines rather than
    streets. Carried to streets (length-weighted), axial values repeat along every street a line
    covers; per-street correlations with the ladder therefore weight long lines by the number of
    streets they span. (`reports/phase1/wp4_axial.md`)
32. **An axial map generated from centrelines does not reproduce a hand-drawn one.** On Barnsbury,
    OSM-generated maps agree with the hand-drawn axial map at ρ 0.04–0.28 for every measure,
    whether OSM content is the walk network (70% more length) or streets only (matched length, but
    a third of the hand-drawn lines follow non-street open space). Hand-drawn lines sit 10–30 m off
    centrelines. Intelligibility 0.20–0.33 vs 0.54. (`reports/phase1/wp4_axial.md`)
33. **Duplicate lines vanish silently in depthmapX.** Junction consolidation leaves some streets
    twice (multi-edges with identical geometry); depthmapX keeps one copy on import, so a tool that
    counts both reports extra connections at those junctions (6–13% of line connectivities on
    cleaned networks, <1% raw). De-duplicate before comparing engines.

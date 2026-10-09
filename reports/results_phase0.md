# Phase 0 results: Copenhagen vs Mumbai island city

S0 to S3 decomposition ladder on OSM walk networks. Each row changes **one** design choice.
Values are Spearman ρ over interior segments at radii 400 / 800 / 1200 / 2000 m.
Run 7 Oct 2026; depthmapX tulip-1024, cityseer 5.8.

## Networks

| | Copenhagen + Frederiksberg | Mumbai City District |
|---|---|---|
| Area | 103.2 km² | 71.2 km² |
| Interior segments | 31,291 | 10,271 |
| Network length (interior) | 2,373 km | 1,033 km |
| **Segments per km²** | **303** | **144** |
| Median segment | 61.7 m | 73.2 m |
| Straight pieces per street (S3) | 3.5 | 3.5 |

Mumbai's built fabric is far denser than Copenhagen's, yet its mapped walk network is much
sparser: Copenhagen has about 1.6× the network length per km² (23.0 vs 14.5 km/km²). The
segment-density ratio (2.1× here) depends on junction consolidation and ranges 1.5–2.6×; the
length ratio does not (see `reports/phase1/wp2_cleaning_sensitivity.md`). The OSM walk network in Mumbai is missing most informal and internal
lanes, so every Mumbai result below is the "without informal lanes" case. Measuring what
that omission does is Project 2.

## Closeness family

| Step (one change) | Copenhagen | Mumbai |
|---|---|---|
| Representation: junction to segment | .91 .93 .95 .97 | .88 .92 .95 .97 |
| Closeness form: harmonic to NC²/TD | .98 .97 .97 .98 | .98 .98 .98 .98 |
| Cost: metric to angular | .75 .76 .78 .83 | .84 .88 .89 .91 |
| Engine + straight pieces: cityseer to depthmapX | .79 .84 .86 .90 | .67 .78 .82 .86 |
| **Normalisation: NC²/TD to NAIN** | **.53 .64 .69 .74** | **.44 .59 .68 .76** |
| End to end: metric harmonic vs NAIN | .07 .21 .29 .42 | −.03 .20 .33 .47 |

## Betweenness family

| Step (one change) | Copenhagen | Mumbai |
|---|---|---|
| Representation: junction to segment¹ | .63 .62 .60 .59 | .69 .67 .65 .61 |
| Cost: metric to angular | .79 .75 .74 .75 | .81 .75 .72 .70 |
| Engine + straight pieces: cityseer to depthmapX | .69 .73 .73 .73 | .62 .67 .66 .67 |
| Normalisation: choice to NACH | .78 .89 .92 .93 | .68 .82 .89 .94 |
| End to end: metric betweenness vs NACH | .57 .63 .64 .65 | .39 .46 .49 .52 |

¹ S0 gives a segment the mean of its two junctions, a crude transfer; read this row with care.

## Control: one straight chord per street instead of exploded curves (Copenhagen)

| Step | Exploded (standard) | Chord | Change |
|---|---|---|---|
| Closeness, engine | .79 .84 .86 .90 | .78 .81 .83 .87 | ≈ 0 / slightly lower |
| Closeness, NC²/TD to NAIN | .53 .64 .69 .74 | .64 .72 .77 .84 | **+.08 to +.11** |
| Betweenness, engine | .69 .73 .73 .73 | .66 .63 .62 .64 | lower |
| Betweenness, choice to NACH | .78 .89 .92 .93 | .88 .94 .96 .97 | **+.04 to +.10** |

## Findings

1. **"Space Syntax vs network analysis" is not one difference but several, of similar size.**
   At local radii no single step explains the gap. Angular cost, depthmapX's conventions and
   SS normalisation each reorder streets substantially. End to end, metric closeness and NAIN
   are close to unrelated at 400 m in both cities (ρ ≈ 0).
2. **The closeness formula hardly matters; the normalisation matters most.** Harmonic and
   NC²/TD agree at ρ ≈ 0.98 in both cities. NC²/TD to NAIN is the largest single step for
   closeness at local radii (ρ 0.44–0.53 at 400 m). NC is the segment count inside the radius,
   so the exponent on NC decides how much network density is rewarded. Choosing integration
   or NAIN is a substantive decision about density, not a cosmetic rescaling.
3. **Engine disagreement has two causes (revised after Phase 1 WP2–2c).** cityseer and
   depthmapX agree more as the radius grows in both cities (Copenhagen .79 to .90; Mumbai
   .67 to .86). (a) Junction consolidation appends stubs that the engines read differently;
   removing them recovers about half the gap. (b) Agreement depends on segment length relative
   to the radius: on stub-free networks closeness agreement follows one curve against median
   segment ÷ radius (rank correlation −0.96), which is the catchment-edge effect of nuance 9.
   See `reports/phase1/wp2b_consolidation_stubs.md`.
4. **Exploding curves inflates SS-normalised measures.** depthmapX counts straight pieces,
   not streets, so a curved street adds several to NC and TD. Using chords raises agreement for
   NAIN by 0.08–0.11 and for NACH by 0.04–0.10. Raw measures are almost unaffected. Any study
   that reports NAIN/NACH on OSM data inherits this geometry choice.
5. **The cities differ in where the divergence sits.** Metric vs angular cost changes Mumbai's
   rankings less than Copenhagen's (closeness .84–.91 vs .75–.83), while the engine and
   normalisation steps change Mumbai's more, and end-to-end betweenness agreement is lower
   (.39–.52 vs .57–.65). A hypothesis to test in Phase 1, not yet a result: Mumbai's mapped
   network is dominated by long arterial roads, where least-angle and shortest routes
   coincide, and is sparse inside blocks, where catchment conventions bite.
6. **cityseer's angular results depend on the radius set requested.** Runs are deterministic
   (two identical 400/800 m runs gave identical tables), but S2 at 800 m differs when 1200 and
   2000 m are computed in the same call: closeness metric to angular 0.891 vs 0.875, betweenness
   0.791 vs 0.753 (Mumbai). cityseer runs one simplest-path search per source out to the largest
   threshold, so which route counts as "simplest" to a target can change with search extent.
   Practical rule: compare radii only within runs that requested the same radius set, and
   report the set. All tables above use the 400–2000 m set.

> **Revision, 7 Oct 2026 (Phase 1 WP2).** These tables use 10 m junction consolidation.
> Finding 3 and the betweenness results are sensitive to that setting; findings 1, 2 and 4
> are not. See `reports/phase1/wp2_cleaning_sensitivity.md`.

## Caveats

- Mumbai is OSM only; Dharavi and other informal areas are under-represented (see Networks).
- Segment counts, NC and TD depend on OSM tagging, junction consolidation (10 m) and curve
  handling. Sensitivity to these is Phase 1.
- Rank agreement is not validity. Which rung tracks observed movement is a separate question
  (counts in Copenhagen; gate counts in Dharavi in Phase 2).

# WP4: S4 axial rung, intelligibility and synergy

Status, 9 Oct 2026: generator, analysis script and validation harness built and checked on
Barnsbury. City runs (Copenhagen, Mumbai island) and the OSM-against-reference validation need
OSM access and run locally; commands at the end.

## Why a generated axial map

The ladder (S0–S3) runs on street centrelines. The classic Space Syntax representation is the
axial map: the fewest longest straight lines that cover the open space, hand-drawn or derived from
building outlines. Neither is feasible for 2 cities × ~10⁴ streets, and building outlines are
incomplete in the informal fabric (Project 2). S4 therefore uses an axial map **generated from
the same centrelines**, following Liu & Jiang (2012):

1. **Natural streets.** At each junction, street ends are paired by *every best fit*: all pairs
   with deflection ≤ 30° are sorted and paired greedily, straightest first.
2. **Straightening.** Each natural street is simplified with Douglas-Peucker at `tol` (default
   8 m, about half a street width). Each straight piece is one axial line.
3. **Connection.** Lines are extended by `tol + 1` m at both ends so lines meeting at a junction
   or at a kink cross. depthmapX then treats the set as an axial map (no fewest-line reduction).
4. **Lineage.** Each line keeps the interval of its natural street it covers, so values return to
   the original streets by length-weighted mean (`transfer_to_streets`).

Code: `src/ssx/syntax/axial_gen.py` (7 tests), `scripts/09_axial.py`, `scripts/10_axial_validate.py`.

This is a third representation, distinct from both hand-drawn axial maps and segment maps. The
question it answers is "what does the axial step add or change, holding the street data fixed",
not "what would a hand-drawn axial map of Mumbai say".

## Self-check: can the generator recover a known axial map?

Input: the depthmapX Barnsbury test map (1,100 hand-drawn axial lines) split at every crossing
into 5,433 segments, used as if they were centrelines. A correct generator should rebuild the
original lines. Matching: reference lines sampled every 10 m, nearest generated line within 15 m
and ≤ 30° of direction.

| | lines | median length (m) | mean connectivity | intelligibility r | synergy r | recall | ρ conn. | ρ HH Rn | ρ HH R3 | ρ choice Rn |
|---|---|---|---|---|---|---|---|---|---|---|
| reference | 1,092 | 178 | 4.00 | 0.535 | 0.721 | | | | | |
| tol 4 m | 1,094 | 179 | 4.14 | 0.542 | 0.738 | 0.998 | 0.984 | 0.985 | 0.985 | 0.963 |
| tol 8 m | 1,094 | 179 | 4.19 | 0.536 | 0.737 | 0.998 | 0.980 | 0.980 | 0.978 | 0.958 |
| tol 12 m | 1,094 | 179 | 4.28 | 0.531 | 0.739 | 0.998 | 0.968 | 0.976 | 0.975 | 0.953 |
| tol 16 m | 1,094 | 179 | 4.29 | 0.536 | 0.743 | 0.998 | 0.966 | 0.976 | 0.974 | 0.964 |

- The line set is recovered (1,094 vs 1,092 analysed; 99.8% of reference length matched).
- The only systematic error is **extra connections from the extension**: mean connectivity
  +3.5% at tol 4 m, +7% at tol 16 m. Connectivity and choice lose rank agreement first;
  integration and intelligibility barely move.
- This bounds the generator's own error. It does **not** say how close an OSM-generated map is
  to a hand-drawn one; that is the local run below (real centrelines curve, offset and fork where
  axial lines do not).

## Smoke run of the S4 rung (Barnsbury, same pseudo-centrelines)

`09_axial.py --site barnsbury_smoke`, interior streets (n = 4,594), Spearman ρ:

| radius | axial HH Rn vs NAIN | axial HH R3 vs NAIN | axial connectivity vs NAIN | axial HH Rn vs metric harmonic | axial choice Rn vs NACH | axial choice R3 vs NACH |
|---|---|---|---|---|---|---|
| 400 | 0.48 | 0.70 | 0.72 | −0.25 | 0.38 | 0.43 |
| 800 | 0.57 | 0.82 | 0.79 | −0.18 | 0.48 | 0.53 |

Read only as a pipeline check (the map is the depthmapX test map rather than a city), but the pattern is
the one to look for in the cities:

- **Axial R3 tracks angular NAIN at 800 m (ρ 0.82) better than axial Rn does (0.57).** Three
  topological steps is a local measure, of roughly walking-catchment size here.
- **Axial global integration is unrelated or opposed to metric closeness** (ρ −0.18 to −0.25):
  long straight lines count as one step regardless of length, so a long peripheral line can be
  globally integrated while metrically remote.
- **Axial choice agrees weakly with angular NACH** (0.38–0.53): topological shortest paths have
  many ties (nuance 4) and count line changes rather than turns.
- Barnsbury intelligibility r = 0.54 (r² 0.29), synergy r = 0.72–0.76.

## City runs (9 Oct 2026, tol 8 m, angle 30°)

| | streets | axial lines | lines / street | median line (m) | mean conn. | intelligibility r (all / interior) | synergy r (all / interior) | dmX = geometric conn. |
|---|---|---|---|---|---|---|---|---|
| Copenhagen c10dp | 45,601 | 38,831 | 0.85 | 54 | 4.60 | 0.125 / 0.120 | 0.216 / 0.228 | 90.5% |
| Mumbai island c10dp | 11,983 | 10,087 | 0.84 | 79 | 4.30 | 0.093 / 0.019 | 0.241 / 0.151 | 93.6% |
| Copenhagen c0 | 97,085 | 54,220 | 0.56 | 40 | 3.64 | 0.105 / 0.095 | 0.248 / 0.284 | 99.2% |
| Mumbai island c0 | 21,348 | 13,322 | 0.62 | 63 | 3.55 | 0.153 / 0.154 | 0.323 / 0.329 | 99.8% |
| Copenhagen c10dp tol 4 | | 51,183 | 1.12 | 40 | 4.10 | 0.117 / 0.121 | 0.200 / 0.220 | 87.0% |
| Copenhagen c10dp tol 16 | | 29,138 | 0.64 | 72 | 5.38 | 0.137 / 0.127 | 0.237 / 0.242 | 92.4% |
| *Barnsbury, hand-drawn* | | 1,092 | | 178 | 4.00 | 0.535 | 0.721 | |

S4 vs the ladder, interior streets, Spearman ρ (c10dp; c0 in brackets):

| | radius | HH Rn vs NAIN | HH R3 vs NAIN | HH Rn vs metric harmonic | choice Rn vs NACH | choice R3 vs NACH |
|---|---|---|---|---|---|---|
| Copenhagen | 400 | 0.12 (0.16) | 0.59 (0.64) | 0.22 (0.17) | 0.61 (0.73) | 0.63 (0.76) |
| | 800 | 0.22 (0.26) | 0.58 (0.59) | 0.40 (0.31) | 0.70 (0.78) | 0.69 (0.79) |
| | 2000 | 0.40 (0.45) | 0.45 (0.45) | 0.68 (0.58) | 0.73 (0.80) | 0.68 (0.78) |
| Mumbai island | 400 | 0.26 (0.26) | 0.45 (0.59) | −0.06 (−0.01) | 0.48 (0.62) | 0.46 (0.64) |
| | 800 | 0.32 (0.33) | 0.58 (0.64) | 0.00 (0.05) | 0.63 (0.72) | 0.58 (0.73) |
| | 2000 | 0.30 (0.44) | 0.55 (0.61) | 0.13 (0.17) | 0.70 (0.78) | 0.60 (0.76) |

Provisional reading (pending the coverage diagnostic below):

1. **Generated lines are 3–4× shorter than hand-drawn axial lines** (median 40–80 m vs 178 m) and
   near one per street. They behave as a line-based topological analysis of the centrelines rather than
   as a fewest-line axial map.
2. **Intelligibility is near zero in both cities (r 0.02–0.15)**, synergy 0.15–0.33. The city
   difference is smaller than the cleaning difference (Mumbai interior intelligibility 0.02 at
   c10dp, 0.15 at c0), and both are far below the hand-drawn Barnsbury map (0.54).
3. **Tolerance moves the map and leaves the ranking.** tol 4 to 16 m: lines 51k to 29k, mean connectivity
   4.10 to 5.38, intelligibility 0.12 to 0.14; every ladder ρ moves by ≤ 0.05.
4. **Axial choice is the bridge between the representations** (ρ 0.6–0.8 with angular NACH at
   every radius, both cities); axial integration Rn is not (0.1–0.45).
5. **City contrast in global axial integration vs metric closeness:** Copenhagen rises to 0.68 at
   2 km; Mumbai island stays at −0.06 to 0.17. The island city is a long peninsula, so Rn depth is
   set by position along it (cf. WP3: global measures follow map shape and position).
6. The 6–13% connectivity mismatch on c10dp was duplicate streets rather than depthmapX (see below).

## Barnsbury: OSM-generated vs hand-drawn (first run)

| map | lines | median (m) | mean conn. | intell. r | synergy r | recall | precision | ρ conn. | ρ HH Rn | ρ choice Rn |
|---|---|---|---|---|---|---|---|---|---|---|
| reference | 1,092 | 178 | 4.00 | 0.535 | 0.721 | | | | | |
| c10dp tol 8 | 5,460 | 53 | 4.26 | 0.203 | 0.320 | 0.35 | 0.39 | 0.08 | 0.18 | 0.24 |
| c0 tol 8 | 7,598 | 39 | 3.61 | 0.177 | 0.370 | 0.43 | 0.39 | 0.18 | 0.15 | 0.31 |

**Coverage diagnostic (`11_axial_diag.py coverage`): no offset; the maps differ in content and
line placement.**

- Offset scan: best shift (0, −1 m), recall within 5 m 0.247 to 0.249. This rules out a datum/grid shift.
- Distance from reference samples to the nearest OSM centreline: 25% within 5 m, 56% within 15 m,
  75% within 25 m, 95% within 50 m. Hand-drawn axial lines run through open space (corner to
  corner, across squares, straight through gentle bends), typically 10–30 m off the centreline.
- Content: OSM walk network 24.2 km/km² inside the hull vs 14.3 km/km² in the reference. About 40%
  of OSM length (footways, estate paths, service roads) has no counterpart in the hand-drawn map.
- Matched share does not vary with reference line length (0.54–0.58); it is lowest in the core
  (0.51–0.52) and highest at the edge (0.63).

**Second run: content and placement separated (30 m matching).**

| OSM network | km/km² (ref 14.3) | reference within 15 / 25 / 50 m | tol | lines | median (m) | intell. r | synergy r | recall | precision | ρ conn. | ρ HH Rn | ρ HH R3 | ρ choice Rn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| walk, c10dp | 24.2 | 0.56 / 0.75 / 0.95 | 8 | 5,460 | 53 | 0.20 | 0.32 | 0.59 | 0.65 | 0.08 | 0.18 | 0.04 | 0.21 |
| walk, c10dp | | | 16 | 4,004 | 73 | 0.27 | 0.43 | 0.59 | 0.65 | 0.10 | 0.20 | 0.06 | 0.19 |
| streets only, c10dp | 13.0 | 0.39 / 0.57 / 0.84 | 8 | 1,782 | 98 | 0.27 | 0.44 | 0.39 | 0.65 | 0.12 | 0.25 | 0.15 | 0.12 |
| streets only, c10dp | | | 16 | 1,400 | 123 | 0.33 | 0.55 | 0.40 | 0.65 | 0.16 | 0.28 | 0.14 | 0.17 |
| *reference (hand-drawn)* | 14.3 | | | 1,092 | 178 | 0.54 | 0.72 | | | | | | |

- Neither OSM layer reproduces the reference's content. With streets only, the length matches
  (13.0 vs 14.3 km/km²) but only 39% of reference length lies within 15 m of a street: about a
  third of the hand-drawn map follows paths and open space that are not streets. With the walk
  network those paths are present, but so is 70% extra length.
- **Rank agreement with the hand-drawn map stays at ρ 0.04–0.28 for every measure, content
  choice, tolerance and matching radius.** Agreement is not limited by matching: lines that
  coincide in space still carry different values, because axial values depend on the topology of
  the whole map.
- Intelligibility and synergy rise with tolerance and with streets-only content (longer, fewer
  lines) but stay well below the hand-drawn map (0.33 / 0.55 at best vs 0.54 / 0.72).

**Conclusion for S4.** An axial map generated from OSM centrelines is a separate representation.
It does not stand in for hand-drawn axial analysis (ρ ≤ 0.28 on Barnsbury). It relates more
closely to the angular segment rung (axial choice vs NACH ρ 0.6–0.8 in both cities) than to the
axial map it imitates. City S4 results are reported as "centreline line-map" results rather than as
axial-map results. A like-for-like axial comparison needs hand-drawn lines (P2 sample tile with a
written protocol).

**Connection diagnostic: resolved, no effect on the results.** The Mumbai c10dp line file has
78 exactly coincident axial lines (the same street present twice in the cleaned network, as
multi-edges left by junction consolidation). depthmapX drops duplicates on import, so it analyses
10,009 lines; the geometric test counted both copies, giving every neighbour one extra connection.
The earlier "missed crossings at merged junctions" were this plus a mapping bug in the diagnostic
(one depthmapX Ref standing for two of our rows). With duplicates removed, depthmapX and the
geometric test agree on 100% of lines. depthmapX had analysed the de-duplicated map all along, so
the city S4 values above stand; only the "dmX = geometric conn." column was measuring duplicates
(c10dp has more because consolidation creates the multi-edges). The generator now merges
coincident lines itself (`axial_lines`, lineage merged), so the check reads 100% on rerun.

## Pending local runs

```bash
export DEPTHMAPX=/path/to/depthmapXcli

# 1. validation against the hand-drawn reference, real OSM centrelines (fetches OSM once)
python scripts/10_axial_validate.py \
  --reference ~/depthmapX/testdata/barnsbury_extended1_axial.csv --crs 27700 --fetch \
  --name barnsbury_osm
python scripts/10_axial_validate.py \
  --reference ~/depthmapX/testdata/barnsbury_extended1_axial.csv --crs 27700 --fetch \
  --consolidate 0 --name barnsbury_osm_c0

# 2. S4 per city, both baselines (ladder.gpkg must exist for the agreement table)
for s in copenhagen_c10dp mumbai_island_c10dp copenhagen_c0 mumbai_island_c0; do
  python scripts/09_axial.py --site $s
done
# tolerance sensitivity on one baseline
python scripts/09_axial.py --site copenhagen_c10dp --tol 4 --tag _tol4
python scripts/09_axial.py --site copenhagen_c10dp --tol 16 --tag _tol16
```

Outputs: `data/<site>/axial/{axial.gpkg, summary.json, agreement_axial.csv}`,
`data/barnsbury_osm*/axial_validate.csv`. Send the console logs back.

Run time: line count is about 0.2 × streets on Barnsbury; on OSM it will be higher (curves).
depthmapX axial Rn with choice is one BFS per line, so expect minutes to tens of minutes per
city, much less than S3.

## What to report from the city runs

1. Validation table (OSM vs reference): recall, precision, ρ per measure, intelligibility of both
   maps. This sets how far S4 results can be read as "axial analysis".
2. Per city: lines, lines per street, median line length, intelligibility (all and interior),
   synergy. Copenhagen vs Mumbai island at both cleaning levels.
3. S4 vs ladder agreement at 400–2000 m, beside the S3 table.
4. Whether cleaning (c0 vs c10dp) changes intelligibility more than the city does (the WP1/WP2
   pattern: within-setup differences vs between-city differences).

## Limits

- A line map rather than a fewest-line map; no unlinks for bridges and flyovers (Mumbai has many; Project 2 may add
  an unlink list from OSM `bridge`/`tunnel` tags).
- Extension adds connections; `tol` and stroke angle change the map and are reported.
- Six interior streets of ~1 cm (degenerate geometry) get no S4 value.
- Intelligibility is known to fall with map size; the two cities' maps differ in size, so compare
  them at matched extents (WP3 extents) before reading a city difference into it.

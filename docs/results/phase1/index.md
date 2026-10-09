# Space Syntax decomposed — Phase 0–1 report

Manish Bilore · 9 October 2026 · code: `ss_vs_assembled` · maps: `reports/atlas/` (`scripts/12_atlas.py`)

## 1. Question

Space Syntax (SS) and "assembled" network analysis (graph centrality on street centrelines, here
cityseer) both rank streets by how central they are, and are often treated as interchangeable or
as rivals. This project does not ask which is better. It asks **which design choices separate
them, how much each one moves the result, and where in a city it does so**, on two contrasting
test beds:

- **Copenhagen + Frederiksberg**: formal, well-mapped network (OSM walk network 23–26 km/km²).
- **Mumbai City District (island city)**: formal fabric interleaved with informal settlements
  (Dharavi) whose lanes OSM largely omits (14–16 km/km² despite far denser built fabric). All
  Mumbai results are the "without informal lanes" case; adding them is Project 2.

## 2. Method: a ladder of single changes

The route from a metric centrality to an SS measure is decomposed into rungs; adjacent rungs
differ by exactly one design choice, and their rank agreement (Spearman ρ over interior streets)
measures what that choice does.

| Rung | Representation | Cost | Measure | Engine |
|---|---|---|---|---|
| S0 | junction graph | metric | harmonic closeness, betweenness | cityseer |
| S1 | segment (dual) graph | metric | harmonic, NC²/TD, betweenness | cityseer |
| S2 | segment graph | angular | NC²/TD, betweenness | cityseer |
| S3 | straight pieces | angular (tulip-1024) | integration, choice to **NAIN, NACH** | depthmapX |
| S4 | axial lines generated from centrelines | topological | integration HH Rn/R3, choice, intelligibility, synergy | depthmapX |

**Fidelity first.** The SS measures were reimplemented from depthmapX's source and checked on
its Barnsbury test map: axial measures match to ~1e-7; angular segment measures match exactly
once depthmapX's conventions are reproduced (tulip binning, metric-first tie-breaking, metric
radius along the least-angle route, per-direction choice counting). These conventions are
catalogued in `docs/nuances.md` (33 entries) because each one changes results.

**Baselines.** Interior = inside the administrative boundary; a 2 km buffer supplies full
catchments (WP3 confirms this suffices). Two network baselines per city: raw OSM (0 m) and
cleaned (10 m junction consolidation, consolidation stubs removed, parallel carriageways merged).

Maps: `a01_context_*` (study networks and zoom windows).

## 3. Findings

### 3.1 The gap between SS and network analysis is several gaps of similar size (Phase 0)

| Step, ρ at 400 / 800 / 1200 / 2000 m | Copenhagen | Mumbai |
|---|---|---|
| junction to segment | .91 .93 .95 .97 | .88 .92 .95 .97 |
| harmonic to NC²/TD | .98 .97 .97 .98 | .98 .98 .98 .98 |
| metric to angular | .75 .76 .78 .83 | .84 .88 .89 .91 |
| cityseer to depthmapX | .79 .84 .86 .90 | .67 .78 .82 .86 |
| **NC²/TD to NAIN** | **.53 .64 .69 .74** | **.44 .59 .68 .76** |
| end to end (metric harmonic vs NAIN) | .07 .21 .29 .42 | −.03 .20 .33 .47 |

(cleaned 10 m baseline; betweenness family in `reports/results_phase0.md`)

- At walking radii, metric closeness and NAIN are nearly unrelated (ρ ≈ 0 at 400 m in both
  cities). No single step explains this: angular cost, engine conventions and SS normalisation
  each reorder streets by comparable amounts.
- The closeness formula hardly matters (ρ 0.98); the **normalisation is the largest single
  step**. NAIN = NC^1.2/(TD+2) decides how much segment density is rewarded.
- Betweenness survives the ladder better (end to end 0.39–0.65).

Maps: `a02_ladder_closeness_*`, `a03_ladder_betweenness_*` (the same streets on every rung),
`a04_steps_closeness_*`, `a05_steps_betweenness_*` (where each step reorders streets),
`a06_radii_nain_*`, `a07_radii_nach_*` (local to city-wide structure).

### 3.2 Places differ more than cities do (WP1)

Recomputing agreement inside 1 km tiles (cleaned baseline, R800): the two city medians differ by
only 0.01–0.04 for every step, while the spread across tiles within one city (p10–p90) is
0.20–0.60 wide. Tile network density explains little (|r| < 0.3 for 6 of 8 steps). Mumbai has the
longer low tail: its worst tiles disagree more than Copenhagen's for NAIN (p10 0.40 vs 0.51),
end-to-end closeness (−0.12 vs 0.00) and betweenness (0.47 vs 0.59).

Maps: `a12_tiles_*`.

### 3.3 Network cleaning is a design choice as large as angular cost (WP2, WP2b)

- One parameter (junction consolidation 0 to 20 m) changes Copenhagen's segment count 4.2× and
  drops cityseer–depthmapX agreement from 0.90–0.99 to 0.54–0.92.
- Mechanism: osmnx consolidation appends stubs at merged junctions; cityseer routes along them
  (angular cost up), depthmapX counts them as pieces (NC up). Removing stubs recovers about half
  of the lost agreement; the rest follows **median segment length ÷ radius** (rank correlation
  −0.96 across 20 runs, both cities). Merging dual carriageways does not change it.
- Compare cities by network length per km² (ratio 1.57–1.58 at every setting), not by segment
  counts (ratio 1.5–2.6 depending on cleaning).

Maps: `a11_cleaning_*` (same window, raw vs cleaned); `figures/fig6`, `fig7`.

### 3.4 Where the map stops matters for global measures, and position matters more than size (WP3)

Dharavi's 278 streets analysed inside maps of growing extent, against Greater Mumbai + 2 km:

- Radius-bounded measures are exact (ρ = 1.00) once the surround reaches the radius. The 2 km
  buffer used throughout is sufficient.
- Global NAIN converges fast with a surround centred on the study area (1 km: 0.96; 4 km: 0.99),
  but the island city, four times larger with Dharavi near its edge, reaches only 0.83. Clipped
  at its boundary, Dharavi's global ranking is 0.53.

Figure: `figures/fig8_nested.png`.

### 3.5 An axial map generated from centrelines is a different representation (WP4)

Axial lines were generated from the same centrelines (natural streets, Douglas-Peucker at 8 m,
extended to cross) and analysed in depthmapX.

| | lines | median line | intelligibility r | synergy r |
|---|---|---|---|---|
| Copenhagen, cleaned / raw | 38.8k / 54.2k | 54 / 40 m | 0.12 / 0.10 | 0.23 / 0.28 |
| Mumbai island, cleaned / raw | 10.1k / 13.3k | 79 / 63 m | 0.02 / 0.15 | 0.15 / 0.33 |
| Barnsbury, hand-drawn | 1.1k | 178 m | 0.54 | 0.72 |

- **Generated maps do not reproduce a hand-drawn one.** On Barnsbury, OSM-generated maps agree
  with the hand-drawn axial map at ρ 0.04–0.28 for every measure, with walk or streets-only OSM,
  at every tolerance. Hand-drawn lines run 10–30 m off centrelines and a third follow open space
  that is not a street; the walk network adds 70% more length than the hand-drawn map holds.
- **Axial choice is the bridge**: it tracks angular NACH at ρ 0.6–0.8 in both cities, at every
  radius. Axial integration Rn does not (0.1–0.45).
- Intelligibility is near zero in both cities, and cleaning moves it more than the city does.
- Global axial integration vs metric closeness: Copenhagen rises to 0.68 at 2 km; Mumbai stays
  near 0. The island city is a long peninsula, so global depth tracks position along it (cf. 3.4).
- depthmapX silently keeps one copy of coincident lines; a tool that counts both reports 6–13%
  extra connections on cleaned networks. Now de-duplicated in the generator.

Maps: `a08_axial_*`, `a09_axial_vs_angular_*`, `b01_barnsbury_axial`, `b02_barnsbury_coverage`.

## 4. What this adds up to

1. "Space Syntax vs network analysis" is a bundle of decisions: representation, cost, engine
   conventions, normalisation, network cleaning, map extent, and (for axial) how lines are drawn.
   Several of them are as large as the headline difference people usually argue about.
2. The decisions that look technical (consolidation tolerance, stub handling, where the map
   stops, duplicate lines) are not small. They belong in every methods section.
3. Choice/betweenness is the robust family across all representations; integration/closeness is
   where the approaches part ways, mostly through normalisation.
4. Differences between neighbourhoods inside a city are an order of magnitude larger than between
   Copenhagen and Mumbai.
   For an interleaved formal–informal city this points straight at Project 2.

## 5. Limits

- Mumbai's OSM network omits most informal lanes; all Mumbai results are a lower bound on what
  the informal fabric changes.
- No empirical movement data yet (WP5: Copenhagen counts; Project 2: Dharavi gate counts). The
  project compares methods, it does not validate either against behaviour.
- One cleaning pipeline (osmnx); one SS engine (depthmapX). S4 is a generated line map, not
  a fewest-line or hand-drawn axial map.
- Coincident duplicate streets remain in the cleaned networks for S0–S3 (≈ 0.7% of Mumbai's
  lines); depthmapX drops them, cityseer keeps them.

## 6. Next

- WP5: Copenhagen pedestrian/cycle counts against each rung (descriptive).
- WP6: conference abstract from §3–4.
- Project 2: Dharavi lanes digitised under a written protocol; informal-lane inclusion delta for
  every measure; hand-drawn axial sample tile; gate counts.
- Project 3: naive pedestrian-weighted exposure pilot built on the robust measures (NACH).

## Atlas index

`reports/atlas/atlas.md` lists every map with an auto-generated caption (ρ values computed from
the data). Classes are quintiles within each panel: ranks, not raw values, are comparable across
panels and cities. Divergence maps show the percentile-rank difference between two measures,
thin grey where they agree within 10 points.

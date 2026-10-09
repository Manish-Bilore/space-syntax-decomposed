# Space Syntax, decomposed: full report (Phases 0–1)

**Manish Bilore** · October 2026 · code and data pipeline: this repository

!!! abstract "Summary"
    Space Syntax (SS) and conventional street-network analysis both rank streets by how central
    they are. They are often used interchangeably, or argued about as rivals, without separating
    the decisions that make them differ. This work breaks the route from a plain metric
    centrality to the standard SS measures (NAIN, NACH) into a **ladder of single changes**
    (representation, cost, closeness formula, engine, normalisation, line construction) and
    measures what each change does to the ranking of streets, in **Copenhagen + Frederiksberg**
    and the **Mumbai island city**, on OpenStreetMap walk networks.

    The SS measures were first reimplemented from depthmapX's source and matched to it exactly
    on its own test map. Then:

    1. At walking radii, metric closeness and SS integration (NAIN) are nearly **unrelated**
       (ρ ≈ 0 at 400 m in both cities). No single step explains it; the **normalisation** is the
       largest one.
    2. **Choice / betweenness is robust** across every representation, including axial lines
       generated from centrelines; integration / closeness is where the approaches part ways.
    3. **Network cleaning** (junction consolidation) is a design choice as large as angular cost,
       and it disturbs the two engines in opposite directions.
    4. **Map extent** matters for global measures, and position matters more than size.
    5. Axial maps **generated from centrelines do not reproduce a hand-drawn axial map**
       (ρ ≤ 0.28).
    6. **Neighbourhoods differ more than cities**: within-city spread of agreement is an order
       of magnitude larger than the Copenhagen–Mumbai difference.

---

## 1. Why this question

Space Syntax (Hillier & Hanson 1984; Hillier 1996) models how the configuration of urban space
relates to movement and use, and has a large empirical literature linking its measures to
pedestrian and vehicle flows (e.g. Hillier & Iida 2005). Network science reached similar
measures independently: closeness and betweenness on the primal or dual street graph
(Porta, Crucitti & Latora 2006; Crucitti, Latora & Porta 2006), now available in open tools
such as cityseer (Simons 2023) and OSMnx (Boeing 2017).

The two traditions differ in many small ways at once: what a "node" is (a junction, a street
segment, a line of sight), how distance is counted (metres, turns, line changes), how a
centrality is normalised, how the network is cleaned, and where the map stops. Published
comparisons usually contrast whole workflows, so a difference in results cannot be attributed to
any one of these choices. Critiques of SS (e.g. Ratti 2004) and its replies have the same
problem.

This project asks a narrower, answerable question:

> **Which design choices separate SS from network analysis, how much does each one move the
> ranking of streets, and where in a city does it do so?**

It does not ask which approach is better; that would need movement data (Section 9).

The two test beds were chosen for contrast:

- **Copenhagen + Frederiksberg**: formal, regular, well-mapped (OSM walk network 23–26 km per km²).
- **Mumbai City District (island city)**: formal fabric interleaved with informal settlements
  such as Dharavi, whose lanes OpenStreetMap largely omits (14–16 km per km², despite far denser
  built fabric). All Mumbai results here are therefore the "without informal lanes" case;
  measuring what the lanes change is Project 2.

---

## 2. Definitions

This section defines every representation and measure used. Notation: a graph has nodes
\(i, j\); \(d_{ij}\) is the shortest-path distance between them under the chosen cost; a radius
\(r\) restricts the analysis from each node to nodes with \(d_{ij} \le r\) (in metres for metric
and angular analysis, in steps for axial analysis); "Rn" means no radius (the whole map).

### 2.1 Representations

**Primal (junction) graph.** Nodes are street junctions and dead ends; edges are street segments
between them, weighted by length. This is the default in OSMnx and most transport analysis.

**Segment (dual) graph.** Nodes are street segments (junction to junction); two segments are
linked if they share a junction. Values belong to streets rather than to junctions, which is how
SS reports results. Called the *dual* graph in network science.

**Straight-piece (segment) map.** depthmapX's segment analysis (Turner 2007) works on straight
lines only. A curved street is split into its straight pieces, each a node; turns between pieces
along the curve count as angular cost.

**Axial map.** The fewest and longest straight lines that cover all open space and make all its
connections (Hillier & Hanson 1984). Nodes are lines; two lines are linked if they intersect.
Distance is the number of line changes (topological steps). Traditionally hand-drawn.

**Generated axial map (S4 here).** Lines generated from street centrelines (Liu & Jiang 2012):
streets are joined into *natural streets* by good continuation at junctions, each natural street
is straightened with a Douglas–Peucker tolerance (8 m by default), and line ends are extended by
the tolerance + 1 m so lines meeting at a junction cross. This is *not* a fewest-line map
(Section 6.5).

**Natural street (stroke).** A chain of street segments that continue each other through
junctions with a deflection ≤ 30°, paired greedily from the straightest continuation down
("every best fit").

**Interior and buffer.** Every study area is analysed with a 2 km buffer of surrounding streets
so that streets near the boundary see a full catchment; only *interior* streets (midpoint inside
the boundary) are reported.

### 2.2 Distance and cost

**Metric distance.** Length along the network, in metres.

**Angular distance.** The sum of turn angles along a route, in units of 90° (a right-angle turn
costs 1, going straight costs 0). The *least-angle* route minimises it. In depthmapX turns are
**binned** ("tulip" binning, 1024 bins per full circle), which quantises angles to 1/256 of a
right angle.

**Topological distance (steps).** The number of line changes between two axial lines.

**Metric radius on angular analysis.** In depthmapX an angular analysis "at R800" includes the
segments whose distance *along the least-angle route* is ≤ 800 m, measured midpoint to midpoint.
This is not the same catchment as the 800 m metric neighbourhood (nuance 9).

### 2.3 Closeness-type measures

For node \(i\) with catchment \(N_i(r)\) (nodes within radius \(r\), excluding \(i\)):

| Measure | Definition | Where used |
|---|---|---|
| Node count \(NC\) | \(\lvert N_i(r) \rvert\) (depthmapX counts the root as well) | all |
| Total depth \(TD\) | \(\sum_{j \in N_i(r)} d_{ij}\) | all |
| Mean depth \(MD\) | \(TD / (k - 1)\), with \(k\) nodes including the root | axial |
| Harmonic closeness | \(\sum_{j \in N_i(r)} 1/d_{ij}\) | S0, S1 (cityseer) |
| Hillier closeness | \(NC^2 / TD\) | S1, S2 (cityseer "hillier") |
| Angular integration | \(NC^2 / TD\) (depthmapX ≥ 10) | S3 |
| **NAIN** | \(NC^{1.2} / (TD + 2)\) (Hillier, Yang & Turner 2012) | S3 |

Axial (topological) integration uses the relative asymmetry of the classical theory:

- **RA** \(= 2(MD - 1)/(k - 2)\): 0 when every line is one step away, 1 when the lines form a chain.
- **D-value** \(D_k = 2\{k[\log_2((k+2)/3) - 1] + 1\}/[(k-1)(k-2)]\): the RA of the root of a
  diamond-shaped graph of \(k\) nodes, used to compare maps of different size.
- **RRA** \(= RA / D_k\), and **integration HH** \(= 1/RRA = D_k / RA\). Higher = more integrated.
- **P-value** and **Teklenburg** integration (Teklenburg, Timmermans & van Wagenberg 1993) are
  alternative normalisers; both are computed but not used in the comparisons.
- Integration is undefined where \(MD \le 1\); depthmapX writes −1 there. It is treated as missing,
  never as a large value (nuance 2).
- **R3** means a radius of three topological steps: a local measure with its own normaliser,
  not a scaled-down Rn (nuance 3).

### 2.4 Betweenness-type measures

| Measure | Definition | Where used |
|---|---|---|
| Betweenness | number of shortest routes (within \(r\)) between other pairs that pass through \(i\) (Freeman 1977) | S0–S2 (cityseer) |
| Choice | the SS name for betweenness on least-angle (segment) or fewest-step (axial) routes | S3, S4 |
| **NACH** | \(\log(CH + 1) / \log(TD + 3)\) (Hillier, Yang & Turner 2012) | S3 |

Two engine conventions matter. depthmapX counts angular choice **per direction** of travel
along a segment (nuance 12), and breaks ties between equally short *axial* routes at **random**
(nuance 4). Both were reproduced exactly in the reimplementation.

### 2.5 Local and second-order axial measures

- **Connectivity**: number of lines a line intersects.
- **Control**: \(\sum_{j \in \text{nbrs}(i)} 1/\text{conn}(j)\). **Controllability**: connectivity
  divided by the number of lines within two steps.
- **Intelligibility**: Pearson \(r\) between connectivity (what is visible from a line) and
  integration HH Rn (its position in the whole). High intelligibility means local cues tell you
  where you are in the city. Reported as \(r\) and \(r^2\).
- **Synergy**: Pearson \(r\) between integration HH R3 and integration HH Rn: whether local and
  global structure coincide.

### 2.6 Comparison statistics

- **Spearman ρ** between two measures over the interior streets: do they *order* streets the
  same way? Ranks are used throughout because the measures have different units and
  normalisations; the research question is about ordering, not magnitude.
- **Top-10% overlap**: the share of the top decile by one measure that is also in the top decile
  by the other.
- **Percentile-rank difference** (maps): for each street, its percentile rank under measure A
  minus under measure B. Within ±10 points counts as agreement.

### 2.7 Network cleaning

- **Junction consolidation** (OSMnx `consolidate_intersections`): merges junction nodes within a
  tolerance (here 0, 10 or 20 m) into one, to collapse dual carriageways and offset crossings.
- **Consolidation stub**: the short straight piece OSMnx appends from a street's old end point to
  the merged junction (Section 6.3).
- **Destubbing**: removing those stubs, so the street runs straight to the merged junction.
- **Parallel merge**: keeping one street where several join the same two junctions within the
  tolerance (dual carriageways).
- **Baselines** used throughout: *raw* (0 m) and *cleaned* (10 m, destubbed, parallels merged),
  labelled `c0` and `c10dp`.

---

## 3. Data and study areas

| | Copenhagen + Frederiksberg | Mumbai City District |
|---|---|---|
| Boundary | the two municipalities | the island city district |
| Area | 103.2 km² | 71.2 km² |
| CRS | ETRS89 / UTM 32N (EPSG:25832) | WGS 84 / UTM 43N (EPSG:32643) |
| OSM walk network (interior), cleaned | 2,373 km; 23.0 km/km² | 1,033 km; 14.5 km/km² |
| Interior streets, raw / cleaned | 64,625 / 31,291 (10 m) | 16,987 / 10,271 (10 m) |
| Median street, raw / cleaned | 27 m / 62 m | 43 m / 73 m |

- Networks: OSMnx walk networks, simplified, projected, made undirected; streets kept as
  junction-to-junction polylines with their geometry.
- Copenhagen has about **1.6× the network length per km²** of Mumbai at every cleaning setting
  (1.57–1.58×). Segment-count ratios are unstable (1.5–2.6× depending on cleaning) and should not
  be quoted (Section 6.3).
- Mumbai's OSM network omits most informal and internal lanes. Every Mumbai result is a lower
  bound on what the informal fabric changes.
- Reference map for fidelity and axial validation: depthmapX's Barnsbury (London) test data,
  1,100 hand-drawn axial lines, 5,459 segments after axial-to-segment conversion.
- Street data © OpenStreetMap contributors, available under the Open Database Licence.

![Copenhagen study network](atlas/a01_context_copenhagen_c10dp.png)
![Mumbai study network](atlas/a01_context_mumbai_island_c10dp.png)

---

## 4. Method

### 4.1 The ladder

The route from a metric centrality to an SS measure is broken into rungs. Adjacent rungs differ
in **exactly one** design choice; the Spearman ρ between them over interior streets measures what
that choice does.

| Rung | Representation | Cost | Measures | Engine |
|---|---|---|---|---|
| S0 | junction graph | metric | harmonic closeness, betweenness | cityseer |
| S1 | segment graph | metric | harmonic, \(NC^2/TD\), betweenness | cityseer |
| S2 | segment graph | angular | \(NC^2/TD\), betweenness | cityseer |
| S3 | straight pieces | angular (tulip-1024) | integration, choice, **NAIN, NACH** | depthmapX |
| S4 | generated axial lines | topological | integration HH Rn / R3, choice, intelligibility, synergy | depthmapX |

Steps compared (closeness family): junction → segment; harmonic → \(NC^2/TD\); metric → angular;
cityseer → depthmapX (engine and straight pieces together); \(NC^2/TD\) → NAIN; and end to end
(S1 harmonic vs NAIN). Betweenness family: the same without the formula step, and choice → NACH.

Radii: 400, 800, 1200 and 2000 m (walking to city-wide). S0 values are carried to streets as
the mean of their two junctions; S3 and S4 values are carried back to the original streets as
length-weighted means over the pieces or lines that cover them.

### 4.2 Fidelity before comparison

A comparison of engines is only meaningful if the reference engine is understood. The SS
measures were reimplemented in Python from depthmapX's source (`axialintegration.cpp`,
`segmtulip.cpp`, `connector.h`) and checked on the Barnsbury map, feeding both the same
connection lists:

- **Axial**: every depth and integration measure matches depthmapX to ~1e-7 relative error on
  all lines. Axial choice matches in total and at ρ 0.996 per line; the residual is depthmapX's
  random tie-breaking (two depthmapX runs agree with each other at 0.995).
- **Angular segment**: node count, total depth and integration match exactly at R400–Rn once
  tulip binning, metric-first tie-breaking within a bin, and metric radius along the least-angle
  route are reproduced. Choice matches exactly for 99.1–100% of segments once depthmapX's
  per-direction counting is reproduced.
- Intelligibility r = 0.535, synergy r = 0.721 on Barnsbury, identical in both implementations.

The conventions found on the way are catalogued with their consequences in the
[nuance catalogue](nuances.md) (33 entries); several of them change results by more than the
differences usually argued about.

### 4.3 Work packages

| WP | Question | Design |
|---|---|---|
| Phase 0 | What does each ladder step do, city-wide? | S0–S3 on both cities, 4 radii; chord control (one straight line per street) |
| WP1 | Is disagreement uniform across a city? | ρ recomputed inside 1 km (and 2 km) equal-area tiles; compared with tile network density |
| WP2 | How much is network cleaning? | full ladder at 0, 10, 20 m consolidation |
| WP2b | Why does cleaning split the engines? | synthetic junction; stub census; destubbing; parallel merge; engine agreement vs segment length ÷ radius (20 runs) |
| WP3 | Does it matter where the map stops? | Dharavi analysed in nested maps (clipped; +0.5, 1, 2, 4 km; G/North ward; island city) against Greater Mumbai + 2 km |
| WP4 | What does the axial step add? | axial lines generated from centrelines (S4); validation against the hand-drawn Barnsbury map; tolerance 4–16 m |

---

## 5. Results: the ladder (Phase 0)

Spearman ρ between adjacent rungs, interior streets, cleaned networks, at 400 / 800 / 1200 / 2000 m:

| Step (one change) | Copenhagen | Mumbai |
|---|---|---|
| junction → segment | .91 .93 .95 .97 | .88 .92 .95 .97 |
| harmonic → \(NC^2/TD\) | .98 .97 .97 .98 | .98 .98 .98 .98 |
| metric → angular | .75 .76 .78 .83 | .84 .88 .89 .91 |
| cityseer → depthmapX | .79 .84 .86 .90 | .67 .78 .82 .86 |
| **\(NC^2/TD\) → NAIN** | **.53 .64 .69 .74** | **.44 .59 .68 .76** |
| **end to end: metric harmonic vs NAIN** | **.07 .21 .29 .42** | **−.03 .20 .33 .47** |

| Step (betweenness) | Copenhagen | Mumbai |
|---|---|---|
| junction → segment | .63 .62 .60 .59 | .69 .67 .65 .61 |
| metric → angular | .79 .75 .74 .75 | .81 .75 .72 .70 |
| cityseer → depthmapX | .69 .73 .73 .73 | .62 .67 .66 .67 |
| choice → NACH | .78 .89 .92 .93 | .68 .82 .89 .94 |
| end to end: metric betweenness vs NACH | .57 .63 .64 .65 | .39 .46 .49 .52 |

**Reading.**

1. *No single step explains the gap.* At walking radii the end-to-end agreement between metric
   closeness and NAIN is near zero in both cities. Angular cost, engine conventions and SS
   normalisation each reorder streets by comparable amounts; the effects compound.
2. *The closeness formula hardly matters* (harmonic vs \(NC^2/TD\): ρ ≈ 0.98). What matters is
   the **normalisation**: NAIN raises NC to the power 1.2 and adds constants, which decides how
   much a dense catchment is rewarded. It is the single largest step at local radii.
3. *Agreement grows with radius* for every step: at 2 km the approaches converge somewhat
   (end to end 0.42–0.47), because large catchments average out local differences.
4. *Betweenness survives the ladder far better* (end to end 0.39–0.65) than closeness.
5. *Curves matter for normalised measures.* Replacing each curved street by one straight chord
   raises \(NC^2/TD\) → NAIN agreement by 0.08–0.11 and choice → NACH by 0.04–0.10, because NC
   and TD count straight pieces and a curve adds pieces (nuance 19).

![Closeness ladder, Copenhagen](atlas/a02_ladder_closeness_copenhagen_c10dp_800.png)
![Closeness ladder, Mumbai](atlas/a02_ladder_closeness_mumbai_island_c10dp_800.png)
![Where each closeness step reorders streets, Copenhagen](atlas/a04_steps_closeness_copenhagen_c10dp_800.png)
![Where each closeness step reorders streets, Mumbai](atlas/a04_steps_closeness_mumbai_island_c10dp_800.png)
![Betweenness ladder, Copenhagen](atlas/a03_ladder_betweenness_copenhagen_c10dp_800.png)
![Betweenness ladder, Mumbai](atlas/a03_ladder_betweenness_mumbai_island_c10dp_800.png)

The divergence maps show *where* a step reorders streets: red where a street ranks higher after
the step, blue where lower, thin grey where the two agree within 10 percentile points. The
end-to-end panel is the one to read first: NAIN promotes long, continuous streets with many
segments in their catchment; metric closeness promotes compact, central junction clusters.

Radius series (local to city-wide structure):

![NAIN by radius, Copenhagen](atlas/a06_radii_nain_copenhagen_c10dp.png)
![NAIN by radius, Mumbai](atlas/a06_radii_nain_mumbai_island_c10dp.png)
![NACH by radius, Copenhagen](atlas/a07_radii_nach_copenhagen_c10dp.png)
![NACH by radius, Mumbai](atlas/a07_radii_nach_mumbai_island_c10dp.png)

---

## 6. Results: work packages

### 6.1 WP1: places differ more than cities

Agreement recomputed inside 1 km tiles (≥ 50 interior streets, ≥ 25% land), cleaned networks, R800:

| Step | City | Tiles | ρ p10 | median | p90 | corr. with tile density |
|---|---|---|---|---|---|---|
| metric → angular | Copenhagen | 98 | 0.58 | 0.78 | 0.89 | −0.16 |
| | Mumbai | 66 | 0.62 | 0.80 | 0.91 | −0.02 |
| \(NC^2/TD\) → NAIN | Copenhagen | 98 | 0.51 | 0.80 | 0.90 | 0.36 |
| | Mumbai | 66 | 0.40 | 0.81 | 0.90 | 0.12 |
| closeness end to end | Copenhagen | 98 | 0.00 | 0.30 | 0.52 | 0.24 |
| | Mumbai | 66 | −0.12 | 0.26 | 0.48 | 0.18 |
| betweenness end to end | Copenhagen | 98 | 0.59 | 0.71 | 0.79 | 0.12 |
| | Mumbai | 66 | 0.47 | 0.67 | 0.79 | 0.35 |

- **The city medians differ by 0.01–0.04; the within-city spread (p10–p90) is 0.20–0.60.** The
  contrast between neighbourhoods is an order of magnitude larger than between the cities.
- **Mumbai has the longer low tail** for NAIN (p10 0.40 vs 0.51), end-to-end closeness
  (−0.12 vs 0.00) and betweenness (0.47 vs 0.59): some of its neighbourhoods are where the two
  approaches disagree most.
- **Network density explains little** (|r| < 0.3 for 6 of 8). The exceptions are NAIN in
  Copenhagen (0.36) and betweenness in Mumbai (0.35).
- Inside a tile, \(NC^2/TD\) and NAIN agree at a median 0.80; city-wide at R800 the figure is
  0.59–0.64. Part of NAIN's effect is a re-ranking **between** neighbourhoods (damping the reward
  for dense areas), not within them.

![Tile agreement, Copenhagen](atlas/a12_tiles_copenhagen_c10dp.png)
![Tile agreement, Mumbai](atlas/a12_tiles_mumbai_island_c10dp.png)

### 6.2 Three neighbourhoods side by side

Indre By (Copenhagen's medieval core), Colaba (southern Mumbai, colonial-era grid and
waterfront) and Dharavi (dense, partly informal, central Mumbai) are compared at the same scale,
3 × 3 km each, with the same measures; classes are quintiles within each window.

![Indre By, Colaba and Dharavi compared](atlas/a13_windows.png)

Per-window numbers (streets per km², network km per km², median street length, and the rank
agreement between NAIN and metric closeness inside each window) are written to
`windows.csv` by the atlas script. Each window also has its own six-measure zoom:

![Zoom: Indre By](atlas/a10_zoom_indre_by_copenhagen_c10dp.png)
![Zoom: Colaba](atlas/a10_zoom_colaba_mumbai_island_c10dp.png)
![Zoom: Dharavi](atlas/a10_zoom_dharavi_mumbai_island_c10dp.png)

Two cautions apply to Dharavi. Its mapped network is the formal skeleton only, so its measures
describe the streets a visitor would find on a map, not the lanes residents use; and WP3 shows
that its *global* values depend on how the map around it is drawn.

### 6.3 WP2 and WP2b: network cleaning is a design choice

**The network itself changes.** Junction consolidation from 0 to 20 m changes Copenhagen's
interior street count 4.2× (64,625 → 15,238) and Mumbai's 2.4×; the median street length goes
from 27 to 130 m in Copenhagen. Network length per km² barely moves.

**Agreement changes.** On raw topology cityseer and depthmapX agree at ρ 0.90–0.99 for
closeness; after 10 m consolidation, 0.67–0.90. Across both families and both cities, 20 m
consolidation leaves engine agreement at 0.54–0.92. NAIN's reordering and
the near-zero end-to-end closeness agreement at 400 m survive every setting.

**Mechanism (WP2b).** OSMnx consolidation keeps each street's line and appends a straight
**stub** from its old end point to the merged junction. The engines read stubs differently:

| Synthetic dual carriageway | cityseer: angular farness | depthmapX-style: pieces / total depth |
|---|---|---|
| raw | 13.0 | 7 / 7.0 |
| consolidated 10 m | 17.0 | 12 / 12.0 |
| consolidated, stubs removed | 9.0 | 6 / 4.0 |

cityseer joins streets only at their end points, so routes pass along the stubs and angular cost
rises; depthmapX joins pieces wherever end points coincide, so cost is unchanged but each stub is
an extra piece in NC. On the real networks one street end in four or five carries a stub at
10 m (19.7% Copenhagen, 25.1% Mumbai). **Destubbing recovers about half of the lost engine
agreement.** The remainder follows one curve: **engine agreement falls as the median segment
length grows relative to the radius** (rank correlation −0.96 over 20 runs, both cities; about
0.95 at a ratio of 0.03, 0.90 at 0.08, 0.80 at 0.18). Merging duplicated carriageways does not
change it.

![Consolidation sensitivity](results/phase1/figures/fig6_consolidation_800.png)
![Engine agreement against segment length ÷ radius](results/phase1/figures/fig7_engine_scale.png)

The same windows, raw vs cleaned:

![Cleaning: Indre By](atlas/a11_cleaning_indre_by.png)
![Cleaning: Colaba](atlas/a11_cleaning_colaba.png)
![Cleaning: Dharavi](atlas/a11_cleaning_dharavi.png)

### 6.4 WP3: where the map stops

Dharavi's 278 streets were analysed inside maps of growing extent, all subsets of one cleaned
network (Greater Mumbai + 2 km, 36,714 streets), and compared with the metropolitan map:

| Map | Streets | NAIN R400 / R800 / R2000 | NAIN Rn | NACH Rn |
|---|---|---|---|---|
| Dharavi, clipped at its boundary | 278 | 0.92 / 0.79 / 0.57 | **0.53** | 0.68 |
| Dharavi + 500 m | 692 | 1.00 / 1.00 / 0.94 | 0.86 | 0.91 |
| Dharavi + 1 km | 1,372 | 1.00 / 1.00 / 1.00 | **0.96** | 0.98 |
| Dharavi + 2 km | 3,116 | 1.00 / 1.00 / 1.00 | 0.97 | 0.99 |
| Dharavi + 4 km | 7,478 | 1.00 / 1.00 / 1.00 | 0.99 | 0.99 |
| G/North ward + 2 km | 5,685 | 1.00 / 1.00 / 1.00 | 0.95 | 0.99 |
| Island city + 2 km | 12,119 | 1.00 / 1.00 / 1.00 | **0.83** | 0.98 |

- **Radius-bounded measures are exact once the surround reaches the radius.** The 2 km buffer
  used throughout is sufficient for R ≤ 2000 m.
- **Global integration converges quickly with a centred surround** (1 km: 0.96).
- **Position matters more than size**: the island city map is four times larger than Dharavi + 2 km
  but places Dharavi near its northern edge, and reaches only 0.83.

![Nested extents](results/phase1/figures/fig8_nested.png)

### 6.5 WP4: the axial step

**Generated maps.**

| | Lines | Median line | Mean connectivity | Intelligibility r (interior) | Synergy r (interior) |
|---|---|---|---|---|---|
| Copenhagen, cleaned / raw | 38,831 / 54,220 | 54 / 40 m | 4.6 / 3.6 | 0.12 / 0.10 | 0.23 / 0.28 |
| Mumbai island, cleaned / raw | 10,087 / 13,322 | 79 / 63 m | 4.3 / 3.6 | 0.02 / 0.15 | 0.15 / 0.33 |
| Copenhagen, tolerance 4 / 16 m | 51,183 / 29,138 | 40 / 72 m | 4.1 / 5.4 | 0.12 / 0.13 | 0.22 / 0.24 |
| *Barnsbury, hand-drawn* | *1,092* | *178 m* | *4.0* | *0.54* | *0.72* |

![Generated axial lines, Copenhagen](atlas/a08_axial_copenhagen_c10dp.png)
![Generated axial lines, Mumbai](atlas/a08_axial_mumbai_island_c10dp.png)

**Validation against a hand-drawn map.** On Barnsbury, the generator recovers the hand-drawn map
almost exactly when fed the hand-drawn lines split into pieces (ρ 0.95–0.99 per measure; the
only systematic error is a few extra connections from the line extension). Fed real OSM
centrelines, it does not:

| OSM input | km per km² (reference 14.3) | Reference within 15 / 50 m of a street | Lines (tol 8 m) | Intelligibility r (tol 8 m) | Best ρ with reference, any tolerance |
|---|---|---|---|---|---|
| walk network | 24.2 | 0.56 / 0.95 | 5,460 | 0.20 | 0.26 |
| streets only | 13.0 | 0.39 / 0.84 | 1,782 | 0.27 | 0.28 |

- No coordinate offset (a shift scan finds the best fit at 0, −1 m).
- Hand-drawn lines run 10–30 m off street centrelines: they cut corners, cross squares, and a
  third of them follow open space that is not a street. The walk network adds 70% more length
  (footways, estate paths, service roads) than the hand-drawn map holds.
- **Rank agreement stays at ρ 0.04–0.28 for every measure, OSM input, tolerance and matching
  radius.** Even where generated and hand-drawn lines coincide, they carry different values,
  because axial values depend on the topology of the whole map.

![Hand-drawn vs generated axial maps, Barnsbury](atlas/b01_barnsbury_axial.png)
![Coverage of the hand-drawn map](atlas/b02_barnsbury_coverage.png)

**S4 against the angular ladder** (interior streets, cleaned; raw in brackets):

| | Radius | Axial HH Rn vs NAIN | Axial HH R3 vs NAIN | Axial HH Rn vs metric harmonic | Axial choice Rn vs NACH |
|---|---|---|---|---|---|
| Copenhagen | 800 | 0.22 (0.26) | 0.58 (0.59) | 0.40 (0.31) | 0.70 (0.78) |
| | 2000 | 0.40 (0.45) | 0.45 (0.45) | 0.68 (0.58) | 0.73 (0.80) |
| Mumbai | 800 | 0.32 (0.33) | 0.58 (0.64) | 0.00 (0.05) | 0.63 (0.72) |
| | 2000 | 0.30 (0.44) | 0.55 (0.61) | 0.13 (0.17) | 0.70 (0.78) |

- **Axial choice is the bridge** between representations: ρ 0.6–0.8 with angular NACH at every
  radius, in both cities.
- **Axial global integration is not**: ρ 0.1–0.45 with NAIN.
- **City contrast**: global axial integration tracks metric closeness at 2 km in Copenhagen
  (0.68) but not in Mumbai (0.13). The island city is a long peninsula, so global depth is set
  by position along it, the same effect as in WP3.
- **Intelligibility is near zero in both cities**, and cleaning moves it more than the city does
  (Mumbai interior 0.02 cleaned, 0.15 raw). Intelligibility is known to fall with map size, so
  these values are not comparable with published values for small hand-drawn maps.
- **Tolerance moves the map, not the ranking**: 4 → 16 m changes the line count by 43% and every
  ladder ρ by ≤ 0.05.
- depthmapX silently keeps one copy of coincident duplicate lines; a tool that counts both
  reports extra connections (6–13% of lines on cleaned networks). The generator now merges them.

![S4 vs angular, Copenhagen](atlas/a09_axial_vs_angular_copenhagen_c10dp.png)
![S4 vs angular, Mumbai](atlas/a09_axial_vs_angular_mumbai_island_c10dp.png)

---

## 7. Implications

### 7.1 For Space Syntax practice

- **NAIN is a modelling decision, not a neutral rescaling.** It is the largest single reordering
  between SS and network closeness. Results that depend on integration should say whether they
  would hold under \(NC^2/TD\) or harmonic closeness.
- **Choice/NACH is the robust family.** If a finding must survive a change of representation,
  engine or cleaning, base it on choice.
- **Report engine conventions.** Tulip bin count, tie-breaking and per-direction choice counting
  change catchments and totals (nuances 7–12); they are invisible in the GUI.
- **Generated axial maps are their own representation.** Automatic axial lines from OSM do not
  stand in for hand-drawn analysis; values and intelligibility differ fundamentally.
- **Global measures need a centred surround** of about 1 km beyond the study area; a larger
  map that puts the area near its edge is worse than a smaller centred one.

### 7.2 For network analysis practice

- **Cleaning parameters are results-relevant.** Consolidation tolerance and stub handling move
  engine agreement as much as the choice between metric and angular cost. Destub after
  consolidation, and report tolerance, stub handling and median segment length with every result.
- **Compare cities by network length per km²**, not segment counts.
- **Report the radius set** with cityseer results: its angular results at one radius depend on
  the other radii requested in the same call (nuance 21).

### 7.3 For comparing cities

- City-level averages hide most of the variation. In both cities, which neighbourhood one looks
  at matters an order of magnitude more than which city. Comparative claims should be made at
  matched neighbourhood scale (Section 6.2) or with the full within-city distribution.

### 7.4 For informal settlements

- OSM's omission of informal lanes is not a small error: in Mumbai the mapped network is 1.6×
  sparser than Copenhagen's despite far denser fabric. Every SS or network measure in such areas
  describes the formal skeleton. Measuring the informal-lane delta (Project 2) is a prerequisite
  for using either approach there.
- Because global measures depend on extent and position (WP3), analyses of a settlement on its
  own (clipped at its boundary) are unreliable (ρ 0.53 for global NAIN).

### 7.5 For exposure and health studies

Pedestrian-weighted exposure needs a movement proxy. The robust candidate from this work is
choice at walking-to-city radii (NACH, or betweenness on the segment graph), which agrees across
representations, engines and cleaning. Integration-based proxies inherit the normalisation and
cleaning sensitivities above.

---

## 8. Reporting checklist

For any SS or network-centrality result on street networks, report:

1. Data source and date; walk/drive filter.
2. Junction consolidation tolerance; stub handling; parallel-street handling; median segment length.
3. Representation (junction graph, segment graph, straight pieces, axial; how axial lines were made).
4. Cost (metric, angular with bin count, topological) and radius definition (along which route).
5. Measure and normalisation (harmonic, \(NC^2/TD\), NAIN, NACH, HH; constants).
6. Engine and version; tie-breaking and choice-counting conventions.
7. Study area, buffer width and how the map boundary was chosen; position of the study area in the map.
8. Radius set, especially with cityseer.
9. How values were transferred to streets (mean of junctions, length-weighted mean of pieces).
10. Ranks or raw values; within-city spread if comparing cities.

---

## 9. Limits

- **No movement data.** This work compares methods; it does not say which predicts movement
  better. WP5 (Copenhagen counts) and Project 2 (Dharavi gate counts) address this.
- **OSM coverage.** Mumbai results describe the mapped formal network only.
- **One cleaning pipeline** (OSMnx) and **one SS engine** (depthmapX); cityseer is the only
  network engine.
- **S4 is a generated line map**, not a fewest-line or hand-drawn axial map; the hand-drawn
  comparison uses one London map.
- **Within-tile ρ** rests on 50 to a few hundred streets; read the distribution, not single tiles.
- **Duplicate streets** remain in the cleaned networks for S0–S3 (≈ 0.7% of Mumbai's lines);
  depthmapX drops them, cityseer keeps them.

---

## 10. What comes next

- **WP5**: Copenhagen pedestrian and cycle counts against each rung (descriptive).
- **Project 2, the invisible network**: Dharavi lanes digitised under a written protocol;
  informal-lane inclusion delta for every measure; a hand-drawn axial sample tile; visibility
  graph analysis on open space; gate counts.
- **Project 3, pedestrian-weighted exposure**: movement potential from the robust measures,
  combined with heat, green and air-quality layers, to rank where interventions reach most
  pedestrians.

---

## References

- Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing
  complex street networks. *Computers, Environment and Urban Systems*, 65, 126–139.
- Crucitti, P., Latora, V. & Porta, S. (2006). Centrality measures in spatial networks of urban
  streets. *Physical Review E*, 73, 036125.
- Freeman, L. C. (1977). A set of measures of centrality based on betweenness. *Sociometry*,
  40(1), 35–41.
- Hillier, B. (1996). *Space is the Machine*. Cambridge University Press.
- Hillier, B. & Hanson, J. (1984). *The Social Logic of Space*. Cambridge University Press.
- Hillier, B. & Iida, S. (2005). Network and psychological effects in urban movement. In
  *Spatial Information Theory (COSIT 2005)*, LNCS 3693, 475–490. Springer.
- Hillier, B., Yang, T. & Turner, A. (2012). Normalising least angle choice in Depthmap and how it
  opens up new perspectives on the global and local analysis of city space. *Journal of Space
  Syntax*, 3(2), 155–193.
- Liu, X. & Jiang, B. (2012). Defining and generating axial lines from street center lines for
  better understanding of urban morphologies. *International Journal of Geographical Information
  Science*, 26(8), 1521–1532.
- Porta, S., Crucitti, P. & Latora, V. (2006). The network analysis of urban streets: a dual
  approach. *Physica A*, 369(2), 853–866.
- Ratti, C. (2004). Space syntax: some inconsistencies. *Environment and Planning B*, 31(4), 487–499.
- Simons, G. (2023). The cityseer Python package for pedestrian-scale network-based urban
  analysis. *Environment and Planning B: Urban Analytics and City Science*, 50(5), 1328–1344.
- Teklenburg, J. A. F., Timmermans, H. J. P. & van Wagenberg, A. F. (1993). Space syntax:
  standardised integration measures and some simulations. *Environment and Planning B*, 20(3),
  347–357.
- Turner, A. (2007). From axial to road-centre lines: a new representation for space syntax and a
  new model of route choice for transport network analysis. *Environment and Planning B*, 34(3),
  539–555.
- depthmapX (SpaceGroupUCL), open-source spatial network analysis software,
  <https://github.com/SpaceGroupUCL/depthmapX>.
- OpenStreetMap contributors. Street data under the Open Database Licence (ODbL).

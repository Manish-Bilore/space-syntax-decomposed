---
title: Glossary
---

Short definitions for quick lookup. Full definitions with formulas are in
[the report, Definitions](report.qmd#definitions).

| Term | Meaning |
|---|---|
| **Angular distance** | Sum of turn angles along a route, in units of 90°. Going straight costs 0, a right-angle turn 1. |
| **Axial line / axial map** | One of the fewest, longest straight lines covering all open space; the classic SS representation. Lines are nodes; intersections are links. |
| **Betweenness** | Number of shortest routes between other pairs of nodes that pass through a node (Freeman 1977). Called *choice* in SS. |
| **Buffer** | Streets around the study area (2 km here) included so interior streets see a full catchment; never reported. |
| **Catchment** | All nodes within the radius of a node. |
| **Choice** | SS betweenness on least-angle (segment) or fewest-step (axial) routes. |
| **cityseer** | Python package for network centrality on street graphs (Simons 2023); used for S0–S2. |
| **Closeness** | How near a node is to all others within the radius; here harmonic (sum of 1/d) or Hillier (NC²/TD). |
| **Connectivity** | Number of lines an axial line intersects. |
| **Consolidation** | Merging junction nodes within a tolerance into one (OSMnx). |
| **Consolidation stub** | Short straight piece OSMnx appends from a street's old end to a merged junction. |
| **Control / controllability** | Local axial measures: share of neighbours' attention a line receives; connectivity relative to lines within two steps. |
| **D-value** | Relative asymmetry of a diamond-shaped graph of k nodes; normalises RA across map sizes. |
| **depthmapX** | Open-source SS software (UCL); the reference engine here (S3, S4). |
| **Destubbing** | Removing consolidation stubs so streets run straight to the merged junction. |
| **Dual (segment) graph** | Streets are nodes; streets sharing a junction are linked. |
| **Generated axial map** | Axial lines produced from street centrelines (natural streets, straightened, extended); S4 here. A line map rather than a fewest-line map. |
| **Integration (HH)** | Axial closeness: D-value / RA. Higher = fewer line changes to everywhere. |
| **Integration (angular)** | NC² / TD on the angular segment map (depthmapX ≥ 10). |
| **Intelligibility** | Correlation between connectivity and global integration: how well local cues predict global position. |
| **Interior** | Streets whose midpoint lies inside the study boundary; the only ones reported. |
| **Ladder** | Sequence of representations S0–S4 where adjacent rungs differ by one design choice. |
| **Least-angle route** | Route minimising total turning, the SS model of route choice. |
| **NACH** | Normalised angular choice: log(CH + 1) / log(TD + 3) (Hillier, Yang & Turner 2012). |
| **NAIN** | Normalised angular integration: NC^1.2 / (TD + 2). |
| **Natural street (stroke)** | Chain of segments continuing each other through junctions with small deflection. |
| **Node count (NC)** | Number of nodes in the catchment. |
| **Percentile-rank difference** | Map statistic: a street's percentile rank under one measure minus under another. |
| **Primal (junction) graph** | Junctions are nodes; streets are links weighted by length. |
| **RA / RRA** | Relative asymmetry 2(MD − 1)/(k − 2), and RA divided by the D-value. |
| **Radius (R400, Rn …)** | Limit of the catchment: metres for metric/angular analysis, steps for axial; n = no limit. |
| **Spearman ρ** | Rank correlation: do two measures order streets the same way (1 = identical order, 0 = unrelated). |
| **Synergy** | Correlation between local (R3) and global (Rn) axial integration. |
| **Total depth (TD)** | Sum of distances from a node to all nodes in its catchment. |
| **Tulip binning** | depthmapX's quantisation of turn angles (1024 bins per circle). |
| **Top-10% overlap** | Share of the top decile under one measure that is also top decile under the other. |

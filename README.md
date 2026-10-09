# Space Syntax, decomposed

[![site](https://github.com/Manish-Bilore/space-syntax-decomposed/actions/workflows/docs.yml/badge.svg)](https://manish-bilore.github.io/space-syntax-decomposed/)
[![tests](https://github.com/Manish-Bilore/space-syntax-decomposed/actions/workflows/tests.yml/badge.svg)](https://github.com/Manish-Bilore/space-syntax-decomposed/actions/workflows/tests.yml)

**Which design choices make Space Syntax differ from street-network analysis, by how much, and
where?** A from-scratch Python reimplementation of Space Syntax measures, matched to depthmapX,
and a ladder of single changes from metric centrality to NAIN / NACH, tested on Copenhagen +
Frederiksberg and the Mumbai island city.

**Project site, report, interactive dashboard and map atlas: <https://manish-bilore.github.io/space-syntax-decomposed/>**

The aim is not to show one approach is better, but to find out which design choice —
representation, cost, closeness formula, normalisation, engine, network cleaning, map extent,
axial line construction — makes the results differ, and whether that differs between a Nordic
and an Indian city.

Key findings: at walking radii metric closeness and NAIN are nearly unrelated (ρ ≈ 0 at 400 m)
with the normalisation as the largest single step; choice/betweenness is robust across
representations; network cleaning matters as much as angular cost; global measures depend on
where the map stops; generated axial maps do not reproduce hand-drawn ones; neighbourhoods
differ an order of magnitude more than the two cities.

## What is here

| Path | Content |
|---|---|
| `src/ssx/syntax/reimpl/topological.py` | Axial/convex measures: TD, MD, RA, RRA (D-value), Integration HH / P-value / Tekl, control, controllability, choice (split ties, or depthmapX random ties), local radii |
| `src/ssx/syntax/reimpl/angular.py` | Angular segment analysis: directed least-angle search, tulip binning, metric radius, NC²/TD, NAIN, NACH, choice (clean rule or depthmapX rule) |
| `src/ssx/syntax/reimpl/derived.py` | Intelligibility, synergy |
| `src/ssx/syntax/reference/` | depthmapX CLI wrapper; cityseer adapter |
| `src/ssx/network/build.py` | OSM walk network to cleaned segments, interior mask, straight-piece explosion |
| `src/ssx/compare/agreement.py` | Spearman / top-10% overlap tables |
| `scripts/00_fidelity.py` | Reimplementation vs depthmapX on one map to `reports/fidelity_<name>.md` |
| `scripts/01_fetch_network.py` | OSM network for a site |
| `scripts/02_ladder.py` | S0–S3 ladder and per-step agreement (`--s3-geometry chord` control) |
| `scripts/03_figures.py` | Phase 0 figures: ladder chart, NACH / NAIN maps, divergence map |
| `scripts/04_tiles.py` | Phase 1: per-tile agreement vs network density, catchment size |
| `scripts/05_sensitivity.py` | Phase 1: ladder agreement across consolidation levels |
| `scripts/06_stub_diag.py` | Phase 1: counts consolidation stubs in existing networks |
| `scripts/07_engine_scale.py` | Phase 1: engine agreement against segment length ÷ radius |
| `scripts/08_nested.py` | Phase 1: nested extents, boundary sensitivity of local and global measures |
| `scripts/09_axial.py` | Phase 1: S4 rung, axial map generated from centrelines, intelligibility, synergy, agreement with the ladder |
| `scripts/11_axial_diag.py` | Phase 1: coverage (offset, distance, content) and connection diagnostics for WP4 |
| `scripts/10_axial_validate.py` | Phase 1: generated vs hand-drawn reference axial map (Barnsbury), tolerance sweep |
| `scripts/12_atlas.py` | Map atlas of every spatial output (north arrow, scale; Indre By, Colaba, Dharavi windows) to `reports/atlas/` |
| `scripts/13_build_site.py` | Assembles the Quarto website in `docs/` (maps, dashboard data, reports); `quarto preview docs` |
| `scripts/14_export_web.py` | Compact percentile data for the interactive dashboard (`docs/dashboard/`) |
| `docs/` | Website source: report, glossary, nuance catalogue, atlas, work-package reports |
| `reports/phase0/README.md` | Phase 0 write-up (figures in `reports/phase0/figures/`) |
| `tests/` | Hand-derived toy layouts (`fixtures.py` shows the working) + depthmapX parity |
| `docs/nuances.md` | What was learned: conventions inside depthmapX that change results |
| `PHASES.md` | Plan: Phase 0 (application) to P1 to P2 informal network to P3 PWE pilot |

## The ladder

One design choice changes per step, so each drop in agreement can be attributed.

| Rung | Representation | Cost | Measure | Engine |
|---|---|---|---|---|
| S0 | Primal (junctions) | Metric | harmonic closeness, betweenness | cityseer |
| S1 | Segment (dual) | Metric | harmonic, NC²/TD, betweenness | cityseer |
| S2 | Segment | Angular | NC²/TD, betweenness | cityseer |
| S3 | Straight segments | Angular, tulip-1024 | NC²/TD to NAIN, choice to NACH | depthmapX or `reimpl` |
| S4 | Axial lines generated from centrelines | Topological | Integration HH, choice, intelligibility, synergy | depthmapX / `reimpl` |
| S5 | VGA (Phase 2) | Visibility | visual integration | — |

## Fidelity (Barnsbury, London — depthmapX's own test data)

Fed the same connection lists as depthmapX:

- **Axial, 1,100 lines:** every depth and integration measure matches to ~1e-7. Choice totals are
  identical; allocation differs only where routes tie, because depthmapX breaks ties at random.
- **Segment, 5,459 segments, R400 / R800 / R1200 / Rn:** node count, total depth and integration
  match for every segment (≥ 99.98%). Choice matches for 99.1–100% of segments once depthmapX's
  per-direction counting rule is reproduced; relative to one count per destination that rule
  shifts totals by −7% to +11% depending on radius, while leaving ranks intact (ρ > 0.999).

Full tables: `reports/fidelity_barnsbury.md`. Explanations: `docs/nuances.md`.

## Quick start

```bash
pip install -e .            # or: pip install -r requirements.txt
pytest -q                   # 31 tests; +2 depthmapX parity tests when $DEPTHMAPX is set

# reference engine (see docs/depthmapx_build.md)
export DEPTHMAPX=/path/to/depthmapXcli

python scripts/00_fidelity.py --lines /path/to/depthmapX/testdata/barnsbury_extended1_axial.csv --name barnsbury
python scripts/01_fetch_network.py --site copenhagen
python scripts/02_ladder.py --site copenhagen --radii 400 800 1200 2000
```

## Conventions

- Choice is reported as ordered-pair counts (both directions), as in depthmapX.
- Angular cost: 90° = 1. Integration = NC²/TD. NAIN = NC^1.2/(TD+2), NACH = log(CH+1)/log(TD+3)
  (Hillier, Yang & Turner 2012).
- Undefined values (e.g. RA = 0) are NaN, where depthmapX writes −1.
- Cross-city comparisons use ranks and radius-bounded measures only; global measures depend on
  system size and are compared within a city.

## Licence and credits

Measure definitions follow depthmapX (GPL-3.0, Space Syntax Laboratory, UCL) and the papers
cited in `docs/nuances.md`; no depthmapX code is included. cityseer (Simons) is used as a
second reference engine.

Code MIT (see `LICENSE`); text and figures CC BY 4.0. Street data © OpenStreetMap contributors
(ODbL); derived networks are not committed and are rebuilt by the scripts. The Barnsbury
reference map is depthmapX test data and is not redistributed. Cite via `CITATION.cff`.

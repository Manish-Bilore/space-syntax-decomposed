# Phases

Programme: learn Space Syntax (SS) from the inside, compare it step by step with an assembled
network workflow, then extend it to informal fabric and pedestrian-weighted exposure (PWE).

| Project | Content | Outlet |
|---|---|---|
| **P1 Space Syntax decomposed** | Reimplementation + fidelity; S0–S4 ladder; Copenhagen vs Mumbai island city | Local conference to SSS / J. Space Syntax |
| **P2 The invisible network** | Dharavi digitised; informal-lane inclusion delta; VGA; gate counts | Journal (EPB / CEUS / JOSS for the code) |
| **P3 Naive PWE pilot** | Movement potential × heat / green / noise / PM; intervention ranking | Bridge to the PhD; later paper |

---

## Phase 0 — application-critical (6–8 Oct 2026; Chalmers deadline 9 Oct)

**Done in this session**
- [x] `syntax/reimpl/topological.py`: TD, MD, RA, RRA (D-value), Integration HH / P-value / Tekl,
      connectivity, control, controllability, choice (split ties and depthmapX random ties), local radii.
- [x] `syntax/reimpl/angular.py`: directed least-angle search, tulip binning, metric radius along the
      least-angle route, integration NC²/TD, NAIN, NACH, choice (clean rule and depthmapX rule).
- [x] 23 tests on hand-derived toy layouts (chain, star, ring with tied paths, L-bend, T-junction radius).
- [x] depthmapX CLI built without Qt; wrapper `syntax/reference/depthmapx.py`.
- [x] Fidelity check on Barnsbury, London (depthmapX test data, 1,100 axial lines / 5,459 segments):
      see `reports/fidelity_barnsbury.md`.
- [x] cityseer adapter; S0–S3 ladder script; smoke-tested end to end on Barnsbury.

**Your steps (local machine, OSM is reachable there)**
1. Build depthmapXcli (`docs/depthmapx_build.md`), `export DEPTHMAPX=...`. ~10 min.
2. `python scripts/01_fetch_network.py --site copenhagen` and `--site mumbai_island`. Note the
   printed summary (segments, density, median length); this is the scale comparison.
3. `python scripts/02_ladder.py --site copenhagen` and `--site mumbai_island`
   (radii 400 800 1200 2000). Produces `ladder.gpkg` and `agreement.csv` per city.
4. Two figures per city in QGIS from `ladder.gpkg`: NACH 800 and NAIN 800 (interior only),
   plus one table: the agreement steps side by side for both cities.
5. Portfolio page: question to method (ladder) to fidelity result to the two-city table to what P2/P3
   add. Link it in the CV and letter.
6. Personal letter. Submit by **8 Oct**.

Cut if short of time: step 4's Mumbai maps (keep the table). Do **not** cut the fidelity result —
it is the direct evidence for "strong knowledge of Space Syntax".

---

## Phase 0 — status (7 Oct 2026): done

Copenhagen + Mumbai island city ladders, chord control, cityseer radius-set check.
Write-up `reports/phase0/README.md`; tables `reports/results_phase0.md`; figures from
`scripts/03_figures.py`.

## Phase 1 — P1 complete (Oct–Dec 2026)

| WP | Content | Status |
|---|---|---|
| 1 | **Equal-area tiles + catchment size** (`04_tiles.py`): per-tile ρ for key steps vs segment density, 1 km and 2 km tiles; NC beside every measure | **done**: `reports/phase1/wp1_tiles.md` (rerun on the clean network after WP2b) |
| 2 | **Cleaning sensitivity**: consolidation 0 / 10 / 20 m (`01_fetch_network.py --consolidate X --name site_cX`), rerun ladder, compare agreement tables | **done**: `reports/phase1/wp2_cleaning_sensitivity.md` |
| 2b | **Why consolidation splits the engines**: **done**: stubs explain about half the gap; the rest follows segment length ÷ radius; duplicated carriageways ruled out. Betweenness residual in Copenhagen still open | `reports/phase1/wp2b_consolidation_stubs.md` |
| — | **Baselines settled**: raw (0 m) and cleaned (10 m, `--destub --merge-parallel`) for both cities | done |
| 3 | **Nested extents (Mumbai)**: Dharavi to G/North ward to island city to Greater Mumbai via `--boundary` / `--osmid`; rank stability of NAIN/NACH across extents | **done**: local measures exact once surround ≥ radius; global NAIN converges with a centred surround (1 km: ρ 0.96, 4 km: 0.99 vs Greater Mumbai) while the larger off-centre island city gets 0.83 (`reports/phase1/wp3_nested_extents.md`) |
| 4 | **S4 axial**: axial maps generated from centrelines (`syntax/axial_gen.py`), `09_axial.py` per city, `10_axial_validate.py` / `11_axial_diag.py` against the Barnsbury reference | **city runs done**; generated maps do not reproduce hand-drawn axial values (ρ ≤ 0.28), relate to angular NACH (ρ 0.6–0.8); intelligibility 0.02–0.15 both cities. Connection mismatch traced to duplicate streets (resolved). **WP4 done** (`reports/phase1/wp4_axial.md`) |
| 5 | **Movement reference (Copenhagen)**: municipal pedestrian/cycle counts, if available, against each rung (descriptive) | find data |
| 6 | Conference abstract | after WP1–3 |

## Documentation (9 Oct 2026)

- Report `docs/report.qmd`; map atlas `scripts/12_atlas.py` (north arrow, scale, Indre By / Colaba / Dharavi windows); Quarto website with interactive dashboard (`scripts/13_build_site.py`, `14_export_web.py`), published from GitHub (`Manish-Bilore/space-syntax-decomposed`).

## Phase 2 — P2 the invisible network (Dec 2026–Mar 2027)

- Digitisation protocol (centreline and axial rules) written before digitising.
- Dharavi lanes digitised from VHR imagery (check licence); formality classes rather than 0/1.
- Informal-lane inclusion delta: every measure with / without lanes, mapped on formal segments.
- VGA (S5) on open space from building footprints in the settlement.
- Gate counts in Dharavi (empirical movement reference; standard SS observation method).

## Phase 3 — P3 naive PWE pilot (Mar–May 2027)

- Movement potential from P1 (NACH / NAIN at walking radii, plus density and attraction).
- Copenhagen: canopy / NDVI, LST, EU noise; Mumbai: LST, NDVI, PM.
- Walking-type hypotheses (transport ↔ choice at large radii; leisure ↔ green access + integration;
  sojourning ↔ local integration + attraction), stated as hypotheses for empirical testing.
- Top-N segments where greening / shading reaches the most pedestrians.

## Phase 4 — papers

1. Conference paper: P1 ladder + fidelity, Copenhagen vs Mumbai island.
2. Journal paper: P1 + P2 (informal-lane delta, nested extents, VGA, gate counts).
3. JOSS (optional): the reimplementation, if it adds tested fidelity + Python VGA beyond cityseer.
4. arXiv preprint of each.

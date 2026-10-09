# Phase 1, WP1 — does divergence track network density?

Each city is cut into 1 km tiles. Within each tile, rank agreement (Spearman ρ) is recomputed
for four ladder steps at R800 m, and compared with the tile's segment density.
Networks: 10 m consolidation. Tiles need ≥ 50 interior segments and ≥ 25% land.
Run 7 Oct 2026. Figure: `figures/fig5_tiles_1000_800.png` (generated locally).

| Step | City | Tiles | ρ p10 | ρ median | ρ p90 | Rank corr. with density |
|---|---|---|---|---|---|---|
| Closeness: metric to angular | Copenhagen | 98 | 0.55 | 0.73 | 0.89 | −0.13 |
| | Mumbai | 68 | 0.48 | 0.79 | 0.92 | −0.02 |
| Closeness: NC²/TD to NAIN | Copenhagen | 98 | 0.59 | 0.81 | 0.91 | 0.39 |
| | Mumbai | 68 | 0.38 | 0.72 | 0.88 | 0.13 |
| Closeness end to end | Copenhagen | 98 | 0.02 | 0.31 | 0.53 | 0.18 |
| | Mumbai | 68 | −0.20 | 0.22 | 0.48 | 0.26 |
| Betweenness end to end | Copenhagen | 98 | 0.53 | 0.67 | 0.77 | 0.01 |
| | Mumbai | 68 | 0.30 | 0.57 | 0.74 | 0.26 |

## Findings

1. **Density explains little.** Seven of the eight correlations between tile density and
   agreement are below 0.3 in size. The exception is NAIN in Copenhagen (0.39): denser tiles
   show somewhat more agreement between NC²/TD and NAIN. The Phase 0 hypothesis that divergence
   follows how densely the network is mapped is not supported at this scale.
2. **Places differ more than cities do.** The spread across tiles within one city (p10 to p90)
   is 0.24–0.68 wide, against differences of 0.06–0.10 between the two city medians. "Mumbai
   vs Copenhagen" is a weaker contrast than "this neighbourhood vs that one".
3. **Mumbai has the longer low tail.** Its 10th-percentile tile is lower on all four steps
   (e.g. NAIN 0.38 vs 0.59; betweenness end to end 0.30 vs 0.53). Some parts of Mumbai are
   where the two approaches disagree most. Which parts, and what they have in common, is the
   next thing to look at on the tile map (`data/<site>/tiles_1000.gpkg`).
4. **Part of NAIN's reordering is between neighbourhoods, not within them.** Inside a tile,
   NC²/TD and NAIN agree at a median 0.81 (Copenhagen) and 0.72 (Mumbai); city-wide at 800 m the
   figures are 0.64 and 0.59. NAIN mostly re-ranks areas against each other by damping the
   effect of how many segments each area has, and re-ranks streets within an area less.

## Limits

- The first table was computed on the 10 m network with consolidation stubs; the rerun below uses
  the cleaned baseline and supersedes it.
- Within-tile ρ rests on 50 to a few hundred segments and a narrower range of values, so
  individual tiles are noisy; read the distribution, not single tiles.
- One tile size and one radius. 2 km tiles and R400 are the obvious checks.


## Rerun on the cleaned baseline (9 Oct 2026)

Networks: 10 m consolidation, destubbed, parallels merged (`*_c10dp`); 1 km tiles, R800.
Maps: `reports/atlas/a12_tiles_*`.

| Step | City | Tiles | ρ p10 | ρ median | ρ p90 | Rank corr. with density |
|---|---|---|---|---|---|---|
| Closeness: metric to angular | Copenhagen | 98 | 0.58 | 0.78 | 0.89 | −0.16 |
| | Mumbai | 66 | 0.62 | 0.80 | 0.91 | −0.02 |
| Closeness: NC²/TD to NAIN | Copenhagen | 98 | 0.51 | 0.80 | 0.90 | 0.36 |
| | Mumbai | 66 | 0.40 | 0.81 | 0.90 | 0.12 |
| Closeness end to end | Copenhagen | 98 | 0.00 | 0.30 | 0.52 | 0.24 |
| | Mumbai | 66 | −0.12 | 0.26 | 0.48 | 0.18 |
| Betweenness end to end | Copenhagen | 98 | 0.59 | 0.71 | 0.79 | 0.12 |
| | Mumbai | 66 | 0.47 | 0.67 | 0.79 | 0.35 |

The findings hold, and sharpen:

- **City medians are now almost identical** (differences 0.01–0.04), while the within-city spread
  (p10–p90) is 0.20–0.60 wide. The contrast between neighbourhoods is an order of magnitude
  larger than the contrast between cities.
- **Mumbai's low tail remains** for NAIN (p10 0.40 vs 0.51), end-to-end closeness (−0.12 vs 0.00)
  and betweenness (0.47 vs 0.59), but no longer for metric to angular.
- Density still explains little: |r| < 0.3 for 6 of 8; the exceptions are NAIN in Copenhagen
  (0.36) and betweenness in Mumbai (0.35).

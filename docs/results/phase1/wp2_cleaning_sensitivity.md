# Phase 1, WP2 — how much of the divergence is network cleaning?

Junction consolidation merges OSM nodes that lie within a tolerance of each other (dual
carriageways, separately mapped pavements, offset crossings). Phase 0 used 10 m. Here the full
ladder is rerun at 0 m (raw OSM topology) and 20 m. Everything else is unchanged.
Run 7 Oct 2026; radius set 400–2000 m; interior segments.

![Consolidation sensitivity](figures/fig6_consolidation_800.png)

## The network itself changes a lot

| | Copenhagen 0 m | 10 m | 20 m | Mumbai 0 m | 10 m | 20 m |
|---|---|---|---|---|---|---|
| Interior segments | 64,625 | 31,291 | 15,238 | 16,987 | 10,271 | 7,143 |
| Segments per km² | 626 | 303 | 148 | 239 | 144 | 100 |
| Median segment (m) | 27 | 62 | 130 | 43 | 73 | 116 |
| Network km per km² | 25.5 | 23.0 | 22.6 | 16.1 | 14.5 | 14.4 |
| Straight pieces per street | 2.1 | 3.5 | 4.3 | 2.3 | 3.5 | 4.2 |

- **Segment count is an unstable property of a city.** One cleaning parameter moves
  Copenhagen's segment density by 4.2× and Mumbai's by 2.4×.
- **The Copenhagen : Mumbai ratio of segment density runs from 2.6 (0 m) to 1.5 (20 m).** The
  Phase 0 statement "half the segment density" holds only at 10 m.
- **Network length per km² is stable:** Copenhagen has 1.57–1.58× Mumbai's at every setting.
  This is the figure to quote for the under-mapping argument.
- Copenhagen loses more segments to consolidation than Mumbai (÷4.2 vs ÷2.4), which fits its
  OSM data mapping pavements and cycle tracks as separate lines far more often.

## Agreement at each consolidation level

### Copenhagen + Frederiksberg — closeness

ρ at 400 / 800 / 1200 / 2000 m

| Step | 0 m | 10 m | 20 m |
|---|---|---|---|
| Junction to segment | .98 .98 .99 .99 | .91 .93 .95 .97 | .84 .90 .91 .92 |
| Harmonic to NC²/TD | .95 .93 .91 .91 | .98 .97 .97 .98 | .99 .98 .98 .99 |
| Metric to angular | .84 .77 .78 .84 | .75 .76 .78 .83 | .77 .83 .85 .89 |
| cityseer to depthmapX | .92 .94 .96 .99 | .79 .84 .86 .90 | .74 .85 .89 .92 |
| NC²/TD to NAIN | .51 .60 .64 .71 | .53 .64 .69 .74 | .55 .68 .71 .79 |
| End to end | −.04 −.02 .02 .17 | .07 .21 .29 .42 | .15 .37 .44 .56 |

### Copenhagen + Frederiksberg — betweenness

ρ at 400 / 800 / 1200 / 2000 m

| Step | 0 m | 10 m | 20 m |
|---|---|---|---|
| Junction to segment | .77 .76 .75 .73 | .63 .61 .60 .59 | .54 .43 .39 .36 |
| Metric to angular | .89 .86 .85 .86 | .79 .75 .74 .75 | .79 .72 .69 .70 |
| cityseer to depthmapX | .90 .93 .94 .94 | .69 .73 .73 .73 | .54 .66 .67 .68 |
| Choice to NACH | .86 .93 .95 .96 | .78 .89 .92 .93 | .78 .87 .90 .93 |
| End to end | .70 .76 .78 .79 | .57 .63 .64 .65 | .53 .56 .55 .54 |

### Mumbai City District — closeness

ρ at 400 / 800 / 1200 / 2000 m

| Step | 0 m | 10 m | 20 m |
|---|---|---|---|
| Junction to segment | .95 .97 .98 .98 | .88 .92 .94 .97 | .92 .96 .97 .98 |
| Harmonic to NC²/TD | .93 .92 .92 .89 | .98 .98 .98 .97 | .99 .99 .99 .99 |
| Metric to angular | .89 .86 .88 .89 | .84 .88 .89 .91 | .88 .90 .92 .94 |
| cityseer to depthmapX | .90 .93 .94 .95 | .67 .78 .82 .86 | .64 .78 .85 .90 |
| NC²/TD to NAIN | .51 .66 .72 .79 | .44 .59 .68 .76 | .47 .57 .67 .77 |
| End to end | .01 .16 .28 .35 | −.03 .20 .33 .47 | .04 .24 .40 .53 |

### Mumbai City District — betweenness

ρ at 400 / 800 / 1200 / 2000 m

| Step | 0 m | 10 m | 20 m |
|---|---|---|---|
| Junction to segment | .79 .79 .78 .77 | .69 .67 .65 .61 | .63 .59 .56 .51 |
| Metric to angular | .94 .89 .87 .86 | .81 .75 .72 .70 | .81 .73 .69 .69 |
| cityseer to depthmapX | .85 .90 .92 .95 | .62 .67 .66 .67 | .51 .61 .62 .61 |
| Choice to NACH | .77 .88 .93 .97 | .68 .82 .89 .94 | .66 .78 .86 .92 |
| End to end | .61 .69 .73 .78 | .39 .46 .49 .52 | .33 .41 .45 .48 |

## Findings

1. **Three Phase 0 results hold at every setting.**
   - NC²/TD to NAIN stays the largest single closeness step: ρ 0.44–0.55 at 400 m in all six
     runs, 0.71–0.79 at 2000 m.
   - Metric closeness and NAIN stay unrelated at 400 m end to end (ρ −0.04 to 0.15).
   - Metric to angular cost changes Mumbai's closeness ranking less than Copenhagen's at every
     setting (0.84–0.94 vs 0.75–0.89).
2. **The engine gap was mostly a cleaning artefact. This revises Phase 0 finding 3.** With raw
   topology, cityseer and depthmapX agree at ρ 0.90–0.99 (closeness) and 0.85–0.95
   (betweenness) in both cities, close to the 0.97–0.99 seen on the London test map. At 10 m
   that falls to 0.67–0.90 and 0.62–0.73; at 20 m to 0.64–0.92 and 0.51–0.68. So most of the
   disagreement attributed to the engines' catchment conventions came from what consolidation
   does to the network. A smaller radius effect remains at every setting (agreement rises with
   radius), consistent with catchment-edge conventions playing a secondary part.
3. **Betweenness divergence is roughly half cleaning.** End to end, metric betweenness vs NACH:
   Copenhagen 0.70–0.79 at 0 m, 0.57–0.65 at 10 m, 0.53–0.56 at 20 m; Mumbai 0.61–0.78,
   0.39–0.52, 0.33–0.48. The gap between the cities also narrows without consolidation
   (0.79 vs 0.78 at 2000 m; 0.70 vs 0.61 at 400 m).
4. **The closeness formula matters a little more on raw data.** Harmonic vs NC²/TD is 0.97–0.99
   at 10 and 20 m but 0.89–0.95 at 0 m, where segments are short and NC is large.
5. **Closeness end to end moves the other way in Copenhagen**: more consolidation gives *more*
   agreement (−0.04…0.17 to 0.15…0.56). Consolidation removes duplicate short segments, which
   NC-based measures reward and metric closeness does not.

## Why consolidation makes the engines disagree

Mechanism identified on a synthetic junction; see `wp2b_consolidation_stubs.md`. Consolidation
appends a short stub from each street's old endpoint to the merged junction point. cityseer
routes through the stubs and its angular cost inflates; depthmapX counts each stub as an extra
piece and its node count inflates. The size of the effect on the real networks is the next
test (`--destub`).

## What this means for the project

- **Report results at 0 m and 10 m together.** Neither is "correct": raw OSM double-counts
  pavements and dual carriageways; consolidation distorts geometry. The findings that survive
  both are the ones to stand on (finding 1).
- **For engine comparisons, use raw topology**, where no geometry has been edited.
- **Quote network length per km² rather than segment counts**, when comparing cities.
- Network cleaning is a sixth design choice in the ladder, as large as angular cost for
  betweenness. That is a result for the paper, and it sharpens Project 2: adding informal lanes
  is a change to the network of the same kind, so its effect should be read against this
  cleaning baseline.

## Reproduce

```bash
for c in 0 20; do
  python scripts/01_fetch_network.py --site copenhagen    --consolidate $c --name copenhagen_c$c
  python scripts/01_fetch_network.py --site mumbai_island --consolidate $c --name mumbai_island_c$c
  python scripts/02_ladder.py --site copenhagen_c$c    --radii 400 800 1200 2000
  python scripts/02_ladder.py --site mumbai_island_c$c --radii 400 800 1200 2000
done
python scripts/05_sensitivity.py
```
Copenhagen at 0 m is the slow one: 204,494 straight pieces, about 2.7 h in depthmapX.

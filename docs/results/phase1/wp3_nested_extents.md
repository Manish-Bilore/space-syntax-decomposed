# Phase 1, WP3 — nested extents: how much do values depend on where the map stops?

## Question

Space Syntax maps always stop somewhere. Global (radius n) measures have no catchment, so in
principle every street's value depends on the whole map. Radius-bounded measures should depend
only on streets within the radius, provided the map extends at least that far beyond the area
being reported. This WP measures both effects for Dharavi's streets as the map grows:

| Run | Map extent |
|---|---|
| dharavi@0 | Dharavi only, clipped at its boundary |
| dharavi@500, @1000, @2000 | Dharavi plus a 500 / 1000 / 2000 m surround |
| dharavi@4000 | Dharavi plus 4 km |
| gnorth@2000 | G/North ward plus 2 km (skipped if the ward boundary cannot be found) |
| island@2000 (reference) | Island city plus 2 km |

The network is fetched once and cleaned (10 m, destubbed, parallels merged). Each run is a
subset of it, so street geometry is identical across runs and the only thing that changes is
where the map stops. Dharavi's streets are compared with Spearman ρ against the reference run,
for NAIN and NACH at 400, 800 and 2000 m and radius n.

## Method check on the London test map

`scripts/08_nested.py` was tested on Barnsbury with three nested boxes (core 0.7 km, middle
1.8 km, whole map). ρ against the whole map, core streets only:

| | Core clipped | Core + 200 m | Core + 400 m | Middle + 400 m |
|---|---|---|---|---|
| NAIN R200 | 0.80 | 1.00 | 1.00 | 1.00 |
| NAIN R400 | 0.57 | 0.97 | 1.00 | 1.00 |
| NAIN radius n | 0.45 | 0.85 | 0.89 | 0.97 |
| NACH R400 | 0.84 | 0.98 | 1.00 | 1.00 |
| NACH radius n | 0.76 | 0.96 | 0.98 | 1.00 |

This behaves as expected: radius-bounded values reach ρ = 1.00 once the surround is at least the
radius; global NAIN keeps moving as the map grows; clipping at the boundary is the worst case for
every measure. It is a test of the code rather than a result about Mumbai.

## Result: Mumbai (8–9 Oct 2026)

Cleaned network (10 m, destubbed, parallels merged), fetched once for Greater Mumbai + 2 km
(36,714 streets). Dharavi = 1.78 km², 278 streets. Every run is a subset of that one network.
**Reference: Greater Mumbai + 2 km** (112,477 straight pieces; radius n took 6.0 h in depthmapX).

![Nested extents against Greater Mumbai](figures/fig8_nested.png)

Spearman ρ for Dharavi's 278 streets against the metropolitan map:

| Map | Streets | NAIN R400 / R800 / R2000 | **NAIN radius n** | NACH radius n |
|---|---|---|---|---|
| Dharavi, clipped | 278 | 0.92 / 0.79 / 0.57 | **0.53** | 0.68 |
| Dharavi + 500 m | 692 | 1.00 / 1.00 / 0.94 | **0.86** | 0.91 |
| Dharavi + 1 km | 1,372 | 1.00 / 1.00 / 1.00 | **0.96** | 0.98 |
| Dharavi + 2 km | 3,116 | 1.00 / 1.00 / 1.00 | **0.97** | 0.99 |
| Dharavi + 4 km | 7,478 | 1.00 / 1.00 / 1.00 | **0.99** | 0.99 |
| G/North ward + 2 km | 5,685 | 1.00 / 1.00 / 1.00 | **0.95** | 0.99 |
| Island city + 2 km | 12,119 | 1.00 / 1.00 / 1.00 | **0.83** | 0.98 |

### Findings

1. **Radius-bounded measures are exact once the surround reaches the radius.** R400 and R800 are
   1.00 from a 500 m surround, R2000 from 1 km (0.997). The 2 km buffer used throughout Phase 0
   and Phase 1 is sufficient.
2. **With a map centred on the study area, global integration converges quickly.** NAIN at radius
   n rises steadily with a centred surround: 0.53, 0.86, 0.96, 0.97, 0.99 for 0, 0.5, 1, 2 and 4 km.
   A 1 km surround already reproduces the metropolitan ranking at 0.96.
3. **An off-centre map is worse than a smaller centred one.** The island city map has 4× the
   streets of Dharavi + 2 km but agrees only at 0.83 (vs 0.97). The G/North ward map, which also
   contains Dharavi but not at its centre, gets 0.95 with almost twice the streets of Dharavi + 2 km.
   Dharavi sits near the island city's northern boundary, so that map extends many kilometres south
   of it and only 2 km north. **For global measures, where the study area sits in the map matters
   more than how large the map is.**
4. **Global choice is far less sensitive** (0.91 from a 500 m surround, ≥ 0.98 from 1 km, 0.98
   even on the off-centre island city).
5. **Clipping at the settlement boundary is badly wrong for everything** (global NAIN 0.53, even
   R2000 NAIN 0.57).

**Correction to the 8 Oct reading.** Against the island-city reference, global NAIN looked unstable
(0.87–0.93 with no convergence). That run's network was fetched for the island city + 2 km, so the
northern side of the larger Dharavi surrounds was cut off, and the reference itself was the
off-centre map. Neither the instability nor the non-monotonic pattern survives a metropolitan
reference.

### What this means

- **Practical rule for the project:** radius-bounded measures need a surround at least as wide as
  the largest radius. Global measures need a surround centred on the study area; 1 km reproduces the
  metropolitan ranking at ρ ≥ 0.96 for Dharavi, 4 km at 0.99. Report the extent either way.
- **For settlement-scale syntax studies:** two common practices are risky. Clipping to the
  settlement distorts every measure. Taking a large administrative window (district, ward) does not
  help global measures if the settlement sits near its edge. A modest surround centred on the
  settlement does better than either.
- **Caveat:** one settlement, one city, OSM network without most informal lanes. Project 2 reruns
  this on the digitised network.

## Run

```bash
export DEPTHMAPX=/path/to/depthmapXcli
python scripts/08_nested.py
# if a boundary does not geocode:
python scripts/08_nested.py --boundary dharavi=path/to/dharavi.gpkg --boundary gnorth=R<osm id>
```

The Mumbai run took about 35 minutes (island-city run with radius n: 21 min).
Metropolitan reference (Greater Mumbai with radius n took 6 h; finished runs are reused, so
adding extents to the series costs only the new runs):

```bash
python scripts/08_nested.py --name mumbai_nested_greater --rn-max-pieces 200000 \
  --runs dharavi@0 dharavi@500 dharavi@1000 dharavi@2000 dharavi@4000 gnorth@2000 island@2000 greater@2000
```

`--rerun` ignores earlier output and recomputes everything.

## Caveat that matters for Project 2

OSM under-maps Dharavi's lanes (Phase 0: Mumbai's mapped network is about 60% of Copenhagen's
per km²). This WP measures boundary effects on the network **as mapped**. Project 2 digitises
the lanes; the boundary question should be rerun on that network.

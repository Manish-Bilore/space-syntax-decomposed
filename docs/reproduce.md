# Reproduce

Everything runs from the repository root. The pipeline downloads OpenStreetMap data, so the
first runs need internet access; later steps reuse what is on disk.

## 1. Environment

```bash
conda create -n ssx python=3.12 -y && conda activate ssx
pip install -e ".[dev]"
pytest -q                      # 31 tests: reimplemented measures on hand-derived toy layouts
```

## 2. depthmapX command-line tool

Build without Qt ([instructions](depthmapx_build.md)), then:

```bash
export DEPTHMAPX=/path/to/depthmapX/build/depthmapXcli/depthmapXcli
```

## 3. Fidelity check (Barnsbury, depthmapX test data)

```bash
python scripts/00_fidelity.py --lines ~/depthmapX/testdata/barnsbury_extended1_axial.csv --name barnsbury
```

## 4. Networks and ladder

```bash
for s in copenhagen mumbai_island; do
  python scripts/01_fetch_network.py --site $s --consolidate 0 --name ${s}_c0
  python scripts/01_fetch_network.py --site $s --consolidate 10 --destub --merge-parallel --name ${s}_c10dp
done
for s in copenhagen_c0 copenhagen_c10dp mumbai_island_c0 mumbai_island_c10dp; do
  python scripts/02_ladder.py --site $s --radii 400 800 1200 2000
done
```

## 5. Work packages

| WP | Command |
|---|---|
| WP1 tiles | `python scripts/04_tiles.py --sites copenhagen_c10dp mumbai_island_c10dp --tile 1000 --radius 800` |
| WP2 cleaning | `python scripts/05_sensitivity.py` (after fetching the 0 / 10 / 20 m variants) |
| WP2b stubs | `python scripts/06_stub_diag.py`, `python scripts/07_engine_scale.py` |
| WP3 nested extents | `python scripts/08_nested.py` (radius n on Greater Mumbai takes hours) |
| WP4 axial | `python scripts/09_axial.py --site <site>`; validation `python scripts/10_axial_validate.py --reference <barnsbury csv> --crs 27700 --fetch`; diagnostics `python scripts/11_axial_diag.py` |

## 6. Maps, dashboard and this website

```bash
python scripts/12_atlas.py              # full-resolution maps -> reports/atlas/
python scripts/13_build_site.py         # web maps, dashboard data, reports -> docs/
quarto preview docs                     # local preview
```

`13_build_site.py` draws the atlas at web resolution into `docs/atlas/`, exports dashboard data
(`scripts/14_export_web.py`) into `docs/dashboard/data/`, and copies the work-package reports into
`docs/results/`. Commit `docs/` and push; GitHub Actions renders the Quarto site and publishes it.

## Data and licences

- Code: MIT licence.
- Text and figures: CC BY 4.0.
- Street data © OpenStreetMap contributors, Open Database Licence. Derived networks are not
  committed; the dashboard data in `docs/dashboard/data/` are derived from OSM and are ODbL.
- Barnsbury reference map: depthmapX test data (SpaceGroupUCL/depthmapX), used for validation
  only and not redistributed here.

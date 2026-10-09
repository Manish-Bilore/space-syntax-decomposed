"""Export compact per-site data for the interactive dashboard (docs/dashboard/data/<site>.json).

    python scripts/14_export_web.py                                   # cleaned networks
    python scripts/14_export_web.py --sites copenhagen_c10dp mumbai_island_c10dp copenhagen_c0

Per site, interior streets only:
  * geometry: WGS84, simplified (default 2 m), quantised to 1e-5 degrees and delta-encoded
  * every ladder measure (S0-S3 at each radius, S4 axial) as a percentile rank 0-99 within the
    site (-1 = missing): the dashboard compares ranks, as the reports do
  * the agreement tables (agreement.csv, agreement_axial.csv), zoom windows and window stats
Derived from OpenStreetMap: the exported files are under the Open Database Licence (ODbL).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("atlas", ROOT / "scripts" / "12_atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)

BASES = ["S0_harmonic", "S1_harmonic", "S1_hillier", "S2_hillier", "S3_integration", "S3_nain",
         "S0_betweenness", "S1_betweenness", "S2_betweenness", "S3_choice", "S3_nach"]
AXIAL = ["S4_connectivity", "S4_integration_hh_Rn", "S4_integration_hh_R3", "S4_choice_Rn",
         "S4_choice_R3"]
Q = 1e5  # quantisation: 1e-5 degrees ~ 1 m


def pct(v: pd.Series) -> list[int]:
    x = pd.to_numeric(v, errors="coerce")
    r = x.rank(pct=True, method="average")
    out = np.floor(r.to_numpy() * 100 - 1e-9).clip(0, 99)
    out = np.where(np.isfinite(out), out, -1).astype(int)
    return out.tolist()


def encode(geom) -> list[list[int]]:
    parts = getattr(geom, "geoms", [geom])
    out = []
    for p in parts:
        c = np.round(np.asarray(p.coords)[:, :2] * Q).astype(np.int64)
        if len(c) < 2:
            continue
        d = np.vstack([c[:1], np.diff(c, axis=0)]).ravel().tolist()
        out.append(d)
    return out


def export_site(site: str, out: Path, simplify: float) -> dict:
    d = ROOT / "data" / site
    lad, bnd, _ = atlas.load_site(site)
    lad = lad[lad.interior.astype(bool)].reset_index(drop=True)
    radii = sorted({int(c.rsplit("_", 1)[1]) for c in lad if c.startswith("S3_nain_")})
    measures = {}
    for b in BASES:
        for r in radii:
            if f"{b}_{r}" in lad:
                measures[f"{b}_{r}"] = pct(lad[f"{b}_{r}"])
    for a in AXIAL:
        if a in lad:
            measures[a] = pct(lad[a])
    g = lad.geometry.simplify(simplify).to_crs(4326)
    lines = [encode(x) for x in g]
    wins = []
    for key, name, bx in atlas.windows_of(site, lad.crs):
        b = gpd.GeoSeries([bx], crs=lad.crs).to_crs(4326).total_bounds
        wins.append({"key": key, "name": name, "bounds": [round(v, 5) for v in b]})
    tabs = {}
    for f in ("agreement.csv", "axial/agreement_axial.csv"):
        p = d / f
        if p.exists():
            t = pd.read_csv(p)
            cols = [c for c in ("radius", "family", "step", "a", "b", "n", "spearman",
                                "top10_overlap") if c in t]
            tabs[Path(f).stem] = json.loads(t[cols].round(4).to_json(orient="records"))
    area = float(bnd.area.iloc[0]) / 1e6
    km = float(lad.length.sum()) / 1000
    meta = {"site": site, "city": atlas.city_of(site), "label": atlas.title_of(site),
            "streets": len(lad), "km": round(km, 1), "km_per_km2": round(km / area, 2),
            "radii": radii, "bounds": [round(v, 5) for v in lad.to_crs(4326).total_bounds],
            "q": Q, "simplify_m": simplify, "windows": wins}
    doc = {"meta": meta, "lines": lines, "measures": measures, "tables": tabs}
    f = out / f"{site}.json"
    f.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"  {site}: {len(lad):,} streets, {len(measures)} measures, {f.stat().st_size / 1e6:.1f} MB")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+", default=["copenhagen_c10dp", "mumbai_island_c10dp"])
    ap.add_argument("--out", default=str(ROOT / "docs" / "dashboard" / "data"))
    ap.add_argument("--simplify", type=float, default=2.0, help="geometry tolerance (m)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    metas = [export_site(s, out, args.simplify) for s in args.sites
             if (ROOT / "data" / s / "ladder.gpkg").exists()]
    win = next((p for p in (ROOT / "docs/atlas/windows.csv", ROOT / "reports/atlas/windows.csv")
                if p.exists()), None)
    windows = json.loads(pd.read_csv(win).round(3).to_json(orient="records")) if win else []
    (out / "index.json").write_text(json.dumps({"sites": metas, "windows": windows}, indent=1))
    print(f"wrote {out / 'index.json'} ({len(metas)} sites)")


if __name__ == "__main__":
    main()

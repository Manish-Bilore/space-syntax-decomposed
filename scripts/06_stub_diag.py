"""Phase 1, WP2b: do consolidated networks carry artificial end-of-street turns?

    python scripts/06_stub_diag.py --sites copenhagen mumbai_island --levels 0 10 20

Reads existing data/<site>[_c<level>]/network.gpkg (no new downloads) and counts 'stub ends':
street ends whose first piece is <= 10 m and turns >= 30 degrees into the next piece.
Writes reports/phase1/wp2b_stubs.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ssx.network.build import stub_stats  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="+", default=["copenhagen", "mumbai_island"])
    ap.add_argument("--levels", nargs="+", default=["0", "10", "20"],
                    help="consolidation levels; also accepts suffixes such as 10d")
    ap.add_argument("--max-len", type=float, default=10.0)
    ap.add_argument("--min-turn", type=float, default=30.0)
    args = ap.parse_args()
    rows = []
    for s in args.sites:
        for lv in args.levels:
            f = ROOT / "data" / (s if lv == "10" else f"{s}_c{lv}") / "network.gpkg"
            if not f.exists():
                print("  missing", f)
                continue
            seg = gpd.read_file(f, layer="segments")
            rows.append({"site": s, "consolidate_m": lv,
                         **stub_stats(seg, args.max_len, args.min_turn)})
    t = pd.DataFrame(rows)
    out = ROOT / "reports" / "phase1"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "wp2b_stubs.csv", index=False)
    with pd.option_context("display.width", 180):
        print(t.to_string(index=False))


if __name__ == "__main__":
    main()

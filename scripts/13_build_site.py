"""Assemble the documentation website in docs/ from the pipeline outputs.

    python scripts/13_build_site.py                # web atlas + dashboard data + reports
    python scripts/13_build_site.py --copy-atlas   # copy reports/atlas instead of redrawing
    quarto preview docs                            # preview; push to publish

What it does:
  * maps      -> docs/atlas/ (*.png, windows.csv; atlas.md becomes docs/atlas/index.md)
  * reports   -> docs/results/ (phase 0, fidelity, phase 1 work packages) with their PNG figures
  * dashboard -> docs/dashboard/data/ (scripts/14_export_web.py)
The hand-written pages (index, report, dashboard, glossary, reproduce, nuances) are not touched.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def copy_reports() -> None:
    res = DOCS / "results"
    jobs = [
        (ROOT / "reports/phase0/README.md", res / "phase0/index.md"),
        (ROOT / "reports/results_phase0.md", res / "results_phase0.md"),
        (ROOT / "reports/fidelity_barnsbury.md", res / "fidelity_barnsbury.md"),
        (ROOT / "reports/phase1/README.md", res / "phase1/index.md"),
    ]
    for f in sorted((ROOT / "reports/phase1").glob("wp*.md")):
        jobs.append((f, res / "phase1" / f.name))
    for src, dst in jobs:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    for ph in ("phase0", "phase1"):
        figs = sorted((ROOT / "reports" / ph / "figures").glob("*.png"))
        out = res / ph / "figures"
        out.mkdir(parents=True, exist_ok=True)
        for f in figs:
            shutil.copy2(f, out / f.name)
        print(f"  {len(figs)} figures -> {out.relative_to(ROOT)}")


def build_atlas(copy: bool, dpi: int) -> None:
    out = DOCS / "atlas"
    out.mkdir(parents=True, exist_ok=True)
    if copy:
        src = ROOT / "reports" / "atlas"
        if not src.exists():
            sys.exit("reports/atlas not found: run scripts/12_atlas.py first, or drop --copy-atlas")
        for f in list(src.glob("*.png")) + list(src.glob("*.csv")) + list(src.glob("*.md")):
            shutil.copy2(f, out / f.name)
    else:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "12_atlas.py"), "--out", str(out),
                        "--dpi", str(dpi)], check=True)
    md = out / "atlas.md"
    if md.exists():
        md.replace(out / "index.md")
    print(f"  atlas -> {out.relative_to(ROOT)} ({len(list(out.glob('*.png')))} maps)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy-atlas", action="store_true", help="copy reports/atlas instead of rerunning")
    ap.add_argument("--dpi", type=int, default=110, help="map resolution for the website")
    ap.add_argument("--skip-atlas", action="store_true")
    ap.add_argument("--skip-dashboard", action="store_true")
    ap.add_argument("--dashboard-sites", nargs="+",
                    default=["copenhagen_c10dp", "mumbai_island_c10dp"])
    args = ap.parse_args()
    print("[reports]")
    copy_reports()
    if not args.skip_atlas:
        print("[atlas]")
        build_atlas(args.copy_atlas, args.dpi)
    if not args.skip_dashboard:
        print("[dashboard]")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "14_export_web.py"), "--sites",
                        *args.dashboard_sites], check=True)
    print("done: preview with `quarto preview docs`, publish by pushing to main")


if __name__ == "__main__":
    main()

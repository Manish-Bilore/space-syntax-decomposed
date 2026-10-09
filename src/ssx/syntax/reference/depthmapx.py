"""Thin wrapper around the depthmapX command-line tool (the reference implementation).

Build the CLI without Qt (see docs/depthmapx_build.md), then point DEPTHMAPX at the binary:

    export DEPTHMAPX=/path/to/build/depthmapXcli/depthmapXcli

Pipeline per run:  IMPORT lines -> MAPCONVERT (axial | segment) -> AXIAL / SEGMENT
                   -> EXPORT shapegraph-map-csv + shapegraph-connections-csv
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


def _bin(binary: str | None = None) -> str:
    b = binary or os.environ.get("DEPTHMAPX") or shutil.which("depthmapXcli")
    if not b:
        raise FileNotFoundError("depthmapXcli not found: set $DEPTHMAPX or pass binary=")
    b = os.path.expanduser(b)
    if not (os.path.isfile(b) and os.access(b, os.X_OK)):
        raise FileNotFoundError(f"DEPTHMAPX={b!r} is not an executable file. Point it at the built "
                                "binary, e.g. export DEPTHMAPX=~/depthmapX/build/depthmapXcli/depthmapXcli")
    return b


def check_binary(binary: str | None = None) -> str:
    """Fail fast (before any long step) if depthmapXcli is missing or not executable."""
    return _bin(binary)


VERBOSE = False


def _run(binary: str, *args: str) -> None:
    import time

    mode = args[args.index("-m") + 1] if "-m" in args else "?"
    t = time.time()
    if VERBOSE:
        print(f"    depthmapX {mode} ...", flush=True)
    res = subprocess.run([binary, *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"depthmapXcli {' '.join(args)} failed:\n{res.stdout}\n{res.stderr}")
    if VERBOSE:
        print(f"    depthmapX {mode} done in {time.time() - t:.0f}s", flush=True)


def write_lines_csv(gdf_or_df, path: str | Path) -> Path:
    """Write lines as the 'Ref,x1,y1,x2,y2' CSV depthmapX imports as a drawing.

    Accepts a GeoDataFrame of 2-point LineStrings, or a DataFrame with x1,y1,x2,y2 columns.
    Multi-vertex lines must be exploded into straight pieces first (network.explode_straight).
    """
    if hasattr(gdf_or_df, "geometry"):
        rows = []
        for i, g in enumerate(gdf_or_df.geometry):
            (x1, y1), (x2, y2) = g.coords[0], g.coords[-1]
            rows.append((i, x1, y1, x2, y2))
        df = pd.DataFrame(rows, columns=["Ref", "x1", "y1", "x2", "y2"])
    else:
        df = gdf_or_df[["x1", "y1", "x2", "y2"]].copy()
        df.insert(0, "Ref", range(len(df)))
    path = Path(path)
    df.to_csv(path, index=False, float_format="%.6f")
    return path


@dataclass
class DmxResult:
    map: pd.DataFrame
    connections: pd.DataFrame
    graph_file: Path
    map_csv: Path
    conn_csv: Path


def run_axial(lines_csv: str | Path, workdir: str | Path, radii: str = "n,3",
              choice: bool = True, binary: str | None = None) -> DmxResult:
    """Lines are treated as an axial map as given (no fewest-line reduction)."""
    b = _bin(binary)
    w = Path(workdir)
    w.mkdir(parents=True, exist_ok=True)
    g = w / "axial.graph"
    _run(b, "-m", "IMPORT", "-f", str(lines_csv), "-o", str(g))
    _run(b, "-m", "MAPCONVERT", "-f", str(g), "-o", str(g), "-co", "axial", "-con", "Axial")
    args = ["-m", "AXIAL", "-f", str(g), "-o", str(g), "-xa", radii, "-xal", "-xar"]
    if choice:
        args.append("-xac")
    _run(b, *args)
    return _export(b, g, w, "axial")


def run_segment(lines_csv: str | Path, workdir: str | Path, radii: str = "n,400,800,1200",
                radius_type: str = "metric", bins: int = 1024, choice: bool = True,
                via_axial: bool = True, stub_pct: float | None = None,
                binary: str | None = None) -> DmxResult:
    """Angular (tulip) segment analysis.

    via_axial=True: lines -> axial map -> segment map. depthmapX splits lines at every crossing
    and removes stubs (`stub_pct`, % of line length). This is the standard SS workflow.
    via_axial=False: lines are converted straight to a segment map (use for road-centreline
    input that is already split at junctions).
    """
    b = _bin(binary)
    w = Path(workdir)
    w.mkdir(parents=True, exist_ok=True)
    g = w / "segment.graph"
    _run(b, "-m", "IMPORT", "-f", str(lines_csv), "-o", str(g))
    if via_axial:
        _run(b, "-m", "MAPCONVERT", "-f", str(g), "-o", str(g), "-co", "axial", "-con", "Axial")
    conv = ["-m", "MAPCONVERT", "-f", str(g), "-o", str(g), "-co", "segment", "-con", "Segment"]
    if via_axial and stub_pct is not None:
        conv += ["-crsl", str(stub_pct)]
    _run(b, *conv)
    args = ["-m", "SEGMENT", "-f", str(g), "-o", str(g), "-st", "tulip", "-stb", str(bins),
            "-srt", radius_type, "-sr", radii]
    if choice:
        args.append("-sic")
    _run(b, *args)
    return _export(b, g, w, "segment")


def _export(b: str, g: Path, w: Path, stem: str) -> DmxResult:
    mcsv = w / f"{stem}_map.csv"
    ccsv = w / f"{stem}_conn.csv"
    _run(b, "-m", "EXPORT", "-f", str(g), "-o", str(mcsv), "-em", "shapegraph-map-csv")
    _run(b, "-m", "EXPORT", "-f", str(g), "-o", str(ccsv), "-em", "shapegraph-connections-csv")
    return DmxResult(map=pd.read_csv(mcsv), connections=pd.read_csv(ccsv), graph_file=g,
                     map_csv=mcsv, conn_csv=ccsv)


AXIAL_COLS = {
    "Connectivity": "connectivity",
    "Node Count": "node_count_Rn",
    "Mean Depth": "mean_depth_Rn",
    "Integration [HH]": "integration_hh_Rn",
    "Integration [HH] R3": "integration_hh_R3",
    "Node Count R3": "node_count_R3",
    "Choice": "choice_Rn",
    "Choice R3": "choice_R3",
    "Line Length": "line_length",
}


def axial_measures(lines, workdir, radii: str = "n,3", choice: bool = True,
                   binary: str | None = None, reuse: bool = True) -> pd.DataFrame:
    """Axial measures for a GeoDataFrame of straight lines, one row per input line (same order).

    depthmapX may drop duplicate or degenerate lines; those rows come back NaN. Undefined values
    (depthmapX writes -1, e.g. integration where every line is one step away) become NaN.
    reuse=True reads a finished export from `workdir` if it was made from the same lines.
    """
    import numpy as np
    from scipy.spatial import cKDTree

    w = Path(workdir)
    w.mkdir(parents=True, exist_ok=True)
    cur = np.array([(g.coords[0][0], g.coords[0][1], g.coords[-1][0], g.coords[-1][1])
                    for g in lines.geometry])
    cached, src = w / "axial_map.csv", w / "lines.csv"
    m = None
    if reuse and cached.exists() and src.exists():
        try:
            old = pd.read_csv(src)[["x1", "y1", "x2", "y2"]].to_numpy(float)
            mc = pd.read_csv(cached)
            if len(old) == len(cur) and np.allclose(old, cur, atol=1e-4) and "Integration [HH]" in mc:
                m = mc
                print(f"    reusing finished depthmapX axial output in {w}", flush=True)
        except Exception:  # noqa: BLE001
            m = None
    if m is None:
        csv = write_lines_csv(lines, src)
        m = run_axial(csv, w, radii=radii, choice=choice, binary=binary).map
    key_d = np.c_[(m.x1 + m.x2) / 2, (m.y1 + m.y2) / 2]
    key_p = np.c_[(cur[:, 0] + cur[:, 2]) / 2, (cur[:, 1] + cur[:, 3]) / 2]
    dist, idx = cKDTree(key_d).query(key_p)
    ok = dist < 0.05
    out = pd.DataFrame(index=range(len(cur)))
    for src_col, dst in AXIAL_COLS.items():
        if src_col in m:
            v = m[src_col].to_numpy(float)[idx]
            v = np.where(v == -1, np.nan, v)
            out[dst] = np.where(ok, v, np.nan)
    out.attrs["matched_share"] = float(ok.mean())
    return out


def _radius_label(r) -> str:
    return "Rn" if str(r) == "n" else f"R{int(r)}"


def _dmx_suffix(r) -> str:
    return "" if str(r) == "n" else f" R{int(r)} metric"


def street_measures(seg, radii, workdir, bins: int = 1024, choice: bool = True,
                    id_col: str = "seg_id", binary: str | None = None,
                    reuse: bool = True) -> pd.DataFrame:
    """Angular segment measures per street, from depthmapX on straight pieces.

    Streets are exploded into straight pieces, run through depthmapX (tulip `bins`, metric
    radii, 'n' allowed), matched back by piece midpoint and averaged to the street with
    piece-length weights. Returns one row per street id with node_count, total_depth,
    integration, nain and (if choice) choice and nach, suffixed _Rn / _R400 ...

    reuse=True: if this workdir already holds a finished depthmapX export made from the same
    pieces (checked against the pieces.csv written for that run) with every requested column,
    it is read instead of rerunning. This lets an interrupted or extended batch resume.
    """
    import numpy as np
    from scipy.spatial import cKDTree

    from ssx.network.build import explode_straight

    w = Path(workdir)
    w.mkdir(parents=True, exist_ok=True)
    pieces = explode_straight(seg, id_col=id_col)
    need = [f"T{bins} Node Count{_dmx_suffix(r)}" for r in radii]
    need += [f"T{bins} Choice{_dmx_suffix(r)}" for r in radii] if choice else []
    cached = w / "segment_map.csv"
    m = None
    if reuse and cached.exists() and (w / "pieces.csv").exists():
        # depthmapX drops a few duplicate or degenerate lines, so its export has fewer rows than
        # the pieces submitted; compare the submitted pieces.csv with the current pieces instead
        try:
            old = pd.read_csv(w / "pieces.csv")[["x1", "y1", "x2", "y2"]].to_numpy(float)
            cur = np.array([(g.coords[0][0], g.coords[0][1], g.coords[-1][0], g.coords[-1][1])
                            for g in pieces.geometry])
            mc = pd.read_csv(cached)
            if (len(old) == len(cur) and np.allclose(old, cur, atol=1e-4)
                    and all(c in mc.columns for c in need)):
                m = mc
                print(f"    reusing finished depthmapX output in {w}", flush=True)
        except Exception:  # noqa: BLE001 - unreadable cache: rerun
            m = None
    if m is None:
        csv = write_lines_csv(pieces, w / "pieces.csv")
        res = run_segment(csv, w, radii=",".join(str(r) for r in radii), radius_type="metric",
                          bins=bins, choice=choice, via_axial=False, binary=binary)
        m = res.map
    mid_d = np.c_[(m.x1 + m.x2) / 2, (m.y1 + m.y2) / 2]
    mid_p = np.array([g.interpolate(0.5, normalized=True).coords[0] for g in pieces.geometry])
    dist, idx = cKDTree(mid_d).query(mid_p)
    ok = dist < 0.05
    cols = {}
    for r in radii:
        lab, sfx = _radius_label(r), _dmx_suffix(r)
        nc = m[f"T{bins} Node Count{sfx}"].to_numpy(float)[idx]
        td = m[f"T{bins} Total Depth{sfx}"].to_numpy(float)[idx]
        cols[f"node_count_{lab}"] = nc
        cols[f"total_depth_{lab}"] = td
        with np.errstate(divide="ignore", invalid="ignore"):
            cols[f"integration_{lab}"] = np.where(td > 0, nc ** 2 / td, np.nan)
            cols[f"nain_{lab}"] = nc ** 1.2 / (td + 2)
        if choice:
            ch = m[f"T{bins} Choice{sfx}"].to_numpy(float)[idx]
            cols[f"choice_{lab}"] = ch
            cols[f"nach_{lab}"] = np.log(ch + 1) / np.log(td + 3)
    d = pd.DataFrame(cols)
    d[~ok] = np.nan
    d["w"] = pieces.geometry.length.to_numpy()
    d["parent"] = pieces[f"parent_{id_col}"].to_numpy()
    d = d.dropna()
    meas = [c for c in d.columns if c not in ("w", "parent")]
    num = d[meas].multiply(d["w"], axis=0).groupby(d["parent"]).sum()
    out = num.divide(d.groupby("parent")["w"].sum(), axis=0)
    out.index.name = id_col
    out.attrs["pieces"] = len(pieces)
    out.attrs["matched_share"] = float(ok.mean())
    return out

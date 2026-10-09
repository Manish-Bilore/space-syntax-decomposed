"""Rank agreement between measures (analysis A1/A2).

Everything is compared on ranks: the engines use different units and normalisations, and the
research question is whether they order streets the same way.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def spearman_table(df: pd.DataFrame, pairs: list[tuple[str, str]],
                   mask: pd.Series | None = None) -> pd.DataFrame:
    rows = []
    d = df if mask is None else df.loc[mask]
    for a, b in pairs:
        if a not in d or b not in d:
            continue
        x, y = d[a].to_numpy(float), d[b].to_numpy(float)
        ok = np.isfinite(x) & np.isfinite(y)
        rho = spearmanr(x[ok], y[ok])[0] if ok.sum() > 2 else np.nan
        rows.append({"a": a, "b": b, "n": int(ok.sum()), "spearman": rho,
                     "top10_overlap": top_overlap(x[ok], y[ok], 0.10)})
    return pd.DataFrame(rows)


def top_overlap(x: np.ndarray, y: np.ndarray, frac: float) -> float:
    """Share of the top `frac` by x that is also in the top `frac` by y."""
    k = max(1, int(round(len(x) * frac)))
    return len(set(np.argsort(-x)[:k]) & set(np.argsort(-y)[:k])) / k


def rank_divergence(df: pd.DataFrame, a: str, b: str) -> pd.Series:
    """Percentile rank of a minus percentile rank of b. +: a ranks the street higher."""
    return df[a].rank(pct=True) - df[b].rank(pct=True)

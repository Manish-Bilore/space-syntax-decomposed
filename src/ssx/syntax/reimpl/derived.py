"""Second-order Space Syntax measures computed across a whole map."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _r(x, y) -> float:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    return float(np.corrcoef(x[ok], y[ok])[0, 1])


def intelligibility(df: pd.DataFrame, global_col: str = "integration_hh_Rn",
                    conn_col: str = "connectivity") -> dict[str, float]:
    """Pearson correlation between connectivity (local, visible) and global integration.

    High intelligibility: what you can see from a line tells you how it sits in the whole.
    Reported both as r and r^2 since the literature uses both.
    """
    r = _r(df[conn_col], df[global_col])
    return {"r": r, "r2": r * r}


def synergy(df: pd.DataFrame, local_col: str = "integration_hh_R3",
            global_col: str = "integration_hh_Rn") -> dict[str, float]:
    """Pearson correlation between local (R3) and global (Rn) integration."""
    r = _r(df[local_col], df[global_col])
    return {"r": r, "r2": r * r}

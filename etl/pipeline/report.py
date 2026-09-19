"""What every stage's manifest says the same way (`P3-35f`, `Q133`).

Out of `arrows.py`, where `ArrowReport.measured` lived and five other stages
imported the whole module to reach it.
"""

from __future__ import annotations

import numpy as np


def tail_of(values: list[float]) -> dict[str, float]:
    """One distribution as a manifest publishes it: p50, p90, p99, max and `n`.

    p90 and p99 rather than `TramwayReport.measured`'s p10/p50/p90: every
    distribution that uses this is a residual whose *tail* is the finding, and a
    median residual near zero says nothing about the arrow on the wrong street.
    ⚠️ **`n` rides along because it is how a reader tells whether the distribution
    was recorded over the refusals too** — `n` exceeding `drawn` — which is what
    keeps it from being confined to its own bar (`Q58`).
    """
    if not values:
        return {}
    points = np.percentile(np.asarray(values), (50, 90, 99, 100))
    return {
        "p50": round(float(points[0]), 4),
        "p90": round(float(points[1]), 4),
        "p99": round(float(points[2]), 4),
        "max": round(float(points[3]), 4),
        "n": len(values),
    }

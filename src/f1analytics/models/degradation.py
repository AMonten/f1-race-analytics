"""Simple linear tyre degradation model: LapTime = α + β × TyreAge.

This is intentionally a minimal model for V1: an ordinary least squares fit
of lap time (seconds) against tyre age (laps completed on the current set
of tyres — FastF1's `TyreLife`, which already accounts for a stint started
on a used rather than fresh set). It is fit independently per driver/stint,
over that stint's *appropriate* laps only (see
`f1analytics.analysis.tyres.compute_stint_degradation` for what "appropriate"
means in practice: this project reuses the clean-lap methodology rather than
a bespoke filter).

What this model does NOT claim
-------------------------------
- It does not separate tyre degradation from fuel burn-off, track evolution,
  traffic, or a driver managing pace to a target gap — all of these also
  change lap time over a stint and are entangled in `slope_s_per_lap`.
  **Tyre age is not implied to be the only cause of lap-time evolution.**
- A single stint, on one compound, at one track, on one day is a small
  sample. Treat `slope_s_per_lap` as describing *this stint*, not a
  compound's general degradation characteristics.
- A high `r_squared` means tyre age explains most of the lap-time variation
  *within this stint's laps* — it is a goodness-of-fit measure, not
  validation that degradation is the causal mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from f1analytics.config import DEGRADATION_LOW_SAMPLE_THRESHOLD, MIN_DEGRADATION_OBSERVATIONS


@dataclass
class DegradationFit:
    """Result of fitting LapTime = intercept + slope * TyreAge over one stint."""

    n_observations: int
    intercept_s: float | None
    slope_s_per_lap: float | None
    r_squared: float | None
    p_value: float | None
    std_err: float | None
    warning: str | None


def fit_degradation_model(tyre_age, lap_time_s) -> DegradationFit:
    """Fit the linear degradation model over one stint's laps.

    Args:
        tyre_age: Tyre age in laps for each observation (e.g. FastF1's
            `TyreLife`).
        lap_time_s: Lap time in seconds for each observation. Callers
            should pass only laps already filtered to be appropriate for
            pace analysis — see the module docstring.

    Returns:
        A `DegradationFit`. Regression fields are all `None`, with a
        `warning` explaining why, when: fewer than
        `MIN_DEGRADATION_OBSERVATIONS` valid observations are available
        (`"insufficient_observations"`), or tyre age doesn't vary across
        observations, making the slope undefined
        (`"no_tyre_age_variation"`). A fit with fewer than
        `DEGRADATION_LOW_SAMPLE_THRESHOLD` observations is still returned,
        but flagged `"low_sample_size"` — interpret it cautiously rather
        than discarding it outright.
    """
    age = np.asarray(tyre_age, dtype=float)
    lap_time = np.asarray(lap_time_s, dtype=float)
    valid = ~np.isnan(age) & ~np.isnan(lap_time)
    age, lap_time = age[valid], lap_time[valid]
    n = len(age)

    if n < MIN_DEGRADATION_OBSERVATIONS:
        return DegradationFit(n, None, None, None, None, None, "insufficient_observations")

    if np.unique(age).size < 2:
        return DegradationFit(n, None, None, None, None, None, "no_tyre_age_variation")

    result = stats.linregress(age, lap_time)
    warning = "low_sample_size" if n < DEGRADATION_LOW_SAMPLE_THRESHOLD else None

    return DegradationFit(
        n_observations=n,
        intercept_s=float(result.intercept),
        slope_s_per_lap=float(result.slope),
        r_squared=float(result.rvalue**2),
        p_value=float(result.pvalue),
        std_err=float(result.stderr),
        warning=warning,
    )

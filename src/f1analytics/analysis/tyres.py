"""Tyre degradation analysis: fits the V1 linear degradation model
(`f1analytics.models.degradation`) per driver/stint and across the field.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from f1analytics.analysis.stints import reconstruct_driver_stints
from f1analytics.models.degradation import DegradationFit, fit_degradation_model


@dataclass
class StintDegradation:
    """Degradation fit for one driver's stint, alongside stint identifiers."""

    driver: str
    stint_number: int
    compound: str | None
    fit: DegradationFit


def compute_stint_degradation(
    flagged_laps: pd.DataFrame, driver: str, stint_number: int
) -> StintDegradation:
    """Fit the linear degradation model for one driver's stint.

    Only that stint's *clean* laps are used as input (see
    `f1analytics.data.preprocessing` for exactly what "clean" excludes: pit
    laps, SC/VSC-affected laps, deleted laps, FastF1-inaccurate laps, and
    statistical outliers) — this reuses the same appropriateness criteria as
    the rest of the project's pace analysis rather than a bespoke filter.
    """
    stint_laps = flagged_laps[
        (flagged_laps["Driver"] == driver)
        & (flagged_laps["Stint"] == stint_number)
        & (flagged_laps["IsCleanLap"])
    ]
    compound = (
        stint_laps["Compound"].dropna().iloc[0]
        if stint_laps["Compound"].notna().any()
        else None
    )
    fit = fit_degradation_model(stint_laps["TyreLife"], stint_laps["LapTimeSeconds"])
    return StintDegradation(
        driver=driver, stint_number=int(stint_number), compound=compound, fit=fit
    )


def compute_driver_degradation(flagged_laps: pd.DataFrame, driver: str) -> list[StintDegradation]:
    """Fit the degradation model for every stint driven by `driver`."""
    stints = reconstruct_driver_stints(flagged_laps, driver)
    return [
        compute_stint_degradation(flagged_laps, driver, stint.stint_number) for stint in stints
    ]


def compute_field_degradation(flagged_laps: pd.DataFrame) -> pd.DataFrame:
    """Fit the degradation model for every driver/stint in the session.

    Returns:
        A DataFrame with one row per (driver, stint): `driver`,
        `stint_number`, `compound`, and the flattened `DegradationFit`
        fields (`n_observations`, `intercept_s`, `slope_s_per_lap`,
        `r_squared`, `p_value`, `std_err`, `warning`). Empty DataFrame if
        the session has no stint data.
    """
    rows = []
    for driver in flagged_laps["Driver"].dropna().unique():
        for result in compute_driver_degradation(flagged_laps, driver):
            rows.append(
                {
                    "driver": result.driver,
                    "stint_number": result.stint_number,
                    "compound": result.compound,
                    **vars(result.fit),
                }
            )
    return pd.DataFrame(rows)

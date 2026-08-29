"""Tyre stint reconstruction.

A "stint" is a continuous run on one set of tyres, identified by FastF1's
per-lap `Stint` counter (incremented every time a driver pits). Stints are
reconstructed from *every* lap of a driver (including pit laps and laps
affected by track status) so the lap range is correct — only the pace
statistics (`median_pace_s`, `pace_variation_s`) are restricted to clean
laps, consistent with the rest of the project's pace methodology (see
`f1analytics.data.preprocessing`).

Tyre age comes from FastF1's own `TyreLife` rather than being recomputed
from position within the stint, since `TyreLife` correctly starts above 0
for a stint begun on a used ("non-fresh") set of tyres.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Stint:
    """One driver's continuous run on a single set of tyres."""

    driver: str
    team: str | None
    stint_number: int
    compound: str | None
    start_lap: int
    end_lap: int
    length: int
    tyre_age_start: int | None
    tyre_age_end: int | None
    n_clean_laps: int
    median_pace_s: float | None
    pace_variation_s: float | None


def reconstruct_driver_stints(flagged_laps: pd.DataFrame, driver: str) -> list[Stint]:
    """Reconstruct every stint driven by `driver` in this session.

    Laps with a missing `Stint` value are excluded from reconstruction —
    this is a data-quality limitation of the underlying timing data
    (typically an installation lap or a lap FastF1 couldn't fully classify),
    not a modelling choice, and affects only how a handful of edge-case laps
    get attributed to a stint.
    """
    driver_laps = flagged_laps[flagged_laps["Driver"] == driver]
    driver_laps = driver_laps[driver_laps["Stint"].notna()]

    stints: list[Stint] = []
    for stint_number, group in driver_laps.groupby("Stint", sort=True):
        group = group.sort_values("LapNumber")
        clean = group[group["IsCleanLap"]]

        team = group["Team"].iloc[0] if "Team" in group.columns else None
        compound = (
            group["Compound"].dropna().iloc[0] if group["Compound"].notna().any() else None
        )
        tyre_age_start = group["TyreLife"].iloc[0]
        tyre_age_end = group["TyreLife"].iloc[-1]

        stints.append(
            Stint(
                driver=driver,
                team=team,
                stint_number=int(stint_number),
                compound=compound,
                start_lap=int(group["LapNumber"].min()),
                end_lap=int(group["LapNumber"].max()),
                length=len(group),
                tyre_age_start=int(tyre_age_start) if pd.notna(tyre_age_start) else None,
                tyre_age_end=int(tyre_age_end) if pd.notna(tyre_age_end) else None,
                n_clean_laps=len(clean),
                median_pace_s=(
                    float(clean["LapTimeSeconds"].median()) if not clean.empty else None
                ),
                pace_variation_s=(
                    float(clean["LapTimeSeconds"].std(ddof=1)) if len(clean) >= 2 else None
                ),
            )
        )
    return stints


def reconstruct_all_stints(flagged_laps: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct stints for every driver in the session.

    Returns:
        A DataFrame with one row per (driver, stint), sorted by driver then
        start lap — the shape used to visualize tyre strategy across the
        grid (Milestone 7). Empty DataFrame if there are no laps with stint
        data at all.
    """
    all_stints: list[Stint] = []
    for driver in flagged_laps["Driver"].dropna().unique():
        all_stints.extend(reconstruct_driver_stints(flagged_laps, driver))

    if not all_stints:
        return pd.DataFrame()

    df = pd.DataFrame([vars(s) for s in all_stints])
    return df.sort_values(["driver", "start_lap"]).reset_index(drop=True)

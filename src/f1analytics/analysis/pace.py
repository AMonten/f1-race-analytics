"""Representative race pace and driver-vs-driver pace comparison.

Everything here is computed from *clean* laps only (see
`f1analytics.data.preprocessing`), because raw lap times mix in pit laps,
SC/VSC-affected laps and outliers that would distort a "pace" figure. All
metrics are descriptive statistics over the clean-lap sample for the
session being analyzed — they say nothing about a driver's or team's
general ability, only about how that car/driver combination performed in
this specific session, under its specific fuel loads, tyre strategy, and
traffic.

Race Pace Index
----------------
Defined as::

    RacePaceIndex = 100 * field_median_clean_lap_seconds / driver_median_clean_lap_seconds

where `field_median_clean_lap_seconds` is the median of every clean lap set
by every driver in the session (not the median of per-driver medians, so it
naturally weights drivers with more clean-lap data more heavily). A value
of 100 means the driver's median clean lap matched the field median exactly;
above 100 means faster than the field median; below 100 means slower.

This index mixes car performance, tyre strategy, fuel load, and track
position/traffic effects — it is **not** a normalized measure of driver
skill, and should not be compared across different sessions or seasons.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from f1analytics.analysis.laps import fastest_lap, get_clean_driver_laps
from f1analytics.data.preprocessing import filter_clean_laps


@dataclass
class DriverRacePace:
    """Representative race pace for one driver, computed from clean laps only."""

    driver: str
    team: str | None
    n_clean_laps: int
    median_s: float | None
    mean_s: float | None
    std_s: float | None
    fastest_representative_s: float | None
    field_median_s: float | None
    delta_to_field_median_s: float | None
    race_pace_index: float | None


@dataclass
class DriverPaceComparison:
    """Pace comparison between two drivers. Positive deltas mean `driver_a`
    was slower (median/fastest) or less consistent (std) than `driver_b`."""

    driver_a: DriverRacePace
    driver_b: DriverRacePace
    median_delta_s: float | None
    fastest_lap_delta_s: float | None
    consistency_delta_s: float | None


def _field_median_clean_lap_seconds(flagged_laps: pd.DataFrame) -> float | None:
    clean = filter_clean_laps(flagged_laps)
    if clean.empty:
        return None
    return float(clean["LapTimeSeconds"].median())


def compute_driver_race_pace(
    flagged_laps: pd.DataFrame,
    driver: str,
    field_median_s: float | None = None,
) -> DriverRacePace:
    """Compute representative race pace for one driver.

    Args:
        flagged_laps: Session laps with clean-lap flags (see
            `f1analytics.data.preprocessing.add_lap_quality_flags`).
        driver: Driver code, e.g. 'VER'.
        field_median_s: Field median clean lap time, in seconds. If `None`,
            it is computed from `flagged_laps` (pass it explicitly when
            comparing many drivers, to avoid recomputing it each time).

    Returns:
        A `DriverRacePace`. All statistics are `None` when the driver has
        zero clean laps; `std_s` is `None` with fewer than 2 clean laps
        (standard deviation is undefined for a single observation).
    """
    clean_laps = get_clean_driver_laps(flagged_laps, driver)
    n = len(clean_laps)

    team = None
    all_driver_laps = flagged_laps[flagged_laps["Driver"] == driver]
    if "Team" in all_driver_laps.columns and not all_driver_laps.empty:
        team = all_driver_laps["Team"].iloc[0]

    if field_median_s is None:
        field_median_s = _field_median_clean_lap_seconds(flagged_laps)

    if n == 0:
        return DriverRacePace(
            driver=driver,
            team=team,
            n_clean_laps=0,
            median_s=None,
            mean_s=None,
            std_s=None,
            fastest_representative_s=None,
            field_median_s=field_median_s,
            delta_to_field_median_s=None,
            race_pace_index=None,
        )

    median_s = float(clean_laps["LapTimeSeconds"].median())
    mean_s = float(clean_laps["LapTimeSeconds"].mean())
    std_s = float(clean_laps["LapTimeSeconds"].std(ddof=1)) if n >= 2 else None
    fastest_row = fastest_lap(clean_laps)
    fastest_representative_s = (
        float(fastest_row["LapTimeSeconds"]) if fastest_row is not None else None
    )

    delta_to_field_median_s = (
        median_s - field_median_s if field_median_s is not None else None
    )
    race_pace_index = (
        100.0 * field_median_s / median_s
        if field_median_s is not None and median_s > 0
        else None
    )

    return DriverRacePace(
        driver=driver,
        team=team,
        n_clean_laps=n,
        median_s=median_s,
        mean_s=mean_s,
        std_s=std_s,
        fastest_representative_s=fastest_representative_s,
        field_median_s=field_median_s,
        delta_to_field_median_s=delta_to_field_median_s,
        race_pace_index=race_pace_index,
    )


def compute_field_race_pace(flagged_laps: pd.DataFrame) -> pd.DataFrame:
    """Compute race pace for every driver in the session.

    Returns:
        A DataFrame with one row per driver (all `DriverRacePace` fields as
        columns), sorted by `median_s` ascending (fastest median first,
        drivers with no clean laps last).
    """
    field_median_s = _field_median_clean_lap_seconds(flagged_laps)
    drivers = flagged_laps["Driver"].dropna().unique().tolist()

    rows = [
        compute_driver_race_pace(flagged_laps, driver, field_median_s=field_median_s)
        for driver in drivers
    ]
    df = pd.DataFrame([vars(row) for row in rows])
    return df.sort_values("median_s", ascending=True, na_position="last").reset_index(
        drop=True
    )


def compare_driver_pace(
    flagged_laps: pd.DataFrame, driver_a: str, driver_b: str
) -> DriverPaceComparison:
    """Compare representative race pace between two drivers.

    Deltas are `driver_a - driver_b`: positive means `driver_a` was slower
    (for `median_delta_s`/`fastest_lap_delta_s`) or less consistent (higher
    lap-time standard deviation, for `consistency_delta_s`) than `driver_b`.
    Any delta involving a driver with insufficient clean-lap data is `None`
    rather than a misleading number.
    """
    field_median_s = _field_median_clean_lap_seconds(flagged_laps)
    pace_a = compute_driver_race_pace(flagged_laps, driver_a, field_median_s=field_median_s)
    pace_b = compute_driver_race_pace(flagged_laps, driver_b, field_median_s=field_median_s)

    def _delta(a: float | None, b: float | None) -> float | None:
        return a - b if a is not None and b is not None else None

    return DriverPaceComparison(
        driver_a=pace_a,
        driver_b=pace_b,
        median_delta_s=_delta(pace_a.median_s, pace_b.median_s),
        fastest_lap_delta_s=_delta(
            pace_a.fastest_representative_s, pace_b.fastest_representative_s
        ),
        consistency_delta_s=_delta(pace_a.std_s, pace_b.std_s),
    )

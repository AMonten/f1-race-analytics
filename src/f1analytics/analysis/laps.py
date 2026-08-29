"""Lap-level analytical helpers built on top of the clean-lap flags.

Every function here expects a laps DataFrame that has already been through
`f1analytics.data.preprocessing.add_lap_quality_flags` (i.e. it has
`LapTimeSeconds` and `IsCleanLap` columns). This module doesn't know about
FastF1 — it only works with the flagged DataFrame shape.
"""

from __future__ import annotations

import pandas as pd


class UnknownDriverError(ValueError):
    """Raised when a requested driver code doesn't appear in the laps table."""


def get_driver_laps(flagged_laps: pd.DataFrame, driver: str) -> pd.DataFrame:
    """Return all laps (clean or not) for a single driver.

    Args:
        flagged_laps: Output of `add_lap_quality_flags`.
        driver: Driver code as it appears in the `Driver` column (e.g. 'VER').

    Raises:
        UnknownDriverError: If `driver` never appears in `flagged_laps`, which
            usually means a typo rather than a driver with zero laps (a
            driver who started but retired lap 1 still has a `Driver` entry).
    """
    if driver not in flagged_laps["Driver"].unique():
        known = sorted(flagged_laps["Driver"].dropna().unique().tolist())
        raise UnknownDriverError(f"Unknown driver {driver!r}. Known drivers: {known}")
    return flagged_laps[flagged_laps["Driver"] == driver].copy()


def get_clean_driver_laps(flagged_laps: pd.DataFrame, driver: str) -> pd.DataFrame:
    """Return only the laps flagged `IsCleanLap` for a single driver."""
    driver_laps = get_driver_laps(flagged_laps, driver)
    return driver_laps[driver_laps["IsCleanLap"]].copy()


def fastest_lap(laps: pd.DataFrame) -> pd.Series | None:
    """Return the row with the lowest `LapTimeSeconds` in `laps`, or `None` if empty.

    Callers decide which population to search: pass clean laps for a
    "fastest representative lap", or all laps for the outright fastest lap
    of the session (which may have been set under conditions the clean-lap
    methodology excludes, e.g. immediately before a red flag).
    """
    valid = laps[laps["LapTimeSeconds"].notna()]
    if valid.empty:
        return None
    return valid.loc[valid["LapTimeSeconds"].idxmin()]

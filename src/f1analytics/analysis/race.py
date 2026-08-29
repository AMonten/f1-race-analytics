"""Race-level (not single-driver) reconstructions: position evolution and
track-status incident periods.

These feed the Race Position Evolution chart (Milestone 7): a lap-by-driver
position grid, plus the lap ranges during which each non-green track status
(yellow flag, Safety Car, Virtual Safety Car, red flag) was active anywhere
in the field, so the chart can annotate SC/VSC periods.
"""

from __future__ import annotations

import pandas as pd

from f1analytics.config import TRACK_STATUS_LABELS


def get_position_by_lap(laps: pd.DataFrame) -> pd.DataFrame:
    """Pivot a session's laps into a lap-number x driver grid of race position.

    Args:
        laps: A session's lap table (raw `session.laps`, or the clean-lap
            flagged version — only `LapNumber`, `Driver`, and `Position`
            are read).

    Returns:
        A DataFrame indexed by `LapNumber`, one column per driver. Values
        are classification position at the end of that lap; `NaN` where a
        driver has no data for that lap (e.g. after retiring).
    """
    pivot = laps.pivot_table(index="LapNumber", columns="Driver", values="Position")
    return pivot.sort_index()


def _contiguous_ranges(values: list[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    ranges: list[tuple[int, int]] = []
    start = prev = values[0]
    for v in values[1:]:
        if v == prev + 1:
            prev = v
        else:
            ranges.append((start, prev))
            start = prev = v
    ranges.append((start, prev))
    return ranges


def get_track_status_periods(laps: pd.DataFrame) -> pd.DataFrame:
    """Detect contiguous lap ranges under each non-green track status.

    For a given lap number, a status code is considered "active" if it
    appears in *any* driver's `TrackStatus` string for that lap — using
    this field-wide union rather than trusting a single driver's record is
    more robust to per-driver timing lag around status changes.

    Green ('1') is excluded; this function only reports incident periods.
    Different codes can legitimately overlap the same lap range (a Safety
    Car period is typically preceded by a lap flagged Yellow).

    Returns:
        A DataFrame with one row per contiguous period: `status_code`,
        `status_label`, `start_lap`, `end_lap`. Empty (but correctly
        columned) if the session had no incidents.
    """
    valid = laps.dropna(subset=["LapNumber"])
    per_lap_codes = valid.groupby("LapNumber")["TrackStatus"].apply(
        lambda statuses: set("".join(s for s in statuses if isinstance(s, str)))
    )

    records = []
    for code, label in TRACK_STATUS_LABELS.items():
        if code == "1":
            continue
        active_laps = sorted(int(lap) for lap, codes in per_lap_codes.items() if code in codes)
        for start, end in _contiguous_ranges(active_laps):
            records.append(
                {"status_code": code, "status_label": label, "start_lap": start, "end_lap": end}
            )

    if not records:
        return pd.DataFrame(columns=["status_code", "status_label", "start_lap", "end_lap"])
    return pd.DataFrame(records).sort_values("start_lap").reset_index(drop=True)

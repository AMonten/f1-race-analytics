"""Qualifying classification, Q1/Q2/Q3 progression, and lap-vs-lap comparison.

Uses a deliberately different "valid lap" filter than the rest of the
project's race-pace analysis (see `f1analytics.data.preprocessing`): a
qualifying lap is valid if it has a recorded time, isn't a pit in/out lap,
wasn't deleted by stewards, and is flagged `IsAccurate` by FastF1 — but,
unlike race pace, an unusually **fast** lap is never excluded as a
"statistical outlier". Setting an exceptional lap is the entire point of
qualifying; `IsCleanLap` from the race-pace methodology would wrongly
penalize exactly that.

Functions here expect a laps DataFrame that has already been through
`f1analytics.data.preprocessing.add_lap_quality_flags` (for `IsPitLap`,
`IsDeleted`, `IsAccurate`, `LapTimeSeconds`). For Q1/Q2/Q3 splitting, it
must additionally have a `QualifyingSegment` column — merge in the result
of `f1analytics.data.loader.get_qualifying_segment_labels(session)` first.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def _timedelta_to_seconds(value: object) -> float:
    if isinstance(value, pd.Timedelta) and pd.notna(value):
        return value.total_seconds()
    return float("nan")


def is_valid_qualifying_lap(laps: pd.DataFrame) -> pd.Series:
    """Boolean mask: laps usable for qualifying pace.

    Timed, not a pit lap, not deleted, and FastF1-accurate. Deliberately
    does **not** exclude statistical outliers (see module docstring).
    """
    return (
        laps["LapTimeSeconds"].notna()
        & ~laps["IsPitLap"]
        & ~laps["IsDeleted"]
        & laps["IsAccurate"]
    )


def get_driver_best_lap(
    laps: pd.DataFrame, driver: str, segment: str | None = None
) -> pd.Series | None:
    """Return `driver`'s fastest valid lap, optionally restricted to one segment.

    Args:
        laps: Flagged laps (see module docstring), optionally with a
            `QualifyingSegment` column.
        driver: Driver code, e.g. 'VER'.
        segment: One of 'Q1'/'Q2'/'Q3' to restrict to that segment, or
            `None` for the whole session (e.g. Sprint Shootout sessions,
            which aren't split the same way).

    Returns:
        The best lap as a `pandas.Series`, or `None` if the driver has no
        valid lap (in that segment, if given).
    """
    driver_laps = laps[laps["Driver"] == driver]
    if segment is not None:
        driver_laps = driver_laps[driver_laps["QualifyingSegment"] == segment]
    valid = driver_laps[is_valid_qualifying_lap(driver_laps)]
    if valid.empty:
        return None
    return valid.loc[valid["LapTimeSeconds"].idxmin()]


def compute_qualifying_classification(
    laps: pd.DataFrame, segment: str | None = None
) -> pd.DataFrame:
    """Build a qualifying classification: one row per driver, fastest first.

    Args:
        laps: Flagged laps, as above.
        segment: Restrict to one of 'Q1'/'Q2'/'Q3', or `None` for the whole
            session.

    Returns:
        A DataFrame with `driver`, `team`, `best_lap_time_s`, `sector1_s`,
        `sector2_s`, `sector3_s`, `n_valid_laps`, and `gap_to_pole_s`
        (difference to the fastest driver's `best_lap_time_s`; `NaN` for
        a driver with no valid lap). Sorted by `best_lap_time_s` ascending,
        drivers with no valid lap last.
    """
    rows = []
    for driver in laps["Driver"].dropna().unique():
        all_driver_laps = laps[laps["Driver"] == driver]
        driver_laps = (
            all_driver_laps[all_driver_laps["QualifyingSegment"] == segment]
            if segment is not None
            else all_driver_laps
        )

        best = get_driver_best_lap(laps, driver, segment=segment)
        team = (
            all_driver_laps["Team"].iloc[0]
            if "Team" in all_driver_laps.columns and not all_driver_laps.empty
            else None
        )
        n_valid = int(is_valid_qualifying_lap(driver_laps).sum()) if not driver_laps.empty else 0

        rows.append(
            {
                "driver": driver,
                "team": team,
                "best_lap_time_s": float(best["LapTimeSeconds"]) if best is not None else float("nan"),
                "sector1_s": _timedelta_to_seconds(best.get("Sector1Time")) if best is not None else float("nan"),
                "sector2_s": _timedelta_to_seconds(best.get("Sector2Time")) if best is not None else float("nan"),
                "sector3_s": _timedelta_to_seconds(best.get("Sector3Time")) if best is not None else float("nan"),
                "n_valid_laps": n_valid,
            }
        )

    df = pd.DataFrame(rows).sort_values(
        "best_lap_time_s", ascending=True, na_position="last"
    ).reset_index(drop=True)

    pole_time = None
    if not df.empty and pd.notna(df["best_lap_time_s"].iloc[0]):
        pole_time = df["best_lap_time_s"].iloc[0]
    df["gap_to_pole_s"] = (
        df["best_lap_time_s"] - pole_time if pole_time is not None else float("nan")
    )
    return df


def get_segment_progression(laps: pd.DataFrame) -> pd.DataFrame:
    """Best lap time per driver, per Q1/Q2/Q3 segment.

    Requires a `QualifyingSegment` column (see module docstring). Rows
    where `QualifyingSegment` is never set for a segment (that segment was
    cancelled) are simply absent from the result.

    Returns:
        The concatenation of `compute_qualifying_classification(laps,
        segment=s)` for each segment `s` that has data, with a `segment`
        column added. Empty DataFrame if no segment has any laps.
    """
    if "QualifyingSegment" not in laps.columns:
        raise KeyError(
            "get_segment_progression requires a QualifyingSegment column "
            "(see f1analytics.data.loader.get_qualifying_segment_labels)"
        )

    frames = []
    for segment in ("Q1", "Q2", "Q3"):
        if not (laps["QualifyingSegment"] == segment).any():
            continue
        classification = compute_qualifying_classification(laps, segment=segment)
        classification["segment"] = segment
        frames.append(classification)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def compare_teammates(laps: pd.DataFrame, segment: str | None = None) -> pd.DataFrame:
    """Pairwise teammate best-lap comparison.

    Only teams with exactly two drivers present in `laps` are included —
    a mid-season replacement, a single-car entry, or a data gap is skipped
    rather than guessed at.

    Returns:
        A DataFrame with `team`, `driver_a`, `driver_a_best_s`, `driver_b`,
        `driver_b_best_s`, `delta_s` (`driver_a - driver_b`; `None` if
        either driver has no valid lap). `driver_a`/`driver_b` are ordered
        alphabetically by driver code, not by who was faster.
    """
    classification = compute_qualifying_classification(laps, segment=segment)
    rows = []
    for team, group in classification.groupby("team"):
        if team is None or len(group) != 2:
            continue
        a, b = group.sort_values("driver").to_dict("records")
        delta = (
            a["best_lap_time_s"] - b["best_lap_time_s"]
            if a["best_lap_time_s"] is not None and b["best_lap_time_s"] is not None
            else None
        )
        rows.append(
            {
                "team": team,
                "driver_a": a["driver"],
                "driver_a_best_s": a["best_lap_time_s"],
                "driver_b": b["driver"],
                "driver_b_best_s": b["best_lap_time_s"],
                "delta_s": delta,
            }
        )
    return pd.DataFrame(rows)


@dataclass
class LapComparison:
    """Detailed comparison between two individual laps. Deltas are `a - b`."""

    driver_a: str | None
    driver_b: str | None
    lap_time_delta_s: float | None
    sector1_delta_s: float | None
    sector2_delta_s: float | None
    sector3_delta_s: float | None


def compare_two_laps(lap_a: pd.Series, lap_b: pd.Series) -> LapComparison:
    """Compare two individual laps (e.g. two drivers' best laps, or one
    driver's laps from two different segments).

    Deltas are `lap_a - lap_b`; positive means `lap_a` was slower.
    """

    def _delta(column: str) -> float | None:
        a = lap_a.get(column)
        b = lap_b.get(column)
        a_s = a.total_seconds() if isinstance(a, pd.Timedelta) else a
        b_s = b.total_seconds() if isinstance(b, pd.Timedelta) else b
        if a_s is None or b_s is None or pd.isna(a_s) or pd.isna(b_s):
            return None
        return float(a_s - b_s)

    return LapComparison(
        driver_a=lap_a.get("Driver"),
        driver_b=lap_b.get("Driver"),
        lap_time_delta_s=_delta("LapTimeSeconds"),
        sector1_delta_s=_delta("Sector1Time"),
        sector2_delta_s=_delta("Sector2Time"),
        sector3_delta_s=_delta("Sector3Time"),
    )

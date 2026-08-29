"""Tests for the clean-lap methodology in f1analytics.data.preprocessing."""

from __future__ import annotations

import pandas as pd
import pytest

from f1analytics.data.preprocessing import add_lap_quality_flags, filter_clean_laps


def _lap(
    driver="VER",
    stint=1.0,
    lap_number=1,
    seconds=90.0,
    pit_in=False,
    pit_out=False,
    track_status="1",
    deleted=None,
    accurate=True,
):
    return {
        "Driver": driver,
        "Stint": stint,
        "LapNumber": lap_number,
        "LapTime": pd.Timedelta(seconds=seconds) if seconds is not None else pd.NaT,
        "PitInTime": pd.Timedelta(seconds=1) if pit_in else pd.NaT,
        "PitOutTime": pd.Timedelta(seconds=1) if pit_out else pd.NaT,
        "TrackStatus": track_status,
        "Deleted": deleted,
        "IsAccurate": accurate,
    }


def _laps_df(rows):
    df = pd.DataFrame(rows)
    for col in ("LapTime", "PitInTime", "PitOutTime"):
        # Explicit dtype avoids pandas inferring an all-NaT column as
        # datetime64 instead of timedelta64 (which real FastF1 lap tables
        # never produce, since these columns always carry Timedelta dtype).
        df[col] = pd.array([r[col] for r in rows], dtype="timedelta64[ns]")
    return df


def test_pit_in_and_out_laps_are_excluded():
    laps = _laps_df(
        [
            _lap(lap_number=1, pit_out=True, seconds=95.0),
            _lap(lap_number=2, seconds=90.0),
            _lap(lap_number=3, pit_in=True, seconds=93.0),
        ]
    )
    flagged = add_lap_quality_flags(laps)

    assert flagged.loc[0, "IsPitLap"] and not flagged.loc[0, "IsCleanLap"]
    assert flagged.loc[2, "IsPitLap"] and not flagged.loc[2, "IsCleanLap"]
    assert flagged.loc[1, "IsCleanLap"]


def test_missing_track_status_is_treated_as_not_clean():
    laps = _laps_df(
        [
            _lap(lap_number=1, track_status=float("nan"), seconds=90.0),
            _lap(lap_number=2, track_status="", seconds=90.0),
        ]
    )
    flagged = add_lap_quality_flags(laps)

    assert not flagged.loc[0, "IsTrackStatusClean"]
    assert not flagged.loc[1, "IsTrackStatusClean"]


def test_non_green_track_status_excludes_lap_even_if_only_partially_affected():
    laps = _laps_df(
        [
            _lap(lap_number=1, track_status="1", seconds=90.0),
            _lap(lap_number=2, track_status="126", seconds=110.0),  # green->yellow->SC
            _lap(lap_number=3, track_status="1", seconds=90.5),
        ]
    )
    flagged = add_lap_quality_flags(laps)

    assert not flagged.loc[1, "IsTrackStatusClean"]
    assert not flagged.loc[1, "IsCleanLap"]
    assert flagged.loc[0, "IsCleanLap"] and flagged.loc[2, "IsCleanLap"]


def test_deleted_lap_is_excluded():
    laps = _laps_df(
        [
            _lap(lap_number=1, seconds=88.0, deleted=True),
            _lap(lap_number=2, seconds=90.0, deleted=False),
        ]
    )
    flagged = add_lap_quality_flags(laps)

    assert not flagged.loc[0, "IsCleanLap"]
    assert flagged.loc[1, "IsCleanLap"]


def test_inaccurate_lap_is_excluded():
    laps = _laps_df(
        [
            _lap(lap_number=1, seconds=90.0, accurate=False),
            _lap(lap_number=2, seconds=90.5, accurate=True),
        ]
    )
    flagged = add_lap_quality_flags(laps)

    assert not flagged.loc[0, "IsCleanLap"]
    assert flagged.loc[1, "IsCleanLap"]


def test_missing_lap_time_is_excluded_without_crashing():
    laps = _laps_df([_lap(lap_number=1, seconds=None)])
    flagged = add_lap_quality_flags(laps)

    assert flagged.loc[0, "LapTimeSeconds"] != flagged.loc[0, "LapTimeSeconds"]  # NaN
    assert not flagged.loc[0, "IsCleanLap"]


def test_statistical_outlier_is_flagged_and_excluded():
    consistent = [_lap(lap_number=i, seconds=90.0 + (i % 2) * 0.1) for i in range(1, 8)]
    outlier = _lap(lap_number=8, seconds=105.0)  # ~15s slower, e.g. traffic/lockup
    laps = _laps_df(consistent + [outlier])

    flagged = add_lap_quality_flags(laps)

    assert flagged.iloc[-1]["IsStatisticalOutlier"]
    assert not flagged.iloc[-1]["IsCleanLap"]
    assert flagged.iloc[:-1]["IsCleanLap"].all()


def test_outlier_baseline_is_scoped_per_driver_and_stint():
    stint_1 = [_lap(stint=1.0, lap_number=i, seconds=90.0) for i in range(1, 5)]
    stint_2 = [_lap(stint=2.0, lap_number=i, seconds=93.0) for i in range(5, 9)]
    laps = _laps_df(stint_1 + stint_2)

    flagged = add_lap_quality_flags(laps)

    # Different tyre/fuel baseline per stint should not cause cross-stint
    # laps to look like outliers relative to each other.
    assert flagged["IsCleanLap"].all()


def test_fewer_than_two_candidates_in_group_skips_outlier_check():
    laps = _laps_df([_lap(lap_number=1, seconds=90.0)])
    flagged = add_lap_quality_flags(laps)

    assert not flagged.loc[0, "IsStatisticalOutlier"]
    assert flagged.loc[0, "IsCleanLap"]


def test_add_lap_quality_flags_does_not_mutate_input():
    laps = _laps_df([_lap(lap_number=1, seconds=90.0)])
    original_columns = list(laps.columns)

    add_lap_quality_flags(laps)

    assert list(laps.columns) == original_columns


def test_filter_clean_laps_returns_only_flagged_rows():
    laps = _laps_df(
        [
            _lap(lap_number=1, seconds=90.0),
            _lap(lap_number=2, pit_out=True, seconds=95.0),
        ]
    )
    flagged = add_lap_quality_flags(laps)

    clean = filter_clean_laps(flagged)

    assert len(clean) == 1
    assert clean.iloc[0]["LapNumber"] == 1


def test_filter_clean_laps_requires_flags_first():
    laps = _laps_df([_lap(lap_number=1, seconds=90.0)])

    with pytest.raises(KeyError):
        filter_clean_laps(laps)

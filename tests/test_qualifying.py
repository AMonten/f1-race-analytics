"""Tests for f1analytics.analysis.qualifying."""

from __future__ import annotations

import pandas as pd
import pytest

from f1analytics.analysis.qualifying import (
    compare_teammates,
    compare_two_laps,
    compute_qualifying_classification,
    get_driver_best_lap,
    get_segment_progression,
    is_valid_qualifying_lap,
)


def _lap(
    driver,
    team,
    segment,
    seconds,
    s1=30.0,
    s2=30.0,
    s3=30.0,
    pit=False,
    deleted=False,
    accurate=True,
):
    return {
        "Driver": driver,
        "Team": team,
        "QualifyingSegment": segment,
        "LapTimeSeconds": seconds,
        "Sector1Time": pd.Timedelta(seconds=s1) if seconds is not None else pd.NaT,
        "Sector2Time": pd.Timedelta(seconds=s2) if seconds is not None else pd.NaT,
        "Sector3Time": pd.Timedelta(seconds=s3) if seconds is not None else pd.NaT,
        "IsPitLap": pit,
        "IsDeleted": deleted,
        "IsAccurate": accurate,
    }


def _laps_df(rows):
    df = pd.DataFrame(rows)
    for col in ("Sector1Time", "Sector2Time", "Sector3Time"):
        df[col] = pd.to_timedelta(df[col])
    return df


def _basic_session():
    return _laps_df(
        [
            _lap("VER", "Red Bull", "Q3", 90.5, s1=30.1, s2=30.2, s3=30.2),
            _lap("VER", "Red Bull", "Q3", 91.0),
            _lap("PER", "Red Bull", "Q3", 90.9, s1=30.3, s2=30.3, s3=30.3),
            _lap("LEC", "Ferrari", "Q2", 91.5),
            _lap("SAI", "Ferrari", "Q2", 91.8),
            _lap("HAM", "Mercedes", "Q1", 92.0, pit=True),  # pit lap, excluded
            _lap("HAM", "Mercedes", "Q1", 91.9, deleted=True),  # deleted, excluded
        ]
    )


def test_is_valid_qualifying_lap_excludes_pit_deleted_inaccurate():
    laps = _laps_df(
        [
            _lap("A", "T", "Q1", 90.0),
            _lap("A", "T", "Q1", 90.0, pit=True),
            _lap("A", "T", "Q1", 90.0, deleted=True),
            _lap("A", "T", "Q1", 90.0, accurate=False),
        ]
    )
    mask = is_valid_qualifying_lap(laps)
    assert mask.tolist() == [True, False, False, False]


def test_is_valid_qualifying_lap_does_not_exclude_fast_outlier():
    # A lap far faster than the driver's others must NOT be excluded here
    # (unlike the race clean-lap methodology).
    laps = _laps_df([_lap("A", "T", "Q1", 95.0), _lap("A", "T", "Q1", 80.0)])
    assert is_valid_qualifying_lap(laps).all()


def test_get_driver_best_lap_picks_minimum_valid_time():
    laps = _basic_session()
    best = get_driver_best_lap(laps, "VER")
    assert best["LapTimeSeconds"] == 90.5


def test_get_driver_best_lap_restricted_to_segment():
    laps = _basic_session()
    best = get_driver_best_lap(laps, "VER", segment="Q3")
    assert best is not None
    best_q1 = get_driver_best_lap(laps, "VER", segment="Q1")
    assert best_q1 is None


def test_get_driver_best_lap_none_when_only_invalid_laps():
    laps = _basic_session()
    best = get_driver_best_lap(laps, "HAM")
    assert best is None


def test_compute_qualifying_classification_sorted_with_gap_to_pole():
    laps = _basic_session()
    classification = compute_qualifying_classification(laps)

    assert classification.iloc[0]["driver"] == "VER"
    assert classification.iloc[0]["gap_to_pole_s"] == 0.0
    per_row = classification[classification["driver"] == "PER"].iloc[0]
    assert per_row["gap_to_pole_s"] == pytest.approx(90.9 - 90.5)

    ham_row = classification[classification["driver"] == "HAM"].iloc[0]
    assert pd.isna(ham_row["best_lap_time_s"])
    assert pd.isna(ham_row["gap_to_pole_s"])


def test_compute_qualifying_classification_sector_times():
    laps = _basic_session()
    classification = compute_qualifying_classification(laps)
    ver_row = classification[classification["driver"] == "VER"].iloc[0]
    assert ver_row["sector1_s"] == pytest.approx(30.1)


def test_get_segment_progression_covers_present_segments():
    laps = _basic_session()
    progression = get_segment_progression(laps)

    assert set(progression["segment"]) == {"Q1", "Q2", "Q3"}


def test_get_segment_progression_requires_segment_column():
    laps = _basic_session().drop(columns=["QualifyingSegment"])
    with pytest.raises(KeyError):
        get_segment_progression(laps)


def test_get_segment_progression_empty_when_no_segment_has_data():
    laps = _basic_session()
    laps["QualifyingSegment"] = None
    assert get_segment_progression(laps).empty


def test_compare_teammates_only_pairs_of_two():
    laps = _basic_session()
    comparison = compare_teammates(laps)

    teams = set(comparison["team"])
    assert "Red Bull" in teams
    assert "Ferrari" in teams
    assert "Mercedes" not in teams  # only one Mercedes driver in this fixture

    rb_row = comparison[comparison["team"] == "Red Bull"].iloc[0]
    assert rb_row["driver_a"] == "PER"
    assert rb_row["driver_b"] == "VER"
    assert rb_row["delta_s"] == pytest.approx(90.9 - 90.5)  # driver_a (PER) - driver_b (VER)


def test_compare_two_laps_deltas():
    laps = _basic_session()
    ver_lap = get_driver_best_lap(laps, "VER")
    per_lap = get_driver_best_lap(laps, "PER")

    comparison = compare_two_laps(ver_lap, per_lap)

    assert comparison.driver_a == "VER"
    assert comparison.driver_b == "PER"
    assert comparison.lap_time_delta_s == pytest.approx(90.5 - 90.9)
    assert comparison.sector1_delta_s == pytest.approx(30.1 - 30.3)

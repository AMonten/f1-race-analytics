"""Tests for f1analytics.analysis.race (position evolution, track-status periods)."""

from __future__ import annotations

import pandas as pd

from f1analytics.analysis.race import get_position_by_lap, get_track_status_periods


def test_get_position_by_lap_pivots_lap_by_driver():
    laps = pd.DataFrame(
        {
            "LapNumber": [1, 1, 2, 2],
            "Driver": ["VER", "HAM", "VER", "HAM"],
            "Position": [1.0, 2.0, 2.0, 1.0],
        }
    )
    grid = get_position_by_lap(laps)

    assert grid.loc[1, "VER"] == 1.0
    assert grid.loc[1, "HAM"] == 2.0
    assert grid.loc[2, "VER"] == 2.0
    assert grid.loc[2, "HAM"] == 1.0


def test_get_position_by_lap_handles_missing_driver_data():
    laps = pd.DataFrame(
        {
            "LapNumber": [1, 2],
            "Driver": ["VER", "VER"],
            "Position": [1.0, 1.0],
        }
    )
    grid = get_position_by_lap(laps)
    assert list(grid.columns) == ["VER"]


def _status_laps(rows):
    return pd.DataFrame(rows)


def test_get_track_status_periods_excludes_green_and_detects_range():
    rows = [
        {"LapNumber": 1, "TrackStatus": "1"},
        {"LapNumber": 2, "TrackStatus": "12"},
        {"LapNumber": 3, "TrackStatus": "24"},
        {"LapNumber": 4, "TrackStatus": "4"},
        {"LapNumber": 5, "TrackStatus": "41"},
        {"LapNumber": 6, "TrackStatus": "1"},
    ]
    periods = get_track_status_periods(_status_laps(rows))

    sc_periods = periods[periods["status_code"] == "4"]
    assert len(sc_periods) == 1
    assert sc_periods.iloc[0]["start_lap"] == 3
    assert sc_periods.iloc[0]["end_lap"] == 5

    yellow_periods = periods[periods["status_code"] == "2"]
    assert len(yellow_periods) == 1
    assert yellow_periods.iloc[0]["start_lap"] == 2
    assert yellow_periods.iloc[0]["end_lap"] == 3

    assert "1" not in periods["status_code"].values


def test_get_track_status_periods_union_across_drivers():
    # Only one of two drivers records the yellow flag on lap 2 (timing lag);
    # the field-wide union should still catch it.
    rows = [
        {"LapNumber": 1, "TrackStatus": "1"},
        {"LapNumber": 2, "TrackStatus": "2"},
        {"LapNumber": 2, "TrackStatus": "1"},
    ]
    periods = get_track_status_periods(_status_laps(rows))

    assert len(periods) == 1
    assert periods.iloc[0]["status_code"] == "2"
    assert periods.iloc[0]["start_lap"] == 2
    assert periods.iloc[0]["end_lap"] == 2


def test_get_track_status_periods_empty_when_all_green():
    rows = [{"LapNumber": i, "TrackStatus": "1"} for i in range(1, 4)]
    periods = get_track_status_periods(_status_laps(rows))

    assert periods.empty
    assert list(periods.columns) == ["status_code", "status_label", "start_lap", "end_lap"]


def test_get_track_status_periods_separates_non_contiguous_ranges():
    rows = [
        {"LapNumber": 1, "TrackStatus": "1"},
        {"LapNumber": 2, "TrackStatus": "6"},
        {"LapNumber": 3, "TrackStatus": "1"},
        {"LapNumber": 4, "TrackStatus": "6"},
    ]
    periods = get_track_status_periods(_status_laps(rows))
    vsc_periods = periods[periods["status_code"] == "6"]

    assert len(vsc_periods) == 2
    assert set(zip(vsc_periods["start_lap"], vsc_periods["end_lap"])) == {(2, 2), (4, 4)}

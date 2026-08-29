"""Tests for f1analytics.analysis.laps."""

from __future__ import annotations

import pandas as pd
import pytest

from f1analytics.analysis.laps import UnknownDriverError, fastest_lap, get_clean_driver_laps, get_driver_laps


def _flagged_laps():
    return pd.DataFrame(
        {
            "Driver": ["VER", "VER", "VER", "HAM", "HAM"],
            "LapNumber": [1, 2, 3, 1, 2],
            "LapTimeSeconds": [90.0, 89.5, 95.0, 91.0, float("nan")],
            "IsCleanLap": [True, True, False, True, False],
        }
    )


def test_get_driver_laps_returns_only_that_driver():
    laps = get_driver_laps(_flagged_laps(), "VER")
    assert set(laps["Driver"]) == {"VER"}
    assert len(laps) == 3


def test_get_driver_laps_unknown_driver_raises():
    with pytest.raises(UnknownDriverError):
        get_driver_laps(_flagged_laps(), "XXX")


def test_get_clean_driver_laps_filters_is_clean():
    laps = get_clean_driver_laps(_flagged_laps(), "VER")
    assert len(laps) == 2
    assert laps["IsCleanLap"].all()


def test_fastest_lap_returns_min_row():
    row = fastest_lap(_flagged_laps())
    assert row["Driver"] == "VER"
    assert row["LapTimeSeconds"] == 89.5


def test_fastest_lap_ignores_nan_lap_times():
    row = fastest_lap(_flagged_laps()[_flagged_laps()["Driver"] == "HAM"])
    assert row["LapTimeSeconds"] == 91.0


def test_fastest_lap_returns_none_when_empty():
    empty = _flagged_laps().iloc[0:0]
    assert fastest_lap(empty) is None

"""Tests for f1analytics.analysis.pace."""

from __future__ import annotations

import pandas as pd
import pytest

from f1analytics.analysis.pace import (
    compare_driver_pace,
    compute_driver_race_pace,
    compute_field_race_pace,
)


def _lap(driver, team, seconds, clean=True):
    return {"Driver": driver, "Team": team, "LapTimeSeconds": seconds, "IsCleanLap": clean}


def _flagged_laps():
    rows = []
    # VER: consistent, fast — clean median 90.0s
    rows += [_lap("VER", "Red Bull Racing", s) for s in [90.0, 89.5, 90.5, 89.8, 90.2]]
    rows.append(_lap("VER", "Red Bull Racing", 110.0, clean=False))  # pit lap, excluded
    # HAM: slower, less consistent — clean median 92.0s
    rows += [_lap("HAM", "Mercedes", s) for s in [91.0, 93.0, 90.0, 94.0, 92.0]]
    # SAR: no clean laps at all
    rows += [_lap("SAR", "Williams", 130.0, clean=False)]
    return pd.DataFrame(rows)


def test_compute_driver_race_pace_field_median_none_when_no_one_has_clean_laps():
    laps = pd.DataFrame([_lap("VER", "Red Bull Racing", 110.0, clean=False), _lap("HAM", "Mercedes", 120.0, clean=False)])

    pace = compute_driver_race_pace(laps, "VER")

    assert pace.field_median_s is None
    assert pace.race_pace_index is None
    assert pace.delta_to_field_median_s is None


def test_compute_driver_race_pace_basic_stats():
    pace = compute_driver_race_pace(_flagged_laps(), "VER")

    assert pace.n_clean_laps == 5
    assert pace.median_s == 90.0
    assert pace.team == "Red Bull Racing"
    assert pace.std_s is not None
    assert pace.fastest_representative_s == 89.5


def test_compute_driver_race_pace_zero_clean_laps_returns_none_stats():
    pace = compute_driver_race_pace(_flagged_laps(), "SAR")

    assert pace.n_clean_laps == 0
    assert pace.median_s is None
    assert pace.std_s is None
    assert pace.fastest_representative_s is None
    # field_median_s should still be populated for context
    assert pace.field_median_s is not None


def test_compute_driver_race_pace_single_clean_lap_std_is_none():
    laps = pd.DataFrame([_lap("PIA", "McLaren", 95.0)])
    pace = compute_driver_race_pace(laps, "PIA")

    assert pace.n_clean_laps == 1
    assert pace.median_s == 95.0
    assert pace.std_s is None


def test_race_pace_index_100_when_driver_matches_field_median():
    laps = pd.DataFrame(
        [_lap("A", "T1", 90.0), _lap("A", "T1", 90.0), _lap("B", "T2", 90.0), _lap("B", "T2", 90.0)]
    )
    pace = compute_driver_race_pace(laps, "A")

    assert pace.race_pace_index == pytest.approx(100.0)


def test_race_pace_index_above_100_for_faster_than_field_driver():
    pace = compute_driver_race_pace(_flagged_laps(), "VER")
    assert pace.race_pace_index > 100.0


def test_compute_field_race_pace_sorted_fastest_first_and_no_clean_laps_last():
    field = compute_field_race_pace(_flagged_laps())

    assert list(field["driver"])[:2] == ["VER", "HAM"]
    assert field.iloc[-1]["driver"] == "SAR"
    assert pd.isna(field.iloc[-1]["median_s"])


def test_compare_driver_pace_delta_signs():
    comparison = compare_driver_pace(_flagged_laps(), "HAM", "VER")

    # HAM (driver_a) is slower and less consistent than VER (driver_b) here.
    assert comparison.median_delta_s > 0
    assert comparison.fastest_lap_delta_s > 0
    assert comparison.consistency_delta_s > 0


def test_compare_driver_pace_none_when_missing_data():
    comparison = compare_driver_pace(_flagged_laps(), "SAR", "VER")

    assert comparison.median_delta_s is None
    assert comparison.fastest_lap_delta_s is None
    assert comparison.consistency_delta_s is None
    assert comparison.driver_a.n_clean_laps == 0

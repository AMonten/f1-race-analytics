"""Tests for f1analytics.analysis.tyres (degradation-per-stint wrapper)."""

from __future__ import annotations

import pandas as pd

from f1analytics.analysis.tyres import (
    compute_driver_degradation,
    compute_field_degradation,
    compute_stint_degradation,
)


def _lap(driver, lap_number, stint, compound, tyre_life, seconds, clean=True):
    return {
        "Driver": driver,
        "Team": "Red Bull Racing",
        "LapNumber": lap_number,
        "Stint": stint,
        "Compound": compound,
        "TyreLife": tyre_life,
        "LapTimeSeconds": seconds,
        "IsCleanLap": clean,
    }


def _degrading_stint_laps(driver="VER", stint=1.0, compound="MEDIUM", n=8):
    return [
        _lap(driver, i, stint, compound, tyre_life=i, seconds=90.0 + 0.1 * i)
        for i in range(1, n + 1)
    ]


def test_compute_stint_degradation_uses_only_clean_laps_of_that_stint():
    rows = _degrading_stint_laps()
    rows.append(_lap("VER", 9, stint=1.0, compound="MEDIUM", tyre_life=9, seconds=130.0, clean=False))
    laps = pd.DataFrame(rows)

    result = compute_stint_degradation(laps, "VER", 1)

    assert result.driver == "VER"
    assert result.compound == "MEDIUM"
    assert result.fit.n_observations == 8  # the dirty lap is excluded
    assert result.fit.slope_s_per_lap is not None
    assert result.fit.warning is None


def test_compute_stint_degradation_flags_low_sample_size():
    laps = pd.DataFrame(_degrading_stint_laps(n=3))

    result = compute_stint_degradation(laps, "VER", 1)

    assert result.fit.warning == "low_sample_size"


def test_compute_driver_degradation_returns_one_result_per_stint():
    stint_1 = _degrading_stint_laps(stint=1.0, compound="SOFT")
    stint_2 = _degrading_stint_laps(stint=2.0, compound="HARD")
    for row in stint_2:
        row["LapNumber"] += 100  # keep lap numbers distinct across stints
    laps = pd.DataFrame(stint_1 + stint_2)

    results = compute_driver_degradation(laps, "VER")

    assert len(results) == 2
    assert {r.compound for r in results} == {"SOFT", "HARD"}


def test_compute_field_degradation_covers_all_drivers():
    ver_laps = _degrading_stint_laps(driver="VER")
    ham_laps = _degrading_stint_laps(driver="HAM")
    for row in ham_laps:
        row["Driver"] = "HAM"
    laps = pd.DataFrame(ver_laps + ham_laps)

    df = compute_field_degradation(laps)

    assert set(df["driver"]) == {"VER", "HAM"}
    assert "slope_s_per_lap" in df.columns


def test_compute_field_degradation_empty_when_no_laps():
    df = compute_field_degradation(pd.DataFrame(columns=["Driver", "Stint", "Compound", "TyreLife", "LapTimeSeconds", "IsCleanLap"]))
    assert df.empty

"""Tests for f1analytics.analysis.stints."""

from __future__ import annotations

import pandas as pd

from f1analytics.analysis.stints import reconstruct_all_stints, reconstruct_driver_stints


def _lap(driver, lap_number, stint, compound, tyre_life, seconds, team="Red Bull Racing", clean=True):
    return {
        "Driver": driver,
        "Team": team,
        "LapNumber": lap_number,
        "Stint": stint,
        "Compound": compound,
        "TyreLife": tyre_life,
        "LapTimeSeconds": seconds,
        "IsCleanLap": clean,
    }


def _two_stint_driver_laps(driver="VER"):
    rows = []
    # Stint 1: SOFT, laps 1-5, tyre age 1-5
    for i, lap_no in enumerate(range(1, 6), start=1):
        rows.append(_lap(driver, lap_no, stint=1.0, compound="SOFT", tyre_life=i, seconds=90.0 + i * 0.1))
    # Pit lap transition (lap 6): excluded from clean, still part of stint 1 or the pit-out lap of stint 2 depending on FastF1 convention.
    # Stint 2: HARD, laps 6-10, tyre age 1-5 (fresh set)
    for i, lap_no in enumerate(range(6, 11), start=1):
        rows.append(_lap(driver, lap_no, stint=2.0, compound="HARD", tyre_life=i, seconds=92.0 + i * 0.05, clean=(i != 1)))
    return pd.DataFrame(rows)


def test_reconstruct_driver_stints_basic_shape():
    laps = _two_stint_driver_laps()
    stints = reconstruct_driver_stints(laps, "VER")

    assert len(stints) == 2
    first, second = stints
    assert first.stint_number == 1
    assert first.compound == "SOFT"
    assert first.start_lap == 1
    assert first.end_lap == 5
    assert first.length == 5
    assert first.tyre_age_start == 1
    assert first.tyre_age_end == 5
    assert first.n_clean_laps == 5

    assert second.stint_number == 2
    assert second.compound == "HARD"
    assert second.start_lap == 6
    assert second.end_lap == 10
    assert second.n_clean_laps == 4  # first lap of stint 2 marked not-clean (pit out)


def test_reconstruct_driver_stints_pace_stats_from_clean_laps_only():
    laps = _two_stint_driver_laps()
    stints = reconstruct_driver_stints(laps, "VER")

    first = stints[0]
    assert first.median_pace_s is not None
    assert first.pace_variation_s is not None


def test_reconstruct_driver_stints_drops_missing_stint_laps():
    laps = _two_stint_driver_laps()
    extra = _lap("VER", 11, stint=float("nan"), compound=None, tyre_life=None, seconds=95.0)
    laps = pd.concat([laps, pd.DataFrame([extra])], ignore_index=True)

    stints = reconstruct_driver_stints(laps, "VER")

    assert len(stints) == 2  # the NaN-stint lap is excluded, not turned into a 3rd stint


def test_reconstruct_driver_stints_single_lap_stint_has_none_pace_variation():
    laps = pd.DataFrame([_lap("HAM", 1, stint=1.0, compound="MEDIUM", tyre_life=1, seconds=91.0)])
    stints = reconstruct_driver_stints(laps, "HAM")

    assert stints[0].n_clean_laps == 1
    assert stints[0].median_pace_s == 91.0
    assert stints[0].pace_variation_s is None


def test_reconstruct_all_stints_covers_every_driver_sorted_by_start_lap():
    ver_laps = _two_stint_driver_laps("VER")
    ham_laps = _two_stint_driver_laps("HAM")
    laps = pd.concat([ver_laps, ham_laps], ignore_index=True)

    df = reconstruct_all_stints(laps)

    assert set(df["driver"]) == {"VER", "HAM"}
    ver_rows = df[df["driver"] == "VER"]
    assert list(ver_rows["start_lap"]) == sorted(ver_rows["start_lap"])


def test_reconstruct_all_stints_empty_when_no_stint_data():
    laps = pd.DataFrame(
        [_lap("VER", 1, stint=float("nan"), compound=None, tyre_life=None, seconds=90.0)]
    )
    df = reconstruct_all_stints(laps)
    assert df.empty

"""Tests for f1analytics.analysis.pitstops."""

from __future__ import annotations

import pandas as pd

from f1analytics.analysis.pitstops import reconstruct_all_pit_stops, reconstruct_driver_pit_stops


def _lap(driver, lap_number, stint, compound, tyre_life, seconds, position, team,
         pit_in=False, pit_out=False, clean=True):
    return {
        "Driver": driver,
        "Team": team,
        "LapNumber": lap_number,
        "Stint": stint,
        "Compound": compound,
        "TyreLife": tyre_life,
        "LapTimeSeconds": seconds,
        "Position": position,
        "PitInTime": pd.Timedelta(seconds=1) if pit_in else pd.NaT,
        "PitOutTime": pd.Timedelta(seconds=1) if pit_out else pd.NaT,
        "IsCleanLap": clean,
    }


def _laps_df(rows):
    df = pd.DataFrame(rows)
    for col in ("PitInTime", "PitOutTime"):
        df[col] = pd.array([r[col] for r in rows], dtype="timedelta64[ns]")
    return df


def _two_driver_race_with_one_stop():
    rows = []
    # Driver A: leads, pits between lap 5 (in) and lap 6 (out), loses the lead.
    for lap in range(1, 6):
        rows.append(_lap("A", lap, 1.0, "SOFT", lap, 90.0, position=1, team="Team A"))
    rows.append(_lap("A", 6, 1.0, "SOFT", 6, 100.0, position=1, team="Team A", pit_in=True, clean=False))
    rows.append(_lap("A", 7, 2.0, "HARD", 1, 110.0, position=2, team="Team A", pit_out=True, clean=False))
    for lap in range(8, 12):
        rows.append(_lap("A", lap, 2.0, "HARD", lap - 6, 91.0, position=1, team="Team A"))

    # Driver B: runs P2 throughout, briefly takes the lead while A is in the pits.
    for lap in range(1, 6):
        rows.append(_lap("B", lap, 1.0, "MEDIUM", lap, 91.0, position=2, team="Team B"))
    rows.append(_lap("B", 6, 1.0, "MEDIUM", 6, 91.5, position=2, team="Team B"))
    rows.append(_lap("B", 7, 1.0, "MEDIUM", 7, 91.2, position=1, team="Team B"))
    for lap in range(8, 12):
        rows.append(_lap("B", lap, 1.0, "MEDIUM", lap, 91.3, position=2, team="Team B"))

    return _laps_df(rows)


def test_reconstruct_driver_pit_stops_basic_fields():
    laps = _two_driver_race_with_one_stop()
    stops = reconstruct_driver_pit_stops(laps, "A")

    assert len(stops) == 1
    stop = stops[0]
    assert stop.in_lap == 6
    assert stop.out_lap == 7
    assert stop.stint_before == 1
    assert stop.stint_after == 2
    assert stop.compound_before == "SOFT"
    assert stop.compound_after == "HARD"
    assert stop.position_before == 1
    assert stop.position_after == 2


def test_reconstruct_driver_pit_stops_time_loss_estimate():
    laps = _two_driver_race_with_one_stop()
    stop = reconstruct_driver_pit_stops(laps, "A")[0]

    assert stop.reference_pace_s == 90.0  # median of A's clean stint-1 laps
    assert stop.in_lap_time_s == 100.0
    assert stop.out_lap_time_s == 110.0
    assert stop.estimated_time_loss_s == (100.0 + 110.0) - 2 * 90.0


def test_reconstruct_driver_pit_stops_nearby_competitors():
    laps = _two_driver_race_with_one_stop()
    stop = reconstruct_driver_pit_stops(laps, "A")[0]

    # Before the stop: A is P1, B is P2 -> B is "behind" A.
    assert stop.driver_behind_before == "B"
    assert stop.driver_ahead_before is None  # nobody ahead of P1
    # After the stop: A drops to P2, B is now P1 -> B is "ahead" of A.
    assert stop.driver_ahead_after == "B"


def test_reconstruct_driver_pit_stops_missing_out_lap_returns_none_fields():
    rows = [
        _lap("C", 1, 1.0, "SOFT", 1, 90.0, position=5, team="Team C"),
        _lap("C", 2, 1.0, "SOFT", 2, 90.0, position=5, team="Team C", pit_in=True, clean=False),
        # no lap 3 at all: retired in the pits
    ]
    laps = _laps_df(rows)
    stop = reconstruct_driver_pit_stops(laps, "C")[0]

    assert stop.out_lap is None
    assert stop.stint_after is None
    assert stop.estimated_time_loss_s is None


def test_reconstruct_driver_pit_stops_no_pit_stops_returns_empty_list():
    laps = _laps_df([_lap("D", 1, 1.0, "SOFT", 1, 90.0, position=1, team="Team D")])
    assert reconstruct_driver_pit_stops(laps, "D") == []


def test_reconstruct_all_pit_stops_covers_all_drivers_sorted():
    laps = _two_driver_race_with_one_stop()
    df = reconstruct_all_pit_stops(laps)

    assert list(df["driver"]) == ["A"]  # only A pitted in this fixture
    assert df.iloc[0]["in_lap"] == 6


def test_reconstruct_all_pit_stops_empty_when_no_stops():
    laps = _laps_df([_lap("D", 1, 1.0, "SOFT", 1, 90.0, position=1, team="Team D")])
    df = reconstruct_all_pit_stops(laps)
    assert df.empty

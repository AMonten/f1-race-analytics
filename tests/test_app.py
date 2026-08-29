"""Smoke tests for the Streamlit pages, using streamlit.testing.v1.AppTest.

These never touch FastF1 or the network: `app/state.py`'s functions are
monkeypatched to return small synthetic data (built the same way the rest
of the test suite builds fixtures), so what's actually being verified is
the UI wiring — that each page runs to completion without an exception
given valid inputs, and renders the expected key elements. Real-data
verification for each page was done manually against cached FastF1 sessions
(see CHANGELOG for the Milestone 7 entry).
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import state as app_state
from f1analytics.data import loader as data_loader
from f1analytics.data.preprocessing import add_lap_quality_flags

PAGES_DIR = APP_DIR / "pages"
DUMMY_SELECTION = (2023, 1, "Race")


def _raw_lap(driver, team, lap_number, stint, compound, tyre_life, seconds, position,
             pit_in=False, pit_out=False, track_status="1"):
    return {
        "Driver": driver,
        "Team": team,
        "DriverNumber": "1" if driver == "VER" else "2",
        "LapNumber": lap_number,
        "Stint": stint,
        "Compound": compound,
        "TyreLife": tyre_life,
        "LapTime": pd.Timedelta(seconds=seconds),
        "PitInTime": pd.Timedelta(seconds=1) if pit_in else pd.NaT,
        "PitOutTime": pd.Timedelta(seconds=1) if pit_out else pd.NaT,
        "TrackStatus": track_status,
        "Position": position,
        "Deleted": False,
        "IsAccurate": True,
        "Sector1Time": pd.Timedelta(seconds=seconds / 3),
        "Sector2Time": pd.Timedelta(seconds=seconds / 3),
        "Sector3Time": pd.Timedelta(seconds=seconds / 3),
    }


def _synthetic_flagged_laps() -> pd.DataFrame:
    rows = []
    for lap in range(1, 6):
        rows.append(_raw_lap("VER", "Red Bull Racing", lap, 1.0, "SOFT", lap, 90.0 + lap * 0.05, position=1))
        rows.append(_raw_lap("PER", "Red Bull Racing", lap, 1.0, "SOFT", lap, 90.5 + lap * 0.05, position=2))
    rows.append(_raw_lap("VER", "Red Bull Racing", 6, 1.0, "SOFT", 6, 101.0, position=1, pit_in=True))
    rows.append(_raw_lap("VER", "Red Bull Racing", 7, 2.0, "HARD", 1, 115.0, position=2, pit_out=True))
    for lap in range(8, 12):
        rows.append(_raw_lap("VER", "Red Bull Racing", lap, 2.0, "HARD", lap - 6, 91.0, position=1))
    for lap in range(6, 12):
        rows.append(_raw_lap("PER", "Red Bull Racing", lap, 1.0, "SOFT", lap, 90.8, position=2))

    laps = pd.DataFrame(rows)
    for col in ("PitInTime", "PitOutTime"):
        laps[col] = pd.array(laps[col].tolist(), dtype="timedelta64[ns]")
    return add_lap_quality_flags(laps)


class _FakeSession:
    def __init__(self, name):
        self.name = name


@pytest.fixture
def synthetic_flagged_laps():
    return _synthetic_flagged_laps()


@pytest.fixture(autouse=True)
def _patch_state(monkeypatch, synthetic_flagged_laps):
    """Point app/state.py's accessors at synthetic data for every test in this module."""
    monkeypatch.setattr(app_state, "require_selection", lambda: DUMMY_SELECTION)
    monkeypatch.setattr(app_state, "get_selection", lambda: DUMMY_SELECTION)
    monkeypatch.setattr(app_state, "get_flagged_laps", lambda: synthetic_flagged_laps)
    monkeypatch.setattr(app_state, "get_session", lambda telemetry=False: _FakeSession("Race"))


def _run(page_name: str, timeout: float = 30) -> AppTest:
    at = AppTest.from_file(str(PAGES_DIR / page_name), default_timeout=timeout)
    at.run()
    return at


def test_race_pace_page_renders_without_error():
    at = _run("1_Race_Pace.py")
    assert not at.exception
    assert len(at.dataframe) >= 1
    assert len(at.get("plotly_chart")) >= 1


def test_tyres_and_stints_page_renders_without_error():
    at = _run("2_Tyres_and_Stints.py")
    assert not at.exception
    assert len(at.get("plotly_chart")) >= 1  # strategy chart at minimum


def test_position_and_pitstops_page_renders_without_error():
    at = _run("3_Position_and_Pitstops.py")
    assert not at.exception
    assert len(at.get("plotly_chart")) == 1


def test_qualifying_page_shows_message_for_non_qualifying_session(monkeypatch):
    monkeypatch.setattr(app_state, "is_qualifying_like", lambda session: False)
    at = _run("4_Qualifying.py")
    assert not at.exception
    assert any("isn't a qualifying-like session" in i.value for i in at.info)


def test_qualifying_page_renders_for_qualifying_session(monkeypatch):
    monkeypatch.setattr(app_state, "is_qualifying_like", lambda session: True)

    def _fake_segment_labels(session):
        laps = app_state.get_flagged_laps()
        return pd.Series("Q1", index=laps.index)

    monkeypatch.setattr(data_loader, "get_qualifying_segment_labels", _fake_segment_labels)

    at = _run("4_Qualifying.py")
    assert not at.exception
    assert len(at.dataframe) >= 1


def test_telemetry_page_prompts_before_loading():
    at = _run("5_Telemetry.py")
    assert not at.exception
    assert any("Load telemetry" in i.value for i in at.info)


def test_telemetry_page_renders_after_synthetic_load(monkeypatch):
    telemetry = pd.DataFrame(
        {
            "Distance": [0.0, 50.0, 100.0],
            "TimeSeconds": [0.0, 1.0, 2.0],
            "Speed": [280.0, 290.0, 300.0],
            "Throttle": [90.0, 100.0, 100.0],
            "Brake": [False, False, False],
            "RPM": [11000.0, 11500.0, 12000.0],
            "nGear": [6, 7, 7],
            "DRS": [0, 12, 12],
        }
    )

    monkeypatch.setattr(data_loader, "load_session", lambda *a, **k: _FakeSession("Qualifying"))
    monkeypatch.setattr(data_loader, "get_driver_fastest_lap_telemetry", lambda session, driver: telemetry)

    at = AppTest.from_file(str(PAGES_DIR / "5_Telemetry.py"), default_timeout=30)
    at.session_state["telemetry_pair"] = ("VER", "PER")
    at.run()

    assert not at.exception
    assert len(at.get("plotly_chart")) == 2

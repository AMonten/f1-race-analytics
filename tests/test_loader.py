"""Tests for f1analytics.data.loader.

`get_available_seasons` and `summarize_session` contain the only non-trivial
logic in this module, so they're what's tested here. We never call FastF1's
network-backed functions (`get_event_schedule`, `get_event`, `get_session`)
directly — those are exercised manually against the real API, not in CI.
"""

from __future__ import annotations

import pandas as pd
import pytest

from f1analytics.data import loader


def test_get_available_seasons_is_descending_and_bounded(monkeypatch):
    monkeypatch.setattr(loader, "MIN_SUPPORTED_SEASON", 2020)
    monkeypatch.setattr(loader, "MAX_SUPPORTED_SEASON", 2023)

    seasons = loader.get_available_seasons()

    assert seasons == [2023, 2022, 2021, 2020]


class _FakeSession:
    """Minimal stand-in for fastf1.core.Session, exposing only what
    summarize_session reads."""

    def __init__(self, event, laps, results, weather_data, name="Race", date=None):
        self.event = event
        self.laps = laps
        self.results = results
        self.weather_data = weather_data
        self.name = name
        self.date = date


def _make_event(round_number=5, event_name="Example Grand Prix", country="Testland", location="Test City"):
    return pd.Series(
        {
            "RoundNumber": round_number,
            "EventName": event_name,
            "Country": country,
            "Location": location,
        }
    )


def test_summarize_session_with_full_data():
    laps = pd.DataFrame({"LapNumber": [1, 2, 3, 1, 2, 3], "Driver": ["VER", "VER", "VER", "HAM", "HAM", "HAM"]})
    results = pd.DataFrame(
        {
            "Abbreviation": ["VER", "HAM"],
            "TeamName": ["Red Bull Racing", "Mercedes"],
            "Position": [1, 2],
        }
    )
    weather = pd.DataFrame(
        {
            "AirTemp": [22.0, 24.0],
            "TrackTemp": [35.0, 37.0],
            "Humidity": [50.0, 52.0],
            "WindSpeed": [10.0, 12.0],
            "Rainfall": [False, False],
        }
    )
    session = _FakeSession(_make_event(), laps, results, weather, date=pd.Timestamp("2023-05-07"))

    overview = loader.summarize_session(session)

    assert overview.event_name == "Example Grand Prix"
    assert overview.round_number == 5
    assert overview.total_laps == 3
    assert overview.drivers == ["HAM", "VER"]
    assert overview.teams == ["Mercedes", "Red Bull Racing"]
    assert overview.weather_summary is not None
    assert overview.weather_summary["rainfall_observed"] is False
    assert overview.results is not None and len(overview.results) == 2


def test_summarize_session_falls_back_when_results_missing():
    laps = pd.DataFrame({"LapNumber": [1, 2], "Driver": ["VER", "HAM"]})
    empty_results = pd.DataFrame()
    session = _FakeSession(_make_event(), laps, empty_results, weather_data=pd.DataFrame())

    overview = loader.summarize_session(session)

    assert overview.drivers == ["HAM", "VER"]
    assert overview.teams == []
    assert overview.weather_summary is None


def test_summarize_session_handles_no_laps_no_results_no_weather():
    session = _FakeSession(_make_event(), laps=pd.DataFrame(), results=pd.DataFrame(), weather_data=pd.DataFrame())

    overview = loader.summarize_session(session)

    assert overview.total_laps is None
    assert overview.drivers == []
    assert overview.results is None
    assert overview.weather_summary is None


def test_summarize_session_missing_round_number_is_none():
    event = _make_event()
    event["RoundNumber"] = float("nan")
    session = _FakeSession(event, laps=pd.DataFrame(), results=pd.DataFrame(), weather_data=pd.DataFrame())

    overview = loader.summarize_session(session)

    assert overview.round_number is None

"""Tests for f1analytics.data.loader.

FastF1's network-backed functions (`fastf1.get_event_schedule`,
`fastf1.get_event`, `fastf1.get_session`, `Session.load`, telemetry
methods) are never called for real here — those are exercised manually
against the real API (see CHANGELOG). What's tested is our own logic on
top: exception wrapping into `SessionLoadError`, session-name filtering,
qualifying-segment label assignment, telemetry column selection/
conversion, and `summarize_session`'s best-effort field extraction.
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


def test_summarize_session_formats_results_time_and_drops_empty_quali_columns():
    laps = pd.DataFrame({"LapNumber": [1, 2], "Driver": ["VER", "PER"]})
    results = pd.DataFrame(
        {
            "Abbreviation": ["VER", "PER", "OCO"],
            "TeamName": ["Red Bull Racing", "Red Bull Racing", "Alpine"],
            "Position": [1, 2, 3],
            "Time": [
                pd.Timedelta(hours=1, minutes=33, seconds=56, milliseconds=736),
                pd.Timedelta(seconds=11, milliseconds=987),
                pd.NaT,
            ],
            "Q1": [pd.NaT, pd.NaT, pd.NaT],  # entirely empty on a race session
        }
    )
    session = _FakeSession(_make_event(), laps, results, weather_data=pd.DataFrame())

    overview = loader.summarize_session(session)

    assert "Q1" not in overview.results.columns  # dropped: entirely empty
    assert overview.results.set_index("Abbreviation").loc["VER", "Time"] == "1:33:56.736"
    assert overview.results.set_index("Abbreviation").loc["PER", "Time"] == "+11.987s"
    assert overview.results.set_index("Abbreviation").loc["OCO", "Time"] is None


def test_summarize_session_keeps_quali_columns_when_populated():
    laps = pd.DataFrame({"LapNumber": [1], "Driver": ["VER"]})
    results = pd.DataFrame(
        {
            "Abbreviation": ["VER"],
            "Position": [1],
            "Q1": [pd.Timedelta(seconds=90)],
        }
    )
    session = _FakeSession(_make_event(), laps, results, weather_data=pd.DataFrame())

    overview = loader.summarize_session(session)

    assert "Q1" in overview.results.columns


# --- Exception-wrapping and other logic on top of FastF1's API ---
# fastf1's own functions are monkeypatched below and never called for real.


def _raise(exc):
    def _inner(*args, **kwargs):
        raise exc

    return _inner


def test_get_event_schedule_wraps_fastf1_exception(monkeypatch):
    monkeypatch.setattr(loader, "enable_cache", lambda: None)
    monkeypatch.setattr(loader.fastf1, "get_event_schedule", _raise(ValueError("bad year")))

    with pytest.raises(loader.SessionLoadError):
        loader.get_event_schedule(2023)


def test_get_available_sessions_wraps_fastf1_exception(monkeypatch):
    monkeypatch.setattr(loader, "enable_cache", lambda: None)
    monkeypatch.setattr(loader.fastf1, "get_event", _raise(ValueError("bad event")))

    with pytest.raises(loader.SessionLoadError):
        loader.get_available_sessions(2023, 1)


def test_get_available_sessions_filters_missing_and_blank_names(monkeypatch):
    monkeypatch.setattr(loader, "enable_cache", lambda: None)
    fake_event = {
        "Session1": "Practice 1",
        "Session2": None,
        "Session3": "",
        "Session4": "Qualifying",
        "Session5": float("nan"),
    }
    monkeypatch.setattr(loader.fastf1, "get_event", lambda year, ident: fake_event)

    names = loader.get_available_sessions(2023, 1)

    assert names == ["Practice 1", "Qualifying"]


def test_load_session_wraps_fastf1_exception(monkeypatch):
    monkeypatch.setattr(loader, "enable_cache", lambda: None)
    monkeypatch.setattr(loader.fastf1, "get_session", _raise(ValueError("bad session")))

    with pytest.raises(loader.SessionLoadError):
        loader.load_session(2023, 1, "Race")


class _FakeLaps:
    """Stand-in for fastf1.core.Laps, exposing only what
    get_qualifying_segment_labels reads."""

    def __init__(self, index, segments=None, raises=None):
        self.index = index
        self._segments = segments
        self._raises = raises

    def split_qualifying_sessions(self):
        if self._raises is not None:
            raise self._raises
        return self._segments


def test_get_qualifying_segment_labels_assigns_each_segment():
    full_index = pd.RangeIndex(4)
    q1 = pd.DataFrame(index=[0, 1])
    q3 = pd.DataFrame(index=[3])
    fake_laps = _FakeLaps(full_index, segments=[q1, None, q3])  # Q2 cancelled
    session = _FakeSession(_make_event(), laps=fake_laps, results=pd.DataFrame(), weather_data=pd.DataFrame())

    labels = loader.get_qualifying_segment_labels(session)

    assert labels.loc[0] == "Q1"
    assert labels.loc[1] == "Q1"
    assert pd.isna(labels.loc[2])  # Q2 was cancelled -> left unset, not guessed
    assert labels.loc[3] == "Q3"


def test_get_qualifying_segment_labels_wraps_value_error():
    fake_laps = _FakeLaps(pd.RangeIndex(2), raises=ValueError("not a qualifying session"))
    session = _FakeSession(_make_event(), laps=fake_laps, results=pd.DataFrame(), weather_data=pd.DataFrame())

    with pytest.raises(loader.SessionLoadError):
        loader.get_qualifying_segment_labels(session)


class _FakeCarData:
    def __init__(self, df):
        self._df = df

    def add_distance(self):
        return self._df


class _FakeLap:
    def __init__(self, car_data_df):
        self._car_data_df = car_data_df

    def get_car_data(self):
        return _FakeCarData(self._car_data_df)


def test_get_lap_telemetry_selects_known_columns_and_converts_time():
    car_data = pd.DataFrame(
        {
            "Distance": [0.0, 10.0],
            "Time": pd.to_timedelta([0.0, 1.5], unit="s"),
            "Speed": [100.0, 200.0],
            "Throttle": [50.0, 100.0],
            "SomeOtherChannel": [1, 2],
        }
    )
    telemetry = loader.get_lap_telemetry(_FakeLap(car_data))

    assert list(telemetry.columns) == ["Distance", "TimeSeconds", "Speed", "Throttle"]
    assert telemetry["TimeSeconds"].tolist() == [0.0, 1.5]


def test_get_lap_telemetry_handles_missing_time_channel():
    car_data = pd.DataFrame({"Distance": [0.0], "Speed": [100.0]})
    telemetry = loader.get_lap_telemetry(_FakeLap(car_data))

    assert "TimeSeconds" not in telemetry.columns
    assert list(telemetry.columns) == ["Distance", "Speed"]


class _FakeLapsPicker:
    def __init__(self, fastest_lap):
        self._fastest_lap = fastest_lap

    def pick_drivers(self, driver):
        return self

    def pick_fastest(self):
        return self._fastest_lap


class _SessionWithLaps:
    def __init__(self, laps):
        self.laps = laps


def test_get_driver_fastest_lap_telemetry_raises_when_no_valid_lap():
    session = _SessionWithLaps(_FakeLapsPicker(fastest_lap=None))

    with pytest.raises(loader.SessionLoadError):
        loader.get_driver_fastest_lap_telemetry(session, "XXX")


def test_get_driver_fastest_lap_telemetry_delegates_to_get_lap_telemetry(monkeypatch):
    sentinel_lap = object()
    session = _SessionWithLaps(_FakeLapsPicker(fastest_lap=sentinel_lap))

    captured = {}

    def _fake_get_lap_telemetry(lap):
        captured["lap"] = lap
        return pd.DataFrame({"Distance": [0.0]})

    monkeypatch.setattr(loader, "get_lap_telemetry", _fake_get_lap_telemetry)

    result = loader.get_driver_fastest_lap_telemetry(session, "VER")

    assert captured["lap"] is sentinel_lap
    assert list(result.columns) == ["Distance"]

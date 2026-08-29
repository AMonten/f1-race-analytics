"""Session discovery and ingestion via FastF1.

This is the only module that talks to FastF1 directly. Analytical modules
(in `f1analytics.analysis`) consume `fastf1.core.Session` objects or the
plain `pandas.DataFrame`/dict structures returned here — they never import
`fastf1` themselves. This keeps the door open to swapping or supplementing
the data source later without touching analytical code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import fastf1
import pandas as pd

from f1analytics.config import MAX_SUPPORTED_SEASON, MIN_SUPPORTED_SEASON
from f1analytics.data.cache import enable_cache

logger = logging.getLogger(__name__)


class SessionLoadError(RuntimeError):
    """Raised when a requested season/event/session cannot be loaded from FastF1."""


@dataclass
class SessionOverview:
    """Lightweight, display-ready summary of a loaded session.

    Deliberately holds only facts read directly off the FastF1 session
    object (metadata, results, weather) — no derived statistics. Analytical
    metrics belong in `f1analytics.analysis`, not here.
    """

    event_name: str
    country: str | None
    location: str | None
    round_number: int | None
    session_name: str
    session_date: pd.Timestamp | None
    total_laps: int | None
    drivers: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)
    results: pd.DataFrame | None = None
    weather_summary: dict[str, Any] | None = None


def get_available_seasons() -> list[int]:
    """Return supported seasons, most recent first.

    FastF1 has reliable, complete timing/telemetry data from 2018 onward;
    earlier seasons are excluded rather than silently returning partial data.
    """
    return list(range(MAX_SUPPORTED_SEASON, MIN_SUPPORTED_SEASON - 1, -1))


def get_event_schedule(year: int) -> pd.DataFrame:
    """Return the full event schedule for a season (testing events excluded)."""
    enable_cache()
    try:
        return fastf1.get_event_schedule(year, include_testing=False)
    except Exception as exc:  # FastF1 raises plain Exception/ValueError on bad input
        raise SessionLoadError(f"Could not fetch event schedule for {year}: {exc}") from exc


def get_available_sessions(year: int, event_identifier: int | str) -> list[str]:
    """Return the session names held at a given event (e.g. 'Practice 1', 'Race').

    Names are returned exactly as FastF1 reports them for that event, which
    correctly handles the sprint-weekend format changing across seasons
    (e.g. 'Sprint Qualifying' vs 'Sprint Shootout').
    """
    enable_cache()
    try:
        event = fastf1.get_event(year, event_identifier)
    except Exception as exc:
        raise SessionLoadError(
            f"Could not resolve event {event_identifier!r} for {year}: {exc}"
        ) from exc

    session_names: list[str] = []
    for i in range(1, 6):
        name = event.get(f"Session{i}")
        if isinstance(name, str) and name.strip():
            session_names.append(name)
    return session_names


def load_session(
    year: int,
    event_identifier: int | str,
    session_identifier: str,
    *,
    laps: bool = True,
    telemetry: bool = False,
    weather: bool = True,
    messages: bool = False,
) -> fastf1.core.Session:
    """Load a single session from FastF1, using the on-disk cache.

    Args:
        year: Season, e.g. 2023.
        event_identifier: Round number, event name, or country/location
            substring accepted by `fastf1.get_event`.
        session_identifier: Session name ('Race', 'Qualifying', ...) or
            shorthand ('R', 'Q', 'FP1', 'FP2', 'FP3', 'S', 'SQ').
        laps: Whether to load lap-by-lap timing data.
        telemetry: Whether to load car telemetry (large; off by default).
        weather: Whether to load weather data.
        messages: Whether to load race control messages.

    Returns:
        A loaded `fastf1.core.Session`.

    Raises:
        SessionLoadError: If the session cannot be resolved or loaded.
    """
    enable_cache()
    try:
        session = fastf1.get_session(year, event_identifier, session_identifier)
        session.load(laps=laps, telemetry=telemetry, weather=weather, messages=messages)
    except Exception as exc:
        raise SessionLoadError(
            f"Could not load {session_identifier} for {event_identifier} {year}: {exc}"
        ) from exc

    logger.info(
        "Loaded session: %s %s %s", year, session.event.get("EventName"), session.name
    )
    return session


def summarize_session(session: fastf1.core.Session) -> SessionOverview:
    """Build a `SessionOverview` from a loaded session's metadata, results and weather.

    Best-effort: FastF1 data completeness varies by season and session type
    (e.g. weather data or results may be unavailable for some practice
    sessions), so missing pieces are left as `None` rather than raising.
    """
    event = session.event

    round_number = event.get("RoundNumber")
    total_laps: int | None = None
    if session.laps is not None and not session.laps.empty:
        total_laps = int(session.laps["LapNumber"].max())

    drivers: list[str] = []
    teams: list[str] = []
    results: pd.DataFrame | None = None
    if session.results is not None and not session.results.empty:
        results = session.results.copy()
        if "Abbreviation" in results.columns:
            drivers = sorted(results["Abbreviation"].dropna().unique().tolist())
        if "TeamName" in results.columns:
            teams = sorted(results["TeamName"].dropna().unique().tolist())
    elif session.laps is not None and not session.laps.empty and "Driver" in session.laps.columns:
        drivers = sorted(session.laps["Driver"].dropna().unique().tolist())

    weather_summary: dict[str, Any] | None = None
    weather = session.weather_data
    if weather is not None and not weather.empty:
        weather_summary = {
            "air_temp_mean_c": round(float(weather["AirTemp"].mean()), 1),
            "track_temp_mean_c": round(float(weather["TrackTemp"].mean()), 1),
            "humidity_mean_pct": round(float(weather["Humidity"].mean()), 1),
            "wind_speed_mean_kph": round(float(weather["WindSpeed"].mean()), 1),
            "rainfall_observed": bool(weather["Rainfall"].any()),
        }

    return SessionOverview(
        event_name=str(event.get("EventName")),
        country=event.get("Country"),
        location=event.get("Location"),
        round_number=int(round_number) if pd.notna(round_number) else None,
        session_name=session.name,
        session_date=session.date,
        total_laps=total_laps,
        drivers=drivers,
        teams=teams,
        results=results,
        weather_summary=weather_summary,
    )

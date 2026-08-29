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


def get_qualifying_segment_labels(session: fastf1.core.Session) -> pd.Series:
    """Return a Series (indexed like `session.laps`) labelling each lap 'Q1'/'Q2'/'Q3'.

    Wraps FastF1's `Laps.split_qualifying_sessions()`, which needs
    session-level timing context (`session.session_status`) beyond what's
    in the lap table itself — this is why the split happens here, in the
    data layer, rather than in `f1analytics.analysis.qualifying`. Merge the
    result into a laps DataFrame (e.g.
    `laps["QualifyingSegment"] = get_qualifying_segment_labels(session)`)
    before calling the qualifying analysis functions.

    Args:
        session: A loaded qualifying-like session (Qualifying, Sprint
            Qualifying/Shootout).

    Returns:
        A Series of 'Q1'/'Q2'/'Q3'/`None`. A segment is `None` throughout
        if it was cancelled (e.g. a red-flagged Q3) — this is a real gap in
        the data, not something to fill in.

    Raises:
        SessionLoadError: If `session` is not a qualifying-like session, or
            session status data isn't available.
    """
    try:
        segments = session.laps.split_qualifying_sessions()
    except ValueError as exc:
        raise SessionLoadError(f"Could not split qualifying segments: {exc}") from exc

    labels = pd.Series(index=session.laps.index, dtype=object)
    for label, segment_laps in zip(("Q1", "Q2", "Q3"), segments):
        if segment_laps is not None:
            labels.loc[segment_laps.index] = label
    return labels


def get_lap_telemetry(lap: fastf1.core.Lap) -> pd.DataFrame:
    """Return one lap's car telemetry against distance, as a plain DataFrame.

    Uses `Lap.get_car_data()` + `add_distance()` rather than the merged
    `Lap.get_telemetry()`, since only car-channel data is needed (no GPS
    position) — this is faster and, per FastF1's own documentation, more
    accurate than the merged method when position data isn't required.

    Requires the session to have been loaded with `telemetry=True` (see
    `load_session`). No channel is derived or fabricated beyond what
    FastF1 provides; `TimeSeconds` is simply `Time` (lap-relative elapsed
    time) converted from `Timedelta` to `float` seconds for easier
    downstream arithmetic.

    Returns:
        A DataFrame with whichever of `Distance`, `TimeSeconds`, `Speed`,
        `Throttle`, `Brake`, `RPM`, `nGear`, `DRS` FastF1 provides.
    """
    car_data = lap.get_car_data().add_distance()

    result = pd.DataFrame({"Distance": car_data["Distance"]})
    if "Time" in car_data.columns:
        result["TimeSeconds"] = car_data["Time"].dt.total_seconds()
    for column in ("Speed", "Throttle", "Brake", "RPM", "nGear", "DRS"):
        if column in car_data.columns:
            result[column] = car_data[column]
    return result


def get_driver_fastest_lap_telemetry(session: fastf1.core.Session, driver: str) -> pd.DataFrame:
    """Convenience: telemetry for `driver`'s fastest personal-best-marked lap.

    Raises:
        SessionLoadError: If the driver has no valid (personal-best-marked)
            lap in this session.
    """
    lap = session.laps.pick_drivers(driver).pick_fastest()
    if lap is None:
        raise SessionLoadError(f"No valid fastest lap found for driver {driver!r}")
    return get_lap_telemetry(lap)


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

"""F1 Race Analytics — Streamlit entry point.

Milestone 1 scope: season / Grand Prix / session selection, session loading
via FastF1 (with caching), and a minimal session overview. Later milestones
add the position evolution, pace, tyre/stint, pit-stop, qualifying and
telemetry sections described in the README.

This module only handles UI wiring and rendering. All data access lives in
`f1analytics.data.loader`; no analytical logic belongs here.
"""

from __future__ import annotations

import logging

import streamlit as st

from f1analytics.data import loader
from f1analytics.data.loader import SessionLoadError, SessionOverview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="F1 Race Analytics",
    page_icon=":checkered_flag:",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def _cached_schedule(year: int):
    return loader.get_event_schedule(year)


@st.cache_data(show_spinner=False)
def _cached_available_sessions(year: int, event_identifier: int):
    return loader.get_available_sessions(year, event_identifier)


@st.cache_resource(show_spinner="Loading session from FastF1 (first fetch can take a while)...")
def _cached_load_session(year: int, event_identifier: int, session_identifier: str):
    return loader.load_session(year, event_identifier, session_identifier)


def _render_session_picker() -> tuple[int, int, str] | None:
    """Render the season / Grand Prix / session selectors in the sidebar.

    Returns:
        `(year, round_number, session_identifier)` once the user has made a
        complete selection, otherwise `None`.
    """
    st.sidebar.header("Session selection")

    year = st.sidebar.selectbox("Season", loader.get_available_seasons())

    try:
        schedule = _cached_schedule(year)
    except SessionLoadError as exc:
        st.sidebar.error(str(exc))
        return None

    event_options = dict(zip(schedule["EventName"], schedule["RoundNumber"]))
    event_name = st.sidebar.selectbox("Grand Prix", list(event_options.keys()))
    round_number = int(event_options[event_name])

    try:
        session_names = _cached_available_sessions(year, round_number)
    except SessionLoadError as exc:
        st.sidebar.error(str(exc))
        return None

    if not session_names:
        st.sidebar.warning("No sessions listed for this event yet.")
        return None

    session_identifier = st.sidebar.selectbox("Session", session_names)

    if not st.sidebar.button("Load session", type="primary"):
        return None

    return year, round_number, session_identifier


def _render_overview(overview: SessionOverview) -> None:
    st.subheader(f"{overview.event_name} — {overview.session_name}")

    meta_cols = st.columns(4)
    meta_cols[0].metric("Round", overview.round_number if overview.round_number else "—")
    meta_cols[1].metric("Location", overview.location or "—")
    meta_cols[2].metric(
        "Date", overview.session_date.strftime("%Y-%m-%d") if overview.session_date else "—"
    )
    meta_cols[3].metric("Laps completed", overview.total_laps if overview.total_laps else "—")

    st.caption(
        f"{len(overview.drivers)} drivers · {len(overview.teams)} teams"
        + (f" · {overview.country}" if overview.country else "")
    )

    if overview.weather_summary:
        st.markdown("**Weather summary**")
        w = overview.weather_summary
        w_cols = st.columns(5)
        w_cols[0].metric("Air temp", f"{w['air_temp_mean_c']} °C")
        w_cols[1].metric("Track temp", f"{w['track_temp_mean_c']} °C")
        w_cols[2].metric("Humidity", f"{w['humidity_mean_pct']} %")
        w_cols[3].metric("Wind", f"{w['wind_speed_mean_kph']} km/h")
        w_cols[4].metric("Rainfall", "Yes" if w["rainfall_observed"] else "No")

    if overview.results is not None and not overview.results.empty:
        st.markdown("**Results / classification**")
        st.dataframe(overview.results, use_container_width=True, hide_index=True)
    else:
        st.info("No results/classification data available for this session yet.")


def main() -> None:
    st.title("F1 Race Analytics")
    st.caption(
        "Unofficial project — not affiliated with Formula 1, the FIA, or any team. "
        "Data via [FastF1](https://docs.fastf1.dev/)."
    )

    selection = _render_session_picker()
    if selection is None:
        st.info("Select a season, Grand Prix and session, then click **Load session**.")
        return

    year, round_number, session_identifier = selection
    try:
        session = _cached_load_session(year, round_number, session_identifier)
        overview = loader.summarize_session(session)
    except SessionLoadError as exc:
        logger.exception("Failed to load session")
        st.error(f"Could not load session: {exc}")
        return

    _render_overview(overview)


if __name__ == "__main__":
    main()

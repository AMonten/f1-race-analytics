"""F1 Race Analytics — Streamlit entry point (Overview page).

Handles season / Grand Prix / session selection and shows a session
overview. Every other section (race pace, tyres & stints, position
evolution & pit stops, qualifying, telemetry) lives in `app/pages/` and
reads the session selected here via `app/state.py`.

This module only handles UI wiring and rendering. All data access lives in
`f1analytics.data.loader`; no analytical logic belongs here.
"""

from __future__ import annotations

import logging

import streamlit as st
from state import FAVICON_PATH, get_selection, get_session, render_branding, set_selection

from f1analytics.data import loader
from f1analytics.data.loader import SessionLoadError, SessionOverview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="F1 Race Analytics",
    page_icon=str(FAVICON_PATH),
    layout="wide",
)
render_branding()


@st.cache_data(show_spinner=False)
def _cached_schedule(year: int):
    return loader.get_event_schedule(year)


@st.cache_data(show_spinner=False)
def _cached_available_sessions(year: int, event_identifier: int):
    return loader.get_available_sessions(year, event_identifier)


def _render_session_picker() -> None:
    """Render the season / Grand Prix / session selectors in the sidebar.

    Pre-selects whatever is currently active (so navigating back to this
    page doesn't reset the picker), and only commits a new selection when
    the user explicitly clicks **Load session** — dropdown changes alone
    don't trigger a fetch.
    """
    st.sidebar.header("Session selection")
    current = get_selection()

    seasons = loader.get_available_seasons()
    year = st.sidebar.selectbox(
        "Season", seasons, index=seasons.index(current[0]) if current else 0
    )

    try:
        schedule = _cached_schedule(year)
    except SessionLoadError as exc:
        st.sidebar.error(str(exc))
        return

    event_options = dict(zip(schedule["EventName"], schedule["RoundNumber"], strict=True))
    event_names = list(event_options.keys())
    default_event_index = 0
    if current:
        matching = [i for i, name in enumerate(event_names) if event_options[name] == current[1]]
        if matching:
            default_event_index = matching[0]
    event_name = st.sidebar.selectbox("Grand Prix", event_names, index=default_event_index)
    round_number = int(event_options[event_name])

    try:
        session_names = _cached_available_sessions(year, round_number)
    except SessionLoadError as exc:
        st.sidebar.error(str(exc))
        return

    if not session_names:
        st.sidebar.warning("No sessions listed for this event yet.")
        return

    default_session_index = (
        session_names.index(current[2])
        if current and current[0] == year and current[1] == round_number and current[2] in session_names
        else 0
    )
    session_identifier = st.sidebar.selectbox(
        "Session", session_names, index=default_session_index
    )

    if st.sidebar.button("Load session", type="primary"):
        set_selection(year, round_number, session_identifier)
        st.rerun()


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

    st.page_link("pages/1_Race_Pace.py", label="Race pace →")
    st.page_link("pages/2_Tyres_and_Stints.py", label="Tyres & stints →")
    st.page_link("pages/3_Position_and_Pitstops.py", label="Position evolution & pit stops →")
    st.page_link("pages/4_Qualifying.py", label="Qualifying →")
    st.page_link("pages/5_Telemetry.py", label="Telemetry →")


def _render_methodology() -> None:
    with st.expander("Methodology (short version — see the README for full detail)"):
        st.markdown(
            "- **Clean laps**: a lap counts as \"clean\" (used for every pace/degradation "
            "figure below) only if it has a time, isn't a pit in/out lap, wasn't run under "
            "yellow/SC/VSC/red flag, wasn't deleted, is flagged accurate by FastF1, and isn't "
            "a statistical outlier for its driver/stint.\n"
            "- **Race Pace Index** = 100 × field median clean lap ÷ driver median clean lap. "
            "100 = matched the field median. This mixes car, strategy, fuel and traffic — "
            "**it is not a measure of driver skill.**\n"
            "- **Tyre degradation** is a simple `LapTime = α + β×TyreAge` fit per stint — "
            "it does not separate tyre wear from fuel burn-off or track evolution.\n"
            "- **Pit-stop time loss** and **telemetry time deltas** are approximations, "
            "documented in full in each analysis module's docstring.\n\n"
            "Full methodology: [README on GitHub]"
            "(https://github.com/AMonten/f1-race-analytics#8-analytical-methodology)."
        )


def main() -> None:
    st.title("F1 Race Analytics")
    st.caption(
        "Unofficial project — not affiliated with Formula 1, the FIA, or any team. "
        "Data via [FastF1](https://docs.fastf1.dev/)."
    )

    _render_session_picker()

    if get_selection() is None:
        st.info("Select a season, Grand Prix and session, then click **Load session**.")
        _render_methodology()
        return

    try:
        session = get_session()
        overview = loader.summarize_session(session)
    except SessionLoadError as exc:
        logger.exception("Failed to load session")
        st.error(f"Could not load session: {exc}")
        return

    _render_overview(overview)
    _render_methodology()


if __name__ == "__main__":
    main()

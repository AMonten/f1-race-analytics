"""Shared Streamlit session-state and caching helpers.

Every page depends on "which session is currently selected" — this module
is the single place that owns that state, the FastF1 loading cache, and the
clean-lap flagging step, so pages don't duplicate the sidebar picker or
cache keys. UI glue only; no analytical logic lives here.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from f1analytics.data import loader
from f1analytics.data.preprocessing import add_lap_quality_flags

SELECTION_KEY = "f1_session_selection"  # (year, round_number, session_identifier)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo.svg"
ICON_PATH = ASSETS_DIR / "icon.svg"
FAVICON_PATH = ASSETS_DIR / "icon-64.png"

# FastF1 session names that split into Q1/Q2/Q3 (see
# fastf1.core.Session._QUALI_LIKE_SESSIONS, which varies by season rules).
QUALIFYING_LIKE_SESSION_NAMES = ("Qualifying", "Sprint Shootout", "Sprint Qualifying")


def get_selection() -> tuple[int, int, str] | None:
    """Return the currently selected `(year, round_number, session_identifier)`, or `None`."""
    return st.session_state.get(SELECTION_KEY)


def set_selection(year: int, round_number: int, session_identifier: str) -> None:
    st.session_state[SELECTION_KEY] = (year, round_number, session_identifier)


@st.cache_resource(show_spinner="Loading session from FastF1 (first fetch can take a while)...")
def _load_session_cached(year: int, round_number: int, session_identifier: str, telemetry: bool):
    return loader.load_session(year, round_number, session_identifier, telemetry=telemetry)


def get_session(telemetry: bool = False):
    """Return the currently selected `fastf1.core.Session`, or `None` if nothing is selected.

    Args:
        telemetry: Pass `True` on pages that need car telemetry (the
            Telemetry page) — this triggers a separate, heavier load from
            the one used for every other page, cached independently.
    """
    selection = get_selection()
    if selection is None:
        return None
    year, round_number, session_identifier = selection
    return _load_session_cached(year, round_number, session_identifier, telemetry)


@st.cache_data(show_spinner=False)
def _flagged_laps_cached(year: int, round_number: int, session_identifier: str):
    session = _load_session_cached(year, round_number, session_identifier, False)
    return add_lap_quality_flags(session.laps)


def get_flagged_laps():
    """Return the currently selected session's laps with clean-lap flags, or `None`."""
    selection = get_selection()
    if selection is None:
        return None
    return _flagged_laps_cached(*selection)


def require_selection() -> tuple[int, int, str]:
    """Stop the page (with a friendly message) if no session is selected yet."""
    selection = get_selection()
    if selection is None:
        st.info("Select a season, Grand Prix and session on the **Overview** page first.")
        st.stop()
    return selection


def is_qualifying_like(session) -> bool:
    """True if `session` is a Qualifying, Sprint Qualifying, or Sprint Shootout session."""
    return session.name in QUALIFYING_LIKE_SESSION_NAMES


def render_branding() -> None:
    """Show the project logo in the sidebar header. Call once per page, right after `st.set_page_config`."""
    st.logo(
        str(LOGO_PATH),
        icon_image=str(ICON_PATH),
        link="https://github.com/AMonten/f1-race-analytics",
    )

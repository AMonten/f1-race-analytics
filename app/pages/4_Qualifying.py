"""Qualifying page: classification, Q1/Q2/Q3 progression, teammate & lap comparison.

UI wiring only — all computation is in `f1analytics.analysis.qualifying`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from state import (
    FAVICON_PATH,
    get_flagged_laps,
    get_session,
    is_qualifying_like,
    render_branding,
    require_selection,
)

from f1analytics.analysis.qualifying import (
    compare_teammates,
    compare_two_laps,
    compute_qualifying_classification,
    get_driver_best_lap,
    get_segment_progression,
)
from f1analytics.data import loader as data_loader

st.set_page_config(
    page_title="Qualifying — F1 Race Analytics", page_icon=str(FAVICON_PATH), layout="wide"
)
render_branding()

require_selection()
session = get_session()

st.title("Qualifying Analysis")

if not is_qualifying_like(session):
    st.info(
        f"The selected session ({session.name}) isn't a qualifying-like session. "
        "Select a Qualifying, Sprint Qualifying, or Sprint Shootout session on the "
        "Overview page to use this page."
    )
    st.stop()

flagged = get_flagged_laps().copy()
flagged["QualifyingSegment"] = data_loader.get_qualifying_segment_labels(session)

st.caption(
    "Uses a different \"valid lap\" filter than race pace: an unusually **fast** lap is "
    "never excluded here (setting one is the whole point of qualifying) — see "
    "Overview → Methodology."
)

st.subheader("Classification")
classification = compute_qualifying_classification(flagged)
st.dataframe(classification.round(3), use_container_width=True, hide_index=True)

progression = get_segment_progression(flagged)
if not progression.empty:
    st.subheader("Q1 / Q2 / Q3 progression")
    st.dataframe(progression.round(3), use_container_width=True, hide_index=True)

st.subheader("Teammate comparison")
teammates = compare_teammates(flagged)
if teammates.empty:
    st.info("No team with exactly two drivers found in this session's data.")
else:
    st.dataframe(teammates.round(3), use_container_width=True, hide_index=True)

st.subheader("Compare two laps")
drivers = sorted(flagged["Driver"].dropna().unique())
if len(drivers) < 2:
    st.info("Need at least two drivers with lap data.")
else:
    col_a, col_b = st.columns(2)
    driver_a = col_a.selectbox("Driver A", drivers, index=0, key="quali_driver_a")
    driver_b = col_b.selectbox(
        "Driver B", drivers, index=1 if len(drivers) > 1 else 0, key="quali_driver_b"
    )

    lap_a = get_driver_best_lap(flagged, driver_a)
    lap_b = get_driver_best_lap(flagged, driver_b)
    if lap_a is None or lap_b is None:
        st.info("One or both drivers have no valid lap in this session.")
    else:
        comparison = compare_two_laps(lap_a, lap_b)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Lap time delta", f"{comparison.lap_time_delta_s:+.3f}s")
        c2.metric(
            "Sector 1 delta",
            f"{comparison.sector1_delta_s:+.3f}s" if comparison.sector1_delta_s is not None else "—",
        )
        c3.metric(
            "Sector 2 delta",
            f"{comparison.sector2_delta_s:+.3f}s" if comparison.sector2_delta_s is not None else "—",
        )
        c4.metric(
            "Sector 3 delta",
            f"{comparison.sector3_delta_s:+.3f}s" if comparison.sector3_delta_s is not None else "—",
        )
        st.caption(f"Positive = {driver_a} slower than {driver_b}.")

"""Telemetry page: distance-synchronized comparison between two drivers' fastest laps.

UI wiring only — all computation is in `f1analytics.analysis.telemetry`. Telemetry
loading is heavier than every other page, so it only happens on an explicit button
click, and the telemetry-enabled session is loaded once (cached) and reused for
both drivers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from state import get_flagged_laps, get_selection, require_selection

from f1analytics.analysis.telemetry import compare_lap_telemetry, identify_gain_loss_zones
from f1analytics.data import loader as data_loader
from f1analytics.visualization.telemetry import build_telemetry_channels_chart, build_time_delta_chart

st.set_page_config(page_title="Telemetry — F1 Race Analytics", page_icon="📡", layout="wide")

require_selection()
flagged = get_flagged_laps()

st.title("Telemetry Comparison")
st.caption(
    "Compares each driver's fastest lap, synchronized by **distance** rather than time. "
    "Loading telemetry is heavier than the rest of the app — the first load can take a "
    "while."
)

drivers = sorted(flagged["Driver"].dropna().unique())
if len(drivers) < 2:
    st.info("Need at least two drivers with lap data.")
    st.stop()

col_a, col_b = st.columns(2)
driver_a = col_a.selectbox("Driver A", drivers, index=0)
driver_b = col_b.selectbox("Driver B", drivers, index=1 if len(drivers) > 1 else 0)

if driver_a == driver_b:
    st.info("Pick two different drivers.")
    st.stop()

if st.button("Load telemetry", type="primary"):
    st.session_state["telemetry_pair"] = (driver_a, driver_b)

pair = st.session_state.get("telemetry_pair")
if pair is None:
    st.info("Click **Load telemetry** to fetch and compare.")
    st.stop()

selected_a, selected_b = pair


@st.cache_resource(show_spinner="Loading telemetry-enabled session (this can take a while)...")
def _load_telemetry_session(year: int, round_number: int, session_identifier: str):
    return data_loader.load_session(year, round_number, session_identifier, telemetry=True)


@st.cache_data(show_spinner=False)
def _telemetry_for(year: int, round_number: int, session_identifier: str, driver: str):
    session = _load_telemetry_session(year, round_number, session_identifier)
    return data_loader.get_driver_fastest_lap_telemetry(session, driver)


selection = get_selection()
try:
    tel_a = _telemetry_for(*selection, selected_a)
    tel_b = _telemetry_for(*selection, selected_b)
except Exception as exc:  # noqa: BLE001 - surfaced directly to the user, not swallowed
    st.error(f"Could not load telemetry: {exc}")
    st.stop()

comparison = compare_lap_telemetry(tel_a, tel_b, driver_a=selected_a, driver_b=selected_b)

st.plotly_chart(
    build_telemetry_channels_chart(comparison.synced, driver_a=selected_a, driver_b=selected_b),
    use_container_width=True,
)

m1, m2, m3 = st.columns(3)
m1.metric(
    "Max speed delta",
    f"{comparison.max_speed_delta_kph:+.1f} km/h"
    if comparison.max_speed_delta_kph is not None
    else "—",
)
m2.metric(
    "Min speed delta",
    f"{comparison.min_speed_delta_kph:+.1f} km/h"
    if comparison.min_speed_delta_kph is not None
    else "—",
)
m3.metric(
    "Approx. time delta",
    f"{comparison.time_delta_at_finish_s:+.3f}s"
    if comparison.time_delta_at_finish_s is not None
    else "—",
)
st.caption(
    "Time delta is an approximation over the two laps' overlapping distance range only "
    "— see Overview → Methodology."
)

if "TimeDelta_s" in comparison.synced.columns:
    st.plotly_chart(
        build_time_delta_chart(comparison.synced, driver_a=selected_a, driver_b=selected_b),
        use_container_width=True,
    )

    st.subheader("Gain / loss zones")
    st.caption(
        "A descriptive read of where the time delta is rising or falling — this does "
        "**not** attribute *why* time was gained or lost."
    )
    zones = identify_gain_loss_zones(comparison.synced)
    notable = zones[zones["direction"] != "even"]
    if notable.empty:
        st.info("No notable gain/loss zones detected above the noise threshold.")
    else:
        st.dataframe(notable, use_container_width=True, hide_index=True)

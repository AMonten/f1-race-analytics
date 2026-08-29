"""Position & Pit Stops page: race position evolution with SC/VSC bands and pit markers.

UI wiring only — all computation is in `f1analytics.analysis.race`/`pitstops`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from state import get_flagged_laps, require_selection

from f1analytics.analysis.pitstops import reconstruct_all_pit_stops
from f1analytics.analysis.race import get_position_by_lap, get_track_status_periods
from f1analytics.visualization.race import build_position_evolution_chart

st.set_page_config(
    page_title="Position & Pit Stops — F1 Race Analytics", page_icon="📈", layout="wide"
)

require_selection()
flagged = get_flagged_laps()

st.title("Race Position Evolution & Pit Stops")

position_grid = get_position_by_lap(flagged)
if position_grid.empty:
    st.warning(
        "No position data available for this session (position evolution is only "
        "meaningful for Race or Sprint sessions)."
    )
    st.stop()

all_drivers = list(position_grid.columns)
selected = st.multiselect(
    "Drivers", all_drivers, default=all_drivers[: min(10, len(all_drivers))]
)

periods = get_track_status_periods(flagged)
pit_stops = reconstruct_all_pit_stops(flagged)

fig = build_position_evolution_chart(
    position_grid,
    drivers=selected or all_drivers,
    track_status_periods=periods,
    pit_stops=pit_stops,
)
st.plotly_chart(fig, use_container_width=True)

if not periods.empty:
    st.subheader("Track status periods")
    st.dataframe(periods, use_container_width=True, hide_index=True)

st.subheader("Pit stops")
st.caption(
    "Estimated time loss = (in-lap + out-lap time) − 2×the driver's own preceding-stint "
    "pace. Position changes are shown for context only — **not** attributed to the stop "
    "itself (could be strategy, a rival's own stop, or an unrelated incident)."
)
if pit_stops.empty:
    st.info("No pit stops reconstructed for this session.")
else:
    pit_cols = [
        "driver",
        "in_lap",
        "out_lap",
        "compound_before",
        "compound_after",
        "position_before",
        "position_after",
        "driver_ahead_before",
        "driver_behind_before",
        "driver_ahead_after",
        "driver_behind_after",
        "estimated_time_loss_s",
    ]
    st.dataframe(pit_stops[pit_cols].round(3), use_container_width=True, hide_index=True)

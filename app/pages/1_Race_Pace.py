"""Race Pace page: field ranking (Race Pace Index) and two-driver comparison.

UI wiring only — all computation is in `f1analytics.analysis.pace`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st
from state import get_flagged_laps, require_selection

from f1analytics.analysis.pace import compare_driver_pace, compute_field_race_pace
from f1analytics.visualization import TEAM_COLORS

st.set_page_config(page_title="Race Pace — F1 Race Analytics", page_icon="🏎️", layout="wide")

require_selection()
flagged = get_flagged_laps()

st.title("Race Pace")
st.caption(
    "Computed from clean laps only (see Overview → Methodology). The Race Pace Index "
    "mixes car, strategy, fuel and traffic — it is **not** a measure of driver skill."
)

field = compute_field_race_pace(flagged)
if field["median_s"].notna().sum() == 0:
    st.warning(
        "No clean laps found in this session — race pace can't be computed here "
        "(this is expected for short practice runs or sessions with very few laps)."
    )
    st.stop()

display_cols = [
    "driver",
    "team",
    "n_clean_laps",
    "median_s",
    "mean_s",
    "std_s",
    "fastest_representative_s",
    "delta_to_field_median_s",
    "race_pace_index",
]
st.dataframe(field[display_cols].round(3), use_container_width=True, hide_index=True)

ranked = field.dropna(subset=["race_pace_index"]).sort_values("race_pace_index", ascending=False)
teams = list(dict.fromkeys(ranked["team"]))
color_map = {team: TEAM_COLORS[i % len(TEAM_COLORS)] for i, team in enumerate(teams)}

fig = px.bar(
    ranked,
    x="driver",
    y="race_pace_index",
    color="team",
    color_discrete_map=color_map,
    title="Race Pace Index by driver (100 = field median clean lap)",
    labels={"race_pace_index": "Race Pace Index", "driver": "Driver", "team": "Team"},
)
fig.add_hline(y=100, line_dash="dash", line_color="#898781", annotation_text="Field median")
fig.update_layout(plot_bgcolor="#fcfcfb")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Compare two drivers")
drivers = sorted(flagged["Driver"].dropna().unique())
if len(drivers) < 2:
    st.info("Need at least two drivers with lap data to compare.")
else:
    col_a, col_b = st.columns(2)
    driver_a = col_a.selectbox("Driver A", drivers, index=0)
    driver_b = col_b.selectbox("Driver B", drivers, index=1)

    if driver_a == driver_b:
        st.info("Pick two different drivers.")
    else:
        comparison = compare_driver_pace(flagged, driver_a, driver_b)
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Median lap delta",
            f"{comparison.median_delta_s:+.3f}s" if comparison.median_delta_s is not None else "—",
        )
        c2.metric(
            "Fastest-lap delta",
            f"{comparison.fastest_lap_delta_s:+.3f}s"
            if comparison.fastest_lap_delta_s is not None
            else "—",
        )
        c3.metric(
            "Consistency delta (std)",
            f"{comparison.consistency_delta_s:+.3f}s"
            if comparison.consistency_delta_s is not None
            else "—",
        )
        st.caption(f"Positive = {driver_a} slower / less consistent than {driver_b}.")

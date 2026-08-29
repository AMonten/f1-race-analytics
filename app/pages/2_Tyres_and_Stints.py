"""Tyres & Stints page: strategy chart across the grid, plus per-stint degradation.

UI wiring only — all computation is in `f1analytics.analysis.stints`/`tyres`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from state import FAVICON_PATH, get_flagged_laps, render_branding, require_selection

from f1analytics.analysis.stints import reconstruct_all_stints, reconstruct_driver_stints
from f1analytics.analysis.tyres import compute_stint_degradation
from f1analytics.visualization.strategy import build_degradation_chart, build_strategy_chart

st.set_page_config(
    page_title="Tyres & Stints — F1 Race Analytics", page_icon=str(FAVICON_PATH), layout="wide"
)
render_branding()

require_selection()
flagged = get_flagged_laps()

st.title("Tyres & Stints")

stints = reconstruct_all_stints(flagged)
if stints.empty:
    st.warning("No stint data available for this session.")
    st.stop()

st.plotly_chart(build_strategy_chart(stints), use_container_width=True)

st.subheader("Stint detail")
stint_cols = [
    "driver",
    "stint_number",
    "compound",
    "start_lap",
    "end_lap",
    "length",
    "tyre_age_start",
    "tyre_age_end",
    "n_clean_laps",
    "median_pace_s",
    "pace_variation_s",
]
st.dataframe(stints[stint_cols].round(3), use_container_width=True, hide_index=True)

st.subheader("Tyre degradation")
st.caption(
    "LapTime = α + β×TyreAge fit per stint, from clean laps only. Does **not** separate "
    "tyre wear from fuel burn-off or track evolution — see Overview → Methodology."
)

drivers = sorted(flagged["Driver"].dropna().unique())
col_driver, col_stint = st.columns(2)
driver = col_driver.selectbox("Driver", drivers)

driver_stints = reconstruct_driver_stints(flagged, driver)
if not driver_stints:
    st.info(f"No stint data for {driver}.")
else:
    stint_options = {
        f"Stint {s.stint_number} — {s.compound} (laps {s.start_lap}-{s.end_lap})": s.stint_number
        for s in driver_stints
    }
    stint_label = col_stint.selectbox("Stint", list(stint_options.keys()))
    stint_number = stint_options[stint_label]

    result = compute_stint_degradation(flagged, driver, stint_number)
    stint_laps = flagged[
        (flagged["Driver"] == driver)
        & (flagged["Stint"] == stint_number)
        & (flagged["IsCleanLap"])
    ]

    if result.fit.n_observations == 0:
        st.info("No clean laps in this stint to fit.")
    else:
        st.plotly_chart(
            build_degradation_chart(stint_laps, result.fit, compound=result.compound),
            use_container_width=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Slope",
            f"{result.fit.slope_s_per_lap:+.3f} s/lap"
            if result.fit.slope_s_per_lap is not None
            else "—",
        )
        m2.metric("R²", f"{result.fit.r_squared:.2f}" if result.fit.r_squared is not None else "—")
        m3.metric("Sample size", result.fit.n_observations)
        if result.fit.warning:
            st.caption(f"⚠️ {result.fit.warning.replace('_', ' ')}")

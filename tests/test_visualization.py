"""Structural smoke tests for the Plotly chart builders.

These check that each builder produces a well-formed figure (right trace
types/count, axis configuration, error handling) — not visual appearance,
which isn't practical to assert in a unit test. The Streamlit app itself is
exercised more fully via streamlit.testing in tests/test_app.py.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from f1analytics.models.degradation import DegradationFit
from f1analytics.visualization.race import build_position_evolution_chart
from f1analytics.visualization.strategy import build_degradation_chart, build_strategy_chart
from f1analytics.visualization.telemetry import build_telemetry_channels_chart, build_time_delta_chart


def test_build_position_evolution_chart_one_trace_per_driver():
    grid = pd.DataFrame(
        {"VER": [1.0, 1.0, 2.0], "HAM": [2.0, 2.0, 1.0]}, index=pd.Index([1, 2, 3], name="LapNumber")
    )
    fig = build_position_evolution_chart(grid)

    assert isinstance(fig, go.Figure)
    assert fig.layout.yaxis.autorange == "reversed"
    line_traces = [t for t in fig.data if t.mode == "lines+markers"]
    assert len(line_traces) == 2


def test_build_position_evolution_chart_respects_driver_filter():
    grid = pd.DataFrame(
        {"VER": [1.0, 2.0], "HAM": [2.0, 1.0]}, index=pd.Index([1, 2], name="LapNumber")
    )
    fig = build_position_evolution_chart(grid, drivers=["VER"])
    line_traces = [t for t in fig.data if t.mode == "lines+markers"]
    assert len(line_traces) == 1
    assert line_traces[0].name == "VER"


def test_build_position_evolution_chart_adds_status_bands_and_pit_markers():
    grid = pd.DataFrame({"VER": [1.0, 1.0, 1.0]}, index=pd.Index([1, 2, 3], name="LapNumber"))
    periods = pd.DataFrame(
        [{"status_code": "4", "status_label": "Safety Car", "start_lap": 2, "end_lap": 3}]
    )
    pit_stops = pd.DataFrame([{"driver": "VER", "in_lap": 2}])

    fig = build_position_evolution_chart(grid, track_status_periods=periods, pit_stops=pit_stops)

    assert len(fig.layout.shapes) == 1  # the vrect
    pit_traces = [t for t in fig.data if t.name == "Pit stop"]
    assert len(pit_traces) == 1
    assert list(pit_traces[0].x) == [2]


def _stints_df():
    return pd.DataFrame(
        [
            {"driver": "VER", "stint_number": 1, "compound": "SOFT", "start_lap": 1, "end_lap": 10, "length": 10},
            {"driver": "VER", "stint_number": 2, "compound": "HARD", "start_lap": 11, "end_lap": 30, "length": 20},
            {"driver": "HAM", "stint_number": 1, "compound": "MEDIUM", "start_lap": 1, "end_lap": 30, "length": 30},
        ]
    )


def test_build_strategy_chart_one_bar_per_stint():
    fig = build_strategy_chart(_stints_df())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3


def test_build_strategy_chart_legend_shown_once_per_compound():
    fig = build_strategy_chart(_stints_df())
    soft_traces = [t for t in fig.data if t.name == "SOFT"]
    assert len(soft_traces) == 1
    assert soft_traces[0].showlegend is True


def test_build_degradation_chart_includes_fit_line_when_available():
    stint_laps = pd.DataFrame({"TyreLife": [1, 2, 3, 4, 5], "LapTimeSeconds": [90.0, 90.2, 90.4, 90.6, 90.8]})
    fit = DegradationFit(
        n_observations=5, intercept_s=89.8, slope_s_per_lap=0.2, r_squared=1.0, p_value=0.0, std_err=0.0, warning=None
    )
    fig = build_degradation_chart(stint_laps, fit, compound="SOFT")

    names = [t.name for t in fig.data]
    assert "Clean laps" in names
    assert any(n and n.startswith("Fit:") for n in names)


def test_build_degradation_chart_annotates_when_no_fit():
    stint_laps = pd.DataFrame({"TyreLife": [1], "LapTimeSeconds": [90.0]})
    fit = DegradationFit(
        n_observations=1, intercept_s=None, slope_s_per_lap=None, r_squared=None, p_value=None, std_err=None,
        warning="insufficient_observations",
    )
    fig = build_degradation_chart(stint_laps, fit)

    assert len(fig.layout.annotations) == 1
    assert "insufficient_observations" in fig.layout.annotations[0].text


def _synced_telemetry():
    return pd.DataFrame(
        {
            "Speed_a": [100.0, 200.0],
            "Speed_b": [150.0, 150.0],
            "Throttle_a": [50.0, 100.0],
            "Throttle_b": [80.0, 90.0],
            "TimeDelta_s": [0.0, -0.3],
        },
        index=pd.Index([0, 50], name="Distance"),
    )


def test_build_telemetry_channels_chart_one_subplot_per_channel():
    fig = build_telemetry_channels_chart(_synced_telemetry(), driver_a="VER", driver_b="PER")
    assert len(fig.data) == 4  # 2 channels x 2 drivers


def test_build_telemetry_channels_chart_raises_without_common_channels():
    empty = pd.DataFrame({"TimeDelta_s": [0.0]}, index=pd.Index([0], name="Distance"))
    with pytest.raises(ValueError):
        build_telemetry_channels_chart(empty)


def test_build_time_delta_chart_requires_time_delta_column():
    no_time = pd.DataFrame({"Speed_a": [1.0], "Speed_b": [1.0]}, index=pd.Index([0], name="Distance"))
    with pytest.raises(KeyError):
        build_time_delta_chart(no_time)


def test_build_time_delta_chart_basic():
    fig = build_time_delta_chart(_synced_telemetry(), driver_a="VER", driver_b="PER")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert "VER behind" in fig.layout.yaxis.title.text

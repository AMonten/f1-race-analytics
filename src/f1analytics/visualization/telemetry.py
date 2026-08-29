"""Telemetry comparison charts: driving-input channels and time delta, both against distance."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from f1analytics.analysis.telemetry import CHANNELS

CHANNEL_UNITS: dict[str, str] = {
    "Speed": "km/h",
    "Throttle": "%",
    "Brake": "",
    "RPM": "rpm",
    "nGear": "gear",
    "DRS": "",
}

DRIVER_A_COLOR = "#2a78d6"
DRIVER_B_COLOR = "#e34948"


def build_telemetry_channels_chart(
    synced: pd.DataFrame,
    driver_a: str | None = None,
    driver_b: str | None = None,
    channels: list[str] | None = None,
) -> go.Figure:
    """Stacked-subplot comparison of driving-input channels against distance.

    Args:
        synced: Output of
            `f1analytics.analysis.telemetry.synchronize_by_distance` (or
            `compare_lap_telemetry(...).synced`).
        driver_a, driver_b: Legend labels.
        channels: Which channels to plot, in order; `None` plots every
            channel from `f1analytics.analysis.telemetry.CHANNELS` present
            in `synced`.

    Returns:
        A Plotly figure with one subplot row per channel, sharing a
        distance x axis.
    """
    if channels is None:
        channels = [c for c in CHANNELS if f"{c}_a" in synced.columns and f"{c}_b" in synced.columns]
    if not channels:
        raise ValueError("No requested channel is present in `synced` for both drivers")

    label_a = driver_a or "Driver A"
    label_b = driver_b or "Driver B"

    fig = make_subplots(
        rows=len(channels),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.4 / len(channels),
        subplot_titles=channels,
    )

    for i, channel in enumerate(channels, start=1):
        fig.add_trace(
            go.Scatter(
                x=synced.index,
                y=synced[f"{channel}_a"],
                mode="lines",
                name=label_a,
                line=dict(color=DRIVER_A_COLOR, width=1.5),
                legendgroup="a",
                showlegend=(i == 1),
            ),
            row=i,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=synced.index,
                y=synced[f"{channel}_b"],
                mode="lines",
                name=label_b,
                line=dict(color=DRIVER_B_COLOR, width=1.5),
                legendgroup="b",
                showlegend=(i == 1),
            ),
            row=i,
            col=1,
        )
        fig.update_yaxes(title_text=CHANNEL_UNITS.get(channel, ""), row=i, col=1)

    fig.update_xaxes(title_text="Distance (m)", row=len(channels), col=1)
    fig.update_layout(
        height=180 * len(channels),
        title=f"Telemetry Comparison — {label_a} vs {label_b}",
        plot_bgcolor="#fcfcfb",
    )
    return fig


def build_time_delta_chart(
    synced: pd.DataFrame, driver_a: str | None = None, driver_b: str | None = None
) -> go.Figure:
    """Chart the approximate time delta (`TimeDelta_s`) over distance.

    Positive means `driver_a` had taken longer to reach that point on
    track (see `f1analytics.analysis.telemetry.compare_lap_telemetry` for
    the exact sign convention and its documented approximation caveats) —
    the y-axis title states this explicitly so the sign is never read off
    color alone.

    Raises:
        KeyError: If `synced` has no `TimeDelta_s` column (see
            `compare_lap_telemetry`, which only adds it when both laps
            have a time channel).
    """
    if "TimeDelta_s" not in synced.columns:
        raise KeyError("build_time_delta_chart requires a TimeDelta_s column")

    label_a = driver_a or "Driver A"
    label_b = driver_b or "Driver B"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=synced.index,
            y=synced["TimeDelta_s"],
            mode="lines",
            fill="tozeroy",
            line=dict(color="#52514e", width=1.5),
            name="Time delta",
            hovertemplate="Distance %{x:.0f}m: %{y:+.3f}s<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color="#c3c2b7", line_width=1)
    fig.update_xaxes(title="Distance (m)")
    fig.update_yaxes(title=f"Time delta (s) — positive = {label_a} behind")
    fig.update_layout(
        title=f"Approximate Time Delta — {label_a} vs {label_b}", plot_bgcolor="#fcfcfb"
    )
    return fig

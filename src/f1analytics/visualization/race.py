"""Race position evolution chart.

Lap on the x axis, classification position on the y axis inverted (P1 at
the top, matching how a race is actually watched), with optional shaded
Safety Car / Virtual Safety Car / yellow-flag bands and pit-stop markers.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from f1analytics.visualization import DRIVER_LINE_COLORS

# Only render bands for statuses that plausibly affect the whole field's
# racing (Yellow/SC/VSC/Red) — this mirrors what
# f1analytics.analysis.race.get_track_status_periods reports.
STATUS_BAND_COLORS: dict[str, str] = {
    "2": "rgba(237, 161, 0, 0.14)",  # Yellow flag
    "4": "rgba(227, 73, 72, 0.16)",  # Safety Car
    "5": "rgba(227, 73, 72, 0.24)",  # Red flag
    "6": "rgba(227, 73, 72, 0.10)",  # VSC deployed
    "7": "rgba(227, 73, 72, 0.06)",  # VSC ending
}


def build_position_evolution_chart(
    position_by_lap: pd.DataFrame,
    drivers: list[str] | None = None,
    track_status_periods: pd.DataFrame | None = None,
    pit_stops: pd.DataFrame | None = None,
) -> go.Figure:
    """Build the race position evolution chart.

    Args:
        position_by_lap: Output of
            `f1analytics.analysis.race.get_position_by_lap`.
        drivers: Drivers to plot; `None` plots every driver in
            `position_by_lap`. With more drivers than
            `DRIVER_LINE_COLORS` has hues, colors repeat — each line is
            still end-labelled with its driver code, so identity doesn't
            depend on color alone.
        track_status_periods: Optional output of
            `f1analytics.analysis.race.get_track_status_periods`, drawn as
            shaded vertical bands with a text label.
        pit_stops: Optional output of
            `f1analytics.analysis.pitstops.reconstruct_all_pit_stops`,
            drawn as a marker on each driver's in-lap.

    Returns:
        A Plotly figure with the Y axis inverted (P1 at the top).
    """
    if drivers is None:
        drivers = list(position_by_lap.columns)

    fig = go.Figure()

    if track_status_periods is not None:
        for _, period in track_status_periods.iterrows():
            color = STATUS_BAND_COLORS.get(str(period["status_code"]))
            if color is None:
                continue
            fig.add_vrect(
                x0=period["start_lap"] - 0.5,
                x1=period["end_lap"] + 0.5,
                fillcolor=color,
                line_width=0,
                layer="below",
                annotation_text=period["status_label"],
                annotation_position="top left",
                annotation_font_size=9,
            )

    for i, driver in enumerate(drivers):
        if driver not in position_by_lap.columns:
            continue
        series = position_by_lap[driver].dropna()
        if series.empty:
            continue
        color = DRIVER_LINE_COLORS[i % len(DRIVER_LINE_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines+markers",
                name=driver,
                line=dict(width=2, color=color),
                marker=dict(size=4, color=color),
                hovertemplate=f"{driver} — Lap %{{x}}: P%{{y}}<extra></extra>",
            )
        )
        fig.add_annotation(
            x=series.index[-1],
            y=series.values[-1],
            text=driver,
            showarrow=False,
            xanchor="left",
            xshift=6,
            font=dict(size=10, color=color),
        )

    if pit_stops is not None and not pit_stops.empty:
        relevant = pit_stops[pit_stops["driver"].isin(drivers)]
        xs, ys, texts = [], [], []
        for _, stop in relevant.iterrows():
            driver, in_lap = stop["driver"], stop["in_lap"]
            if in_lap in position_by_lap.index and pd.notna(position_by_lap.loc[in_lap, driver]):
                xs.append(in_lap)
                ys.append(position_by_lap.loc[in_lap, driver])
                texts.append(f"{driver} pit stop, lap {in_lap}")
        if xs:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers",
                    name="Pit stop",
                    marker=dict(symbol="triangle-down", size=11, color="black"),
                    hovertext=texts,
                    hoverinfo="text",
                )
            )

    fig.update_yaxes(autorange="reversed", title="Position", dtick=1, gridcolor="#e1e0d9")
    fig.update_xaxes(title="Lap", gridcolor="#e1e0d9")
    fig.update_layout(
        title="Race Position Evolution",
        hovermode="closest",
        legend_title="Driver",
        plot_bgcolor="#fcfcfb",
    )
    return fig

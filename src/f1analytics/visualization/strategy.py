"""Tyre strategy and degradation charts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from f1analytics.models.degradation import DegradationFit

# Widely-recognized dry/wet compound colors (the 2018+ F1 convention) — a
# fixed, domain-standard mapping distinct from the generic categorical set
# in f1analytics.visualization, since compound identity has its own
# convention that drivers and fans already read at a glance.
COMPOUND_COLORS: dict[str, str] = {
    "SOFT": "#e34948",
    "MEDIUM": "#eda100",
    "HARD": "#f0efec",
    "INTERMEDIATE": "#1baf7a",
    "WET": "#2a78d6",
    "UNKNOWN": "#898781",
}


def build_strategy_chart(stints: pd.DataFrame, driver_order: list[str] | None = None) -> go.Figure:
    """Build a tyre-strategy chart: one horizontal bar per stint, one row per driver.

    Args:
        stints: Output of `f1analytics.analysis.stints.reconstruct_all_stints`.
        driver_order: Drivers top-to-bottom; `None` uses the order drivers
            first appear in `stints` (sort `stints` by classification
            position before calling this to get finishing order).

    Returns:
        A Plotly horizontal bar chart, stints stacked left-to-right along
        the lap axis, colored by compound (with a legend and hover
        tooltip — color never carries compound identity alone).
    """
    if driver_order is None:
        driver_order = list(dict.fromkeys(stints["driver"]))

    fig = go.Figure()
    seen_compounds: set[str] = set()
    for _, stint in stints.sort_values(["driver", "start_lap"]).iterrows():
        compound = stint["compound"] or "UNKNOWN"
        color = COMPOUND_COLORS.get(compound, COMPOUND_COLORS["UNKNOWN"])
        show_legend = compound not in seen_compounds
        seen_compounds.add(compound)
        fig.add_trace(
            go.Bar(
                y=[stint["driver"]],
                x=[stint["length"]],
                base=[stint["start_lap"] - 1],
                orientation="h",
                name=compound,
                legendgroup=compound,
                showlegend=show_legend,
                marker=dict(color=color, line=dict(color="#0b0b0b", width=0.5)),
                hovertemplate=(
                    f"{stint['driver']} — {compound}<br>"
                    f"Laps {stint['start_lap']}-{stint['end_lap']} "
                    f"({stint['length']} laps)<extra></extra>"
                ),
            )
        )

    fig.update_yaxes(
        title="Driver", categoryorder="array", categoryarray=list(reversed(driver_order))
    )
    fig.update_xaxes(title="Lap")
    fig.update_layout(
        title="Tyre Strategy",
        barmode="stack",
        legend_title="Compound",
        plot_bgcolor="#fcfcfb",
    )
    return fig


def build_degradation_chart(
    stint_laps: pd.DataFrame, fit: DegradationFit, compound: str | None = None
) -> go.Figure:
    """Scatter of clean-lap time vs tyre age for one stint, with the fitted degradation line.

    Args:
        stint_laps: The same laps passed to
            `f1analytics.models.degradation.fit_degradation_model` — needs
            `TyreLife` and `LapTimeSeconds` columns.
        fit: The `DegradationFit` computed for those laps.
        compound: Optional compound name, used for marker color and title.

    Returns:
        A Plotly figure. If `fit.slope_s_per_lap` is `None` (no reliable
        fit — see `fit.warning`), only the scatter is drawn, with an
        annotation naming the reason instead of a fabricated line.
    """
    color = COMPOUND_COLORS.get(compound or "UNKNOWN", COMPOUND_COLORS["UNKNOWN"])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=stint_laps["TyreLife"],
            y=stint_laps["LapTimeSeconds"],
            mode="markers",
            name="Clean laps",
            marker=dict(color=color, size=9, line=dict(color="#0b0b0b", width=1)),
        )
    )

    if fit.slope_s_per_lap is not None:
        age_range = np.linspace(stint_laps["TyreLife"].min(), stint_laps["TyreLife"].max(), 20)
        fitted = fit.intercept_s + fit.slope_s_per_lap * age_range
        fig.add_trace(
            go.Scatter(
                x=age_range,
                y=fitted,
                mode="lines",
                name=(
                    f"Fit: {fit.slope_s_per_lap:+.3f} s/lap "
                    f"(R²={fit.r_squared:.2f}, n={fit.n_observations})"
                ),
                line=dict(color="#0b0b0b", dash="dash", width=2),
            )
        )
    else:
        fig.add_annotation(
            text=f"No reliable fit ({fit.warning})",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.95,
            showarrow=False,
            font=dict(color="#898781", size=11),
        )

    fig.update_xaxes(title="Tyre age (laps)")
    fig.update_yaxes(title="Lap time (s)")
    fig.update_layout(
        title=f"Tyre Degradation — {compound or 'Unknown compound'}",
        plot_bgcolor="#fcfcfb",
    )
    return fig

"""Plotly chart builders consumed by the Streamlit app.

Every function here is a pure function: DataFrame/dataclass in, a
`plotly.graph_objects.Figure` out. No Streamlit import, no FastF1 import,
no analytical computation — that lives in `f1analytics.analysis`. This
keeps charts usable from a notebook or script, not just the dashboard.
"""

from __future__ import annotations

# Colors below are a Formula 1 dashboard's two distinct categorical needs:
#
# - DRIVER_LINE_COLORS: an 8-hue, fixed-order, CVD-validated categorical
#   sequence (adjacent-pair Delta E >= 8 in OKLab, both light and dark
#   surfaces). With more series than colors (a session has up to ~20
#   drivers), colors repeat — every chart that uses this also end-labels
#   each line with its driver code, so identity never depends on color
#   alone (see f1analytics.visualization.race).
# - TEAM_COLORS: Carto's "Safe" qualitative palette (11 colors), a
#   separately published colorblind-safe set, used where every team
#   (up to 10) needs its own color in one chart — more categories than
#   DRIVER_LINE_COLORS' validated 8-slot set supports.
DRIVER_LINE_COLORS: list[str] = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

TEAM_COLORS: list[str] = [
    "#88CCEE",
    "#CC6677",
    "#DDCC77",
    "#117733",
    "#332288",
    "#AA4499",
    "#44AA99",
    "#999933",
    "#882255",
    "#661100",
    "#6699CC",
]

# Diverging pair (blue <-> red, gray midpoint) for gain/loss and delta
# charts: positive values (first pole) render blue, negative render red.
DIVERGING_COLORSCALE = [[0.0, "#e34948"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]

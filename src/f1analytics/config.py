"""Central configuration: filesystem paths and package-wide constants.

Paths default to locations inside the repository so the project works
out-of-the-box after a fresh clone, but every path can be overridden with an
environment variable for deployments where the repo tree is read-only.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR: Path = Path(os.environ.get("F1ANALYTICS_DATA_DIR", PROJECT_ROOT / "data"))

FASTF1_CACHE_DIR: Path = Path(
    os.environ.get("F1ANALYTICS_CACHE_DIR", DATA_DIR / "fastf1_cache")
)

# FastF1 provides reliable, complete session data (laps, telemetry, timing)
# starting from the 2018 season. Earlier seasons have partial or no timing data.
MIN_SUPPORTED_SEASON: int = 2018
MAX_SUPPORTED_SEASON: int = date.today().year

SESSION_TYPE_LABELS: dict[str, str] = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Q": "Qualifying",
    "SQ": "Sprint Qualifying",
    "S": "Sprint",
    "R": "Race",
}

# --- Clean-lap methodology (see f1analytics.data.preprocessing) ---

# FastF1 track-status codes that indicate the track was NOT green for the
# full duration of a lap. Any of these appearing in a lap's TrackStatus
# string is enough to exclude the lap from the "clean" set. '3' is included
# defensively even though FastF1's own docs say it has never been observed.
NON_GREEN_TRACK_STATUS_CODES: frozenset[str] = frozenset({"2", "3", "4", "5", "6", "7"})

# A lap's time is flagged as a statistical outlier if it deviates from its
# driver/stint group's median by more than this many scaled MADs (Median
# Absolute Deviations). 1.4826 * MAD approximates a normal distribution's
# standard deviation, so this multiplier is comparable to a z-score threshold.
OUTLIER_MAD_MULTIPLIER: float = 3.0

# Floor applied to the scaled MAD before comparison, so that extremely
# consistent stints (near-zero natural variance) don't get essentially every
# lap flagged as an outlier over sub-tenth differences.
OUTLIER_MIN_MAD_SECONDS: float = 0.05

# --- Tyre degradation model (see f1analytics.models.degradation) ---

# Below this many clean-lap observations, no slope can be fit at all (need
# at least 2 points to draw a line).
MIN_DEGRADATION_OBSERVATIONS: int = 2

# Below this many observations, a slope IS still fit and returned, but
# flagged with a "low_sample_size" warning rather than silently presented
# as equally reliable as a well-sampled stint.
DEGRADATION_LOW_SAMPLE_THRESHOLD: int = 5

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

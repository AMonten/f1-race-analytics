"""Distance-synchronized telemetry comparison between two laps.

FastF1 samples telemetry at irregular time (and therefore distance)
intervals, and two different laps are never sampled at the same points on
track. To compare them meaningfully — "what was each driver doing at the
same point on track" rather than "at the same elapsed time" — both laps
are linearly interpolated onto a shared, evenly-spaced distance grid. No
channel is invented: interpolation only fills gaps *between* real recorded
samples, over the distance range actually covered by both laps (their
overlap) — nothing is extrapolated beyond either lap's recorded data.

Functions here take plain telemetry DataFrames as produced by
`f1analytics.data.loader.get_lap_telemetry` — this module has no FastF1
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

DEFAULT_DISTANCE_STEP_M = 5.0

# "Driving input" channels compared side-by-side.
CHANNELS = ["Speed", "Throttle", "Brake", "RPM", "nGear", "DRS"]

# Elapsed lap time, in seconds — interpolated the same way, but used for the
# time-delta calculation rather than a driving-input comparison.
TIME_CHANNEL = "TimeSeconds"


def synchronize_by_distance(
    telemetry_a: pd.DataFrame,
    telemetry_b: pd.DataFrame,
    step_m: float = DEFAULT_DISTANCE_STEP_M,
) -> pd.DataFrame:
    """Resample two laps' telemetry onto a common, evenly-spaced distance grid.

    Args:
        telemetry_a, telemetry_b: Per-lap telemetry with at least a
            `Distance` column (see `f1analytics.data.loader.get_lap_telemetry`).
        step_m: Distance grid resolution, in metres.

    Returns:
        A DataFrame indexed by `Distance` (metres), with `<channel>_a`/
        `<channel>_b` columns for every channel present in *both* inputs
        (from `CHANNELS` and, if available, `TIME_CHANNEL`). The grid only
        spans the overlap of the two laps' recorded distance ranges.

    Raises:
        ValueError: If the two laps share no telemetry channel, or their
            recorded distance ranges don't overlap at all.
    """
    candidate_channels = CHANNELS + [TIME_CHANNEL]
    common_channels = [
        c for c in candidate_channels if c in telemetry_a.columns and c in telemetry_b.columns
    ]
    if not common_channels:
        raise ValueError("No common telemetry channels between the two laps")

    min_distance = max(telemetry_a["Distance"].min(), telemetry_b["Distance"].min())
    max_distance = min(telemetry_a["Distance"].max(), telemetry_b["Distance"].max())
    if max_distance <= min_distance:
        raise ValueError("The two laps' telemetry do not overlap in distance")

    grid = np.arange(min_distance, max_distance, step_m)

    synced = pd.DataFrame({"Distance": grid})
    for suffix, telemetry in (("a", telemetry_a), ("b", telemetry_b)):
        sorted_telemetry = telemetry.sort_values("Distance")
        for channel in common_channels:
            synced[f"{channel}_{suffix}"] = np.interp(
                grid, sorted_telemetry["Distance"], sorted_telemetry[channel]
            )
    return synced.set_index("Distance")


@dataclass
class TelemetryComparison:
    """Result of comparing two laps' telemetry, synchronized by distance."""

    driver_a: str | None
    driver_b: str | None
    synced: pd.DataFrame
    max_speed_delta_kph: float | None
    min_speed_delta_kph: float | None
    time_delta_at_finish_s: float | None


def compare_lap_telemetry(
    telemetry_a: pd.DataFrame,
    telemetry_b: pd.DataFrame,
    driver_a: str | None = None,
    driver_b: str | None = None,
    step_m: float = DEFAULT_DISTANCE_STEP_M,
) -> TelemetryComparison:
    """Synchronize two laps by distance and compute speed/time deltas.

    Adds `SpeedDelta` (`Speed_a - Speed_b`, km/h; positive means `driver_a`
    was faster at that point) to the synchronized grid, and, when a
    `TimeSeconds` channel is available for both laps, `TimeDelta_s`
    (`TimeSeconds_a - TimeSeconds_b`; **positive means `driver_a` had taken
    longer to reach that point on track, i.e. was behind/slower up to
    there**): each driver's own elapsed lap time, interpolated onto the
    same distance points. `time_delta_at_finish_s` (the value at the last
    grid point) is an **approximation** of the total time gap over the
    shared stretch of track — not the true lap-time difference, since the
    grid only covers the two laps' overlapping distance range and each
    lap's telemetry is independently resampled.

    Returns:
        A `TelemetryComparison`. `time_delta_at_finish_s` is `None` if
        neither lap has a `TimeSeconds` channel.
    """
    synced = synchronize_by_distance(telemetry_a, telemetry_b, step_m=step_m)
    synced["SpeedDelta"] = synced.get("Speed_a") - synced.get("Speed_b") if "Speed_a" in synced.columns and "Speed_b" in synced.columns else None

    time_delta_at_finish_s = None
    if f"{TIME_CHANNEL}_a" in synced.columns and f"{TIME_CHANNEL}_b" in synced.columns:
        synced["TimeDelta_s"] = synced[f"{TIME_CHANNEL}_a"] - synced[f"{TIME_CHANNEL}_b"]
        time_delta_at_finish_s = float(synced["TimeDelta_s"].iloc[-1])

    return TelemetryComparison(
        driver_a=driver_a,
        driver_b=driver_b,
        synced=synced,
        max_speed_delta_kph=float(synced["SpeedDelta"].max()) if "SpeedDelta" in synced.columns and synced["SpeedDelta"].notna().any() else None,
        min_speed_delta_kph=float(synced["SpeedDelta"].min()) if "SpeedDelta" in synced.columns and synced["SpeedDelta"].notna().any() else None,
        time_delta_at_finish_s=time_delta_at_finish_s,
    )


def identify_gain_loss_zones(synced: pd.DataFrame, noise_threshold_s: float = 0.02) -> pd.DataFrame:
    """Identify contiguous distance stretches where `driver_a` gains or loses time.

    Based on the sign of the point-to-point change in `TimeDelta_s` (see
    `compare_lap_telemetry`): a rising `TimeDelta_s` means `driver_a` is
    losing time to `driver_b` over that stretch; a falling one means
    gaining. Changes smaller than `noise_threshold_s` are treated as
    "even" to avoid fragmenting the result into many sub-metre zones driven
    by sample-to-sample telemetry noise rather than a real trend.

    This is a purely descriptive read of the recorded telemetry — it does
    not attribute *why* time was gained or lost (braking point, corner-exit
    traction, top speed, etc.); that interpretation is left to a human
    looking at the synchronized channels alongside this result.

    Args:
        synced: Output of `compare_lap_telemetry(...).synced`, i.e. must
            contain a `TimeDelta_s` column.
        noise_threshold_s: Minimum |change| in `TimeDelta_s` between
            consecutive grid points to count as a real gain/loss rather
            than noise.

    Returns:
        A DataFrame with `direction` ('gaining'/'losing'/'even'),
        `start_distance_m`, `end_distance_m`. Empty if `synced` has fewer
        than 2 rows.

    Raises:
        KeyError: If `synced` has no `TimeDelta_s` column.
    """
    if "TimeDelta_s" not in synced.columns:
        raise KeyError(
            "identify_gain_loss_zones requires a TimeDelta_s column "
            "(see compare_lap_telemetry)"
        )

    distances = synced.index.to_numpy(dtype=float)
    delta = synced["TimeDelta_s"].to_numpy()
    if len(delta) < 2:
        return pd.DataFrame(columns=["direction", "start_distance_m", "end_distance_m"])

    diffs = np.diff(delta)
    directions = np.where(
        diffs > noise_threshold_s, "losing", np.where(diffs < -noise_threshold_s, "gaining", "even")
    )

    zones = []
    start = 0
    for i in range(1, len(directions)):
        if directions[i] != directions[start]:
            zones.append(
                {
                    "direction": directions[start],
                    "start_distance_m": float(distances[start]),
                    "end_distance_m": float(distances[i]),
                }
            )
            start = i
    zones.append(
        {
            "direction": directions[start],
            "start_distance_m": float(distances[start]),
            "end_distance_m": float(distances[-1]),
        }
    )
    return pd.DataFrame(zones)

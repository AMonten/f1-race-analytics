"""Pit-stop reconstruction and approximate time-loss estimation.

A pit stop spans two lap rows in FastF1's lap table: the **in-lap** (has
`PitInTime` set — the driver enters the pit lane during this lap, ending
the outgoing stint) and the following **out-lap** (has `PitOutTime` set —
the new stint begins here). Both laps are individually much slower than a
normal racing lap, since pit-lane speed limits and the stationary tyre
change are split across the end of the in-lap and the start of the out-lap.

Approximate time-loss methodology
----------------------------------
    estimated_time_loss_s = (in_lap_time_s + out_lap_time_s) - 2 * reference_pace_s

where `reference_pace_s` is the driver's own **median clean lap time of the
stint that just ended** (reused from `f1analytics.analysis.stints`) — their
own normal pace at that point in the race, under that fuel load and tyre
wear. This estimates how much time was lost to pitting relative to if the
driver had continued racing at their own established pace.

Limitations (do not over-read this number):

- It does **not** separate pit-lane transit time from stationary
  (tyre-change) time — it is a total combined-lap estimate.
- It depends on the chosen baseline: the preceding stint's own median pace
  was chosen deliberately (over a field-wide baseline) so it reflects that
  specific driver's fuel/tyre state, but a stint with few or no clean laps
  yields no reliable baseline, and the estimate is `None` rather than
  guessed.
- It says nothing about *why* a time loss was faster or slower than
  another driver's stop (could be a slow release, traffic in the pit lane,
  a driver mistake, or track conditions) — this project does not have the
  underlying pit-lane telemetry to attribute a cause.

Position and "nearby competitors" context
-------------------------------------------
`position_before`/`position_after` report classification position at the
end of the in-lap and out-lap respectively (as FastF1 reports it — not the
exact instant of entering/exiting the pit lane). `driver_ahead_*`/
`driver_behind_*` name whichever driver held the adjacent position on that
same lap, for context. **A position change around a pit stop is not
attributed to the stop itself** — it may reflect strategy (undercut/
overcut), other cars' own stops, or unrelated on-track incidents, and this
module makes no causal claim about it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from f1analytics.analysis.race import get_position_by_lap
from f1analytics.analysis.stints import reconstruct_driver_stints


@dataclass
class PitStop:
    """One pit stop, with stint transition, position, and time-loss context."""

    driver: str
    team: str | None
    in_lap: int
    out_lap: int | None
    stint_before: int | None
    stint_after: int | None
    compound_before: str | None
    compound_after: str | None
    position_before: int | None
    position_after: int | None
    driver_ahead_before: str | None
    driver_behind_before: str | None
    driver_ahead_after: str | None
    driver_behind_after: str | None
    in_lap_time_s: float | None
    out_lap_time_s: float | None
    reference_pace_s: float | None
    estimated_time_loss_s: float | None


def _driver_at_position(
    position_by_lap: pd.DataFrame, lap_number: int | None, position: float | None
) -> str | None:
    if lap_number is None or position is None or lap_number not in position_by_lap.index:
        return None
    row = position_by_lap.loc[lap_number]
    matches = row[row == position]
    return str(matches.index[0]) if not matches.empty else None


def reconstruct_driver_pit_stops(
    flagged_laps: pd.DataFrame,
    driver: str,
    position_by_lap: pd.DataFrame | None = None,
) -> list[PitStop]:
    """Reconstruct every pit stop made by `driver` in this session.

    Args:
        flagged_laps: Session laps with clean-lap flags (only used here for
            `LapTimeSeconds`; the pit/stint/position columns are FastF1's
            raw fields, unaffected by the clean-lap flags).
        driver: Driver code, e.g. 'VER'.
        position_by_lap: Precomputed `get_position_by_lap(flagged_laps)`.
            Pass this in when reconstructing stops for many drivers, to
            avoid recomputing the pivot each time.

    Returns:
        One `PitStop` per in-lap found for `driver`, in lap order. If the
        matching out-lap can't be found (e.g. the driver retired in the
        pits), `out_lap` and every field that depends on it are `None`.
    """
    if position_by_lap is None:
        position_by_lap = get_position_by_lap(flagged_laps)

    driver_laps = flagged_laps[flagged_laps["Driver"] == driver].sort_values("LapNumber")
    team = driver_laps["Team"].iloc[0] if not driver_laps.empty and "Team" in driver_laps.columns else None
    stints_by_number = {s.stint_number: s for s in reconstruct_driver_stints(flagged_laps, driver)}

    stops: list[PitStop] = []
    for _, in_row in driver_laps[driver_laps["PitInTime"].notna()].iterrows():
        in_lap = int(in_row["LapNumber"])
        out_candidates = driver_laps[
            (driver_laps["LapNumber"] == in_lap + 1) & (driver_laps["PitOutTime"].notna())
        ]
        out_row = out_candidates.iloc[0] if not out_candidates.empty else None
        out_lap = int(out_row["LapNumber"]) if out_row is not None else None

        stint_before = int(in_row["Stint"]) if pd.notna(in_row["Stint"]) else None
        stint_after = (
            int(out_row["Stint"]) if out_row is not None and pd.notna(out_row["Stint"]) else None
        )

        position_before = int(in_row["Position"]) if pd.notna(in_row["Position"]) else None
        position_after = (
            int(out_row["Position"])
            if out_row is not None and pd.notna(out_row["Position"])
            else None
        )

        reference_stint = stints_by_number.get(stint_before)
        reference_pace_s = reference_stint.median_pace_s if reference_stint else None

        in_lap_time_s = (
            float(in_row["LapTimeSeconds"]) if pd.notna(in_row["LapTimeSeconds"]) else None
        )
        out_lap_time_s = (
            float(out_row["LapTimeSeconds"])
            if out_row is not None and pd.notna(out_row["LapTimeSeconds"])
            else None
        )

        estimated_time_loss_s = None
        if in_lap_time_s is not None and out_lap_time_s is not None and reference_pace_s is not None:
            estimated_time_loss_s = (in_lap_time_s + out_lap_time_s) - 2 * reference_pace_s

        stops.append(
            PitStop(
                driver=driver,
                team=team,
                in_lap=in_lap,
                out_lap=out_lap,
                stint_before=stint_before,
                stint_after=stint_after,
                compound_before=in_row["Compound"] if pd.notna(in_row["Compound"]) else None,
                compound_after=(
                    out_row["Compound"] if out_row is not None and pd.notna(out_row["Compound"]) else None
                ),
                position_before=position_before,
                position_after=position_after,
                driver_ahead_before=_driver_at_position(
                    position_by_lap, in_lap, (position_before - 1) if position_before else None
                ),
                driver_behind_before=_driver_at_position(
                    position_by_lap, in_lap, (position_before + 1) if position_before else None
                ),
                driver_ahead_after=_driver_at_position(
                    position_by_lap, out_lap, (position_after - 1) if position_after else None
                ),
                driver_behind_after=_driver_at_position(
                    position_by_lap, out_lap, (position_after + 1) if position_after else None
                ),
                in_lap_time_s=in_lap_time_s,
                out_lap_time_s=out_lap_time_s,
                reference_pace_s=reference_pace_s,
                estimated_time_loss_s=estimated_time_loss_s,
            )
        )
    return stops


def reconstruct_all_pit_stops(flagged_laps: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct pit stops for every driver in the session.

    Returns:
        A DataFrame with one row per pit stop, sorted by driver then
        in-lap. Empty DataFrame if no pit stops occurred.
    """
    position_by_lap = get_position_by_lap(flagged_laps)
    all_stops: list[PitStop] = []
    for driver in flagged_laps["Driver"].dropna().unique():
        all_stops.extend(
            reconstruct_driver_pit_stops(flagged_laps, driver, position_by_lap=position_by_lap)
        )

    if not all_stops:
        return pd.DataFrame()
    df = pd.DataFrame([vars(s) for s in all_stops])
    return df.sort_values(["driver", "in_lap"]).reset_index(drop=True)

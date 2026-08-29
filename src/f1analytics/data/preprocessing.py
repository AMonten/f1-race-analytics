"""Clean-lap methodology.

Every lap in a FastF1 session's lap table is a *timing record*, not
necessarily a representative measure of car/driver pace: in- and out-laps
are run at reduced pace through the pit lane, laps under Safety Car / Virtual
Safety Car / yellow-flag conditions are artificially slow, some lap times are
deleted by stewards (e.g. track-limits violations), and FastF1 itself flags
laps whose sector times don't sum consistently to the reported lap time.

This module never deletes rows. `add_lap_quality_flags` returns every input
lap unchanged plus a set of boolean flag columns explaining *why* a lap is or
isn't considered "clean". `filter_clean_laps` is a thin, explicit filter on
top of those flags — callers who want the raw data (e.g. to show a driver
their in-lap) still have it.

Methodology
-----------
A lap is flagged `IsCleanLap` only if **all** of the following hold:

1. **Has a recorded lap time** (`LapTime` is not null).
2. **Not a pit lap** — neither `PitInTime` nor `PitOutTime` is set. In- and
   out-laps are run partly in the pit lane at reduced speed and are not
   representative of racing pace.
3. **Track fully green for the whole lap** — `TrackStatus` contains no
   status code other than `'1'` (Track clear). FastF1 encodes every status
   that occurred during a lap as a concatenated digit string (e.g. `'126'`
   means the lap started green, then went yellow, then Safety Car was
   deployed), so this excludes laps affected by yellow flags, Safety Car,
   Virtual Safety Car, or red flags at any point during the lap — not only
   laps run entirely under one of those conditions. See
   `f1analytics.config.NON_GREEN_TRACK_STATUS_CODES`.
4. **Not deleted** — `Deleted` is not `True` (e.g. laps deleted by stewards
   for track-limits violations).
5. **Internally consistent** — FastF1's own `IsAccurate` flag is `True`
   (its sector times sum to within tolerance of the reported lap time).
6. **Not a statistical outlier** within its driver/stint group — see below.

### Statistical outlier detection

Grouped by `(Driver, Stint)`, so that pace differences between stints
(different tyre compound, fuel load, track evolution) don't distort the
baseline. Within each group:

- A "candidate" lap is one that already satisfies conditions 1–5 above.
- The group's baseline is the **median** lap time (seconds) of its
  candidate laps, and its spread is the **MAD** (Median Absolute
  Deviation) of those candidates, scaled by 1.4826 (the factor that makes
  MAD comparable to a standard deviation under normality), floored at
  `f1analytics.config.OUTLIER_MIN_MAD_SECONDS` so near-zero natural
  variance doesn't make every lap look like an outlier.
- A lap (candidate or not) is flagged `IsStatisticalOutlier` if its
  deviation from the group median exceeds
  `f1analytics.config.OUTLIER_MAD_MULTIPLIER` scaled MADs.
- If a group has fewer than 2 candidate laps, no baseline can be computed
  and no lap in that group is flagged as an outlier — this is a limitation
  (very short/disrupted stints get no outlier screening), not a silent
  assumption of cleanliness for the *other* flags.

This is a heuristic, not a certainty: it will occasionally flag a
legitimately fast lap on a short, fast stint, and it cannot catch every
non-representative lap (e.g. a lap that is merely a bit slower due to
traffic, without being an extreme outlier). Treat `IsCleanLap` as "safe
default sample for pace analysis", not as "every excluded lap was invalid".
"""

from __future__ import annotations

import pandas as pd

from f1analytics.config import (
    NON_GREEN_TRACK_STATUS_CODES,
    OUTLIER_MAD_MULTIPLIER,
    OUTLIER_MIN_MAD_SECONDS,
)

MAD_TO_STD_SCALE = 1.4826


def _is_track_status_clean(track_status: object) -> bool:
    """True if no non-green status code appears anywhere in the lap's TrackStatus string."""
    if not isinstance(track_status, str) or track_status == "":
        return False
    return not any(code in NON_GREEN_TRACK_STATUS_CODES for code in track_status)


def _flag_outliers(group: pd.DataFrame, candidate_mask: pd.Series) -> pd.Series:
    """Flag statistical outliers within a single (Driver, Stint) group."""
    candidates = group.loc[candidate_mask, "LapTimeSeconds"]
    if len(candidates) < 2:
        return pd.Series(False, index=group.index)

    median = candidates.median()
    mad = (candidates - median).abs().median()
    scaled_mad = max(mad * MAD_TO_STD_SCALE, OUTLIER_MIN_MAD_SECONDS)

    deviation = (group["LapTimeSeconds"] - median).abs()
    return deviation > (OUTLIER_MAD_MULTIPLIER * scaled_mad)


def add_lap_quality_flags(laps: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `laps` with clean-lap methodology flag columns added.

    Added columns: `LapTimeSeconds`, `IsPitLap`, `IsTrackStatusClean`,
    `IsDeleted`, `IsAccurate`, `IsStatisticalOutlier`, `IsCleanLap`.

    See the module docstring for the full methodology. Input rows are never
    dropped or reordered.

    Args:
        laps: A session's lap table, as returned by `fastf1.core.Session.laps`.

    Returns:
        A new DataFrame — the input `laps` is not modified.
    """
    flagged = laps.copy()

    flagged["LapTimeSeconds"] = flagged["LapTime"].dt.total_seconds()
    flagged["IsPitLap"] = flagged["PitInTime"].notna() | flagged["PitOutTime"].notna()
    flagged["IsTrackStatusClean"] = flagged["TrackStatus"].apply(_is_track_status_clean)
    flagged["IsDeleted"] = flagged["Deleted"] == True  # noqa: E712 - explicit vs. NaN/None
    flagged["IsAccurate"] = flagged["IsAccurate"] == True  # noqa: E712

    candidate_mask = (
        flagged["LapTimeSeconds"].notna()
        & ~flagged["IsPitLap"]
        & flagged["IsTrackStatusClean"]
        & ~flagged["IsDeleted"]
        & flagged["IsAccurate"]
    )

    outlier_flags = pd.Series(False, index=flagged.index)
    group_cols = ["Driver", "Stint"]
    for _, group in flagged.groupby(group_cols, sort=False):
        outlier_flags.loc[group.index] = _flag_outliers(group, candidate_mask.loc[group.index])
    flagged["IsStatisticalOutlier"] = outlier_flags

    flagged["IsCleanLap"] = candidate_mask & ~flagged["IsStatisticalOutlier"]

    return flagged


def filter_clean_laps(flagged_laps: pd.DataFrame) -> pd.DataFrame:
    """Return only the laps flagged `IsCleanLap` by `add_lap_quality_flags`.

    Args:
        flagged_laps: Output of `add_lap_quality_flags`.

    Raises:
        KeyError: If `flagged_laps` doesn't have an `IsCleanLap` column,
            i.e. `add_lap_quality_flags` was not called first.
    """
    if "IsCleanLap" not in flagged_laps.columns:
        raise KeyError(
            "filter_clean_laps requires flags from add_lap_quality_flags() first"
        )
    return flagged_laps[flagged_laps["IsCleanLap"]].copy()

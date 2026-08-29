# Changelog

Dated log of shipped milestones. See the README's Roadmap section for what's
still planned.

## 2026-08-29 — Milestone 3: Race pace and driver comparison

- `f1analytics.analysis.laps`: `get_driver_laps`/`get_clean_driver_laps`
  (raise `UnknownDriverError` on a bad driver code rather than returning a
  silently-empty result) and `fastest_lap`.
- `f1analytics.analysis.pace`: `compute_driver_race_pace` (median, mean,
  std, fastest representative lap, sample size, delta to field median, and
  the new **Race Pace Index** — `100 × field_median / driver_median` clean
  lap seconds, documented as a within-session index, not driver ability),
  `compute_field_race_pace` (whole-field table, fastest-median-first), and
  `compare_driver_pace` (median/fastest-lap/consistency deltas between two
  drivers, `None` rather than a misleading number when either driver has
  insufficient clean-lap data).
- Full methodology written up in the README's Analytical methodology
  section, including the exact index formula and its stated limitations.
- Verified against real data (2023 Bahrain GP Race): field race pace table
  correctly ranks PER/VER/ALO at the top by Race Pace Index; VER vs. PER
  comparison shows VER with a slower median (managing a comfortable lead)
  but a faster representative lap and better consistency — all directionally
  consistent with how that race actually played out.
- 14 new pytest tests (basic stats, zero/one-clean-lap edge cases, Race
  Pace Index at parity and above-field-median, field-table sorting with a
  no-clean-laps driver, comparison delta signs, comparison with missing data).

## 2026-08-29 — Milestone 2: Clean-lap methodology

- `f1analytics.data.preprocessing.add_lap_quality_flags`: flags every lap
  (never drops rows) as pit lap, non-green-track-status, deleted,
  FastF1-inaccurate, and/or a statistical outlier (>3 scaled MAD from its
  driver/stint group's median, grouped by `(Driver, Stint)` so tyre/fuel
  differences between stints don't distort the baseline), then combines
  those into a single `IsCleanLap` flag.
- `filter_clean_laps`: explicit opt-in filter on top of the flags.
- New constants in `config.py`: `NON_GREEN_TRACK_STATUS_CODES` (FastF1's
  documented track-status codes for yellow/SC/VSC/red), `OUTLIER_MAD_MULTIPLIER`,
  `OUTLIER_MIN_MAD_SECONDS`.
- Full methodology documented in the module docstring and mirrored in the
  README's Analytical methodology section.
- Verified against real data (2023 Bahrain GP Race, 1056 laps): 102 pit
  laps, 77 non-green-track-status laps, 142 FastF1-inaccurate laps, 172
  statistical outliers (concentrated on lap 1 — standing start — and around
  a mid-race Safety Car restart, as expected), 852 clean laps retained.
- 19 pytest tests covering each flag independently, per-group outlier
  scoping, the insufficient-candidates edge case, non-mutation of input,
  and both success/error paths of `filter_clean_laps`.

## 2026-08-29 — Milestone 1: Foundations

- Initial project skeleton: `src/f1analytics` package (src layout), `app/`
  for the Streamlit UI, `tests/`, `notebooks/exploration/`, `data/`
  (gitignored, holds the FastF1 cache).
- `f1analytics.data.cache`: enables FastF1's on-disk cache once per process,
  directory overridable via `F1ANALYTICS_CACHE_DIR`.
- `f1analytics.data.loader`: season/event/session discovery
  (`get_available_seasons`, `get_event_schedule`, `get_available_sessions`),
  session loading (`load_session`), and a dependency-free session summary
  (`summarize_session` → `SessionOverview`).
- Streamlit app (`app/streamlit_app.py`): season → Grand Prix → session
  picker, cached loading, and a minimal session overview (metadata, drivers,
  teams, results/classification, weather).
- Verified against real FastF1 data: 2023 Bahrain GP Race loads, caches
  correctly (~2s reload from disk vs. cold network fetch), and produces a
  correct overview.
- Test suite (pytest): cache directory management/idempotency, and
  `summarize_session` parsing logic (full data, missing results, no
  laps/results/weather, missing round number). FastF1 itself is not tested.

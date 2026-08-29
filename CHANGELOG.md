# Changelog

Dated log of shipped milestones. See the README's Roadmap section for what's
still planned.

## 2026-08-29 — Branding: project logo

- Added `assets/logo.svg` (the horizontal icon+wordmark lockup) and a
  derived square `assets/icon.svg` variant, rasterized to
  `assets/icon-64.png` (app favicon) and `assets/icon-512.png` (general
  high-res use, e.g. social previews).
- README: logo banner at the top of the file.
- App: favicon set from the icon PNG on every page; `app/state.py` gained
  `render_branding()` (calls `st.logo`, wide logo in the sidebar header,
  square icon when collapsed), called from the Overview page and all five
  analysis pages.

## 2026-08-29 — Milestone 7: Streamlit dashboard

- `f1analytics.visualization`: three chart-builder modules, each a pure
  function (DataFrame/dataclass in, `plotly.graph_objects.Figure` out, no
  Streamlit/FastF1 import):
  - `race.py`: `build_position_evolution_chart` — inverted position axis
    (P1 at top), shaded Yellow/SC/VSC/Red bands, pit-stop markers,
    end-of-line driver labels (so identity never depends on color alone
    when more drivers are plotted than the palette has hues).
  - `strategy.py`: `build_strategy_chart` (compound-colored stint bars
    across the grid) and `build_degradation_chart` (clean-lap scatter +
    fitted line, or an explicit "no reliable fit" annotation instead of a
    fabricated line).
  - `telemetry.py`: `build_telemetry_channels_chart` (stacked per-channel
    subplots) and `build_time_delta_chart` (time-delta area chart with an
    explicit sign-convention axis title).
  - Palette: an 8-hue CVD-validated categorical set for driver lines
    (Delta E >= 8 OKLab, both light/dark surfaces — from the dataviz
    skill's reference palette), Carto's "Safe" 11-color set for the
    10-team case, and a validated blue<->red diverging pair for gain/loss.
- `app/state.py`: shared Streamlit session-state/caching glue — the single
  place owning "which session is selected", FastF1 loading (cached), and
  clean-lap flagging (cached), so every page reads from one source of truth
  instead of duplicating the sidebar picker.
- Full interactive dashboard: `app/streamlit_app.py` (Overview: session
  picker + methodology summary) plus five pages — **Race Pace**, **Tyres &
  Stints**, **Position & Pit Stops**, **Qualifying** (gracefully declines on
  non-qualifying sessions), and **Telemetry** (loads on demand — the only
  page that needs the heavier telemetry=True session load, cached once and
  shared across both compared drivers).
- Verified with `streamlit.testing.v1.AppTest` against real cached FastF1
  data (2023 Bahrain GP Race and Qualifying, including telemetry) for every
  page, plus a full `streamlit run` boot check — no exceptions, correct
  page-type handling (e.g. Qualifying page on a Race session).
- 11 new pytest tests for the chart builders (structural: trace counts,
  axis config, error paths) and 7 for the Streamlit pages themselves
  (via AppTest with synthetic data injected through monkeypatched
  `app/state.py` accessors — no network or FastF1 dependency, consistent
  with "don't test FastF1 itself").

## 2026-08-29 — Milestone 6: Qualifying and telemetry analysis

- `f1analytics.data.loader`: `get_qualifying_segment_labels` (wraps
  FastF1's `Laps.split_qualifying_sessions()`, which needs session-timing
  context beyond the lap table — the one FastF1-touching helper qualifying
  analysis depends on), `get_lap_telemetry` (car data + computed `Distance`,
  as a plain DataFrame; `Time` converted to float `TimeSeconds`), and
  `get_driver_fastest_lap_telemetry` convenience wrapper.
- `f1analytics.analysis.qualifying`: `is_valid_qualifying_lap` (timed, not
  pit/deleted, FastF1-accurate — deliberately does NOT exclude fast
  statistical outliers, unlike the race clean-lap methodology, since
  setting an exceptional lap is the point of qualifying),
  `compute_qualifying_classification` (gap to pole, sector times, sorted),
  `get_segment_progression` (Q1/Q2/Q3), `compare_teammates` (only pairs
  teams with exactly two drivers present), and `compare_two_laps` (sector
  and lap-time deltas between any two laps).
- `f1analytics.analysis.telemetry`: `synchronize_by_distance` (interpolates
  two laps' telemetry onto a shared evenly-spaced distance grid, covering
  only their recorded overlap — nothing extrapolated or fabricated),
  `compare_lap_telemetry` (adds `SpeedDelta` and an approximate
  `TimeDelta_s`/`time_delta_at_finish_s`, with documented sign conventions
  and explicit "this is approximate, not the true lap-time difference"
  caveat), and `identify_gain_loss_zones` (sign-of-slope read of the time
  delta, noise-thresholded, explicitly described as descriptive only — no
  causal attribution of *why* time was gained or lost).
- Full methodology documented in both module docstrings and the README.
- Verified against real data (2023 Bahrain GP Qualifying): reconstructed
  classification exactly matches the actual historical result (VER pole
  1:29.708, PER +0.138s, LEC +0.292s, SAI +0.446s, ALO/RUS ~+0.63s);
  VER-vs-PER telemetry comparison gave an approximate time delta (-0.244s)
  consistent with their real 0.138s qualifying gap, within the expected
  approximation error from only covering the two laps' overlapping
  distance range.
- 21 new pytest tests (qualifying: valid-lap filtering including the
  fast-outlier-not-excluded case, best-lap lookup, classification sorting/
  gap-to-pole/sector times, segment progression, teammate pairing,
  two-lap comparison; telemetry: distance synchronization and its overlap/
  no-common-channel error cases, speed and time delta sign conventions,
  gain/loss zone detection and its edge cases).

## 2026-08-29 — Milestone 5: Race position evolution and pit-stop analysis

- `f1analytics.analysis.race`: `get_position_by_lap` pivots a session's
  laps into a lap-number × driver position grid (the shape needed for the
  future position-evolution chart); `get_track_status_periods` detects
  contiguous lap ranges under each non-green FastF1 track-status code
  (Yellow/Safety Car/VSC/Red), using the field-wide union of every
  driver's `TrackStatus` per lap so a single driver's timing lag can't
  hide an incident.
- `f1analytics.analysis.pitstops`: `reconstruct_driver_pit_stops`/
  `reconstruct_all_pit_stops` build `PitStop` records — stint/compound
  transition, position before/after, the driver holding the adjacent
  track position (context only, no causal claim about *why* position
  changed), and an approximate pit-stop time-loss estimate:
  `(in_lap_time + out_lap_time) - 2 × reference_pace`, where
  `reference_pace` is the driver's own median clean lap of the stint that
  just ended (reused from Milestone 4's `stints.py`). `None` rather than a
  guess when the preceding stint has too few clean laps for a reliable
  baseline, or the out-lap can't be found (e.g. retired in the pits).
- New config constant: `TRACK_STATUS_LABELS` (human-readable names for all
  7 FastF1 track-status codes).
- Full methodology documented in both module docstrings and the README,
  including the explicit limitation that the time-loss estimate combines
  pit-lane transit and stationary time rather than separating them, and
  cannot attribute *why* a stop was fast or slow.
- Verified against real data (2023 Bahrain GP Race): both of VER's pit
  stops estimated at ~23-24s time loss (matches Bahrain's known pit-lane
  loss); the field-wide 50-stop time-loss distribution had a 23.9s median
  with a plausible long tail (double-stacked/SC-affected stops); detected
  incident periods (Yellow laps 1-2 and 39-41, VSC laps 40-42) line up
  exactly with the statistical outlier laps flagged back in Milestone 2's
  validation — closing the loop between the two milestones.
- 13 new pytest tests (position grid pivoting/missing data, track-status
  period detection — contiguous ranges, cross-driver union, all-green,
  non-contiguous ranges — and pit-stop reconstruction: basic fields,
  time-loss arithmetic, nearby-competitor lookups, missing out-lap,
  no-stops case, field-wide aggregation).

## 2026-08-29 — Milestone 4: Tyres, stints and degradation model

- `f1analytics.analysis.stints`: `reconstruct_driver_stints`/
  `reconstruct_all_stints` build `Stint` records (compound, start/end lap,
  length, tyre age start/end from FastF1's `TyreLife`, clean-lap count,
  median pace, pace variation) from every lap of a driver, grouped by
  FastF1's own `Stint` counter. Laps with a missing `Stint` value are
  excluded rather than mis-attributed.
- `f1analytics.models.degradation`: `fit_degradation_model` — OLS fit of
  `LapTime = α + β × TyreAge` via `scipy.stats.linregress`, returning
  sample size, intercept, slope, R², p-value, and std error. Returns
  `None` regression fields with an explicit `warning` when there are fewer
  than 2 observations (`"insufficient_observations"`) or no variation in
  tyre age (`"no_tyre_age_variation"`); flags (but still fits and returns)
  `"low_sample_size"` below 5 observations.
- `f1analytics.analysis.tyres`: `compute_stint_degradation`/
  `compute_driver_degradation`/`compute_field_degradation` — fit the
  degradation model per driver/stint using that stint's clean laps only
  (reusing the Milestone 2 clean-lap flags rather than a new filter).
- New dependency: `scipy>=1.11` (justified by needing OLS regression with
  significance/goodness-of-fit statistics, not just a raw slope).
- New config constants: `MIN_DEGRADATION_OBSERVATIONS`,
  `DEGRADATION_LOW_SAMPLE_THRESHOLD`.
- Full methodology documented in both module docstrings and the README,
  including the explicit statement that tyre age is not implied to be the
  only cause of lap-time evolution (fuel burn-off, track evolution,
  traffic, and pace management are all entangled in the fitted slope).
- Verified against real data (2023 Bahrain GP Race): 70 stints
  reconstructed across the grid (35 Soft / 34 Hard / 1 Medium stints,
  consistent with the race's real two-stop strategies); VER's first
  (11-lap Soft) stint showed a small but statistically significant
  degradation slope (~0.066 s/lap, R²=0.88), while shorter later stints
  showed flat, non-significant slopes — directionally sensible.
- 17 new pytest tests (degradation fit correctness on synthetic
  known-slope data, all warning paths, NaN handling; stint reconstruction
  shape/pace-stats/missing-stint-data edge cases; per-driver and
  field-level degradation wrappers).

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

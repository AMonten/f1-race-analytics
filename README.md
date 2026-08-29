<p align="center">
  <img src="assets/logo.svg" alt="F1 Race Analytics" width="480">
</p>

# F1 Race Analytics

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Milestone%207%20%E2%80%94%20dashboard-yellow)
![Built with FastF1](https://img.shields.io/badge/data-FastF1-e10600)

> **Unofficial project.** This is not affiliated with, endorsed by, or connected
> to Formula 1, the FIA, Formula One World Championship Limited, or any team.
> It is an independent analytics tool built on top of the public [FastF1](https://docs.fastf1.dev/)
> library.

## 1. Project description

F1 Race Analytics ingests historical Formula 1 session data and turns it into
reusable analytical datasets: clean lap classifications, representative race
pace, tyre-stint reconstructions, degradation estimates, pit-stop timing, and
telemetry comparisons. A Streamlit dashboard sits on top of that analytical
core so the results are explorable interactively, but the analysis itself is
plain, tested Python that can also be used from a notebook or script.

The question the project tries to answer, for any given session, is:

> **What happened during this Formula 1 session, and what does the data tell
> us about driver and team performance?**

## 2. Motivation

Most public F1 dashboards are either fan-facing visualizations or one-off
notebooks that don't survive past a single Grand Prix weekend. This project
is built as a proper, maintainable analytics application: a clear separation
between data ingestion, analysis, and presentation; a documented methodology
for every derived metric; and enough test coverage that the analytical code
can be trusted and extended.

## 3. Screenshots

_Screenshots will be added at the v1.0 tag (Milestone 8) once the UI is in its final polished state — the dashboard itself is fully functional as of Milestone 7 (`streamlit run app/streamlit_app.py`)._

## 4. Architecture

```
f1-race-analytics/
│
├── app/
│   ├── streamlit_app.py     # Overview page: session selection + summary
│   ├── state.py             # shared session-state/caching glue (UI-only, no analysis)
│   └── pages/
│       ├── 1_Race_Pace.py
│       ├── 2_Tyres_and_Stints.py
│       ├── 3_Position_and_Pitstops.py
│       ├── 4_Qualifying.py
│       └── 5_Telemetry.py
│
├── src/
│   └── f1analytics/
│       ├── config.py          # paths, supported seasons, constants
│       ├── data/
│       │   ├── loader.py      # the only module that talks to FastF1
│       │   ├── cache.py       # FastF1 on-disk cache management
│       │   └── preprocessing.py   # clean-lap methodology (flags, never drops rows)
│       │
│       ├── analysis/
│       │   ├── laps.py        # per-driver lap slicing, fastest-lap lookup
│       │   ├── pace.py        # representative race pace, driver comparison
│       │   ├── stints.py      # tyre stint reconstruction
│       │   ├── tyres.py       # per-stint/field tyre degradation fitting
│       │   ├── race.py        # lap-by-driver position grid, SC/VSC periods
│       │   ├── pitstops.py    # pit-stop reconstruction, approx. time loss
│       │   ├── qualifying.py  # classification, Q1/Q2/Q3, teammate/lap comparison
│       │   └── telemetry.py   # distance-synchronized telemetry comparison
│       ├── models/
│       │   └── degradation.py # LapTime = α + β×TyreAge linear fit (scipy)
│       └── visualization/
│           ├── race.py        # position evolution chart
│           ├── strategy.py    # tyre strategy + degradation charts
│           └── telemetry.py   # telemetry channel + time-delta charts
│
├── tests/                     # pytest — analytical logic, not FastF1 itself
├── notebooks/exploration/     # scratch analysis, not shipped code
├── data/                      # FastF1 cache lives here, gitignored
├── assets/                    # logo/icon (README + app favicon/sidebar branding)
└── pyproject.toml / requirements.txt
```

**Design rule:** `f1analytics.data` is the only layer that imports `fastf1`.
Analytical modules consume plain `pandas` DataFrames and dataclasses, so a
different or additional data provider could be introduced later without
rewriting `analysis/`, `models/`, or `visualization/`. The Streamlit app
only renders — it calls into `f1analytics` for every computation.

## 5. Features

Implemented so far (Milestone 1):

- [x] Season / Grand Prix / session selection, driven by FastF1's live event schedule
- [x] FastF1 on-disk caching (sessions are fetched once, reused afterwards)
- [x] Session overview: event metadata, drivers, teams, results/classification, weather summary

Implemented (Milestone 2):

- [x] Clean-lap methodology: every lap flagged (not dropped) for pit-lap,
  non-green track status, deletion, FastF1 accuracy, and statistical
  outlier status — see [Analytical methodology](#8-analytical-methodology)

Implemented (Milestone 3):

- [x] Representative race pace per driver (median, mean, std, fastest
  representative lap, sample size, delta to field median, Race Pace Index)
- [x] Two-driver pace comparison (median/fastest-lap/consistency deltas)

Implemented (Milestone 4):

- [x] Tyre stint reconstruction (compound, lap range, length, tyre age,
  median pace, pace variation) for any driver or the whole grid
- [x] Tyre degradation model: `LapTime = α + β × TyreAge`, fit per
  driver/stint with sample size, R², p-value and low-sample warnings

Implemented (Milestone 5):

- [x] Race position evolution data (lap-by-driver position grid) and
  Safety Car / Virtual Safety Car / yellow-flag period detection
- [x] Pit-stop reconstruction: stint transition, position before/after,
  nearby competitors, and approximate pit-stop time loss

Implemented (Milestone 6):

- [x] Qualifying classification with gap to pole, sector times, Q1/Q2/Q3
  progression, teammate comparison, and detailed two-lap comparison
- [x] Distance-synchronized telemetry comparison (speed/throttle/brake/RPM/
  gear/DRS), with speed deltas, an approximate time-delta-over-the-lap, and
  gain/loss zone detection

Implemented (Milestone 7):

- [x] Full interactive Streamlit dashboard: an Overview page (session
  selection + methodology summary) plus five analysis pages — Race Pace,
  Tyres & Stints, Position & Pit Stops, Qualifying, and Telemetry — each
  backed entirely by `f1analytics.analysis`/`visualization` functions
- [x] Race position evolution chart (inverted position axis, SC/VSC/yellow
  shading, pit-stop markers, per-driver selection)
- [x] Tyre strategy chart (compound-colored stint bars across the grid)
  and an interactive per-stint degradation scatter + fit line
- [x] Distance-synchronized telemetry charts (per-channel comparison,
  time-delta area chart, gain/loss zone table)

Planned (see [Roadmap](#11-roadmap)):

- [ ] A unified two-driver comparison view bringing pace + stints + telemetry together in one place (each is already viewable independently)

## 6. Installation

Requires Python 3.10+ (3.11+ preferred).

```bash
git clone https://github.com/AMonten/f1-race-analytics.git
cd f1-race-analytics

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

This installs the `f1analytics` package in editable mode plus `pytest`. If
you'd rather not install the package, `pip install -r requirements.txt` gives
you the same runtime + dev dependencies.

## 7. Usage

Launch the dashboard:

```bash
streamlit run app/streamlit_app.py
```

Then, in the browser tab that opens: on the **Overview** page, pick a
**season**, **Grand Prix**, and **session** in the sidebar, and click
**Load session**. The first load for a given session downloads data from
FastF1 and caches it under `data/fastf1_cache/`; subsequent loads of the
same session are near-instant. Once loaded, use the page navigation
(sidebar) to move between:

- **Race Pace** — field ranking, Race Pace Index, two-driver comparison
- **Tyres & Stints** — strategy chart across the grid, per-stint degradation
- **Position & Pit Stops** — position evolution chart, pit-stop table
- **Qualifying** — classification, Q1/Q2/Q3, teammate comparison (only for
  Qualifying/Sprint Qualifying/Sprint Shootout sessions)
- **Telemetry** — distance-synchronized comparison between two drivers'
  fastest laps (loads on demand — heavier than the rest of the app)

The cache location can be overridden with an environment variable, e.g. to
share a cache across projects:

```bash
export F1ANALYTICS_CACHE_DIR=/path/to/shared/cache
```

You can also use the ingestion layer directly, outside Streamlit:

```python
from f1analytics.data import loader

session = loader.load_session(2023, "Bahrain", "Race")
overview = loader.summarize_session(session)
print(overview.event_name, overview.total_laps, overview.drivers)
```

Or compute race pace directly:

```python
from f1analytics.data.preprocessing import add_lap_quality_flags
from f1analytics.analysis.pace import compute_field_race_pace, compare_driver_pace

flagged = add_lap_quality_flags(session.laps)
field_pace = compute_field_race_pace(flagged)          # one row per driver
comparison = compare_driver_pace(flagged, "VER", "PER")  # head-to-head deltas
```

Or reconstruct tyre stints and fit the degradation model:

```python
from f1analytics.analysis.stints import reconstruct_all_stints
from f1analytics.analysis.tyres import compute_field_degradation

stints = reconstruct_all_stints(flagged)          # one row per (driver, stint)
degradation = compute_field_degradation(flagged)  # one row per (driver, stint), with slope/R²/warnings
```

Or reconstruct position evolution and pit stops:

```python
from f1analytics.analysis.race import get_position_by_lap, get_track_status_periods
from f1analytics.analysis.pitstops import reconstruct_all_pit_stops

position_grid = get_position_by_lap(flagged)        # lap number x driver -> classification position
incidents = get_track_status_periods(flagged)       # Yellow/SC/VSC/Red lap ranges
pit_stops = reconstruct_all_pit_stops(flagged)       # one row per stop, with estimated time loss
```

Or analyze a qualifying session and compare telemetry between two laps:

```python
from f1analytics.analysis.qualifying import compute_qualifying_classification, compare_teammates
from f1analytics.analysis.telemetry import compare_lap_telemetry, identify_gain_loss_zones

quali_session = loader.load_session(2023, "Bahrain", "Qualifying")
quali_flagged = add_lap_quality_flags(quali_session.laps)
quali_flagged["QualifyingSegment"] = loader.get_qualifying_segment_labels(quali_session)

classification = compute_qualifying_classification(quali_flagged)  # gap to pole, sector times
teammates = compare_teammates(quali_flagged)

telemetry_session = loader.load_session(2023, "Bahrain", "Qualifying", telemetry=True)
tel_a = loader.get_driver_fastest_lap_telemetry(telemetry_session, "VER")
tel_b = loader.get_driver_fastest_lap_telemetry(telemetry_session, "PER")
comparison = compare_lap_telemetry(tel_a, tel_b, driver_a="VER", driver_b="PER")
zones = identify_gain_loss_zones(comparison.synced)  # where VER gains/loses time on PER
```

Run the test suite:

```bash
pytest
```

## 8. Analytical methodology

Documented as each milestone lands so the methodology is never separated
from the code that implements it:

- **Session overview** — read directly from FastF1's event schedule, session
  results, and weather data. No derived statistics; see
  `f1analytics.data.loader.summarize_session`.

- **Clean-lap methodology** — a lap is flagged `IsCleanLap` only if it (1)
  has a recorded lap time, (2) is not a pit in/out lap, (3) has no
  non-green FastF1 track-status code (yellow flag, Safety Car, Virtual
  Safety Car, or red flag) anywhere during the lap, (4) was not deleted by
  stewards, (5) is flagged `IsAccurate` by FastF1 itself (sector times sum
  consistently), and (6) is not a statistical outlier relative to its own
  driver/stint group — computed as more than 3 scaled Median Absolute
  Deviations from that group's median lap time, with the MAD floored at
  0.05s so ultra-consistent stints aren't over-flagged, and skipped
  entirely for groups with fewer than 2 candidate laps.
  **No lap is ever deleted** — `add_lap_quality_flags` returns every input
  row plus these flag columns, so raw data (e.g. a driver's own in-lap) is
  always still available. See the full methodology and its documented
  limitations in the `f1analytics.data.preprocessing` module docstring —
  in particular, this heuristic can occasionally flag a legitimately fast
  lap on a short stint, and does not catch every non-representative lap
  (e.g. ordinary traffic-related loss that isn't extreme enough to trip the
  MAD threshold).

- **Race pace and Race Pace Index** — computed exclusively from clean laps
  (see above). For each driver: median, mean, and standard deviation of
  clean lap time, the fastest *representative* lap (fastest among clean
  laps — not necessarily the outright fastest lap of the session, which may
  have been set under conditions the clean-lap methodology excludes), the
  number of clean-lap observations, and the delta to the field median.
  The **Race Pace Index** is defined as:

  ```
  RacePaceIndex = 100 × field_median_clean_lap_seconds / driver_median_clean_lap_seconds
  ```

  where the field median is computed over every clean lap set by every
  driver in the session (not the median of per-driver medians). 100 means
  the driver's median clean lap matched the field median; above 100 means
  faster than the field median; below 100 means slower. **This index mixes
  car performance, tyre strategy, fuel load, and traffic — it is not a
  normalized measure of driver skill**, and figures from different
  sessions or seasons are not comparable to each other. See
  `f1analytics.analysis.pace` for the full docstring, `DriverRacePace`, and
  `DriverPaceComparison` (which reports median/fastest-lap/consistency
  deltas between two drivers rather than two independent numbers).

- **Tyre stint reconstruction** — a stint is a continuous run on one set of
  tyres, identified by FastF1's own per-lap `Stint` counter. Stints are
  built from *all* of a driver's laps (so the lap range and transitions are
  correct), but `median_pace_s`/`pace_variation_s` are computed from that
  stint's clean laps only, consistent with the rest of the pace
  methodology. Tyre age uses FastF1's `TyreLife` directly (not a
  recomputed lap-in-stint counter), so a stint started on a used
  ("non-fresh") set of tyres is represented correctly. See
  `f1analytics.analysis.stints`.

- **Tyre degradation model** — a simple linear fit,
  `LapTime = α + β × TyreAge`, computed independently per driver/stint via
  ordinary least squares (`scipy.stats.linregress`), using only that
  stint's clean laps (the same "appropriate lap" criteria as the rest of
  the project, not a bespoke filter). Every fit reports its sample size,
  R², and p-value, and is flagged `"low_sample_size"` below 5 observations
  or `"insufficient_observations"`/`"no_tyre_age_variation"` when no slope
  can be fit at all — never silently presented as more reliable than it is.
  **This model does not separate tyre degradation from fuel burn-off,
  track evolution, traffic, or deliberate pace management** — all of these
  also move lap times over a stint and are entangled in the fitted slope.
  A single stint on one compound at one circuit on one day is a small
  sample: treat the slope as describing *that stint*, not a compound's
  general degradation characteristics. See
  `f1analytics.models.degradation` for the full docstring and
  `f1analytics.analysis.tyres` for the driver/stint/field-level wrappers.

- **Race position evolution / track-status periods** — the position grid
  is a direct pivot of FastF1's per-lap `Position` column (no derived
  statistics). Track-status incident periods (Yellow flag, Safety Car,
  Virtual Safety Car, Red flag) are detected using the *field-wide union*
  of every driver's `TrackStatus` string per lap (more robust than trusting
  a single driver's record, since timing can lag slightly around a status
  change) — the same status codes used by the clean-lap methodology. See
  `f1analytics.analysis.race`.

- **Pit-stop time-loss estimation** —
  `estimated_time_loss_s = (in_lap_time_s + out_lap_time_s) - 2 × reference_pace_s`,
  where `reference_pace_s` is the driver's own median *clean* lap time from
  the stint that just ended (not a field-wide baseline, so it reflects that
  driver's specific fuel load and tyre wear at that point in the race).
  This is a combined estimate of pit-lane transit **and** stationary time —
  it does not separate the two, and the estimate is `None` (not guessed)
  when the preceding stint had too few clean laps to establish a reliable
  baseline. Pit stops also report position before/after and whichever
  driver held the adjacent track position at that lap, purely as context:
  **a position change around a pit stop is not attributed to the stop
  itself** — it may reflect strategy (undercut/overcut), a rival's own
  stop, or an unrelated incident, and this project does not claim to know
  which. See `f1analytics.analysis.pitstops` for the full docstring.

- **Qualifying classification** — uses a deliberately different "valid
  lap" filter than race pace: timed, not a pit lap, not deleted, and
  FastF1-accurate — but, unlike the race clean-lap methodology, an
  unusually **fast** lap is never excluded as a statistical outlier
  (setting an exceptional lap is the entire point of qualifying). Q1/Q2/Q3
  splitting uses FastF1's own `Laps.split_qualifying_sessions()` (which
  needs session-timing context beyond the lap table itself, so it lives in
  `f1analytics.data.loader.get_qualifying_segment_labels`, the one
  fastf1-touching exception to this analysis module). Teammate comparison
  only pairs teams with exactly two drivers present — a mid-season
  replacement or data gap is skipped rather than guessed at. See
  `f1analytics.analysis.qualifying`.

- **Telemetry comparison** — two laps are never sampled at the same points
  on track, so both are linearly interpolated onto a shared, evenly-spaced
  distance grid (5m steps by default) covering only their *overlapping*
  recorded range — nothing is extrapolated beyond either lap's real data,
  and no channel is fabricated beyond what FastF1 provides. From this:
  `SpeedDelta` at every point, and (when both laps have a time channel) an
  approximate `TimeDelta_s` — each driver's own elapsed lap time
  interpolated onto the same distance points, so their difference
  approximates the time gap at each point on track. This is explicitly an
  **approximation**, not the true lap-time difference: it only covers the
  overlapping distance range, and each lap is independently resampled.
  Gain/loss zones are a simple sign-of-slope read of that time delta (with
  a small noise threshold to avoid fragmenting on sample-to-sample
  telemetry noise) — a purely descriptive summary that does **not**
  attribute *why* time was gained or lost. See
  `f1analytics.analysis.telemetry` for the full docstring and exact sign
  conventions.

## 9. Data source

All F1 session data is retrieved through [FastF1](https://docs.fastf1.dev/),
an open-source Python library that provides access to official F1 timing,
telemetry, and session data. This project only uses documented, supported
FastF1 APIs — it does not scrape the official F1 website. FastF1 has
reliable, complete data from the **2018 season onward**; earlier seasons are
intentionally excluded from the season selector rather than exposing partial
data silently.

## 10. Limitations

- Data completeness depends entirely on what FastF1 exposes for a given
  session — some practice sessions have limited or no telemetry/weather data.
- Historical timing data occasionally contains known FastF1/upstream quirks
  (missing sectors, timing gaps around red flags); these are not silently
  patched — see the methodology docs for how each analysis handles them.
- Derived metrics (race pace, degradation) describe the session analyzed,
  not a driver's or team's general ability — sample sizes are always shown.
- No live/real-time session support — this is a historical-data analysis tool.

## 11. Roadmap

Development proceeds in milestones; see [`CHANGELOG.md`](CHANGELOG.md) *(added
once the first milestone commit lands)* for what's shipped.

1. ~~Project structure, FastF1 ingestion, caching, session selection~~ ✅
2. ~~Lap preprocessing and clean-lap methodology~~ ✅
3. ~~Race pace and driver comparison~~ ✅
4. ~~Tyres, stints and degradation model~~ ✅
5. ~~Race position evolution and pit-stop analysis~~ ✅
6. ~~Qualifying and telemetry analysis~~ ✅
7. ~~Streamlit UX and visualization refinement~~ ✅
8. Testing, documentation, and v1.0 release

V1.0 is feature-complete when a user can select a historical Grand Prix,
reconstruct its position evolution, inspect tyre strategy, compare two
drivers, calculate race pace, inspect stint degradation, compare telemetry,
and analyze qualifying — all backed by documented methodology. After v1.0,
this repository enters maintenance mode; strategy simulation is planned as a
**separate** future project rather than an ever-expanding addition to this one.

## 12. Project status

**Milestone 7 of 8 — interactive dashboard complete.** Every analysis
module is now reachable in the running Streamlit app: session Overview,
Race Pace, Tyres & Stints, Position & Pit Stops, Qualifying, and
Telemetry — each page a thin UI layer over the tested
`f1analytics.analysis`/`visualization` modules. Everything described in the
[Roadmap](#11-roadmap)'s v1.0 criteria is usable by someone cloning the
repo today. What's left for v1.0 (Milestone 8): a final pass over the test
suite and code for release quality, screenshots, and tagging.

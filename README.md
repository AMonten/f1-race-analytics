# F1 Race Analytics

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Milestone%203%20%E2%80%94%20race%20pace-yellow)
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

_Screenshots will be added once the dashboard UI is further along (Milestone 7)._

## 4. Architecture

```
f1-race-analytics/
│
├── app/
│   ├── streamlit_app.py     # UI wiring only — no analytical logic
│   └── pages/                # additional Streamlit pages (later milestones)
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
│       │   └── ...            # tyres, stints, pit stops, qualifying, telemetry (later milestones)
│       ├── models/            # (Milestone 4) tyre degradation regression
│       └── visualization/     # (Milestone 5+) Plotly chart builders
│
├── tests/                     # pytest — analytical logic, not FastF1 itself
├── notebooks/exploration/     # scratch analysis, not shipped code
├── data/                      # FastF1 cache lives here, gitignored
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

Planned (see [Roadmap](#11-roadmap)):

- [ ] Race position evolution with pit-stop and SC/VSC markers
- [ ] Full two-driver comparison (strategy, stints, telemetry — pace comparison already implemented)
- [ ] Tyre stint reconstruction and a simple degradation model
- [ ] Pit-stop timing and approximate time-loss analysis
- [ ] Qualifying analysis (Q1/Q2/Q3, sector times, lap comparison)
- [ ] Distance-synchronized telemetry comparison

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

Then, in the browser tab that opens: pick a **season**, **Grand Prix**, and
**session** in the sidebar, and click **Load session**. The first load for a
given session downloads data from FastF1 and caches it under
`data/fastf1_cache/`; subsequent loads of the same session are near-instant.

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

- **Tyre degradation model, pit-stop time-loss estimation** — to be
  documented here as Milestone 4 is implemented. Every derived metric will
  state precisely what is included/excluded, why, and what it does *not*
  claim to prove.

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
4. Tyres, stints and degradation model
5. Race position evolution and pit-stop analysis
6. Qualifying and telemetry analysis
7. Streamlit UX and visualization refinement
8. Testing, documentation, and v1.0 release

V1.0 is feature-complete when a user can select a historical Grand Prix,
reconstruct its position evolution, inspect tyre strategy, compare two
drivers, calculate race pace, inspect stint degradation, compare telemetry,
and analyze qualifying — all backed by documented methodology. After v1.0,
this repository enters maintenance mode; strategy simulation is planned as a
**separate** future project rather than an ever-expanding addition to this one.

## 12. Project status

**Milestone 3 of 8 — race pace and driver comparison.** Project structure,
FastF1 ingestion, caching, session selection, the clean-lap methodology, and
representative race pace (including the Race Pace Index and two-driver pace
comparison) are implemented and tested. Not yet ready for general use as an
analytics tool — tyre/stint, pit-stop, qualifying, and telemetry analysis,
and the interactive dashboard sections for all of the above, are still to
come.

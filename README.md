# F1 Race Analytics

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Milestone%201%20%E2%80%94%20foundations-yellow)
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
│       │   └── preprocessing.py   # (Milestone 2) clean-lap methodology
│       │
│       ├── analysis/          # (Milestones 2–6) pace, tyres, stints,
│       │                      # pit stops, qualifying, telemetry
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

Planned (see [Roadmap](#11-roadmap)):

- [ ] Race position evolution with pit-stop and SC/VSC markers
- [ ] Clean-lap methodology and lap-time analysis
- [ ] Race Pace Index and driver/field pace comparisons
- [ ] Two-driver comparison (pace, consistency, strategy, telemetry)
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
- **Clean-lap classification, Race Pace Index, tyre degradation model,
  pit-stop time-loss estimation** — to be documented here as Milestones 2–4
  are implemented. Every derived metric will state precisely what is
  included/excluded, why, and what it does *not* claim to prove (in
  particular: race pace and degradation figures describe performance
  *within the selected session*, not a general measure of driver or tyre
  ability).

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
2. Lap preprocessing and clean-lap methodology
3. Race pace and driver comparison
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

**Milestone 1 of 8 — foundations.** Project structure, FastF1 ingestion,
caching, and session selection are implemented and tested. Not yet ready for
general use as an analytics tool — the analytical sections described above
are still to come.

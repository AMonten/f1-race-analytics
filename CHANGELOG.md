# Changelog

Dated log of shipped milestones. See the README's Roadmap section for what's
still planned.

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

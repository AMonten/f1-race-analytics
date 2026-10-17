"""Full-throttle vs rest-of-lap time loss: Alonso vs the pole lap, 2026 qualifying.

Reproduces (and checks) the method of Mark Hughes' article in The Race,
"The extraordinary figures hinting at Aston Martin's pole potential"
(2026-10-16): split the gap between Alonso's best qualifying lap and the pole
lap into time lost on full-throttle sections vs. everywhere else.

Data comes from the public OpenF1 API (https://openf1.org), not FastF1: FastF1
returned no car telemetry for 2026 Singapore qualifying. This script is a
standalone case study and deliberately does not import `f1analytics` — the
package's "only `data/` talks to the data source" rule is untouched.

Two alignment methods are implemented, because the difference between them
*is* the finding:

- ``speed`` (v1, flawed): lap distance obtained by integrating each car's
  speed trace. Small errors accumulate differently for each car, so braking
  points end up a few metres apart; that shifts time between corners and
  straights and makes the car look faster than pole in the corners.
- ``gps`` (v2, used for the published numbers): lap distance taken from
  the pole car's x/y path; Alonso's x/y samples are projected onto that path,
  so both laps share the same distance reference.

"Full throttle" = the pole car's throttle >= 98 % at that point on track.

Usage:
    python analysis.py                 # GPS method, writes results.csv
    python analysis.py --method speed  # the original v1 method, for comparison
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE.parent.parent / "data" / "openf1_cache"  # data/* is gitignored
API = "https://api.openf1.org/v1/"
ALONSO = 14
FULL_THROTTLE_PCT = 98

# OpenF1 qualifying session keys — the tracks The Race analysed (since the
# Hungary upgrade).
SESSIONS = {
    "Hungaroring": 11338,
    "Zandvoort": 11349,
    "Monza": 11357,
    "Madrid": 11365,
    "Baku": 11373,
    "Sepang": 11730,
    "Singapore": 11384,
}

# The Race's published figures: (full-throttle loss, rest-of-lap loss), seconds.
THE_RACE = {
    "Hungaroring": (1.291, 1.310),
    "Zandvoort": (1.476, 1.011),
    "Monza": (3.127, 0.237),
    "Madrid": (2.561, 1.003),
    "Baku": (1.854, 2.203),
    "Sepang": (2.238, -0.148),
    "Singapore": (3.220, -0.370),
}


def get(path: str):
    """GET an OpenF1 endpoint, cached on disk; backs off on HTTP 429."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / (hashlib.md5(path.encode()).hexdigest() + ".json")
    if cached.exists():
        return json.loads(cached.read_text())
    for attempt in range(8):
        try:
            with urllib.request.urlopen(API + path, timeout=60) as resp:
                data = json.load(resp)
            cached.write_text(json.dumps(data))
            time.sleep(0.6)
            return data
        except Exception as exc:  # noqa: BLE001 — retried, re-raised below
            last = exc
            time.sleep(5 + attempt * 5)
    raise last


def best_lap(session_key: int, driver: int) -> dict:
    laps = [
        lap
        for lap in get(f"laps?session_key={session_key}&driver_number={driver}")
        if lap["lap_duration"]
    ]
    return min(laps, key=lambda lap: lap["lap_duration"])


def lap_samples(endpoint: str, session_key: int, driver: int, lap: dict) -> pd.DataFrame:
    """`car_data` or `location` samples for one lap, with `t` = seconds since lap start."""
    t0 = datetime.fromisoformat(lap["date_start"])
    t1 = t0 + timedelta(seconds=lap["lap_duration"])
    pad = timedelta(seconds=1)
    query = (
        f"{endpoint}?session_key={session_key}&driver_number={driver}"
        f"&date>={(t0 - pad).isoformat()}&date<={(t1 + pad).isoformat()}"
    ).replace("+00:00", "")
    df = pd.DataFrame(get(query))
    df["t"] = (pd.to_datetime(df["date"], format="ISO8601") - pd.Timestamp(t0)).dt.total_seconds()
    return df.sort_values("t").reset_index(drop=True)


def distance_from_speed(car: pd.DataFrame, lap_s: float, n: int = 4000):
    """v1: (time grid, distance in metres) by integrating speed. Flawed — see module docstring."""
    tg = np.linspace(0, lap_s, n)
    v = np.interp(tg, car.t, car.speed) / 3.6
    dist = np.concatenate([[0], np.cumsum((v[1:] + v[:-1]) / 2 * np.diff(tg))])
    return tg, dist


def align_speed(pole_car, alo_car, pole_lap, alo_lap):
    tP, sP = distance_from_speed(pole_car, pole_lap["lap_duration"])
    tA, sA = distance_from_speed(alo_car, alo_lap["lap_duration"])
    sA = sA * sP[-1] / sA[-1]  # stretch to the same lap length
    return tP, sP, tA, sA


def align_gps(pole_loc, alo_loc, pole_lap, alo_lap, n: int = 6000):
    """v2: pole path from x/y; each Alonso sample projected onto the nearest pole-path point.

    OpenF1 x/y are in decimetres, so distances are converted to metres.
    """
    tP = np.linspace(0, pole_lap["lap_duration"], n)
    px, py = np.interp(tP, pole_loc.t, pole_loc.x), np.interp(tP, pole_loc.t, pole_loc.y)
    sP = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))]) / 10

    tA = np.linspace(0, alo_lap["lap_duration"], n)
    ax, ay = np.interp(tA, alo_loc.t, alo_loc.x), np.interp(tA, alo_loc.t, alo_loc.y)
    sA = np.empty(n)
    j = 0
    for i in range(n):  # search a local window so the projection can't jump across the track
        lo, hi = max(0, j - 50), min(n, j + 300)
        j = lo + int(np.argmin((px[lo:hi] - ax[i]) ** 2 + (py[lo:hi] - ay[i]) ** 2))
        sA[i] = sP[j]
    sA = np.maximum.accumulate(sA)
    keep = np.concatenate([[True], np.diff(sA) > 0])
    return tP, sP, tA[keep], sA[keep]


def analyse(track: str, session_key: int, method: str) -> dict:
    pole = get(f"session_result?session_key={session_key}&position=1")[0]["driver_number"]
    pole_lap, alo_lap = best_lap(session_key, pole), best_lap(session_key, ALONSO)
    pole_car = lap_samples("car_data", session_key, pole, pole_lap)
    alo_car = lap_samples("car_data", session_key, ALONSO, alo_lap)
    if method == "gps":
        pole_loc = lap_samples("location", session_key, pole, pole_lap)
        alo_loc = lap_samples("location", session_key, ALONSO, alo_lap)
        tP, sP, tA, sA = align_gps(pole_loc, alo_loc, pole_lap, alo_lap)
    else:
        tP, sP, tA, sA = align_speed(pole_car, alo_car, pole_lap, alo_lap)

    grid = np.arange(0, sP[-1], 0.2 if method == "gps" else 2.0)
    time_pole, time_alo = np.interp(grid, sP, tP), np.interp(grid, sA, tA)
    delta = time_alo - time_pole
    delta -= delta[0]
    step = np.diff(delta, prepend=0)
    throttle_pole = np.interp(time_pole, pole_car.t, pole_car.throttle)
    full = throttle_pole >= FULL_THROTTLE_PCT

    pole_code = get(f"drivers?session_key={session_key}&driver_number={pole}")[0]["name_acronym"]
    return {
        "track": track,
        "pole_driver": pole_code,
        "pole_lap_s": pole_lap["lap_duration"],
        "alonso_lap_s": alo_lap["lap_duration"],
        "official_gap_s": round(alo_lap["lap_duration"] - pole_lap["lap_duration"], 3),
        "computed_gap_s": round(float(delta[-1]), 3),
        "full_throttle_loss_s": round(float(step[full].sum()), 3),
        "rest_of_lap_loss_s": round(float(step[~full].sum()), 3),
        "full_throttle_loss_95_s": round(float(step[throttle_pole >= 95].sum()), 3),
        "full_throttle_loss_99_s": round(float(step[throttle_pole >= 99].sum()), 3),
        "the_race_full_throttle_s": THE_RACE[track][0],
        "the_race_rest_of_lap_s": THE_RACE[track][1],
        # per-metre series, used by slides.py
        "_distance_m": grid,
        "_delta_s": delta,
        "_full_throttle": full,
        "_speed_pole": np.interp(time_pole, pole_car.t, pole_car.speed),
        "_speed_alo": np.interp(time_alo, alo_car.t, alo_car.speed),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--method", choices=["gps", "speed"], default="gps")
    args = parser.parse_args()

    results = [analyse(track, key, args.method) for track, key in SESSIONS.items()]
    table = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in results])
    print(table.to_string(index=False))

    suffix = "" if args.method == "gps" else "_v1_speed"
    table.to_csv(HERE / f"results{suffix}.csv", index=False)
    with open(CACHE_DIR / f"series{suffix}.pkl", "wb") as fh:
        pickle.dump({r["track"]: r for r in results}, fh)


if __name__ == "__main__":
    main()

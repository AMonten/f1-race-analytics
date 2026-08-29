"""Tests for f1analytics.analysis.telemetry."""

from __future__ import annotations

import pandas as pd
import pytest

from f1analytics.analysis.telemetry import (
    compare_lap_telemetry,
    identify_gain_loss_zones,
    synchronize_by_distance,
)


def _telemetry(distance, speed=None, time_seconds=None, throttle=None):
    data = {"Distance": distance}
    if speed is not None:
        data["Speed"] = speed
    if time_seconds is not None:
        data["TimeSeconds"] = time_seconds
    if throttle is not None:
        data["Throttle"] = throttle
    return pd.DataFrame(data)


def test_synchronize_by_distance_interpolates_on_common_grid():
    tel_a = _telemetry([0, 10, 20], speed=[100.0, 200.0, 300.0])
    tel_b = _telemetry([0, 10, 20], speed=[150.0, 150.0, 150.0])

    synced = synchronize_by_distance(tel_a, tel_b, step_m=10)

    assert list(synced.index) == [0, 10]
    assert synced.loc[0, "Speed_a"] == 100.0
    assert synced.loc[10, "Speed_a"] == 200.0
    assert synced.loc[0, "Speed_b"] == 150.0


def test_synchronize_by_distance_only_covers_overlap():
    tel_a = _telemetry([0, 10, 20], speed=[100.0, 100.0, 100.0])
    tel_b = _telemetry([5, 15, 25], speed=[100.0, 100.0, 100.0])

    synced = synchronize_by_distance(tel_a, tel_b, step_m=5)

    assert synced.index.min() >= 5
    assert synced.index.max() < 20


def test_synchronize_by_distance_raises_on_no_overlap():
    tel_a = _telemetry([0, 10], speed=[100.0, 100.0])
    tel_b = _telemetry([100, 110], speed=[100.0, 100.0])

    with pytest.raises(ValueError):
        synchronize_by_distance(tel_a, tel_b)


def test_synchronize_by_distance_raises_on_no_common_channels():
    tel_a = pd.DataFrame({"Distance": [0, 10]})
    tel_b = pd.DataFrame({"Distance": [0, 10]})

    with pytest.raises(ValueError):
        synchronize_by_distance(tel_a, tel_b)


def test_compare_lap_telemetry_speed_delta():
    # step_m=50 over a [0, 100) overlap grids only at distances 0 and 50.
    tel_a = _telemetry([0, 50, 100], speed=[100.0, 200.0, 300.0])
    tel_b = _telemetry([0, 50, 100], speed=[150.0, 150.0, 150.0])

    result = compare_lap_telemetry(tel_a, tel_b, driver_a="A", driver_b="B", step_m=50)

    assert result.max_speed_delta_kph == pytest.approx(50.0)  # at distance 50: 200-150
    assert result.min_speed_delta_kph == pytest.approx(-50.0)  # at distance 0: 100-150


def test_compare_lap_telemetry_time_delta_sign_convention():
    # Driver A reaches distance 50 in 1.0s; driver B takes 1.2s -> A is ahead there.
    # step_m=50 over a [0, 100) overlap only grids at distances 0 and 50.
    tel_a = _telemetry([0, 50, 100], speed=[100.0] * 3, time_seconds=[0.0, 1.0, 2.0])
    tel_b = _telemetry([0, 50, 100], speed=[100.0] * 3, time_seconds=[0.0, 1.2, 2.5])

    result = compare_lap_telemetry(tel_a, tel_b, step_m=50)

    assert result.time_delta_at_finish_s == pytest.approx(1.0 - 1.2)
    assert result.time_delta_at_finish_s < 0  # A took less time to reach distance 50


def test_compare_lap_telemetry_none_time_delta_when_no_time_channel():
    tel_a = _telemetry([0, 50], speed=[100.0, 100.0])
    tel_b = _telemetry([0, 50], speed=[100.0, 100.0])

    result = compare_lap_telemetry(tel_a, tel_b, step_m=50)

    assert result.time_delta_at_finish_s is None


def test_identify_gain_loss_zones_detects_losing_then_gaining():
    tel_a = _telemetry([0, 10, 20, 30], speed=[100.0] * 4, time_seconds=[0.0, 0.5, 1.5, 1.5])
    tel_b = _telemetry([0, 10, 20, 30], speed=[100.0] * 4, time_seconds=[0.0, 0.1, 0.2, 1.0])

    result = compare_lap_telemetry(tel_a, tel_b, step_m=10)
    zones = identify_gain_loss_zones(result.synced, noise_threshold_s=0.01)

    assert set(zones["direction"]) <= {"losing", "gaining", "even"}
    assert "losing" in zones["direction"].values  # A falls behind between 0 and 20


def test_identify_gain_loss_zones_requires_time_delta_column():
    synced = pd.DataFrame({"Speed_a": [1, 2], "Speed_b": [1, 2]}, index=pd.Index([0, 10], name="Distance"))
    with pytest.raises(KeyError):
        identify_gain_loss_zones(synced)


def test_identify_gain_loss_zones_empty_for_single_row():
    synced = pd.DataFrame({"TimeDelta_s": [0.0]}, index=pd.Index([0], name="Distance"))
    zones = identify_gain_loss_zones(synced)
    assert zones.empty

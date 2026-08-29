"""Tests for f1analytics.models.degradation."""

from __future__ import annotations

import numpy as np
import pytest

from f1analytics.models.degradation import fit_degradation_model


def test_fit_recovers_known_slope_and_intercept():
    age = np.arange(1, 11)
    lap_time = 90.0 + 0.15 * age  # perfect linear relationship, no noise

    fit = fit_degradation_model(age, lap_time)

    assert fit.n_observations == 10
    assert fit.warning is None
    assert fit.intercept_s == pytest.approx(90.0)
    assert fit.slope_s_per_lap == pytest.approx(0.15)
    assert fit.r_squared == pytest.approx(1.0)


def test_insufficient_observations_returns_none_fields():
    fit = fit_degradation_model([1.0], [90.0])

    assert fit.n_observations == 1
    assert fit.warning == "insufficient_observations"
    assert fit.slope_s_per_lap is None
    assert fit.r_squared is None


def test_no_observations_returns_none_fields():
    fit = fit_degradation_model([], [])

    assert fit.n_observations == 0
    assert fit.warning == "insufficient_observations"


def test_constant_tyre_age_returns_no_variation_warning():
    fit = fit_degradation_model([5.0, 5.0, 5.0], [90.0, 90.5, 89.8])

    assert fit.warning == "no_tyre_age_variation"
    assert fit.slope_s_per_lap is None


def test_low_sample_size_is_flagged_but_still_fit():
    age = [1.0, 2.0, 3.0]
    lap_time = [90.0, 90.2, 90.4]

    fit = fit_degradation_model(age, lap_time)

    assert fit.n_observations == 3
    assert fit.warning == "low_sample_size"
    assert fit.slope_s_per_lap is not None


def test_nan_observations_are_dropped_before_fitting():
    age = [1.0, 2.0, float("nan"), 4.0, 5.0, 6.0]
    lap_time = [90.0, 90.2, 99.0, 90.6, 90.8, 91.0]

    fit = fit_degradation_model(age, lap_time)

    assert fit.n_observations == 5
    assert fit.warning is None

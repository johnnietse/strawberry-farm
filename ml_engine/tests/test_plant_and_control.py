"""Plant model physics, the lighting task, the exported policy and the controller decision.
Run from ml_engine/: python -m pytest tests"""
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from biology_engine import compute_state  # noqa: E402
from controller import decide  # noqa: E402
from forecaster import PersistenceForecaster  # noqa: E402
from greenhouse_env import LightingTask, TaskConfig, Weather, in_dark_period  # noqa: E402
from plant_model import (LedParams, LightMix, PlantParams, ambient_ppfd_from_lux, canopy, led_light,  # noqa: E402
                         leaf_photosynthesis, vpd_kpa)
from policy import load_policy  # noqa: E402


def test_vpd_known_value():
    # saturation vapour pressure at 25 C is 3.17 kPa (FAO-56 table 2.3)
    assert vpd_kpa(25, 0) == pytest.approx(3.17, abs=0.01)
    assert vpd_kpa(25, 100) == 0


def test_light_response_rises_and_saturates_in_strawberry_range():
    a = [leaf_photosynthesis(q * 0.85, 25, 1.0).an for q in (0, 100, 300, 600, 1000, 1500, 2000)]
    assert a[0] < 0                               # dark respiration
    assert all(x <= y for x, y in zip(a, a[1:]))  # never less with more light (flat once Rubisco-limited)
    assert a[1] < a[2] < a[3] < a[4]               # rises through the light-limited range
    assert 14 <= a[-2] <= 20                      # light-saturated rate reported for strawberry
    assert a[-1] - a[-2] < 1.0                    # saturated


def test_co2_and_temperature_responses():
    co2 = [leaf_photosynthesis(1200, 25, 1, co2=c).an for c in (200, 400, 800, 1200)]
    assert all(x < y for x, y in zip(co2, co2[1:]))
    temp = {t: leaf_photosynthesis(1200, t, 1).an for t in range(5, 46, 5)}
    t_opt = max(temp, key=temp.get)
    assert 20 <= t_opt <= 32 and temp[45] < temp[t_opt] / 2


def test_stomatal_model_is_consistent_with_fick_law():
    leaf = leaf_photosynthesis(800, 25, 1.2)
    # A = gs / 1.6 * (Ca - Ci) with g0 = 0
    assert leaf.an == pytest.approx(leaf.gs / 1.6 * (420 - leaf.ci), rel=1e-6)


def test_red_photons_are_used_better_than_blue():
    blue = leaf_photosynthesis(80, 25, 1, rqe=0.73).an
    red = leaf_photosynthesis(80, 25, 1, rqe=0.95).an
    assert red > blue


def test_canopy_transpiration_rises_with_light_and_vpd():
    low = canopy(LightMix(sun=200), 22, 75).transpiration_g_m2_h
    bright = canopy(LightMix(sun=1000), 22, 75).transpiration_g_m2_h
    dry = canopy(LightMix(sun=1000), 22, 45).transpiration_g_m2_h
    assert 0 < low < bright < dry


def test_lux_conversion_removes_led_share():
    led = LedParams()
    sun_lux = 300 * 54.0
    mix = led_light(50, 50, led)
    measured = sun_lux + mix.blue * 9.0 + mix.red * 10.0
    assert ambient_ppfd_from_lux(measured, 50, 50, led) == pytest.approx(300, rel=1e-6)


def test_dark_period_wraps_midnight():
    cfg = TaskConfig(dark_start_h=22, dark_end_h=6)
    assert in_dark_period(23, cfg) and in_dark_period(3, cfg) and not in_dark_period(12, cfg)


def test_lighting_pays_on_a_dark_day_and_is_forced_off_at_night():
    task = LightingTask()
    rng = np.random.default_rng(3)
    w = Weather.random_day(rng)
    w.sun_ppfd[:] = 0                              # closed phytotron
    off = task.run_day(w, lambda o, k, w: (0, 0))
    on = task.run_day(w, lambda o, k, w: (100, 100))
    assert on["reward"] > off["reward"] and on["dli"] > off["dli"]
    assert task.safe_action(23.0, 22, 100, 100) == (0.0, 0.0)
    assert task.safe_action(12.0, 35, 100, 100) == (0.0, 0.0)


def test_trained_policy_loads_and_is_competitive():
    policy = load_policy()
    assert policy is not None, "models/led_policy.npz missing: run train_rl.py"
    import json
    with open(os.path.join(os.path.dirname(__file__), "..", "models", "led_policy_eval.json")) as f:
        res = json.load(f)["results"]
    # within 2 % of the model-based optimiser, far better than leaving the LEDs off
    assert res["ppo"]["reward"] >= res["greedy_model"]["reward"] * 1.02
    assert res["ppo"]["reward"] > res["off"]["reward"]
    for obs in np.random.default_rng(0).uniform(-1, 1, (20, 10)):
        b, r = policy.act(obs)
        assert 0 <= b <= 100 and 0 <= r <= 100


def test_controller_respects_photoperiod_and_lights_dark_day():
    task = LightingTask()
    policy = load_policy()
    for pol in (policy, None):
        b, r, _ = decide(task, pol, 23.5, 0.0, 22.0, 70.0, 5.0, (0, 0))
        assert (b, r) == (0.0, 0.0)
        b, r, _ = decide(task, pol, 10.0, 0.0, 22.0, 70.0, 2.0, (0, 0))
        assert b + r > 100            # a dark morning with a low light integral: light it


def test_biology_engine_state_and_light_integral():
    now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
    reading = {"temp_c": 22.0, "humidity_pct": 70.0, "par_umol": 300.0, "light_lux": None}
    s1 = compute_state(reading, (50, 50), None, now, timezone.utc)
    assert s1["ppfd_ambient"] == 300 and s1["ppfd_led"] == 60 and s1["an_umol"] > 0
    prev = (datetime(2026, 11, 15, 11, 59, tzinfo=timezone.utc), 1.0, 300.0, 60.0)
    s2 = compute_state(reading, (50, 50), prev, now, timezone.utc)
    assert s2["dli_mol"] == pytest.approx(1.0 + 360 * 60 / 1e6)
    assert compute_state({**reading, "temp_c": None}, (0, 0), None, now, timezone.utc) is None


def test_node_par_sensor_reading_has_the_led_share_removed():
    """Rev 3.2: the node's quantum sensor sees daylight plus the LED board; the engine keeps
    only daylight as ambient PPFD (the LED share is added back from the LED level)."""
    now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
    node = {"temp_c": 22.0, "humidity_pct": 70.0, "par_umol": 360.0, "par_source": "node", "light_lux": 9000}
    s = compute_state(node, (50, 50), None, now, timezone.utc)
    assert s["ppfd_ambient"] == 300 and s["ppfd_led"] == 60
    dark = compute_state({**node, "par_umol": 40.0}, (50, 50), None, now, timezone.utc)
    assert dark["ppfd_ambient"] == 0                      # never negative
    other = compute_state({**node, "par_source": None}, (50, 50), None, now, timezone.utc)
    assert other["ppfd_ambient"] == 360                   # a separate PAR instrument: as measured


def test_led_parameters_for_the_667_ma_option():
    from plant_model import LedParams
    lo, hi = LedParams.for_current(333), LedParams.for_current(667)
    assert hi.blue_ppfd_100 == 2 * lo.blue_ppfd_100 and hi.blue_watts_100 > 2 * lo.blue_watts_100 * 0.9
    with pytest.raises(ValueError):
        LedParams.for_current(500)


def test_persistence_forecast_shape():
    p = PersistenceForecaster().predict(np.array([[20, 21, 22], [60, 61, 62]]), 4)
    assert p.shape == (2, 4) and (p[0] == 22).all()

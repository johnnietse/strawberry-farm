"""
Greenhouse lighting environment for the LED controller.

One LED driver board lighting one canopy patch, one day per episode, one decision every
10 minutes. Daylight, temperature and humidity follow a random diurnal pattern; the plant
responds through `plant_model.canopy`. The agent picks the blue and red LED levels.

Reward per step (dollars, so the trade-off is explicit and every weight is a named setting):
    value of CO2 fixed by the canopy patch
  - electricity used by the LED board
  - penalty when LEDs are on with too little blue in the total light (below `min_blue_fraction`
    plants stretch; red-only light is known to cause abnormal growth)
  - penalty at the end of the day if the daily light integral (DLI) is below `dli_min`
The same rules the gateway's safety monitor enforces (dark period, over-temperature cut-off)
are applied here, so the policy learns inside the limits it will meet in service.

The core (`LightingTask`) is plain numpy so the controller service can use it without
gymnasium; `GreenhouseLightingEnv` wraps it for training.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from plant_model import (LedParams, LightMix, PlantParams, canopy, led_light, led_power_w,
                         vpd_kpa)

STEP_MIN = 10
STEPS_PER_DAY = 24 * 60 // STEP_MIN


@dataclass(frozen=True)
class TaskConfig:
    value_per_g_co2: float = 0.01     # $ per g CO2 fixed (sets how much light is worth)
    price_per_kwh: float = 0.15       # $ per kWh
    min_blue_fraction: float = 0.12   # blue photons / all photons while the LEDs are on
    blue_penalty: float = 0.002       # $ per step per 0.1 below the minimum
    dli_min: float = 12.0             # mol m-2 day-1, lower end of the strawberry range (12 to 17)
    dli_penalty: float = 0.02         # $ per mol m-2 below dli_min at the end of the day
    dark_start_h: float = 22.0        # photoperiod: LEDs forced off from 22:00 ...
    dark_end_h: float = 6.0           # ... to 06:00 (16 h day)
    t_cutoff_c: float = 32.0          # LEDs forced off above this air temperature
    co2_ppm: float = 420.0


def in_dark_period(hour: float, cfg: TaskConfig) -> bool:
    s, e = cfg.dark_start_h, cfg.dark_end_h
    return (s <= hour or hour < e) if s > e else (s <= hour < e)


@dataclass
class Weather:
    """One day of exogenous conditions at STEP_MIN resolution."""
    sun_ppfd: np.ndarray
    temp_c: np.ndarray
    rh_pct: np.ndarray

    @classmethod
    def random_day(cls, rng: np.random.Generator) -> "Weather":
        t = np.arange(STEPS_PER_DAY) * STEP_MIN / 60.0
        # daylight: 0 (closed phytotron) to a bright greenhouse day, with passing clouds
        peak = rng.choice([0.0, rng.uniform(50, 300), rng.uniform(300, 1200)], p=[0.2, 0.4, 0.4])
        sunrise, sunset = rng.uniform(5.5, 7.5), rng.uniform(17, 20)
        frac = np.clip((t - sunrise) / (sunset - sunrise), 0, 1)
        sun = peak * np.sin(np.pi * frac) ** 1.5
        clouds = np.clip(1 - 0.6 * np.abs(np.convolve(rng.normal(0, 0.5, t.size), np.ones(6) / 6, "same")), 0.2, 1)
        sun = sun * clouds
        tmean, tamp = rng.uniform(17, 26), rng.uniform(1, 6)
        temp = tmean + tamp * np.sin(2 * np.pi * (t - 9) / 24) + rng.normal(0, 0.3, t.size)
        rh = np.clip(rng.uniform(55, 80) - 1.5 * (temp - tmean) + rng.normal(0, 1.5, t.size), 30, 98)
        return cls(sun, temp, rh)


class LightingTask:
    """Plain-numpy core: step a day with given LED actions and score it."""

    OBS_SIZE = 10

    def __init__(self, cfg: TaskConfig = TaskConfig(), plant: PlantParams = PlantParams(),
                 led: LedParams = LedParams()):
        self.cfg, self.plant, self.led = cfg, plant, led

    def safe_action(self, hour: float, temp_c: float, blue_pct: float, red_pct: float):
        if in_dark_period(hour, self.cfg) or temp_c > self.cfg.t_cutoff_c:
            return 0.0, 0.0
        return float(np.clip(blue_pct, 0, 100)), float(np.clip(red_pct, 0, 100))

    def step_reward(self, sun: float, temp: float, rh: float, blue_pct: float, red_pct: float):
        """Reward for one STEP_MIN step with the given (already safe) LED levels.
        Returns (reward, info)."""
        cfg = self.cfg
        mix = led_light(blue_pct, red_pct, self.led)
        light = LightMix(sun, mix.blue, mix.red)
        c = canopy(light, temp, rh, cfg.co2_ppm, self.plant)
        c0 = canopy(LightMix(sun), temp, rh, cfg.co2_ppm, self.plant) if (blue_pct or red_pct) else c
        dt = STEP_MIN * 60.0
        gain_g = max(c.an - c0.an, 0.0) * 44.01e-6 * dt * self.led.area_m2   # extra CO2 from the LEDs
        energy_kwh = led_power_w(blue_pct, red_pct, self.led) * dt / 3.6e6
        reward = gain_g * cfg.value_per_g_co2 - energy_kwh * cfg.price_per_kwh
        if blue_pct + red_pct > 0 and light.blue_fraction < cfg.min_blue_fraction:
            reward -= cfg.blue_penalty * (cfg.min_blue_fraction - light.blue_fraction) / 0.1
        info = {"an": c.an, "an_no_led": c0.an, "ppfd": light.total, "blue_fraction": light.blue_fraction,
                "energy_kwh": energy_kwh, "gain_g": gain_g, "transpiration_g_m2_h": c.transpiration_g_m2_h}
        return reward, info

    def observe(self, step: int, w: Weather, dli: float, last: tuple[float, float]) -> np.ndarray:
        hour = step * STEP_MIN / 60.0
        i = min(step, STEPS_PER_DAY - 1)
        return np.array([
            math.sin(2 * math.pi * hour / 24), math.cos(2 * math.pi * hour / 24),
            w.sun_ppfd[i] / 1000.0, w.temp_c[i] / 40.0, w.rh_pct[i] / 100.0,
            vpd_kpa(w.temp_c[i], w.rh_pct[i]) / 3.0, dli / self.cfg.dli_min,
            last[0] / 100.0, last[1] / 100.0, 0.0 if in_dark_period(hour, self.cfg) else 1.0,
        ], dtype=np.float32)

    def run_day(self, w: Weather, policy) -> dict:
        """Run a day with `policy(obs, step, weather) -> (blue_pct, red_pct)`; return totals."""
        dli, last, total, kwh, gain = 0.0, (0.0, 0.0), 0.0, 0.0, 0.0
        for k in range(STEPS_PER_DAY):
            hour = k * STEP_MIN / 60.0
            obs = self.observe(k, w, dli, last)
            b, r = policy(obs, k, w)
            b, r = self.safe_action(hour, w.temp_c[k], b, r)
            rew, info = self.step_reward(w.sun_ppfd[k], w.temp_c[k], w.rh_pct[k], b, r)
            dli += info["ppfd"] * STEP_MIN * 60 / 1e6
            total += rew
            kwh += info["energy_kwh"]
            gain += info["gain_g"]
            last = (b, r)
        total -= self.cfg.dli_penalty * max(self.cfg.dli_min - dli, 0.0)
        return {"reward": total, "dli": dli, "kwh": kwh, "co2_gain_g": gain}

    def greedy_action(self, hour: float, sun: float, temp: float, rh: float, dli_so_far: float = 0.0,
                      levels=(0, 25, 50, 75, 100)):
        """Model-based baseline: the LED setting that maximises this step's reward (grid search).
        Adds a small bonus toward the DLI floor late in the photoperiod."""
        if self.safe_action(hour, temp, 100, 100) == (0.0, 0.0):
            return 0.0, 0.0
        best, best_r = (0.0, 0.0), -1e9
        for b in levels:
            for r in levels:
                rew, info = self.step_reward(sun, temp, rh, b, r)
                rew += self.cfg.dli_penalty * info["ppfd"] * STEP_MIN * 60 / 1e6 * (dli_so_far < self.cfg.dli_min)
                if rew > best_r:
                    best, best_r = (float(b), float(r)), rew
        return best


try:
    import gymnasium as gym
    from gymnasium import spaces

    class GreenhouseLightingEnv(gym.Env):
        metadata = {"render_modes": []}

        def __init__(self, cfg: TaskConfig = TaskConfig(), seed: int | None = None):
            super().__init__()
            self.task = LightingTask(cfg)
            self.observation_space = spaces.Box(-2.0, 2.0, (LightingTask.OBS_SIZE,), np.float32)
            # actions in [-1, 1] (PPO works best with symmetric bounds), mapped to 0..100 %
            self.action_space = spaces.Box(-1.0, 1.0, (2,), np.float32)
            self._rng = np.random.default_rng(seed)

        def reset(self, seed=None, options=None):
            super().reset(seed=seed)
            if seed is not None:
                self._rng = np.random.default_rng(seed)
            self.w = (options or {}).get("weather") or Weather.random_day(self._rng)
            self.k, self.dli, self.last = 0, 0.0, (0.0, 0.0)
            return self.task.observe(0, self.w, 0.0, self.last), {}

        def step(self, action):
            a = (np.clip(action, -1, 1) + 1) * 50.0
            hour = self.k * STEP_MIN / 60.0
            b, r = self.task.safe_action(hour, self.w.temp_c[self.k], a[0], a[1])
            # wasted request in the dark period: small penalty so the policy learns the schedule
            wasted = (b, r) == (0.0, 0.0) and float(a.sum()) > 5.0
            rew, info = self.task.step_reward(self.w.sun_ppfd[self.k], self.w.temp_c[self.k], self.w.rh_pct[self.k], b, r)
            rew -= 0.0002 * wasted
            self.dli += info["ppfd"] * STEP_MIN * 60 / 1e6
            self.last = (b, r)
            self.k += 1
            done = self.k >= STEPS_PER_DAY
            if done:
                rew -= self.task.cfg.dli_penalty * max(self.task.cfg.dli_min - self.dli, 0.0)
            obs = self.task.observe(self.k, self.w, self.dli, self.last)
            # scale rewards up: per-step values are fractions of a cent
            return obs, float(rew * 100.0), done, False, info
except ImportError:  # gymnasium is only needed for training
    GreenhouseLightingEnv = None

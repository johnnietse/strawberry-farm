"""
Charts for the documentation, written to docs/images/ml/:
  plant_response.png     leaf photosynthesis vs light (3 temperatures) and vs temperature
  led_policy_day.png     one held-out day: daylight and LED light, LED levels chosen by PPO
  policy_comparison.png  daily reward of each LED policy on 60 held-out days
  forecast_error.png     VPD forecast error vs lead time for each forecast backend
  forecast_example.png   one temperature forecast: Chronos-Bolt Tiny and persistence vs measured

    python plot_results.py          (needs matplotlib; the forecast charts need torch + chronos)
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from greenhouse_env import STEP_MIN, LightingTask, Weather  # noqa: E402
from plant_model import leaf_photosynthesis, led_light  # noqa: E402
from policy import load_policy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "images", "ml")

# Reference palette (validated: CVD separation and normal-vision floor pass on #fcfcfb)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#1f1f1e", "#5f5e58", "#e6e5e0"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"   # blue, orange, aqua, yellow
LED_BLUE, LED_RED = "#2a78d6", "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlecolor": INK,
    "axes.titlelocation": "left", "lines.linewidth": 2, "legend.frameon": False,
})


def label_end(ax, x, y, text, color, dy=0):
    ax.annotate(text, (x, y), xytext=(6, dy), textcoords="offset points", va="center",
                color=INK, fontsize=9)
    ax.plot([x], [y], "o", ms=5, color=color, mec=SURFACE, mew=1.5)


def plant_response():
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    q = np.linspace(0, 1800, 120)
    for t, c, dy in ((15, S1, 0), (25, S2, 7), (32, S3, -7)):
        an = [leaf_photosynthesis(x * 0.85, t, 1.0).an for x in q]
        a.plot(q, an, color=c, label=f"{t} C")
        label_end(a, q[-1], an[-1], f"{t} C", c, dy)
    a.axhspan(15, 20, color=S4, alpha=0.15, lw=0)
    a.text(40, 19.2, "strawberry literature, 15-20", color=INK2, fontsize=8.5)
    a.set_xlim(0, 2150)
    a.set_title("Leaf photosynthesis vs light (420 ppm, VPD 1 kPa)")
    a.set_xlabel("PPFD, umol m-2 s-1")
    a.set_ylabel("net photosynthesis, umol m-2 s-1")
    a.legend(loc="lower right")
    temps = np.linspace(5, 45, 81)
    an = [leaf_photosynthesis(1200 * 0.85, t, 1.0).an for t in temps]
    b.plot(temps, an, color=S1)
    i = int(np.argmax(an))
    b.annotate(f"optimum {temps[i]:.0f} C", (temps[i], an[i]), xytext=(0, 10), textcoords="offset points",
               ha="center", color=INK, fontsize=9)
    b.set_ylim(None, max(an) + 1.5)
    b.set_title("Leaf photosynthesis vs temperature (PPFD 1200)")
    b.set_xlabel("leaf temperature, C")
    b.set_ylabel("net photosynthesis, umol m-2 s-1")
    fig.savefig(os.path.join(OUT, "plant_response.png"), dpi=150)
    plt.close(fig)


def policy_day():
    task, policy = LightingTask(), load_policy()
    rng = np.random.default_rng(12345)
    days = [Weather.random_day(rng) for _ in range(60)]
    # a held-out day with some daylight, so the policy has something to respond to
    w = max(days, key=lambda d: (100 < d.sun_ppfd.max() < 450, d.sun_ppfd.max()))
    hours = np.arange(len(w.sun_ppfd)) * STEP_MIN / 60
    blue, red, dli, last = [], [], 0.0, (0.0, 0.0)
    for k, h in enumerate(hours):
        obs = task.observe(k, w, dli, last)
        b, r = task.safe_action(h, w.temp_c[k], *policy.act(obs))
        mix = led_light(b, r, task.led)
        dli += (w.sun_ppfd[k] + mix.total) * STEP_MIN * 60 / 1e6
        blue.append(b)
        red.append(r)
        last = (b, r)
    led = np.array([led_light(b, r, task.led).total for b, r in zip(blue, red)])
    fig, (a, b) = plt.subplots(2, 1, figsize=(10, 5.6), sharex=True, constrained_layout=True)
    a.fill_between(hours, 0, w.sun_ppfd, color=S4, alpha=0.55, lw=0, label="daylight")
    a.fill_between(hours, w.sun_ppfd, w.sun_ppfd + led, color=S1, alpha=0.45, lw=0, label="LED board")
    a.set_ylabel("PPFD, umol m-2 s-1")
    a.set_title(f"A held-out day: light at the canopy (daily light integral {dli:.1f} mol m-2)")
    a.legend(loc="upper left", ncols=2)
    b.step(hours, blue, where="post", color=LED_BLUE, label="blue LED")
    b.step(hours, red, where="post", color=LED_RED, label="red LED", linestyle=(0, (4, 2)))
    b.axvspan(0, 6, color=GRID, alpha=0.6, lw=0)
    b.axvspan(22, 24, color=GRID, alpha=0.6, lw=0)
    b.text(0.3, 50, "dark period", color=INK2, fontsize=8.5)
    b.set_ylim(-5, 110)
    b.set_ylabel("LED level, %")
    b.set_xlabel("hour of day")
    b.set_title("LED levels chosen by the PPO policy (after the safety rules)")
    b.legend(loc="center right")
    b.set_xticks(range(0, 25, 3))
    fig.savefig(os.path.join(OUT, "led_policy_day.png"), dpi=150)
    plt.close(fig)


def policy_comparison():
    res = json.load(open(os.path.join(HERE, "models", "led_policy_eval.json")))["results"]
    names = {"off": "LEDs off", "fixed_25_75": "fixed 25 / 75 %", "always_full": "always full",
             "greedy_model": "model-based optimiser", "ppo": "PPO (deployed)"}
    keys = [k for k in names if k in res]
    vals = [res[k]["reward"] * 100 for k in keys]   # cents per day
    fig, ax = plt.subplots(figsize=(8, 3.2), constrained_layout=True)
    colors = [S1 if k == "ppo" else "#9ec5f4" for k in keys]
    ax.barh([names[k] for k in keys], vals, color=colors, height=0.6, edgecolor=SURFACE, linewidth=2)
    for y, v in enumerate(vals):
        ax.text(v - 0.25, y, f"{v:.2f}", va="center", ha="right", color=INK, fontsize=9)
    ax.set_xlim(min(vals) * 1.18, 0.5)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.invert_yaxis()
    ax.set_xlabel("daily reward, cents per LED board (CO2 value - electricity - penalties; higher is better)")
    ax.set_title("LED policies on 60 held-out days")
    ax.grid(axis="y", visible=False)
    fig.savefig(os.path.join(OUT, "policy_comparison.png"), dpi=150)
    plt.close(fig)


def forecast_error():
    res = json.load(open(os.path.join(HERE, "models", "forecast_eval.json")))["results"]
    style = {"chronos": ("Chronos-Bolt Tiny", S1, "-"), "ttm": ("TinyTimeMixer r2", S3, "-"),
             "persistence": ("persistence (no change)", S2, (0, (4, 2))),
             "seasonal_naive_24h": ("same time yesterday", S4, (0, (1, 2)))}
    fig, ax = plt.subplots(figsize=(8, 3.8), constrained_layout=True)
    for k, (name, c, ls) in style.items():
        y = res[k]["vpd_mae_kpa"]
        x = np.arange(1, len(y) + 1)
        ax.plot(x, y, color=c, linestyle=ls, marker="o", ms=5, mec=SURFACE, label=name)
        ax.annotate(name, (x[-1], y[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                    color=INK, fontsize=9)
    ax.set_xlim(0.8, 8.8)
    ax.set_ylim(0, None)
    ax.set_xlabel("forecast lead time, hours")
    ax.set_ylabel("VPD mean absolute error, kPa")
    ax.set_title("VPD forecast error, 120 forecasts over a year of measured weather")
    ax.legend(loc="upper left")
    fig.savefig(os.path.join(OUT, "forecast_error.png"), dpi=150)
    plt.close(fig)


def forecast_example():
    from forecaster import ChronosForecaster, PersistenceForecaster
    d = json.load(open(os.path.join(HERE, "data", "openmeteo_kingston_2025.json")))["hourly"]
    s = np.array([d["temperature_2m"], d["relative_humidity_2m"]], dtype=np.float32)
    start = 24 * 200 + 8   # a summer morning, 08:00
    ctx, h = 512, 12
    past = s[:, start - ctx:start]
    chron = ChronosForecaster().predict(past, h)[0]
    pers = PersistenceForecaster().predict(past, h)[0]
    t_past = np.arange(-48, 0)
    t_f = np.arange(0, h)
    fig, ax = plt.subplots(figsize=(9, 3.6), constrained_layout=True)
    ax.plot(t_past, past[0, -48:], color=INK2, lw=1.5, label="measured (input)")
    ax.plot(t_f, s[0, start:start + h], color=INK, lw=2, label="measured (truth)")
    ax.plot(t_f, chron, color=S1, label="Chronos-Bolt Tiny")
    ax.plot(t_f, pers, color=S2, linestyle=(0, (4, 2)), label="persistence")
    ax.axvline(0, color=INK2, lw=0.8)
    ax.text(0.3, ax.get_ylim()[1], " forecast starts", va="top", color=INK2, fontsize=8.5)
    ax.set_xlabel("hours from forecast start")
    ax.set_ylabel("air temperature, C")
    ax.set_title("Example 12 h temperature forecast (Kingston, ON, measured hourly data)")
    ax.legend(loc="lower left", ncols=2)
    fig.savefig(os.path.join(OUT, "forecast_example.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    plant_response()
    policy_day()
    policy_comparison()
    forecast_error()
    try:
        forecast_example()
    except ImportError as e:
        print(f"forecast_example skipped: {e}")
    print("written to", os.path.abspath(OUT))

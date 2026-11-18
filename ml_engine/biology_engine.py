"""
Biology engine service: runs the strawberry canopy model (plant_model.py) on live data.

Every BIO_PERIOD_S (default 60 s), for each node that reported in the last 15 minutes:
  1. Light: daylight PPFD from the node (par_umol if the source measures PAR, else the
     TSL2591 lux minus the LEDs' own share) plus the LED board's PPFD at the levels the node
     is running.
  2. Plant: canopy photosynthesis, conductance and transpiration (Penman-Monteith), VPD.
  3. Daily light integral so far today (local time, LED_TZ).
  4. Climate forecast for the next hours (forecaster.py; FORECAST_BACKEND, default chronos,
     falls back to persistence without torch).
Writes one plant_state row per node. The API, dashboard, controller and Grafana read it.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

import gos_db
from forecaster import make_forecaster
from plant_model import LedParams, LightMix, PlantParams, ambient_ppfd_from_lux, canopy, led_light

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BIO-ENGINE] %(message)s")
logger = logging.getLogger("BiologyEngine")

FORECAST_EVERY_S = 900
FORECAST_HORIZON = 8          # buckets of 15 min = 2 h


def compute_state(reading: dict, led_pct: tuple, prev: tuple | None, now: datetime, tz,
                  plant: PlantParams = PlantParams(), led: LedParams = LedParams()) -> dict | None:
    """Plant state for one node. `prev` is (time, dli, ppfd_ambient, ppfd_led) of the last row."""
    t, rh = reading["temp_c"], reading["humidity_pct"]
    if t is None or rh is None:
        return None
    if reading.get("par_umol") is not None:
        sun = max(float(reading["par_umol"]), 0.0)
    else:
        sun = ambient_ppfd_from_lux(reading.get("light_lux") or 0.0, *led_pct, led=led)
    mix = led_light(*led_pct, led=led)
    light = LightMix(sun, mix.blue, mix.red)
    c = canopy(light, float(t), float(rh), p=plant)

    dli = 0.0
    if prev is not None:
        prev_time, prev_dli, prev_sun, prev_led = prev
        same_day = prev_time.astimezone(tz).date() == now.astimezone(tz).date() if tz else True
        dt = min((now - prev_time).total_seconds(), 900.0)  # do not integrate across long gaps
        if same_day and dt > 0:
            # trapezoid between the previous and this PPFD
            dli = float(prev_dli or 0.0) + 0.5 * ((prev_sun or 0) + (prev_led or 0) + light.total) * dt / 1e6
    return {"ppfd_ambient": round(sun, 2), "ppfd_led": round(mix.total, 2),
            "blue_fraction": round(light.blue_fraction, 4), "vpd_kpa": round(c.vpd, 4),
            "an_umol": round(c.an, 3), "gc_mol": round(c.gc, 4),
            "transpiration_g_m2_h": round(c.transpiration_g_m2_h, 2), "dli_mol": round(dli, 4)}


def forecast_for(conn, forecaster, node_id: str) -> dict | None:
    times, temp, rh = gos_db.climate_history(conn, node_id)
    if len(temp) < max(getattr(forecaster, "min_context", 1), 8):
        return None
    ctx = getattr(forecaster, "min_context", 1)
    series = np.array([temp, rh], dtype=np.float32)
    if forecaster.name == "ttm" and series.shape[1] < ctx:
        return None
    pred = forecaster.predict(series, FORECAST_HORIZON)
    from plant_model import vpd_kpa
    start = times[-1]
    return {"backend": forecaster.name, "step_min": 15,
            "times": [(start + timedelta(minutes=15 * (h + 1))).isoformat() for h in range(FORECAST_HORIZON)],
            "temp_c": [round(float(x), 2) for x in pred[0]],
            "humidity_pct": [round(float(x), 1) for x in pred[1]],
            "vpd_kpa": [round(vpd_kpa(float(a), float(b)), 3) for a, b in zip(pred[0], pred[1])]}


def main():
    period = float(os.getenv("BIO_PERIOD_S", "60"))
    tz = ZoneInfo(os.getenv("LED_TZ", "UTC")) if ZoneInfo else None
    forecaster = make_forecaster(os.getenv("FORECAST_BACKEND", "chronos"))
    logger.info(f"Biology engine started: period {period:g} s, forecast backend {forecaster.name}")
    conn, last_forecast, forecasts = None, {}, {}
    while True:
        try:
            if conn is None or conn.closed:
                conn = gos_db.connect()
            now = datetime.now(timezone.utc)
            for r in gos_db.active_nodes(conn):
                node = r["node_id"]
                state = compute_state(r, gos_db.led_state(conn, node), gos_db.last_plant_state(conn, node), now, tz)
                if state is None:
                    continue
                if time.time() - last_forecast.get(node, 0) > FORECAST_EVERY_S:
                    try:
                        forecasts[node] = forecast_for(conn, forecaster, node)
                    except Exception as e:
                        logger.warning(f"{node}: forecast failed: {e}")
                        forecasts[node] = None
                    last_forecast[node] = time.time()
                    if forecasts[node] is None:
                        logger.info(f"{node}: not enough history for a forecast yet")
                # every row carries the newest forecast (made at most FORECAST_EVERY_S ago)
                state["forecast"] = forecasts.get(node)
                gos_db.insert_plant_state(conn, node, state)
                logger.info(f"{node}: PPFD {state['ppfd_ambient']:.0f}+{state['ppfd_led']:.0f}, "
                            f"A {state['an_umol']:.1f} umol/m2/s, E {state['transpiration_g_m2_h']:.0f} g/m2/h, "
                            f"VPD {state['vpd_kpa']:.2f} kPa, DLI {state['dli_mol']:.2f}")
        except Exception as e:
            logger.error(f"cycle failed: {e}")
            try:
                conn.close()
            except Exception:
                pass
            conn = None
        time.sleep(period)


if __name__ == "__main__":
    main()

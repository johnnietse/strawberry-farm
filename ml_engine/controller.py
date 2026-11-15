"""
LED controller service (the "ml_engine" container).

Every CONTROL_PERIOD_S (default 300 s), for each active node without a manual override:
  1. builds the same observation the policy was trained on (greenhouse_env.LightingTask):
     time of day, daylight PPFD, temperature, humidity, VPD, light integral so far, current
     LED levels, photoperiod flag;
  2. picks blue and red LED levels with the trained PPO policy (models/led_policy.npz,
     numpy inference) or, if CONTROL_POLICY=greedy or no policy file exists, the model-based
     one-step optimiser;
  3. writes a setpoint to led_setpoints, valid CONTROL_VALID_MIN (default 15) minutes.
coap_receiver then sends it to the node after the safety monitor. If this service stops,
setpoints expire and the safety fallback takes over; the node itself falls back after
CONFIG_GOS_LED_HOLD_S without commands.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

import gos_db
from greenhouse_env import LightingTask, TaskConfig, Weather
from plant_model import vpd_kpa
from policy import load_policy

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LED-CONTROL] %(message)s")
logger = logging.getLogger("LedController")


def task_config_from_env() -> TaskConfig:
    return TaskConfig(dark_start_h=float(os.getenv("LED_DARK_START", 22)),
                      dark_end_h=float(os.getenv("LED_DARK_END", 6)),
                      t_cutoff_c=float(os.getenv("LED_T_CUTOFF_C", 32)))


def decide(task: LightingTask, policy, hour: float, sun: float, temp: float, rh: float,
           dli: float, last: tuple) -> tuple[float, float, str]:
    """(blue_pct, red_pct, reason) for one node."""
    if policy is not None:
        w = Weather(np.array([sun]), np.array([temp]), np.array([rh]))
        step = int(hour * 60 // 10)
        obs = task.observe(0, w, dli, last)
        # observe() takes the time from the step index; set the clock features directly
        obs[0], obs[1] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
        from greenhouse_env import in_dark_period
        obs[9] = 0.0 if in_dark_period(hour, task.cfg) else 1.0
        b, r = policy.act(obs)
        b, r = task.safe_action(hour, temp, b, r)
        return b, r, f"ppo (step {step}, DLI {dli:.1f}, daylight {sun:.0f})"
    b, r = task.greedy_action(hour, sun, temp, rh, dli)
    return b, r, f"greedy model (DLI {dli:.1f}, daylight {sun:.0f})"


def main():
    period = float(os.getenv("CONTROL_PERIOD_S", "300"))
    valid = int(os.getenv("CONTROL_VALID_MIN", "15"))
    tz = ZoneInfo(os.getenv("LED_TZ", "UTC")) if ZoneInfo else None
    task = LightingTask(task_config_from_env())
    policy = None if os.getenv("CONTROL_POLICY", "ppo") == "greedy" else load_policy()
    logger.info(f"LED controller started: {'PPO policy' if policy else 'greedy model'}, every {period:g} s")
    conn = None
    while True:
        try:
            if conn is None or conn.closed:
                conn = gos_db.connect()
            now = datetime.now(timezone.utc)
            local = now.astimezone(tz) if tz else now
            hour = local.hour + local.minute / 60.0
            for r in gos_db.active_nodes(conn):
                node = r["node_id"]
                if r["temp_c"] is None or r["humidity_pct"] is None:
                    continue
                if gos_db.manual_override(conn, node):
                    logger.info(f"{node}: manual setting active, not changed")
                    continue
                ps = gos_db.last_plant_state(conn, node)
                dli = float(ps[1] or 0.0) if ps else 0.0
                sun = float(ps[2] or 0.0) if ps else float(r["par_umol"] or 0.0)
                last = gos_db.led_state(conn, node)
                b, rd, reason = decide(task, policy, hour, sun, float(r["temp_c"]), float(r["humidity_pct"]), dli, last)
                gos_db.insert_setpoint(conn, node, b, rd, "controller", reason, valid)
                logger.info(f"{node}: blue {b:.0f} %, red {rd:.0f} % ({reason}; "
                            f"VPD {vpd_kpa(float(r['temp_c']), float(r['humidity_pct'])):.2f} kPa)")
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

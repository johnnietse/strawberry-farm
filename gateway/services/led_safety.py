"""
LED safety monitor: the last check before an LED level leaves the gateway for a sensor node.

Every LED command, whether it comes from the ML controller, a manual setting in the dashboard
or a schedule, passes through `LedSafetyMonitor.check` inside coap_receiver, just before it is
signed and sent. The controller cannot bypass it because the receiver is the only component
that holds the node keys.

Rules (each one is a safety property that must hold at every step, written in LTL as G(...)):
  G(level in 0..100)                         each channel clamped to 0..100 %
  G(dark_period -> off)                      photoperiod: off from dark_start to dark_end (local time).
                                             Light in the night breaks the dark period that
                                             short-day strawberries need to flower.
  G(temp > t_cutoff -> off)                  over-temperature cut-off (the LEDs add heat)
  G(temp unknown -> level <= cap_unknown)    no temperature reading: limit the light
  G(stale setpoint -> fallback)              no fresh setpoint (controller down): fallback levels
  G(|level - last level| <= max_step)        ramp limit per command, no sudden spectral jumps

Configuration (environment variables, read by `LedSafetyConfig.from_env`):
  LED_DARK_START, LED_DARK_END       hours, default 22 and 6
  LED_T_CUTOFF_C                     default 32
  LED_CAP_UNKNOWN_PCT                default 50
  LED_MAX_STEP_PCT                   default 25 (per command, one command per node per minute)
  LED_FALLBACK_BLUE, LED_FALLBACK_RED  default 0 and 0
  LED_TZ                             IANA time zone of the phytotron, default UTC
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


@dataclass(frozen=True)
class LedSafetyConfig:
    dark_start_h: float = 22.0
    dark_end_h: float = 6.0
    t_cutoff_c: float = 32.0
    cap_unknown_pct: float = 50.0
    max_step_pct: float = 25.0
    fallback: tuple = (0.0, 0.0)
    tz: str = "UTC"

    @classmethod
    def from_env(cls) -> "LedSafetyConfig":
        e = os.getenv
        return cls(float(e("LED_DARK_START", 22)), float(e("LED_DARK_END", 6)), float(e("LED_T_CUTOFF_C", 32)),
                   float(e("LED_CAP_UNKNOWN_PCT", 50)), float(e("LED_MAX_STEP_PCT", 25)),
                   (float(e("LED_FALLBACK_BLUE", 0)), float(e("LED_FALLBACK_RED", 0))), e("LED_TZ", "UTC"))


@dataclass
class SafetyDecision:
    blue: int
    red: int
    requested: Optional[tuple]
    notes: list = field(default_factory=list)


def in_dark_period(hour: float, start: float, end: float) -> bool:
    if start == end:
        return False
    return (start <= hour or hour < end) if start > end else (start <= hour < end)


class LedSafetyMonitor:
    def __init__(self, cfg: LedSafetyConfig = LedSafetyConfig()):
        self.cfg = cfg
        self.last: dict[str, tuple[float, float]] = {}
        self._tz = ZoneInfo(cfg.tz) if ZoneInfo and cfg.tz else None

    def local_hour(self, now: datetime) -> float:
        if self._tz is not None and now.tzinfo is not None:
            now = now.astimezone(self._tz)
        return now.hour + now.minute / 60.0

    def check(self, node_id: str, requested: Optional[tuple], temp_c: Optional[float],
              now: datetime) -> SafetyDecision:
        """`requested` is (blue_pct, red_pct) from a fresh setpoint, or None if there is none."""
        cfg = self.cfg
        notes = []
        if requested is None:
            b, r = cfg.fallback
            notes.append("no fresh setpoint: fallback")
        else:
            b, r = requested
        b, r = min(max(float(b), 0.0), 100.0), min(max(float(r), 0.0), 100.0)
        if requested is not None and (b, r) != (float(requested[0]), float(requested[1])):
            notes.append("clamped to 0..100")

        if in_dark_period(self.local_hour(now), cfg.dark_start_h, cfg.dark_end_h):
            if b or r:
                notes.append("dark period: off")
            b = r = 0.0
        elif temp_c is None:
            cap = cfg.cap_unknown_pct
            if b > cap or r > cap:
                notes.append(f"no temperature reading: capped at {cap:g} %")
            b, r = min(b, cap), min(r, cap)
        elif temp_c > cfg.t_cutoff_c:
            if b or r:
                notes.append(f"{temp_c:.1f} C above {cfg.t_cutoff_c:g} C: off")
            b = r = 0.0

        # ramp limit; switching off is always allowed immediately
        lb, lr = self.last.get(node_id, (0.0, 0.0))
        step = cfg.max_step_pct
        nb = b if b < lb else min(b, lb + step)
        nr = r if r < lr else min(r, lr + step)
        if (nb, nr) != (b, r):
            notes.append(f"ramp limited to +{step:g} % per command")
        b, r = nb, nr

        self.last[node_id] = (b, r)
        return SafetyDecision(int(round(b)), int(round(r)), requested, notes)

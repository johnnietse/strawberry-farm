"""
LED policy inference in plain numpy (no torch), so it runs on a Raspberry Pi in a few
microseconds per decision. The weights come from `train_rl.py` (PPO, stable-baselines3).
"""
from __future__ import annotations

import json
import os

import numpy as np

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "models", "led_policy.npz")


class NumpyPolicy:
    def __init__(self, path: str = DEFAULT_PATH):
        data = np.load(path)
        self.layers = []
        i = 0
        while f"w{i}" in data:
            self.layers.append((data[f"w{i}"], data[f"b{i}"]))
            i += 1
        self.meta = json.loads(str(data["meta"])) if "meta" in data else {}

    def act(self, obs: np.ndarray) -> tuple[float, float]:
        """Deterministic action: (blue_pct, red_pct) in 0..100."""
        x = np.asarray(obs, dtype=np.float32)
        for k, (w, b) in enumerate(self.layers):
            x = x @ w + b
            if k < len(self.layers) - 1:
                x = np.tanh(x)
        a = (np.clip(x, -1.0, 1.0) + 1.0) * 50.0
        return float(a[0]), float(a[1])


def load_policy(path: str = DEFAULT_PATH):
    return NumpyPolicy(path) if os.path.exists(path) else None

"""
Train the LED policy with PPO in the greenhouse lighting environment, compare it with simple
baselines on held-out days, and export it for the numpy controller.

    pip install -r requirements-train.txt
    python train_rl.py --steps 300000

Writes models/led_policy.npz (weights for policy.py) and models/led_policy_eval.json.
Training needs torch; the controller that uses the result does not.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from greenhouse_env import STEP_MIN, GreenhouseLightingEnv, LightingTask, Weather
from policy import NumpyPolicy

HERE = os.path.dirname(os.path.abspath(__file__))


def export(model, path: str, meta: dict) -> None:
    pol = model.policy
    linears = [m for m in pol.mlp_extractor.policy_net if hasattr(m, "weight")] + [pol.action_net]
    arrays = {}
    for i, lin in enumerate(linears):
        arrays[f"w{i}"] = lin.weight.detach().cpu().numpy().T.astype(np.float32)
        arrays[f"b{i}"] = lin.bias.detach().cpu().numpy().astype(np.float32)
    np.savez(path, meta=json.dumps(meta), **arrays)


def evaluate(task: LightingTask, days, policies: dict) -> dict:
    out = {}
    for name, pol in policies.items():
        runs = [task.run_day(d, pol) for d in days]
        out[name] = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=300_000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--eval-days", type=int, default=60)
    args = ap.parse_args()

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env

    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    env = make_vec_env(lambda: GreenhouseLightingEnv(), n_envs=8, seed=args.seed)
    model = PPO("MlpPolicy", env, seed=args.seed, n_steps=576, batch_size=576, gamma=0.995,
                gae_lambda=0.95, learning_rate=3e-4, ent_coef=0.0,
                policy_kwargs={"net_arch": [64, 64]}, verbose=0)
    t0 = time.time()
    model.learn(total_timesteps=args.steps)
    train_s = time.time() - t0

    path = os.path.join(HERE, "models", "led_policy.npz")
    export(model, path, {"algo": "PPO", "steps": args.steps, "seed": args.seed, "step_min": STEP_MIN})
    np_policy = NumpyPolicy(path)

    # the numpy export must reproduce the torch policy
    obs = np.random.default_rng(0).uniform(-1, 1, (32, 10)).astype(np.float32)
    torch_a = (np.clip(model.predict(obs, deterministic=True)[0], -1, 1) + 1) * 50
    np_a = np.array([np_policy.act(o) for o in obs])
    max_err = float(np.abs(torch_a - np_a).max())

    task = LightingTask()
    rng = np.random.default_rng(12345)   # held-out days, not seen in training
    days = [Weather.random_day(rng) for _ in range(args.eval_days)]
    hour = lambda k: k * STEP_MIN / 60.0
    results = evaluate(task, days, {
        "off": lambda o, k, w: (0.0, 0.0),
        "always_full": lambda o, k, w: (100.0, 100.0),
        "fixed_25_75": lambda o, k, w: (25.0, 75.0),
        "greedy_model": lambda o, k, w: task.greedy_action(hour(k), w.sun_ppfd[k], w.temp_c[k], w.rh_pct[k],
                                                           o[6] * task.cfg.dli_min),
        "ppo": lambda o, k, w: np_policy.act(o),
    })
    report = {"train_seconds": train_s, "numpy_vs_torch_max_abs_pct": max_err,
              "eval_days": args.eval_days, "results": results}
    with open(os.path.join(HERE, "models", "led_policy_eval.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

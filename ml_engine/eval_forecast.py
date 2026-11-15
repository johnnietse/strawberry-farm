"""
Compare the climate forecasters on a measured temperature / humidity series.

    python eval_forecast.py --data openmeteo.json [--horizon 6] [--origins 120]

`--data` is an Open-Meteo archive response with hourly temperature_2m and
relative_humidity_2m (https://archive-api.open-meteo.com/v1/archive). Forecasts start at
`--origins` evenly spaced times after the first 512 hours, each using only the data before
it. Reports the mean absolute error of temperature, humidity and VPD for each backend and
lead time, and writes models/forecast_eval.json. Rerun on node data once the nodes have
logged a few weeks.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from forecaster import PersistenceForecaster, make_forecaster
from plant_model import vpd_kpa

HERE = os.path.dirname(os.path.abspath(__file__))


class SeasonalNaive:
    name = "seasonal_naive_24h"
    min_context = 24

    def predict(self, series, horizon):
        s = np.asarray(series)
        return np.stack([s[:, -24 + (h % 24)] for h in range(horizon)], axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--horizon", type=int, default=6)
    ap.add_argument("--origins", type=int, default=120)
    ap.add_argument("--backends", default="persistence,seasonal,chronos,ttm")
    args = ap.parse_args()

    d = json.load(open(args.data))["hourly"]
    series = np.array([d["temperature_2m"], d["relative_humidity_2m"]], dtype=np.float32)
    ok = ~np.isnan(series).any(axis=0)
    series = series[:, ok]
    ctx = 512
    starts = np.linspace(ctx, series.shape[1] - args.horizon - 1, args.origins).astype(int)

    models = []
    for b in args.backends.split(","):
        if b == "persistence":
            models.append(PersistenceForecaster())
        elif b == "seasonal":
            models.append(SeasonalNaive())
        else:
            m = make_forecaster(b)
            if m.name == b:
                models.append(m)

    results = {}
    for m in models:
        t0 = time.time()
        err = np.zeros((3, args.horizon))
        for s in starts:
            pred = m.predict(series[:, s - ctx:s], args.horizon)
            truth = series[:, s:s + args.horizon]
            err[0] += np.abs(pred[0] - truth[0])
            err[1] += np.abs(pred[1] - truth[1])
            vp = np.array([vpd_kpa(pred[0, h], pred[1, h]) for h in range(args.horizon)])
            vt = np.array([vpd_kpa(truth[0, h], truth[1, h]) for h in range(args.horizon)])
            err[2] += np.abs(vp - vt)
        err /= len(starts)
        results[m.name] = {
            "temp_mae_c": [round(float(x), 3) for x in err[0]],
            "rh_mae_pct": [round(float(x), 2) for x in err[1]],
            "vpd_mae_kpa": [round(float(x), 4) for x in err[2]],
            "seconds_per_forecast": round((time.time() - t0) / len(starts), 4),
        }
        print(m.name, results[m.name])
    out = {"data": os.path.basename(args.data), "origins": len(starts), "context_h": ctx,
           "horizon_h": args.horizon, "results": results}
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    with open(os.path.join(HERE, "models", "forecast_eval.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()

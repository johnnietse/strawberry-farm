"""
Short-term climate forecast (temperature, humidity) per sensor node.

Three interchangeable backends, all zero-shot (nothing to train on site):
  - "persistence": the last value repeats. The baseline any forecaster must beat.
  - "chronos":     Amazon Chronos-Bolt Tiny (amazon/chronos-bolt-tiny on Hugging Face, 8.7 M
                   parameters, Apache-2.0), a pretrained time-series foundation model.
  - "ttm":         IBM Granite TinyTimeMixer r2 (ibm-granite/granite-timeseries-ttm-r2,
                   0.8 M parameters, Apache-2.0), small enough for a Raspberry Pi CPU.
`eval_forecast.py` compares them on measured data; pick the backend with FORECAST_BACKEND.
The foundation-model backends need torch (requirements-forecast.txt); without it the service
falls back to persistence.
"""
from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger("Forecaster")


class PersistenceForecaster:
    name = "persistence"
    min_context = 1

    def predict(self, series: np.ndarray, horizon: int) -> np.ndarray:
        """series: (n_channels, T). Returns (n_channels, horizon)."""
        series = np.asarray(series, dtype=np.float32)
        return np.repeat(series[:, -1:], horizon, axis=1)


class ChronosForecaster:
    name = "chronos"
    min_context = 32

    def __init__(self, model_id: str = "amazon/chronos-bolt-tiny"):
        import torch
        from chronos import BaseChronosPipeline

        self.torch = torch
        self.pipe = BaseChronosPipeline.from_pretrained(model_id, device_map="cpu", torch_dtype=torch.float32)

    def predict(self, series: np.ndarray, horizon: int) -> np.ndarray:
        x = self.torch.tensor(np.asarray(series, dtype=np.float32))
        _, mean = self.pipe.predict_quantiles(x, prediction_length=horizon, quantile_levels=[0.5])
        return mean.numpy()


class TTMForecaster:
    """TTM-r2 with per-series standardisation (the model expects scaled inputs)."""
    name = "ttm"

    def __init__(self, context: int = 512, horizon: int = 96,
                 model_id: str = "ibm-granite/granite-timeseries-ttm-r2"):
        import torch
        from tsfm_public.toolkit.get_model import get_model

        self.torch = torch
        self.context, self.max_horizon = context, horizon
        self.min_context = context
        self.model = get_model(model_id, context_length=context, prediction_length=horizon)
        self.model.eval()

    def predict(self, series: np.ndarray, horizon: int) -> np.ndarray:
        x = np.asarray(series, dtype=np.float32)[:, -self.context:]
        if x.shape[1] < self.context:   # pad the front with the first value
            x = np.concatenate([np.repeat(x[:, :1], self.context - x.shape[1], axis=1), x], axis=1)
        mu = x.mean(axis=1, keepdims=True)
        sd = x.std(axis=1, keepdims=True) + 1e-6
        z = ((x - mu) / sd).T[None]              # (1, T, channels)
        with self.torch.no_grad():
            out = self.model(past_values=self.torch.tensor(z)).prediction_outputs[0].numpy()  # (H, C)
        return (out[:horizon].T * sd + mu)


def make_forecaster(backend: str = "persistence"):
    try:
        if backend == "chronos":
            return ChronosForecaster()
        if backend == "ttm":
            return TTMForecaster()
    except Exception as e:  # torch or the model not available: say so and keep running
        logger.warning(f"forecast backend {backend} unavailable ({e}); using persistence")
    return PersistenceForecaster()

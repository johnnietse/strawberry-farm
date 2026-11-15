# ml_engine: plant model, LED controller, climate forecast

Everything here runs on the Raspberry Pi (or any Linux host) next to the database. Nothing runs
on the sensor node: the nRF52840 measures, sends and applies LED levels; the decisions are made
here and sent back to it, signed, in the reply to its next packet.

```
node packet ──► coap_receiver ──► raw_telemetry
                                      │
               biology_engine.py ◄────┘   plant model + 2 h climate forecast ──► plant_state
                                      │
               controller.py   ◄──────┘   PPO policy ──► led_setpoints
                                      │
dashboard / API (manual) ─────────────┘            ──► led_setpoints (source 'manual')
                                      │
coap_receiver: newest setpoint ──► led_safety ──► signed LED command in the reply ──► node PWM
```

| File | What it is |
|---|---|
| `plant_model.py` | The **biology engine's** model: strawberry canopy photosynthesis (Farquhar-von Caemmerer-Berry), stomatal conductance (Medlyn), transpiration (Penman-Monteith), spectrum effects. Mechanistic, not trained. |
| `biology_engine.py` | Service: runs the model on every active node each minute, adds the daily light integral and a climate forecast, writes `plant_state`. |
| `greenhouse_env.py` | The lighting task the controller learns in: one day, a decision every 10 min, reward in dollars (CO2 fixed minus electricity, penalties for too little blue and a low daily light integral), same limits as the gateway's safety monitor. |
| `train_rl.py` | Trains the LED policy with PPO (stable-baselines3) and compares it with baselines on 60 held-out days. Run on a PC. |
| `policy.py` | The trained policy in plain numpy (`models/led_policy.npz`), so the Pi needs no torch for control. |
| `controller.py` | Service: every 5 min, one LED setpoint per node (PPO, or the model-based optimiser with `CONTROL_POLICY=greedy`). Skips nodes under a manual setting. |
| `forecaster.py`, `eval_forecast.py` | Climate forecast backends (persistence, Chronos-Bolt Tiny, TinyTimeMixer) and their comparison on measured data. |
| `gos_db.py` | Database queries shared by the two services. |

## Which model for which job

Three different kinds of "model", each picked for what it has to do:

| Job | Model | Why this one |
|---|---|---|
| What is the plant doing? (biology engine) | Mechanistic: FvCB + Medlyn + Penman-Monteith | There is no data from these plants yet, and a physical model is right from the first day, explainable, and is what crop scientists use. No Hugging Face model does this: a search for strawberry models found only image datasets (disease, picking robots) and unrelated language models. |
| How should the LEDs be set? | PPO reinforcement learning, trained in the plant model, exported to numpy | Learns the trade-off between light, electricity and plant needs over a whole day; runs in microseconds on the Pi. Checked against a model-based optimiser. |
| What will the climate do next? | Amazon Chronos-Bolt Tiny (Hugging Face `amazon/chronos-bolt-tiny`, 8.7 M parameters, Apache-2.0) | Pretrained time-series foundation model: works zero-shot, with no training on site. Best of the three on measured data (below). IBM TinyTimeMixer r2 (`ibm-granite/granite-timeseries-ttm-r2`, 0.8 M) is the smaller option. |
| Turn a researcher's note into an event | Qwen2.5-1.5B-Instruct via Ollama (offline), or Claude if a key is set, else keyword rules | See `gateway/services/assistant.py`. Qwen2.5-0.5B was tested first and put 5 of 6 test notes in the wrong category; 1.5B got all 6 right in about 5 s each on a PC CPU. |

On the node itself (nRF52840: 1 MB flash, 256 KB RAM) only a tiny model would fit (TensorFlow
Lite Micro), and there is nothing for it to decide that the gateway cannot decide better with
all nodes' data; the node stays a sensor and actuator.

## Results

**Plant model** (`tests/test_plant_and_control.py`): light-saturated leaf photosynthesis
15.9 umol m-2 s-1 at 25 C and 420 ppm (strawberry literature: about 15 to 20), optimum near
25 to 30 C, rising with CO2, consistent with Fick's law; red photons used better than blue
(McCree). Parameters are generic C3 values: no strawberry-cultivar gas-exchange fit was found,
so calibrate `vcmax25`, `jmax25` and `g1` with an A-Ci curve when a LI-COR is available.

**LED policy** (`models/led_policy_eval.json`, 60 held-out days, 600 k training steps, 4 min on a PC):

| Policy | Reward ($/day per board) | DLI (mol/m2/day) | kWh/day | Extra CO2 fixed (g/day) |
|---|---|---|---|---|
| LEDs off | -0.147 | 5.9 | 0 | 0 |
| Fixed 25 % blue / 75 % red | -0.086 | 9.4 | 0.051 | 1.26 |
| Always full | -0.0385 | 12.8 | 0.109 | 2.29 |
| Model-based optimiser (greedy) | -0.0383 | 12.5 | 0.102 | 2.21 |
| **PPO (deployed)** | **-0.0385** | **12.8** | **0.108** | **2.28** |

PPO matches the model-based optimiser to within 0.5 %. The numpy export reproduces the torch
policy to 0.00002 %. The honest finding: one LED board adds at most about 120 umol m-2 s-1 over
0.25 m2, so on most days the best policy is "full on during the photoperiod", and the learned
policy finds exactly that. The controller earns its keep when the light budget is tighter (more
daylight, a higher electricity price, a bigger board) - change `TaskConfig` and retrain.

**Climate forecast** (`models/forecast_eval.json`): 120 forecasts over 2025 hourly temperature
and humidity for Kingston, ON (Open-Meteo archive), 512 h of context each, mean absolute error:

| Backend | Temp 1 h | Temp 6 h | RH 6 h | VPD 1 h | VPD 6 h | Time per forecast (PC CPU) |
|---|---|---|---|---|---|---|
| Persistence | 0.59 C | 2.72 C | 11.3 % | 0.063 kPa | 0.245 kPa | 0 |
| Seasonal naive (24 h) | 3.69 C | 4.05 C | 12.2 % | 0.178 kPa | 0.171 kPa | 0 |
| TinyTimeMixer r2 | 0.83 C | 2.24 C | 8.1 % | 0.063 kPa | 0.135 kPa | 7 ms |
| **Chronos-Bolt Tiny** | **0.54 C** | **1.70 C** | **7.1 %** | **0.044 kPa** | **0.118 kPa** | 19 ms |

Outdoor weather, not phytotron air: rerun `eval_forecast.py` on node data after a few weeks.

## Run

```bash
pip install -r requirements.txt -r requirements-forecast.txt
python -m pytest tests                    # plant model, task, policy, controller
python biology_engine.py                  # needs DATABASE_URL
python controller.py
pip install -r requirements-train.txt     # PC only
python train_rl.py --steps 600000         # rewrites models/led_policy.npz
python eval_forecast.py --data openmeteo.json
```

In Docker both services start with the stack (`biology_engine`, `ml_engine`). Build the image
with `--build-arg FORECAST=0` to leave out torch (the forecast then uses persistence).

## Not verified

- No real plant has been measured: model parameters are literature values.
- LED photon flux at the canopy (`LedParams`, 60 umol m-2 s-1 per channel at 100 %) is a design
  estimate; measure it with a quantum sensor at plant height.
- The TSL2591 lux-to-PPFD conversion assumes daylight; it is approximate under the LEDs.
- The blue-light stomatal effect (`blue_g1_gain`) is an assumption.

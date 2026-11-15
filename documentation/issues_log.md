# Issues log

Every problem found while finishing G.O.S. rev 3.1, what it would have caused, and what was
done. Newest round first. Status: **fixed**, **open (needs hardware)**, or **outside the
project** (the development PC, not the system). Last updated 2026-11-15.

Evidence for "fixed": gateway 79 tests, ml_engine 13 tests, firmware host test, both firmware
builds, and `tests/e2e/run_e2e.sh` (14 checks, with torch, the Chronos model and the local Qwen
model) all pass.

## Round 4: access, models, end-to-end with every model

| # | Issue | Effect | Status |
|---|---|---|---|
| 1 | The forecast was made every 15 min but saved only on that one plant-state row; the next 14 rows (one a minute) had none | the API and dashboard showed no forecast most of the time | **fixed**: every row carries the newest forecast; e2e checks it |
| 2 | The dashboard's nginx resolved the API's address once at start | after the API container restarted, every dashboard request failed (502) until nginx restarted | **fixed**: Docker DNS re-resolved every 10 s; verified by restarting the API |
| 3 | The dashboard called the API on port 5000 directly, and CORS allowed only `localhost:8080` | the dashboard broke when opened at the Pi's network address, so on any other network | **fixed**: nginx serves page and `/api` on one address; no CORS needed |
| 4 | Database (5432) and MQTT (1883, 9001, anonymous) were published on every network interface | anyone on the same Wi-Fi could try the database password or write fake sensor rows through MQTT | **fixed**: both bound to the Pi only by default (`DB_BIND`, `MQTT_BIND`) |
| 5 | The hardware receiver took `DATABASE_URL` from `.env`, whose host is `db` (container network), but it runs on the host network | with a `.env`, the real receiver could not reach the database | **fixed**: it builds its own `localhost` address |
| 6 | The assistant's rate limit used the caller address, which behind nginx is always nginx | all users would have shared one limit | **fixed**: uses the forwarded client address |
| 7 | Manual LED settings capped at 24 h; assistant capped at 2000 characters and 10 per minute | too tight for long experiments | **changed**: "keep until switched back" (no expiry) or up to 90 days; assistant 8000 characters, 30 per minute, both settings |
| 8 | Dashboard could not use another G.O.S. server | one dashboard per Pi | **added**: server choice in the page, stored in the browser, never from the link; token per server |
| 9 | Models were downloaded at run time from Hugging Face / Ollama | the Pi needed internet; results could change with upstream updates | **fixed**: Chronos and TTM weights in `ml_engine/models/hf/` (pinned revisions, loaded offline, same results); Qwen in a GitHub release with a checksum; `fetch_models.sh` |
| 10 | The CrowdStrike Falcon Foundry plugin's hooks timed out ("didn't answer in time") | none on the project: those hooks only guide Foundry app development; no build, test or result depended on them, so nothing needed rerunning | **outside the project, fixed**: plugin turned off for this project only (`.claude/settings.local.json` in the workspace) |

## Round 3: security review of the API

| # | Issue | Effect | Status |
|---|---|---|---|
| 11 | No authentication on LED and event changes, CORS open to every site | any web page a researcher visited, or anyone on the network, could change the lights | **fixed**: token in the `Authorization` header for every change; CORS off by default |
| 12 | Assistant open to anyone, no size limit | could run up a paid model bill | **fixed**: token, length cap, rate limit |
| 13 | Dashboard took the API address from `?api=` in the link | a crafted link could send the dashboard, and the token, to another server | **fixed**: removed; the server is chosen inside the page only |

## Round 2: software review

| # | Issue | Effect | Status |
|---|---|---|---|
| 14 | LED control loop open: the node never received anything back | LEDs could only change by reflashing the node | **fixed**: signed LED command in the reply to each packet |
| 15 | "RL agent" was two if-statements on random numbers | no learning, no real data | **fixed**: PPO trained in the plant model, within 0.5 % of the optimiser |
| 16 | "FvCB" photosynthesis ignored light and temperature | plant numbers meaningless | **fixed**: full canopy model, tested against literature ranges |
| 17 | Safety monitor was a demo nothing called | no limits on LED commands | **fixed**: inside the receiver, every command passes it |
| 18 | Services defaulted to a different database password from the database | stack only worked with a `.env` | **fixed** |
| 19 | Dashboard showed random numbers; assistant was keyword matching in the browser | nothing real on screen | **fixed**: live data, server-side assistant |
| 20 | Logging an event without a description returned 500 | lost GUI requests | **fixed** |

## Round 1: hardware review

| # | Issue | Effect | Status |
|---|---|---|---|
| 21 | LED inductor 47 uH: AL8860 switched up to 1.27 MHz (limit 1 MHz) | current error, heating | **fixed**: 100 uH, 435 to 672 kHz (LTspice) |
| 22 | CTRL pull-down 2.2 k left 24 mV margin | LEDs could glow with the cable unplugged | **fixed**: 1.5 k, 0.12 V worst case |
| 23 | Switching loops long, through vias | noise near the radio and sensors | **fixed**: routed by hand, measured |
| 24 | Raspberry Pi guide's network settings did not match the firmware | nodes would never join | **fixed** |

## Development PC (not the project)

| # | Issue | Effect | What to do |
|---|---|---|---|
| 25 | `python3` is the Microsoft Store stub, so plugin hooks written in Python fail ("Python was not found", about 1,900 times this session) | none on the project | Windows Settings > Apps > Advanced app settings > App execution aliases: turn off `python.exe` and `python3.exe`. A change to Windows settings is yours to make. Real Python: `py -3`. |
| 26 | 74 plugins enabled; several have slow start-up and prompt hooks | the "didn't answer in time" notices | turn off plugins you do not use (`/plugin` in Claude Code) |
| 27 | Drive C: has 3 to 4 GB free | Docker builds can fail | free space before large builds; the e2e test removes its images |
| 28 | HawkScan (DAST) not run: no `HAWK_API_KEY` | no external scan result | set a StackHawk key to run it; the API's own security tests cover auth, CORS and limits |

## Open: needs hardware or plants

- Bench tests in `bring_up.md`: sleep current, charging, Thread range, on-chip HMAC, LED current
  and fail-safe with the real AL8860.
- Calibrate the plant model (leaf gas-exchange A-Ci curve: `vcmax25`, `jmax25`, `g1`).
- Measure LED light at plant height with a PAR sensor (`LedParams`).
- Rerun `eval_forecast.py` on a few weeks of node data (tested on outdoor weather so far).
- SHT40 offset while charging; lux calibration with the lid on.

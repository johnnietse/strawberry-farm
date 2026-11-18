# Issues log

Every problem found while finishing G.O.S. rev 3.1, what it would have caused, and what was
done. Newest round first. Status: **fixed**, **open (needs hardware)**, or **outside the
project** (the development PC, not the system). Last updated 2026-11-15.

Evidence for "fixed": gateway 81 tests, ml_engine 13 tests, firmware host test, all four firmware
builds, and `tests/e2e/run_e2e.sh` (17 checks, with torch, the Chronos model, the local Qwen
model, the curated dataset and Grafana) all pass.

## Round 6: secrets, crystal, drawings (2026-11-16)

*Table 1. Round 6 (secrets, crystal, drawings, assembly): each issue, its effect and its status.*

| # | Issue | Effect | Status |
|---|---|---|---|
| 39 | `docker-compose.yml` fell back to a fixed database password (in the repository since the first commit) and Grafana to a fixed admin password | anyone could read the default; a stack started without `.env` used it | **fixed**: no defaults; compose refuses to start without the passwords. History: both branches and the release tag were rewritten on 2026-11-17 so the old defaults no longer appear in any commit (commit IDs changed; re-clone any older copy) |
| 40 | Secrets audit of both branches, the PR and the release | none of `.env`, the API token, node keys or `credentials.conf` was ever pushed; the only network key in history is OpenThread's public example key (legacy rev 2 firmware) | **checked** |
| 41 | Crystal Y1 checked by datasheet only | load capacitance not shown in a circuit | **verified**: Nordic reference circuit uses the same 9 pF crystal with 12 pF NP0; LTspice loop model: +0.3 ppm at the design stray, at most 38 ppm over 0 to 4 pF |
| 42 | No engineering drawings of the enclosures | nothing to hand to a print shop or reviewer | **added**: two drawing sheets (orthographic views, exploded view, parts list, title block) |
| 43 | Docker Desktop failed to start ("rename ... engine.sock ... cannot be accessed") | development PC only | **fixed (development PC)**: stale secrets-engine socket removed, WSL restarted |
| 44 | No drawing of how the units go together, and nothing about the gateway's housing | assembler has to work out cable routing, order and placement | **added**: system assembly drawing GOS-MECH-003 (both enclosures at 1:2, joint exploded view, interconnect list W1 to W7, assembly sequence); gateway uses the Pi's official case, Dongle on a USB 2.0 extension |
| 45 | The control cable's 2.54 mm housing does not pass the M12 gland's seal | cable cannot be fitted as bought | **documented**: release the pins, thread the wires through the gland, refit the pins (drawing sheet 1 note 2, mechanical/README.md) |
| 46 | Climate nodes have an open gland hole (no LED cable) | humid air and drips enter | **documented**: M12 x 1.5 blanking plug (ordering.md) |
| 47 | Light node 5 V adapter, Pi case and power supply, USB extension missing from the shopping list | incomplete order | **added** to ordering.md |

## Round 5: whole-system review (`system_review.md`)

*Table 2. Round 5 (whole-system review): each issue, its effect and its status.*

| # | Issue | Effect | Status |
|---|---|---|---|
| 29 | Every node was a sleepy end device; those never relay | no mesh: each node had to reach the border router directly | **fixed**: `router.conf` (Thread router) for USB-powered light nodes; deployment plan in `system_review.md` |
| 30 | Thread poll every 1 s | an estimated 20 to 40 uA, more than the rest of the sleeping board | **fixed**: 30 s poll, fast polls only after each packet |
| 31 | Keys readable with a debugger | a stolen node gives away the Thread network key | **added**: `lock.conf` (APPROTECT) for nodes in service |
| 32 | ML dataset joined the requested LED schedule, had no plant-model columns, and the API could not serve it (no `data/` mount) | wrong training data; `/api/curated` always "pending" | **fixed**: joins `led_commands` and `plant_state` per node; API mounts `data/`; e2e checks the columns |
| 33 | `/api/phenotype` made its own fixed LED recommendation | two contradicting sources of LED decisions | **fixed**: one source (controller and manual settings) |
| 34 | Simulators ran in every deployment unless compose was edited; `sync_engine` depended on them | simulated rows mixed with real ones | **fixed**: `--profile sim` |
| 35 | Grafana: fixed database password and user in its datasource, no dashboards, plugins downloaded at each start, unpinned image | Grafana could not reach the database with any `.env`; nothing to look at | **fixed**: credentials from `.env`, provisioned phytotron dashboard, Grafana 13.2.6; e2e checks it |
| 36 | Database healthcheck passed during first-start setup (and assumed user "researcher") | services and tests started against a database about to restart | **fixed**: ready only when the schema exists, with the configured user |
| 37 | Assistant rate limit trusted `X-Forwarded-For` from anyone | a direct caller could bypass the limit by changing the header | **fixed**: trusted only behind nginx (`GOS_TRUST_PROXY`), port 5000 local by default, global limit for the paid backend |
| 38 | Plugin hooks call `python3`, which is the Windows Store stub here | "Python was not found" on every tool call (no effect on the project) | **fixed (development PC)**: `~/bin/python3` forwards to `py -3`; hooks now run (hookify tested) |

## Round 4: access, models, end-to-end with every model

*Table 3. Round 4 (access, models, end-to-end test with every model): each issue, its effect and its status.*

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

*Table 4. Round 3 (security review of the API): each issue, its effect and its status.*

| # | Issue | Effect | Status |
|---|---|---|---|
| 11 | No authentication on LED and event changes, CORS open to every site | any web page a researcher visited, or anyone on the network, could change the lights | **fixed**: token in the `Authorization` header for every change; CORS off by default |
| 12 | Assistant open to anyone, no size limit | could run up a paid model bill | **fixed**: token, length cap, rate limit |
| 13 | Dashboard took the API address from `?api=` in the link | a crafted link could send the dashboard, and the token, to another server | **fixed**: removed; the server is chosen inside the page only |

## Round 2: software review

*Table 5. Round 2 (software review): each issue, its effect and its status.*

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

*Table 6. Round 1 (hardware review): each issue, its effect and its status.*

| # | Issue | Effect | Status |
|---|---|---|---|
| 21 | LED inductor 47 uH: AL8860 switched up to 1.27 MHz (limit 1 MHz) | current error, heating | **fixed**: 100 uH, 435 to 672 kHz (LTspice) |
| 22 | CTRL pull-down 2.2 k left 24 mV margin | LEDs could glow with the cable unplugged | **fixed**: 1.5 k, 0.12 V worst case |
| 23 | Switching loops long, through vias | noise near the radio and sensors | **fixed**: routed by hand, measured |
| 24 | Raspberry Pi guide's network settings did not match the firmware | nodes would never join | **fixed** |

## Development PC (not the project)

*Table 7. Problems on the development PC, not in the project, and what to do about each.*

| # | Issue | Effect | What to do |
|---|---|---|---|
| 25 | `python3` is the Microsoft Store stub, so plugin hooks written in Python fail ("Python was not found", about 1,900 times this session) | none on the project | **worked around** (#38): `~/bin/python3` forwards to `py -3`. For a permanent fix you can also turn off `python.exe` and `python3.exe` under Windows Settings > Apps > Advanced app settings > App execution aliases. |
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

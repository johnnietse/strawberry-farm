#!/usr/bin/env bash
# End-to-end test of the whole software path, no hardware needed:
#   simulated node (signed PACKET_V4) -> coap_receiver -> TimescaleDB -> biology_engine
#   (plant model + Chronos-Bolt forecast from the repository copy, offline) -> LED controller
#   (PPO policy) -> safety monitor -> signed LED command in the CoAP reply -> checked by the
#   simulated node with the node's key.
# Also: the dashboard and its /api proxy, token protection, manual override (timed and
# "until switched back"), and the research assistant (local LLM if Ollama runs on the host).
#
#   bash tests/e2e/run_e2e.sh          (from the repo root; needs Docker, about 3 GB free)
#
# Runs as its own compose project (gos_e2e): API on 5055, dashboard on 8088, nothing else on
# the host. Removes its containers, volumes and images at the end (KEEP=1 keeps them running).
set -euo pipefail
cd "$(dirname "$0")/../.."
P=(docker compose -p gos_e2e -f docker-compose.yml -f tests/e2e/e2e.override.yml)
API=http://localhost:5055
DASH=http://localhost:8088
PY=${PYTHON:-python}
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

export GOS_API_TOKEN="e2e-$($PY -c 'import secrets;print(secrets.token_hex(16))')"
AUTH=(-H "Authorization: Bearer $GOS_API_TOKEN")
$PY - <<'EOF'
import json, os
json.dump({"nodes": {"7": {"key": os.urandom(16).hex()}}}, open("tests/e2e/node_keys.json", "w"))
EOF
cleanup() {
  if [ "${KEEP:-0}" = 1 ]; then echo "KEEP=1: stack left running (project gos_e2e)"; return; fi
  "${P[@]}" --profile e2e down -v --rmi local >/dev/null 2>&1 || true
  rm -f tests/e2e/node_keys.json
}
trap cleanup EXIT

"${P[@]}" up -d --build db
"${P[@]}" up -d --wait db
# 24 h of history for the test node, so the climate forecast has context from the first cycle
"${P[@]}" exec -T db psql -q -U "${POSTGRES_USER:-researcher}" -d "${POSTGRES_DB:-strawberry_research}" -c "
  INSERT INTO raw_telemetry (time, node_id, sample_identity, temp_c, humidity_pct, battery_mv, payload)
  SELECT NOW() - make_interval(mins => m), 'RF-NODE-07', 'EUI64:F4CE360011223344',
         22 + 3 * sin(2 * pi() * (m / 1440.0)), 68 - 6 * sin(2 * pi() * (m / 1440.0)), 3900,
         jsonb_build_object('light_lux', 8000, 'authenticated', false, 'source', 'e2e-history')
  FROM generate_series(1440, 2, -2) AS m;"
"${P[@]}" up -d --build api biology_engine ml_engine coap_receiver_e2e dashboard
sleep 40   # first controller run and biology engine cycle (Chronos loads once)

out=$("${P[@]}" --profile e2e run --rm -e PACKETS=8 -e PERIOD_S=8 fake_node)
echo "$out" | grep -E "packet|RESULT"
check "8/8 replies carry a valid signed LED command" 'echo "$out" | grep -q "RESULT 8/8"'

plant=$(curl -sf "$API/api/plant")
check "plant state for RF-NODE-07" "echo '$plant' | $PY -c \"import json,sys; d=[x for x in json.load(sys.stdin) if x['node_id']=='RF-NODE-07']; assert d[0]['photosynthesis_umol_m2_s'] > 0\""
check "Chronos forecast in plant state" "echo '$plant' | $PY -c \"import json,sys; d=[x for x in json.load(sys.stdin) if x['node_id']=='RF-NODE-07'][0]['forecast']; assert d and d['backend']=='chronos' and len(d['vpd_kpa'])==8, d\""

check "dashboard page served" '[ "$(curl -s -o /dev/null -w "%{http_code}" $DASH/)" = 200 ]'
check "dashboard /api proxy reaches the API" "curl -sf $DASH/api/nodes | $PY -c 'import json,sys; assert any(n[\"node_id\"]==\"RF-NODE-07\" for n in json.load(sys.stdin))'"
check "write without token refused (401)" '[ "$(curl -s -o /dev/null -w "%{http_code}" -XPOST $DASH/api/led -H "Content-Type: application/json" -d "{\"blue_pct\":100,\"red_pct\":100}")" = 401 ]'
check "write with a wrong token refused (401)" '[ "$(curl -s -o /dev/null -w "%{http_code}" -XPOST $DASH/api/led -H "Authorization: Bearer wrong-token-wrong-token" -H "Content-Type: application/json" -d "{\"blue_pct\":100,\"red_pct\":100}")" = 401 ]'

curl -sf -XPOST "$DASH/api/led" "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{"node":"RF-NODE-07","blue_pct":10,"red_pct":90,"minutes":0}' >/dev/null
out=$("${P[@]}" --profile e2e run --rm -e PACKETS=1 -e PERIOD_S=0 fake_node)
check "manual override (until cleared) reaches the node" 'echo "$out" | grep -q "blue 10 %, red 90 %"'
check "override listed with no expiry" "curl -sf $API/api/plant | $PY -c \"import json,sys; s=[x for x in json.load(sys.stdin) if x['node_id']=='RF-NODE-07'][0]['led_setpoint']; assert s['source']=='manual' and s['expires_at'] is None\""
ended=$(curl -sf -XDELETE "$DASH/api/led/override?node=RF-NODE-07" "${AUTH[@]}")
check "back to automatic" 'echo "$ended" | grep -q "\"ended\":1"'

asst=$(curl -sf -XPOST "$DASH/api/assistant" "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{"text":"Grey mould on the fruit in row 1, a lot of it","commit":true}')
echo "     assistant: $asst"
check "assistant files the note as DISEASE in row 1" "echo '$asst' | $PY -c \"import json,sys; d=json.load(sys.stdin); assert d['event']['event_type']=='DISEASE' and d['event']['sector']=='row 1' and d['stored']\""
check "event visible through the API" "curl -sf $API/api/events | grep -q 'Grey mould'"

check "no errors in service logs" '! "${P[@]}" logs biology_engine ml_engine coap_receiver_e2e api 2>&1 | grep -E "Traceback|cycle failed|ERROR" | grep -v "assistant backend" '

[ $fail = 0 ] && echo "E2E PASSED" || { echo "E2E FAILED"; exit 1; }

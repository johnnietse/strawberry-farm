#!/usr/bin/env bash
# End-to-end test of the whole software path, no hardware needed:
#   simulated node (signed PACKET_V4) -> coap_receiver -> TimescaleDB -> biology_engine
#   -> LED controller (PPO policy) -> safety monitor -> signed LED command in the CoAP reply
#   -> checked by the simulated node with the node's key.
# Also checks the API's plant state, manual LED override and research assistant.
#
#   bash tests/e2e/run_e2e.sh          (from the repo root; needs Docker)
#
# Runs as its own compose project (gos_e2e) with no host ports except the API on 5055,
# and removes its containers, volumes and images at the end. The ML image is built without
# torch (FORECAST=0) to keep it small; the forecast backends are tested in ml_engine/.
set -euo pipefail
cd "$(dirname "$0")/../.."
P=(docker compose -p gos_e2e -f docker-compose.yml -f tests/e2e/e2e.override.yml)
API=http://localhost:5055
fail=0

python - <<'EOF'
import json, os
json.dump({"nodes": {"7": {"key": os.urandom(16).hex()}}}, open("tests/e2e/node_keys.json", "w"))
EOF
cleanup() { "${P[@]}" --profile e2e down -v --rmi local >/dev/null 2>&1 || true; rm -f tests/e2e/node_keys.json; }
trap cleanup EXIT

"${P[@]}" up -d --build db api biology_engine ml_engine coap_receiver_e2e
sleep 25   # first controller run and biology engine cycle

out=$("${P[@]}" --profile e2e run --rm -e PACKETS=8 -e PERIOD_S=8 fake_node)
echo "$out" | grep -E "packet|RESULT"
echo "$out" | grep -q "RESULT 8/8" || { echo "FAIL: not every reply carried a valid LED command"; fail=1; }

curl -sf "$API/api/plant" | python -c "import json,sys; d=[x for x in json.load(sys.stdin) if x['node_id']=='RF-NODE-07']; assert d and d[0]['photosynthesis_umol_m2_s'] is not None; print('plant state ok:', d[0]['photosynthesis_umol_m2_s'], 'umol/m2/s')" || fail=1

curl -sf -XPOST "$API/api/led" -H "Content-Type: application/json" -d '{"node":"RF-NODE-07","blue_pct":10,"red_pct":90,"minutes":5}' >/dev/null
out=$("${P[@]}" --profile e2e run --rm -e PACKETS=1 -e PERIOD_S=0 fake_node)
echo "$out" | grep -q "blue 10 %, red 90 %" && echo "manual override ok" || { echo "FAIL: manual override not sent"; fail=1; }

curl -sf -XPOST "$API/api/assistant" -H "Content-Type: application/json" -d '{"text":"aphids on bench 2"}' \
  | python -c "import json,sys; e=json.load(sys.stdin)['event']; assert e['event_type']=='PEST' and e['sector']=='bench 2'; print('assistant ok:', e)" || fail=1

[ $fail = 0 ] && echo "E2E PASSED" || { echo "E2E FAILED"; exit 1; }

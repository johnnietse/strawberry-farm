"""
G.O.S. Research Support API
===========================
REST API for Group 2 GUI: Event logging, yield tracking, LED control.

ELEC 490/498 Requirement: "Fully functional, annotatable, user-friendly GUI
(web browser based). User can input events (pest pressures, fertilizer mixes,
equipment failures, etc) that get fed into the ML pipeline."

Endpoints:
- POST /api/event - Log research events (pest, fertilizer, equipment failure)
- POST /api/yield - Log harvest yield data
- POST /api/led - Update LED schedule
- GET /api/nodes - Get node status summary
- GET /api/events - Get recent events
- GET /api/curated - Get latest curated dataset
- GET /api/plant - Latest plant state per node (biology engine)
- GET /api/led/commands - LED commands sent to the nodes (after the safety monitor)
- DELETE /api/led/override - End manual LED settings; the controller takes over again
- POST /api/assistant - Turn a free-text note into a research event (LLM or rules)
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import psycopg2
import hmac
import os
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

try:
    from assistant import parse_note
except ImportError:  # imported as services.api
    from services.assistant import parse_note

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResearchAPI")

# Security
# - Every request that changes something (POST, PUT, PATCH, DELETE) needs
#   "Authorization: Bearer <GOS_API_TOKEN>". The token is sent as a header, never a cookie, so
#   another web site cannot make a visitor's browser send it (no CSRF). Without GOS_API_TOKEN
#   set, writes are refused: the LEDs are actuators and must not be open to the network.
# - The dashboard reaches the API through its own nginx (same origin, /api/...), so it needs no
#   CORS and works at any address on any network. Other web pages may call the API from a
#   browser only if their origin is listed in GOS_CORS_ORIGINS (comma-separated; "*" = any
#   site may read, and write with the token). Credentials (cookies) are never allowed.
# - The assistant takes at most ASSISTANT_MAX_CHARS characters and ASSISTANT_RATE requests per
#   client per minute (0 = no limit); the Claude backend is a paid model.
API_TOKEN = os.getenv("GOS_API_TOKEN", "")
CORS_ORIGINS = [o.strip() for o in os.getenv("GOS_CORS_ORIGINS", "").split(",") if o.strip()]
if CORS_ORIGINS:
    CORS(app, origins="*" if "*" in CORS_ORIGINS else CORS_ORIGINS, supports_credentials=False,
         allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "DELETE"])
ASSISTANT_MAX_CHARS = int(os.getenv("ASSISTANT_MAX_CHARS", "8000"))
ASSISTANT_RATE = int(os.getenv("ASSISTANT_RATE", "30"))
MAX_OVERRIDE_MIN = 90 * 24 * 60   # timed settings up to 90 days; "minutes": 0 = until cleared
_rate = defaultdict(deque)
_rate_lock = threading.Lock()


@app.before_request
def require_token_for_writes():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    if not API_TOKEN:
        return jsonify({"status": "error", "message": "writes are disabled: set GOS_API_TOKEN"}), 503
    if len(API_TOKEN) < 16:
        return jsonify({"status": "error", "message": "GOS_API_TOKEN is too short (16 characters minimum)"}), 503
    sent = request.headers.get("Authorization", "")
    if not (sent.startswith("Bearer ") and hmac.compare_digest(sent[7:].encode(), API_TOKEN.encode())):
        return jsonify({"status": "error", "message": "missing or wrong API token"}), 401
    return None


def rate_limited(key: str, limit: int, window_s: float = 60.0) -> bool:
    if limit <= 0:
        return False
    now = time.monotonic()
    with _rate_lock:
        q = _rate[key]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        return False

DB_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    """Get a database connection."""
    return psycopg2.connect(DB_URL)


# === EVENT LOGGING (Group 2 GUI) ===

@app.route('/api/event', methods=['POST'])
def log_event():
    """
    Log a research event (pest pressure, fertilizer, equipment failure, etc.)
    Feeds directly into the ML pipeline via the sync engine.
    """
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO research_events
                (event_type, description, severity, created_via_llm, sector_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data.get('type'),
                data.get('description'),
                data.get('severity', 1),
                data.get('is_llm', False),
                data.get('sector', None)
            ))
        conn.commit()
        conn.close()
        logger.info(f"Event logged: {data.get('type')} - {(data.get('description') or '')[:50]}")
        return jsonify({
            "status": "success",
            "message": "Research event synchronized to data backbone."
        }), 201
    except Exception as e:
        logger.error(f"Event logging error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/events', methods=['GET'])
def get_events():
    """Get recent research events."""
    limit = request.args.get('limit', 50, type=int)
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT time, event_type, severity, description, created_via_llm, sector_id
                FROM research_events
                ORDER BY time DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
        conn.close()

        events = [{
            'time': row[0].isoformat() if row[0] else None,
            'type': row[1],
            'severity': row[2],
            'description': row[3],
            'via_llm': row[4],
            'sector': row[5]
        } for row in rows]

        return jsonify(events), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# === YIELD LOGGING ===

@app.route('/api/yield', methods=['POST'])
def log_yield():
    """Log harvest yield data (weight, brix, plant ID)."""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO yield_logs
                (row_index, weight_grams, brix_value, plant_id)
                VALUES (%s, %s, %s, %s)
            """, (
                data.get('row'),
                data.get('weight'),
                data.get('brix'),
                data.get('plant_id')
            ))
        conn.commit()
        conn.close()
        logger.info(f"Yield logged: {data.get('weight')}g @ Brix {data.get('brix')}")
        return jsonify({
            "status": "success",
            "message": "Yield data recorded."
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# === LED CONTROL ===

def _led_levels(data: dict) -> tuple:
    """Blue and red level in % from either {"blue_pct", "red_pct"} or the older
    {"blue_ratio", "red_ratio", "intensity"} form."""
    if "blue_pct" in data or "red_pct" in data:
        b, r = float(data.get("blue_pct", 0)), float(data.get("red_pct", 0))
    else:
        i = float(data.get("intensity", 100))
        b, r = float(data.get("blue_ratio", 0.3)) * i, float(data.get("red_ratio", 0.7)) * i
    if not (0 <= b <= 100 and 0 <= r <= 100):
        raise ValueError("LED levels must be 0..100 %")
    return b, r


@app.route('/api/led', methods=['POST'])
def update_led_schedule():
    """Set the LEDs by hand: {"node": "RF-NODE-01" or "ALL", "blue_pct": 30, "red_pct": 70,
    "minutes": 60}. Overrides the ML controller for that long ("minutes": 0 = until
    DELETE /api/led/override); the gateway's safety monitor still applies (dark period,
    temperature cut-off, ramp limit)."""
    data = request.json or {}
    try:
        b, r = _led_levels(data)
        node = str(data.get('node') or data.get('sector') or 'ALL')
        minutes = int(data.get('minutes', 60))
        if not 0 <= minutes <= MAX_OVERRIDE_MIN:
            raise ValueError(f"minutes must be 0 (until cleared) .. {MAX_OVERRIDE_MIN}")
    except (TypeError, ValueError) as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO led_setpoints (node_id, blue_pct, red_pct, source, reason, expires_at)
                VALUES (%s, %s, %s, 'manual', %s, %s)
            """, (node, b, r, str(data.get('reason', 'dashboard'))[:200],
                  None if minutes == 0 else datetime.now(timezone.utc) + timedelta(minutes=minutes)))
            total = b + r
            cur.execute("""
                INSERT INTO led_schedule_history (blue_ratio, red_ratio, intensity_pct, sector_id)
                VALUES (%s, %s, %s, %s)
            """, (b / total if total else 0, r / total if total else 0, int(round(max(b, r))), node))
        conn.commit()
        conn.close()
        span = "until switched back to automatic" if minutes == 0 else f"for {minutes} min"
        logger.info(f"Manual LED setting for {node}: blue {b:.0f} %, red {r:.0f} % {span}")
        return jsonify({
            "status": "success",
            "message": f"{node}: blue {b:.0f} %, red {r:.0f} % {span} (sent on each node's next packet).",
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/led/override', methods=['DELETE'])
def end_led_override():
    """End manual LED settings (one node with ?node=..., else all)."""
    node = request.args.get('node')
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if node:
                cur.execute("UPDATE led_setpoints SET expires_at = NOW() WHERE source = 'manual' "
                            "AND node_id = %s AND (expires_at IS NULL OR expires_at > NOW())", (node,))
            else:
                cur.execute("UPDATE led_setpoints SET expires_at = NOW() WHERE source = 'manual' "
                            "AND (expires_at IS NULL OR expires_at > NOW())")
            n = cur.rowcount
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "ended": n}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/led/commands', methods=['GET'])
def get_led_commands():
    """LED commands the gateway sent to the nodes, newest first."""
    limit = min(request.args.get('limit', 50, type=int), 500)
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT time, node_id, blue_pct, red_pct, requested_blue, requested_red, safety_notes
                FROM led_commands ORDER BY time DESC LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
        conn.close()
        return jsonify([{
            'time': r[0].isoformat(), 'node_id': r[1], 'blue_pct': r[2], 'red_pct': r[3],
            'requested_blue': r[4], 'requested_red': r[5], 'safety_notes': r[6],
        } for r in rows]), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/plant', methods=['GET'])
def get_plant_state():
    """Latest plant state per node from the biology engine, with the active LED setpoint."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (node_id) node_id, time, ppfd_ambient, ppfd_led, blue_fraction,
                       vpd_kpa, an_umol, gc_mol, transpiration_g_m2_h, dli_mol, climate_forecast
                FROM plant_state WHERE time > NOW() - INTERVAL '1 hour'
                ORDER BY node_id, time DESC
            """)
            rows = cur.fetchall()
            cur.execute("""
                SELECT DISTINCT ON (node_id) node_id, blue_pct, red_pct, source, reason, expires_at
                FROM led_setpoints WHERE expires_at IS NULL OR expires_at > NOW()
                ORDER BY node_id, time DESC
            """)
            setpoints = {r[0]: r for r in cur.fetchall()}
        conn.close()
        out = []
        for r in rows:
            sp = setpoints.get(r[0]) or setpoints.get('ALL')
            out.append({
                'node_id': r[0], 'time': r[1].isoformat(), 'ppfd_ambient': r[2], 'ppfd_led': r[3],
                'blue_fraction': r[4], 'vpd_kpa': r[5], 'photosynthesis_umol_m2_s': r[6],
                'canopy_conductance_mol_m2_s': r[7], 'transpiration_g_m2_h': r[8], 'dli_mol_m2': r[9],
                'forecast': r[10],
                'led_setpoint': None if sp is None else {
                    'blue_pct': sp[1], 'red_pct': sp[2], 'source': sp[3], 'reason': sp[4],
                    'expires_at': sp[5].isoformat() if sp[5] else None},
            })
        return jsonify(out), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/assistant', methods=['POST'])
def assistant_parse():
    """{"text": "...", "commit": false} -> structured research event. With commit true the
    event is also stored in research_events (created_via_llm unless the rules made it)."""
    data = request.json or {}
    text = str(data.get('text', ''))
    if len(text) > ASSISTANT_MAX_CHARS:
        return jsonify({"status": "error", "message": f"note longer than {ASSISTANT_MAX_CHARS} characters"}), 413
    # behind the dashboard's nginx every request comes from nginx: use the client it forwarded.
    # (A direct caller could forge the header, but only after passing the token check.)
    client = (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
              or request.remote_addr or "?")
    if rate_limited(client, ASSISTANT_RATE):
        return jsonify({"status": "error", "message": "too many requests, try again in a minute"}), 429
    try:
        event, backend = parse_note(text)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    stored = False
    if data.get('commit'):
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO research_events (event_type, description, severity, created_via_llm, sector_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (event['event_type'], text, event['severity'], backend != 'rules', event['sector']))
            conn.commit()
            conn.close()
            stored = True
        except Exception as e:
            return jsonify({"status": "error", "message": str(e), "event": event, "backend": backend}), 500
    return jsonify({"event": event, "backend": backend, "stored": stored}), 200


@app.route('/api/led', methods=['GET'])
def get_led_schedule():
    """Get current LED schedule."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT time, blue_ratio, red_ratio, intensity_pct, sector_id
                FROM led_schedule_history
                ORDER BY time DESC
                LIMIT 1
            """)
            row = cur.fetchone()
        conn.close()

        if row:
            return jsonify({
                'time': row[0].isoformat() if row[0] else None,
                'blue_ratio': row[1],
                'red_ratio': row[2],
                'intensity': row[3],
                'sector': row[4]
            }), 200
        else:
            return jsonify({'message': 'No LED schedule set'}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# === NODE STATUS ===

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Get summary of all nodes and their latest readings."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (node_id)
                    node_id, sample_identity, temp_c, humidity_pct,
                    par_umol, battery_mv, rssi, time,
                    (payload->>'light_lux')::double precision, (payload->>'charging')::boolean
                FROM raw_telemetry
                WHERE time > NOW() - INTERVAL '1 day'
                ORDER BY node_id, time DESC
            """)
            rows = cur.fetchall()
        conn.close()

        nodes = [{
            'node_id': row[0],
            'sample_identity': row[1],
            'temp_c': row[2],
            'humidity_pct': row[3],
            'par_umol': row[4],
            'battery_mv': row[5],
            'rssi': row[6],
            'last_seen': row[7].isoformat() if row[7] else None,
            'light_lux': row[8],
            'charging': row[9],
        } for row in rows]

        return jsonify(nodes), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# === CURATED DATASET ACCESS ===

@app.route('/api/curated', methods=['GET'])
def get_curated_dataset():
    """Download the latest ML-ready curated dataset."""
    try:
        dataset_path = "/app/data/curated_research_dataset.csv"
        if os.path.exists(dataset_path):
            return send_file(
                dataset_path,
                mimetype='text/csv',
                as_attachment=True,
                download_name='curated_research_dataset.csv'
            )
        else:
            return jsonify({
                "status": "pending",
                "message": "Curated dataset not yet generated. Check back in 5 minutes."
            }), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# === PHENOTYPING ENDPOINTS ===

@app.route('/api/phenotype', methods=['POST'])
def calculate_phenotype():
    """
    Calculate real-time phenotype metrics from sensor data.

    Input: {"temp_c": 25.0, "humidity_pct": 65.0, "par_umol": 800.0}
    Output: VPD, transpiration, stress score, recommendations
    """
    data = request.json
    try:
        temp_c = float(data.get('temp_c', 25.0))
        humidity_pct = float(data.get('humidity_pct', 60.0))
        par_umol = float(data.get('par_umol', 500.0))

        # VPD Calculation (Tetens equation)
        import numpy as np
        svp = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
        avp = svp * (humidity_pct / 100.0)
        vpd = round(svp - avp, 3)

        # VPD Classification
        if vpd < 0.4:
            vpd_status = "LOW_TRANSPIRATION"
        elif vpd < 0.8:
            vpd_status = "OPTIMAL"
        elif vpd < 1.2:
            vpd_status = "MILD_STRESS"
        elif vpd < 1.5:
            vpd_status = "MODERATE_STRESS"
        else:
            vpd_status = "SEVERE_STRESS"

        # Transpiration Estimate (simplified Penman-Monteith)
        rn = par_umol * 0.22  # PAR to net radiation
        gamma = 0.066  # Psychrometric constant
        delta = 4098 * 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3)) / \
                ((temp_c + 237.3) ** 2)
        stomatal_factor = min(1.0, par_umol / 500)
        stress_factor = max(0.2, 1 - (vpd - 0.8) / 2) if vpd > 0.8 else 1.0
        et = (delta * rn * 0.0036 + gamma * vpd * stomatal_factor * stress_factor) / \
             (delta + gamma)
        transpiration = round(max(0, et * 1000 * 3.5), 2)  # g/m²/h

        # Stress Detection
        stress_score = 0
        if temp_c > 30:
            stress_score += 20
        if temp_c < 15:
            stress_score += 15
        if vpd > 1.5:
            stress_score += 25
        if par_umol < 100:
            stress_score += 10
        if humidity_pct > 90 or humidity_pct < 40:
            stress_score += 15
        stress_score = min(100, stress_score)

        if stress_score < 10:
            stress_level = "OPTIMAL"
        elif stress_score < 25:
            stress_level = "MILD"
        elif stress_score < 50:
            stress_level = "MODERATE"
        elif stress_score < 75:
            stress_level = "SEVERE"
        else:
            stress_level = "CRITICAL"

        # LED Recommendations based on phenotype
        if vpd > 1.2:
            led_recommendation = {"action": "INCREASE_BLUE", "blue": 0.6, "red": 0.4,
                                   "reason": "High VPD - blue light helps maintain stomatal conductance"}
        elif temp_c > 28:
            led_recommendation = {"action": "SHIFT_BLUE", "blue": 0.8, "red": 0.2,
                                   "reason": "Heat stress - blue spectrum reduces thermal load"}
        elif par_umol < 200:
            led_recommendation = {"action": "INCREASE_RED", "blue": 0.3, "red": 0.7,
                                   "reason": "Low light - red promotes photosynthesis"}
        else:
            led_recommendation = {"action": "MAINTAIN", "blue": 0.4, "red": 0.6,
                                   "reason": "Optimal conditions"}

        return jsonify({
            "phenotype": {
                "vpd_kpa": vpd,
                "vpd_status": vpd_status,
                "transpiration_g_m2_h": transpiration,
                "stress_score": stress_score,
                "stress_level": stress_level
            },
            "conditions": {
                "temp_c": temp_c,
                "humidity_pct": humidity_pct,
                "par_umol": par_umol
            },
            "led_recommendation": led_recommendation,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Phenotype calculation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/phenotype/summary', methods=['GET'])
def get_phenotype_summary():
    """
    Get phenotype summary across all nodes (last hour).
    Returns average VPD, transpiration, and stress distribution.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    AVG(temp_c) as avg_temp,
                    AVG(humidity_pct) as avg_humidity,
                    AVG(par_umol) as avg_par,
                    MIN(temp_c) as min_temp,
                    MAX(temp_c) as max_temp,
                    COUNT(DISTINCT node_id) as active_nodes
                FROM raw_telemetry
                WHERE time > NOW() - INTERVAL '1 hour'
            """)
            row = cur.fetchone()
        conn.close()

        if row and row[0]:
            import numpy as np
            temp_c = float(row[0])
            humidity_pct = float(row[1])
            par_umol = float(row[2]) if row[2] else 500.0

            # Calculate VPD
            svp = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
            avp = svp * (humidity_pct / 100.0)
            vpd = round(svp - avp, 3)

            return jsonify({
                "period": "1 hour",
                "active_nodes": row[5],
                "environment": {
                    "avg_temp_c": round(temp_c, 2),
                    "min_temp_c": round(float(row[3]), 2),
                    "max_temp_c": round(float(row[4]), 2),
                    "avg_humidity_pct": round(humidity_pct, 2),
                    "avg_par_umol": round(par_umol, 2)
                },
                "phenotype": {
                    "vpd_kpa": vpd,
                    "vpd_status": "OPTIMAL" if 0.4 <= vpd <= 1.2 else "STRESS"
                },
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "no_data",
                "message": "No telemetry data in last hour"
            }), 200

    except Exception as e:
        logger.error(f"Phenotype summary error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# === HEALTH CHECK ===

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker."""
    return jsonify({"status": "healthy", "service": "gos-research-api"}), 200


if __name__ == "__main__":
    logger.info("=== G.O.S. Research Support API ===")
    logger.info("Endpoints: /api/event, /api/yield, /api/led, /api/nodes, /api/curated, /api/plant, /api/assistant")
    app.run(host='0.0.0.0', port=5000)

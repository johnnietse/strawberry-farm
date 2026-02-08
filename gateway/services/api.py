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
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import psycopg2
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable Dashboard to talk to API
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResearchAPI")

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
        logger.info(f"Event logged: {data.get('type')} - {data.get('description')[:50]}...")
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

@app.route('/api/led', methods=['POST'])
def update_led_schedule():
    """Update LED spectral schedule (blue/red ratio, intensity)."""
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO led_schedule_history 
                (blue_ratio, red_ratio, intensity_pct, sector_id)
                VALUES (%s, %s, %s, %s)
            """, (
                data.get('blue_ratio', 0.3),
                data.get('red_ratio', 0.7),
                data.get('intensity', 100),
                data.get('sector', 'ALL')
            ))
        conn.commit()
        conn.close()
        logger.info(f"LED schedule: Blue={data.get('blue_ratio')}, Red={data.get('red_ratio')}")
        return jsonify({
            "status": "success",
            "message": "LED schedule updated and logged."
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


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
                    par_umol, battery_mv, rssi, time
                FROM raw_telemetry
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
            'last_seen': row[7].isoformat() if row[7] else None
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
    logger.info("Endpoints: /api/event, /api/yield, /api/led, /api/nodes, /api/curated")
    app.run(host='0.0.0.0', port=5000)

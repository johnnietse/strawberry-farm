"""Database access shared by the biology engine and the LED controller."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import psycopg2

ACTIVE_MINUTES = 15


def connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not set")
    return psycopg2.connect(url)


def active_nodes(conn) -> list[dict]:
    """Latest reading of every node seen in the last ACTIVE_MINUTES."""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT ON (node_id) node_id, time, temp_c, humidity_pct, par_umol,
                   (payload->>'light_lux')::double precision, (payload->>'charging')::boolean
            FROM raw_telemetry
            WHERE time > NOW() - INTERVAL '{ACTIVE_MINUTES} minutes'
            ORDER BY node_id, time DESC
        """)
        rows = cur.fetchall()
    conn.commit()
    return [dict(zip(("node_id", "time", "temp_c", "humidity_pct", "par_umol", "light_lux", "charging"), r))
            for r in rows]


def climate_history(conn, node_id: str, hours: int = 48, bucket: str = "15 minutes"):
    """Bucketed temperature and humidity history, oldest first: (times, temp, rh)."""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT time_bucket(INTERVAL '{bucket}', time) AS b, AVG(temp_c), AVG(humidity_pct)
            FROM raw_telemetry
            WHERE node_id = %s AND time > NOW() - INTERVAL '{int(hours)} hours'
              AND temp_c IS NOT NULL AND humidity_pct IS NOT NULL
            GROUP BY b ORDER BY b
        """, (node_id,))
        rows = cur.fetchall()
    conn.commit()
    return [r[0] for r in rows], [float(r[1]) for r in rows], [float(r[2]) for r in rows]


def led_state(conn, node_id: str) -> tuple[float, float]:
    """LED levels the node is running: the last command sent to it, else its current
    setpoint (simulated nodes get no commands), else off."""
    with conn.cursor() as cur:
        cur.execute("SELECT blue_pct, red_pct FROM led_commands WHERE node_id = %s "
                    "AND time > NOW() - INTERVAL '15 minutes' ORDER BY time DESC LIMIT 1", (node_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute("SELECT blue_pct, red_pct FROM led_setpoints WHERE node_id IN (%s, 'ALL') "
                        "AND (expires_at IS NULL OR expires_at > NOW()) "
                        "ORDER BY (node_id = %s) DESC, time DESC LIMIT 1", (node_id, node_id))
            row = cur.fetchone()
    conn.commit()
    return (float(row[0]), float(row[1])) if row else (0.0, 0.0)


def last_plant_state(conn, node_id: str):
    with conn.cursor() as cur:
        cur.execute("SELECT time, dli_mol, ppfd_ambient, ppfd_led FROM plant_state WHERE node_id = %s "
                    "ORDER BY time DESC LIMIT 1", (node_id,))
        row = cur.fetchone()
    conn.commit()
    return row


def insert_plant_state(conn, node_id: str, s: dict) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO plant_state (node_id, ppfd_ambient, ppfd_led, blue_fraction, vpd_kpa, an_umol,
                                     gc_mol, transpiration_g_m2_h, dli_mol, climate_forecast)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (node_id, s["ppfd_ambient"], s["ppfd_led"], s["blue_fraction"], s["vpd_kpa"], s["an_umol"],
              s["gc_mol"], s["transpiration_g_m2_h"], s["dli_mol"],
              json.dumps(s["forecast"]) if s.get("forecast") else None))
    conn.commit()


def manual_override(conn, node_id: str) -> bool:
    """True if a person set this node's (or every node's) LEDs and that setting has not expired."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM led_setpoints WHERE node_id IN (%s, 'ALL') AND source = 'manual' "
                    "AND (expires_at IS NULL OR expires_at > NOW()) LIMIT 1", (node_id,))
        row = cur.fetchone()
    conn.commit()
    return row is not None


def insert_setpoint(conn, node_id: str, blue: float, red: float, source: str, reason: str,
                    valid_minutes: int) -> None:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO led_setpoints (node_id, blue_pct, red_pct, source, reason, expires_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (node_id, round(blue, 1), round(red, 1), source, reason,
                     datetime.now(timezone.utc) + timedelta(minutes=valid_minutes)))
    conn.commit()

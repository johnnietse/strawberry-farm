-- G.O.S. Research Database Schema (TimescaleDB Optimized)
-- Targets: Queen's University ELEC 490/498 Data Backbone
-- Database: TimescaleDB (PostgreSQL extension for time-series)

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Hardware Tier: Wireless nRF52 Node Telemetry
CREATE TABLE IF NOT EXISTS raw_telemetry (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_id TEXT NOT NULL, 
    sample_identity TEXT, -- MAC Address or EUI64
    temp_c DOUBLE PRECISION,
    humidity_pct DOUBLE PRECISION,
    par_umol DOUBLE PRECISION,
    battery_mv INTEGER,
    rssi INTEGER,
    payload JSONB -- Additional data
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('raw_telemetry', 'time', if_not_exists => TRUE);

-- 2. Meteorological Tier: Phytotron Sensor Station
CREATE TABLE IF NOT EXISTS met_station_data (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    net_radiation DOUBLE PRECISION,
    spectral_blue_irradiance DOUBLE PRECISION,
    spectral_red_irradiance DOUBLE PRECISION,
    air_temp_c DOUBLE PRECISION,
    relative_humidity_pct DOUBLE PRECISION,
    co2_ppm DOUBLE PRECISION
);

SELECT create_hypertable('met_station_data', 'time', if_not_exists => TRUE);

-- 3. Auxiliary Tier: User-Defined Research Events (Group 2 GUI)
CREATE TABLE IF NOT EXISTS research_events (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50), -- 'PEST', 'FERTILIZER', 'EQUIPMENT_FAIL', 'YIELD'
    severity INT CHECK (severity >= 1 AND severity <= 5),
    description TEXT,
    created_via_llm BOOLEAN DEFAULT FALSE,
    sector_id TEXT
);

SELECT create_hypertable('research_events', 'time', if_not_exists => TRUE);

-- 4. Yield Logging (Auxiliary Source)
CREATE TABLE IF NOT EXISTS yield_logs (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_index INT,
    weight_grams DOUBLE PRECISION,
    brix_value DOUBLE PRECISION, -- Fruit sugar content
    plant_id TEXT
);

SELECT create_hypertable('yield_logs', 'time', if_not_exists => TRUE);

-- 5. LED Control History (ML-Ready Schedule)
CREATE TABLE IF NOT EXISTS led_schedule_history (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    blue_ratio DOUBLE PRECISION CHECK (blue_ratio >= 0 AND blue_ratio <= 1),
    red_ratio DOUBLE PRECISION CHECK (red_ratio >= 0 AND red_ratio <= 1),
    intensity_pct INT CHECK (intensity_pct >= 0 AND intensity_pct <= 100),
    sector_id TEXT
);

SELECT create_hypertable('led_schedule_history', 'time', if_not_exists => TRUE);

-- 6. Node Health Monitoring (For production deployment)
CREATE TABLE IF NOT EXISTS node_health (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_id TEXT NOT NULL,
    battery_mv INTEGER,
    rssi INTEGER,
    parent_rssi INTEGER,
    uptime_seconds BIGINT,
    reboot_count INTEGER
);

SELECT create_hypertable('node_health', 'time', if_not_exists => TRUE);

-- 7. LED setpoints: what the controller, a person (dashboard) or a schedule asks for.
--    coap_receiver sends the newest unexpired row per node (node_id 'ALL' = every node),
--    after the safety monitor, in its reply to the node's next packet.
CREATE TABLE IF NOT EXISTS led_setpoints (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_id TEXT NOT NULL,
    blue_pct DOUBLE PRECISION NOT NULL CHECK (blue_pct >= 0 AND blue_pct <= 100),
    red_pct DOUBLE PRECISION NOT NULL CHECK (red_pct >= 0 AND red_pct <= 100),
    source TEXT NOT NULL,          -- 'controller', 'manual', 'schedule'
    reason TEXT,
    expires_at TIMESTAMPTZ
);
SELECT create_hypertable('led_setpoints', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_led_setpoints_node ON led_setpoints (node_id, time DESC);

-- 8. LED commands actually sent to each node (after the safety monitor): the LED state
--    the plants really got, for the ML dataset.
CREATE TABLE IF NOT EXISTS led_commands (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_id TEXT NOT NULL,
    blue_pct INT NOT NULL,
    red_pct INT NOT NULL,
    requested_blue DOUBLE PRECISION,
    requested_red DOUBLE PRECISION,
    counter BIGINT,
    safety_notes TEXT
);
SELECT create_hypertable('led_commands', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_led_commands_node ON led_commands (node_id, time DESC);

-- 9. Plant state from the biology engine (ml_engine/plant_model.py), one row per node per run
CREATE TABLE IF NOT EXISTS plant_state (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_id TEXT NOT NULL,
    ppfd_ambient DOUBLE PRECISION,     -- umol m-2 s-1 from daylight / room light
    ppfd_led DOUBLE PRECISION,         -- umol m-2 s-1 from the LED board
    blue_fraction DOUBLE PRECISION,
    vpd_kpa DOUBLE PRECISION,
    an_umol DOUBLE PRECISION,          -- canopy net photosynthesis, umol CO2 m-2 s-1
    gc_mol DOUBLE PRECISION,           -- canopy conductance, mol H2O m-2 s-1
    transpiration_g_m2_h DOUBLE PRECISION,
    dli_mol DOUBLE PRECISION,          -- daily light integral so far today, mol m-2
    climate_forecast JSONB             -- forecast temperature / humidity / VPD
);
SELECT create_hypertable('plant_state', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_plant_state_node ON plant_state (node_id, time DESC);

-- Compression policies (commented out - requires enabling columnstore first)
-- For TimescaleDB 2.x, enable compression on table first with:
-- ALTER TABLE raw_telemetry SET (timescaledb.compress);
-- SELECT add_compression_policy('raw_telemetry', INTERVAL '7 days', if_not_exists => TRUE);
-- SELECT add_compression_policy('met_station_data', INTERVAL '7 days', if_not_exists => TRUE);

-- Data retention policies (optional - adjust as needed)
-- SELECT add_retention_policy('raw_telemetry', INTERVAL '1 year', if_not_exists => TRUE);

-- Continuous aggregates for faster queries
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_node_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    node_id,
    AVG(temp_c) AS avg_temp,
    MIN(temp_c) AS min_temp,
    MAX(temp_c) AS max_temp,
    AVG(humidity_pct) AS avg_humidity,
    AVG(par_umol) AS avg_par,
    COUNT(*) AS sample_count
FROM raw_telemetry
GROUP BY bucket, node_id
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('hourly_node_stats',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_telemetry_node ON raw_telemetry (node_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON research_events (event_type, time DESC);
CREATE INDEX IF NOT EXISTS idx_node_health ON node_health (node_id, time DESC);

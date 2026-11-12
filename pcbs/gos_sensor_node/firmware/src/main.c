#include "gos_main.h"
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/net/coap.h>
#include <zephyr/net/socket.h>
#include <openthread/coap.h>
#include <openthread/thread.h>
#include <string.h>
#include <stdio.h>

LOG_MODULE_REGISTER(gos_main, LOG_LEVEL_INF);

struct gos_sensor_data g_sensor_data = {0};
struct gos_system_config g_system_config = {
    .sensor_interval_ms = 60000,
    .coap_interval_ms = 300000,
    .log_interval_ms = 10000,
    .spectral_blue_pct = 50,
    .spectral_red_pct = 50,
    .tx_power_dbm = 14,
    .spreading_factor = 7,
    .bandwidth = 125,
    .coding_rate = 1,
};

struct k_mutex sensor_data_mutex;

K_THREAD_STACK_DEFINE(sensor_stack, 4096);
K_THREAD_STACK_DEFINE(radio_stack, 4096);
K_THREAD_STACK_DEFINE(power_stack, 2048);
K_THREAD_STACK_DEFINE(led_stack, 2048);

struct k_thread sensor_thread;
struct k_thread radio_thread;
struct k_thread power_thread;
struct k_thread led_thread;

static struct k_sem coap_ready_sem;
static struct k_sem radio_ready_sem;

static const struct device *sht40_dev = DEVICE_DT_GET(DT_NODELABEL(sht40));
static const struct device *tsl2591_dev = DEVICE_DT_GET(DT_NODELABEL(tsl2591));
static const struct device *bq24075_dev = DEVICE_DT_GET(DT_NODELABEL(bq24075));
static const struct device *tps62740_dev = DEVICE_DT_GET(DT_NODELABEL(tps62740));
static const struct device *dw01a_dev = DEVICE_DT_GET(DT_NODELABEL(dw01a));
static const struct device *sx1262_dev = DEVICE_DT_GET(DT_NODELABEL(sx1262));
static const struct device *l76k_dev = DEVICE_DT_GET(DT_NODELABEL(l76k));
static const struct device *al8860_blue_dev = DEVICE_DT_GET(DT_NODELABEL(al8860_blue));
static const struct device *al8860_red_dev = DEVICE_DT_GET(DT_NODELABEL(al8860_red));
static const struct device *battery_adc_dev = DEVICE_DT_GET(DT_NODELABEL(battery_adc));
static const struct device *power_mgmt_dev = DEVICE_DT_GET(DT_NODELABEL(power_mgmt));
static const struct device *watchdog_dev = DEVICE_DT_GET(DT_NODELABEL(wdt));
static const struct device *ext_flash_dev = DEVICE_DT_GET(DT_NODELABEL(ext_flash));

static struct coap_resource coap_sensor_resource;
static struct coap_resource coap_config_resource;
static struct coap_resource coap_status_resource;

static struct coap_client coap_client;
static struct sockaddr_in6 coap_server_addr;

static void sensor_data_lock(void)
{
    k_mutex_lock(&sensor_data_mutex, K_FOREVER);
}

static void sensor_data_unlock(void)
{
    k_mutex_unlock(&sensor_data_mutex);
}

static int read_sht40(void)
{
    if (!device_is_ready(sht40_dev)) {
        LOG_WRN("SHT40 not ready");
        return -ENODEV;
    }

    struct sensor_value temp, hum;
    int err = sensor_sample_fetch(sht40_dev);
    if (err) {
        LOG_ERR("SHT40 sample fetch failed: %d", err);
        return err;
    }

    err = sensor_channel_get(sht40_dev, SENSOR_CHAN_AMBIENT_TEMP, &temp);
    if (err) return err;

    err = sensor_channel_get(sht40_dev, SENSOR_CHAN_HUMIDITY, &hum);
    if (err) return err;

    sensor_data_lock();
    g_sensor_data.temp_c = sensor_value_to_double(&temp);
    g_sensor_data.humidity_pct = sensor_value_to_double(&hum);
    sensor_data_unlock();

    return 0;
}

static int read_tsl2591(void)
{
    if (!device_is_ready(tsl2591_dev)) {
        LOG_WRN("TSL2591 not ready");
        return -ENODEV;
    }

    struct sensor_value lux;
    int err = sensor_sample_fetch(tsl2591_dev);
    if (err) {
        LOG_ERR("TSL2591 sample fetch failed: %d", err);
        return err;
    }

    err = sensor_channel_get(tsl2591_dev, SENSOR_CHAN_LIGHT, &lux);
    if (err) return err;

    sensor_data_lock();
    g_sensor_data.lux = sensor_value_to_double(&lux);
    sensor_data_unlock();

    return 0;
}

static int read_battery_adc(void)
{
    if (!device_is_ready(battery_adc_dev)) {
        LOG_WRN("Battery ADC not ready");
        return -ENODEV;
    }

    struct adc_sequence sequence = {
        .channels = BIT(0) | BIT(1) | BIT(2),
        .buffer = NULL,
        .buffer_size = 0,
        .resolution = 12,
        .oversampling = 4,
        .calibrate = true,
    };

    int16_t buf[3];
    sequence.buffer = buf;
    sequence.buffer_size = sizeof(buf);

    int err = adc_read(battery_adc_dev, &sequence);
    if (err) {
        LOG_ERR("ADC read failed: %d", err);
        return err;
    }

    sensor_data_lock();
    g_sensor_data.battery_mv = (int16_t)((buf[0] * 600 * 2) / 4095);  /* 1M/1M divider, 0.6V ref */
    sensor_data_unlock();

    return 0;
}

static void sensor_thread(void *p1, void *p2, void *p3)
{
    LOG_INF("Sensor thread started");

    k_sem_take(&coap_ready_sem, K_FOREVER);

    while (1) {
        int err = read_sht40();
        if (err) LOG_WRN("SHT40 read failed: %d", err);

        err = read_tsl2591();
        if (err) LOG_WRN("TSL2591 read failed: %d", err);

        err = read_battery_adc();
        if (err) LOG_WRN("Battery ADC read failed: %d", err);

        k_sleep(K_MSEC(g_system_config.sensor_interval_ms));
    }
}

static void radio_thread(void *p1, void *p2, void *p3)
{
    LOG_INF("Radio thread started");

    k_sem_take(&radio_ready_sem, K_FOREVER);

    while (1) {
        k_sleep(K_MSEC(g_system_config.coap_interval_ms));

        sensor_data_lock();
        char payload[256];
        int len = snprintf(payload, sizeof(payload),
            "{\"temp\":%.2f,\"hum\":%.1f,\"lux\":%.0f,\"bat\":%d,\"ts\":%u}",
            g_sensor_data.temp_c, g_sensor_data.humidity_pct,
            g_sensor_data.lux, g_sensor_data.battery_mv,
            g_sensor_data.timestamp);
        sensor_data_unlock();

        if (len > 0) {
            struct coap_packet request;
            uint8_t payload[256];
            int len = coap_packet_init(&request, payload, sizeof(payload),
                1, COAP_TYPE_CON, 8, coap_next_token(),
                COAP_METHOD_POST, coap_next_id());
            if (len > 0) {
                coap_packet_append_option(&request, COAP_OPTION_URI_PATH,
                    "sensor", strlen("sensor"));
                coap_packet_append_payload_marker(&request);
                coap_append_data(&request, payload, len);

                int err = coap_send(&coap_client, &request, &coap_server_addr);
                if (err) {
                    LOG_ERR("CoAP send failed: %d", err);
                }
            }
        }

        k_sleep(K_MSEC(g_system_config.coap_interval_ms));
    }
}

static void power_thread(void *p1, void *p2, void *p3)
{
    LOG_INF("Power management thread started");

    while (1) {
        int16_t vbatt = gos_battery_adc_get_vbatt_mv();
        int16_t vbus = gos_battery_adc_get_vbus_mv();
        int16_t vsys = gos_battery_adc_get_vsys_mv();

        if (vbatt > 0 && vbatt < 3300) {
            LOG_WRN("Low battery: %d mV", vbatt);
            gos_power_mgmt_set_state(power_mgmt_dev, GOS_POWER_STATE_SYSTEM_ON_LP);
        } else if (vbus > 4500) {
            gos_power_mgmt_set_state(power_mgmt_dev, GOS_POWER_STATE_ACTIVE_FULL);
        }

        k_sleep(K_SECONDS(60));
    }
}

static void led_thread(void *p1, void *p2, void *p3)
{
    LOG_INF("LED thread started");

    while (1) {
        gos_set_spectral_mix(g_system_config.spectral_blue_pct, g_system_config.spectral_red_pct);
        k_sleep(K_MSEC(1000));
    }
}

static int coap_init(void)
{
    int err = coap_client_init(&coap_client, NULL);
    if (err) return err;

    memset(&coap_server_addr, 0, sizeof(coap_server_addr));
    coap_server_addr.sin6_family = AF_INET6;
    coap_server_addr.sin6_port = htons(5683);
    inet_pton(AF_INET6, "fd00::1", &coap_server_addr.sin6_addr);

    return 0;
}

static void coap_response_cb(struct coap_packet *response, struct coap_reply *reply, const struct sockaddr *from)
{
    LOG_INF("CoAP response received: %d", coap_header_get_code(response));
}

int gos_system_init(void)
{
    int err;

    k_mutex_init(&sensor_data_mutex);
    k_sem_init(&coap_ready_sem, 0, 1);
    k_sem_init(&radio_ready_sem, 0, 1);

    if (!device_is_ready(sht40_dev)) {
        LOG_ERR("SHT40 not ready");
        return -ENODEV;
    }
    if (!device_is_ready(tsl2591_dev)) {
        LOG_WRN("TSL2591 not ready");
    }
    if (!device_is_ready(bq24075_dev)) {
        LOG_WRN("BQ24075 not ready");
    }
    if (!device_is_ready(tps62740_dev)) {
        LOG_WRN("TPS62740 not ready");
    }
    if (!device_is_ready(dw01a_dev)) {
        LOG_WRN("DW01A not ready");
    }
    if (!device_is_ready(sx1262_dev)) {
        LOG_WRN("SX1262 not ready");
    }
    if (!device_is_ready(l76k_dev)) {
        LOG_WRN("L76K not ready");
    }
    if (!device_is_ready(al8860_blue_dev)) {
        LOG_WRN("AL8860 Blue not ready");
    }
    if (!device_is_ready(al8860_red_dev)) {
        LOG_WRN("AL8860 Red not ready");
    }
    if (!device_is_ready(battery_adc_dev)) {
        LOG_WRN("Battery ADC not ready");
    }
    if (!device_is_ready(power_mgmt_dev)) {
        LOG_WRN("Power management not ready");
    }
    if (!device_is_ready(watchdog_dev)) {
        LOG_WRN("Watchdog not ready");
    }
    if (!device_is_ready(ext_flash_dev)) {
        LOG_WRN("External flash not ready");
    }

    int err = coap_init();
    if (err) {
        LOG_ERR("CoAP init failed: %d", err);
        return err;
    }

    err = gos_power_mgmt_init(power_mgmt_dev);
    if (err) {
        LOG_ERR("Power mgmt init failed: %d", err);
        return err;
    }

    err = gos_battery_adc_init(battery_adc_dev);
    if (err) {
        LOG_ERR("Battery ADC init failed: %d", err);
        return err;
    }

    err = gos_watchdog_init(watchdog_dev);
    if (err) {
        LOG_ERR("Watchdog init failed: %d", err);
        return err;
    }

    k_sem_give(&coap_ready_sem);
    k_sem_give(&radio_ready_sem);

    LOG_INF("System initialized successfully");
    return 0;
}

int gos_sensor_thread_start(void)
{
    k_thread_create(&sensor_thread, sensor_stack, K_THREAD_STACK_SIZEOF(sensor_stack),
                    sensor_thread, NULL, NULL, NULL,
                    K_PRIO_COOP(7), 0, K_NO_WAIT);
    k_thread_name_set(&sensor_thread, "sensor_thread");
    return 0;
}

int gos_radio_thread_start(void)
{
    k_thread_create(&radio_thread, radio_stack, K_THREAD_STACK_SIZEOF(radio_stack),
                    radio_thread, NULL, NULL, NULL,
                    K_PRIO_COOP(7), 0, K_NO_WAIT);
    k_thread_name_set(&radio_thread, "radio_thread");
    return 0;
}

int gos_power_thread_start(void)
{
    k_thread_create(&power_thread, power_stack, K_THREAD_STACK_SIZEOF(power_stack),
                    power_thread, NULL, NULL, NULL,
                    K_PRIO_COOP(7), 0, K_NO_WAIT);
    k_thread_name_set(&power_thread, "power_thread");
    return 0;
}

int gos_led_thread_start(void)
{
    k_thread_create(&led_thread, led_stack, K_THREAD_STACK_SIZEOF(led_stack),
                    led_thread, NULL, NULL, NULL,
                    K_PRIO_COOP(7), 0, K_NO_WAIT);
    k_thread_name_set(&led_thread, "led_thread");
    return 0;
}

void gos_sensor_data_lock(void)
{
    k_mutex_lock(&sensor_data_mutex, K_FOREVER);
}

void gos_sensor_data_unlock(void)
{
    k_mutex_unlock(&sensor_data_mutex);
}

int main(void)
{
    LOG_INF("G.O.S. Sensor Node v2.0 starting...");

    int err = gos_system_init();
    if (err) {
        LOG_ERR("System init failed: %d", err);
        return err;
    }

    err = gos_sensor_thread_start();
    if (err) return err;

    err = gos_radio_thread_start();
    if (err) return err;

    err = gos_power_thread_start();
    if (err) return err;

    err = gos_led_thread_start();
    if (err) return err;

    LOG_INF("All threads started, entering main loop");

    while (1) {
        gos_watchdog_feed(watchdog_dev);
        k_sleep(K_SECONDS(10));
    }

    return 0;
}
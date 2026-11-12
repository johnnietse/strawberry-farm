#include "l76k.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

LOG_MODULE_REGISTER(l76k, LOG_LEVEL_INF);

struct l76k_data {
    struct gos_l76k_data data;
    struct gos_l76k_config config;
    struct k_mutex mutex;
    struct k_sem pps_sem;
    struct k_fifo rx_fifo;
    uint8_t rx_buffer[256];
    size_t rx_len;
    bool initialized;
};

static int l76k_uart_configure(const struct device *dev)
{
    const struct gos_l76k_config *config = dev->config;
    struct l76k_data *data = dev->data;
    int err;

    if (!device_is_ready(config->uart.bus)) {
        LOG_ERR("UART device not ready");
        return -ENODEV;
    }

    struct uart_config uart_cfg = {
        .baudrate = config->baudrate,
        .parity = UART_CFG_PARITY_NONE,
        .stop_bits = UART_CFG_STOP_BITS_1,
        .data_bits = UART_CFG_DATA_BITS_8,
        .flow_ctrl = UART_CFG_FLOW_CTRL_NONE,
    };

    int err = uart_configure(config->uart.bus, &uart_cfg);
    if (err) {
        LOG_ERR("Failed to configure UART: %d", err);
        return err;
    }

    if (data->config.pps_gpio.port) {
        if (!gpio_is_ready_dt(&data->config.pps_gpio)) {
            LOG_WRN("PPS GPIO not ready");
        } else {
            gpio_pin_configure_dt(&data->config.pps_gpio, GPIO_INPUT);
            gpio_pin_interrupt_configure_dt(&data->config.pps_gpio, GPIO_INT_EDGE_RISING);
        }
    }

    return 0;
}

static void l76k_uart_callback(const struct device *dev, void *user_data)
{
    struct l76k_data *data = user_data;
    uint8_t c;
    while (uart_fifo_read(data->config.uart.bus, &c, 1) == 1) {
        if (data->rx_len < sizeof(data->rx_buffer) - 1) {
            data->rx_buffer[data->rx_len++] = c;
            if (c == '\n') {
                data->rx_buffer[data->rx_len] = '\0';
                k_fifo_put(&data->rx_fifo, &data->rx_buffer[0]);
                data->rx_len = 0;
            }
        }
    }
}

static int l76k_parse_nmea_gga(const char *sentence, struct gos_l76k_data *data)
{
    /* $GPGGA,time,lat,NS,lon,EW,quality,sats,hdop,alt,M,geoid,M,age,station*checksum */
    char *token;
    char *str = strdup(sentence);
    if (!str) return -ENOMEM;

    char *saveptr;
    token = strtok_r(str, ",", &saveptr); /* $GPGGA */
    token = strtok_r(NULL, ",", &saveptr); /* time */
    token = strtok_r(NULL, ",", &saveptr); /* lat */
    if (!token) { free(str); return -EINVAL; }
    double lat = atof(token);
    token = strtok_r(NULL, ",", &saveptr); /* NS */
    if (token && token[0] == 'S') lat = -lat;
    token = strtok_r(NULL, ",", &saveptr); /* lon */
    if (!token) { free(str); return -EINVAL; }
    double lon = atof(token);
    token = strtok_r(NULL, ",", &saveptr); /* EW */
    if (token && token[0] == 'W') lon = -lon;
    token = strtok_r(NULL, ",", &saveptr); /* quality */
    int quality = atoi(token);
    token = strtok_r(NULL, ",", &saveptr); /* sats */
    int sats = atoi(token);
    token = strtok_r(NULL, ",", &saveptr); /* hdop */
    token = strtok_r(NULL, ",", &saveptr); /* alt */
    double alt = atof(token);
    token = strtok_r(NULL, ",", &saveptr); /* M */
    token = strtok_r(NULL, ",", &saveptr); /* geoid */
    token = strtok_r(NULL, ",", &saveptr); /* age */
    token = strtok_r(NULL, ",", &saveptr); /* station */

    free(str);

    if (quality == 0) return -ENODATA;

    data->latitude = lat;
    data->longitude = lon;
    data->altitude = alt;
    data->satellites = sats;
    data->fix_quality = quality;
    data->valid = true;
    data->timestamp = k_uptime_get_32();

    return 0;
}

static int l76k_parse_nmea_rmc(const char *sentence, struct gos_l76k_data *data)
{
    /* $GPRMC,time,status,lat,NS,lon,EW,speed,course,date,magvar,EW*checksum */
    char *token;
    char *str = strdup(sentence);
    if (!str) return -ENOMEM;

    char *saveptr;
    token = strtok_r(str, ",", &saveptr); /* $GPRMC */
    token = strtok_r(NULL, ",", &saveptr); /* time */
    token = strtok_r(NULL, ",", &saveptr); /* status */
    if (!token || token[0] != 'A') { free(str); return -ENODATA; }
    token = strtok_r(NULL, ",", &saveptr); /* lat */
    if (!token) { free(str); return -EINVAL; }
    double lat = atof(token);
    token = strtok_r(NULL, ",", &saveptr); /* NS */
    if (token && token[0] == 'S') lat = -lat;
    token = strtok_r(NULL, ",", &saveptr); /* lon */
    if (!token) { free(str); return -EINVAL; }
    double lon = atof(token);
    token = strtok_r(NULL, ",", &saveptr); /* EW */
    if (token && token[0] == 'W') lon = -lon;
    token = strtok_r(NULL, ",", &saveptr); /* speed knots */
    double speed_knots = atof(token);
    token = strtok_r(NULL, ",", &saveptr); /* course */
    double course = atof(token);
    token = strtok_r(NULL, ",", &saveptr); /* date */

    free(str);

    data->latitude = lat;
    data->longitude = lon;
    data->speed = speed_knots * 0.514444; /* knots to m/s */
    data->course = course;
    data->valid = true;
    data->timestamp = k_uptime_get_32();

    return 0;
}

static void l76k_uart_callback(const struct device *dev, void *user_data)
{
    struct l76k_data *data = user_data;
    uint8_t c;
    while (uart_fifo_read(data->config.uart.bus, &c, 1) == 1) {
        if (data->rx_len < sizeof(data->rx_buffer) - 1) {
            data->rx_buffer[data->rx_len++] = c;
            if (c == '\n') {
                data->rx_buffer[data->rx_len] = '\0';
                k_fifo_put(&data->rx_fifo, &data->rx_buffer[0]);
                data->rx_len = 0;
            }
        }
    }
}

static void l76k_pps_callback(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
    struct l76k_data *data = CONTAINER_OF(cb, struct l76k_data, pps_cb);
    data->data.pps_sync = true;
    data->data.timestamp = k_uptime_get_32();
    k_sem_give(&data->pps_sem);
}

int gos_l76k_init(const struct device *dev)
{
    struct l76k_data *data = dev->data;
    int err;

    k_mutex_init(&data->mutex);
    k_sem_init(&data->pps_sem, 0, 1);
    k_fifo_init(&data->rx_fifo);

    data->config = *(const struct gos_l76k_config *)dev->config;

    err = l76k_uart_configure(dev);
    if (err) return err;

    uart_callback_set(data->config.uart.bus, l76k_uart_callback, data);

    if (data->config.pps_gpio.port) {
        if (!gpio_is_ready_dt(&data->config.pps_gpio)) {
            LOG_WRN("PPS GPIO not ready");
        } else {
            gpio_pin_configure_dt(&data->config.pps_gpio, GPIO_INPUT);
            gpio_pin_interrupt_configure_dt(&data->config.pps_gpio, GPIO_INT_EDGE_RISING);
            gpio_init_callback(&data->pps_cb, l76k_pps_callback, BIT(data->config.pps_gpio.pin));
            gpio_add_callback(data->config.pps_gpio.port, &data->pps_cb);
        }
    }

    data->initialized = true;
    LOG_INF("L76K GNSS initialized");
    return 0;
}

int gos_l76k_read_position(const struct device *dev, double *lat, double *lon, double *alt)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized || !data->data.valid) return -ENODEV;
    k_mutex_lock(&data->mutex, K_FOREVER);
    if (lat) *lat = data->data.latitude;
    if (lon) *lon = data->data.longitude;
    if (alt) *alt = data->data.altitude;
    k_mutex_unlock(&data->mutex);
    return 0;
}

int gos_l76k_read_velocity(const struct device *dev, double *speed, double *course)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized || !data->data.valid) return -ENODEV;
    k_mutex_lock(&data->mutex, K_FOREVER);
    if (speed) *speed = data->data.speed;
    if (course) *course = data->data.course;
    k_mutex_unlock(&data->mutex);
    return 0;
}

int gos_l76k_read_satellites(const struct device *dev, uint8_t *count, uint8_t *quality)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized || !data->data.valid) return -ENODEV;
    k_mutex_lock(&data->mutex, K_FOREVER);
    if (count) *count = data->data.satellites;
    if (quality) *quality = data->data.fix_quality;
    k_mutex_unlock(&data->mutex);
    return 0;
}

bool gos_l76k_has_fix(const struct device *dev)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized) return false;
    k_mutex_lock(&data->mutex, K_FOREVER);
    bool valid = data->data.valid;
    k_mutex_unlock(&data->mutex);
    return valid;
}

bool gos_l76k_has_pps_sync(const struct device *dev)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized) return false;
    k_mutex_lock(&data->mutex, K_FOREVER);
    bool sync = data->data.pps_sync;
    k_mutex_unlock(&data->mutex);
    return sync;
}

int gos_l76k_get_timestamp(const struct device *dev, uint32_t *timestamp)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized) return -ENODEV;
    k_mutex_lock(&data->mutex, K_FOREVER);
    *timestamp = data->data.timestamp;
    k_mutex_unlock(&data->mutex);
    return 0;
}

int gos_l76k_set_baudrate(const struct device *dev, uint32_t baud)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized) return -ENODEV;

    struct uart_config uart_cfg = {
        .baudrate = baud,
        .parity = UART_CFG_PARITY_NONE,
        .stop_bits = UART_CFG_STOP_BITS_1,
        .data_bits = UART_CFG_DATA_BITS_8,
        .flow_ctrl = UART_CFG_FLOW_CTRL_NONE,
    };

    return uart_configure(data->config.uart.bus, &uart_cfg);
}

int gos_l76k_set_update_rate(const struct device *dev, uint16_t hz)
{
    /* Send PMTK220 command to set update rate */
    return 0;
}

int gos_l76k_enable_pps(const struct device *dev, bool enable)
{
    struct l76k_data *data = dev->data;
    if (!data->initialized) return -ENODEV;

    if (data->config.pps_gpio.port) {
        if (enable) {
            gpio_pin_interrupt_configure_dt(&data->config.pps_gpio, GPIO_INT_EDGE_RISING);
        } else {
            gpio_pin_interrupt_configure_dt(&data->config.pps_gpio, GPIO_INT_DISABLE);
        }
    }
    return 0;
}

#define DT_DRV_COMPAT quectel_l76k

static struct l76k_data l76k_data_0 = {
    .config = {
        .uart = UART_DT_SPEC_INST_GET(0),
        .pps_gpio = GPIO_DT_SPEC_INST_GET_OR(0, pps_gpios, {0}),
        .baudrate = DT_INST_PROP(0, current_speed),
    },
};

DEVICE_DT_INST_DEFINE(0, gos_l76k_init, NULL,
                      &l76k_data_0, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
#include "watchdog.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/watchdog.h>
#include <zephyr/kernel.h>

LOG_MODULE_REGISTER(watchdog, LOG_LEVEL_INF);

static int watchdog_init(const struct device *dev)
{
    struct gos_watchdog_data *data = dev->data;
    const struct gos_watchdog_config *config = dev->config;

    k_mutex_init(&data->mutex);

    if (!device_is_ready(DEVICE_DT_GET(DT_NODELABEL(wdt)))) {
        LOG_ERR("Watchdog device not ready");
        return -ENODEV;
    }

    struct wdt_timeout_cfg wdt_config = {
        .window = {
            .min = config->window_mode ? config->window_ms : 0,
            .max = config->timeout_ms,
        },
        .callback = NULL,
        .flags = WDT_FLAG_RESET_SOC,
    };

    int err = wdt_install(DEVICE_DT_GET(DT_NODELABEL(wdt)), &wdt_config);
    if (err) {
        LOG_ERR("Failed to install watchdog: %d", err);
        return err;
    }

    err = wdt_setup(DEVICE_DT_GET(DT_NODELABEL(wdt)), WDT_OPT_PAUSE_HALTED_BY_DBG);
    if (err) {
        LOG_ERR("Failed to setup watchdog: %d", err);
        return err;
    }

    data->initialized = true;
    data->timeout_ms = config->timeout_ms;
    data->window_mode = config->window_mode;
    data->window_ms = config->window_ms;
    data->feed_count = 0;
    data->reset_count = 0;
    data->last_feed_time = k_uptime_get_32();

    LOG_INF("Watchdog initialized (timeout=%d ms, window=%d ms)", config->timeout_ms, config->window_ms);
    return 0;
}

int gos_watchdog_feed(const struct device *dev)
{
    struct gos_watchdog_data *data = dev->data;

    if (!data->initialized) {
        return -ENODEV;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);

    int err = wdt_feed(DEVICE_DT_GET(DT_NODELABEL(wdt)), 0);
    if (err == 0) {
        data->feed_count++;
        data->last_feed_time = k_uptime_get_32();
    }

    k_mutex_unlock(&data->mutex);
    return err;
}

int gos_watchdog_set_timeout(const struct device *dev, uint32_t timeout_ms)
{
    struct gos_watchdog_data *data = dev->data;

    if (!data->initialized) {
        return -ENODEV;
    }

    if (timeout_ms < 100 || timeout_ms > 60000) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    data->timeout_ms = timeout_ms;
    k_mutex_unlock(&data->mutex);

    /* Reinstall watchdog with new timeout */
    struct wdt_timeout_cfg wdt_config = {
        .window = {
            .min = data->window_mode ? data->window_ms : 0,
            .max = data->timeout_ms,
        },
        .callback = NULL,
        .flags = WDT_FLAG_RESET_SOC,
    };

    int err = wdt_install(DEVICE_DT_GET(DT_NODELABEL(wdt)), &wdt_config);
    if (err) {
        LOG_ERR("Failed to reinstall watchdog: %d", err);
        return err;
    }

    return 0;
}

int gos_watchdog_set_window(const struct device *dev, uint32_t window_ms)
{
    struct gos_watchdog_data *data = dev->data;

    if (!data->initialized) {
        return -ENODEV;
    }

    if (window_ms >= data->timeout_ms) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    data->window_ms = window_ms;
    data->window_mode = (window_ms > 0);
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_watchdog_get_timeout(const struct device *dev, uint32_t *timeout_ms)
{
    struct gos_watchdog_data *data = dev->data;

    if (!data->initialized || !timeout_ms) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    *timeout_ms = data->timeout_ms;
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_watchdog_get_window(const struct device *dev, uint32_t *window_ms)
{
    struct gos_watchdog_data *data = dev->data;

    if (!data->initialized || !window_ms) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    *window_ms = data->window_ms;
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_watchdog_get_stats(const struct device *dev, uint32_t *feed_count, uint32_t *reset_count)
{
    struct gos_watchdog_data *data = dev->data;

    if (!data->initialized || !feed_count || !reset_count) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    *feed_count = data->feed_count;
    *reset_count = data->reset_count;
    k_mutex_unlock(&data->mutex);

    return 0;
}

bool gos_watchdog_is_expired(const struct device *dev)
{
    struct gos_watchdog_data *data = dev->data;

    if (!data->initialized) {
        return false;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    bool expired = (k_uptime_get_32() - data->last_feed_time) > data->timeout_ms;
    k_mutex_unlock(&data->mutex);

    return expired;
}

int gos_watchdog_install_callback(const struct device *dev, void (*callback)(void))
{
    /* Watchdog callback not supported in this implementation */
    return -ENOTSUP;
}

#define DT_DRV_COMPAT gos_watchdog

static struct gos_watchdog_data watchdog_data_0 = {
    .config = {
        .timeout_ms = DT_INST_PROP(0, timeout_ms),
        .window_mode = DT_INST_PROP(0, window_mode),
        .window_ms = DT_INST_PROP(0, window_ms),
    },
};

DEVICE_DT_INST_DEFINE(0, gos_watchdog_init, NULL,
                      &watchdog_data_0, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
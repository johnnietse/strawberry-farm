#include "power_mgmt.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/pm/device.h>
#include <zephyr/pm/device_runtime.h>
#include <zephyr/pm/policy.h>

LOG_MODULE_REGISTER(power_mgmt, LOG_LEVEL_INF);

static int power_mgmt_init(const struct device *dev)
{
    const struct gos_power_mgmt_config *config = dev->config;
    struct gos_power_mgmt_data *data = dev->data;
    int err;

    k_mutex_init(&data->mutex);

    if (config->bat_en_gpio.port) {
        if (!gpio_is_ready_dt(&config->bat_en_gpio)) {
            LOG_WRN("BAT_EN GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->bat_en_gpio, GPIO_OUTPUT_ACTIVE);
            if (err) {
                LOG_ERR("Failed to configure BAT_EN GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->vbus_sense_gpio.port) {
        if (!gpio_is_ready_dt(&config->vbus_sense_gpio)) {
            LOG_WRN("VBUS_SENSE GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->vbus_sense_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure VBUS_SENSE GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->bat_chg_gpio.port) {
        if (!gpio_is_ready_dt(&config->bat_chg_gpio)) {
            LOG_WRN("BAT_CHG GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->bat_chg_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure BAT_CHG GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->pg_gpio.port) {
        if (!gpio_is_ready_dt(&config->pg_gpio)) {
            LOG_WRN("PG GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->pg_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure PG GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->stat_gpio.port) {
        if (!gpio_is_ready_dt(&config->stat_gpio)) {
            LOG_WRN("STAT GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->stat_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure STAT GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->ce_gpio.port) {
        if (!gpio_is_ready_dt(&config->ce_gpio)) {
            LOG_WRN("CE GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->ce_gpio, GPIO_OUTPUT_INACTIVE);
            if (err) {
                LOG_ERR("Failed to configure CE GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->ts_gpio.port) {
        if (!gpio_is_ready_dt(&config->ts_gpio)) {
            LOG_WRN("TS GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->ts_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure TS GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->bat_en_gpio.port) {
        if (!gpio_is_ready_dt(&config->bat_en_gpio)) {
            LOG_WRN("BAT_EN GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->bat_en_gpio, GPIO_OUTPUT_ACTIVE);
            if (err) {
                LOG_ERR("Failed to configure BAT_EN GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->vbus_sense_gpio.port) {
        if (!gpio_is_ready_dt(&config->vbus_sense_gpio)) {
            LOG_WRN("VBUS_SENSE GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->vbus_sense_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure VBUS_SENSE GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->bat_chg_gpio.port) {
        if (!gpio_is_ready_dt(&config->bat_chg_gpio)) {
            LOG_WRN("BAT_CHG GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->bat_chg_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure BAT_CHG GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->pg_gpio.port) {
        if (!gpio_is_ready_dt(&config->pg_gpio)) {
            LOG_WRN("PG GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->pg_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure PG GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->stat_gpio.port) {
        if (!gpio_is_ready_dt(&config->stat_gpio)) {
            LOG_WRN("STAT GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->stat_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure STAT GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->ce_gpio.port) {
        if (!gpio_is_ready_dt(&config->ce_gpio)) {
            LOG_WRN("CE GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->ce_gpio, GPIO_OUTPUT_INACTIVE);
            if (err) {
                LOG_ERR("Failed to configure CE GPIO: %d", err);
                return err;
            }
        }
    }

    if (config->ts_gpio.port) {
        if (!gpio_is_ready_dt(&config->ts_gpio)) {
            LOG_WRN("TS GPIO not ready");
        } else {
            err = gpio_pin_configure_dt(&config->ts_gpio, GPIO_INPUT);
            if (err) {
                LOG_ERR("Failed to configure TS GPIO: %d", err);
                return err;
            }
        }
    }

    data->current_state = GOS_POWER_STATE_ACTIVE_FULL;
    data->target_state = GOS_POWER_STATE_ACTIVE_FULL;
    data->pm_enabled = true;
    data->timestamp = k_uptime_get_32();

    LOG_INF("Power management initialized");
    return 0;
}

int gos_power_mgmt_set_state(const struct device *dev, enum gos_power_state state)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled) {
        return -ENODEV;
    }

    if (state >= GOS_POWER_STATE_ACTIVE_FULL) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);

    data->target_state = state;
    data->current_state = state;
    data->timestamp = k_uptime_get_32();

    k_mutex_unlock(&data->mutex);

    LOG_INF("Power state changed to %d", state);
    return 0;
}

int gos_power_mgmt_get_state(const struct device *dev, enum gos_power_state *state)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled) {
        return -ENODEV;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    *state = data->current_state;
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_power_mgmt_sleep(const struct device *dev, uint32_t duration_ms, uint32_t wake_sources)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled) {
        return -ENODEV;
    }

    if (duration_ms == 0) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);

    data->wake_sources = wake_sources;
    data->sleep_duration_ms = duration_ms;
    data->timestamp = k_uptime_get_32();

    k_mutex_unlock(&data->mutex);

    /* Configure wake sources */
    if (wake_sources & GOS_WAKE_RTC) {
        /* Configure RTC alarm */
    }

    if (wake_sources & GOS_WAKE_GPIO) {
        /* Configure GPIO wake sources */
    }

    if (wake_sources & GOS_WAKE_RADIO) {
        /* Configure radio wake */
    }

    if (wake_sources & GOS_WAKE_ACCEL) {
        /* Configure accelerometer wake */
    }

    if (wake_sources & GOS_WAKE_USB) {
        /* Configure USB wake */
    }

    if (wake_sources & GOS_WAKE_WDT) {
        /* Configure watchdog wake */
    }

    /* Enter sleep state */
    int err = pm_policy_state_lock_get(PM_STATE_SOFT_OFF, PM_ALL_SUBSTATES);
    if (err) {
        LOG_ERR("Failed to lock PM state: %d", err);
        return err;
    }

    k_msleep(duration_ms);

    pm_policy_state_lock_put(PM_STATE_SOFT_OFF, PM_ALL_SUBSTATES);

    data->total_sleep_ms += duration_ms;
    data->timestamp = k_uptime_get_32();

    return 0;
}

int gos_power_mgmt_wake(const struct device *dev, enum gos_power_wake_source source)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled) {
        return -ENODEV;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    data->wake_sources |= source;
    data->timestamp = k_uptime_get_32();
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_power_mgmt_get_stats(const struct device *dev, uint32_t *total_sleep_ms, uint32_t *total_active_ms)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled) {
        return -ENODEV;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    if (total_sleep_ms) *total_sleep_ms = data->total_sleep_ms;
    if (total_active_ms) *total_active_ms = data->total_active_ms;
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_power_mgmt_register_wake_source(const struct device *dev, enum gos_power_wake_source source, struct gpio_dt_spec *gpio)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled) {
        return -ENODEV;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    data->wake_sources |= source;
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_power_mgmt_unregister_wake_source(const struct device *dev, enum gos_power_wake_source source)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled) {
        return -ENODEV;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    data->wake_sources &= ~source;
    k_mutex_unlock(&data->mutex);

    return 0;
}

bool gos_power_mgmt_is_vbus_present(const struct device *dev)
{
    const struct gos_power_mgmt_config *config = dev->config;
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled || !config->vbus_sense_gpio.port) {
        return false;
    }

    return gpio_pin_get_dt(&config->vbus_sense_gpio) == 1;
}

bool gos_power_mgmt_is_charging(const struct device *dev)
{
    const struct gos_power_mgmt_config *config = dev->config;
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled || !config->stat_gpio.port) {
        return false;
    }

    return gpio_pin_get_dt(&config->stat_gpio) == 0; /* Active low */
}

bool gos_power_mgmt_is_battery_low(const struct device *dev)
{
    struct gos_power_mgmt_data *data = dev->data;
    if (!data->pm_enabled) {
        return false;
    }

    /* This would typically check battery ADC */
    return false;
}

int gos_power_mgmt_get_battery_percent(const struct device *dev, uint8_t *percent)
{
    struct gos_power_mgmt_data *data = dev->data;

    if (!data->pm_enabled || !percent) {
        return -EINVAL;
    }

    /* This would typically read from battery ADC */
    *percent = 0;
    return 0;
}

#define DT_DRV_COMPAT gos_power_mgmt

static struct gos_power_mgmt_data power_mgmt_data_0 = {
    .config = {
        .bat_en_gpio = GPIO_DT_SPEC_INST_GET_OR(0, bat_en_gpios, {0}),
        .vbus_sense_gpio = GPIO_DT_SPEC_INST_GET_OR(0, vbus_sense_gpios, {0}),
        .bat_chg_gpio = GPIO_DT_SPEC_INST_GET_OR(0, bat_chg_gpios, {0}),
        .pg_gpio = GPIO_DT_SPEC_INST_GET_OR(0, pg_gpios, {0}),
        .stat_gpio = GPIO_DT_SPEC_INST_GET_OR(0, stat_gpios, {0}),
        .ce_gpio = GPIO_DT_SPEC_INST_GET_OR(0, ce_gpios, {0}),
        .ts_gpio = GPIO_DT_SPEC_INST_GET_OR(0, ts_gpios, {0}),
        .bat_en_gpio = GPIO_DT_SPEC_INST_GET_OR(0, bat_en_gpios, {0}),
        .vbus_sense_gpio = GPIO_DT_SPEC_INST_GET_OR(0, vbus_sense_gpios, {0}),
        .bat_chg_gpio = GPIO_DT_SPEC_INST_GET_OR(0, bat_chg_gpios, {0}),
        .pg_gpio = GPIO_DT_SPEC_INST_GET_OR(0, pg_gpios, {0}),
        .stat_gpio = GPIO_DT_SPEC_INST_GET_OR(0, stat_gpios, {0}),
        .ce_gpio = GPIO_DT_SPEC_INST_GET_OR(0, ce_gpios, {0}),
        .ts_gpio = GPIO_DT_SPEC_INST_GET_OR(0, ts_gpios, {0}),
    },
};

DEVICE_DT_INST_DEFINE(0, power_mgmt_init, NULL,
                      &power_mgmt_data_0, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
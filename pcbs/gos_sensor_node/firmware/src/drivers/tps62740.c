#include "tps62740.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

LOG_MODULE_REGISTER(tps62740, LOG_LEVEL_INF);

static int tps62740_init(const struct device *dev)
{
    const struct gos_tps62740_config *config = dev->config;
    struct gos_tps62740_data *data = dev->data;
    int err;

    if (!device_is_ready(config->en_gpio.port)) {
        LOG_ERR("EN GPIO device not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->vsel0_gpio.port)) {
        LOG_ERR("VSEL0 GPIO device not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->vsel1_gpio.port)) {
        LOG_ERR("VSEL1 GPIO device not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->pg_gpio.port)) {
        LOG_ERR("PG GPIO device not ready");
        return -ENODEV;
    }

    err = gpio_pin_configure_dt(&config->en_gpio, GPIO_OUTPUT_ACTIVE);
    if (err) {
        LOG_ERR("Failed to configure EN GPIO: %d", err);
        return err;
    }

    err = gpio_pin_configure_dt(&config->vsel0_gpio, GPIO_OUTPUT_INACTIVE);
    if (err) {
        LOG_ERR("Failed to configure VSEL0 GPIO: %d", err);
        return err;
    }

    err = gpio_pin_configure_dt(&config->vsel1_gpio, GPIO_OUTPUT_INACTIVE);
    if (err) {
        LOG_ERR("Failed to configure VSEL1 GPIO: %d", err);
        return err;
    }

    err = gpio_pin_configure_dt(&config->pg_gpio, GPIO_INPUT);
    if (err) {
        LOG_ERR("Failed to configure PG GPIO: %d", err);
        return err;
    }

    data->en_state = true;
    data->vsel0_state = false;
    data->vsel1_state = false;
    data->valid = true;
    data->timestamp = k_uptime_get_32();

    LOG_INF("TPS62740 initialized (EN=1, VSEL0=0, VSEL1=0 -> 3.3V)");
    return 0;
}

int gos_tps62740_get_pg_status(const struct device *dev, bool *pg)
{
    const struct gos_tps62740_config *config = dev->config;
    struct gos_tps62740_data *data = dev->data;

    if (!data->valid) {
        return -ENODEV;
    }

    int val = gpio_pin_get_dt(&config->pg_gpio);
    if (val < 0) {
        return -EIO;
    }

    data->pg_status = (val == 0); /* PG is active low */
    data->timestamp = k_uptime_get_32();

    if (pg) {
        *pg = data->pg_status;
    }

    return 0;
}

int gos_tps62740_set_enable(const struct device *dev, bool enable)
{
    const struct gos_tps62740_config *config = dev->config;
    struct gos_tps62740_data *data = dev->data;

    if (!data->valid) {
        return -ENODEV;
    }

    int err = gpio_pin_set_dt(&config->en_gpio, enable ? 1 : 0);
    if (err) {
        return err;
    }

    data->en_state = enable;
    data->timestamp = k_uptime_get_32();
    return 0;
}

int gos_tps62740_set_vsel(const struct device *dev, bool vsel0, bool vsel1)
{
    const struct gos_tps62740_config *config = dev->config;
    struct gos_tps62740_data *data = dev->data;
    int err;

    if (!data->valid) {
        return -ENODEV;
    }

    err = gpio_pin_set_dt(&config->vsel0_gpio, vsel0 ? 1 : 0);
    if (err) {
        return err;
    }

    err = gpio_pin_set_dt(&config->vsel1_gpio, vsel1 ? 1 : 0);
    if (err) {
        return err;
    }

    data->vsel0_state = vsel0;
    data->vsel1_state = vsel1;
    data->timestamp = k_uptime_get_32();
    return 0;
}

int gos_tps62740_get_vsel(const struct device *dev, bool *vsel0, bool *vsel1)
{
    struct gos_tps62740_data *data = dev->data;

    if (!data->valid) {
        return -ENODEV;
    }

    if (vsel0) *vsel0 = data->vsel0_state;
    if (vsel1) *vsel1 = data->vsel1_state;
    return 0;
}

bool gos_tps62740_is_pg(const struct device *dev)
{
    struct gos_tps62740_data *data = dev->data;
    if (!data->valid) {
        return false;
    }
    return data->pg_status;
}

bool gos_tps62740_is_enabled(const struct device *dev)
{
    struct gos_tps62740_data *data = dev->data;
    if (!data->valid) {
        return false;
    }
    return data->en_state;
}

#define DT_DRV_COMPAT ti_tps62740

static struct gos_tps62740_data tps62740_data_0 = {
    .config = {
        .en_gpio = GPIO_DT_SPEC_INST_GET(0, en_gpios),
        .vsel0_gpio = GPIO_DT_SPEC_INST_GET(0, vsel0_gpios),
        .vsel1_gpio = GPIO_DT_SPEC_INST_GET(0, vsel1_gpios),
        .pg_gpio = GPIO_DT_SPEC_INST_GET(0, pg_gpios),
    },
};

DEVICE_DT_INST_DEFINE(0, tps62740_init, NULL,
                      NULL, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
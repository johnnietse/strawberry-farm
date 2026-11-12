#include "dw01a.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

LOG_MODULE_REGISTER(dw01a, LOG_LEVEL_INF);

static int dw01a_init(const struct device *dev)
{
    const struct gos_dw01a_config *config = dev->config;
    struct gos_dw01a_data *data = dev->data;
    int err;

    if (!device_is_ready(config->od_gpio.port)) {
        LOG_ERR("OD GPIO device not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->oc_gpio.port)) {
        LOG_ERR("OC GPIO device not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->cs_gpio.port)) {
        LOG_ERR("CS GPIO device not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->vcc_gpio.port)) {
        LOG_ERR("VCC GPIO device not ready");
        return -ENODEV;
    }

    err = gpio_pin_configure_dt(&config->od_gpio, GPIO_INPUT);
    if (err) {
        LOG_ERR("Failed to configure OD GPIO: %d", err);
        return err;
    }

    err = gpio_pin_configure_dt(&config->oc_gpio, GPIO_INPUT);
    if (err) {
        LOG_ERR("Failed to configure OC GPIO: %d", err);
        return err;
    }

    err = gpio_pin_configure_dt(&config->cs_gpio, GPIO_INPUT);
    if (err) {
        LOG_ERR("Failed to configure CS GPIO: %d", err);
        return err;
    }

    err = gpio_pin_configure_dt(&config->vcc_gpio, GPIO_INPUT);
    if (err) {
        LOG_ERR("Failed to configure VCC GPIO: %d", err);
        return err;
    }

    if (config->gnd_gpio.port) {
        err = gpio_pin_configure_dt(&config->gnd_gpio, GPIO_INPUT);
        if (err) {
            LOG_ERR("Failed to configure GND GPIO: %d", err);
            return err;
        }
    }

    data->valid = true;
    data->timestamp = k_uptime_get_32();

    LOG_INF("DW01A protection IC initialized");
    return 0;
}

int gos_dw01a_read_status(const struct device *dev, bool *od, bool *oc, bool *cs, bool *vcc_ok)
{
    const struct gos_dw01a_config *config = dev->config;
    struct gos_dw01a_data *data = dev->data;

    if (!data->valid) {
        return -ENODEV;
    }

    int od_val = gpio_pin_get_dt(&config->od_gpio);
    int oc_val = gpio_pin_get_dt(&config->oc_gpio);
    int cs_val = gpio_pin_get_dt(&config->cs_gpio);
    int vcc_val = gpio_pin_get_dt(&config->vcc_gpio);

    if (od_val < 0 || oc_val < 0 || cs_val < 0 || vcc_val < 0) {
        return -EIO;
    }

    data->od_status = (od_val == 0);  /* Active low */
    data->oc_status = (oc_val == 0);  /* Active low */
    data->cs_status = (cs_val == 1);  /* Active high */
    data->vcc_ok = (vcc_val == 1);
    data->timestamp = k_uptime_get_32();

    if (od) *od = data->od_status;
    if (oc) *oc = data->oc_status;
    if (cs) *cs = data->cs_status;
    if (vcc_ok) *vcc_ok = data->vcc_ok;

    return 0;
}

bool gos_dw01a_is_overdischarged(const struct device *dev)
{
    struct gos_dw01a_data *data = dev->data;
    if (!data->valid) {
        return false;
    }
    return data->od_status;
}

bool gos_dw01a_is_overcurrent(const struct device *dev)
{
    struct gos_dw01a_data *data = dev->data;
    if (!data->valid) {
        return false;
    }
    return data->oc_status;
}

bool gos_dw01a_is_vcc_ok(const struct device *dev)
{
    struct gos_dw01a_data *data = dev->data;
    if (!data->valid) {
        return false;
    }
    return data->vcc_ok;
}

int gos_dw01a_get_status(const struct device *dev, uint8_t *status)
{
    struct gos_dw01a_data *data = dev->data;
    if (!data->valid) {
        return -ENODEV;
    }

    uint8_t status = 0;
    if (data->od_status) status |= BIT(0);
    if (data->oc_status) status |= BIT(1);
    if (data->cs_status) status |= BIT(2);
    if (data->vcc_ok) status |= BIT(3);

    *status = status;
    return 0;
}

#define DT_DRV_COMPAT ablic_dw01a

static struct gos_dw01a_data dw01a_data_0 = {
    .config = {
        .od_gpio = GPIO_DT_SPEC_INST_GET(0, od_gpios),
        .oc_gpio = GPIO_DT_SPEC_INST_GET(0, oc_gpios),
        .cs_gpio = GPIO_DT_SPEC_INST_GET(0, cs_gpios),
        .vcc_gpio = GPIO_DT_SPEC_INST_GET(0, vcc_gpios),
        .gnd_gpio = GPIO_DT_SPEC_INST_GET_OR(0, gnd_gpios, {0}),
        .ov_threshold_mv = DT_INST_PROP_OR(0, ov_threshold_mv, 4250),
        .uv_threshold_mv = DT_INST_PROP_OR(0, uv_threshold_mv, 2400),
        .oc_threshold_mv = DT_INST_PROP_OR(0, oc_threshold_mv, 150),
        .oc_delay_ms = DT_INST_PROP_OR(0, oc_delay_ms, 100),
    },
};

DEVICE_DT_INST_DEFINE(0, dw01a_init, NULL,
                      NULL, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
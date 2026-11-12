#include "al8860.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

LOG_MODULE_REGISTER(al8860, LOG_LEVEL_INF);

static int al8860_init(const struct device *dev)
{
    const struct gos_al8860_config *config = dev->config;
    struct gos_al8860_data *data = dev->data;
    int err;

    k_mutex_init(&data->mutex);

    if (!device_is_ready(config->pwm.dev)) {
        LOG_ERR("PWM device not ready");
        return -ENODEV;
    }

    if (config->fb_gpio.port) {
        if (!gpio_is_ready_dt(&config->fb_gpio)) {
            LOG_WRN("FB GPIO not ready");
        } else {
            gpio_pin_configure_dt(&config->fb_gpio, GPIO_INPUT);
        }
    }

    if (config->en_gpio.port) {
        if (!gpio_is_ready_dt(&config->en_gpio)) {
            LOG_WRN("EN GPIO not ready");
        } else {
            gpio_pin_configure_dt(&config->en_gpio, GPIO_OUTPUT_INACTIVE);
        }
    }

    if (!pwm_is_ready_dt(&config->pwm)) {
        LOG_ERR("PWM device not ready");
        return -ENODEV;
    }

    int err = pwm_set_dt(&config->pwm, config->pwm_frequency_hz, 0);
    if (err) {
        LOG_ERR("Failed to set PWM: %d", err);
        return err;
    }

    data->current_ma = config->current_ma;
    data->pwm_duty_cycle = 0;
    data->enabled = false;
    data->initialized = true;

    LOG_INF("AL8860 initialized (current=%d mA, freq=%d Hz)",
            config->current_ma, config->pwm_frequency_hz);

    return 0;
}

int gos_al8860_set_current(const struct device *dev, uint32_t current_ma)
{
    struct gos_al8860_data *data = dev->data;
    const struct gos_al8860_config *config = dev->config;

    if (!data->initialized) {
        return -ENODEV;
    }

    if (current_ma > 1500) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);

    data->current_ma = current_ma;

    /* AL8860: I_LED = V_FB / R_SENSE, V_FB = 0.1V typical
     * Duty cycle = I_LED * R_SENSE / V_FB
     * With R_SENSE = 0.33 ohm, V_FB = 0.1V:
     * Duty = I_LED * 0.33 / 0.1 = I_LED * 3.3
     * For 300mA: Duty = 300 * 3.3 = 990 (out of 10000) = 9.9%
     */
    uint32_t duty_ns = (current_ma * 3300) / 1000; /* 0.1V / 0.33ohm = 3.3 mA per % duty */

    int err = pwm_set_dt(&config->pwm, config->pwm_frequency_hz, duty_ns);
    if (err == 0) {
        data->current_ma = current_ma;
        data->pwm_duty_cycle = duty_ns;
    }

    k_mutex_unlock(&data->mutex);
    return err;
}

int gos_al8860_set_brightness(const struct device *dev, uint8_t percent)
{
    struct gos_al8860_data *data = dev->data;
    const struct gos_al8860_config *config = dev->config;

    if (!data->initialized) {
        return -ENODEV;
    }

    if (percent > 100) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);

    uint32_t current_ma = (config->current_ma * percent) / 100;
    uint32_t duty_ns = (current_ma * 3300) / 1000;

    int err = pwm_set_dt(&config->pwm, config->pwm_frequency_hz, duty_ns);
    if (err == 0) {
        data->current_ma = current_ma;
        data->pwm_duty_cycle = duty_ns;
    }

    k_mutex_unlock(&data->mutex);
    return err;
}

int gos_al8860_enable(const struct device *dev, bool enable)
{
    struct gos_al8860_data *data = dev->data;
    const struct gos_al8860_config *config = dev->config;

    if (!data->initialized) {
        return -ENODEV;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);

    int err = 0;
    if (enable && !data->enabled) {
        err = pwm_set_dt(&config->pwm, config->pwm_frequency_hz, data->pwm_duty_cycle);
        if (err == 0) {
            data->enabled = true;
        }
    } else if (!enable && data->enabled) {
        err = pwm_set_dt(&config->pwm, config->pwm_frequency_hz, 0);
        if (err == 0) {
            data->enabled = false;
        }
    }

    k_mutex_unlock(&data->mutex);
    return err;
}

bool gos_al8860_is_enabled(const struct device *dev)
{
    struct gos_al8860_data *data = dev->data;
    return data->initialized && data->enabled;
}

int gos_al8860_get_current(const struct device *dev, uint32_t *current_ma)
{
    struct gos_al8860_data *data = dev->data;

    if (!data->initialized || !current_ma) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);
    *current_ma = data->current_ma;
    k_mutex_unlock(&data->mutex);

    return 0;
}

int gos_al8860_set_pwm_frequency(const struct device *dev, uint32_t freq_hz)
{
    struct gos_al8860_data *data = dev->data;
    const struct gos_al8860_config *config = dev->config;

    if (!data->initialized) {
        return -ENODEV;
    }

    if (freq_hz < 1000 || freq_hz > 1000000) {
        return -EINVAL;
    }

    k_mutex_lock(&data->mutex, K_FOREVER);

    int err = pwm_set_dt(&config->pwm, freq_hz, data->pwm_duty_cycle);
    if (err == 0) {
        /* Update config */
        ((struct gos_al8860_config *)config)->pwm_frequency_hz = freq_hz;
    }

    k_mutex_unlock(&data->mutex);
    return err;
}

#define DT_DRV_COMPAT diodes_al8860

static struct gos_al8860_data al8860_data_0 = {
    .config = {
        .pwm = PWM_DT_SPEC_INST_GET(0),
        .fb_gpio = GPIO_DT_SPEC_INST_GET_OR(0, fb_gpios, {0}),
        .en_gpio = GPIO_DT_SPEC_INST_GET_OR(0, en_gpios, {0}),
        .current_ma = DT_INST_PROP(0, current_ma),
        .pwm_frequency_hz = DT_INST_PROP(0, pwm_frequency),
    },
};

DEVICE_DT_INST_DEFINE(0, al8860_init, NULL,
                      &al8860_data_0, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
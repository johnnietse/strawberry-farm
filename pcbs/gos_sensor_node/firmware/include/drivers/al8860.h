#ifndef GOS_AL8860_H
#define GOS_AL8860_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/gpio.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

struct gos_al8860_config {
    struct pwm_dt_spec pwm;
    struct gpio_dt_spec fb_gpio;
    struct gpio_dt_spec en_gpio;
    uint32_t current_ma;
    uint32_t pwm_frequency_hz;
};

struct gos_al8860_data {
    struct k_mutex mutex;
    uint32_t current_ma;
    uint32_t pwm_duty_cycle;
    bool enabled;
    bool initialized;
};

int gos_al8860_init(const struct device *dev);
int gos_al8860_set_current(const struct device *dev, uint32_t current_ma);
int gos_al8860_set_brightness(const struct device *dev, uint8_t percent);
int gos_al8860_enable(const struct device *dev, bool enable);
bool gos_al8860_is_enabled(const struct device *dev);
int gos_al8860_get_current(const struct device *dev, uint32_t *current_ma);
int gos_al8860_set_pwm_frequency(const struct device *dev, uint32_t freq_hz);

#ifdef __cplusplus
}
#endif

#endif /* GOS_AL8860_H */
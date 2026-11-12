#ifndef GOS_TPS62740_H
#define GOS_TPS62740_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

struct gos_tps62740_data {
    bool pg_status;
    bool vsel0_state;
    bool vsel1_state;
    bool en_state;
    uint32_t timestamp;
    bool valid;
};

struct gos_tps62740_config {
    struct gpio_dt_spec en_gpio;
    struct gpio_dt_spec vsel0_gpio;
    struct gpio_dt_spec vsel1_gpio;
    struct gpio_dt_spec pg_gpio;
};

int gos_tps62740_init(const struct device *dev);
int gos_tps62740_get_pg_status(const struct device *dev, bool *pg);
int gos_tps62740_set_enable(const struct device *dev, bool enable);
int gos_tps62740_set_vsel(const struct device *dev, bool vsel0, bool vsel1);
int gos_tps62740_get_vsel(const struct device *dev, bool *vsel0, bool *vsel1);
bool gos_tps62740_is_pg(const struct device *dev);
bool gos_tps62740_is_enabled(const struct device *dev);

#ifdef __cplusplus
}
#endif

#endif /* GOS_TPS62740_H */
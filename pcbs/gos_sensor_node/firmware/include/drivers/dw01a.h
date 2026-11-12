#ifndef GOS_DW01A_H
#define GOS_DW01A_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

struct gos_dw01a_data {
    bool od_status;      /* Over-discharge detection */
    bool oc_status;      /* Over-current detection */
    bool cs_status;      /* Current sense status */
    bool vcc_ok;         /* VCC above threshold */
    uint32_t timestamp;
    bool valid;
};

struct gos_dw01a_config {
    struct gpio_dt_spec od_gpio;   /* Over-discharge output */
    struct gpio_dt_spec oc_gpio;   /* Over-current output */
    struct gpio_dt_spec cs_gpio;   /* Current sense input */
    struct gpio_dt_spec vcc_gpio;  /* VCC monitor */
    struct gpio_dt_spec gnd_gpio;  /* GND pin (for reference) */
    uint32_t ov_threshold_mv;      /* Over-voltage threshold (mV) */
    uint32_t uv_threshold_mv;      /* Under-voltage threshold (mV) */
    uint32_t oc_threshold_mv;      /* Over-current threshold (mV) */
    uint32_t oc_delay_ms;          /* Over-current delay (ms) */
};

int gos_dw01a_init(const struct device *dev);
int gos_dw01a_read_status(const struct device *dev, bool *od, bool *oc, bool *cs, bool *vcc_ok);
bool gos_dw01a_is_overdischarged(const struct device *dev);
bool gos_dw01a_is_overcurrent(const struct device *dev);
bool gos_dw01a_is_vcc_ok(const struct device *dev);
int gos_dw01a_get_status(const struct device *dev, uint8_t *status);

#ifdef __cplusplus
}
#endif

#endif /* GOS_DW01A_H */
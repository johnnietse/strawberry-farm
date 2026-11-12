#ifndef GOS_L76K_H
#define GOS_L76K_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

struct gos_l76k_data {
    double latitude;
    double longitude;
    double altitude;
    double speed;
    double course;
    uint8_t satellites;
    uint8_t fix_quality;
    uint32_t timestamp;
    bool valid;
    bool pps_sync;
};

struct gos_l76k_config {
    struct uart_dt_spec uart;
    struct gpio_dt_spec pps_gpio;
    uint32_t baudrate;
};

int gos_l76k_init(const struct device *dev);
int gos_l76k_read_position(const struct device *dev, double *lat, double *lon, double *alt);
int gos_l76k_read_velocity(const struct device *dev, double *speed, double *course);
int gos_l76k_read_satellites(const struct device *dev, uint8_t *count, uint8_t *quality);
bool gos_l76k_has_fix(const struct device *dev);
bool gos_l76k_has_pps_sync(const struct device *dev);
int gos_l76k_get_timestamp(const struct device *dev, uint32_t *timestamp);
int gos_l76k_set_baudrate(const struct device *dev, uint32_t baud);
int gos_l76k_set_update_rate(const struct device *dev, uint16_t hz);
int gos_l76k_enable_pps(const struct device *dev, bool enable);

#ifdef __cplusplus
}
#endif

#endif /* GOS_L76K_H */
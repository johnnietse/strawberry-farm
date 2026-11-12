#ifndef GOS_POWER_MGMT_H
#define GOS_POWER_MGMT_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

enum gos_power_state {
    GOS_POWER_STATE_OFF = 0,
    GOS_POWER_STATE_SYSTEM_ON_LP = 1,   /* SYSTEM_ON_LP: ~2.5µA, RTC + RAM retention */
    GOS_POWER_STATE_SYSTEM_ON_CL = 2,   /* SYSTEM_ON_CL: ~15µA, constant latency */
    GOS_POWER_STATE_ACTIVE_RADIO = 3,   /* ACTIVE_RADIO: ~8.5mA, radio active */
    GOS_POWER_STATE_ACTIVE_SENSORS = 4, /* ACTIVE_SENSORS: ~5mA, sensors active */
    GOS_POWER_STATE_ACTIVE_FULL = 5,    /* ACTIVE_FULL: ~15mA, all active */
};

enum gos_power_wake_source {
    GOS_WAKE_NONE = 0,
    GOS_WAKE_RTC = BIT(0),
    GOS_WAKE_GPIO = BIT(1),
    GOS_WAKE_RADIO = BIT(2),
    GOS_WAKE_ACCEL = BIT(3),
    GOS_WAKE_USB = BIT(4),
    GOS_WAKE_WDT = BIT(5),
};

struct gos_power_mgmt_config {
    struct gpio_dt_spec bat_en_gpio;
    struct gpio_dt_spec vbus_sense_gpio;
    struct gpio_dt_spec bat_chg_gpio;
    struct gpio_dt_spec pg_gpio;
    struct gpio_dt_spec stat_gpio;
    struct gpio_dt_spec ce_gpio;
    struct gpio_dt_spec ts_gpio;
};

struct gos_power_mgmt_data {
    enum gos_power_state current_state;
    enum gos_power_state target_state;
    uint32_t wake_sources;
    uint32_t sleep_duration_ms;
    uint32_t active_duration_ms;
    uint32_t total_sleep_ms;
    uint32_t total_active_ms;
    uint32_t timestamp;
    bool pm_enabled;
    struct k_mutex mutex;
};

int gos_power_mgmt_init(const struct device *dev);
int gos_power_mgmt_set_state(const struct device *dev, enum gos_power_state state);
int gos_power_mgmt_get_state(const struct device *dev, enum gos_power_state *state);
int gos_power_mgmt_sleep(const struct device *dev, uint32_t duration_ms, uint32_t wake_sources);
int gos_power_mgmt_wake(const struct device *dev, enum gos_power_wake_source source);
int gos_power_mgmt_get_stats(const struct device *dev, uint32_t *total_sleep_ms, uint32_t *total_active_ms);
int gos_power_mgmt_register_wake_source(const struct device *dev, enum gos_power_wake_source source, struct gpio_dt_spec *gpio);
int gos_power_mgmt_unregister_wake_source(const struct device *dev, enum gos_power_wake_source source);
bool gos_power_mgmt_is_vbus_present(const struct device *dev);
bool gos_power_mgmt_is_charging(const struct device *dev);
bool gos_power_mgmt_is_battery_low(const struct device *dev);
int gos_power_mgmt_get_battery_percent(const struct device *dev, uint8_t *percent);

#ifdef __cplusplus
}
#endif

#endif /* GOS_POWER_MGMT_H */
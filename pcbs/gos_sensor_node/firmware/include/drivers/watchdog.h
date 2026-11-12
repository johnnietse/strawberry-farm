#ifndef GOS_WATCHDOG_H
#define GOS_WATCHDOG_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

struct gos_watchdog_config {
    uint32_t timeout_ms;
    bool window_mode;
    uint32_t window_ms;
};

struct gos_watchdog_data {
    struct k_mutex mutex;
    bool initialized;
    uint32_t timeout_ms;
    bool window_mode;
    uint32_t window_ms;
    uint32_t last_feed_time;
    uint32_t feed_count;
    uint32_t reset_count;
};

int gos_watchdog_init(const struct device *dev);
int gos_watchdog_feed(const struct device *dev);
int gos_watchdog_set_timeout(const struct device *dev, uint32_t timeout_ms);
int gos_watchdog_set_window(const struct device *dev, uint32_t window_ms);
int gos_watchdog_get_timeout(const struct device *dev, uint32_t *timeout_ms);
int gos_watchdog_get_window(const struct device *dev, uint32_t *window_ms);
int gos_watchdog_get_stats(const struct device *dev, uint32_t *feed_count, uint32_t *reset_count);
bool gos_watchdog_is_expired(const struct device *dev);
int gos_watchdog_install_callback(const struct device *dev, void (*callback)(void));

#ifdef __cplusplus
}
#endif

#endif /* GOS_WATCHDOG_H */
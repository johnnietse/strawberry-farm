#ifndef GOS_MAIN_H
#define GOS_MAIN_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

struct gos_sensor_data {
    float temp_c;
    float humidity_pct;
    float pressure_hpa;
    float lux;
    int16_t battery_mv;
    uint32_t timestamp;
};

struct gos_system_config {
    uint32_t sensor_interval_ms;
    uint32_t coap_interval_ms;
    uint32_t log_interval_ms;
    uint8_t spectral_blue_pct;
    uint8_t spectral_red_pct;
    int8_t tx_power_dbm;
    uint8_t spreading_factor;
    uint8_t bandwidth;
    uint8_t coding_rate;
};

extern struct gos_sensor_data g_sensor_data;
extern struct gos_system_config g_system_config;
extern struct k_mutex sensor_data_mutex;

int gos_system_init(void);
int gos_sensor_thread_start(void);
int gos_radio_thread_start(void);
int gos_power_thread_start(void);
int gos_led_thread_start(void);

void gos_sensor_data_lock(void);
void gos_sensor_data_unlock(void);

#ifdef __cplusplus
}
#endif

#endif /* GOS_MAIN_H */
#ifndef GOS_MAIN_H
#define GOS_MAIN_H

#include <stdbool.h>
#include <stdint.h>

#include <zephyr/sys/util.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Bits of gos_sensor_data.valid: set when that reading succeeded */
#define GOS_VALID_CLIMATE BIT(0)
#define GOS_VALID_LIGHT   BIT(1)
#define GOS_VALID_BATTERY BIT(2)
#define GOS_VALID_CHARGER BIT(3)

struct gos_sensor_data {
	int temp_mc;        /* air temperature, 0.001 degC */
	int humidity_mpct;  /* relative humidity, 0.001 % */
	int light_lux;      /* TSL2591 combined reading, lux */
	int battery_mv;     /* cell voltage at VBAT, mV */
	bool usb_power;     /* charger reports good USB power */
	bool charging;      /* charger reports charge in progress */
	uint8_t valid;      /* GOS_VALID_* */
	int64_t uptime_ms;
};

/* Set the two LED-board PWM channels, 0 to 100 % each. */
int gos_set_spectral_mix(uint8_t blue_pct, uint8_t red_pct);

#ifdef __cplusplus
}
#endif

#endif /* GOS_MAIN_H */

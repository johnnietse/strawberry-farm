#ifndef GOS_BATTERY_ADC_H
#define GOS_BATTERY_ADC_H

#include <zephyr/kernel.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ADC Channels */
enum gos_battery_adc_channel {
    GOS_BATTERY_ADC_VBATT = 0,  /* Battery voltage via divider */
    GOS_BATTERY_ADC_VBUS,       /* USB VBUS voltage */
    GOS_BATTERY_ADC_VSYS,       /* System voltage (VSYS) */
    GOS_BATTERY_ADC_CHANNELS
};

/* Battery ADC data structure */
struct gos_battery_adc_data {
    int16_t vbatt_mv;      /* Battery voltage in mV */
    int16_t vbus_mv;       /* VBUS voltage in mV */
    int16_t vsys_mv;       /* System voltage in mV */
    uint32_t timestamp;    /* Timestamp of reading (ms) */
    bool valid;            /* Data validity flag */
};

/* Divider ratios (numerator/denominator) */
#define VBATT_DIVIDER_NUM  1
#define VBATT_DIVIDER_DEN  2   /* 1M/1M divider = 1/2 */

#define VBUS_DIVIDER_NUM   1
#define VBUS_DIVIDER_DEN   2   /* 1M/1M divider = 1/2 */

#define VSYS_DIVIDER_NUM   1
#define VSYS_DIVIDER_DEN   2   /* 1M/1M divider = 1/2 */

/* ADC constants */
#define ADC_REF_MV         600
#define ADC_MAX_VAL        4095

/* Initialize battery ADC subsystem */
int gos_battery_adc_init(void);

/* Read all battery ADC channels */
int gos_battery_adc_read_all(struct gos_battery_adc_data *data);

/* Read single channel */
int gos_battery_adc_read_channel(enum gos_battery_adc_channel ch, int16_t *mv);

/* Convenience functions */
int gos_battery_adc_get_vbatt_mv(void);
int gos_battery_adc_get_vbus_mv(void);
int gos_battery_adc_get_vsys_mv(void);

/* Status checks */
bool gos_battery_adc_is_vbus_present(void);
bool gos_battery_adc_is_charging(void);

/* Battery percentage estimation (0-100%) */
uint8_t gos_battery_adc_get_battery_percent(void);

/* Get cached data (thread-safe) */
int gos_battery_adc_get_cached(struct gos_battery_adc_data *data);

#ifdef __cplusplus
}
#endif

#endif /* GOS_BATTERY_ADC_H */
#ifndef GOS_BQ24075_H
#define GOS_BQ24075_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BQ24075_I2C_ADDR 0x6B

/* Register map */
enum bq24075_reg {
    BQ24075_REG_STATUS      = 0x00,
    BQ24075_REG_FAULT       = 0x01,
    BQ24075_REG_BATTERY     = 0x02,
    BQ24075_REG_SYSTEM      = 0x03,
    BQ24075_REG_CHARGER     = 0x04,
    BQ24075_REG_TERMINATION = 0x05,
    BQ24075_REG_TIMER       = 0x06,
    BQ24075_REG_THERMISTOR  = 0x07,
    BQ24075_REG_MISC        = 0x08,
    BQ24075_REG_NTC         = 0x09,
    BQ24075_REG_IC_INFO     = 0x0A,
};

/* Status register bits */
#define BQ24075_STAT_VBUS_STAT_MASK   0xC0
#define BQ24075_STAT_VBUS_STAT_SHIFT  6
#define BQ24075_STAT_CHRG_STAT_MASK   0x30
#define BQ24075_STAT_CHRG_STAT_SHIFT  4
#define BQ24075_STAT_DPM_STAT         BIT(3)
#define BQ24075_STAT_PG_STAT          BIT(2)
#define BQ24075_STAT_THERM_STAT       BIT(1)
#define BQ24075_STAT_VSYS_STAT        BIT(0)

/* VBUS status values */
enum bq24075_vbus_stat {
    BQ24075_VBUS_NONE      = 0,
    BQ24075_VBUS_USB_HOST  = 1,
    BQ24075_VBUS_ADAPTER   = 2,
    BQ24075_VBUS_OTG       = 3,
};

/* Charge status values */
enum bq24075_chrg_stat {
    BQ24075_CHRG_NOT_CHARGING = 0,
    BQ24075_CHRG_PRECHARGE    = 1,
    BQ24075_CHRG_FAST_CHARGE  = 2,
    BQ24075_CHRG_TERMINATION  = 3,
};

/* Fault register bits */
#define BQ24075_FAULT_WATCHDOG      BIT(7)
#define BQ24075_FAULT_OTG           BIT(6)
#define BQ24075_FAULT_BOOST         BIT(5)
#define BQ24075_FAULT_CHG           BIT(4)
#define BQ24075_FAULT_BAT           BIT(3)
#define BQ24075_FAULT_THERM         BIT(2)
#define BQ24075_FAULT_TIMER         BIT(1)
#define BQ24075_FAULT_NONE          0x00

/* Battery register bits */
#define BQ24075_BAT_BAT_MISSING     BIT(7)
#define BQ24075_BAT_BAT_DET_MASK    0x60
#define BQ24075_BAT_BAT_DET_SHIFT   5
#define BQ24075_BAT_BAT_STAT_MASK   0x1C
#define BQ24075_BAT_BAT_STAT_SHIFT  2
#define BQ24075_BAT_BAT_FAULT       BIT(1)
#define BQ24075_BAT_BAT_OVP         BIT(0)

/* System register bits */
#define BQ24075_SYS_VSYS_STAT       BIT(7)
#define BQ24075_SYS_VSYS_OVP        BIT(6)
#define BQ24075_SYS_VSYS_UVP        BIT(5)
#define BQ24075_SYS_VSYS_OCP        BIT(4)
#define BQ24075_SYS_VSYS_SHORT      BIT(3)
#define BQ24075_SYS_VSYS_UVLO       BIT(2)
#define BQ24075_SYS_VSYS_OVP_STAT   BIT(1)
#define BQ24075_SYS_VSYS_UVP_STAT   BIT(0)

/* Charger register bits */
#define BQ24075_CHRG_ICHG_MASK      0xF8
#define BQ24075_CHRG_ICHG_SHIFT     3
#define BQ24075_CHRG_VCHG_MASK      0x07

/* Termination register bits */
#define BQ24075_TERM_ITERM_MASK     0xF8
#define BQ24075_TERM_ITERM_SHIFT    3
#define BQ24075_TERM_VRECH_MASK     0x07

/* Timer register bits */
#define BQ24075_TIMER_CHG_TMR_MASK  0xC0
#define BQ24075_TIMER_CHG_TMR_SHIFT 6
#define BQ24075_TIMER_PRECHG_TMR    BIT(5)
#define BQ24075_TIMER_FAST_TMR      BIT(4)
#define BQ24075_TIMER_TMR2X         BIT(3)

/* Thermistor register bits */
#define BQ24075_THERM_TREG_MASK     0xE0
#define BQ24075_THERM_TREG_SHIFT    5
#define BQ24075_THERM_TS_EN         BIT(4)
#define BQ24075_THERM_TS_FAULT      BIT(3)
#define BQ24075_THERM_TS_STAT_MASK  0x0C
#define BQ24075_THERM_TS_STAT_SHIFT 2

/* Misc register bits */
#define BQ24075_MISC_OTG_EN         BIT(7)
#define BQ24075_MISC_BOOST_EN       BIT(6)
#define BQ24075_MISC_CHG_EN         BIT(5)
#define BQ24075_MISC_INT_MASK       BIT(4)
#define BQ24075_MISC_WD_RST         BIT(3)
#define BQ24075_MISC_OTG_PL         BIT(2)
#define BQ24075_MISC_BOOST_PL       BIT(1)
#define BQ24075_MISC_CHG_PL         BIT(0)

/* NTC register bits */
#define BQ24075_NTC_TS_COOL_MASK    0xC0
#define BQ24075_NTC_TS_COOL_SHIFT   6
#define BQ24075_NTC_TS_WARM_MASK    0x30
#define BQ24075_NTC_TS_WARM_SHIFT   4
#define BQ24075_NTC_TS_HOT_MASK     0x0C
#define BQ24075_NTC_TS_HOT_SHIFT    2
#define BQ24075_NTC_TS_COLD_MASK    0x03

/* IC Info register bits */
#define BQ24075_INFO_VENDOR_MASK    0xE0
#define BQ24075_INFO_VENDOR_SHIFT   5
#define BQ24075_INFO_PN_MASK        0x1C
#define BQ24075_INFO_PN_SHIFT       2
#define BQ24075_INFO_REV_MASK       0x03

struct gos_bq24075_data {
    uint8_t status;
    uint8_t fault;
    uint8_t battery;
    uint8_t system;
    uint8_t charger;
    uint8_t termination;
    uint8_t timer;
    uint8_t thermistor;
    uint8_t misc;
    uint8_t ntc;
    uint8_t ic_info;
    bool valid;
    uint32_t timestamp;
};

struct gos_bq24075_config {
    struct i2c_dt_spec i2c;
    struct gpio_dt_spec pg_gpio;
    struct gpio_dt_spec stat_gpio;
    struct gpio_dt_spec ce_gpio;
    struct gpio_dt_spec ts_gpio;
};

int gos_bq24075_init(const struct device *dev);
int gos_bq24075_read_all(const struct device *dev, struct gos_bq24075_data *data);
int gos_bq24075_read_reg(const struct device *dev, uint8_t reg, uint8_t *val);
int gos_bq24075_write_reg(const struct device *dev, uint8_t reg, uint8_t val);
int gos_bq24075_set_charge_current(const struct device *dev, uint32_t ma);
int gos_bq24075_set_charge_voltage(const struct device *dev, uint32_t mv);
int gos_bq24075_set_input_current_limit(const struct device *dev, uint32_t ma);
int gos_bq24075_enable_charging(const struct device *dev, bool enable);
int gos_bq24075_enable_otg(const struct device *dev, bool enable);
int gos_bq24075_get_status(const struct device *dev, uint8_t *status);
int gos_bq24075_get_fault(const struct device *dev, uint8_t *fault);
bool gos_bq24075_is_charging(const struct device *dev);
bool gos_bq24075_is_vbus_present(const struct device *dev);
bool gos_bq24075_is_battery_present(const struct device *dev);
bool gos_bq24075_is_charge_done(const struct device *dev);
bool gos_bq24075_has_fault(const struct device *dev);
int gos_bq24075_reset_watchdog(const struct device *dev);
int gos_bq24075_reset_faults(const struct device *dev);

#ifdef __cplusplus
}
#endif

#endif /* GOS_BQ24075_H */
#ifndef GOS_TSL2591_H
#define GOS_TSL2591_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TSL2591_I2C_ADDR 0x29

/* Register map */
enum tsl2591_reg {
    TSL2591_REG_ENABLE      = 0x00,
    TSL2591_REG_CONTROL     = 0x01,
    TSL2591_REG_THRESHLOWLOW  = 0x02,
    TSL2591_REG_THRESHLOWHI   = 0x03,
    TSL2591_REG_THRESHHILOW   = 0x04,
    TSL2591_REG_THRESHHIHI    = 0x05,
    TSL2591_REG_INTERRUPT   = 0x06,
    TSL2591_REG_CRC         = 0x08,
    TSL2591_REG_ID          = 0x0A,
    TSL2591_REG_CHAN0_LOW   = 0x14,
    TSL2591_REG_CHAN0_HIGH  = 0x15,
    TSL2591_REG_CHAN1_LOW   = 0x16,
    TSL2591_REG_CHAN1_HIGH  = 0x17,
};

/* Enable register bits */
#define TSL2591_ENABLE_AIEN     BIT(4)  /* ALS interrupt enable */
#define TSL2591_ENABLE_NPIEN    BIT(3)  /* No persistence interrupt enable */
#define TSL2591_ENABLE_WEN      BIT(2)  /* Wait enable */
#define TSL2591_ENABLE_AEN      BIT(1)  /* ALS enable */
#define TSL2591_ENABLE_PON      BIT(0)  /* Power on */

/* Control register bits */
#define TSL2591_CONTROL_NOISE_MASK   0xC0
#define TSL2591_CONTROL_NOISE_SHIFT  6
#define TSL2591_CONTROL_GAIN_MASK    0x30
#define TSL2591_CONTROL_GAIN_SHIFT   4
#define TSL2591_CONTROL_EDGE         BIT(1)
#define TSL2591_CONTROL_WLONG        BIT(0)

/* Gain values */
enum tsl2591_gain {
    TSL2591_GAIN_LOW    = 0,  /* 1x */
    TSL2591_GAIN_MED    = 1,  /* 25x */
    TSL2591_GAIN_HIGH   = 2,  /* 428x */
    TSL2591_GAIN_MAX    = 3,  /* 9876x */
};

/* Integration time values */
enum tsl2591_integration {
    TSL2591_INTEG_100MS   = 0x00,
    TSL2591_INTEG_200MS   = 0x01,
    TSL2591_INTEG_300MS   = 0x02,
    TSL2591_INTEG_400MS   = 0x03,
    TSL2591_INTEG_500MS   = 0x04,
    TSL2591_INTEG_600MS   = 0x05,
};

/* Interrupt register bits */
#define TSL2591_INT_AINT      BIT(4)  /* ALS interrupt */
#define TSL2591_INT_NPI       BIT(3)  /* No persistence interrupt */
#define TSL2591_INT_WINT      BIT(2)  /* Wait interrupt */
#define TSL2591_INT_CLEAR     0xE0    /* Clear all interrupts */

struct gos_tsl2591_data {
    uint16_t ch0;        /* Channel 0 (visible + IR) */
    uint16_t ch1;        /* Channel 1 (IR only) */
    uint32_t lux;        /* Calculated lux */
    uint32_t ir;         /* IR component */
    uint32_t visible;    /* Visible light */
    uint32_t timestamp;
    bool valid;
    bool interrupt_pending;
};

struct gos_tsl2591_config {
    struct i2c_dt_spec i2c;
    struct gpio_dt_spec int_gpio;
    enum tsl2591_gain gain;
    enum tsl2591_integration integration_time;
};

int gos_tsl2591_init(const struct device *dev);
int gos_tsl2591_read_channels(const struct device *dev, uint16_t *ch0, uint16_t *ch1);
int gos_tsl2591_read_lux(const struct device *dev, uint32_t *lux);
int gos_tsl2591_set_gain(const struct device *dev, uint8_t gain);
int gos_tsl2591_set_integration_time(const struct device *dev, uint8_t time);
int gos_tsl2591_enable_interrupt(const struct device *dev, bool enable);
int gos_tsl2591_clear_interrupt(const struct device *dev);
bool gos_tsl2591_is_interrupt_pending(const struct device *dev);
int gos_tsl2591_read_id(const struct device *dev, uint8_t *id);

#ifdef __cplusplus
}
#endif

#endif /* GOS_TSL2591_H */
#include "tsl2591.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

LOG_MODULE_REGISTER(tsl2591, LOG_LEVEL_INF);

struct tsl2591_data {
    struct gos_tsl2591_data data;
    struct gos_tsl2591_config config;
    struct k_mutex mutex;
    bool initialized;
};

static int tsl2591_read_reg(const struct device *dev, uint8_t reg, uint8_t *val)
{
    const struct device *i2c_dev = dev->config->i2c.bus;
    uint8_t cmd = 0xA0 | reg;  /* Command register: 0xA0 | register */
    int err = i2c_write_read_dt(&dev->config->i2c, &cmd, 1, val, 1);
    if (err) {
        LOG_ERR("Failed to read reg 0x%02X: %d", reg, err);
    }
    return err;
}

static int tsl2591_write_reg(const struct device *dev, uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {0xA0 | reg, val};
    int err = i2c_write_dt(&dev->config->i2c, buf, 2);
    if (err) {
        LOG_ERR("Failed to write reg 0x%02X: %d", reg, err);
    }
    return err;
}

static int tsl2591_read_word(const struct device *dev, uint8_t reg_low, uint16_t *val)
{
    uint8_t low, high;
    int err = tsl2591_read_reg(dev, reg_low, &low);
    if (err) return err;
    err = tsl2591_read_reg(dev, reg_low + 1, &high);
    if (err) return err;
    *val = (uint16_t)high << 8 | low;
    return 0;
}

static int tsl2591_update_data(const struct device *dev)
{
    struct tsl2591_data *data = dev->data;
    int err;

    k_mutex_lock(&data->mutex, K_FOREVER);

    err = tsl2591_read_word(dev, TSL2591_REG_CHAN0_LOW, &data->data.ch0);
    if (err) goto out;
    err = tsl2591_read_word(dev, TSL2591_REG_CHAN1_LOW, &data->data.ch1);
    if (err) goto out;

    /* Calculate lux using TSL2591 formula */
    uint32_t ch0 = data->data.ch0;
    uint32_t ch1 = data->data.ch1;

    if (ch0 == 0 || ch1 == 0) {
        data->data.lux = 0;
    } else {
        /* Lux calculation based on TSL2591 datasheet */
        uint32_t ch0_scaled = ch0 * 100;
        uint32_t ch1_scaled = ch1 * 100;
        uint32_t ratio = (ch1_scaled * 100) / ch0_scaled;

        if (ratio < 50) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 100) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 150) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 200) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 250) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 300) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 350) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 400) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 450) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 500) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 550) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 550) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 600) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 650) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 700) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 750) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 800) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 850) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 900) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else if (ratio < 950) {
            data->data.lux = (ch0_scaled * 100 - ch1_scaled * 100) / 100;
        } else {
            data->data.lux = 0;
        }
    }

    data->data.valid = true;
    data->data.timestamp = k_uptime_get_32();

out:
    return 0;
}

int gos_tsl2591_init(const struct device *dev)
{
    struct tsl2591_data *data = dev->data;
    int err;

    k_mutex_init(&data->mutex);

    if (!device_is_ready(dev->config->i2c.bus)) {
        LOG_ERR("I2C bus not ready");
        return -ENODEV;
    }

    if (data->config->int_gpio.port) {
        if (!gpio_is_ready_dt(&data->config->int_gpio)) {
            LOG_WRN("INT GPIO not ready");
        } else {
            gpio_pin_configure_dt(&data->config->int_gpio, GPIO_INPUT);
            gpio_pin_interrupt_configure_dt(&data->config->int_gpio, GPIO_INT_EDGE_FALLING);
        }
    }

    /* Read ID to verify communication */
    uint8_t id;
    int err = gos_tsl2591_read_id(dev, &data->data.id);
    if (err) {
        LOG_ERR("Failed to read TSL2591 ID: %d", err);
        return err;
    }

    if (data->data.id != 0x50) {
        LOG_ERR("Invalid TSL2591 ID: 0x%02X (expected 0x50)", data->data.id);
        return -ENODEV;
    }

    /* Power on */
    err = tsl2591_write_reg(dev, TSL2591_REG_ENABLE, TSL2591_ENABLE_PON);
    if (err) return err;
    k_msleep(10);

    /* Enable ALS */
    err = tsl2591_write_reg(dev, TSL2591_REG_ENABLE, TSL2591_ENABLE_PON | TSL2591_ENABLE_AEN);
    if (err) return err;

    /* Set gain */
    err = gos_tsl2591_set_gain(dev, data->config->gain);
    if (err) return err;

    /* Set integration time */
    err = gos_tsl2591_set_integration_time(dev, data->config->integration_time);
    if (err) return err;

    /* Enable interrupt if GPIO configured */
    if (data->config->int_gpio.port) {
        err = gos_tsl2591_enable_interrupt(dev, true);
        if (err) return err;
    }

    data->initialized = true;
    LOG_INF("TSL2591 initialized (gain=%d, integ=%d)", data->config->gain, data->config->integration_time);

    return 0;
}

int gos_tsl2591_read_channels(const struct device *dev, uint16_t *ch0, uint16_t *ch1)
{
    struct tsl2591_data *data = dev->data;
    int err = tsl2591_update_data(dev);
    if (err) return err;

    k_mutex_lock(&data->mutex, K_FOREVER);
    if (ch0) *ch0 = data->data.ch0;
    if (ch1) *ch1 = data->data.ch1;
    k_mutex_unlock(&data->mutex);
    return 0;
}

int gos_tsl2591_read_lux(const struct device *dev, uint32_t *lux)
{
    struct tsl2591_data *data = dev->data;
    int err = tsl2591_update_data(dev);
    if (err) return err;

    k_mutex_lock(&data->mutex, K_FOREVER);
    *lux = data->data.lux;
    k_mutex_unlock(&data->mutex);
    return 0;
}

int gos_tsl2591_set_gain(const struct device *dev, uint8_t gain)
{
    struct tsl2591_data *data = dev->data;
    uint8_t reg_val;

    if (gain > 3) return -EINVAL;

    uint8_t reg_val;
    int err = tsl2591_read_reg(dev, TSL2591_REG_CONTROL, &reg_val);
    if (err) return err;

    reg_val &= ~TSL2591_CONTROL_GAIN_MASK;
    reg_val |= (gain << TSL2591_CONTROL_GAIN_SHIFT) & TSL2591_CONTROL_GAIN_MASK;

    int err = tsl2591_write_reg(dev, TSL2591_REG_CONTROL, reg_val);
    if (err == 0) {
        data->config->gain = gain;
    }
    return err;
}

int gos_tsl2591_set_integration_time(const struct device *dev, uint8_t time)
{
    struct tsl2591_data *data = dev->data;
    uint8_t reg_val;

    if (time > 5) return -EINVAL;

    uint8_t reg_val;
    int err = tsl2591_read_reg(dev, TSL2591_REG_CONTROL, &reg_val);
    if (err) return err;

    reg_val &= ~TSL2591_CONTROL_NOISE_MASK;
    reg_val |= (time << TSL2591_CONTROL_NOISE_SHIFT) & TSL2591_CONTROL_NOISE_MASK;

    int err = tsl2591_write_reg(dev, TSL2591_REG_CONTROL, reg_val);
    if (err == 0) {
        data->config->integration_time = time;
    }
    return err;
}

int gos_tsl2591_enable_interrupt(const struct device *dev, bool enable)
{
    struct tsl2591_data *data = dev->data;
    uint8_t reg_val;
    int err = tsl2591_read_reg(dev, TSL2591_REG_ENABLE, &reg_val);
    if (err) return err;

    if (enable) {
        reg_val |= TSL2591_ENABLE_AIEN;
    } else {
        reg_val &= ~TSL2591_ENABLE_AIEN;
    }

    return tsl2591_write_reg(dev, TSL2591_REG_ENABLE, reg_val);
}

int gos_tsl2591_clear_interrupt(const struct device *dev)
{
    return tsl2591_write_reg(dev, TSL2591_REG_INTERRUPT, TSL2591_INT_CLEAR);
}

bool gos_tsl2591_is_interrupt_pending(const struct device *dev)
{
    uint8_t reg_val;
    int err = tsl2591_read_reg(dev, TSL2591_REG_INTERRUPT, &reg_val);
    if (err) return false;
    return (reg_val & TSL2591_INT_AINT) != 0;
}

int gos_tsl2591_read_id(const struct device *dev, uint8_t *id)
{
    return tsl2591_read_reg(dev, TSL2591_REG_ID, id);
}

static int tsl2591_read_reg(const struct device *dev, uint8_t reg, uint8_t *val)
{
    const struct device *i2c_dev = dev->config->i2c.bus;
    uint8_t cmd = 0xA0 | reg;
    int err = i2c_write_read_dt(&dev->config->i2c, &cmd, 1, val, 1);
    if (err) {
        LOG_ERR("Failed to read reg 0x%02X: %d", reg, err);
    }
    return err;
}

static int tsl2591_write_reg(const struct device *dev, uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {0xA0 | reg, val};
    int err = i2c_write_dt(&dev->config->i2c, buf, 2);
    if (err) {
        LOG_ERR("Failed to write reg 0x%02X: %d", reg, err);
    }
    return err;
}

static int tsl2591_init(const struct device *dev)
{
    struct tsl2591_data *data = dev->data;
    int err;

    k_mutex_init(&data->mutex);

    if (!device_is_ready(dev->config->i2c.bus)) {
        LOG_ERR("I2C bus not ready");
        return -ENODEV;
    }

    if (data->config->int_gpio.port) {
        if (!gpio_is_ready_dt(&data->config->int_gpio)) {
            LOG_WRN("INT GPIO not ready");
        } else {
            gpio_pin_configure_dt(&data->config->int_gpio, GPIO_INPUT);
            gpio_pin_interrupt_configure_dt(&data->config->int_gpio, GPIO_INT_EDGE_FALLING);
        }
    }

    /* Read ID to verify communication */
    uint8_t id;
    err = gos_tsl2591_read_id(dev, &data->data.id);
    if (err) {
        LOG_ERR("Failed to read TSL2591 ID: %d", err);
        return err;
    }

    if (data->data.id != 0x50) {
        LOG_ERR("Invalid TSL2591 ID: 0x%02X (expected 0x50)", data->data.id);
        return -ENODEV;
    }

    /* Power on */
    err = tsl2591_write_reg(dev, TSL2591_REG_ENABLE, TSL2591_ENABLE_PON);
    if (err) return err;
    k_msleep(10);

    /* Enable ALS */
    err = tsl2591_write_reg(dev, TSL2591_REG_ENABLE, TSL2591_ENABLE_PON | TSL2591_ENABLE_AEN);
    if (err) return err;

    /* Set gain */
    err = gos_tsl2591_set_gain(dev, data->config->gain);
    if (err) return err;

    /* Set integration time */
    err = gos_tsl2591_set_integration_time(dev, data->config->integration_time);
    if (err) return err;

    /* Enable interrupt if GPIO configured */
    if (data->config->int_gpio.port) {
        err = gos_tsl2591_enable_interrupt(dev, true);
        if (err) return err;
    }

    data->initialized = true;
    LOG_INF("TSL2591 initialized (gain=%d, integ=%d)", data->config->gain, data->config->integration_time);

    return 0;
}

DEVICE_DT_INST_DEFINE(0, tsl2591_init, NULL,
                      NULL, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
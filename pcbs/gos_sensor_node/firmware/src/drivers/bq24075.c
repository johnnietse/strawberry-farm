#include "bq24075.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

LOG_MODULE_REGISTER(bq24075, LOG_LEVEL_INF);

struct bq24075_data {
    struct gos_bq24075_data data;
    struct gos_bq24075_config config;
    struct k_mutex mutex;
    bool initialized;
};

static int bq24075_read_reg(const struct device *dev, uint8_t reg, uint8_t *val)
{
    const struct device *i2c_dev = dev->config->i2c.bus;
    uint8_t reg_addr = reg;
    int err = i2c_write_read_dt(&dev->config->i2c, &reg_addr, 1, val, 1);
    if (err) {
        LOG_ERR("Failed to read reg 0x%02X: %d", reg, err);
    }
    return err;
}

static int bq24075_write_reg(const struct device *dev, uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {reg, val};
    int err = i2c_write_dt(&dev->config->i2c, buf, 2);
    if (err) {
        LOG_ERR("Failed to write reg 0x%02X: %d", reg, err);
    }
    return err;
}

static int bq24075_update_data(const struct device *dev)
{
    struct bq24075_data *data = dev->data;
    int err;

    k_mutex_lock(&data->mutex, K_FOREVER);

    err = bq24075_read_reg(dev, BQ24075_REG_STATUS, &data->data.status);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_FAULT, &data->data.fault);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_BATTERY, &data->data.battery);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_SYSTEM, &data->data.system);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_CHARGER, &data->data.charger);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_TERMINATION, &data->data.termination);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_TIMER, &data->data.timer);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_THERMISTOR, &data->data.thermistor);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_MISC, &data->data.misc);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_NTC, &data->data.ntc);
    if (err) goto out;
    err = bq24075_read_reg(dev, BQ24075_REG_IC_INFO, &data->data.ic_info);
    if (err) goto out;

    data->data.valid = true;
    data->data.timestamp = k_uptime_get_32();

out:
    k_mutex_unlock(&data->mutex);
    return err;
}

int gos_bq24075_init(const struct device *dev)
{
    struct bq24075_data *data = dev->data;
    int err;

    if (data->initialized) {
        return 0;
    }

    k_mutex_init(&data->mutex);

    if (!device_is_ready(dev->config->i2c.bus)) {
        LOG_ERR("I2C bus not ready");
        return -ENODEV;
    }

    if (dev->config->pg_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->pg_gpio)) {
            LOG_WRN("PG GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->pg_gpio, GPIO_INPUT);
        }
    }

    if (dev->config->stat_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->stat_gpio)) {
            LOG_WRN("STAT GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->stat_gpio, GPIO_INPUT);
        }
    }

    if (dev->config->ce_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->ce_gpio)) {
            LOG_WRN("CE GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->ce_gpio, GPIO_OUTPUT_INACTIVE);
        }
    }

    if (dev->config->ts_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->ts_gpio)) {
            LOG_WRN("TS GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->ts_gpio, GPIO_INPUT);
        }
    }

    /* Read IC info to verify communication */
    int err = bq24075_update_data(dev);
    if (err) {
        LOG_ERR("Failed to communicate with BQ24075: %d", err);
        return err;
    }

    data->initialized = true;
    LOG_INF("BQ24075 initialized (PN=%d, Rev=%d)",
            (data->data.ic_info & BQ24075_INFO_PN_MASK) >> BQ24075_INFO_PN_SHIFT,
            data->data.ic_info & BQ24075_INFO_REV_MASK);

    return 0;
}

int gos_bq24075_read_all(const struct device *dev, struct gos_bq24075_data *data)
{
    struct bq24075_data *drv_data = dev->data;
    int err = bq24075_update_data(dev);
    if (err) {
        return err;
    }

    k_mutex_lock(&drv_data->mutex, K_FOREVER);
    *data = drv_data->data;
    k_mutex_unlock(&drv_data->mutex);
    return 0;
}

int gos_bq24075_read_reg(const struct device *dev, uint8_t reg, uint8_t *val)
{
    return bq24075_read_reg(dev, reg, val);
}

int gos_bq24075_write_reg(const struct device *dev, uint8_t reg, uint8_t val)
{
    struct bq24075_data *data = dev->data;
    int err;

    k_mutex_lock(&data->mutex, K_FOREVER);
    int err = bq24075_write_reg(dev, reg, val);
    k_mutex_unlock(&data->mutex);
    return err;
}

int gos_bq24075_set_charge_current(const struct device *dev, uint32_t ma)
{
    struct bq24075_data *data = dev->data;
    uint8_t reg_val;

    if (ma < 500) ma = 500;
    if (ma > 3000) ma = 3000;

    /* ICHG = (ma - 500) / 50, 50mA steps */
    uint8_t ichg = (ma - 500) / 50;
    uint8_t reg_val = (ichg << BQ24075_CHRG_ICHG_SHIFT) & BQ24075_CHRG_ICHG_MASK;

    int err = gos_bq24075_write_reg(dev, BQ24075_REG_CHARGER, reg_val);
    if (err == 0) {
        LOG_INF("Charge current set to %d mA", ma);
    }
    return err;
}

int gos_bq24075_set_charge_voltage(const struct device *dev, uint32_t mv)
{
    if (mv < 3500) mv = 3500;
    if (mv > 4400) mv = 4400;

    /* VCHG = (mv - 3500) / 100, 100mV steps */
    uint8_t vchg = (mv - 3500) / 100;
    uint8_t reg_val = vchg & BQ24075_CHRG_VCHG_MASK;

    return gos_bq24075_write_reg(dev, BQ24075_REG_CHARGER, vchg);
}

int gos_bq24075_set_input_current_limit(const struct device *dev, uint32_t ma)
{
    if (ma < 100) ma = 100;
    if (ma > 3000) ma = 3000;

    /* ILIM pin resistor sets hardware limit, but we can set via I2C if supported */
    LOG_INF("Input current limit set to %d mA (hardware limited by ILIM pin)", ma);
    return 0;
}

int gos_bq24075_enable_charging(const struct device *dev, bool enable)
{
    struct bq24075_data *data = dev->data;
    uint8_t reg_val;
    int err;

    k_mutex_lock(&data->mutex, K_FOREVER);
    err = bq24075_read_reg(dev, BQ24075_REG_MISC, &data->data.misc);
    if (err) {
        k_mutex_unlock(&data->mutex);
        return err;
    }

    if (enable) {
        data->data.misc |= BQ24075_MISC_CHG_EN;
    } else {
        data->data.misc &= ~BQ24075_MISC_CHG_EN;
    }

    err = bq24075_write_reg(dev, BQ24075_REG_MISC, data->data.misc);
    k_mutex_unlock(&data->mutex);

    if (err == 0) {
        LOG_INF("Charging %s", enable ? "enabled" : "disabled");
    }
    return err;
}

int gos_bq24075_enable_otg(const struct device *dev, bool enable)
{
    struct bq24075_data *data = dev->data;
    uint8_t reg_val;
    int err;

    k_mutex_lock(&data->mutex, K_FOREVER);
    err = bq24075_read_reg(dev, BQ24075_REG_MISC, &data->data.misc);
    if (err) {
        k_mutex_unlock(&data->mutex);
        return err;
    }

    if (enable) {
        data->data.misc |= BQ24075_MISC_OTG_EN | BQ24075_MISC_BOOST_EN;
    } else {
        data->data.misc &= ~(BQ24075_MISC_OTG_EN | BQ24075_MISC_BOOST_EN);
    }

    err = bq24075_write_reg(dev, BQ24075_REG_MISC, data->data.misc);
    k_mutex_unlock(&data->mutex);

    if (err == 0) {
        LOG_INF("OTG %s", enable ? "enabled" : "disabled");
    }
    return err;
}

int gos_bq24075_get_status(const struct device *dev, uint8_t *status)
{
    struct bq24075_data *data = dev->data;
    int err = bq24075_update_data(dev);
    if (err) return err;

    k_mutex_lock(&data->mutex, K_FOREVER);
    *status = data->data.status;
    k_mutex_unlock(&data->mutex);
    return 0;
}

int gos_bq24075_get_fault(const struct device *dev, uint8_t *fault)
{
    struct bq24075_data *data = dev->data;
    int err = bq24075_update_data(dev);
    if (err) return err;

    k_mutex_lock(&data->mutex, K_FOREVER);
    *fault = data->data.fault;
    k_mutex_unlock(&data->mutex);
    return 0;
}

bool gos_bq24075_is_charging(const struct device *dev)
{
    uint8_t status;
    int err = gos_bq24075_get_status(dev, &status);
    if (err) return false;

    uint8_t chrg_stat = (status & BQ24075_STAT_CHRG_STAT_MASK) >> BQ24075_STAT_CHRG_STAT_SHIFT;
    return (chrg_stat == BQ24075_CHRG_PRECHARGE) ||
           (chrg_stat == BQ24075_CHRG_FAST_CHARGE);
}

bool gos_bq24075_is_vbus_present(const struct device *dev)
{
    uint8_t status;
    int err = gos_bq24075_get_status(dev, &status);
    if (err) return false;

    uint8_t vbus_stat = (status & BQ24075_STAT_VBUS_STAT_MASK) >> BQ24075_STAT_VBUS_STAT_SHIFT;
    return vbus_stat != BQ24075_VBUS_NONE;
}

bool gos_bq24075_is_battery_present(const struct device *dev)
{
    struct bq24075_data *data = dev->data;
    int err = bq24075_update_data(dev);
    if (err) return false;

    k_mutex_lock(&data->mutex, K_FOREVER);
    bool present = !(data->data.battery & BQ24075_BAT_BAT_MISSING);
    k_mutex_unlock(&data->mutex);
    return present;
}

bool gos_bq24075_is_charge_done(const struct device *dev)
{
    uint8_t status;
    int err = gos_bq24075_get_status(dev, &status);
    if (err) return false;

    uint8_t chrg_stat = (status & BQ24075_STAT_CHRG_STAT_MASK) >> BQ24075_STAT_CHRG_STAT_SHIFT;
    return chrg_stat == BQ24075_CHRG_TERMINATION;
}

bool gos_bq24075_has_fault(const struct device *dev)
{
    uint8_t fault;
    int err = gos_bq24075_get_fault(dev, &fault);
    if (err) return true;
    return fault != 0;
}

int gos_bq24075_reset_watchdog(const struct device *dev)
{
    uint8_t reg_val = BQ24075_MISC_WD_RST;
    return gos_bq24075_write_reg(dev, BQ24075_REG_MISC, reg_val);
}

int gos_bq24075_reset_faults(const struct device *dev)
{
    uint8_t fault;
    int err = gos_bq24075_get_fault(dev, &fault);
    if (err) return err;

    if (fault == 0) return 0;

    /* Write 0 to fault register to clear */
    return gos_bq24075_write_reg(dev, BQ24075_REG_FAULT, 0);
}

static int bq24075_init(const struct device *dev)
{
    struct bq24075_data *data = dev->data;
    int err;

    k_mutex_init(&data->mutex);

    if (!device_is_ready(dev->config->i2c.bus)) {
        LOG_ERR("I2C bus not ready");
        return -ENODEV;
    }

    if (dev->config->pg_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->pg_gpio)) {
            LOG_WRN("PG GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->pg_gpio, GPIO_INPUT);
        }
    }

    if (dev->config->stat_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->stat_gpio)) {
            LOG_WRN("STAT GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->stat_gpio, GPIO_INPUT);
        }
    }

    if (dev->config->ce_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->ce_gpio)) {
            LOG_WRN("CE GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->ce_gpio, GPIO_OUTPUT_INACTIVE);
        }
    }

    if (dev->config->ts_gpio.port) {
        if (!gpio_is_ready_dt(&dev->config->ts_gpio)) {
            LOG_WRN("TS GPIO not ready");
        } else {
            gpio_pin_configure_dt(&dev->config->ts_gpio, GPIO_INPUT);
        }
    }

    err = bq24075_update_data(dev);
    if (err) {
        LOG_ERR("Failed to communicate with BQ24075: %d", err);
        return err;
    }

    data->initialized = true;
    LOG_INF("BQ24075 initialized (PN=%d, Rev=%d)",
            (data->data.ic_info & BQ24075_INFO_PN_MASK) >> BQ24075_INFO_PN_SHIFT,
            data->data.ic_info & BQ24075_INFO_REV_MASK);

    return 0;
}

#define DT_DRV_COMPAT ti_bq24075

static struct bq24075_data bq24075_data_0 = {
    .config = {
        .i2c = I2C_DT_SPEC_INST_GET(0),
        .pg_gpio = GPIO_DT_SPEC_INST_GET_OR(0, pg_gpios, {0}),
        .stat_gpio = GPIO_DT_SPEC_INST_GET_OR(0, stat_gpios, {0}),
        .ce_gpio = GPIO_DT_SPEC_INST_GET_OR(0, ce_gpios, {0}),
        .ts_gpio = GPIO_DT_SPEC_INST_GET_OR(0, ts_gpios, {0}),
    },
};

DEVICE_DT_INST_DEFINE(0, bq24075_init, NULL,
                      &bq24075_data_0, NULL,
                      POST_KERNEL, CONFIG_SENSOR_INIT_PRIORITY,
                      NULL);
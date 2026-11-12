#include "battery_adc.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

LOG_MODULE_REGISTER(battery_adc, LOG_LEVEL_INF);

#define ADC_NODE DT_NODELABEL(adc)
#define VBATT_CHANNEL DT_IO_CHANNELS_CTLR_BY_NAME(ADC_NODE, vbatt)
#define VBUS_CHANNEL DT_IO_CHANNELS_CTLR_BY_NAME(ADC_NODE, vbus)
#define VSYS_CHANNEL DT_IO_CHANNELS_CTLR_BY_NAME(ADC_NODE, vsys)

#define VBATT_DIVIDER_NUM 1000000  /* 1M */
#define VBATT_DIVIDER_DEN 1000000  /* 1M */
#define VBUS_DIVIDER_NUM 1000000
#define VBUS_DIVIDER_DEN 1000000
#define VSYS_DIVIDER_NUM 1000000
#define VSYS_DIVIDER_DEN 1000000

#define ADC_RESOLUTION 12
#define ADC_REF_MV 3000
#define ADC_MAX_VAL ((1 << ADC_RESOLUTION) - 1)

static const struct device *adc_dev;
static struct adc_channel_cfg channel_cfgs[3];
static struct gos_battery_adc_data cached_data;
static struct k_mutex data_mutex;
static bool initialized = false;

static int adc_channel_setup(enum gos_battery_adc_channel ch, const struct adc_channel_cfg *cfg)
{
    int err = adc_channel_setup(adc_dev, cfg);
    if (err) {
        LOG_ERR("Failed to setup ADC channel %d: %d", ch, err);
    }
    return err;
}

int gos_battery_adc_init(void)
{
    int err;

    if (initialized) {
        return 0;
    }

    adc_dev = DEVICE_DT_GET(ADC_NODE);
    if (!device_is_ready(adc_dev)) {
        LOG_ERR("ADC device not ready");
        return -ENODEV;
    }

    k_mutex_init(&data_mutex);

    /* VBATT channel */
    channel_cfgs[GOS_BATTERY_ADC_VBATT] = (struct adc_channel_cfg){
        .gain = ADC_GAIN_1_6,
        .reference = ADC_REF_INTERNAL,
        .acquisition_time = ADC_ACQ_TIME(ADC_ACQ_TIME_MICROSECONDS, 10),
        .channel_id = VBATT_CHANNEL,
        .differential = 0,
    };
    err = adc_channel_setup(adc_dev, &channel_cfgs[GOS_BATTERY_ADC_VBATT]);
    if (err) {
        LOG_ERR("Failed to setup VBATT channel: %d", err);
        return err;
    }

    /* VBUS channel */
    channel_cfgs[GOS_BATTERY_ADC_VBUS] = (struct adc_channel_cfg){
        .gain = ADC_GAIN_1_6,
        .reference = ADC_REF_INTERNAL,
        .acquisition_time = ADC_ACQ_TIME(ADC_ACQ_TIME_MICROSECONDS, 10),
        .channel_id = VBUS_CHANNEL,
        .differential = 0,
    };
    err = adc_channel_setup(adc_dev, &channel_cfgs[GOS_BATTERY_ADC_VBUS]);
    if (err) {
        LOG_ERR("Failed to setup VBUS channel: %d", err);
        return err;
    }

    /* VSYS channel */
    channel_cfgs[GOS_BATTERY_ADC_VSYS] = (struct adc_channel_cfg){
        .gain = ADC_GAIN_1_6,
        .reference = ADC_REF_INTERNAL,
        .acquisition_time = ADC_ACQ_TIME(ADC_ACQ_TIME_MICROSECONDS, 10),
        .channel_id = VSYS_CHANNEL,
        .differential = 0,
    };
    err = adc_channel_setup(adc_dev, &channel_cfgs[GOS_BATTERY_ADC_VSYS]);
    if (err) {
        LOG_ERR("Failed to setup VSYS channel: %d", err);
        return err;
    }

    /* Initial read */
    err = gos_battery_adc_read_all(&cached_data);
    if (err) {
        LOG_WRN("Initial ADC read failed: %d", err);
    } else {
        cached_data.valid = true;
    }

    initialized = true;
    LOG_INF("Battery ADC initialized (3 channels)");
    return 0;
}

static int read_channel_raw(enum gos_battery_adc_channel ch, int32_t *raw)
{
    int32_t raw_val = 0;
    struct adc_sequence sequence = {
        .channels = BIT(channel_cfgs[ch].channel_id),
        .buffer = &raw_val,
        .buffer_size = sizeof(raw_val),
        .resolution = ADC_RESOLUTION,
        .oversampling = 4,
        .calibrate = true,
    };

    int err = adc_read(adc_dev, &sequence);
    if (err) {
        LOG_ERR("ADC read failed for channel %d: %d", ch, err);
        return err;
    }

    *raw = raw_val;
    return 0;
}

static int32_t raw_to_mv(int32_t raw, uint32_t div_num, uint32_t div_den)
{
    int64_t mv = (int64_t)raw * ADC_REF_MV * div_den;
    mv = mv / (ADC_MAX_VAL * div_num);
    return (int32_t)mv;
}

int gos_battery_adc_read_all(struct gos_battery_adc_data *data)
{
    if (!initialized || !data) {
        return -EINVAL;
    }

    int32_t raw[3];
    int err;

    for (int i = 0; i < 3; i++) {
        err = read_channel_raw(i, &raw[i]);
        if (err) {
            return err;
        }
    }

    k_mutex_lock(&data_mutex, K_FOREVER);

    data->vbatt_mv = raw_to_mv(raw[GOS_BATTERY_ADC_VBATT], VBATT_DIVIDER_NUM, VBATT_DIVIDER_DEN);
    data->vbus_mv = raw_to_mv(raw[GOS_BATTERY_ADC_VBUS], VBUS_DIVIDER_NUM, VBUS_DIVIDER_DEN);
    data->vsys_mv = raw_to_mv(raw[GOS_BATTERY_ADC_VSYS], VSYS_DIVIDER_NUM, VSYS_DIVIDER_DEN);
    data->timestamp = k_uptime_get_32();
    data->valid = true;

    cached_data = *data;

    k_mutex_unlock(&data_mutex);

    return 0;
}

int gos_battery_adc_read_channel(enum gos_battery_adc_channel ch, int16_t *mv)
{
    if (!initialized || ch >= GOS_BATTERY_ADC_CHANNELS || !mv) {
        return -EINVAL;
    }

    int32_t raw;
    int err = read_channel_raw(ch, &raw);
    if (err) {
        return err;
    }

    uint32_t div_num, div_den;
    switch (ch) {
        case GOS_BATTERY_ADC_VBATT:
            div_num = VBATT_DIVIDER_NUM;
            div_den = VBATT_DIVIDER_DEN;
            break;
        case GOS_BATTERY_ADC_VBUS:
            div_num = VBUS_DIVIDER_NUM;
            div_den = VBUS_DIVIDER_DEN;
            break;
        case GOS_BATTERY_ADC_VSYS:
            div_num = VSYS_DIVIDER_NUM;
            div_den = VSYS_DIVIDER_DEN;
            break;
        default:
            return -EINVAL;
    }

    *mv = (int16_t)raw_to_mv(raw, div_num, div_den);
    return 0;
}

int gos_battery_adc_get_vbatt_mv(void)
{
    int16_t mv;
    int err = gos_battery_adc_read_channel(GOS_BATTERY_ADC_VBATT, &mv);
    return err ? err : mv;
}

int gos_battery_adc_get_vbus_mv(void)
{
    int16_t mv;
    int err = gos_battery_adc_read_channel(GOS_BATTERY_ADC_VBUS, &mv);
    return err ? err : mv;
}

int gos_battery_adc_get_vsys_mv(void)
{
    int16_t mv;
    int err = gos_battery_adc_read_channel(GOS_BATTERY_ADC_VSYS, &mv);
    return err ? err : mv;
}

bool gos_battery_adc_is_vbus_present(void)
{
    int16_t vbus_mv = gos_battery_adc_get_vbus_mv();
    return vbus_mv > 4000; /* > 4V = USB present */
}

bool gos_battery_adc_is_charging(void)
{
    int16_t vbus_mv = gos_battery_adc_get_vbus_mv();
    int16_t vbatt_mv = gos_battery_adc_get_vbatt_mv();
    return (vbus_mv > 4500) && (vbus_mv > vbatt_mv);
}

uint8_t gos_battery_adc_get_battery_percent(void)
{
    int16_t vbatt_mv = gos_battery_adc_get_vbatt_mv();

    if (vbatt_mv >= 4200) return 100;
    if (vbatt_mv >= 4100) return 90 + (vbatt_mv - 4100) / 11;
    if (vbatt_mv >= 4000) return 80 + (vbatt_mv - 4000) / 12;
    if (vbatt_mv >= 3900) return 60 + (vbatt_mv - 3900) / 16;
    if (vbatt_mv >= 3800) return 40 + (vbatt_mv - 3800) / 25;
    if (vbatt_mv >= 3700) return 20 + (vbatt_mv - 3700) / 50;
    if (vbatt_mv >= 3600) return 10 + (vbatt_mv - 3600) / 100;
    if (vbatt_mv >= 3400) return 5 + (vbatt_mv - 3400) / 400;
    if (vbatt_mv >= 3200) return 1 + (vbatt_mv - 3200) / 200;
    return 0;
}
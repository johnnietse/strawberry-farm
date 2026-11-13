/*
 * G.O.S. sensor node rev 3.0 application.
 *
 * Every SAMPLE_PERIOD_S: read SHT40, TSL2591, battery voltage and charger
 * status, log them, flash the status LED. The two PWM channels to the LED
 * driver board start at 0 %.
 *
 * Not implemented: Thread / CoAP uplink, low-power sleep.
 */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/drivers/watchdog.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/util.h>

#include <stdlib.h>

#include "gos_main.h"

LOG_MODULE_REGISTER(gos_main, LOG_LEVEL_INF);

#define SAMPLE_PERIOD_S   60
#define WDT_TIMEOUT_MS    30000
#define WDT_FEED_PERIOD_S 10
#define BATTERY_LOW_MV    3300

BUILD_ASSERT(WDT_FEED_PERIOD_S * 1000 < WDT_TIMEOUT_MS, "watchdog would expire between feeds");

#define USER_NODE DT_PATH(zephyr_user)

static const struct device *const sht40 = DEVICE_DT_GET(DT_NODELABEL(sht40));
static const struct device *const tsl2591 = DEVICE_DT_GET(DT_NODELABEL(tsl2591));
static const struct device *const vbatt = DEVICE_DT_GET(DT_NODELABEL(vbatt));
static const struct device *const wdt = DEVICE_DT_GET(DT_ALIAS(watchdog0));

static const struct gpio_dt_spec pgood = GPIO_DT_SPEC_GET(USER_NODE, pgood_gpios);
static const struct gpio_dt_spec chg = GPIO_DT_SPEC_GET(USER_NODE, chg_gpios);
static const struct gpio_dt_spec status_led = GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);

static const struct pwm_dt_spec pwm_blue = PWM_DT_SPEC_GET(DT_ALIAS(pwm_led0));
static const struct pwm_dt_spec pwm_red = PWM_DT_SPEC_GET(DT_ALIAS(pwm_led1));

static int wdt_channel = -1;

static int to_milli(const struct sensor_value *v)
{
	return v->val1 * 1000 + v->val2 / 1000;
}

static int read_climate(struct gos_sensor_data *d)
{
	struct sensor_value temp, rh;
	int err;

	if (!device_is_ready(sht40)) {
		return -ENODEV;
	}
	err = sensor_sample_fetch(sht40);
	if (err) {
		return err;
	}
	err = sensor_channel_get(sht40, SENSOR_CHAN_AMBIENT_TEMP, &temp);
	if (err) {
		return err;
	}
	err = sensor_channel_get(sht40, SENSOR_CHAN_HUMIDITY, &rh);
	if (err) {
		return err;
	}
	d->temp_mc = to_milli(&temp);
	d->humidity_mpct = to_milli(&rh);
	return 0;
}

static int read_light(struct gos_sensor_data *d)
{
	struct sensor_value lux;
	int err;

	if (!device_is_ready(tsl2591)) {
		return -ENODEV;
	}
	/*
	 * The Zephyr TSL2591 driver reports lux only on SENSOR_CHAN_ALL.
	 * SENSOR_CHAN_LIGHT is the raw visible channel, a relative value.
	 */
	err = sensor_sample_fetch_chan(tsl2591, SENSOR_CHAN_ALL);
	if (err) {
		return err;
	}
	err = sensor_channel_get(tsl2591, SENSOR_CHAN_ALL, &lux);
	if (err) {
		return err;
	}
	d->light_lux = lux.val1;
	return 0;
}

static int read_battery(struct gos_sensor_data *d)
{
	struct sensor_value volts;
	int err;

	if (!device_is_ready(vbatt)) {
		return -ENODEV;
	}
	err = sensor_sample_fetch(vbatt);
	if (err) {
		return err;
	}
	err = sensor_channel_get(vbatt, SENSOR_CHAN_VOLTAGE, &volts);
	if (err) {
		return err;
	}
	d->battery_mv = to_milli(&volts);
	return 0;
}

static int read_charger(struct gos_sensor_data *d)
{
	int usb = gpio_pin_get_dt(&pgood);
	int charging = gpio_pin_get_dt(&chg);

	if (usb < 0) {
		return usb;
	}
	if (charging < 0) {
		return charging;
	}
	d->usb_power = usb > 0;
	d->charging = charging > 0;
	return 0;
}

static void sample_all(struct gos_sensor_data *d)
{
	static const struct {
		const char *name;
		int (*read)(struct gos_sensor_data *d);
		uint8_t flag;
	} sources[] = {
		{ "SHT40", read_climate, GOS_VALID_CLIMATE },
		{ "TSL2591", read_light, GOS_VALID_LIGHT },
		{ "battery", read_battery, GOS_VALID_BATTERY },
		{ "charger", read_charger, GOS_VALID_CHARGER },
	};

	*d = (struct gos_sensor_data){ .uptime_ms = k_uptime_get() };

	for (size_t i = 0; i < ARRAY_SIZE(sources); i++) {
		int err = sources[i].read(d);

		if (err) {
			LOG_WRN("%s read failed: %d", sources[i].name, err);
		} else {
			d->valid |= sources[i].flag;
		}
	}
}

static void report(const struct gos_sensor_data *d)
{
	if (d->valid & GOS_VALID_CLIMATE) {
		LOG_INF("temp %s%d.%03d C, humidity %d.%03d %%", d->temp_mc < 0 ? "-" : "",
			abs(d->temp_mc) / 1000, abs(d->temp_mc) % 1000,
			d->humidity_mpct / 1000, d->humidity_mpct % 1000);
	}
	if (d->valid & GOS_VALID_LIGHT) {
		LOG_INF("light %d lux", d->light_lux);
	}
	if (d->valid & GOS_VALID_BATTERY) {
		LOG_INF("battery %d mV", d->battery_mv);
		if (d->battery_mv < BATTERY_LOW_MV) {
			LOG_WRN("battery low");
		}
	}
	if (d->valid & GOS_VALID_CHARGER) {
		LOG_INF("usb power %s, %s", d->usb_power ? "present" : "absent",
			d->charging ? "charging" : "not charging");
	}
}

int gos_set_spectral_mix(uint8_t blue_pct, uint8_t red_pct)
{
	const struct {
		const struct pwm_dt_spec *pwm;
		uint8_t pct;
	} channels[] = {
		{ &pwm_blue, MIN(blue_pct, 100) },
		{ &pwm_red, MIN(red_pct, 100) },
	};

	for (size_t i = 0; i < ARRAY_SIZE(channels); i++) {
		const struct pwm_dt_spec *pwm = channels[i].pwm;
		uint32_t pulse = (uint32_t)(((uint64_t)pwm->period * channels[i].pct) / 100U);
		int err;

		if (!pwm_is_ready_dt(pwm)) {
			return -ENODEV;
		}
		err = pwm_set_pulse_dt(pwm, pulse);
		if (err) {
			return err;
		}
	}
	return 0;
}

static int gpio_init(void)
{
	const struct {
		const struct gpio_dt_spec *spec;
		gpio_flags_t flags;
	} pins[] = {
		{ &pgood, GPIO_INPUT },
		{ &chg, GPIO_INPUT },
		{ &status_led, GPIO_OUTPUT_INACTIVE },
	};

	for (size_t i = 0; i < ARRAY_SIZE(pins); i++) {
		int err;

		if (!gpio_is_ready_dt(pins[i].spec)) {
			return -ENODEV;
		}
		err = gpio_pin_configure_dt(pins[i].spec, pins[i].flags);
		if (err) {
			return err;
		}
	}
	return 0;
}

static int watchdog_start(void)
{
	const struct wdt_timeout_cfg cfg = {
		.flags = WDT_FLAG_RESET_SOC,
		.window.min = 0U,
		.window.max = WDT_TIMEOUT_MS,
	};
	int channel;
	int err;

	if (!device_is_ready(wdt)) {
		return -ENODEV;
	}
	channel = wdt_install_timeout(wdt, &cfg);
	if (channel < 0) {
		return channel;
	}
	err = wdt_setup(wdt, WDT_OPT_PAUSE_HALTED_BY_DBG);
	if (err) {
		return err;
	}
	wdt_channel = channel;
	return 0;
}

int main(void)
{
	struct gos_sensor_data data;
	int err;

	LOG_INF("G.O.S. sensor node rev 3.0");

	err = gpio_init();
	if (err) {
		LOG_ERR("GPIO init failed: %d", err);
	}
	err = gos_set_spectral_mix(0, 0);
	if (err) {
		LOG_ERR("LED board PWM init failed: %d", err);
	}
	err = watchdog_start();
	if (err) {
		LOG_ERR("watchdog not started: %d", err);
	}

	while (1) {
		gpio_pin_set_dt(&status_led, 1);
		sample_all(&data);
		report(&data);
		gpio_pin_set_dt(&status_led, 0);

		for (int waited = 0; waited < SAMPLE_PERIOD_S; waited += WDT_FEED_PERIOD_S) {
			if (wdt_channel >= 0) {
				wdt_feed(wdt, wdt_channel);
			}
			k_sleep(K_SECONDS(WDT_FEED_PERIOD_S));
		}
	}
	return 0;
}

/**
 * G.O.S. Phytotron Node - Main Firmware
 * =====================================
 * Target: nRF52840 DK/Dongle
 * RTOS: Zephyr v3.x (via nRF Connect SDK)
 * Protocol: OpenThread (Thread 1.3) + CoAP
 * Sensors: SHT4x (Temp/Humidity), TSL2591 (Light)
 *
 * This is PRODUCTION-READY firmware using official Zephyr APIs.
 */

#include <openthread/coap.h>
#include <openthread/thread.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/net/coap.h>
#include <zephyr/net/openthread.h>


LOG_MODULE_REGISTER(gos_main, CONFIG_LOG_DEFAULT_LEVEL);

/* Device Tree node references */
#define SHT4X_NODE DT_NODELABEL(sht4x_sensor)
#define PWM_LED_BLUE DT_NODELABEL(pwm_led_blue)
#define PWM_LED_RED DT_NODELABEL(pwm_led_red)

/* Sensor device pointers */
static const struct device *sht4x_dev;
static const struct device *tsl2591_dev;

/* PWM LED devices */
static const struct pwm_dt_spec pwm_blue = PWM_DT_SPEC_GET(PWM_LED_BLUE);
static const struct pwm_dt_spec pwm_red = PWM_DT_SPEC_GET(PWM_LED_RED);

/* Thread stacks */
#define SENSOR_STACK_SIZE 2048
#define SENSOR_PRIORITY 5
K_THREAD_STACK_DEFINE(sensor_stack, SENSOR_STACK_SIZE);
static struct k_thread sensor_thread;

/* Global sensor data (protected by mutex) */
static struct k_mutex sensor_mutex;
static struct {
  float temp_c;
  float humidity_pct;
  float par_umol;
  uint32_t battery_mv;
} sensor_data;

/* CoAP endpoint URI */
#define COAP_URI_PATH "telemetry"

/**
 * Initialize all sensors
 */
static int sensors_init(void) {
  /* SHT4x Temperature/Humidity */
  sht4x_dev = DEVICE_DT_GET(SHT4X_NODE);
  if (!device_is_ready(sht4x_dev)) {
    LOG_ERR("SHT4x sensor not ready");
    return -ENODEV;
  }
  LOG_INF("SHT4x sensor initialized");

  /* TSL2591 Light Sensor (optional) */
  tsl2591_dev = device_get_binding("TSL2591");
  if (tsl2591_dev) {
    LOG_INF("TSL2591 light sensor initialized");
  }

  return 0;
}

/**
 * Initialize PWM for LED control
 */
static int leds_init(void) {
  if (!pwm_is_ready_dt(&pwm_blue) || !pwm_is_ready_dt(&pwm_red)) {
    LOG_ERR("PWM LEDs not ready");
    return -ENODEV;
  }

  /* Set initial state: LEDs off */
  pwm_set_pulse_dt(&pwm_blue, 0);
  pwm_set_pulse_dt(&pwm_red, 0);

  LOG_INF("PWM LED control initialized");
  return 0;
}

/**
 * Set LED spectral mix (0.0 - 1.0)
 */
void gos_set_spectral_mix(float blue_ratio, float red_ratio) {
  uint32_t blue_pulse = (uint32_t)(blue_ratio * pwm_blue.period);
  uint32_t red_pulse = (uint32_t)(red_ratio * pwm_red.period);

  pwm_set_pulse_dt(&pwm_blue, blue_pulse);
  pwm_set_pulse_dt(&pwm_red, red_pulse);

  LOG_DBG("Spectral mix set: Blue=%.2f, Red=%.2f", blue_ratio, red_ratio);
}

/**
 * Read sensors and update global data
 */
static void read_sensors(void) {
  struct sensor_value temp, hum;
  int ret;

  /* Read SHT4x */
  ret = sensor_sample_fetch(sht4x_dev);
  if (ret == 0) {
    sensor_channel_get(sht4x_dev, SENSOR_CHAN_AMBIENT_TEMP, &temp);
    sensor_channel_get(sht4x_dev, SENSOR_CHAN_HUMIDITY, &hum);

    k_mutex_lock(&sensor_mutex, K_FOREVER);
    sensor_data.temp_c = sensor_value_to_float(&temp);
    sensor_data.humidity_pct = sensor_value_to_float(&hum);
    k_mutex_unlock(&sensor_mutex);

    LOG_INF("Temp: %.2f°C, Humidity: %.1f%%", sensor_data.temp_c,
            sensor_data.humidity_pct);
  } else {
    LOG_WRN("SHT4x read failed: %d", ret);
  }

  /* Read TSL2591 (if available) */
  if (tsl2591_dev) {
    struct sensor_value light;
    ret = sensor_sample_fetch(tsl2591_dev);
    if (ret == 0) {
      sensor_channel_get(tsl2591_dev, SENSOR_CHAN_LIGHT, &light);
      k_mutex_lock(&sensor_mutex, K_FOREVER);
      sensor_data.par_umol = sensor_value_to_float(&light);
      k_mutex_unlock(&sensor_mutex);
    }
  }

  /* Autonomous LED control based on temperature */
  if (sensor_data.temp_c > 28.0f) {
    /* Heat stress: shift to blue spectrum */
    gos_set_spectral_mix(0.8f, 0.2f);
    LOG_WRN("High temp! Shifting to blue spectrum");
  } else {
    /* Normal: balanced spectrum */
    gos_set_spectral_mix(0.4f, 0.6f);
  }
}

/**
 * Send telemetry via CoAP to Border Router
 */
static void send_coap_telemetry(void) {
  otInstance *ot = openthread_get_default_instance();
  if (!otThreadGetDeviceRole(ot)) {
    LOG_WRN("Thread not attached, skipping CoAP");
    return;
  }

  otError error;
  otMessage *message;
  otMessageInfo messageInfo;
  otCoapType coapType = OT_COAP_TYPE_CONFIRMABLE;

  message = otCoapNewMessage(ot, NULL);
  if (message == NULL) {
    LOG_ERR("Failed to create CoAP message");
    return;
  }

  otCoapMessageInit(message, coapType, OT_COAP_CODE_POST);
  otCoapMessageAppendUriPathOptions(message, COAP_URI_PATH);
  otCoapMessageSetPayloadMarker(message);

  /* Create JSON payload */
  char payload[128];
  k_mutex_lock(&sensor_mutex, K_FOREVER);
  snprintf(payload, sizeof(payload),
           "{\"temp\":%.2f,\"hum\":%.1f,\"par\":%.0f,\"bat\":%u}",
           sensor_data.temp_c, sensor_data.humidity_pct, sensor_data.par_umol,
           sensor_data.battery_mv);
  k_mutex_unlock(&sensor_mutex);

  otMessageAppend(message, payload, strlen(payload));

  /* Send to Border Router IPv6 address */
  memset(&messageInfo, 0, sizeof(messageInfo));
  otIp6AddressFromString("fd00::1", &messageInfo.mPeerAddr);
  messageInfo.mPeerPort = OT_DEFAULT_COAP_PORT;

  error = otCoapSendRequest(ot, message, &messageInfo, NULL, NULL);
  if (error != OT_ERROR_NONE) {
    LOG_ERR("CoAP send failed: %s", otThreadErrorToString(error));
    otMessageFree(message);
  } else {
    LOG_INF("CoAP telemetry sent");
  }
}

/**
 * Sensor thread entry point
 */
static void sensor_thread_entry(void *p1, void *p2, void *p3) {
  ARG_UNUSED(p1);
  ARG_UNUSED(p2);
  ARG_UNUSED(p3);

  LOG_INF("Sensor thread started");

  while (1) {
    read_sensors();
    send_coap_telemetry();

    /* Sleep for 60 seconds (configurable) */
    k_sleep(K_SECONDS(60));
  }
}

/**
 * Main entry point
 */
int main(void) {
  LOG_INF("=== G.O.S. Phytotron Node v2.0 ===");
  LOG_INF("Queen's University EPOWER Lab");

  k_mutex_init(&sensor_mutex);

  /* Initialize hardware */
  if (sensors_init() != 0) {
    LOG_ERR("Sensor init failed!");
    return -1;
  }

  if (leds_init() != 0) {
    LOG_WRN("LED init failed, continuing without LED control");
  }

  /* Start sensor thread */
  k_thread_create(&sensor_thread, sensor_stack, SENSOR_STACK_SIZE,
                  sensor_thread_entry, NULL, NULL, NULL, SENSOR_PRIORITY, 0,
                  K_NO_WAIT);
  k_thread_name_set(&sensor_thread, "gos_sensor");

  LOG_INF("System initialized, starting sensor loop");

  return 0;
}

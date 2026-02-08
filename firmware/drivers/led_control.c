/**
 * G.O.S. LED Control Driver
 * Uses Zephyr PWM API for dimming control
 */

#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>


LOG_MODULE_REGISTER(led_control, CONFIG_LOG_DEFAULT_LEVEL);

/* Fallback GPIO-only control for boards without PWM */
#define LED_BLUE_NODE DT_ALIAS(led0_blue)
#define LED_RED_NODE DT_ALIAS(led1_red)

#if DT_NODE_HAS_STATUS(LED_BLUE_NODE, okay)
static const struct gpio_dt_spec blue_led =
    GPIO_DT_SPEC_GET(LED_BLUE_NODE, gpios);
static const struct gpio_dt_spec red_led =
    GPIO_DT_SPEC_GET(LED_RED_NODE, gpios);

void gos_led_init(void) {
  if (!gpio_is_ready_dt(&blue_led) || !gpio_is_ready_dt(&red_led)) {
    LOG_ERR("LED GPIO devices not ready");
    return;
  }

  gpio_pin_configure_dt(&blue_led, GPIO_OUTPUT_INACTIVE);
  gpio_pin_configure_dt(&red_led, GPIO_OUTPUT_INACTIVE);

  LOG_INF("LED GPIO control initialized");
}

void gos_set_spectral_mix(float blue_level, float red_level) {
  /* Simple threshold-based on/off for GPIO mode */
  gpio_pin_set_dt(&blue_led, blue_level > 0.1f ? 1 : 0);
  gpio_pin_set_dt(&red_led, red_level > 0.1f ? 1 : 0);
}

#else
/* No LED nodes defined - stub implementation */
void gos_led_init(void) { LOG_WRN("No LED nodes defined in devicetree"); }

void gos_set_spectral_mix(float blue_level, float red_level) {
  ARG_UNUSED(blue_level);
  ARG_UNUSED(red_level);
}
#endif

#ifndef GOS_SX1262_H
#define GOS_SX1262_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/drivers/gpio.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SX1262_MAX_PAYLOAD 255

enum sx1262_op_mode {
    SX1262_MODE_SLEEP = 0,
    SX1262_MODE_STDBY_RC,
    SX1262_MODE_STDBY_XOSC,
    SX1262_MODE_FS,
    SX1262_MODE_TX,
    SX1262_MODE_RX,
    SX1262_MODE_CAD,
};

enum sx1262_modulation {
    SX1262_MOD_LORA = 0,
    SX1262_MOD_FSK = 1,
};

struct gos_sx1262_config {
    struct spi_dt_spec spi;
    struct gpio_dt_spec nss_gpio;
    struct gpio_dt_spec busy_gpio;
    struct gpio_dt_spec dio1_gpio;
    struct gpio_dt_spec dio2_gpio;
    struct gpio_dt_spec dio3_gpio;
    struct gpio_dt_spec nreset_gpio;
    uint32_t frequency_hz;
    uint8_t spreading_factor;
    uint8_t bandwidth;
    uint8_t coding_rate;
    uint8_t preamble_length;
    int8_t tx_power_dbm;
};

struct gos_sx1262_data {
    enum sx1262_op_mode mode;
    struct k_mutex mutex;
    struct k_sem tx_done_sem;
    struct k_sem rx_done_sem;
    struct k_sem cad_done_sem;
    uint8_t rx_buffer[255];
    uint8_t rx_len;
    int16_t rssi;
    int8_t snr;
    bool rx_done;
    bool tx_done;
    bool cad_done;
    bool initialized;
};

int gos_sx1262_init(const struct device *dev);
int gos_sx1262_set_mode(const struct device *dev, enum sx1262_op_mode mode);
int gos_sx1262_set_modulation(const struct device *dev, enum sx1262_modulation mod);
int gos_sx1262_set_frequency(const struct device *dev, uint32_t freq_hz);
int gos_sx1262_set_tx_power(const struct device *dev, int8_t power_dbm);
int gos_sx1262_set_lora_params(const struct device *dev, uint8_t sf, uint8_t bw, uint8_t cr, uint8_t preamble);
int gos_sx1262_tx(const struct device *dev, const uint8_t *data, uint8_t len, int32_t timeout_ms);
int gos_sx1262_rx(const struct device *dev, int32_t timeout_ms);
int gos_sx1262_rx_get(const struct device *dev, uint8_t *data, uint8_t *len, int16_t *rssi, int8_t *snr);
int gos_sx1262_cad(const struct device *dev, int32_t timeout_ms);
int gos_sx1262_sleep(const struct device *dev);
int gos_sx1262_wake(const struct device *dev);
int gos_sx1262_get_status(const struct device *dev, uint8_t *status);
bool gos_sx1262_is_busy(const struct device *dev);

#ifdef __cplusplus
}
#endif

#endif /* GOS_SX1262_H */
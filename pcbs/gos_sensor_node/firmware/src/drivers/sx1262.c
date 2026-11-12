#include "sx1262.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <string.h>

LOG_MODULE_REGISTER(sx1262, LOG_LEVEL_INF);

/* SX1262 Commands */
#define SX1262_CMD_SET_SLEEP              0x84
#define SX1262_CMD_SET_STANDBY            0x80
#define SX1262_CMD_SET_FS                 0xC1
#define SX1262_CMD_SET_TX                 0x83
#define SX1262_CMD_SET_RX                 0x82
#define SX1262_CMD_SET_CAD                0xC5
#define SX1262_CMD_SET_TX_CONTINUOUS_WAVE 0xD1
#define SX1262_CMD_SET_TX_CONTINUOUS_PREAMBLE 0xD2
#define SX1262_CMD_SET_PACKET_TYPE        0x8A
#define SX1262_CMD_SET_RF_FREQUENCY       0x86
#define SX1262_CMD_SET_TX_PARAMS          0x8E
#define SX1262_CMD_SET_PACKET_PARAMS      0x8C
#define SX1262_CMD_SET_BUFFER_BASE_ADDRESS 0x8F
#define SX1262_CMD_SET_LORA_SYMB_NUM_TIMEOUT 0xA0
#define SX1262_CMD_GET_STATUS             0xC0
#define SX1262_CMD_GET_RSSI_INST          0x15
#define SX1262_CMD_GET_RX_BUFFER_STATUS   0x13
#define SX1262_CMD_GET_PACKET_STATUS      0x14
#define SX1262_CMD_GET_RSSI_INST          0x15
#define SX1262_CMD_GET_STATS              0x10
#define SX1262_CMD_RESET_STATS            0x00
#define SX1262_CMD_WRITE_BUFFER           0x0E
#define SX1262_CMD_READ_BUFFER            0x1D
#define SX1262_CMD_SET_DIO_IRQ_PARAMS     0x8D
#define SX1262_CMD_GET_IRQ_STATUS         0x12
#define SX1262_CMD_CLR_IRQ_STATUS         0x02
#define SX1262_CMD_SET_DIO2_AS_RF_SWITCH  0x9D
#define SX1262_CMD_SET_DIO3_AS_TCXO_CTRL  0x97
#define SX1262_CMD_CALIBRATE              0x89
#define SX1262_CMD_SET_REGULATOR_MODE     0x96
#define SX1262_CMD_SET_SAVE_CONTEXT       0xD5
#define SX1262_CMD_SET_AUTO_TX            0x98
#define SX1262_CMD_SET_AUTO_FS            0x9E
#define SX1262_CMD_SET_LONG_PREAMBLE      0x9B
#define SX1262_CMD_SET_UART_SPEED         0x9D
#define SX1262_CMD_SET_RANGING_ROLE       0xA3

/* Packet types */
#define SX1262_PACKET_TYPE_GFSK 0x00
#define SX1262_PACKET_TYPE_LORA 0x01

/* LoRa bandwidths */
#define SX1262_LORA_BW_7_81_KHZ   0x00
#define SX1262_LORA_BW_10_41_KHZ  0x08
#define SX1262_LORA_BW_15_62_KHZ  0x01
#define SX1262_LORA_BW_20_83_KHZ  0x09
#define SX1262_LORA_BW_31_25_KHZ  0x02
#define SX1262_LORA_BW_41_66_KHZ  0x0A
#define SX1262_LORA_BW_62_50_KHZ  0x03
#define SX1262_LORA_BW_125_KHZ    0x04
#define SX1262_LORA_BW_250_KHZ    0x05
#define SX1262_LORA_BW_500_KHZ    0x06

/* LoRa coding rates */
#define SX1262_LORA_CR_4_5 0x01
#define SX1262_LORA_CR_4_6 0x02
#define SX1262_LORA_CR_4_7 0x03
#define SX1262_LORA_CR_4_8 0x04

/* IRQ masks */
#define SX1262_IRQ_TX_DONE          BIT(0)
#define SX1262_IRQ_RX_DONE          BIT(1)
#define SX1262_IRQ_PREAMBLE_DETECTED BIT(2)
#define SX1262_IRQ_SYNC_WORD_VALID  BIT(3)
#define SX1262_IRQ_HEADER_VALID     BIT(4)
#define SX1262_IRQ_HEADER_ERR       BIT(5)
#define SX1262_IRQ_CRC_ERR          BIT(6)
#define SX1262_IRQ_CAD_DONE         BIT(7)
#define SX1262_IRQ_CAD_ACTIVITY     BIT(7)
#define SX1262_IRQ_RX_TX_TIMEOUT    BIT(8)

static int sx1262_write_cmd(const struct device *dev, uint8_t cmd, const uint8_t *data, uint8_t len)
{
    struct sx1262_data *data = dev->data;
    const struct gos_sx1262_config *config = dev->config;
    uint8_t buf[256];
    buf[0] = cmd;
    if (data && len > 0) {
        memcpy(&buf[1], data, len);
    }
    struct spi_buf tx_buf = {.buf = buf, .len = len + 1};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    int err = spi_write_dt(&config->spi, &tx_bufs);
    if (err) {
        LOG_ERR("SPI write failed: %d", err);
    }
    return err;
}

static int sx1262_read_cmd(const struct device *dev, uint8_t cmd, uint8_t *data, uint8_t len)
{
    const struct gos_sx1262_config *config = dev->config;
    uint8_t cmd_byte = cmd;
    struct spi_buf tx_buf = {.buf = &cmd_byte, .len = 1};
    struct spi_buf rx_buf = {.buf = data, .len = len};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    struct spi_buf_set rx_bufs = {.buffers = &rx_buf, .count = 1};
    int err = spi_transceive_dt(&config->spi, &tx_bufs, &rx_bufs);
    if (err) {
        LOG_ERR("SPI read failed: %d", err);
    }
    return err;
}

static int sx1262_wait_busy(const struct device *dev, int32_t timeout_ms)
{
    const struct gos_sx1262_config *config = dev->config;
    int64_t start = k_uptime_get();
    while (gpio_pin_get_dt(&config->busy_gpio) == 1) {
        if (k_uptime_get() - start > timeout_ms) {
            return -ETIMEDOUT;
        }
        k_msleep(1);
    }
    return 0;
}

static int sx1262_set_standby(const struct device *dev, uint8_t mode)
{
    uint8_t data = mode;
    return sx1262_write_cmd(dev, SX1262_CMD_SET_STANDBY, &data, 1);
}

static int sx1262_set_sleep(const struct device *dev, uint8_t config)
{
    uint8_t data = config;
    return sx1262_write_cmd(dev, SX1262_CMD_SET_SLEEP, &data, 1);
}

static int sx1262_set_fs(const struct device *dev)
{
    return sx1262_write_cmd(dev, SX1262_CMD_SET_FS, NULL, 0);
}

static int sx1262_set_packet_type(const struct device *dev, uint8_t type)
{
    uint8_t data = type;
    return sx1262_write_cmd(dev, SX1262_CMD_SET_PACKET_TYPE, &data, 1);
}

static int sx1262_set_rf_frequency(const struct device *dev, uint32_t freq_hz)
{
    uint32_t freq = (uint32_t)((uint64_t)freq_hz * 524288 / 32000000);
    uint8_t data[4] = {
        (freq >> 24) & 0xFF,
        (freq >> 16) & 0xFF,
        (freq >> 8) & 0xFF,
        freq & 0xFF
    };
    return sx1262_write_cmd(dev, SX1262_CMD_SET_RF_FREQUENCY, data, 4);
}

static int sx1262_set_tx_params(const struct device *dev, int8_t power_dbm, uint8_t ramp_time)
{
    uint8_t data[2] = {power_dbm & 0xFF, ramp_time};
    return sx1262_write_cmd(dev, SX1262_CMD_SET_TX_PARAMS, data, 2);
}

static int sx1262_set_lora_modulation_params(const struct device *dev, uint8_t sf, uint8_t bw, uint8_t cr, uint8_t ldro)
{
    uint8_t data[4] = {sf, bw, cr, ldro};
    return sx1262_write_cmd(dev, 0x8B, data, 4);
}

static int sx1262_set_packet_params(const struct device *dev, uint16_t preamble, uint8_t header_type, uint8_t payload_len, uint8_t crc_type, uint8_t invert_iq)
{
    uint8_t data[6] = {
        (preamble >> 8) & 0xFF, preamble & 0xFF,
        header_type,
        payload_len,
        crc_type,
        invert_iq
    };
    return sx1262_write_cmd(dev, SX1262_CMD_SET_PACKET_PARAMS, data, 6);
}

static int sx1262_set_buffer_base_address(const struct device *dev, uint8_t tx_base, uint8_t rx_base)
{
    uint8_t data[2] = {tx_base, rx_base};
    return sx1262_write_cmd(dev, SX1262_CMD_SET_BUFFER_BASE_ADDRESS, data, 2);
}

static int sx1262_set_dio_irq_params(const struct device *dev, uint16_t irq_mask, uint16_t dio1_mask, uint16_t dio2_mask, uint16_t dio3_mask)
{
    uint8_t data[8] = {
        (irq_mask >> 8) & 0xFF, irq_mask & 0xFF,
        (dio1_mask >> 8) & 0xFF, dio1_mask & 0xFF,
        (dio2_mask >> 8) & 0xFF, dio2_mask & 0xFF,
        (dio3_mask >> 8) & 0xFF, dio3_mask & 0xFF
    };
    return sx1262_write_cmd(dev, SX1262_CMD_SET_DIO_IRQ_PARAMS, data, 8);
}

static int sx1262_get_irq_status(const struct device *dev, uint16_t *irq)
{
    uint8_t data[2];
    int err = sx1262_read_cmd(dev, SX1262_CMD_GET_IRQ_STATUS, data, 2);
    if (err) return err;
    *irq = (data[0] << 8) | data[1];
    return 0;
}

static int sx1262_clear_irq_status(const struct device *dev, uint16_t irq_mask)
{
    uint8_t data[2] = {(irq_mask >> 8) & 0xFF, irq_mask & 0xFF};
    return sx1262_write_cmd(dev, SX1262_CMD_CLR_IRQ_STATUS, data, 2);
}

static int sx1262_get_status(const struct device *dev, uint8_t *status)
{
    return sx1262_read_cmd(dev, SX1262_CMD_GET_STATUS, status, 1);
}

static int sx1262_get_rssi_inst(const struct device *dev, int16_t *rssi)
{
    uint8_t data;
    int err = sx1262_read_cmd(dev, SX1262_CMD_GET_RSSI_INST, &data, 1);
    if (err) return err;
    *rssi = -(int16_t)data / 2;
    return 0;
}

static int sx1262_get_packet_status(const struct device *dev, int16_t *rssi, int8_t *snr)
{
    uint8_t data[3];
    int err = sx1262_read_cmd(dev, SX1262_CMD_GET_PACKET_STATUS, data, 3);
    if (err) return err;
    *rssi = -(int16_t)data[0] / 2;
    *snr = (int8_t)data[1] / 4;
    return 0;
}

static int sx1262_get_rx_buffer_status(const struct device *dev, uint8_t *len, uint8_t *offset)
{
    uint8_t data[2];
    int err = sx1262_read_cmd(dev, SX1262_CMD_GET_RX_BUFFER_STATUS, data, 2);
    if (err) return err;
    *len = data[0];
    *offset = data[1];
    return 0;
}

static int sx1262_read_buffer(const struct device *dev, uint8_t offset, uint8_t *data, uint8_t len)
{
    uint8_t cmd = SX1262_CMD_READ_BUFFER;
    uint8_t buf[256];
    buf[0] = SX1262_CMD_READ_BUFFER;
    buf[1] = offset;
    struct spi_buf tx_buf = {.buf = buf, .len = 2};
    struct spi_buf rx_buf = {.buf = data, .len = len};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    struct spi_buf_set rx_bufs = {.buffers = &rx_buf, .count = 1};
    int err = spi_transceive_dt(&dev->config->spi, &tx_bufs, &rx_bufs);
    return err;
}

static int sx1262_write_buffer(const struct device *dev, uint8_t offset, const uint8_t *data, uint8_t len)
{
    uint8_t buf[256];
    buf[0] = SX1262_CMD_WRITE_BUFFER;
    buf[1] = offset;
    memcpy(&buf[2], data, len);
    struct spi_buf tx_buf = {.buf = buf, .len = len + 2};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    int err = spi_write_dt(&dev->config->spi, &tx_bufs);
    return err;
}

int gos_sx1262_init(const struct device *dev)
{
    struct sx1262_data *data = dev->data;
    const struct gos_sx1262_config *config = dev->config;
    int err;

    k_mutex_init(&data->mutex);
    k_sem_init(&data->tx_done_sem, 0, 1);
    k_sem_init(&data->rx_done_sem, 0, 1);
    k_sem_init(&data->cad_done_sem, 0, 1);

    if (!device_is_ready(config->spi.bus)) {
        LOG_ERR("SPI bus not ready");
        return -ENODEV;
    }

    if (!device_is_ready(config->nss_gpio.port)) {
        LOG_ERR("NSS GPIO not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->busy_gpio.port)) {
        LOG_ERR("BUSY GPIO not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->dio1_gpio.port)) {
        LOG_ERR("DIO1 GPIO not ready");
        return -ENODEV;
    }
    if (!device_is_ready(config->nreset_gpio.port)) {
        LOG_ERR("NRESET GPIO not ready");
        return -ENODEV;
    }

    gpio_pin_configure_dt(&config->nss_gpio, GPIO_OUTPUT_ACTIVE);
    gpio_pin_configure_dt(&config->busy_gpio, GPIO_INPUT);
    gpio_pin_configure_dt(&config->dio1_gpio, GPIO_INPUT);
    gpio_pin_configure_dt(&config->dio2_gpio, GPIO_INPUT);
    gpio_pin_configure_dt(&config->dio3_gpio, GPIO_INPUT);
    gpio_pin_configure_dt(&config->nreset_gpio, GPIO_OUTPUT_ACTIVE);

    if (config->dio2_gpio.port) {
        gpio_pin_configure_dt(&config->dio2_gpio, GPIO_INPUT);
    }
    if (config->dio3_gpio.port) {
        gpio_pin_configure_dt(&config->dio3_gpio, GPIO_INPUT);
    }

    /* Reset the radio */
    gpio_pin_set_dt(&config->nreset_gpio, 0);
    k_msleep(10);
    gpio_pin_set_dt(&config->nreset_gpio, 1);
    k_msleep(20);

    /* Wait for BUSY to go low */
    err = sx1262_wait_busy(dev, 1000);
    if (err) {
        LOG_ERR("Radio did not become ready after reset");
        return -ETIMEDOUT;
    }

    /* Set standby RC */
    err = sx1262_set_standby(dev, 0x00);
    if (err) return err;

    /* Set packet type to LoRa */
    err = sx1262_set_packet_type(dev, SX1262_PACKET_TYPE_LORA);
    if (err) return err;

    /* Set RF frequency */
    err = sx1262_set_rf_frequency(dev, config->frequency_hz);
    if (err) return err;

    /* Set TX power */
    err = sx1262_set_tx_params(dev, config->tx_power_dbm, 0x00);
    if (err) return err;

    /* Set LoRa modulation parameters */
    uint8_t bw;
    switch (config->bandwidth) {
        case 125: bw = SX1262_LORA_BW_125_KHZ; break;
        case 250: bw = SX1262_LORA_BW_250_KHZ; break;
        case 500: bw = SX1262_LORA_BW_500_KHZ; break;
        default: bw = SX1262_LORA_BW_125_KHZ;
    }
    err = sx1262_set_lora_modulation_params(dev, config->spreading_factor, bw, config->coding_rate, 0);
    if (err) return err;

    /* Set packet parameters */
    err = sx1262_set_packet_params(dev, config->preamble_length, 0x00, 0xFF, 0x01, 0x00);
    if (err) return err;

    /* Set buffer base addresses */
    err = sx1262_set_buffer_base_address(dev, 0x00, 0x00);
    if (err) return err;

    /* Set DIO IRQ parameters */
    err = sx1262_set_dio_irq_params(dev,
        SX1262_IRQ_TX_DONE | SX1262_IRQ_RX_DONE | SX1262_IRQ_CRC_ERR | SX1262_IRQ_RX_TX_TIMEOUT,
        SX1262_IRQ_TX_DONE | SX1262_IRQ_RX_DONE | SX1262_IRQ_CRC_ERR | SX1262_IRQ_RX_TX_TIMEOUT,
        0, 0);
    if (err) return err;

    /* Set DIO2 as RF switch control */
    err = sx1262_write_cmd(dev, SX1262_CMD_SET_DIO2_AS_RF_SWITCH, (uint8_t[]){1}, 1);
    if (err) return err;

    /* Calibrate */
    err = sx1262_write_cmd(dev, SX1262_CMD_CALIBRATE, (uint8_t[]){0xFF}, 1);
    if (err) return err;

    /* Set standby RC */
    err = sx1262_set_standby(dev, 0x00);
    if (err) return err;

    data->initialized = true;
    data->mode = SX1262_MODE_STDBY_RC;

    LOG_INF("SX1262 initialized (freq=%d Hz, SF=%d, BW=%d kHz, CR=4/%d, preamble=%d, power=%d dBm)",
            config->frequency_hz, config->spreading_factor, config->bandwidth,
            config->coding_rate + 4, config->preamble_length, config->tx_power_dbm);

    return 0;
}

int gos_sx1262_set_mode(const struct device *dev, enum sx1262_op_mode mode)
{
    struct sx1262_data *data = dev->data;
    int err;

    k_mutex_lock(&data->mutex, K_FOREVER);

    int err;
    switch (mode) {
        case SX1262_MODE_SLEEP:
            err = sx1262_set_sleep(dev, 0x00);
            break;
        case SX1262_MODE_STDBY_RC:
            err = sx1262_set_standby(dev, 0x00);
            break;
        case SX1262_MODE_STDBY_XOSC:
            err = sx1262_set_standby(dev, 0x01);
            break;
        case SX1262_MODE_FS:
            err = sx1262_set_fs(dev);
            break;
        case SX1262_MODE_TX:
            err = sx1262_write_cmd(dev, SX1262_CMD_SET_TX, NULL, 0);
            break;
        case SX1262_MODE_RX:
            err = sx1262_write_cmd(dev, SX1262_CMD_SET_RX, NULL, 0);
            break;
        case SX1262_MODE_CAD:
            err = sx1262_write_cmd(dev, SX1262_CMD_SET_CAD, NULL, 0);
            break;
        default:
            err = -EINVAL;
    }

    if (err == 0) {
        data->mode = mode;
    }

    k_mutex_unlock(&data->mutex);
    return err;
}

int gos_sx1262_set_modulation(const struct device *dev, enum sx1262_modulation mod)
{
    return sx1262_set_packet_type(dev, mod);
}

int gos_sx1262_set_frequency(const struct device *dev, uint32_t freq_hz)
{
    return sx1262_set_rf_frequency(dev, freq_hz);
}

int gos_sx1262_set_tx_power(const struct device *dev, int8_t power_dbm)
{
    return sx1262_set_tx_params(dev, power_dbm, 0x00);
}

int gos_sx1262_set_lora_params(const struct device *dev, uint8_t sf, uint8_t bw, uint8_t cr, uint8_t preamble)
{
    struct gos_sx1262_config *config = dev->config;
    config->spreading_factor = sf;
    config->bandwidth = bw;
    config->coding_rate = cr;
    config->preamble_length = preamble;
    return sx1262_set_lora_modulation_params(dev, sf, bw, cr, 0);
}

int gos_sx1262_tx(const struct device *dev, const uint8_t *data, uint8_t len, int32_t timeout_ms)
{
    struct sx1262_data *drv_data = dev->data;
    int err;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    /* Write payload to buffer */
    err = sx1262_write_buffer(dev, 0x00, data, len);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    /* Set payload length */
    err = sx1262_set_packet_params(dev, drv_data->config->preamble_length, 0x00, len, 0x01, 0x00);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    /* Clear IRQ */
    err = sx1262_clear_irq_status(dev, SX1262_IRQ_TX_DONE | SX1262_IRQ_RX_TX_TIMEOUT);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    /* Set TX mode */
    err = sx1262_set_mode(dev, SX1262_MODE_TX);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    /* Wait for TX done or timeout */
    k_mutex_unlock(&drv_data->mutex);
    err = k_sem_take(&drv_data->tx_done_sem, K_MSEC(timeout_ms));
    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return -ETIMEDOUT;
    }

    /* Check for errors */
    uint16_t irq;
    err = sx1262_get_irq_status(dev, &irq);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    if (irq & SX1262_IRQ_CRC_ERR) {
        k_mutex_unlock(&drv_data->mutex);
        return -EIO;
    }

    if (irq & SX1262_IRQ_RX_TX_TIMEOUT) {
        k_mutex_unlock(&drv_data->mutex);
        return -ETIMEDOUT;
    }

    k_mutex_unlock(&drv_data->mutex);
    return 0;
}

int gos_sx1262_rx(const struct device *dev, int32_t timeout_ms)
{
    struct sx1262_data *drv_data = dev->data;
    int err;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    /* Clear IRQ */
    err = sx1262_clear_irq_status(dev, SX1262_IRQ_RX_DONE | SX1262_IRQ_CRC_ERR | SX1262_IRQ_RX_TX_TIMEOUT);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    /* Set RX mode */
    err = sx1262_set_mode(dev, SX1262_MODE_RX);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    k_mutex_unlock(&drv_data->mutex);
    err = k_sem_take(&drv_data->rx_done_sem, K_MSEC(timeout_ms));
    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return -ETIMEDOUT;
    }

    /* Check for errors */
    uint16_t irq;
    err = sx1262_get_irq_status(dev, &irq);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    if (irq & SX1262_IRQ_CRC_ERR) {
        k_mutex_unlock(&drv_data->mutex);
        return -EIO;
    }

    if (irq & SX1262_IRQ_RX_TX_TIMEOUT) {
        k_mutex_unlock(&drv_data->mutex);
        return -ETIMEDOUT;
    }

    k_mutex_unlock(&drv_data->mutex);
    return 0;
}

int gos_sx1262_rx_get(const struct device *dev, uint8_t *data, uint8_t *len, int16_t *rssi, int8_t *snr)
{
    struct sx1262_data *drv_data = dev->data;
    int err;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    /* Get packet status */
    err = sx1262_get_packet_status(dev, rssi, snr);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    /* Get buffer status */
    uint8_t rx_len, offset;
    err = sx1262_get_rx_buffer_status(dev, &rx_len, &offset);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    if (rx_len > SX1262_MAX_PAYLOAD) {
        rx_len = SX1262_MAX_PAYLOAD;
    }

    /* Read payload */
    err = sx1262_read_buffer(dev, offset, data, rx_len);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    *len = rx_len;
    k_mutex_unlock(&drv_data->mutex);
    return 0;
}

int gos_sx1262_cad(const struct device *dev, int32_t timeout_ms)
{
    struct sx1262_data *data = dev->data;
    int err;

    k_mutex_lock(&data->mutex, K_FOREVER);

    err = sx1262_set_mode(dev, SX1262_MODE_CAD);
    if (err) {
        k_mutex_unlock(&data->mutex);
        return err;
    }

    k_mutex_unlock(&data->mutex);
    err = k_sem_take(&data->cad_done_sem, K_MSEC(timeout_ms));
    if (err) {
        return -ETIMEDOUT;
    }

    return 0;
}

int gos_sx1262_sleep(const struct device *dev)
{
    return gos_sx1262_set_mode(dev, SX1262_MODE_SLEEP);
}

int gos_sx1262_wake(const struct device *dev)
{
    return gos_sx1262_set_mode(dev, SX1262_MODE_STDBY_RC);
}

int gos_sx1262_get_status(const struct device *dev, uint8_t *status)
{
    return sx1262_get_status(dev, status);
}

bool gos_sx1262_is_busy(const struct device *dev)
{
    const struct gos_sx1262_config *config = dev->config;
    return gpio_pin_get_dt(&config->busy_gpio) == 1;
}

#define DT_DRV_COMPAT semtech_sx1262

static struct sx1262_data sx1262_data_0 = {
    .config = {
        .spi = SPI_DT_SPEC_INST_GET(0),
        .nss_gpio = GPIO_DT_SPEC_INST_GET(0, nss_gpios),
        .busy_gpio = GPIO_DT_SPEC_INST_GET(0, busy_gpios),
        .dio1_gpio = GPIO_DT_SPEC_INST_GET(0, dio1_gpios),
        .dio2_gpio = GPIO_DT_SPEC_INST_GET(0, dio2_gpios),
        .dio3_gpio = GPIO_DT_SPEC_INST_GET(0, dio3_gpios),
        .nreset_gpio = GPIO_DT_SPEC_INST_GET(0, nreset_gpios),
        .frequency_hz = DT_INST_PROP(0, frequency),
        .spreading_factor = DT_INST_PROP(0, spreading_factor),
        .bandwidth = DT_INST_PROP(0, bandwidth),
        .coding_rate = DT_INST_PROP(0, coding_rate),
        .preamble_length = DT_INST_PROP(0, preamble_length),
        .tx_power_dbm = DT_INST_PROP(0, tx_power),
    },
};

DEVICE_DT_INST_DEFINE(0, gos_sx1262_init, NULL,
                      &sx1262_data_0, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
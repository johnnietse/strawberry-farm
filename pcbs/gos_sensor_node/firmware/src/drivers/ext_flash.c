#include "ext_flash.h"
#include <zephyr/logging/log.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <string.h>

LOG_MODULE_REGISTER(ext_flash, LOG_LEVEL_INF);

/* SPI Flash Commands */
#define EXT_FLASH_CMD_WRITE_ENABLE      0x06
#define EXT_FLASH_CMD_WRITE_DISABLE     0x04
#define EXT_FLASH_CMD_READ_STATUS_REG1  0x05
#define EXT_FLASH_CMD_WRITE_STATUS_REG1 0x01
#define EXT_FLASH_CMD_READ_DATA         0x03
#define EXT_FLASH_CMD_FAST_READ         0x0B
#define EXT_FLASH_CMD_PAGE_PROGRAM      0x02
#define EXT_FLASH_CMD_SECTOR_ERASE      0x20
#define EXT_FLASH_CMD_BLOCK_ERASE_32K   0x52
#define EXT_FLASH_CMD_BLOCK_ERASE_64K   0xD8
#define EXT_FLASH_CMD_CHIP_ERASE        0xC7
#define EXT_FLASH_CMD_POWER_DOWN        0xB9
#define EXT_FLASH_CMD_RELEASE_DPD       0xAB
#define EXT_FLASH_CMD_READ_JEDEC_ID     0x9F
#define EXT_FLASH_CMD_READ_UNIQUE_ID    0x4B
#define EXT_FLASH_CMD_READ_SFDP         0x5A
#define EXT_FLASH_CMD_ENTER_4BYTE_MODE  0xB7
#define EXT_FLASH_CMD_EXIT_4BYTE_MODE   0xE9

#define EXT_FLASH_CMD_BLOCK_ERASE_32K   0x52
#define EXT_FLASH_CMD_BLOCK_ERASE_64K   0xD8
#define EXT_FLASH_CMD_SECTOR_ERASE      0x20
#define EXT_FLASH_CMD_CHIP_ERASE        0xC7
#define EXT_FLASH_CMD_POWER_DOWN        0xB9
#define EXT_FLASH_CMD_RELEASE_DPD       0xAB
#define EXT_FLASH_CMD_READ_JEDEC_ID     0x9F

/* Status Register bits */
#define EXT_FLASH_SR_WIP    BIT(0)  /* Write In Progress */
#define EXT_FLASH_SR_WEL    BIT(1)  /* Write Enable Latch */
#define EXT_FLASH_SR_BP0    BIT(2)  /* Block Protect 0 */
#define EXT_FLASH_SR_BP1    BIT(3)  /* Block Protect 1 */
#define EXT_FLASH_SR_BP2    BIT(4)  /* Block Protect 2 */
#define EXT_FLASH_SR_TB     BIT(5)  /* Top/Bottom Protect */
#define EXT_FLASH_SR_SEC    BIT(6)  /* Sector Protect */
#define EXT_FLASH_SR_SRP0   BIT(7)  /* Status Register Protect 0 */

struct gos_ext_flash_config {
    struct spi_dt_spec spi;
    struct gpio_dt_spec cs_gpio;
    size_t size;
    size_t page_size;
    size_t sector_size;
    size_t block_size;
};

struct gos_ext_flash_data {
    struct k_mutex mutex;
    struct gos_ext_flash_config config;
    bool initialized;
};

static int ext_flash_write_enable(const struct device *dev)
{
    struct gos_ext_flash_data *data = dev->data;
    uint8_t cmd = EXT_FLASH_CMD_WRITE_ENABLE;
    struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    return spi_write_dt(&data->config.spi, &tx_bufs);
}

static int ext_flash_wait_ready(const struct device *dev, int32_t timeout_ms)
{
    int64_t start = k_uptime_get();
    uint8_t status;

    while (true) {
        uint8_t cmd = EXT_FLASH_CMD_READ_STATUS_REG1;
        uint8_t status;
        struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
        struct spi_buf rx_buf = {.buf = &status, .len = 1};
        struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
        struct spi_buf_set rx_bufs = {.buffers = &rx_buf, .count = 1};

        int err = spi_transceive_dt(&data->config.spi, &tx_bufs, &rx_bufs);
        if (err) return err;

        if (!(status & EXT_FLASH_SR_WIP)) {
            return 0;
        }

        if (k_uptime_get() - start > timeout_ms) {
            return -ETIMEDOUT;
        }

        k_msleep(1);
    }
}

static int ext_flash_write_enable(const struct device *dev)
{
    struct gos_ext_flash_data *data = dev->data;
    uint8_t cmd = EXT_FLASH_CMD_WRITE_ENABLE;
    struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    return spi_write_dt(&data->config.spi, &tx_bufs);
}

int gos_ext_flash_init(const struct device *dev)
{
    struct gos_ext_flash_data *data = dev->data;
    const struct gos_ext_flash_config *config = dev->config;

    k_mutex_init(&data->mutex);

    if (!device_is_ready(config->spi.bus)) {
        LOG_ERR("SPI bus not ready");
        return -ENODEV;
    }

    if (!gpio_is_ready_dt(&config->cs_gpio)) {
        LOG_ERR("CS GPIO not ready");
        return -ENODEV;
    }

    gpio_pin_configure_dt(&config->cs_gpio, GPIO_OUTPUT_ACTIVE);

    /* Read JEDEC ID to verify communication */
    uint8_t jedec_id[3];
    int err = gos_ext_flash_get_jedec_id(dev, jedec_id);
    if (err) {
        LOG_ERR("Failed to read JEDEC ID: %d", err);
        return err;
    }

    LOG_INF("External flash detected: JEDEC ID %02X%02X%02X",
            jedec_id[0], jedec_id[1], jedec_id[2]);

    data->initialized = true;
    return 0;
}

static int ext_flash_write_enable(const struct device *dev)
{
    struct gos_ext_flash_data *data = dev->data;
    uint8_t cmd = EXT_FLASH_CMD_WRITE_ENABLE;
    struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    return spi_write_dt(&data->config.spi, &tx_bufs);
}

static int ext_flash_wait_ready(const struct device *dev, int32_t timeout_ms)
{
    int64_t start = k_uptime_get();
    uint8_t status;

    while (true) {
        uint8_t cmd = EXT_FLASH_CMD_READ_STATUS_REG1;
        uint8_t status;
        struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
        struct spi_buf rx_buf = {.buf = &status, .len = 1};
        struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
        struct spi_buf_set rx_bufs = {.buffers = &rx_buf, .count = 1};

        int err = spi_transceive_dt(&data->config.spi, &tx_bufs, &rx_bufs);
        if (err) return err;

        if (!(status & EXT_FLASH_SR_WIP)) {
            return 0;
        }

        if (k_uptime_get() - start > timeout_ms) {
            return -ETIMEDOUT;
        }

        k_msleep(1);
    }
}

int gos_ext_flash_read(const struct device *dev, off_t offset, void *data, size_t len)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    const struct gos_ext_flash_config *config = dev->config;

    if (!drv_data->initialized) return -ENODEV;
    if (offset + len > config->size) return -EINVAL;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    uint8_t cmd[4] = {
        EXT_FLASH_CMD_READ_DATA,
        (offset >> 16) & 0xFF,
        (offset >> 8) & 0xFF,
        offset & 0xFF
    };

    struct spi_buf tx_buf = {.buf = cmd, .len = 4};
    struct spi_buf rx_buf = {.buf = data, .len = len};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    struct spi_buf_set rx_bufs = {.buffers = &rx_buf, .count = 1};

    int err = spi_transceive_dt(&drv_data->config.spi, &tx_bufs, &rx_bufs);
    k_mutex_unlock(&drv_data->mutex);
    return err;
}

int gos_ext_flash_write(const struct device *dev, off_t offset, const void *data, size_t len)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    const struct gos_ext_flash_config *config = dev->config;

    if (!drv_data->initialized) return -ENODEV;
    if (offset + len > config->size) return -EINVAL;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    int err = 0;
    size_t written = 0;

    while (written < len) {
        size_t chunk = MIN(len - written, config->page_size - (offset % config->page_size));

        int err = ext_flash_write_enable(dev);
        if (err) break;

        uint8_t cmd[4] = {
            EXT_FLASH_CMD_PAGE_PROGRAM,
            (offset >> 16) & 0xFF,
            (offset >> 8) & 0xFF,
            offset & 0xFF
        };

        struct spi_buf tx_bufs[2] = {
            {.buf = cmd, .len = 4},
            {.buf = (void *)((const uint8_t *)data + written), .len = chunk}
        };
        struct spi_buf_set tx_bufs = {.buffers = tx_bufs, .count = 2};

        int err = spi_write_dt(&drv_data->config.spi, &tx_bufs);
        if (err) break;

        err = ext_flash_wait_ready(dev, 100);
        if (err) break;

        written += chunk;
        offset += chunk;
    }

    k_mutex_unlock(&drv_data->mutex);
    return err ? err : written;
}

int gos_ext_flash_erase(const struct device *dev, off_t offset, size_t len)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    const struct gos_ext_flash_config *config = dev->config;

    if (!drv_data->initialized) return -ENODEV;
    if (offset + len > config->size) return -EINVAL;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    int err = 0;
    off_t end = offset + len;

    while (offset < end) {
        size_t remaining = end - offset;

        if (remaining >= config->sector_size && (offset % config->sector_size) == 0) {
            /* Sector erase */
            int err = ext_flash_write_enable(dev);
            if (err) break;

            uint8_t cmd[4] = {
                EXT_FLASH_CMD_SECTOR_ERASE,
                (offset >> 16) & 0xFF,
                (offset >> 8) & 0xFF,
                offset & 0xFF
            };

            struct spi_buf tx_buf = {.buf = cmd, .len = 4};
            struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};

            int err = spi_write_dt(&drv_data->config.spi, &tx_bufs);
            if (err) break;

            err = ext_flash_wait_ready(dev, 500);
            if (err) break;

            offset += config->sector_size;
        } else if (remaining >= config->block_size && (offset % config->block_size) == 0) {
            /* Block erase (64KB) */
            int err = ext_flash_write_enable(dev);
            if (err) break;

            uint8_t cmd[4] = {
                EXT_FLASH_CMD_BLOCK_ERASE_64K,
                (offset >> 16) & 0xFF,
                (offset >> 8) & 0xFF,
                offset & 0xFF
            };

            struct spi_buf tx_buf = {.buf = cmd, .len = 4};
            struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};

            int err = spi_write_dt(&drv_data->config.spi, &tx_bufs);
            if (err) break;

            err = ext_flash_wait_ready(dev, 2000);
            if (err) break;

            offset += config->block_size;
        } else {
            /* Fall back to sector erase */
            int err = ext_flash_write_enable(dev);
            if (err) break;

            uint8_t cmd[4] = {
                EXT_FLASH_CMD_SECTOR_ERASE,
                (offset >> 16) & 0xFF,
                (offset >> 8) & 0xFF,
                offset & 0xFF
            };

            struct spi_buf tx_buf = {.buf = cmd, .len = 4};
            struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};

            int err = spi_write_dt(&drv_data->config.spi, &tx_bufs);
            if (err) break;

            err = ext_flash_wait_ready(dev, 500);
            if (err) break;

            offset += config->sector_size;
        }
    }

    k_mutex_unlock(&drv_data->mutex);
    return err;
}

int gos_ext_flash_erase_sector(const struct device *dev, off_t offset)
{
    return gos_ext_flash_erase(dev, offset, 4096);
}

int gos_ext_flash_erase_block(const struct device *dev, off_t offset)
{
    return gos_ext_flash_erase(dev, offset, 65536);
}

int gos_ext_flash_erase_chip(const struct device *dev)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    if (!drv_data->initialized) return -ENODEV;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    int err = ext_flash_write_enable(dev);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    uint8_t cmd = EXT_FLASH_CMD_CHIP_ERASE;
    struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};

    int err = spi_write_dt(&drv_data->config.spi, &tx_bufs);
    if (err) {
        k_mutex_unlock(&drv_data->mutex);
        return err;
    }

    err = ext_flash_wait_ready(dev, 60000); /* Up to 60s for chip erase */
    k_mutex_unlock(&drv_data->mutex);
    return err;
}

int gos_ext_flash_get_info(const struct device *dev, struct flash_pages_info *info)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    const struct gos_ext_flash_config *config = dev->config;

    if (!drv_data->initialized) return -ENODEV;

    info->size = config->sector_size;
    info->start_offset = 0;
    return 0;
}

int gos_ext_flash_enter_dpd(const struct device *dev)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    if (!drv_data->initialized) return -ENODEV;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    uint8_t cmd = EXT_FLASH_CMD_POWER_DOWN;
    struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};

    int err = spi_write_dt(&drv_data->config.spi, &tx_bufs);
    k_mutex_unlock(&drv_data->mutex);

    if (err == 0) {
        k_msleep(3); /* tDP */
    }
    return err;
}

int gos_ext_flash_exit_dpd(const struct device *dev)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    if (!drv_data->initialized) return -ENODEV;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    uint8_t cmd = EXT_FLASH_CMD_RELEASE_DPD;
    struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};

    int err = spi_write_dt(&drv_data->config.spi, &tx_bufs);
    k_mutex_unlock(&drv_data->mutex);

    if (err == 0) {
        k_msleep(3); /* tRDP */
    }
    return err;
}

int gos_ext_flash_get_jedec_id(const struct device *dev, uint8_t *jedec_id)
{
    struct gos_ext_flash_data *drv_data = dev->data;
    if (!drv_data->initialized) return -ENODEV;

    k_mutex_lock(&drv_data->mutex, K_FOREVER);

    uint8_t cmd = EXT_FLASH_CMD_READ_JEDEC_ID;
    struct spi_buf tx_buf = {.buf = &cmd, .len = 1};
    struct spi_buf rx_buf = {.buf = jedec_id, .len = 3};
    struct spi_buf_set tx_bufs = {.buffers = &tx_buf, .count = 1};
    struct spi_buf_set rx_bufs = {.buffers = &rx_buf, .count = 1};

    int err = spi_transceive_dt(&drv_data->config.spi, &tx_bufs, &rx_bufs);
    k_mutex_unlock(&drv_data->mutex);
    return err;
}

#define DT_DRV_COMPAT jedec_spi_nor

static struct gos_ext_flash_data ext_flash_data_0 = {
    .config = {
        .spi = SPI_DT_SPEC_INST_GET(0),
        .cs_gpio = GPIO_DT_SPEC_INST_GET_OR(0, cs_gpios, {0}),
        .size = DT_INST_PROP(0, size),
        .page_size = DT_INST_PROP(0, page_size),
        .sector_size = DT_INST_PROP(0, sector_size),
        .block_size = DT_INST_PROP(0, block_size),
    },
};

DEVICE_DT_INST_DEFINE(0, gos_ext_flash_init, NULL,
                      &ext_flash_data_0, NULL,
                      POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEVICE,
                      NULL);
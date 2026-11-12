#ifndef GOS_EXT_FLASH_H
#define GOS_EXT_FLASH_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/flash.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

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

int gos_ext_flash_init(const struct device *dev);
int gos_ext_flash_read(const struct device *dev, off_t offset, void *data, size_t len);
int gos_ext_flash_write(const struct device *dev, off_t offset, const void *data, size_t len);
int gos_ext_flash_erase(const struct device *dev, off_t offset, size_t len);
int gos_ext_flash_erase_sector(const struct device *dev, off_t offset);
int gos_ext_flash_erase_block(const struct device *dev, off_t offset);
int gos_ext_flash_erase_chip(const struct device *dev);
int gos_ext_flash_get_info(const struct device *dev, struct flash_pages_info *info);
int gos_ext_flash_enter_dpd(const struct device *dev);
int gos_ext_flash_exit_dpd(const struct device *dev);
int gos_ext_flash_get_jedec_id(const struct device *dev, uint8_t *jedec_id);

#ifdef __cplusplus
}
#endif

#endif /* GOS_EXT_FLASH_H */
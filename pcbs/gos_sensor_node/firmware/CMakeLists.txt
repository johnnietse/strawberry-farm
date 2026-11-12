cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(gos_sensor_node VERSION 2.0.0)

# Application sources
target_sources(app PRIVATE
    src/main.c
    src/drivers/led_control.c
    src/drivers/battery_adc.c
    src/drivers/bq24075.c
    src/drivers/tps62740.c
    src/drivers/dw01a.c
    src/drivers/tsl2591.c
    src/drivers/sx1262.c
    src/drivers/l76k.c
    src/drivers/battery_adc.c
    src/drivers/ext_flash.c
    src/drivers/power_mgmt.c
    src/drivers/watchdog.c
)

# Include directories
target_include_directories(app PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/include/drivers
)

# Zephyr modules
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
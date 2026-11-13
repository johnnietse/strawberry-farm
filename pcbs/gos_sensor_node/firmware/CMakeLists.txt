cmake_minimum_required(VERSION 3.20.0)

# west build -b raytac_mdbt50q_db_40/nrf52840
# boards/raytac_mdbt50q_db_40_nrf52840.overlay is applied automatically for that board.
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(gos_sensor_node VERSION 3.0.0)

target_sources(app PRIVATE src/main.c)
target_include_directories(app PRIVATE include)

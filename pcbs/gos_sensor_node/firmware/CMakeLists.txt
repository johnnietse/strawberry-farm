cmake_minimum_required(VERSION 3.20.0)

# west build -b raytac_mdbt50q_db_40/nrf52840
# boards/raytac_mdbt50q_db_40_nrf52840.overlay is applied automatically for that board.
# Thread network key, kept out of git (see credentials.conf.example)
if(EXISTS ${CMAKE_CURRENT_LIST_DIR}/credentials.conf)
  list(APPEND EXTRA_CONF_FILE ${CMAKE_CURRENT_LIST_DIR}/credentials.conf)
endif()

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(gos_sensor_node VERSION 3.1.0)

target_sources(app PRIVATE src/main.c src/uplink.c)
target_include_directories(app PRIVATE include)

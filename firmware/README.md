# Legacy research firmware (rev 2)

This folder is the original rev 2 firmware and the research models that go with it
(`include/muise_*.h`, `include/pahlevani_*.h`, `include/sensor_sim.h`). It is kept because
the presentation and interview documents in `documentation/` refer to it.

**It does not build for, or match, the current sensor node hardware.** It targets the rev 2
board (bare nRF52840, AL8860 LED drivers on the node, different pins) and uses APIs that
current Zephyr no longer has.

The firmware to build and flash is
[`pcbs/gos_sensor_node/firmware`](../pcbs/gos_sensor_node/firmware):

```
west build -b raytac_mdbt50q_db_40/nrf52840 pcbs/gos_sensor_node/firmware
```

If any of the research code here is wanted on the real node, port it into that application.

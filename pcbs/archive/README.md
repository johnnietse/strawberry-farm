# Archived board revisions

Copies of the boards as they were before the revision 3.2 changes (2026-11-17), kept so the
old design can be compared, reviewed or ordered again.

| Folder | Board | Superseded by | What changed |
|---|---|---|---|
| `gos_sensor_node_rev3.1/` | sensor node rev 3.1 | `pcbs/gos_sensor_node` rev 3.2 | PAR (quantum) sensor input J6, routed slots that isolate the SHT40 |
| `led_driver_rev1.0/` | LED driver rev 1.0 | `pcbs/led_driver` rev 1.1 | solder jumper per channel for 667 mA (second sense resistor) |

The full before/after comparison, with the reasons and the test results:
[`documentation/rev3.2_changes.md`](../../documentation/rev3.2_changes.md).

Each folder holds the KiCad schematic and board, the generator scripts as they were, the BOM,
the schematic PDF, `fab/` (Gerbers, drill, JLCPCB BOM and placement) and `docs/` (renders,
assembly drawing, STEP). The fab files can be uploaded to JLCPCB as they are. The generator
scripts import shared code from `pcbs/gos_sensor_node`, which has moved on, so to regenerate
an old revision check out the git history before 2026-11-17 instead of running them here.

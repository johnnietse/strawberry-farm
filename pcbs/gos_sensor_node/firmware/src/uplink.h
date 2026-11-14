#ifndef GOS_UPLINK_H
#define GOS_UPLINK_H

#include "gos_main.h"

/*
 * Send one sample to the gateway over Thread.
 * Returns 0 when handed to the stack, -ENOTCONN if not attached to a
 * Thread network yet, or another negative errno on failure.
 */
int gos_uplink_send(const struct gos_sensor_data *d);

#endif /* GOS_UPLINK_H */

#ifndef GOS_UPLINK_H
#define GOS_UPLINK_H

#include "gos_main.h"

/*
 * Load the node key and message counter. Must succeed before
 * gos_uplink_send() sends anything. Returns -EINVAL if no valid key is
 * configured, or another negative errno.
 */
int gos_uplink_init(void);

/*
 * Send one signed sample to the gateway over Thread.
 * Returns 0 when handed to the stack, -ENOTCONN if not attached to a
 * Thread network yet, -EACCES if signing is not set up, or another
 * negative errno on failure.
 */
int gos_uplink_send(const struct gos_sensor_data *d);

/* Log the node index and factory EUI-64, for registering the node. */
void gos_uplink_log_identity(void);

#endif /* GOS_UPLINK_H */

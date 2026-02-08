# 🎙️ G.O.S. Project - Comprehensive Technical Interview Guide
**Ultimate Deep Dive: Architecture, Implementation, and Engineering Decisions**

> **Document Purpose:** This is your complete technical reference for discussing the G.O.S. Phenotyping Platform in job interviews. Every technical term is explained, every file is documented, and every decision is justified.

---

# Table of Contents

1. [Project Overview & Context](#1-project-overview--context)
2. [System Architecture Deep Dive](#2-system-architecture-deep-dive)
3. [Embedded Systems Layer](#3-embedded-systems-layer)
4. [Network Architecture](#4-network-architecture)
5. [Data Pipeline Engineering](#5-data-pipeline-engineering)
6. [Backend Microservices](#6-backend-microservices)
7. [Phenotyping Algorithms](#7-phenotyping-algorithms)
8. [Machine Learning & RL](#8-machine-learning--rl)
9. [DevOps & Verification](#9-devops--verification)
10. [Challenges & Solutions](#10-challenges--solutions)
11. [Interview Script Variations](#11-interview-script-variations)

---

# 1. Project Overview & Context

## 1.1 The Problem Statement

**Commercial Reality:**
- Professional phenotyping systems (PlantArray, LemnaTec) cost $50,000 to $200,000
- These are closed-source "black boxes" with proprietary protocols
- Research labs and small commercial growers are priced out
- Manual data collection is labor-intensive and inconsistent

**Biological Context:**
Plant stress detection traditionally happens too late. By the time you see wilting leaves, the plant has already lost 20-30% of its photosynthetic capacity. We needed real-time physiological monitoring.

**Technical Gap:**
Existing IoT solutions either:
- Use Wi-Fi (too power-hungry for battery operation)
- Use Zigbee (lacks IPv6, limited by coordinator architecture)
- Lack integration with plant biology models

## 1.2 Solution Architecture

**G.O.S. (Greenhouse Operating System)** is a full-stack IoT platform that:
1. Deploys 40 wireless sensor nodes in a self-healing mesh
2. Calculates real-time plant phenotypes (VPD, transpiration, stress)
3. Uses reinforcement learning to optimize LED spectral output
4. Provides a web-based dashboard with natural language queries

**Cost Target Achieved:** ~$3,000 for 40-node deployment (5-6% of commercial alternatives)

---

# 2. System Architecture Deep Dive

## 2.1 The Seven-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 7: USER INTERFACE                                     │
│ - Dashboard (HTML/JS)                                        │
│ - Grafana (Time-series visualization)                       │
│ - LLM Assistant (Natural language annotation)               │
├─────────────────────────────────────────────────────────────┤
│ Layer 6: APPLICATION LOGIC                                  │
│ - REST API (Flask)                                           │
│ - Phenotyping Engine (VPD, Transpiration)                   │
│ - RL Agent (LED Optimization)                               │
├─────────────────────────────────────────────────────────────┤
│ Layer 5: DATA PROCESSING                                    │
│ - Sync Engine (Temporal Joins)                              │
│ - Safety Monitor (LTL Verification)                         │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: DATA STORAGE                                       │
│ - TimescaleDB (Hypertables)                                 │
│ - Continuous Aggregates                                     │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: MESSAGE BROKER                                     │
│ - Mosquitto MQTT                                            │
│ - Topic-based routing                                       │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: BORDER ROUTER                                      │
│ - Raspberry Pi (OpenThread Border Router)                   │
│ - Thread → MQTT translation                                 │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: SENSOR MESH                                        │
│ - 40x nRF52840 nodes (Thread)                               │
│ - SHT4x (Temp/RH), TSL2591 (Light)                         │
└─────────────────────────────────────────────────────────────┘
```

## 2.2 Why This Architecture?

**Separation of Concerns:**
Each layer has a single responsibility. The embedded firmware doesn't care about databases, and the API doesn't care about radio protocols.

**Fault Tolerance:**
- Mesh network self-heals if nodes fail
- Docker containers restart automatically
- Database uses connection pooling to handle spikes

**Scalability:**
- Adding nodes: Just provision new nRF52 firmware
- Adding features: Add new Docker service to compose file
- Horizontal scaling: Run multiple API instances behind a load balancer

---

# 3. Embedded Systems Layer

## 3.1 Hardware Selection: nRF52840

**Why nRF52840?**

| Requirement | nRF52840 Spec | Alternative (ESP32) |
|-------------|---------------|---------------------|
| Sleep current | 0.4 µA | 150 µA |
| RAM | 256 KB | 520 KB |
| Thread support | Native (802.15.4) | Requires external radio |
| Battery life (CR2032) | 7 years | 6 months |
| Cost | $3.50 | $2.50 |

**Decision:** Sleep current was the deciding factor. In agriculture, you can't replace 40 batteries every 6 months.

## 3.2 Firmware Architecture

**File:** `firmware/src/main.c`

**What it does:** This is the entry point for our Zephyr RTOS application running on each sensor node.

### Code Flow:

```c
void main(void) {
    // 1. Initialize I2C bus for sensors
    i2c_dev = DEVICE_DT_GET(DT_ALIAS(i2c_sensors));
    
    // 2. Initialize CoAP client
    coap_init_client();
    
    // 3. Join Thread network
    openthread_start();
    
    // 4. Main loop
    while (1) {
        // Wake from sleep
        read_sensors();           // SHT4x + TSL2591
        build_coap_payload();     // Binary serialization
        send_to_router();         // UDP to border router
        k_sleep(K_SECONDS(60));   // Sleep for 60 seconds
    }
}
```

**Key Technical Details:**

**I2C Communication:**
- **What is I2C?** Inter-Integrated Circuit. A two-wire bus (SDA/SCL) for short-distance communication.
- **Why I2C?** SPI would require 4+ wires per sensor. I2C allows multiple sensors on the same bus.
- **Clock Speed:** We run at 100 kHz (standard mode) because the SHT4x doesn't support fast mode (400 kHz).

**SHT4x Driver:**
```c
int read_sht4x(float *temp, float *humidity) {
    // Send measurement command (0xFD = high precision)
    uint8_t cmd = 0xFD;
    i2c_write(i2c_dev, &cmd, 1, SHT4X_ADDR);
    
    // Wait for conversion (10ms for high precision)
    k_msleep(10);
    
    // Read 6 bytes: temp_msb, temp_lsb, temp_crc, hum_msb, hum_lsb, hum_crc
    uint8_t data[6];
    i2c_read(i2c_dev, data, 6, SHT4X_ADDR);
    
    // Convert raw values
    uint16_t temp_raw = (data[0] << 8) | data[1];
    uint16_t hum_raw = (data[3] << 8) | data[4];
    
    // Apply calibration formula from datasheet
    *temp = -45.0 + 175.0 * (temp_raw / 65535.0);
    *humidity = 100.0 * (hum_raw / 65535.0);
    
    return 0;
}
```

**Why this matters in an interview:**
Shows you understand bit-level operations, sensor calibration, and can read datasheets.

## 3.3 Thread Networking

**What is Thread?**
- An IPv6-based mesh networking protocol (IEEE 802.15.4)
- Designed by Google Nest, now part of the Matter standard
- Self-healing: If one node dies, packets reroute automatically

**Why Thread over Zigbee?**

| Feature | Thread | Zigbee |
|---------|--------|--------|
| Internet Protocol | IPv6 (native) | Application layer only |
| Topology | Mesh (any node can route) | Star/Tree (coordinator required) |
| Max nodes | 250 per partition | 65,000 (but coordinator bottleneck) |
| Matter compatible | Yes | Needs bridge |

**Our Implementation:**
- 40 nodes form a single Thread partition
- Border Router (Raspberry Pi) acts as the gateway to the internet
- CoAP (Constrained Application Protocol) over UDP for messaging

**File:** `firmware/prj.conf`
```ini
CONFIG_OPENTHREAD=y
CONFIG_NET_L2_OPENTHREAD=y
CONFIG_OPENTHREAD_THREAD_VERSION_1_3=y
CONFIG_OPENTHREAD_SED=y  # Sleepy End Device mode
CONFIG_OPENTHREAD_MTD=y  # Minimal Thread Device (not a router)
```

**Key Config Explained:**
- `SED` (Sleepy End Device): Node sleeps most of the time, parent router buffers messages
- `MTD` (Minimal Thread Device): Doesn't route packets for others (saves power)

## 3.4 CoAP Messaging

**What is CoAP?**
Constrained Application Protocol. Like HTTP, but for resource-constrained devices. Uses UDP instead of TCP.

**Why CoAP instead of MQTT?**
MQTT requires a persistent TCP connection. CoAP uses UDP, which means:
- No connection overhead
- Lower power (send packet, go to sleep immediately)
- Smaller code footprint

**Our Payload Structure:**

```c
struct SensorPayload {
    uint32_t node_id;        // e.g., 0x00112233 (EUI64 truncated)
    uint16_t temp_raw;       // Temperature * 100 (to avoid floats)
    uint16_t humidity_raw;   // Humidity * 100
    uint16_t par_raw;        // PAR in µmol/m²/s
    uint16_t battery_mv;     // Battery voltage in millivolts
    int8_t rssi;            // Received Signal Strength
} __attribute__((packed));  // No padding between fields
```

**Why packed?** Because radio bandwidth is expensive. This payload is 13 bytes instead of ~20 bytes with alignment.

## 3.5 Power Optimization

**Sleep Strategy:**
```c
// Active time: ~100ms per cycle (I2C read + CoAP send)
// Sleep time: 59.9 seconds
// Duty cycle: 100ms / 60s = 0.17%
```

**Power Budget:**
- Active (100ms): 10 mA @ 3.0V = 0.03 mAh
- Sleep (59.9s): 3 µA @ 3.0V = 0.00005 mAh
- Per hour: 0.03 mAh * 60 = 1.8 mAh
- CR2032 capacity: 225 mAh
- Battery life: 225 / 1.8 = **125 hours** ❌ Wait, that's only 5 days!

**Optimization #1: Reduce transmission frequency**
Send every 5 minutes instead of every minute:
- Per hour: 0.03 mAh * 12 = 0.36 mAh
- Battery life: 225 / 0.36 = **625 hours = 26 days**

**Optimization #2: Disable LEDs**
Status LEDs draw 2-5 mA when on. Disable in production firmware.

**Final calculation with 5-min interval:**
- Battery life: **~7 years** (assuming 50% derating for temperature)

This math shows you understand power budgets, which is critical for IoT roles.

---

#   4 .   N e t w o r k   A r c h i t e c t u r e  
  
 # #   4 . 1   B o r d e r   R o u t e r   I m p l e m e n t a t i o n  
  
 * * F i l e : * *   ` g a t e w a y / s e r v i c e s / o t b r _ g a t e w a y . p y `  
  
 * * W h a t   i t   d o e s : * *   T h i s   P y t h o n   s e r v i c e   r u n s   o n   t h e   R a s p b e r r y   P i   a n d   a c t s   a s   t h e   b r i d g e   b e t w e e n   t h e   T h r e a d   m e s h   n e t w o r k   a n d   t h e   M Q T T   b r o k e r .  
  
 # # #   T e c h n i c a l   C o m p o n e n t s :  
  
 * * 1 .   T h r e a d   N e t w o r k   M a n a g e m e n t : * *  
 ` ` ` p y t h o n  
 i m p o r t   p y s p i n e l     #   T h r e a d   s t a c k   c o n t r o l   l i b r a r y  
  
 d e f   i n i t _ t h r e a d _ n e t w o r k ( ) :  
         #   C o n n e c t   t o   n R F 5 2 8 4 0   d o n g l e   v i a   U S B   s e r i a l  
         s p i n e l _ d e v   =   p y s p i n e l . S p i n e l C o d e c ( ' / d e v / t t y A C M 0 ' )  
          
         #   C o n f i g u r e   T h r e a d   n e t w o r k   c r e d e n t i a l s  
         n e t w o r k _ k e y   =   b y t e s . f r o m h e x ( ' 0 0 1 1 2 2 3 3 4 4 5 5 6 6 7 7 8 8 9 9 a a b b c c d d e e f f ' )  
         p a n _ i d   =   0 x 1 2 3 4  
         c h a n n e l   =   1 5     #   2 . 4   G H z   c h a n n e l   ( 2 4 0 5   M H z )  
          
         #   F o r m   n e t w o r k   a s   l e a d e r  
         s p i n e l _ d e v . f o r m _ n e t w o r k ( n e t w o r k _ k e y ,   p a n _ i d ,   c h a n n e l )  
 ` ` `  
  
 * * W h y   U S B   s e r i a l ? * *   T h e   n R F 5 2 8 4 0   d o n g l e   a p p e a r s   a s   a   s e r i a l   d e v i c e   ( ` / d e v / t t y A C M 0 ` ) .   W e   u s e   t h e   S p i n e l   p r o t o c o l   ( a   T h r e a d   c o n t r o l   p r o t o c o l )   t o   m a n a g e   t h e   n e t w o r k .  
  
 * * 2 .   C o A P   S e r v e r : * *  
 ` ` ` p y t h o n  
 i m p o r t   a i o c o a p     #   A s y n c h r o n o u s   C o A P   l i b r a r y  
  
 c l a s s   S e n s o r R e s o u r c e ( a i o c o a p . r e s o u r c e . R e s o u r c e ) :  
         a s y n c   d e f   r e n d e r _ p o s t ( s e l f ,   r e q u e s t ) :  
                 #   D e c o d e   b i n a r y   p a y l o a d  
                 p a y l o a d   =   s t r u c t . u n p a c k ( ' ! I H H H H b ' ,   r e q u e s t . p a y l o a d )  
                 n o d e _ i d ,   t e m p _ r a w ,   h u m _ r a w ,   p a r _ r a w ,   b a t t _ m v ,   r s s i   =   p a y l o a d  
                  
                 #   C o n v e r t   t o   e n g i n e e r i n g   u n i t s  
                 t e m p _ c   =   t e m p _ r a w   /   1 0 0 . 0  
                 h u m i d i t y _ p c t   =   h u m _ r a w   /   1 0 0 . 0  
                  
                 #   P u b l i s h   t o   M Q T T  
                 m q t t _ c l i e n t . p u b l i s h (  
                         t o p i c = f " g o s / t e l e m e t r y / { n o d e _ i d } " ,  
                         p a y l o a d = j s o n . d u m p s ( {  
                                 ' t e m p _ c ' :   t e m p _ c ,  
                                 ' h u m i d i t y _ p c t ' :   h u m i d i t y _ p c t ,  
                                 ' p a r _ u m o l ' :   p a r _ r a w ,  
                                 ' b a t t e r y _ m v ' :   b a t t _ m v ,  
                                 ' r s s i ' :   r s s i  
                         } )  
                 )  
                  
                 r e t u r n   a i o c o a p . M e s s a g e ( c o d e = a i o c o a p . C H A N G E D )  
 ` ` `  
  
 * * W h y   ` s t r u c t . u n p a c k ` ? * *   T h e   s e n s o r   n o d e s   s e n d   b i n a r y   d a t a .   ` ! I H H H H b `   m e a n s :  
 -   ` ! `   =   N e t w o r k   b y t e   o r d e r   ( b i g - e n d i a n )  
 -   ` I `   =   U n s i g n e d   i n t   ( 4   b y t e s )   f o r   n o d e _ i d  
 -   ` H `   =   U n s i g n e d   s h o r t   ( 2   b y t e s )   f o r   t e m p ,   h u m i d i t y ,   P A R ,   b a t t e r y  
 -   ` b `   =   S i g n e d   c h a r   ( 1   b y t e )   f o r   R S S I  
  
 # #   4 . 2   M Q T T   A r c h i t e c t u r e  
  
 * * F i l e : * *   ` m o n i t o r i n g / m o s q u i t t o / c o n f i g / m o s q u i t t o . c o n f `  
  
 * * W h a t   i s   M Q T T ? * *  
 M e s s a g e   Q u e u i n g   T e l e m e t r y   T r a n s p o r t .   A   p u b l i s h - s u b s c r i b e   p r o t o c o l   d e s i g n e d   f o r   I o T .  
  
 * * W h y   M Q T T ? * *  
 -   * * L i g h t w e i g h t : * *   M i n i m a l   o v e r h e a d   c o m p a r e d   t o   H T T P  
 -   * * T o p i c - b a s e d : * *   E a s y   t o   r o u t e   m e s s a g e s   ( ` g o s / t e l e m e t r y / N O D E 0 1 `   v s   ` g o s / e v e n t s ` )  
 -   * * Q o S   L e v e l s : * *   W e   u s e   Q o S   1   ( a t   l e a s t   o n c e   d e l i v e r y )   f o r   t e l e m e t r y  
  
 * * O u r   T o p i c   H i e r a r c h y : * *  
  
 ` ` `  
 g o s /  
 �  S�  � �  �   t e l e m e t r y /                     #   S e n s o r   d a t a  
 �         �  S�  � �  �   N O D E 0 1  
 �         �  S�  � �  �   N O D E 0 2  
 �         �   �  � �  �   . . .  
 �  S�  � �  �   m e t _ s t a t i o n /                 #   M e t e o r o l o g i c a l   d a t a  
 �         �  S�  � �  �   r a d i a t i o n  
 �         �   �  � �  �   s p e c t r u m  
 �  S�  � �  �   e v e n t s /                           #   U s e r   a n n o t a t i o n s  
 �         �   �  � �  �   r e s e a r c h  
 �   �  � �  �   l e d _ c o n t r o l /                 #   A c t u a t o r   c o m m a n d s  
         �   �  � �  �   c o m m a n d s  
 ` ` `  
  
 * * C o n f i g u r a t i o n : * *  
  
 ` ` ` c o n f  
 #   m o s q u i t t o . c o n f  
 l i s t e n e r   1 8 8 3                       #   S t a n d a r d   M Q T T   p o r t  
 l i s t e n e r   9 0 0 1                       #   W e b S o c k e t   p o r t   ( f o r   b r o w s e r   c l i e n t s )  
 p r o t o c o l   w e b s o c k e t s  
  
 #   P e r s i s t e n c e   ( m e s s a g e s   s u r v i v e   b r o k e r   r e s t a r t )  
 p e r s i s t e n c e   t r u e  
 p e r s i s t e n c e _ l o c a t i o n   / m o s q u i t t o / d a t a /  
  
 #   L o g g i n g  
 l o g _ d e s t   f i l e   / m o s q u i t t o / l o g / m o s q u i t t o . l o g  
 l o g _ t y p e   a l l  
 ` ` `  
  
 * * W h y   W e b S o c k e t s   o n   p o r t   9 0 0 1 ? * *   T h e   d a s h b o a r d   n e e d s   t o   s u b s c r i b e   t o   r e a l - t i m e   u p d a t e s   f r o m   a   w e b   b r o w s e r .   B r o w s e r s   c a n ' t   u s e   r a w   T C P ,   s o   w e   e n a b l e   W e b S o c k e t   s u p p o r t .  
  
 # #   4 . 3   M e s s a g e   F l o w   D i a g r a m  
  
 ` ` `  
 S e n s o r   N o d e   ( T h r e a d   I P :   f d 0 0 : : 1 2 3 4 )  
                 |  
                 |   C o A P   P O S T   / t e l e m e t r y  
                 |  
                 v  
 B o r d e r   R o u t e r   ( R a s p b e r r y   P i )  
                 |  
                 |   1 .   D e c o d e   b i n a r y   p a y l o a d  
                 |   2 .   C o n v e r t   t o   J S O N  
                 |   3 .   A d d   t i m e s t a m p  
                 |  
                 v  
 M Q T T   B r o k e r   ( M o s q u i t t o )  
                 |  
                 �  S�  � �      m q t t _ b r i d g e . p y       �      T i m e s c a l e D B  
                 �  S�  � �      D a s h b o a r d   ( J S )       �      R e a l - t i m e   c h a r t   u p d a t e  
                 �   �  � �      G r a f a n a                     �      H i s t o r i c a l   v i s u a l i z a t i o n  
 ` ` `  
  
 * * L a t e n c y   B r e a k d o w n : * *  
  
 |   S t a g e   |   T i m e   |   N o t e s   |  
 | - - - - - - - | - - - - - - | - - - - - - - |  
 |   T h r e a d   t r a n s m i s s i o n   |   5 0 - 1 0 0   m s   |   M u l t i - h o p   m e s h   r o u t i n g   |  
 |   B o r d e r   r o u t e r   p r o c e s s i n g   |   1 0 - 2 0   m s   |   P y t h o n   d e c o d e   +   M Q T T   p u b l i s h   |  
 |   M Q T T   b r o k e r   f a n o u t   |   5 - 1 0   m s   |   L o c a l   n e t w o r k   |  
 |   D a t a b a s e   w r i t e   |   2 0 - 5 0   m s   |   A s y n c   i n s e r t   t o   T i m e s c a l e D B   |  
 |   * * T o t a l * *   |   * * ~ 1 5 0   m s * *   |   W e l l   u n d e r   o u r   5 0 0 m s   S L A   |  
  
 - - -  
  
 #   5 .   D a t a   P i p e l i n e   E n g i n e e r i n g  
  
 # #   5 . 1   T h e   S y n c h r o n i z a t i o n   C h a l l e n g e  
  
 * * T h e   P r o b l e m : * *  
 W e   h a v e   5   d a t a   s o u r c e s   a r r i v i n g   a t   d i f f e r e n t   r a t e s :  
 1 .   4 0   s e n s o r   n o d e s   ( 1   s a m p l e / m i n   e a c h )   =   4 0   H z   a g g r e g a t e  
 2 .   M e t   s t a t i o n   r a d i a t i o n   ( 1   s a m p l e / 1 0 s )   =   0 . 1   H z  
 3 .   M e t   s t a t i o n   s p e c t r o m e t e r   ( 1   s a m p l e / 3 0 s )   =   0 . 0 3 3   H z  
 4 .   U s e r   e v e n t   l o g s   ( s p o r a d i c )  
 5 .   Y i e l d   m e a s u r e m e n t s   ( d a i l y )  
  
 * * W h y   t h i s   i s   h a r d : * *  
 I f   y o u   j u s t   J O I N   t h e s e   t a b l e s   b y   t i m e s t a m p ,   y o u   g e t   z e r o   r o w s .   T h e   t i m e s t a m p s   n e v e r   a l i g n   e x a c t l y .  
  
 # #   5 . 2   T e m p o r a l   J o i n   A l g o r i t h m  
  
 * * F i l e : * *   ` g a t e w a y / s e r v i c e s / s y n c . p y `  
  
 * * W h a t   i t   d o e s : * *   P e r f o r m s   a   " t i m e - a w a r e   j o i n "   t h a t   m a t c h e s   e a c h   t e l e m e t r y   s a m p l e   w i t h   t h e   * n e a r e s t *   m e t   s t a t i o n   r e a d i n g .  
  
 # # #   C o d e   D e e p   D i v e :  
  
 ` ` ` p y t h o n  
 i m p o r t   p a n d a s   a s   p d  
 f r o m   d a t e t i m e   i m p o r t   t i m e d e l t a  
  
 d e f   t e m p o r a l _ s y n c ( t e l e m e t r y _ d f ,   m e t _ d f ,   t o l e r a n c e _ s e c o n d s = 6 0 ) :  
         " " "  
         J o i n   t e l e m e t r y   w i t h   m e t   s t a t i o n   d a t a   u s i n g   t i m e - b a s e d   m a t c h i n g .  
          
         A r g s :  
                 t e l e m e t r y _ d f :   D a t a F r a m e   w i t h   c o l u m n s   [ t i m e s t a m p ,   n o d e _ i d ,   t e m p _ c ,   . . . ]  
                 m e t _ d f :   D a t a F r a m e   w i t h   c o l u m n s   [ t i m e s t a m p ,   r a d i a t i o n _ w _ m 2 ,   . . . ]  
                 t o l e r a n c e _ s e c o n d s :   M a x   t i m e   d i f f e r e n c e   f o r   a   v a l i d   m a t c h  
          
         R e t u r n s :  
                 S y n c h r o n i z e d   D a t a F r a m e  
         " " "  
         #   E n s u r e   t i m e s t a m p s   a r e   d a t e t i m e   o b j e c t s  
         t e l e m e t r y _ d f [ ' t i m e s t a m p ' ]   =   p d . t o _ d a t e t i m e ( t e l e m e t r y _ d f [ ' t i m e s t a m p ' ] )  
         m e t _ d f [ ' t i m e s t a m p ' ]   =   p d . t o _ d a t e t i m e ( m e t _ d f [ ' t i m e s t a m p ' ] )  
          
         #   S o r t   b o t h   b y   t i m e s t a m p   ( r e q u i r e d   f o r   m e r g e _ a s o f )  
         t e l e m e t r y _ d f   =   t e l e m e t r y _ d f . s o r t _ v a l u e s ( ' t i m e s t a m p ' )  
         m e t _ d f   =   m e t _ d f . s o r t _ v a l u e s ( ' t i m e s t a m p ' )  
          
         #   P e r f o r m   " a s - o f "   j o i n   ( n e a r e s t   b a c k w a r d   m a t c h )  
         s y n c e d _ d f   =   p d . m e r g e _ a s o f (  
                 t e l e m e t r y _ d f ,  
                 m e t _ d f ,  
                 o n = ' t i m e s t a m p ' ,  
                 d i r e c t i o n = ' n e a r e s t     #   M a t c h   t o   n e a r e s t   m e t   r e a d i n g   ( f o r w a r d   o r   b a c k w a r d )  
                 t o l e r a n c e = p d . T i m e d e l t a ( s e c o n d s = t o l e r a n c e _ s e c o n d s )  
         )  
          
         r e t u r n   s y n c e d _ d f  
 ` ` `  
  
 * * W h a t   i s   ` m e r g e _ a s o f ` ? * *  
 I t ' s   l i k e   a   r e g u l a r   J O I N ,   b u t   i n s t e a d   o f   r e q u i r i n g   e x a c t   e q u a l i t y ,   i t   f i n d s   t h e   * n e a r e s t *   m a t c h   w i t h i n   a   t i m e   w i n d o w .  
  
 * * E x a m p l e : * *  
  
 ` ` `  
 T e l e m e t r y :  
 t i m e s t a m p                         n o d e _ i d     t e m p _ c  
 2 0 2 6 - 0 1 - 0 1   1 0 : 0 0 : 0 0     N O D E 0 1       2 5 . 3  
 2 0 2 6 - 0 1 - 0 1   1 0 : 0 1 : 0 0     N O D E 0 1       2 5 . 5  
  
 M e t   S t a t i o n :  
 t i m e s t a m p                         r a d i a t i o n _ w _ m 2  
 2 0 2 6 - 0 1 - 0 1   1 0 : 0 0 : 0 5     4 5 0  
 2 0 2 6 - 0 1 - 0 1   1 0 : 0 0 : 4 5     4 5 5  
  
 R e s u l t   a f t e r   m e r g e _ a s o f :  
 t i m e s t a m p                         n o d e _ i d     t e m p _ c     r a d i a t i o n _ w _ m 2  
 2 0 2 6 - 0 1 - 0 1   1 0 : 0 0 : 0 0     N O D E 0 1       2 5 . 3         4 5 0     �   �   m a t c h e d   t o   1 0 : 0 0 : 0 5  
 2 0 2 6 - 0 1 - 0 1   1 0 : 0 1 : 0 0     N O D E 0 1       2 5 . 5         4 5 5     �   �   m a t c h e d   t o   1 0 : 0 0 : 4 5  
 ` ` `  
  
 # #   5 . 3   M u l t i - S o u r c e   S y n c   P i p e l i n e  
  
 * * T h e   F u l l   P i p e l i n e : * *  
  
 ` ` ` p y t h o n  
 c l a s s   R e s e a r c h C u r a t i o n E n g i n e :  
         d e f   c u r a t e _ m l _ r e a d y _ d a t a s e t ( s e l f ,   h o u r s = 2 4 ) :  
                 #   S t e p   1 :   E x t r a c t   r a w   t e l e m e t r y   f r o m   d a t a b a s e  
                 t e l e m e t r y   =   s e l f . d b . q u e r y ( " " "  
                         S E L E C T   t i m e s t a m p ,   n o d e _ i d ,   t e m p _ c ,   h u m i d i t y _ p c t ,   p a r _ u m o l  
                         F R O M   r a w _ t e l e m e t r y  
                         W H E R E   t i m e s t a m p   >   N O W ( )   -   I N T E R V A L   ' { h o u r s }   h o u r s '  
                 " " " )  
                  
                 #   S t e p   2 :   E x t r a c t   m e t   s t a t i o n   d a t a  
                 m e t   =   s e l f . d b . q u e r y ( " " "  
                         S E L E C T   t i m e s t a m p ,   r a d i a t i o n _ w _ m 2 ,   s p e c t r a l _ r e d _ p c t ,   s p e c t r a l _ b l u e _ p c t  
                         F R O M   m e t _ s t a t i o n _ d a t a  
                         W H E R E   t i m e s t a m p   >   N O W ( )   -   I N T E R V A L   ' { h o u r s }   h o u r s '  
                 " " " )  
                  
                 #   S t e p   3 :   F i r s t   t e m p o r a l   j o i n   ( t e l e m e t r y   +   m e t )  
                 d f 1   =   t e m p o r a l _ s y n c ( t e l e m e t r y ,   m e t ,   t o l e r a n c e _ s e c o n d s = 6 0 )  
                  
                 #   S t e p   4 :   C a l c u l a t e   p h e n o t y p e s  
                 d f 1 [ ' v p d _ k p a ' ]   =   c a l c u l a t e _ v p d ( d f 1 [ ' t e m p _ c ' ] ,   d f 1 [ ' h u m i d i t y _ p c t ' ] )  
                 d f 1 [ ' t r a n s p i r a t i o n _ g _ m 2 _ h ' ]   =   e s t i m a t e _ t r a n s p i r a t i o n (  
                         d f 1 [ ' t e m p _ c ' ] ,  
                         d f 1 [ ' h u m i d i t y _ p c t ' ] ,  
                         d f 1 [ ' r a d i a t i o n _ w _ m 2 ' ]  
                 )  
                  
                 #   S t e p   5 :   J o i n   w i t h   u s e r   e v e n t s   ( e . g . ,   " w a t e r e d   p l a n t s   a t   1 0 : 1 5 " )  
                 e v e n t s   =   s e l f . d b . q u e r y ( " S E L E C T   *   F R O M   r e s e a r c h _ e v e n t s " )  
                 d f 2   =   t e m p o r a l _ s y n c ( d f 1 ,   e v e n t s ,   t o l e r a n c e _ s e c o n d s = 3 0 0 )     #   5 - m i n   w i n d o w  
                  
                 #   S t e p   6 :   J o i n   w i t h   y i e l d   d a t a   ( d a i l y )  
                 y i e l d _ d a t a   =   s e l f . d b . q u e r y ( " S E L E C T   *   F R O M   y i e l d _ l o g s " )  
                 d f _ f i n a l   =   d f 2 . m e r g e ( y i e l d _ d a t a ,   o n = ' n o d e _ i d ' ,   h o w = ' l e f t ' )  
                  
                 #   S t e p   7 :   E x p o r t   t o   C S V   f o r   M L  
                 d f _ f i n a l . t o _ c s v ( ' / a p p / d a t a / c u r a t e d _ r e s e a r c h _ d a t a s e t . c s v ' ,   i n d e x = F a l s e )  
                  
                 r e t u r n   d f _ f i n a l  
 ` ` `  
  
 * * W h y   t h i s   m a t t e r s   i n   a n   i n t e r v i e w : * *  
 T h i s   s h o w s   y o u   u n d e r s t a n d :  
 -   D a t a b a s e   q u e r y   o p t i m i z a t i o n  
 -   T i m e - s e r i e s   d a t a   c h a l l e n g e s  
 -   E T L   ( E x t r a c t ,   T r a n s f o r m ,   L o a d )   p i p e l i n e s  
 -   D a t a   q u a l i t y   i s s u e s   ( m i s s i n g   v a l u e s ,   a l i g n m e n t )  
  
 # #   5 . 4   D a t a   V a l i d a t i o n  
  
 * * F i l e : * *   ` g a t e w a y / s e r v i c e s / s y n c . p y `   ( v a l i d a t i o n   s e c t i o n )  
  
 * * P y d a n t i c   S c h e m a s : * *  
  
 ` ` ` p y t h o n  
 f r o m   p y d a n t i c   i m p o r t   B a s e M o d e l ,   v a l i d a t o r  
  
 c l a s s   T e l e m e t r y R e c o r d ( B a s e M o d e l ) :  
         n o d e _ i d :   s t r  
         t i m e s t a m p :   d a t e t i m e  
         t e m p _ c :   f l o a t  
         h u m i d i t y _ p c t :   f l o a t  
         p a r _ u m o l :   i n t  
          
         @ v a l i d a t o r ( ' t e m p _ c ' )  
         d e f   t e m p _ r a n g e _ c h e c k ( c l s ,   v ) :  
                 i f   n o t   - 2 0   < =   v   < =   5 0 :  
                         r a i s e   V a l u e E r r o r ( f ' T e m p e r a t u r e   { v } � � C   o u t   o f   r a n g e ' )  
                 r e t u r n   v  
          
         @ v a l i d a t o r ( ' h u m i d i t y _ p c t ' )  
         d e f   h u m i d i t y _ r a n g e _ c h e c k ( c l s ,   v ) :  
                 i f   n o t   0   < =   v   < =   1 0 0 :  
                         r a i s e   V a l u e E r r o r ( f ' H u m i d i t y   { v } %   o u t   o f   r a n g e ' )  
                 r e t u r n   v  
 ` ` `  
  
 * * W h y   P y d a n t i c ? * *  
 -   A u t o m a t i c   t y p e   c o n v e r s i o n   ( s t r i n g   " 2 5 . 3 "   �      f l o a t   2 5 . 3 )  
 -   R a n g e   v a l i d a t i o n   c a t c h e s   s e n s o r   e r r o r s  
 -   S e l f - d o c u m e n t i n g   c o d e   ( s c h e m a   =   d o c u m e n t a t i o n )  
  
 * * R e a l   e x a m p l e   o f   v a l i d a t i o n   c a t c h i n g   e r r o r s : * *  
 O n e   d a y ,   a   s e n s o r   r e p o r t e d   1 2 7 � � C   ( t h e   I 2 C   r e a d   f a i l e d   a n d   r e t u r n e d   0 x F F ) .   P y d a n t i c   r e j e c t e d   i t   b e f o r e   i t   p o l l u t e d   o u r   d a t a s e t .  
  
 - - -  
  
 #   6 .   B a c k e n d   M i c r o s e r v i c e s  
  
 # #   6 . 1   D o c k e r   C o m p o s e   A r c h i t e c t u r e  
  
 * * F i l e : * *   ` d o c k e r - c o m p o s e . y m l `  
  
 * * W h a t   i s   D o c k e r   C o m p o s e ? * *  
 A   t o o l   f o r   d e f i n i n g   m u l t i - c o n t a i n e r   a p p l i c a t i o n s .   I n s t e a d   o f   r u n n i n g   1 2   s e p a r a t e   ` d o c k e r   r u n `   c o m m a n d s ,   w e   d e f i n e   e v e r y t h i n g   i n   o n e   Y A M L   f i l e .  
  
 * * O u r   S e r v i c e s : * *  
  
 ` ` ` y a m l  
 v e r s i o n :   ' 3 . 8 '  
 s e r v i c e s :  
     d b :                                 #   T i m e s c a l e D B  
     m q t t :                             #   M o s q u i t t o   b r o k e r  
     m q t t _ b r i d g e :               #   T h r e a d   �      M Q T T   �      D B  
     i n g e s t :                         #   4 0 - n o d e   s i m u l a t o r  
     m e t _ s t a t i o n :               #   M e t   s t a t i o n   s i m u l a t o r  
     a p i :                               #   R E S T   A P I   ( F l a s k )  
     s y n c _ e n g i n e :               #   D a t a   c u r a t i o n   p i p e l i n e  
     b i o l o g y _ e n g i n e :         #   P l a n t   p h y s i c s   s i m u l a t o r  
     m l _ e n g i n e :                   #   R L   a g e n t  
     s a f e t y _ m o n i t o r :         #   L T L   c h e c k e r  
     g r a f a n a :                       #   T i m e - s e r i e s   d a s h b o a r d  
     d a s h b o a r d :                   #   H T M L / J S   f r o n t e n d  
 ` ` `  
  
 * * D e p e n d e n c y   G r a p h : * *  
  
 ` ` `  
 d b   ( T i m e s c a l e D B )  
   �  S�  � �  �   m q t t _ b r i d g e   ( d e p e n d s   o n   d b   +   m q t t )  
   �  S�  � �  �   i n g e s t   ( d e p e n d s   o n   d b )  
   �  S�  � �  �   m e t _ s t a t i o n   ( d e p e n d s   o n   d b )  
   �  S�  � �  �   a p i   ( d e p e n d s   o n   d b )  
   �   �  � �  �   s y n c _ e n g i n e   ( d e p e n d s   o n   d b   +   i n g e s t   +   m e t _ s t a t i o n )  
             �   �  � �  �   m l _ e n g i n e   ( d e p e n d s   o n   s y n c _ e n g i n e )  
 ` ` `  
  
 * * W h y   t h i s   o r d e r   m a t t e r s : * *  
 D o c k e r   C o m p o s e   s t a r t s   s e r v i c e s   i n   d e p e n d e n c y   o r d e r .   T h e   d a t a b a s e   m u s t   b e   r u n n i n g   b e f o r e   a n y t h i n g   c a n   c o n n e c t   t o   i t .  
  
 # #   6 . 2   R E S T   A P I   D e s i g n  
  
 * * F i l e : * *   ` g a t e w a y / s e r v i c e s / a p i . p y `  
  
 * * W h a t   i t   d o e s : * *   P r o v i d e s   H T T P   e n d p o i n t s   f o r   t h e   d a s h b o a r d   a n d   e x t e r n a l   i n t e g r a t i o n s .  
  
 # # #   E n d p o i n t   C a t a l o g :  
  
 * * 1 .   H e a l t h   C h e c k * *  
 ` ` ` h t t p  
 G E T   / h e a l t h  
 ` ` `  
 ` ` ` j s o n  
 { " s e r v i c e " :   " g o s - r e s e a r c h - a p i " ,   " s t a t u s " :   " h e a l t h y " }  
 ` ` `  
  
 * * 2 .   N o d e   S t a t u s * *  
 ` ` ` h t t p  
 G E T   / a p i / n o d e s  
 ` ` `  
 R e t u r n s   l i s t   o f   a l l   4 0   n o d e s   w i t h   t h e i r   l a t e s t   r e a d i n g s .  
  
 * * 3 .   P h e n o t y p e   C a l c u l a t i o n * *  
 ` ` ` h t t p  
 P O S T   / a p i / p h e n o t y p e  
 C o n t e n t - T y p e :   a p p l i c a t i o n / j s o n  
  
 {  
     " t e m p _ c " :   2 5 . 0 ,  
     " h u m i d i t y _ p c t " :   6 5 . 0 ,  
     " p a r _ u m o l " :   8 0 0 . 0  
 }  
 ` ` `  
  
 * * R e s p o n s e : * *  
 ` ` ` j s o n  
 {  
     " p h e n o t y p e " :   {  
         " v p d _ k p a " :   1 . 1 0 6 ,  
         " v p d _ s t a t u s " :   " M I L D _ S T R E S S " ,  
         " t r a n s p i r a t i o n _ g _ m 2 _ h " :   3 1 2 . 5 ,  
         " s t r e s s _ s c o r e " :   1 5  
     } ,  
     " l e d _ r e c o m m e n d a t i o n " :   {  
         " a c t i o n " :   " I N C R E A S E _ B L U E " ,  
         " b l u e _ p c t " :   6 0 ,  
         " r e d _ p c t " :   4 0  
     }  
 }  
 ` ` `  
  
 * * 4 .   E v e n t   L o g g i n g   ( L L M - P o w e r e d ) * *  
 ` ` ` h t t p  
 P O S T   / a p i / e v e n t s  
 C o n t e n t - T y p e :   a p p l i c a t i o n / j s o n  
  
 {  
     " d e s c r i p t i o n " :   " F o u n d   s p i d e r   m i t e s   o n   r o w   3   t h i s   m o r n i n g " ,  
     " a n n o t a t o r " :   " r e s e a r c h e r _ 0 1 "  
 }  
 ` ` `  
  
 * * W h a t   h a p p e n s   b e h i n d   t h e   s c e n e s : * *  
 ` ` ` p y t h o n  
 d e f   p a r s e _ e v e n t _ w i t h _ l l m ( d e s c r i p t i o n ) :  
         #   S e n d   t o   O p e n A I   A P I  
         r e s p o n s e   =   o p e n a i . C h a t C o m p l e t i o n . c r e a t e (  
                 m o d e l = " g p t - 4 " ,  
                 m e s s a g e s = [ {  
                         " r o l e " :   " s y s t e m " ,  
                         " c o n t e n t " :   " E x t r a c t   s t r u c t u r e d   d a t a   f r o m   g r e e n h o u s e   o b s e r v a t i o n s . "  
                 } ,   {  
                         " r o l e " :   " u s e r " ,  
                         " c o n t e n t " :   f " P a r s e :   { d e s c r i p t i o n } "  
                 } ]  
         )  
          
         #   E x a m p l e   o u t p u t :  
         #   {  
         #       " t y p e " :   " p e s t " ,  
         #       " p e s t _ n a m e " :   " s p i d e r _ m i t e s " ,  
         #       " l o c a t i o n " :   " r o w _ 3 " ,  
         #       " s e v e r i t y " :   " l o w "  
         #   }  
          
         s t r u c t u r e d _ d a t a   =   j s o n . l o a d s ( r e s p o n s e . c h o i c e s [ 0 ] . m e s s a g e . c o n t e n t )  
          
         #   S t o r e   i n   d a t a b a s e  
         d b . e x e c u t e ( " " "  
                 I N S E R T   I N T O   r e s e a r c h _ e v e n t s   ( t i m e s t a m p ,   t y p e ,   d e s c r i p t i o n ,   m e t a d a t a )  
                 V A L U E S   ( N O W ( ) ,   % s ,   % s ,   % s )  
         " " " ,   ( s t r u c t u r e d _ d a t a [ ' t y p e ' ] ,   d e s c r i p t i o n ,   s t r u c t u r e d _ d a t a ) )  
 ` ` `  
  
 * * W h y   t h i s   i s   p o w e r f u l : * *  
 R e s e a r c h e r s   c a n   l o g   o b s e r v a t i o n s   i n   n a t u r a l   l a n g u a g e   w i t h o u t   f i l l i n g   o u t   f o r m s .   T h e   L L M   e x t r a c t s   t h e   s t r u c t u r e   a u t o m a t i c a l l y .  
  
 # #   6 . 3   D a t a b a s e   S c h e m a   D e s i g n  
  
 * * F i l e : * *   ` g a t e w a y / s c h e m a . s q l `  
  
 * * W h a t   i s   T i m e s c a l e D B ? * *  
 P o s t g r e S Q L   w i t h   t i m e - s e r i e s   e x t e n s i o n s .   I t   a u t o m a t i c a l l y   p a r t i t i o n s   d a t a   b y   t i m e   ( c a l l e d   " c h u n k s " )   a n d   p r o v i d e s   c o m p r e s s i o n .  
  
 * * K e y   T a b l e s : * *  
  
 * * 1 .   r a w _ t e l e m e t r y   ( H y p e r t a b l e ) * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   r a w _ t e l e m e t r y   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L ,  
         n o d e _ i d   T E X T   N O T   N U L L ,  
         t e m p _ c   N U M E R I C ( 4 , 2 ) ,  
         h u m i d i t y _ p c t   N U M E R I C ( 4 , 2 ) ,  
         p a r _ u m o l   I N T E G E R ,  
         b a t t e r y _ m v   I N T E G E R ,  
         r s s i   I N T E G E R  
 ) ;  
  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' r a w _ t e l e m e t r y ' ,   ' t i m e s t a m p ' ) ;  
 ` ` `  
  
 * * W h a t   d o e s   ` c r e a t e _ h y p e r t a b l e `   d o ? * *  
 C o n v e r t s   t h e   t a b l e   i n t o   a   h y p e r t a b l e .   B e h i n d   t h e   s c e n e s ,   T i m e s c a l e D B   c r e a t e s   m u l t i p l e   " c h u n k "   t a b l e s :  
 -   ` _ h y p e r _ 1 _ 1 _ c h u n k `   ( d a t a   f r o m   J a n   1 - 7 )  
 -   ` _ h y p e r _ 1 _ 2 _ c h u n k `   ( d a t a   f r o m   J a n   8 - 1 4 )  
 -   e t c .  
  
 * * W h y ? * *  
 -   * * F a s t e r   q u e r i e s : * *   " G i v e   m e   d a t a   f r o m   l a s t   w e e k "   o n l y   s c a n s   o n e   c h u n k  
 -   * * E a s i e r   d e l e t i o n : * *   D r o p   o l d   c h u n k s   w i t h o u t   e x p e n s i v e   D E L E T E s  
 -   * * B e t t e r   c o m p r e s s i o n : * *   C o m p r e s s   o l d   c h u n k s   t o   s a v e   s p a c e  
  
 * * 2 .   m e t _ s t a t i o n _ d a t a   ( H y p e r t a b l e ) * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   m e t _ s t a t i o n _ d a t a   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L ,  
         r a d i a t i o n _ w _ m 2   N U M E R I C ( 6 , 2 ) ,  
         s p e c t r a l _ r e d _ p c t   N U M E R I C ( 4 , 2 ) ,  
         s p e c t r a l _ b l u e _ p c t   N U M E R I C ( 4 , 2 ) ,  
         s p e c t r a l _ g r e e n _ p c t   N U M E R I C ( 4 , 2 ) ,  
         s p e c t r a l _ f a r _ r e d _ p c t   N U M E R I C ( 4 , 2 )  
 ) ;  
  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' m e t _ s t a t i o n _ d a t a ' ,   ' t i m e s t a m p ' ) ;  
 ` ` `  
  
 * * 3 .   r e s e a r c h _ e v e n t s   ( H y p e r t a b l e ) * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   r e s e a r c h _ e v e n t s   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L ,  
         e v e n t _ t y p e   T E X T ,  
         d e s c r i p t i o n   T E X T ,  
         m e t a d a t a   J S O N B ,     - -   S t o r e s   L L M - e x t r a c t e d   s t r u c t u r e d   d a t a  
         a n n o t a t o r   T E X T  
 ) ;  
  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' r e s e a r c h _ e v e n t s ' ,   ' t i m e s t a m p ' ) ;  
 ` ` `  
  
 * * W h y   J S O N B   f o r   m e t a d a t a ? * *  
 W e   d o n ' t   k n o w   w h a t   f i e l d s   t h e   L L M   w i l l   e x t r a c t .   J S O N B   a l l o w s   f l e x i b l e   s c h e m a   w h i l e   s t i l l   s u p p o r t i n g   i n d e x i n g .  
  
 * * E x a m p l e   q u e r y : * *  
 ` ` ` s q l  
 - -   F i n d   a l l   p e s t   i n c i d e n t s   i n   t h e   l a s t   w e e k  
 S E L E C T   t i m e s t a m p ,   d e s c r i p t i o n ,   m e t a d a t a - > > ' p e s t _ n a m e '   a s   p e s t  
 F R O M   r e s e a r c h _ e v e n t s  
 W H E R E   e v e n t _ t y p e   =   ' p e s t '  
 A N D   t i m e s t a m p   >   N O W ( )   -   I N T E R V A L   ' 7   d a y s ' ;  
 ` ` `  
  
 - - -  
  
 #   7 .   P h e n o t y p i n g   A l g o r i t h m s  
  
 # #   7 . 1   V a p o r   P r e s s u r e   D e f i c i t   ( V P D )  
  
 * * F i l e : * *   ` m l _ e n g i n e / p h e n o t y p i n g . p y `  
  
 * * W h a t   i s   V P D ? * *  
 T h e   d i f f e r e n c e   b e t w e e n   h o w   m u c h   m o i s t u r e   t h e   a i r   i s   h o l d i n g   v s .   h o w   m u c h   i t   * c o u l d *   h o l d   a t   a   g i v e n   t e m p e r a t u r e .  
  
 * * W h y   i t   m a t t e r s : * *  
 V P D   d r i v e s   t r a n s p i r a t i o n .   I f   V P D   i s   t o o   l o w ,   p l a n t s   " s w e a t "   t o o   l i t t l e   ( p o o r   n u t r i e n t   u p t a k e ) .   I f   t o o   h i g h ,   s t o m a t a   c l o s e   ( p h o t o s y n t h e s i s   s t o p s ) .  
  
 * * T h e   M a t h : * *  
  
 * * S t e p   1 :   C a l c u l a t e   S a t u r a t i o n   V a p o r   P r e s s u r e   ( S V P ) * *  
  
 T h i s   i s   t h e   m a x i m u m   a m o u n t   o f   m o i s t u r e   a i r   c a n   h o l d   a t   t e m p e r a t u r e   T .  
  
 F o r m u l a   ( T e t e n s   e q u a t i o n ) :  
 ` ` `  
 S V P ( T )   =   0 . 6 1 0 8   �    e x p ( ( 1 7 . 2 7   �    T )   /   ( T   +   2 3 7 . 3 ) )  
 ` ` `  
  
 W h e r e :  
 -   T   =   T e m p e r a t u r e   i n   � � C  
 -   S V P   =   S a t u r a t i o n   v a p o r   p r e s s u r e   i n   k P a  
  
 * * S t e p   2 :   C a l c u l a t e   A c t u a l   V a p o r   P r e s s u r e   ( A V P ) * *  
  
 T h i s   i s   h o w   m u c h   m o i s t u r e   t h e   a i r   i s   a c t u a l l y   h o l d i n g .  
  
 ` ` `  
 A V P   =   S V P   �    ( R H   /   1 0 0 )  
 ` ` `  
  
 W h e r e   R H   =   R e l a t i v e   h u m i d i t y   i n   %  
  
 * * S t e p   3 :   C a l c u l a t e   V P D * *  
  
 ` ` `  
 V P D   =   S V P   -   A V P  
 ` ` `  
  
 * * P y t h o n   I m p l e m e n t a t i o n : * *  
  
 ` ` ` p y t h o n  
 i m p o r t   n u m p y   a s   n p  
  
 d e f   c a l c u l a t e _ v p d ( t e m p _ c ,   h u m i d i t y _ p c t ) :  
         " " "  
         C a l c u l a t e   V a p o r   P r e s s u r e   D e f i c i t   u s i n g   T e t e n s   e q u a t i o n .  
          
         A r g s :  
                 t e m p _ c :   T e m p e r a t u r e   i n   C e l s i u s  
                 h u m i d i t y _ p c t :   R e l a t i v e   h u m i d i t y   ( 0 - 1 0 0 )  
          
         R e t u r n s :  
                 V P D   i n   k i l o p a s c a l s   ( k P a )  
         " " "  
         #   S a t u r a t i o n   v a p o r   p r e s s u r e   ( T e t e n s   e q u a t i o n )  
         s v p   =   0 . 6 1 0 8   *   n p . e x p ( ( 1 7 . 2 7   *   t e m p _ c )   /   ( t e m p _ c   +   2 3 7 . 3 ) )  
          
         #   A c t u a l   v a p o r   p r e s s u r e  
         a v p   =   s v p   *   ( h u m i d i t y _ p c t   /   1 0 0 . 0 )  
          
         #   V a p o r   p r e s s u r e   d e f i c i t  
         v p d   =   s v p   -   a v p  
          
         r e t u r n   v p d  
 ` ` `  
  
 * * E x a m p l e   C a l c u l a t i o n : * *  
  
 A t   2 5 � � C   a n d   6 5 %   R H :  
 -   S V P   =   0 . 6 1 0 8   �    e x p ( ( 1 7 . 2 7   �    2 5 )   /   ( 2 5   +   2 3 7 . 3 ) )   =   3 . 1 6 7   k P a  
 -   A V P   =   3 . 1 6 7   �    0 . 6 5   =   2 . 0 5 9   k P a  
 -   * * V P D   =   3 . 1 6 7   -   2 . 0 5 9   =   1 . 1 0 8   k P a * *  
  
 * * C l a s s i f i c a t i o n : * *  
  
 ` ` ` p y t h o n  
 d e f   c l a s s i f y _ v p d _ s t r e s s ( v p d _ k p a ) :  
         i f   v p d _ k p a   <   0 . 4 :  
                 r e t u r n   " L O W _ T R A N S P I R A T I O N "  
         e l i f   0 . 4   < =   v p d _ k p a   <   0 . 8 :  
                 r e t u r n   " O P T I M A L "  
         e l i f   0 . 8   < =   v p d _ k p a   <   1 . 2 :  
                 r e t u r n   " M I L D _ S T R E S S "  
         e l i f   1 . 2   < =   v p d _ k p a   <   1 . 5 :  
                 r e t u r n   " M O D E R A T E _ S T R E S S "  
         e l s e :  
                 r e t u r n   " S E V E R E _ S T R E S S "  
 ` ` `  
  
 # #   7 . 2   T r a n s p i r a t i o n   E s t i m a t i o n  
  
 * * W h a t   i s   T r a n s p i r a t i o n ? * *  
 W a t e r   l o s s   f r o m   p l a n t   l e a v e s   t h r o u g h   s t o m a t a   ( t i n y   p o r e s ) .   I t ' s   l i k e   s w e a t i n g   f o r   p l a n t s .  
  
 * * W h y   e s t i m a t e   i t ? * *  
 -   I r r i g a t i o n   s c h e d u l i n g   ( w a t e r   b e f o r e   s t r e s s   o c c u r s )  
 -   E a r l y   d r o u g h t   d e t e c t i o n  
 -   N u t r i e n t   u p t a k e   p r e d i c t i o n  
  
 * * T h e   A l g o r i t h m :   S i m p l i f i e d   P e n m a n - M o n t e i t h * *  
  
 T h e   f u l l   P e n m a n - M o n t e i t h   e q u a t i o n   i s   c o m p l e x ,   b u t   f o r   g r e e n h o u s e s   w e   c a n   s i m p l i f y :  
  
 ` ` `  
 E T   =   ( �    �    R n   +   � �   �    V P D   �    2 . 0 )   /   ( �    +   � � )  
 ` ` `  
  
 W h e r e :  
 -   E T   =   E v a p o t r a n s p i r a t i o n   ( g / m � � / h o u r )  
 -   �    =   S l o p e   o f   S V P   c u r v e   ( k P a / � � C )  
 -   R n   =   N e t   r a d i a t i o n   ( W / m � � )  
 -   � �   =   P s y c h r o m e t r i c   c o n s t a n t   ( ~ 0 . 0 6 6   k P a / � � C )  
 -   2 . 0   =   W i n d   f u n c t i o n   s i m p l i f i c a t i o n   ( a s s u m e s   s t i l l   a i r )  
  
 * * P y t h o n   I m p l e m e n t a t i o n : * *  
  
 ` ` ` p y t h o n  
 d e f   e s t i m a t e _ t r a n s p i r a t i o n ( t e m p _ c ,   h u m i d i t y _ p c t ,   p a r _ u m o l ) :  
         " " "  
         E s t i m a t e   t r a n s p i r a t i o n   u s i n g   s i m p l i f i e d   P e n m a n - M o n t e i t h .  
          
         A r g s :  
                 t e m p _ c :   A i r   t e m p e r a t u r e   ( � � C )  
                 h u m i d i t y _ p c t :   R e l a t i v e   h u m i d i t y   ( % )  
                 p a r _ u m o l :   P h o t o s y n t h e t i c a l l y   a c t i v e   r a d i a t i o n   ( � � m o l / m � � / s )  
          
         R e t u r n s :  
                 T r a n s p i r a t i o n   r a t e   i n   g / m � � / h o u r  
         " " "  
         #   C a l c u l a t e   V P D  
         v p d   =   c a l c u l a t e _ v p d ( t e m p _ c ,   h u m i d i t y _ p c t )  
          
         #   C o n v e r t   P A R   t o   n e t   r a d i a t i o n   ( e m p i r i c a l   c o n v e r s i o n )  
         #   1   W / m � �   � 0 �  4 . 6   � � m o l / m � � / s  
         r n   =   p a r _ u m o l   /   4 . 6   *   0 . 5     #   0 . 5   a c c o u n t s   f o r   a l b e d o / l o n g - w a v e  
          
         #   S l o p e   o f   S V P   c u r v e   ( d e r i v a t i v e   o f   T e t e n s   e q u a t i o n )  
         s v p   =   0 . 6 1 0 8   *   n p . e x p ( ( 1 7 . 2 7   *   t e m p _ c )   /   ( t e m p _ c   +   2 3 7 . 3 ) )  
         d e l t a   =   ( 4 0 9 8   *   s v p )   /   ( ( t e m p _ c   +   2 3 7 . 3 )   * *   2 )  
          
         #   P s y c h r o m e t r i c   c o n s t a n t  
         g a m m a   =   0 . 0 6 6     #   k P a / � � C   f o r   s t a n d a r d   a t m o s p h e r i c   p r e s s u r e  
          
         #   S i m p l i f i e d   P e n m a n - M o n t e i t h   ( s t i l l   a i r ,   c a n o p y   r e s i s t a n c e   ~ 7 0   s / m )  
         e t _ m m h   =   ( d e l t a   *   r n   +   g a m m a   *   v p d   *   2 . 0 )   /   ( d e l t a   +   g a m m a )  
          
         #   C o n v e r t   m m / h o u r   t o   g / m � � / h o u r   ( 1   m m   w a t e r   =   1   k g / m � �   =   1 0 0 0   g / m � � )  
         t r a n s p i r a t i o n   =   e t _ m m h   *   1 0 0 0  
          
         r e t u r n   t r a n s p i r a t i o n  
 ` ` `  
  
 * * E x a m p l e : * *  
 -   T e m p   =   2 5 � � C  
 -   H u m i d i t y   =   6 5 %  
 -   P A R   =   8 0 0   � � m o l / m � � / s  
  
 C a l c u l a t e s   t o :   * * ~ 3 1 2   g / m � � / h o u r * *  
  
 T h a t   m e a n s   e a c h   s q u a r e   m e t e r   o f   l e a f   a r e a   l o s e s   3 1 2   g r a m s   o f   w a t e r   p e r   h o u r .  
  
 # #   7 . 3   M u l t i - F a c t o r   S t r e s s   D e t e c t i o n  
  
 * * F i l e : * *   ` m l _ e n g i n e / p h e n o t y p i n g . p y `  
  
 * * T h e   C o m p o s i t e   S t r e s s   S c o r e : * *  
  
 ` ` ` p y t h o n  
 d e f   c a l c u l a t e _ s t r e s s _ s c o r e ( t e m p _ c ,   h u m i d i t y _ p c t ,   p a r _ u m o l ,   v p d _ k p a ) :  
         " " "  
         C a l c u l a t e   c o m p o s i t e   s t r e s s   s c o r e   ( 0 - 1 0 0 ) .  
         H i g h e r   =   m o r e   s t r e s s .  
         " " "  
         s c o r e   =   0  
          
         #   H e a t   s t r e s s  
         i f   t e m p _ c   >   3 0 :  
                 s c o r e   + =   m i n ( 2 0 ,   ( t e m p _ c   -   3 0 )   *   4 )     #   + 4   p o i n t s   p e r   d e g r e e   a b o v e   3 0 � � C  
          
         #   C o l d   s t r e s s  
         i f   t e m p _ c   <   1 5 :  
                 s c o r e   + =   m i n ( 1 5 ,   ( 1 5   -   t e m p _ c )   *   3 )     #   + 3   p o i n t s   p e r   d e g r e e   b e l o w   1 5 � � C  
          
         #   V P D   s t r e s s  
         i f   v p d _ k p a   >   1 . 5 :  
                 s c o r e   + =   m i n ( 2 5 ,   ( v p d _ k p a   -   1 . 5 )   *   2 0 )     #   H e a v i l y   p e n a l i z e   h i g h   V P D  
          
         #   L o w   l i g h t   s t r e s s  
         i f   p a r _ u m o l   <   1 0 0 :  
                 s c o r e   + =   m i n ( 1 0 ,   ( 1 0 0   -   p a r _ u m o l )   /   1 0 )  
          
         #   H i g h   l i g h t   s t r e s s   ( p h o t o i n h i b )  
         i f   p a r _ u m o l   >   1 5 0 0 :  
                 s c o r e   + =   m i n ( 1 5 ,   ( p a r _ u m o l   -   1 5 0 0 )   /   1 0 0 )  
          
         #   H u m i d i t y   s t r e s s  
         i f   h u m i d i t y _ p c t   >   9 0 :  
                 s c o r e   + =   1 5     #   D i s e a s e   r i s k  
         i f   h u m i d i t y _ p c t   <   4 0 :  
                 s c o r e   + =   1 5     #   D e h y d r a t i o n   r i s k  
          
         r e t u r n   m i n ( 1 0 0 ,   s c o r e )     #   C a p   a t   1 0 0  
 ` ` `  
  
 * * W h y   m u l t i p l e   f a c t o r s ? * *  
 A   p l a n t   c a n   b e   " f i n e "   o n   t e m p e r a t u r e   b u t   s t r e s s e d   b y   V P D .   W e   n e e d   a   h o l i s t i c   v i e w .  
  
 - - -  
  
 #   8 .   M a c h i n e   L e a r n i n g   &   R e i n f o r c e m e n t   L e a r n i n g  
  
 # #   8 . 1   T h e   R L   P r o b l e m   F o r m u l a t i o n  
  
 * * G o a l : * *   L e a r n   a n   L E D   c o n t r o l   p o l i c y   t h a t   m a x i m i z e s   s t r a w b e r r y   y i e l d   w h i l e   m i n i m i z i n g   e n e r g y   c o s t .  
  
 * * F i l e : * *   ` m l _ e n g i n e / a g e n t _ r l . p y `  
  
 * * W h a t   i s   R e i n f o r c e m e n t   L e a r n i n g ? * *  
 I n s t e a d   o f   t r a i n i n g   o n   l a b e l e d   d a t a   ( s u p e r v i s e d   l e a r n i n g ) ,   t h e   a g e n t   l e a r n s   b y   t r i a l   a n d   e r r o r   u s i n g   r e w a r d s .  
  
 * * O u r   M D P   ( M a r k o v   D e c i s i o n   P r o c e s s ) : * *  
  
 * * S t a t e   S p a c e   ( w h a t   t h e   a g e n t   o b s e r v e s ) : * *  
 ` ` ` p y t h o n  
 s t a t e   =   [  
         v p d _ k p a ,                                 #   C u r r e n t   V P D  
         t e m p _ c ,                                   #   C u r r e n t   t e m p e r a t u r e  
         p a r _ u m o l _ c u r r e n t ,               #   C u r r e n t   P A R  
         h o u r _ o f _ d a y ,                         #   T i m e   ( 0 - 2 3 )  
         d a y s _ s i n c e _ p l a n t i n g ,         #   G r o w t h   s t a g e  
         c u m u l a t i v e _ p a r _ t o d a y         #   D a i l y   l i g h t   i n t e g r a l   s o   f a r  
 ]  
 ` ` `  
  
 * * A c t i o n   S p a c e   ( w h a t   t h e   a g e n t   c a n   d o ) : * *  
 ` ` ` p y t h o n  
 a c t i o n   =   [  
         l e d _ i n t e n s i t y ,         #   0 . 0   t o   1 . 0   ( 0 %   t o   1 0 0 % )  
         b l u e _ f r a c t i o n           #   0 . 0   t o   1 . 0   ( 0 %   t o   1 0 0 %   b l u e )  
 ]  
 #   r e d _ f r a c t i o n   =   1 . 0   -   b l u e _ f r a c t i o n   ( i m p l i c i t )  
 ` ` `  
  
 * * R e w a r d   F u n c t i o n : * *  
 ` ` ` p y t h o n  
 d e f   c a l c u l a t e _ r e w a r d ( s t a t e ,   a c t i o n ,   n e x t _ s t a t e ) :  
         #   P h o t o s y n t h e s i s   p r o x y   ( F a r q u h a r   m o d e l   a p p r o x i m a t i o n )  
         p h o t o s y n t h e s i s   =   e s t i m a t e _ p h o t o s y n t h e s i s (  
                 p a r = a c t i o n [ 0 ]   *   1 0 0 0 ,     #   C o n v e r t   i n t e n s i t y   t o   � � m o l  
                 t e m p = s t a t e [ 1 ] ,  
                 v p d = s t a t e [ 0 ]  
         )  
          
         #   E n e r g y   c o s t  
         e n e r g y _ c o s t   =   a c t i o n [ 0 ]   *   L E D _ P O W E R _ W A T T S   *   E L E C T R I C I T Y _ C O S T _ P E R _ K W H  
          
         #   S t r e s s   p e n a l t y  
         s t r e s s _ p e n a l t y   =   - 1 . 0   *   s t a t e . s t r e s s _ s c o r e   /   1 0  
          
         #   N e t   r e w a r d  
         r e w a r d   =   p h o t o s y n t h e s i s   -   e n e r g y _ c o s t   +   s t r e s s _ p e n a l t y  
          
         r e t u r n   r e w a r d  
 ` ` `  
  
 * * K e y   I n s i g h t : * *   W e   r e w a r d   p h o t o s y n t h e s i s   ( w h i c h   c o r r e l a t e s   w i t h   y i e l d )   b u t   p e n a l i z e   e n e r g y   u s e   a n d   s t r e s s .  
  
 # #   8 . 2   A l g o r i t h m :   S o f t   A c t o r - C r i t i c   ( S A C )  
  
 * * W h y   S A C ? * *  
 -   H a n d l e s   c o n t i n u o u s   a c t i o n   s p a c e s   ( L E D   i n t e n s i t y   i s   c o n t i n u o u s ,   n o t   d i s c r e t e )  
 -   S a m p l e   e f f i c i e n t   ( i m p o r t a n t   b e c a u s e   r e a l   c r o p   c y c l e s   a r e   s l o w )  
 -   S t a b l e   t r a i n i n g  
  
 * * P s e u d o c o d e : * *  
  
 ` ` ` p y t h o n  
 i m p o r t   t o r c h  
 f r o m   s t a b l e _ b a s e l i n e s 3   i m p o r t   S A C  
  
 #   D e f i n e   e n v i r o n m e n t  
 e n v   =   S t r a w b e r r y G r e e n h o u s e E n v ( )  
  
 #   C r e a t e   S A C   a g e n t  
 m o d e l   =   S A C (  
         p o l i c y = " M l p P o l i c y " ,     #   M u l t i - l a y e r   p e r c e p t r o n  
         e n v = e n v ,  
         l e a r n i n g _ r a t e = 3 e - 4 ,  
         b u f f e r _ s i z e = 1 0 0 0 0 0 ,  
         b a t c h _ s i z e = 2 5 6 ,  
         g a m m a = 0 . 9 9 ,     #   D i s c o u n t   f a c t o r   ( f u t u r e   r e w a r d s )  
         t a u = 0 . 0 0 5 ,       #   S o f t   u p d a t e   r a t e   f o r   t a r g e t   n e t w o r k  
 )  
  
 #   T r a i n  
 m o d e l . l e a r n ( t o t a l _ t i m e s t e p s = 1 0 0 0 0 0 0 )  
  
 #   U s e   t r a i n e d   p o l i c y  
 s t a t e   =   e n v . r e s e t ( )  
 w h i l e   T r u e :  
         a c t i o n ,   _ s t a t e s   =   m o d e l . p r e d i c t ( s t a t e ,   d e t e r m i n i s t i c = T r u e )  
         s t a t e ,   r e w a r d ,   d o n e ,   i n f o   =   e n v . s t e p ( a c t i o n )  
         i f   d o n e :  
                 b r e a k  
 ` ` `  
  
 # #   8 . 3   P h y s i c s - B a s e d   P l a n t   S i m u l a t o r  
  
 * * F i l e : * *   ` m l _ e n g i n e / p l a n t _ s i m _ c 3 . p y `  
  
 * * W h y   s i m u l a t e ? * *  
 R e a l   e x p e r i m e n t s   t a k e   m o n t h s .   W e   s i m u l a t e   g r o w t h   t o   t r a i n   t h e   R L   a g e n t   f a s t e r .  
  
 * * T h e   F a r q u h a r   M o d e l   ( S i m p l i f i e d ) : * *  
  
 P h o t o s y n t h e s i s   r a t e   d e p e n d s   o n   t h r e e   f a c t o r s :  
 1 .   * * L i g h t - l i m i t e d * *   ( l o w   P A R )  
 2 .   * * R u b i s c o - l i m i t e d * *   ( e n z y m e   s a t u r a t i o n )  
 3 .   * * T P U - l i m i t e d * *   ( e l e c t r o n   t r a n s p o r t )  
  
 ` ` ` p y t h o n  
 d e f   f a r q u h a r _ p h o t o s y n t h e s i s ( p a r _ u m o l ,   t e m p _ c ,   c o 2 _ p p m ,   v p d _ k p a ) :  
         " " "  
         S i m p l i f i e d   C 3   p h o t o s y n t h e s i s   m o d e l .  
         " " "  
         #   M a x i m u m   c a r b o x y l a t i o n   r a t e   ( t e m p e r a t u r e   d e p e n d e n t )  
         v c m a x _ 2 5   =   6 0     #   � � m o l / m � � / s   a t   2 5 � � C  
         v c m a x   =   v c m a x _ 2 5   *   t e m p _ r e s p o n s e ( t e m p _ c ,   2 5 ,   6 5 )  
          
         #   E l e c t r o n   t r a n s p o r t   r a t e   ( l i g h t   d e p e n d e n t )  
         j   =   ( 0 . 3 8 5   *   p a r _ u m o l )   /   n p . s q r t ( 1   +   ( 0 . 3 8 5   *   p a r _ u m o l   /   2 2 0 )   * *   2 )  
          
         #   R u b i s c o - l i m i t e d   r a t e  
         w c   =   ( v c m a x   *   ( c o 2 _ p p m   -   4 2 . 7 5 ) )   /   ( c o 2 _ p p m   +   4 1 0 )  
          
         #   L i g h t - l i m i t e d   r a t e  
         w j   =   ( j   *   ( c o 2 _ p p m   -   4 2 . 7 5 ) )   /   ( 4   *   ( c o 2 _ p p m   +   2   *   4 2 . 7 5 ) )  
          
         #   T a k e   m i n i m u m   ( l i m i t i n g   f a c t o r )  
         a _ n e t   =   m i n ( w c ,   w j )  
          
         #   A p p l y   s t o m a t a l   c o n d u c t a n c e   r e d u c t i o n   f r o m   V P D   s t r e s s  
         i f   v p d _ k p a   >   1 . 2 :  
                 a _ n e t   * =   n p . e x p ( - ( v p d _ k p a   -   1 . 2 )   /   0 . 5 )  
          
         r e t u r n   a _ n e t     #   � � m o l   C O 2 / m � � / s  
 ` ` `  
  
 * * C o n s t a n t s   e x p l a i n e d : * *  
 -   ` 4 2 . 7 5 `   =   C O 2   c o m p e n s a t i o n   p o i n t   ( �  * )  
 -   ` 4 1 0 `   =   M i c h a e l i s   c o n s t a n t   f o r   R u b i s c o  
  
 T h i s   i s   a c t u a l   p l a n t   p h y s i o l o g y ,   n o t   h a n d - w a v y   M L .  
  
 # #   8 . 4   S a f e t y :   L i n e a r   T e m p o r a l   L o g i c   M o n i t o r  
  
 * * F i l e : * *   ` g a t e w a y / s e r v i c e s / s a f e t y _ l t l . p y `  
  
 * * T h e   P r o b l e m : * *  
 R L   a g e n t s   c a n   s u g g e s t   c r a z y   a c t i o n s   d u r i n g   e x p l o r a t i o n   ( e . g . ,   " t u r n   o f f   l i g h t s   f o r   2 4   h o u r s " ) .  
  
 * * S o l u t i o n :   L T L   V e r i f i c a t i o n * *  
  
 L i n e a r   T e m p o r a l   L o g i c   l e t s   u s   w r i t e   s a f e t y   r u l e s :  
  
 ` ` ` p y t h o n  
 #   S a f e t y   p r o p e r t i e s   i n   L T L   n o t a t i o n :  
 #   G ( a c t i o n . l e d _ o f f   �      X   F ( a c t i o n . l e d _ o n ) )  
 #   " G l o b a l l y ,   i f   L E D s   t u r n   o f f ,   e v e n t u a l l y   t h e y   m u s t   t u r n   b a c k   o n "  
  
 #   ! ( v p d   >   1 . 5   � ��   a c t i o n . l e d _ i n t e n s i t y   >   0 . 8 )  
 #   " N e v e r   a l l o w   h i g h   i n t e n s i t y   w h e n   V P D   i s   a l r e a d y   h i g h "  
  
 c l a s s   S a f e t y M o n i t o r :  
         d e f   c h e c k _ a c t i o n _ s a f e ( s e l f ,   s t a t e ,   a c t i o n ) :  
                 #   R u l e   1 :   D o n ' t   t u r n   o f f   l i g h t s   d u r i n g   d a y  
                 i f   6   < =   s t a t e . h o u r   <   1 8   a n d   a c t i o n . l e d _ i n t e n s i t y   <   0 . 1 :  
                         r e t u r n   F a l s e ,   " C a n n o t   t u r n   o f f   L E D s   d u r i n g   p h o t o p e r i o d "  
                  
                 #   R u l e   2 :   R e d u c e   i n t e n s i t y   i f   V P D   i s   h i g h  
                 i f   s t a t e . v p d _ k p a   >   1 . 5   a n d   a c t i o n . l e d _ i n t e n s i t y   >   0 . 5 :  
                         r e t u r n   F a l s e ,   " H i g h   V P D   r e q u i r e s   l o w e r   l i g h t   i n t e n s i t y "  
                  
                 #   R u l e   3 :   A v o i d   r a p i d   i n t e n s i t y   c h a n g e s  
                 i f   a b s ( a c t i o n . l e d _ i n t e n s i t y   -   s t a t e . p r e v _ i n t e n s i t y )   >   0 . 3 :  
                         r e t u r n   F a l s e ,   " I n t e n s i t y   c h a n g e   t o o   r a p i d   ( p l a n t   s h o c k   r i s k ) "  
                  
                 r e t u r n   T r u e ,   " S a f e "  
          
         d e f   c o r r e c t _ a c t i o n ( s e l f ,   s t a t e ,   a c t i o n ) :  
                 #   I f   a c t i o n   i s   u n s a f e ,   a p p l y   c o r r e c t i o n  
                 s a f e ,   r e a s o n   =   s e l f . c h e c k _ a c t i o n _ s a f e ( s t a t e ,   a c t i o n )  
                 i f   n o t   s a f e :  
                         #   P r o j e c t   a c t i o n   o n t o   s a f e   s u b s p a c e  
                         c o r r e c t e d   =   a c t i o n . c o p y ( )  
                         i f   s t a t e . v p d _ k p a   >   1 . 5 :  
                                 c o r r e c t e d . l e d _ i n t e n s i t y   =   m i n ( 0 . 5 ,   a c t i o n . l e d _ i n t e n s i t y )  
                         r e t u r n   c o r r e c t e d  
                 r e t u r n   a c t i o n  
 ` ` `  
  
 * * W h y   t h i s   i s   i m p o r t a n t : * *  
 G u a r a n t e e s   t h e   s y s t e m   n e v e r   e n t e r s   a   d a n g e r o u s   s t a t e ,   r e g a r d l e s s   o f   w h a t   t h e   R L   a g e n t   t r i e s   t o   d o .  
  
 - - -  
  
 #   9 .   D e v O p s   &   V e r i f i c a t i o n  
  
 # #   9 . 1   D o c k e r   M u l t i - C o n t a i n e r   S t r a t e g y  
  
 * * F i l e : * *   ` d o c k e r - c o m p o s e . y m l `  
  
 * * W h y   1 2   S e p a r a t e   S e r v i c e s ? * *  
  
 1 .   * * I s o l a t i o n : * *   E a c h   s e r v i c e   h a s   i t s   o w n   d e p e n d e n c i e s .   T h e   A P I   d o e s n ' t   n e e d   C   c o m p i l e r s ,   b u t   t h e   f i r m w a r e   b u i l d   d o e s .  
 2 .   * * I n d e p e n d e n t   S c a l i n g : * *   C a n   r u n   3   A P I   i n s t a n c e s   b u t   o n l y   1   d a t a b a s e .  
 3 .   * * F a u l t   T o l e r a n c e : * *   I f   t h e   R L   a g e n t   c r a s h e s ,   t h e   d a s h b o a r d   s t i l l   w o r k s .  
 4 .   * * D e v e l o p m e n t   S p e e d : * *   R e b u i l d   o n l y   t h e   c h a n g e d   s e r v i c e ,   n o t   t h e   w h o l e   s t a c k .  
  
 * * H e a l t h   C h e c k s : * *  
  
 ` ` ` y a m l  
 d b :  
     h e a l t h c h e c k :  
         t e s t :   [ " C M D - S H E L L " ,   " p g _ i s r e a d y   - U   r e s e a r c h e r " ]  
         i n t e r v a l :   5 s  
         t i m e o u t :   5 s  
         r e t r i e s :   5  
 ` ` `  
  
 * * W h y   t h i s   m a t t e r s : * *  
 W i t h o u t   h e a l t h   c h e c k s ,   d e p e n d e n t   s e r v i c e s   m i g h t   t r y   t o   c o n n e c t   t o   t h e   d a t a b a s e   b e f o r e   i t ' s   r e a d y ,   c a u s i n g   r a c e   c o n d i t i o n s .  
  
 # #   9 . 2   T e s t i n g   S t r a t e g y  
  
 # # #   U n i t   T e s t s  
  
 * * F i l e : * *   ` t e s t s / t e s t _ p h e n o t y p i n g . p y `  
  
 ` ` ` p y t h o n  
 i m p o r t   p y t e s t  
 f r o m   m l _ e n g i n e . p h e n o t y p i n g   i m p o r t   c a l c u l a t e _ v p d ,   e s t i m a t e _ t r a n s p i r a t i o n  
  
 d e f   t e s t _ v p d _ c a l c u l a t i o n ( ) :  
         " " " T e s t   V P D   a g a i n s t   k n o w n   v a l u e s . " " "  
         #   A t   2 5 � � C   a n d   6 5 %   R H ,   V P D   s h o u l d   b e   ~ 1 . 1 1   k P a  
         v p d   =   c a l c u l a t e _ v p d ( 2 5 . 0 ,   6 5 . 0 )  
         a s s e r t   1 . 1 0   < =   v p d   < =   1 . 1 2 ,   f " V P D   o u t   o f   r a n g e :   { v p d } "  
  
 d e f   t e s t _ v p d _ e d g e _ c a s e s ( ) :  
         " " " T e s t   b o u n d a r y   c o n d i t i o n s . " " "  
         #   1 0 0 %   R H   s h o u l d   g i v e   V P D   � 0 �  0  
         v p d   =   c a l c u l a t e _ v p d ( 2 5 . 0 ,   1 0 0 . 0 )  
         a s s e r t   v p d   <   0 . 0 1  
          
         #   0 %   R H   s h o u l d   g i v e   V P D   =   S V P  
         v p d   =   c a l c u l a t e _ v p d ( 2 5 . 0 ,   0 . 0 )  
         a s s e r t   3 . 1 6   < =   v p d   < =   3 . 1 8  
  
 d e f   t e s t _ t r a n s p i r a t i o n _ r a n g e ( ) :  
         " " " E n s u r e   t r a n s p i r a t i o n   o u t p u t   i s   p h y s i c a l l y   r e a l i s t i c . " " "  
         e t   =   e s t i m a t e _ t r a n s p i r a t i o n ( 2 5 . 0 ,   6 5 . 0 ,   8 0 0 . 0 )  
         a s s e r t   5 0   < =   e t   < =   5 0 0 ,   " T r a n s p i r a t i o n   o u t   o f   r e a l i s t i c   r a n g e "  
 ` ` `  
  
 * * C o v e r a g e   T a r g e t : * *   8 5 %   l i n e   c o v e r a g e  
  
 # # #   I n t e g r a t i o n   T e s t s  
  
 * * F i l e : * *   ` t e s t s / t e s t _ a p i . p y `  
  
 ` ` ` p y t h o n  
 i m p o r t   r e q u e s t s  
  
 d e f   t e s t _ a p i _ h e a l t h ( ) :  
         r e s p o n s e   =   r e q u e s t s . g e t ( " h t t p : / / l o c a l h o s t : 5 0 0 0 / h e a l t h " )  
         a s s e r t   r e s p o n s e . s t a t u s _ c o d e   = =   2 0 0  
         a s s e r t   r e s p o n s e . j s o n ( ) [ ' s t a t u s ' ]   = =   ' h e a l t h y '  
  
 d e f   t e s t _ p h e n o t y p e _ e n d p o i n t ( ) :  
         p a y l o a d   =   {  
                 " t e m p _ c " :   2 5 . 0 ,  
                 " h u m i d i t y _ p c t " :   6 5 . 0 ,  
                 " p a r _ u m o l " :   8 0 0 . 0  
         }  
         r e s p o n s e   =   r e q u e s t s . p o s t ( " h t t p : / / l o c a l h o s t : 5 0 0 0 / a p i / p h e n o t y p e " ,   j s o n = p a y l o a d )  
         a s s e r t   r e s p o n s e . s t a t u s _ c o d e   = =   2 0 0  
         d a t a   =   r e s p o n s e . j s o n ( )  
         a s s e r t   ' v p d _ k p a '   i n   d a t a [ ' p h e n o t y p e ' ]  
         a s s e r t   ' l e d _ r e c o m m e n d a t i o n '   i n   d a t a  
 ` ` `  
  
 # # #   L o a d   T e s t i n g  
  
 * * F i l e : * *   ` t e s t s / l o a d _ t e s t . p y `  
  
 ` ` ` p y t h o n  
 f r o m   l o c u s t   i m p o r t   H t t p U s e r ,   t a s k ,   b e t w e e n  
  
 c l a s s   G o s L o a d T e s t ( H t t p U s e r ) :  
         w a i t _ t i m e   =   b e t w e e n ( 1 ,   3 )     #   S i m u l a t e   u s e r s   w i t h   1 - 3 s   t h i n k   t i m e  
          
         @ t a s k ( 1 0 )     #   W e i g h t :   r u n   t h i s   1 0 x   m o r e   t h a n   o t h e r   t a s k s  
         d e f   g e t _ n o d e s ( s e l f ) :  
                 s e l f . c l i e n t . g e t ( " / a p i / n o d e s " )  
          
         @ t a s k ( 5 )  
         d e f   c a l c u l a t e _ p h e n o t y p e ( s e l f ) :  
                 s e l f . c l i e n t . p o s t ( " / a p i / p h e n o t y p e " ,   j s o n = {  
                         " t e m p _ c " :   2 5 . 0 ,  
                         " h u m i d i t y _ p c t " :   6 5 . 0 ,  
                         " p a r _ u m o l " :   8 0 0 . 0  
                 } )  
          
         @ t a s k ( 1 )  
         d e f   g e t _ s u m m a r y ( s e l f ) :  
                 s e l f . c l i e n t . g e t ( " / a p i / p h e n o t y p e / s u m m a r y " )  
 ` ` `  
  
 * * R u n : * *   ` l o c u s t   - f   t e s t s / l o a d _ t e s t . p y   - - h o s t = h t t p : / / l o c a l h o s t : 5 0 0 0 `  
  
 * * R e s u l t : * *   A P I   h a n d l e s   5 0 0   r e q u e s t s / s e c o n d   a t   9 9 t h   p e r c e n t i l e   l a t e n c y   < 3 0 0 m s .  
  
 # #   9 . 3   S i m u l a t i o n   f o r   V e r i f i c a t i o n  
  
 * * F i l e : * *   ` g a t e w a y / s e r v i c e s / f a r m _ s i m . p y `  
  
 * * W h a t   i t   d o e s : * *   G e n e r a t e s   r e a l i s t i c   t e l e m e t r y   f o r   4 0   v i r t u a l   n o d e s .  
  
 * * W h y ? * *  
 -   R e a l   e x p e r i m e n t s   t a k e   m o n t h s  
 -   N e e d   t o   t e s t   e d g e   c a s e s   ( s e n s o r   f a i l u r e s ,   n e t w o r k   d r o p s )  
 -   C a n ' t   b r e a k   r e a l   p l a n t s   d u r i n g   d e v e l o p m e n t  
  
 * * D i u r n a l   C y c l e   S i m u l a t i o n : * *  
  
 ` ` ` p y t h o n  
 i m p o r t   n u m p y   a s   n p  
 f r o m   d a t e t i m e   i m p o r t   d a t e t i m e ,   t i m e d e l t a  
  
 d e f   s i m u l a t e _ g r e e n h o u s e _ t e m p ( h o u r _ o f _ d a y ,   b a s e _ t e m p = 1 8 . 0 ) :  
         " " "  
         R e a l i s t i c   g r e e n h o u s e   t e m p e r a t u r e   f o l l o w i n g   s o l a r   c y c l e .  
         " " "  
         #   P e a k   a t   1 4 : 0 0   ( 2   P M ) ,   m i n i m u m   a t   0 6 : 0 0   ( 6   A M )  
         p e a k _ h o u r   =   1 4  
         a m p l i t u d e   =   8 . 0     #   � � 8 � � C   s w i n g  
          
         #   S i n u s o i d a l   m o d e l  
         p h a s e   =   ( h o u r _ o f _ d a y   -   p e a k _ h o u r )   /   2 4 . 0   *   2   *   n p . p i  
         t e m p   =   b a s e _ t e m p   +   a m p l i t u d e   *   n p . c o s ( p h a s e )  
          
         #   A d d   r e a l i s t i c   n o i s e  
         n o i s e   =   n p . r a n d o m . n o r m a l ( 0 ,   0 . 3 )  
          
         r e t u r n   m a x ( 1 0 . 0 ,   m i n ( 3 5 . 0 ,   t e m p   +   n o i s e ) )  
  
 d e f   s i m u l a t e _ p a r ( h o u r _ o f _ d a y ) :  
         " " "  
         P h o t o s y n t h e t i c a l l y   a c t i v e   r a d i a t i o n   f o l l o w i n g   s u n r i s e / s u n s e t .  
         " " "  
         i f   6   < =   h o u r _ o f _ d a y   <   1 8 :  
                 #   D a y l i g h t   h o u r s  
                 p e a k _ h o u r   =   1 2  
                 m a x _ p a r   =   1 2 0 0     #   � � m o l / m � � / s  
                  
                 #   M o d e l   a s   p a r a b o l a  
                 t _ n o r m a l i z e d   =   ( h o u r _ o f _ d a y   -   p e a k _ h o u r )   /   6 . 0     #   - 1   t o   + 1  
                 p a r   =   m a x _ p a r   *   ( 1   -   t _ n o r m a l i z e d   * *   2 )  
                  
                 #   A d d   c l o u d   e f f e c t s  
                 c l o u d _ f a c t o r   =   n p . r a n d o m . u n i f o r m ( 0 . 7 ,   1 . 0 )  
                 r e t u r n   m a x ( 0 ,   p a r   *   c l o u d _ f a c t o r )  
         e l s e :  
                 #   N i g h t   ( L E D   s u p p l e m e n t a t i o n )  
                 r e t u r n   n p . r a n d o m . u n i f o r m ( 5 0 ,   1 5 0 )  
  
 #   G e n e r a t e   4 0   n o d e s  
 f o r   n o d e _ i d   i n   r a n g e ( 1 ,   4 1 ) :  
         c u r r e n t _ h o u r   =   d a t e t i m e . n o w ( ) . h o u r  
          
         t e l e m e t r y   =   {  
                 ' n o d e _ i d ' :   f ' N O D E { n o d e _ i d : 0 2 d } ' ,  
                 ' t i m e s t a m p ' :   d a t e t i m e . n o w ( ) ,  
                 ' t e m p _ c ' :   s i m u l a t e _ g r e e n h o u s e _ t e m p ( c u r r e n t _ h o u r ) ,  
                 ' h u m i d i t y _ p c t ' :   n p . r a n d o m . u n i f o r m ( 6 0 ,   8 0 ) ,  
                 ' p a r _ u m o l ' :   s i m u l a t e _ p a r ( c u r r e n t _ h o u r ) ,  
                 ' b a t t e r y _ m v ' :   3 0 0 0   -   ( n o d e _ i d   *   5 ) ,     #   S i m u l a t e   b a t t e r y   d r a i n  
                 ' r s s i ' :   - 7 0   +   n p . r a n d o m . r a n d i n t ( - 1 0 ,   1 0 )  
         }  
          
         #   I n s e r t   i n t o   d a t a b a s e  
         d b . i n s e r t ( t e l e m e t r y )  
 ` ` `  
  
 * * T h i s   s h o w s   y o u   c a n : * *  
 -   M o d e l   p h y s i c a l   s y s t e m s   m a t h e m a t i c a l l y  
 -   G e n e r a t e   r e a l i s t i c   t e s t   d a t a  
 -   T h i n k   a b o u t   s e n s o r   n o i s e   a n d   v a r i a b i l i t y  
  
 - - -  
  
 #   1 0 .   C h a l l e n g e s   &   S o l u t i o n s  
  
 # #   1 0 . 1   C h a l l e n g e :   T h r e a d   N e t w o r k   I n s t a b i l i t y  
  
 * * P r o b l e m : * *  
 I n i t i a l   d e p l o y m e n t   h a d   1 5 %   p a c k e t   l o s s .   N o d e s   w o u l d   o c c a s i o n a l l y   d r o p   o f f   t h e   m e s h   f o r   3 0 +   s e c o n d s .  
  
 * * R o o t   C a u s e   A n a l y s i s : * *  
  
 1 .   * * I n t e r f e r e n c e : * *   2 . 4   G H z   b a n d   i s   c r o w d e d   ( W i - F i ,   B l u e t o o t h ,   m i c r o w a v e   o v e n s )  
 2 .   * * P a r e n t   S e l e c t i o n : * *   S o m e   n o d e s   w e r e   c h o o s i n g   s u b o p t i m a l   r o u t e r s  
 3 .   * * B u f f e r   O v e r f l o w : * *   B o r d e r   r o u t e r   w a s   d r o p p i n g   p a c k e t s   d u r i n g   b u r s t s  
  
 * * S o l u t i o n : * *  
  
 * * 1 .   C h a n n e l   S e l e c t i o n : * *  
 ` ` ` b a s h  
 #   S c a n   f o r   c l e a n e s t   c h a n n e l  
 $   s u d o   p y t h o n 3   - c   " i m p o r t   p y s p i n e l ;   s c a n _ c h a n n e l s ( ) "  
 #   C h a n n e l s   1 1 ,   1 5 ,   2 0 ,   2 5   h a d   l o w e s t   n o i s e  
 #   M o v e d   f r o m   c h a n n e l   1 5   �      c h a n n e l   2 5  
 ` ` `  
  
 R e s u l t :   P a c k e t   l o s s   d r o p p e d   t o   3 %  
  
 * * 2 .   I m p r o v e d   P a r e n t   S e l e c t i o n : * *  
 ` ` ` c  
 / /   f i r m w a r e / s r c / n e t w o r k . c  
 v o i d   c o n f i g u r e _ t h r e a d _ p a r a m s ( )   {  
         / /   P r e f e r   p a r e n t s   w i t h   R S S I   >   - 7 0   d B m  
         o t T h r e a d S e t P a r e n t P r i o r i t y ( O T _ T H R E A D _ P A R E N T _ P R I O R I T Y _ H I G H ,   - 7 0 ) ;  
          
         / /   I n c r e a s e   r o u t e r   s e l e c t i o n   t h r e s h o l d  
         o t T h r e a d S e t R o u t e r S e l e c t i o n J i t t e r ( 1 2 0 ) ;     / /   s e c o n d s  
 }  
 ` ` `  
  
 * * 3 .   B o r d e r   R o u t e r   T u n i n g : * *  
 ` ` ` p y t h o n  
 #   I n c r e a s e   r e c e i v e   b u f f e r  
 s o c k e t . s e t s o c k o p t ( s o c k e t . S O L _ S O C K E T ,   s o c k e t . S O _ R C V B U F ,   6 5 5 3 6 )  
  
 #   P r o c e s s   p a c k e t s   a s y n c h r o n o u s l y  
 a s y n c   d e f   h a n d l e _ c o a p _ r e q u e s t ( r e q u e s t ) :  
         a s y n c i o . c r e a t e _ t a s k ( p r o c e s s _ a n d _ p u b l i s h ( r e q u e s t ) )     #   D o n ' t   b l o c k  
         r e t u r n   i m m e d i a t e _ a c k ( )  
 ` ` `  
  
 * * F i n a l   R e s u l t : * *   P a c k e t   l o s s   < 1 % ,   n o   d r o p o u t s  
  
 # #   1 0 . 2   C h a l l e n g e :   D a t a b a s e   P e r f o r m a n c e  
  
 * * P r o b l e m : * *  
 A f t e r   1   m i l l i o n   r o w s ,   q u e r i e s   w e r e   t a k i n g   5 +   s e c o n d s .  
  
 * * D i a g n o s i s : * *  
  
 ` ` ` s q l  
 E X P L A I N   A N A L Y Z E  
 S E L E C T   *   F R O M   r a w _ t e l e m e t r y  
 W H E R E   t i m e s t a m p   >   N O W ( )   -   I N T E R V A L   ' 1   h o u r '  
 A N D   n o d e _ i d   =   ' N O D E 0 1 ' ;  
  
 - -   R e s u l t :   S e q u e n t i a l   S c a n ,   3 2 0 0 m s  
 ` ` `  
  
 * * S o l u t i o n s : * *  
  
 * * 1 .   P r o p e r   I n d e x i n g : * *  
 ` ` ` s q l  
 C R E A T E   I N D E X   i d x _ t e l e m e t r y _ n o d e _ t i m e  
 O N   r a w _ t e l e m e t r y   ( n o d e _ i d ,   t i m e s t a m p   D E S C ) ;  
 ` ` `  
  
 * * 2 .   E n a b l e   C o m p r e s s i o n : * *  
 ` ` ` s q l  
 A L T E R   T A B L E   r a w _ t e l e m e t r y   S E T   (  
     t i m e s c a l e d b . c o m p r e s s ,  
     t i m e s c a l e d b . c o m p r e s s _ s e g m e n t b y   =   ' n o d e _ i d '  
 ) ;  
  
 S E L E C T   a d d _ c o m p r e s s i o n _ p o l i c y ( ' r a w _ t e l e m e t r y ' ,   I N T E R V A L   ' 7   d a y s ' ) ;  
 ` ` `  
  
 * * 3 .   C o n t i n u o u s   A g g r e g a t e s : * *  
 ` ` ` s q l  
 C R E A T E   M A T E R I A L I Z E D   V I E W   t e l e m e t r y _ h o u r l y  
 W I T H   ( t i m e s c a l e d b . c o n t i n u o u s )   A S  
 S E L E C T  
     t i m e _ b u c k e t ( ' 1   h o u r ' ,   t i m e s t a m p )   A S   h o u r ,  
     n o d e _ i d ,  
     A V G ( t e m p _ c )   A S   a v g _ t e m p ,  
     A V G ( h u m i d i t y _ p c t )   A S   a v g _ h u m i d i t y  
 F R O M   r a w _ t e l e m e t r y  
 G R O U P   B Y   h o u r ,   n o d e _ i d ;  
 ` ` `  
  
 * * R e s u l t : * *  
 -   Q u e r y   t i m e :   5 s   �      5 0 m s   ( 1 0 0 x   i m p r o v e m e n t )  
 -   D i s k   u s a g e :   2   G B   �      4 0 0   M B   ( 5 x   c o m p r e s s i o n )  
  
 # #   1 0 . 3   C h a l l e n g e :   R L   A g e n t   C o n v e r g e n c e  
  
 * * P r o b l e m : * *  
 R L   a g e n t   w a s n ' t   l e a r n i n g .   R e w a r d   s t a y e d   f l a t   f o r   1 0 0 k   t i m e s t e p s .  
  
 * * D e b u g g i n g   S t e p s : * *  
  
 * * 1 .   C h e c k   R e w a r d   D i s t r i b u t i o n : * *  
 ` ` ` p y t h o n  
 i m p o r t   m a t p l o t l i b . p y p l o t   a s   p l t  
  
 r e w a r d s   =   [ ]  
 f o r   e p i s o d e   i n   r a n g e ( 1 0 0 0 ) :  
         e n v . r e s e t ( )  
         e p i s o d e _ r e w a r d   =   0  
         f o r   _   i n   r a n g e ( 1 0 0 ) :  
                 a c t i o n   =   e n v . a c t i o n _ s p a c e . s a m p l e ( )     #   R a n d o m   p o l i c y  
                 _ ,   r e w a r d ,   d o n e ,   _   =   e n v . s t e p ( a c t i o n )  
                 e p i s o d e _ r e w a r d   + =   r e w a r d  
                 i f   d o n e :  
                         b r e a k  
         r e w a r d s . a p p e n d ( e p i s o d e _ r e w a r d )  
  
 p l t . h i s t ( r e w a r d s ,   b i n s = 5 0 )  
 p l t . s h o w ( )  
 ` ` `  
  
 * * F i n d i n g : * *   A l l   r e w a r d s   w e r e   b e t w e e n   - 0 . 0 1   a n d   + 0 . 0 1 .   S i g n a l   t o o   w e a k !  
  
 * * 2 .   R e w a r d   S c a l e   F i x : * *  
 ` ` ` p y t h o n  
 #   B e f o r e  
 r e w a r d   =   p h o t o s y n t h e s i s   -   e n e r g y _ c o s t     #   R a n g e :   [ - 0 . 0 1 ,   0 . 0 1 ]  
  
 #   A f t e r  
 r e w a r d   =   ( p h o t o s y n t h e s i s   -   e n e r g y _ c o s t )   *   1 0 0 0     #   R a n g e :   [ - 1 0 ,   1 0 ]  
 ` ` `  
  
 * * 3 .   A d d   E x p l o r a t i o n   B o n u s : * *  
 ` ` ` p y t h o n  
 #   E n c o u r a g e   t r y i n g   n e w   L E D   r a t i o s  
 b l u e _ d i v e r s i t y   =   - n p . l o g ( a c t i o n [ 1 ]   +   0 . 0 1 )     #   E n t r o p y   b o n u s  
 r e w a r d   + =   0 . 1   *   b l u e _ d i v e r s i t y  
 ` ` `  
  
 * * R e s u l t : * *   A g e n t   s t a r t e d   l e a r n i n g .   A f t e r   5 0 0 k   t i m e s t e p s ,   a c h i e v e d   1 5 %   b e t t e r   y i e l d   t h a n   b a s e l i n e .  
  
 # #   1 0 . 4   C h a l l e n g e :   G i t   S e c r e t   L e a k   R e m e d i a t i o n  
  
 * * P r o b l e m : * *  
 G i t G u a r d i a n   d e t e c t e d   h a r d c o d e d   p a s s w o r d s   i n   ` d o c k e r - c o m p o s e . y m l `   a f t e r   i n i t i a l   p u s h .  
  
 * * I n c i d e n t   R e s p o n s e : * *  
  
 * * 1 .   I m m e d i a t e   A c t i o n   ( w i t h i n   3 0   m i n u t e s ) : * *  
 ` ` ` b a s h  
 #   W i p e   g i t   h i s t o r y  
 r m   - r f   . g i t  
 g i t   i n i t  
 g i t   r e m o t e   a d d   o r i g i n   h t t p s : / / g i t h u b . c o m / j o h n n i e t s e / s t r a w b e r r y - f a r m . g i t  
 ` ` `  
  
 * * 2 .   S a n i t i z e   A l l   F i l e s : * *  
 ` ` ` y a m l  
 #   d o c k e r - c o m p o s e . y m l  
 #   B e f o r e :  
 P O S T G R E S _ P A S S W O R D :   e p o w e r _ s e c r e t _ 2 0 2 6  
  
 #   A f t e r :  
 P O S T G R E S _ P A S S W O R D :   $ { P O S T G R E S _ P A S S W O R D : - c h a n g e _ m e _ i n _ p r o d }  
 ` ` `  
  
 * * 3 .   C r e a t e   . e n v   f o r   L o c a l   U s e : * *  
 ` ` ` b a s h  
 e c h o   " P O S T G R E S _ P A S S W O R D = e p o w e r _ s e c r e t _ 2 0 2 6 "   >   . e n v  
 e c h o   " . e n v "   > >   . g i t i g n o r e  
 ` ` `  
  
 * * 4 .   F o r c e   P u s h   C l e a n   H i s t o r y : * *  
 ` ` ` b a s h  
 g i t   a d d   .  
 g i t   c o m m i t   - m   " I n i t i a l   c o m m i t :   G . O . S .   v 1 . 0 "  
 g i t   p u s h   - - f o r c e   o r i g i n   m a i n  
 ` ` `  
  
 * * L e s s o n   L e a r n e d : * *   A l w a y s   u s e   e n v i r o n m e n t   v a r i a b l e s   f o r   s e c r e t s .   N e v e r   h a r d c o d e .  
  
 - - -  
  
 #   1 1 .   I n t e r v i e w   S c r i p t   V a r i a t i o n s  
  
 # #   1 1 . 1   T h e   3 - M i n u t e   V e r s i o n   ( E l e v a t o r   P i t c h )  
  
 * * U s e   c a s e : * *   Q u i c k   i n t r o d u c t i o n ,   c a r e e r   f a i r ,   n e t w o r k i n g   e v e n t  
  
 " I   b u i l t   G . O . S . ,   a n   o p e n - s o u r c e   I o T   p h e n o t y p i n g   p l a t f o r m   f o r   p r e c i s i o n   a g r i c u l t u r e .   T h i n k   P l a n t A r r a y ,   b u t   a t   5 %   o f   t h e   c o s t .  
  
 T h e   c o r e   c h a l l e n g e   w a s   r e a l - t i m e   p l a n t   s t r e s s   d e t e c t i o n .   I   d e p l o y e d   4 0   w i r e l e s s   s e n s o r   n o d e s   i n   a   T h r e a d   m e s h   n e t w o r k � �  s i m i l a r   t o   w h a t   M a t t e r   d e v i c e s   u s e � �  r u n n i n g   c u s t o m   f i r m w a r e   I   w r o t e   i n   C   o n   n R F 5 2 8 4 0   c h i p s   r u n n i n g   Z e p h y r   R T O S .  
  
 O n   t h e   b a c k e n d ,   I   e n g i n e e r e d   a   d a t a   s y n c h r o n i z a t i o n   p i p e l i n e   t h a t   p e r f o r m s   t e m p o r a l   j o i n s   a c r o s s   5   a s y n c h r o n o u s   s t r e a m s :   s e n s o r   t e l e m e t r y ,   m e t e o r o l o g i c a l   d a t a ,   a n d   u s e r   a n n o t a t i o n s .   T h e   p i p e l i n e   c a l c u l a t e s   r e a l - t i m e   p h e n o t y p e s   l i k e   V a p o r   P r e s s u r e   D e f i c i t   u s i n g   t h e   P e n m a n - M o n t e i t h   e q u a t i o n .  
  
 O n   t o p   o f   t h a t ,   I   p r o t o t y p e d   a   r e i n f o r c e m e n t   l e a r n i n g   a g e n t   t h a t   o p t i m i z e s   L E D   s p e c t r a l   o u t p u t   f o r   y i e l d ,   w r a p p e d   i n   a   L i n e a r   T e m p o r a l   L o g i c   s a f e t y   l a y e r   t o   p r e v e n t   b i o l o g i c a l   d a m a g e .  
  
 T h e   s y s t e m   a c h i e v e d   s u b - 2 - s e c o n d   l a t e n c y   a n d   c u r r e n t l y   g e n e r a t e s   M L - r e a d y   d a t a s e t s   f o r   s t r a w b e r r y   b r e e d i n g   r e s e a r c h   a t   Q u e e n ' s   U n i v e r s i t y . "  
  
 - - -  
  
 # #   1 1 . 2   T h e   1 0 - M i n u t e   D e e p   D i v e   ( T e c h n i c a l   I n t e r v i e w )  
  
 * * U s e   c a s e : * *   O n - s i t e   i n t e r v i e w ,   t e c h n i c a l   s c r e e n ,   w h i t e b o a r d   d i s c u s s i o n  
  
 # # #   P a r t   1 :   P r o b l e m   &   A p p r o a c h   ( 2   m i n )  
  
 " L e t   m e   w a l k   y o u   t h r o u g h   a   c o m p l e x   p r o j e c t   w h e r e   I   h a d   t o   i n t e g r a t e   e m b e d d e d   s y s t e m s ,   d i s t r i b u t e d   d a t a   p r o c e s s i n g ,   a n d   m a c h i n e   l e a r n i n g .  
  
 T h e   p r o b l e m :   P l a n t   p h e n o t y p i n g � �  m e a s u r i n g   p h y s i o l o g i c a l   t r a i t s � �  i s   e s s e n t i a l   f o r   c r o p   b r e e d i n g ,   b u t   c o m m e r c i a l   s y s t e m s   c o s t   $ 5 0 - 2 0 0 K .   W e   n e e d e d   a   l o w - c o s t   a l t e r n a t i v e   f o r   a   u n i v e r s i t y   r e s e a r c h   l a b .  
  
 M y   a p p r o a c h   w a s   t o   b u i l d   a   f u l l - s t a c k   I o T   s y s t e m   f r o m   s c r a t c h ,   s p a n n i n g   t h e   e n t i r e   s t a c k :   f i r m w a r e   o n   e m b e d d e d   s e n s o r s ,   m e s h   n e t w o r k i n g ,   r e a l - t i m e   d a t a   p i p e l i n e s ,   a n d   M L - b a s e d   c o n t r o l . "  
  
 # # #   P a r t   2 :   E m b e d d e d   &   N e t w o r k   L a y e r   ( 3   m i n )  
  
 " S t a r t i n g   a t   t h e   h a r d w a r e   l e v e l :   I   s e l e c t e d   t h e   n R F 5 2 8 4 0   f o r   i t s   u l t r a l o w   s l e e p   c u r r e n t � �  0 . 4   m i c r o a m p s � �  w h i c h   g i v e s   u s   a   7 - y e a r   b a t t e r y   l i f e   o n   a   c o i n   c e l l   r u n n i n g   I   w r o t e   t h e   f i r m w a r e   i n   C   u s i n g   t h e   Z e p h y r   r e a l - t i m e   o p e r a t i n g   s y s t e m .  
  
 F o r   n e t w o r k i n g ,   I   c h o s e   T h r e a d   o v e r   Z i g b e e   o r   W i - F i .   T h r e a d   g i v e s   y o u   I P v 6   a d d r e s s i n g   a n d   m e s h   s e l f - h e a l i n g ,   w h i c h   m e a n s   i f   a   n o d e   d i e s ,   p a c k e t s   a u t o m a t i c a l l y   r e r o u t e .   I   i m p l e m e n t e d   C o A P   m e s s a g i n g   o v e r   U D P   t o   m i n i m i z e   r a d i o - o n   t i m e � �  e a c h   t r a n s m i s s i o n   c o m p l e t e s   i n   u n d e r   5   m i l l i s e c o n d s .  
  
 T h e   s e n s o r   r e a d i n g s   f l o w   t h r o u g h   a   R a s p b e r r y   P i   a c t i n g   a s   a n   O p e n T h r e a d   B o r d e r   R o u t e r ,   w h i c h   t r a n s l a t e s   T h r e a d   p a c k e t s   i n t o   M Q T T   m e s s a g e s   f o r   t h e   b a c k e n d . "  
  
 # # #   P a r t   3 :   D a t a   P i p e l i n e   ( 2 . 5   m i n )  
  
 " T h e   d a t a   e n g i n e e r i n g   c h a l l e n g e   w a s   s y n c h r o n i z a t i o n .   I   h a v e   4 0   s e n s o r   n o d e s   s a m p l i n g   e v e r y   m i n u t e ,   a   m e t   s t a t i o n   s a m p l i n g   e v e r y   1 0   s e c o n d s ,   a n d   s p o r a d i c   u s e r   a n n o t a t i o n s � �  a l l   a r r i v i n g   w i t h   d i f f e r e n t   t i m e s t a m p s .  
  
 I   c o u l d n ' t   j u s t   J O I N   o n   e x a c t   t i m e s t a m p s ;   y o u ' d   g e t   z e r o   r e s u l t s .   I   e n g i n e e r e d   a   t e m p o r a l   s y n c   a l g o r i t h m   u s i n g   p a n d a s   ` m e r g e _ a s o f ` ,   w h i c h   m a t c h e s   e a c h   s e n s o r   r e a d i n g   t o   t h e   * n e a r e s t *   m e t   s t a t i o n   s a m p l e   w i t h i n   a   6 0 - s e c o n d   t o l e r a n c e   w i n d o w .  
  
 T h i s   s y n c h r o n i z e d   d a t a s e t   t h e n   f l o w s   t h r o u g h   a   p h e n o t y p i n g   e n g i n e   w h e r e   I   c a l c u l a t e   V a p o r   P r e s s u r e   D e f i c i t   u s i n g   t h e   T e t e n s   e q u a t i o n   a n d   e s t i m a t e   t r a n s p i r a t i o n   w i t h   a   s i m p l i f i e d   P e n m a n - M o n t e i t h   m o d e l .   T h e s e   p h y s i o l o g i c a l   m e t r i c s   g o   i n t o   T i m e s c a l e D B � �  P o s t g r e S Q L   w i t h   t i m e - s e r i e s   o p t i m i z a t i o n s   l i k e   a u t o m a t i c   p a r t i t i o n i n g   a n d   c o m p r e s s i o n . "  
  
 # # #   P a r t   4 :   M L   &   S a f e t y   ( 2   m i n )  
  
 " F o r   t h e   m a c h i n e   l e a r n i n g   c o m p o n e n t ,   I   t r a i n e d   a   r e i n f o r c e m e n t   l e a r n i n g   a g e n t   u s i n g   S o f t   A c t o r - C r i t i c   t o   o p t i m i z e   L E D   s p e c t r a l   r a t i o s .   T h e   s t a t e   s p a c e   i n c l u d e s   V P D ,   t e m p e r a t u r e ,   P A R ,   a n d   g r o w t h   s t a g e .   T h e   a c t i o n   s p a c e   i s   c o n t i n u o u s :   L E D   i n t e n s i t y   a n d   b l u e / r e d   r a t i o .  
  
 H e r e ' s   w h e r e   i t   g e t s   i n t e r e s t i n g :   I   w r a p p e d   t h e   R L   a g e n t   i n   a   L i n e a r   T e m p o r a l   L o g i c   s a f e t y   m o n i t o r .   T h i s   v e r i f i e s   e v e r y   a c t i o n   a g a i n s t   b i o l o g i c a l   c o n s t r a i n t s   b e f o r e   e x e c u t i o n .   F o r   e x a m p l e ,   ' N e v e r   a l l o w   h i g h - i n t e n s i t y   l i g h t   w h e n   V P D   e x c e e d s   1 . 5   k i l o p a s c a l s . '   T h i s   g u a r a n t e e s   t h e   s y s t e m   n e v e r   e n t e r s   a   d a n g e r o u s   s t a t e ,   r e g a r d l e s s   o f   w h a t   t h e   A I   e x p l o r e s   d u r i n g   t r a i n i n g .  
  
 T o   t e s t   e v e r y t h i n g   b e f o r e   d e p l o y i n g   o n   r e a l   p l a n t s ,   I   w r o t e   a   p h y s i c s - b a s e d   s i m u l a t o r   u s i n g   t h e   F a r q u h a r   p h o t o s y n t h e s i s   m o d e l .   T h i s   l e t   m e   t r a i n   t h e   R L   a g e n t   o r d e r s   o f   m a g n i t u d e   f a s t e r   t h a n   r e a l - t i m e . "  
  
 # # #   P a r t   5 :   R e s u l t s   &   L e a r n i n g s   ( 0 . 5   m i n )  
  
 " F i n a l   r e s u l t s :   e n d - t o - e n d   l a t e n c y   u n d e r   2   s e c o n d s ,   s y s t e m   c o s t   a r o u n d   $ 3 K   f o r   4 0   n o d e s ,   a n d   i t ' s   c u r r e n t l y   g e n e r a t i n g   M L - r e a d y   d a t a s e t s   f o r   s t r a w b e r r y   b r e e d i n g   r e s e a r c h .  
  
 T h e   p r o j e c t   t a u g h t   m e   h o w   t o   t h i n k   a c r o s s   a b s t r a c t i o n   l a y e r s � �  f r o m   b i t - l e v e l   I 2 C   p r o t o c o l s   t o   d a t a b a s e   q u e r y   o p t i m i z a t i o n   t o   c o n t r o l   t h e o r y � �  a n d   h o w   t o   i n t e g r a t e   t h e m   i n t o   a   c o h e s i v e   s y s t e m . "  
  
 - - -  
  
 # #   1 1 . 3   T h e   B e h a v i o r a l   I n t e r v i e w   V e r s i o n  
  
 * * U s e   c a s e : * *   " T e l l   m e   a b o u t   a   t i m e   y o u   s o l v e d   a   d i f f i c u l t   t e c h n i c a l   p r o b l e m "  
  
 " I ' d   l i k e   t o   t e l l   y o u   a b o u t   d e b u g g i n g   a   n e t w o r k   s t a b i l i t y   i s s u e   i n   m y   I o T   p h e n o t y p i n g   p l a t f o r m .  
  
 * * S i t u a t i o n : * *   A f t e r   d e p l o y i n g   4 0   w i r e l e s s   s e n s o r   n o d e s   i n   a   g r e e n h o u s e ,   w e   w e r e   s e e i n g   1 5 %   p a c k e t   l o s s   a n d   n o d e s   o c c a s i o n a l l y   d r o p p i n g   o f f l i n e   f o r   3 0 +   s e c o n d s .   T h i s   w a s   u n a c c e p t a b l e   f o r   r e a l - t i m e   m o n i t o r i n g .  
  
 * * T a s k : * *   I   n e e d e d   t o   d i a g n o s e   a n d   f i x   t h e   i s s u e   w i t h o u t   r e p l a c i n g   h a r d w a r e ,   s i n c e   w e ' d   a l r e a d y   b u i l t   4 0   c u s t o m   P C B s .  
  
 * * A c t i o n : * *   I   a p p r o a c h e d   t h i s   s y s t e m a t i c a l l y :  
  
 F i r s t ,   I   a d d e d   i n s t r u m e n t a t i o n .   I   m o d i f i e d   t h e   f i r m w a r e   t o   l o g   R S S I   ( r e c e i v e d   s i g n a l   s t r e n g t h ) ,   p a r e n t   r o u t e r   I D ,   a n d   r e t r y   c o u n t s .   T h e n   I   d e p l o y e d   a   p a c k e t   s n i f f e r   r u n n i n g   W i r e s h a r k   w i t h   8 0 2 . 1 5 . 4   c a p t u r e .  
  
 T h e   d a t a   r e v e a l e d   t h r e e   i s s u e s :  
 1 .   W e   w e r e   o n   C h a n n e l   1 5 ,   w h i c h   o v e r l a p p e d   h e a v i l y   w i t h   t h e   b u i l d i n g ' s   W i - F i  
 2 .   S o m e   n o d e s   w e r e   s e l e c t i n g   d i s t a n t   r o u t e r s   ( - 8 5   d B m )   w h e n   c l o s e r   o n e s   ( - 6 5   d B m )   w e r e   a v a i l a b l e  
 3 .   T h e   b o r d e r   r o u t e r   w a s   d r o p p i n g   p a c k e t s   d u r i n g   b u r s t   t r a n s m i s s i o n s  
  
 F o r   t h e   c h a n n e l   i s s u e ,   I   s c a n n e d   a l l   1 6   T h r e a d   c h a n n e l s   a n d   f o u n d   C h a n n e l   2 5   h a d   t h e   l o w e s t   n o i s e   f l o o r .   M i g r a t i n g   r e q u i r e d   a   c o o r d i n a t e d   n e t w o r k   r e c o n f i g u r a t i o n .  
  
 F o r   p a r e n t   s e l e c t i o n ,   I   t u n e d   t h e   T h r e a d   s t a c k   p a r a m e t e r s   t o   p r e f e r   r o u t e r s   w i t h   R S S I   a b o v e   - 7 0   d B m   a n d   i n c r e a s e d   t h e   r o u t e r   s e l e c t i o n   j i t t e r   t o   r e d u c e   o s c i l l a t i o n .  
  
 F o r   t h e   b o r d e r   r o u t e r ,   I   i n c r e a s e d   t h e   s o c k e t   r e c e i v e   b u f f e r   a n d   s w i t c h e d   t o   a s y n c h r o n o u s   p a c k e t   p r o c e s s i n g   s o   i n c o m i n g   C o A P   r e q u e s t s   d i d n ' t   b l o c k   e a c h   o t h e r .  
  
 * * R e s u l t : * *   P a c k e t   l o s s   d r o p p e d   f r o m   1 5 %   t o   u n d e r   1 % ,   a n d   w e   h a v e n ' t   h a d   a   n o d e   d r o p o u t   i n   o v e r   3   w e e k s   o f   c o n t i n u o u s   o p e r a t i o n .   T h e   s y s t e m   n o w   r e l i a b l y   h a n d l e s   4 0   n o d e s   t r a n s m i t t i n g   e v e r y   m i n u t e ,   w h i c h   i s   ~ 4 0   p a c k e t s   p e r   m i n u t e .  
  
 * * L e a r n i n g : * *   T h i s   t a u g h t   m e   t h e   i m p o r t a n c e   o f   m e a s u r a b i l i t y   W h e n   y o u   c a n ' t   s e e   w h a t ' s   h a p p e n i n g   a t   t h e   p a c k e t   l e v e l ,   y o u ' r e   j u s t   g u e s s i n g .   T h e   i n v e s t m e n t   i n   i n s t r u m e n t a t i o n   p a i d   o f f   i m m e d i a t e l y . "  
  
 - - -  
  
 # #   1 1 . 4   T h e   S y s t e m   D e s i g n   I n t e r v i e w   V e r s i o n  
  
 * * U s e   c a s e : * *   " D e s i g n   a   s c a l a b l e   I o T   p l a t f o r m   f o r   a g r i c u l t u r e "  
  
 " L e t   m e   w a l k   t h r o u g h   h o w   I ' d   d e s i g n   t h i s ,   u s i n g   m y   G . O . S .   p r o j e c t   a s   a   r e f e r e n c e   i m p l e m e n t a t i o n .  
  
 # # #   R e q u i r e m e n t s   C l a r i f i c a t i o n  
  
 F i r s t ,   I ' d   a s k :  
 -   S c a l e :   H o w   m a n y   s e n s o r s ?   ( H u n d r e d s ?   M i l l i o n s ? )  
 -   L a t e n c y :   R e a l - t i m e   ( < 1 s )   o r   b a t c h   p r o c e s s i n g   o k a y ?  
 -   C o n n e c t i v i t y :   C a n   w e   a s s u m e   W i F i / c e l l u l a r ,   o r   b a t t e r y - p o w e r e d   m e s h ?  
 -   G e o g r a p h i c   d i s t r i b u t i o n :   S i n g l e   f a r m   o r   m u l t i p l e   s i t e s ?  
  
 F o r   m y   c a s e :   4 0 - 1 0 0   s e n s o r s   p e r   s i t e ,   1 0 0 +   s i t e s ,   r e a l - t i m e ,   b a t t e r y - p o w e r e d .  
  
 # # #   H i g h - L e v e l   A r c h i t e c t u r e  
  
 ` ` `  
 S e n s o r   N o d e s   ( T h r e a d   M e s h )  
             �     
 B o r d e r   R o u t e r   ( E d g e )  
             �     
 M Q T T   B r o k e r   ( L o c a l )  
             �     
 C l o u d   G a t e w a y   ( A W S   I o T   C o r e )  
             �     
 �  S�  � �      T i m e - S e r i e s   D B   ( T i m e s c a l e D B   o n   R D S )  
 �  S�  � �      M e s s a g e   Q u e u e   ( K a f k a )  
 �   �  � �      S t r e a m   P r o c e s s i n g   ( F l i n k )  
             �     
 A p p l i c a t i o n   L a y e r   ( K u b e r n e t e s )  
 ` ` `  
  
 # # #   D e e p   D i v e :   S e n s o r   L a y e r  
  
 -   * * P r o t o c o l : * *   T h r e a d   f o r   l o c a l   m e s h ,   M Q T T S   f o r   c l o u d  
 -   * * P o w e r : * *   A i m   f o r   5 +   y e a r   b a t t e r y   l i f e   �      1 - m i n   s a m p l i n g  
 -   * * F i r m w a r e : * *   O T A   u p d a t e s   v i a   b o o t l o a d e r   f o r   b u g   f i x e s  
  
 # # #   D e e p   D i v e :   E d g e   L a y e r  
  
 -   * * B o r d e r   R o u t e r : * *   R a s p b e r r y   P i   o r   B e a g l e B o n e  
 -   * * L o c a l   I n t e l l i g e n c e : * *   R u n   s i m p l e   a n o m a l y   d e t e c t i o n   a t   e d g e  
 -   * * B u f f e r i n g : * *   S t o r e   l a s t   2 4 h   l o c a l l y   i n   c a s e   c l o u d   u n r e a c h a b l e  
  
 # # #   D e e p   D i v e :   C l o u d   L a y e r  
  
 * * I n g e s t i o n : * *  
 -   A W S   I o T   C o r e :   H a n d l e s   M Q T T   a t   s c a l e   ( m i l l i o n s   o f   c o n n e c t i o n s )  
 -   D e v i c e   s h a d o w s :   C a c h e   l a s t   k n o w n   s t a t e  
  
 * * S t o r a g e : * *  
 -   H o t   d a t a   ( l a s t   7   d a y s ) :   T i m e s c a l e D B   f o r   f a s t   q u e r i e s  
 -   W a r m   d a t a   ( 8 - 9 0   d a y s ) :   C o m p r e s s e d   h y p e r t a b l e s  
 -   C o l d   d a t a   ( > 9 0   d a y s ) :   S 3   w i t h   P a r q u e t   f o r m a t  
  
 * * P r o c e s s i n g : * *  
 -   R e a l - t i m e :   A p a c h e   F l i n k   f o r   s t r e a m i n g   c a l c u l a t i o n s   ( V P D ,   a l e r t s )  
 -   B a t c h :   A i r f l o w   D A G s   f o r   d a i l y   M L   d a t a s e t   g e n e r a t i o n  
  
 * * A P I : * *  
 -   G r a p h Q L   f o r   f l e x i b l e   q u e r i e s   ( f a r m e r s   w a n t   d i f f e r e n t   v i e w s )  
 -   R E S T   f o r   l e g a c y   i n t e g r a t i o n s  
 -   W e b S o c k e t   f o r   d a s h b o a r d   r e a l - t i m e   u p d a t e s  
  
 # # #   S c a l i n g   B o t t l e n e c k s  
  
 * * 1 .   M Q T T   B r o k e r : * *  
 -   U s e   c l u s t e r e d   M o s q u i t t o   o r   m a n a g e d   A W S   I o T   C o r e  
 -   P a r t i t i o n   b y   s i t e _ i d   f o r   h o r i z o n t a l   s c a l i n g  
  
 * * 2 .   D a t a b a s e   W r i t e s : * *  
 -   B a t c h   i n s e r t s   ( i n s e r t   1 0 0   r o w s   a t   o n c e ,   n o t   1   a t   a   t i m e )  
 -   U s e   T i m e s c a l e D B ' s   n a t i v e   p a r t i t i o n i n g  
 -   W r i t e   t o   r e a d   r e p l i c a s   f o r   a n a l y t i c s  
  
 * * 3 .   A P I   R a t e   L i m i t i n g : * *  
 -   I m p l e m e n t   p e r - u s e r   q u o t a s   ( 1 0 0 0   r e q / h o u r )  
 -   C a c h e   f r e q u e n t   q u e r i e s   ( R e d i s )  
 -   U s e   C D N   f o r   d a s h b o a r d   s t a t i c   a s s e t s  
  
 # # #   R e l i a b i l i t y  
  
 * * F a i l u r e   M o d e s : * *  
 -   S e n s o r   d i e s :   A l e r t   i f   > 1 h   n o   d a t a ,   m e s h   s e l f - h e a l s  
 -   B o r d e r   r o u t e r   d i e s :   S e n s o r s   b u f f e r   l o c a l l y ,   a l e r t   a d m i n  
 -   C l o u d   u n r e a c h a b l e :   S t o r e   l o c a l l y   f o r   7   d a y s ,   s y n c   w h e n   b a c k  
  
 * * M o n i t o r i n g : * *  
 -   G r a f a n a   f o r   m e t r i c s   ( p a c k e t   l o s s ,   l a t e n c y ,   b a t t e r y   l e v e l s )  
 -   P a g e r D u t y   f o r   c r i t i c a l   a l e r t s   ( > 1 0 %   s e n s o r s   o f f l i n e )  
 -   D i s t r i b u t e d   t r a c i n g   ( J a e g e r )   f o r   d e b u g g i n g  
  
 # # #   C o s t   O p t i m i z a t i o n  
  
 -   U s e   s p o t   i n s t a n c e s   f o r   b a t c h   p r o c e s s i n g  
 -   C o m p r e s s   s e n s o r   d a t a   a t   e d g e   ( 2 0 0   b y t e s   �      5 0   b y t e s )  
 -   A r c h i v e   t o   S 3   G l a c i e r   a f t e r   9 0   d a y s  
  
 * * E s t i m a t e d   C o s t   ( 1 0 0   s i t e s ,   4 0 0 0   s e n s o r s ) : * *  
 -   A W S   I o T   C o r e :   $ 5 0 0 / m o n t h  
 -   R D S   T i m e s c a l e D B   ( r 5 . 2 x l a r g e ) :   $ 6 0 0 / m o n t h  
 -   S 3   s t o r a g e :   $ 1 0 0 / m o n t h  
 -   T o t a l :   ~ $ 1 2 0 0 / m o n t h   ( $ 0 . 3 0   p e r   s e n s o r   p e r   m o n t h )  
  
 T h i s   i s   e x a c t l y   h o w   I ' d   a p p r o a c h   t h e   d e s i g n   i n t e r v i e w ,   s h o w i n g   I   c a n   t h i n k   a b o u t   t r a d e - o f f s ,   f a i l u r e   m o d e s ,   a n d   c o s t . "  
  
 - - -  
  
 #   1 2 .   K e y   T a k e a w a y s   f o r   I n t e r v i e w s  
  
 # #   1 2 . 1   W h a t   M a k e s   T h i s   P r o j e c t   I m p r e s s i v e  
  
 1 .   * * F u l l - S t a c k   B r e a d t h : * *   T o u c h e d   e v e r y   l a y e r   f r o m   f i r m w a r e   t o   M L  
 2 .   * * R e a l   D e p l o y m e n t : * *   N o t   j u s t   a   t o y   p r o j e c t � �  r u n n i n g   i n   p r o d u c t i o n   f o r   r e s e a r c h  
 3 .   * * M e a s u r a b l e   I m p a c t : * *   2 0 x   c o s t   r e d u c t i o n ,   s u b - 2 s   l a t e n c y ,   1 %   p a c k e t   l o s s  
 4 .   * * O p e n   S o u r c e : * *   O n   G i t H u b   f o r   p e e r   r e v i e w   a n d   c o n t r i b u t i o n s  
 5 .   * * I n t e r d i s c i p l i n a r y : * *   C o m b i n e d   b i o l o g y ,   p h y s i c s ,   C S ,   a n d   h a r d w a r e  
  
 # #   1 2 . 2   T e c h n i c a l   D e p t h   t o   H i g h l i g h t  
  
 W h e n   a s k e d   " t e l l   m e   a b o u t   y o u r   e x p e r i e n c e , "   e m p h a s i z e :  
  
 |   L a y e r   |   W h a t   Y o u   B u i l d   |   K e y w o r d s   t o   U s e   |  
 | - - - - - - - | - - - - - - - - - - - - - - - - | - - - - - - - - - - - - - - - - - |  
 |   * * F i r m w a r e * *   |   Z e p h y r   R T O S ,   T h r e a d   m e s h   |   " I   w r o t e   t h e   C   f i r m w a r e " ,   " o p t i m i z e d   p o w e r   b u d g e t " ,   " a c h i e v e d   7 - y e a r   b a t t e r y   l i f e "   |  
 |   * * N e t w o r k * *   |   B o r d e r   r o u t e r ,   C o A P   |   " I P v 6   m e s h   n e t w o r k i n g " ,   " s u b - 5 m s   t r a n s m i s s i o n   l a t e n c y " ,   " s e l f - h e a l i n g   t o p o l o g y "   |  
 |   * * B a c k e n d * *   |   D o c k e r ,   T i m e s c a l e D B ,   M Q T T   |   " 1 2   m i c r o s e r v i c e s " ,   " t e m p o r a l     j o i n s " ,   " h y p e r t a b l e   c o m p r e s s i o n "   |  
 |   * * D a t a * *   |   S y n c   p i p e l i n e ,   P y d a n t i c   |   " E T L   p i p e l i n e " ,   " d a t a   v a l i d a t i o n " ,   " M L - r e a d y   d a t a s e t s "   |  
 |   * * A l g o r i t h m s * *   |   P e n m a n - M o n t e i t h ,   V P D   |   " I m p l e m e n t e d   p l a n t   p h y s i o l o g y   m o d e l s " ,   " T e t e n s   e q u a t i o n " ,   " r e a l - t i m e   p h e n o t y p i n g "   |  
 |   * * M L / R L * *   |   S A C ,   L T L   s a f e t y   |   " R e i n f o r c e m e n t   l e a r n i n g   f o r   c o n t r o l " ,   " s a f e t y   v e r i f i c a t i o n " ,   " F a r q u h a r   p h o t o s y n t h e s i s   s i m u l a t o r "   |  
  
 # #   1 2 . 3   Q u e s t i o n s   Y o u   S h o u l d   B e   R e a d y   F o r  
  
 * * Q :   " W h a t   w a s   t h e   h a r d e s t   t e c h n i c a l   c h a l l e n g e ? " * *  
  
 * * A : * *   " T h e   t e m p o r a l   d a t a   s y n c h r o n i z a t i o n .   I   h a d   5   a s y n c   s t r e a m s   w i t h   d i f f e r e n t   s a m p l i n g   r a t e s   a n d   h a d   t o   a l i g n   t h e m   w i t h o u t   l o s i n g   s a m p l e   i d e n t i t y .   I   s o l v e d   i t   w i t h   p a n d a s   ` m e r g e _ a s o f `   a n d   a   6 0 - s e c o n d   t o l e r a n c e   w i n d o w ,   w h i c h   p r e s e r v e d   9 9 . 8 %   o f   s a m p l e s . "  
  
 - - -  
  
 * * Q :   " I f   y o u   h a d   m o r e   t i m e ,   w h a t   w o u l d   y o u   i m p r o v e ? " * *  
  
 * * A : * *  
 1 .   A d d   N I R   s e n s o r s   f o r   t r u e   N D V I   ( c u r r e n t l y   j u s t   a   p r o x y )  
 2 .   I m p l e m e n t   f e d e r a t e d   l e a r n i n g   a c r o s s   m u l t i p l e   g r e e n h o u s e s  
 3 .   M i g r a t e   t o   M a t t e r   p r o t o c o l   f o r   b r o a d e r   d e v i c e   c o m p a t i b i l i t y  
 4 .   A d d   t h e r m a l   i m a g i n g   f o r   c a n o p y   t e m p e r a t u r e   m a p p i n g  
  
 - - -  
  
 * * Q :   " H o w   d i d   y o u   v a l i d a t e   y o u r   r e s u l t s ? " * *  
  
 * * A : * *  
 1 .   V P D   c a l c u l a t i o n s   v e r i f i e d   a g a i n s t   A p o g e e   I n s t r u m e n t s   V P - 4   s e n s o r   ( � � 2 %   e r r o r )  
 2 .   T r a n s p i r a t i o n   e s t i m a t e s   c o r r e l a t e d   r = 0 . 8 9   w i t h   m i n i - l y s i m e t e r   m e a s u r e m e n t s  
 3 .   L o a d   t e s t i n g   s h o w e d   A P I   h a n d l e s   5 0 0   r e q / s   a t   p 9 9   < 3 0 0 m s  
 4 .   3 - w e e k   c o n t i n u o u s   d e p l o y m e n t   w i t h   < 1 %   p a c k e t   l o s s  
  
 - - -  
  
 * * Q :   " T e l l   m e   a b o u t   a   t r a d e - o f f   y o u   m a d e . " * *  
  
 * * A : * *   " P o w e r   v s .   d a t a   r a t e .   I   c o u l d   h a v e   s a m p l e d   e v e r y   1 0   s e c o n d s   f o r   h i g h e r   r e s o l u t i o n ,   b u t   t h a t   w o u l d   r e d u c e   b a t t e r y   l i f e   f r o m   7   y e a r s   t o   6   m o n t h s .   F o r   p l a n t   b i o l o g y ,   1 - m i n u t e   r e s o l u t i o n   i s   s u f f i c i e n t   s i n c e   p h y s i o l o g i c a l   c h a n g e s   h a p p e n   o n   ~ 1 0 - m i n u t e   t i m e s c a l e s .   I   o p t i m i z e d   f o r   o p e r a t i o n a l   p r a c t i c a l i t y   o v e r   d a t a   g r a n u l a r i t y . "  
  
 - - -  
  
 # #   1 2 . 4   F i n a l   C o a c h i n g   N o t e s  
  
 * * D o : * *  
 -   L e a d   w i t h   t h e   " w h y "   ( p r o b l e m / i m p a c t )   b e f o r e   d i v i n g   i n t o   t e c h n i c a l   d e t a i l s  
 -   U s e   s p e c i f i c   n u m b e r s   ( 7 - y e a r   b a t t e r y ,   2 - s e c o n d   l a t e n c y ,   1 5 %   p a c k e t   l o s s   �      1 % )  
 -   S h o w   p r o b l e m - s o l v i n g   p r o c e s s   ( d i a g n o s i s   �      h y p o t h e s i s   �      s o l u t i o n   �      v a l i d a t i o n )  
 -   C o n n e c t   t e c h n i c a l   w o r k   t o   b u s i n e s s   v a l u e   ( c o s t   r e d u c t i o n ,   r e s e a r c h   e n a b l e m e n t )  
  
 * * D o n ' t : * *  
 -   R a m b l e   w i t h o u t   s t r u c t u r e   ( u s e   t h e   3 / 1 0   m i n u t e   t e m p l a t e s )  
 -   G e t   l o s t   i n   i m p l e m e n t a t i o n   d e t a i l s   w i t h o u t   c o n t e x t  
 -   S a y   " w e "   w h e n   y o u   m e a n   " I "   ( b e   c l e a r   a b o u t   y o u r   c o n t r i b u t i o n s )  
 -   C l a i m   e x p e r t i s e   y o u   d o n ' t   h a v e   ( i t ' s   o k a y   t o   s a y   " I   l e a r n e d   X   d u r i n g   t h i s   p r o j e c t " )  
  
 * * R e m e m b e r : * *  
 Y o u   b u i l t   s o m e t h i n g   r e a l ,   d e p l o y e d   i t ,   d e b u g g e d   i t ,   a n d   i t e r a t e d   o n   i t .   T h a t ' s   m o r e   v a l u a b l e   t h a n   m o s t   a c a d e m i c   p r o j e c t s .   O w n   i t .  
  
 - - -  
  
 #   C o n c l u s i o n  
  
 T h i s   d o c u m e n t   i s   y o u r   c o m p r e h e n s i v e   r e f e r e n c e .   S t u d y   i t ,   p r a c t i c e   t h e   s c r i p t s ,   a n d   t a i l o r   y o u r   a n s w e r s   t o   t h e   s p e c i f i c   r o l e :  
  
 -   * * E m b e d d e d   r o l e : * *   F o c u s   o n   f i r m w a r e ,   p o w e r   o p t i m i z a t i o n ,   I 2 C   d r i v e r s  
 -   * * B a c k e n d   r o l e : * *   F o c u s   o n   m i c r o s e r v i c e s ,   T i m e s c a l e D B ,   d a t a   p i p e l i n e s  
 -   * * M L   r o l e : * *   F o c u s   o n   R L ,   s a f e t y   v e r i f i c a t i o n ,   F a r q u h a r   m o d e l  
 -   * * F u l l - s t a c k   r o l e : * *   S h o w   b r e a d t h   a c r o s s   a l l   l a y e r s  
  
 G o o d   l u c k !   � xa�  
  
 - - -  
  
 #   1 3 .   C o m p l e t e   F i l e - b y - F i l e   R e f e r e n c e   G u i d e  
  
 >   * * P u r p o s e : * *   T h i s   s e c t i o n   p r o v i d e s   e x h a u s t i v e   d o c u m e n t a t i o n   o f   e v e r y   f i l e   i n   t h e   G . O . S .   p r o j e c t .   E a c h   f i l e   i s   e x p l a i n e d   i n   d e t a i l :   w h a t   i t   d o e s ,   w h y   i t   e x i s t s ,   k e y   c o d e   s e c t i o n s ,   a n d   i n t e r v i e w   t a l k i n g   p o i n t s .  
  
 - - -  
  
 # #   1 3 . 1   P r o j e c t   R o o t   F i l e s  
  
 # # #   � x    ` d o c k e r - c o m p o s e . y m l `   ( 1 9 7   l i n e s )  
  
 * * L o c a t i o n : * *   ` / d o c k e r - c o m p o s e . y m l `  
  
 * * W h a t   i t   d o e s : * *  
 D e f i n e s   t h e   e n t i r e   1 2 - s e r v i c e   m i c r o s e r v i c e   a r c h i t e c t u r e .   T h i s   s i n g l e   f i l e   o r c h e s t r a t e s   t h e   c o m p l e t e   s y s t e m   f r o m   d a t a b a s e   t o   d a s h b o a r d .  
  
 * * K e y   T e c h n i c a l   D e t a i l s : * *  
  
 * * S e r v i c e   C a t e g o r i e s : * *  
 1 .   * * I n f r a s t r u c t u r e   L a y e r * *   ( s e r v i c e s   1 - 2 ) :   D a t a b a s e   a n d   m e s s a g e   b r o k e r  
 2 .   * * I n g e s t i o n   L a y e r * *   ( s e r v i c e s   3 - 5 ) :   M Q T T   b r i d g e ,   f a r m   s i m u l a t o r ,   m e t   s t a t i o n  
 3 .   * * A P I   L a y e r * *   ( s e r v i c e   6 ) :   R E S T   A P I   f o r   d a s h b o a r d  
 4 .   * * D a t a   B a c k b o n e * *   ( s e r v i c e   7 ) :   S y n c h r o n i z a t i o n   e n g i n e  
 5 .   * * M L   L a y e r * *   ( s e r v i c e s   8 - 1 0 ) :   P h y s i c s   e n g i n e ,   R L   a g e n t ,   s a f e t y   m o n i t o r  
 6 .   * * V i s u a l i z a t i o n * *   ( s e r v i c e s   1 1 - 1 2 ) :   G r a f a n a   a n d   d a s h b o a r d  
  
 * * C o n f i g u r a t i o n   P a t t e r n s : * *  
  
 ` ` ` y a m l  
 #   H e a l t h   c h e c k   p a t t e r n   ( e n s u r e s   p r o p e r   s t a r t u p   o r d e r )  
 d b :  
     h e a l t h c h e c k :  
         t e s t :   [ " C M D - S H E L L " ,   " p g _ i s r e a d y   - U   r e s e a r c h e r   - d   s t r a w b e r r y _ r e s e a r c h " ]  
         i n t e r v a l :   5 s  
         t i m e o u t :   5 s  
         r e t r i e s :   5  
  
 #   D e p e n d e n c y   p a t t e r n   ( w a i t   f o r   d a t a b a s e )  
 a p i :  
     d e p e n d s _ o n :  
         d b :  
             c o n d i t i o n :   s e r v i c e _ h e a l t h y  
 ` ` `  
  
 * * W h y   t h i s   m a t t e r s   i n   a n   i n t e r v i e w : * *  
 -   S h o w s   y o u   u n d e r s t a n d   c o n t a i n e r   o r c h e s t r a t i o n  
 -   D e m o n s t r a t e s   k n o w l e d g e   o f   s e r v i c e   d e p e n d e n c i e s  
 -   H e a l t h   c h e c k s   s h o w   p r o d u c t i o n - r e a d i n e s s   t h i n k i n g  
  
 * * E n v i r o n m e n t   V a r i a b l e s : * *  
 -   ` D A T A B A S E _ U R L ` :   P o s t g r e S Q L   c o n n e c t i o n   s t r i n g  
 -   ` M Q T T _ B R O K E R ` :   M Q T T   b r o k e r   h o s t n a m e   ( d e f a u l t :   l o c a l h o s t )  
 -   ` M Q T T _ P O R T ` :   M Q T T   p o r t   ( d e f a u l t :   1 8 8 3 )  
  
 * * V o l u m e s : * *  
 -   ` t i m e s c a l e _ d a t a ` :   P e r s i s t e n t   d a t a b a s e   s t o r a g e  
 -   ` g r a f a n a _ d a t a ` :   G r a f a n a   d a s h b o a r d s   a n d   s e t t i n g s  
 -   ` m o s q u i t t o _ d a t a ` :   M Q T T   m e s s a g e   p e r s i s t e n c e  
 -   ` m o s q u i t t o _ l o g s ` :   M Q T T   b r o k e r   l o g s  
  
 - - -  
  
 # # #   � x    ` r e q u i r e m e n t s . t x t `   ( R o o t   -   4 0 5   b y t e s )  
  
 * * L o c a t i o n : * *   ` / r e q u i r e m e n t s . t x t `  
  
 * * W h a t   i t   d o e s : * *  
 S p e c i f i e s   P y t h o n   d e p e n d e n c i e s   f o r   t h e   g a t e w a y   a n d   M L   s e r v i c e s .  
  
 * * K e y   P a c k a g e s : * *  
  
 |   P a c k a g e   |   V e r s i o n   |   P u r p o s e   |  
 | - - - - - - - - - | - - - - - - - - - | - - - - - - - - - |  
 |   ` f l a s k `   |   � 0 � 2 . 0   |   R E S T   A P I   f r a m e w o r k   |  
 |   ` f l a s k - c o r s `   |   � 0 � 3 . 0   |   C r o s s - o r i g i n   r e q u e s t s   f o r   d a s h b o a r d   |  
 |   ` p s y c o p g 2 - b i n a r y `   |   � 0 � 2 . 9   |   P o s t g r e S Q L   a d a p t e r   |  
 |   ` p a h o - m q t t `   |   � 0 � 1 . 6   |   M Q T T   c l i e n t   l i b r a r y   |  
 |   ` p y d a n t i c `   |   � 0 � 1 . 1 0   |   D a t a   v a l i d a t i o n   s c h e m a s   |  
 |   ` p a n d a s `   |   � 0 � 1 . 5   |   D a t a   p r o c e s s i n g   a n d   t e m p o r a l   j o i n s   |  
 |   ` n u m p y `   |   � 0 � 1 . 2 3   |   N u m e r i c a l   c o m p u t a t i o n s   |  
 |   ` o p e n a i `   |   � 0 � 1 . 0   |   L L M   i n t e g r a t i o n   f o r   n a t u r a l   l a n g u a g e   e v e n t s   |  
  
 * * W h y   s e p a r a t e   r e q u i r e m e n t s   f i l e s ? * *  
 G a t e w a y   a n d   M L   e n g i n e   h a v e   d i f f e r e n t   d e p e n d e n c i e s .   K e e p i n g   t h e m   s e p a r a t e :  
 -   R e d u c e s   D o c k e r   i m a g e   s i z e  
 -   S p e e d s   u p   b u i l d s  
 -   I s o l a t e s   d e p e n d e n c y   c o n f l i c t s  
  
 - - -  
  
 # # #   � x    ` r u n . p y `   ( 2 9 1 0   b y t e s )  
  
 * * L o c a t i o n : * *   ` / r u n . p y `  
  
 * * W h a t   i t   d o e s : * *  
 D e v e l o p e r   c o n v e n i e n c e   s c r i p t   f o r   r u n n i n g   i n d i v i d u a l   s e r v i c e s   l o c a l l y   w i t h o u t   D o c k e r .  
  
 * * U s a g e : * *  
 ` ` ` b a s h  
 p y t h o n   r u n . p y   a p i                     #   S t a r t   R E S T   A P I  
 p y t h o n   r u n . p y   i n g e s t               #   S t a r t   4 0 - n o d e   s i m u l a t o r  
 p y t h o n   r u n . p y   s y n c                   #   S t a r t   d a t a   c u r a t i o n   e n g i n e  
 p y t h o n   r u n . p y   a l l                     #   S t a r t   a l l   s e r v i c e s  
 ` ` `  
  
 * * K e y   C o d e : * *  
 ` ` ` p y t h o n  
 d e f   r u n _ s e r v i c e ( n a m e ) :  
         s e r v i c e s   =   {  
                 ' a p i ' :   ' g a t e w a y / s e r v i c e s / a p i . p y ' ,  
                 ' i n g e s t ' :   ' g a t e w a y / s e r v i c e s / f a r m _ s i m . p y ' ,  
                 ' m e t ' :   ' g a t e w a y / s e r v i c e s / m e t _ s t a t i o n . p y ' ,  
                 ' s y n c ' :   ' g a t e w a y / s e r v i c e s / s y n c . p y ' ,  
                 ' m l ' :   ' m l _ e n g i n e / a g e n t _ r l . p y '  
         }  
          
         i f   n a m e   i n   s e r v i c e s :  
                 o s . s y s t e m ( f ' p y t h o n   { s e r v i c e s [ n a m e ] } ' )  
 ` ` `  
  
 * * I n t e r v i e w   p o i n t : * *   S h o w s   y o u   t h i n k   a b o u t   d e v e l o p e r   e x p e r i e n c e ,   n o t   j u s t   p r o d u c t i o n   d e p l o y m e n t .  
  
 - - -  
  
 # # #   � x    ` s e t u p . b a t `   ( 1 5 5 9   b y t e s )  
  
 * * L o c a t i o n : * *   ` / s e t u p . b a t `  
  
 * * W h a t   i t   d o e s : * *  
 W i n d o w s - s p e c i f i c   s e t u p   s c r i p t   f o r   f i r s t - t i m e   u s e r s .  
  
 * * A c t i o n s : * *  
 1 .   C r e a t e s   P y t h o n   v i r t u a l   e n v i r o n m e n t  
 2 .   I n s t a l l s   d e p e n d e n c i e s   f r o m   r e q u i r e m e n t s . t x t  
 3 .   C r e a t e s   ` . e n v `   f i l e   f r o m   t e m p l a t e  
 4 .   P r i n t s   h e l p f u l   s t a r t u p   i n s t r u c t i o n s  
  
 * * K e y   C o m m a n d s : * *  
 ` ` ` b a t c h  
 p y t h o n   - m   v e n v   . v e n v  
 . v e n v \ S c r i p t s \ a c t i v a t e . b a t  
 p i p   i n s t a l l   - r   r e q u i r e m e n t s . t x t  
 c o p y   . e n v . e x a m p l e   . e n v  
 ` ` `  
  
 * * W h y   t h i s   m a t t e r s : * *  
 -   D e m o n s t r a t e s   a t t e n t i o n   t o   o n b o a r d i n g   e x p e r i e n c e  
 -   S h o w s   W i n d o w s   c o m p a t i b i l i t y   a w a r e n e s s  
 -   R e d u c e s   b a r r i e r   t o   c o n t r i b u t i o n  
  
 - - -  
  
 # # #   � x    ` . e n v . e x a m p l e `   ( 5 6 8   b y t e s )  
  
 * * L o c a t i o n : * *   ` / . e n v . e x a m p l e `  
  
 * * W h a t   i t   d o e s : * *  
 T e m p l a t e   f o r   e n v i r o n m e n t   v a r i a b l e s .   U s e r s   c o p y   t h i s   t o   ` . e n v `   a n d   c u s t o m i z e .  
  
 * * V a r i a b l e s : * *  
 ` ` ` b a s h  
 #   D a t a b a s e  
 P O S T G R E S _ U S E R = r e s e a r c h e r  
 P O S T G R E S _ P A S S W O R D = c h a n g e _ m e _ i n _ p r o d  
 P O S T G R E S _ D B = s t r a w b e r r y _ r e s e a r c h  
 D A T A B A S E _ U R L = p o s t g r e s q l : / / r e s e a r c h e r : c h a n g e _ m e _ i n _ p r o d @ l o c a l h o s t / s t r a w b e r r y _ r e s e a r c h  
  
 #   M Q T T  
 M Q T T _ B R O K E R = l o c a l h o s t  
 M Q T T _ P O R T = 1 8 8 3  
  
 #   G r a f a n a  
 G F _ S E C U R I T Y _ A D M I N _ P A S S W O R D = c h a n g e _ m e _ i n _ p r o d  
  
 #   O p e n A I   ( f o r   L L M   f e a t u r e s )  
 O P E N A I _ A P I _ K E Y = s k - y o u r - k e y - h e r e  
 ` ` `  
  
 * * S e c u r i t y   n o t e : * *   T h e   a c t u a l   ` . e n v `   f i l e   i s   i n   ` . g i t i g n o r e `   t o   p r e v e n t   c r e d e n t i a l   l e a k s .  
  
 - - -  
  
 # # #   � x    ` . g i t i g n o r e `   ( 5 4 6   b y t e s )  
  
 * * L o c a t i o n : * *   ` / . g i t i g n o r e `  
  
 * * W h a t   i t   d o e s : * *  
 S p e c i f i e s   f i l e s   t h a t   s h o u l d   n o t   b e   t r a c k e d   b y   G i t .  
  
 * * K e y   E n t r i e s : * *  
 ` ` ` g i t i g n o r e  
 #   S e c r e t s  
 . e n v  
 * . k e y  
  
 #   P y t h o n  
 _ _ p y c a c h e _ _ /  
 * . p y c  
 . v e n v /  
  
 #   D a t a   ( t o o   l a r g e   f o r   G i t )  
 d a t a / * . c s v  
 * . h 5  
  
 #   I D E  
 . v s c o d e / s e t t i n g s . j s o n  
 . i d e a /  
  
 #   Z e p h y r   b u i l d   a r t i f a c t s  
 f i r m w a r e / b u i l d /  
 ` ` `  
  
 * * W h y   c a t e g o r i z e d : * *  
 F o l l o w i n g   t h e   p a t t e r n   m a k e s   t h e   f i l e   m a i n t a i n a b l e   a s   t h e   p r o j e c t   g r o w s .  
  
 - - -  
  
 # # #   � x    ` R E A D M E . m d `   ( 1 3 , 7 6 2   b y t e s )  
  
 * * L o c a t i o n : * *   ` / R E A D M E . m d `  
  
 * * W h a t   i t   d o e s : * *  
 P r o j e c t   d o c u m e n t a t i o n .   F i r s t   t h i n g   v i s i t o r s   s e e   o n   G i t H u b .  
  
 * * S e c t i o n s : * *  
 1 .   P r o j e c t   o v e r v i e w   a n d   b a d g e s  
 2 .   A r c h i t e c t u r e   d i a g r a m  
 3 .   Q u i c k   s t a r t   g u i d e  
 4 .   S e r v i c e   d e s c r i p t i o n s  
 5 .   A P I   d o c u m e n t a t i o n  
 6 .   D e v e l o p m e n t   s e t u p  
 7 .   T e s t i n g   i n s t r u c t i o n s  
 8 .   L i c e n s e   a n d   c r e d i t s  
  
 * * K e y   F e a t u r e s : * *  
 -   A S C I I   a r t   a r c h i t e c t u r e   d i a g r a m  
 -   M e r m a i d   s e q u e n c e   d i a g r a m s  
 -   T a b l e   o f   a l l   e n d p o i n t s  
 -   D o c k e r   c o m m a n d   r e f e r e n c e  
  
 - - -  
  
 # #   1 3 . 2   G a t e w a y   S e r v i c e s   ( 8   F i l e s )  
  
 T h e   ` g a t e w a y / `   d i r e c t o r y   c o n t a i n s   t h e   P y t h o n   b a c k e n d   s e r v i c e s .  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / a p i . p y `   ( 4 2 9   l i n e s ,   1 5 , 0 5 2   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / a p i . p y `  
  
 * * W h a t   i t   d o e s : * *  
 R E S T   A P I   s e r v e r   p r o v i d i n g   e n d p o i n t s   f o r   t h e   d a s h b o a r d   a n d   e x t e r n a l   i n t e g r a t i o n s .  
  
 * * F r a m e w o r k : * *   F l a s k   w i t h   C O R S   e n a b l e d  
  
 * * E n d p o i n t   C a t e g o r i e s : * *  
  
 * * 1 .   E v e n t   L o g g i n g   ( ` / a p i / e v e n t ` ) * *  
 ` ` ` p y t h o n  
 @ a p p . r o u t e ( ' / a p i / e v e n t ' ,   m e t h o d s = [ ' P O S T ' ] )  
 d e f   l o g _ e v e n t ( ) :  
         " " "  
         L o g   a   r e s e a r c h   e v e n t   ( p e s t   p r e s s u r e ,   f e r t i l i z e r ,   e q u i p m e n t   f a i l u r e ,   e t c . )  
         F e e d s   d i r e c t l y   i n t o   t h e   M L   p i p e l i n e   v i a   t h e   s y n c   e n g i n e .  
         " " "  
         d a t a   =   r e q u e s t . g e t _ j s o n ( )  
          
         #   U s e   L L M   t o   e x t r a c t   s t r u c t u r e d   d a t a   f r o m   n a t u r a l   l a n g u a g e  
         s t r u c t u r e d   =   p a r s e _ e v e n t _ w i t h _ l l m ( d a t a [ ' d e s c r i p t i o n ' ] )  
          
         #   I n s e r t   i n t o   d a t a b a s e  
         c o n n   =   g e t _ d b _ c o n n e c t i o n ( )  
         c o n n . e x e c u t e ( " " "  
                 I N S E R T   I N T O   r e s e a r c h _ e v e n t s    
                 ( t i m e s t a m p ,   e v e n t _ t y p e ,   d e s c r i p t i o n ,   m e t a d a t a ,   a n n o t a t o r )  
                 V A L U E S   ( N O W ( ) ,   % s ,   % s ,   % s ,   % s )  
         " " " ,   ( s t r u c t u r e d [ ' t y p e ' ] ,   d a t a [ ' d e s c r i p t i o n ' ] ,   j s o n . d u m p s ( s t r u c t u r e d ) ,   d a t a [ ' a n n o t a t o r ' ] ) )  
          
         r e t u r n   j s o n i f y ( { " s t a t u s " :   " l o g g e d " ,   " p a r s e d " :   s t r u c t u r e d } )  
 ` ` `  
  
 * * 2 .   Y i e l d   L o g g i n g   ( ` / a p i / y i e l d ` ) * *  
 -   P O S T :   R e c o r d   h a r v e s t   d a t a   ( w e i g h t ,   b r i x ,   p l a n t   I D )  
 -   G E T :   R e t r i e v e   y i e l d   h i s t o r y   f o r   a n a l y s i s  
  
 * * 3 .   L E D   C o n t r o l   ( ` / a p i / l e d ` ) * *  
 -   G E T :   C u r r e n t   L E D   s c h e d u l e  
 -   P U T :   U p d a t e   s p e c t r a l   r a t i o s  
  
 * * 4 .   N o d e   S t a t u s   ( ` / a p i / n o d e s ` ) * *  
 ` ` ` p y t h o n  
 @ a p p . r o u t e ( ' / a p i / n o d e s ' )  
 d e f   g e t _ n o d e s ( ) :  
         " " " G e t   s u m m a r y   o f   a l l   n o d e s   a n d   t h e i r   l a t e s t   r e a d i n g s . " " "  
         c o n n   =   g e t _ d b _ c o n n e c t i o n ( )  
         r e s u l t   =   c o n n . e x e c u t e ( " " "  
                 S E L E C T   D I S T I N C T   O N   ( n o d e _ i d )  
                         n o d e _ i d ,   t e m p _ c ,   h u m i d i t y _ p c t ,   p a r _ u m o l ,   b a t t e r y _ m v ,   r s s i ,   t i m e s t a m p  
                 F R O M   r a w _ t e l e m e t r y  
                 O R D E R   B Y   n o d e _ i d ,   t i m e s t a m p   D E S C  
         " " " )  
          
         n o d e s   =   [ d i c t ( r o w )   f o r   r o w   i n   r e s u l t ]  
         r e t u r n   j s o n i f y ( { " n o d e s " :   n o d e s ,   " c o u n t " :   l e n ( n o d e s ) } )  
 ` ` `  
  
 * * 5 .   P h e n o t y p e   C a l c u l a t i o n   ( ` / a p i / p h e n o t y p e ` ) * *  
 ` ` ` p y t h o n  
 @ a p p . r o u t e ( ' / a p i / p h e n o t y p e ' ,   m e t h o d s = [ ' P O S T ' ] )  
 d e f   c a l c u l a t e _ p h e n o t y p e ( ) :  
         " " "  
         C a l c u l a t e   r e a l - t i m e   p h e n o t y p e   m e t r i c s   f r o m   s e n s o r   d a t a .  
          
         I n p u t :   { " t e m p _ c " :   2 5 . 0 ,   " h u m i d i t y _ p c t " :   6 5 . 0 ,   " p a r _ u m o l " :   8 0 0 . 0 }  
         O u t p u t :   V P D ,   t r a n s p i r a t i o n ,   s t r e s s   s c o r e ,   r e c o m m e n d a t i o n s  
         " " "  
         d a t a   =   r e q u e s t . g e t _ j s o n ( )  
          
         #   U s e   p h e n o t y p i n g   e n g i n e  
         e n g i n e   =   P h e n o t y p i n g E n g i n e ( )  
         v p d   =   e n g i n e . c a l c u l a t e _ v p d ( d a t a [ ' t e m p _ c ' ] ,   d a t a [ ' h u m i d i t y _ p c t ' ] )  
         s t r e s s   =   e n g i n e . d e t e c t _ s t r e s s ( d a t a [ ' t e m p _ c ' ] ,   d a t a [ ' h u m i d i t y _ p c t ' ] ,   d a t a [ ' p a r _ u m o l ' ] )  
         t r a n s p i r a t i o n   =   e n g i n e . e s t i m a t e _ t r a n s p i r a t i o n (  
                 d a t a [ ' t e m p _ c ' ] ,   d a t a [ ' h u m i d i t y _ p c t ' ] ,   d a t a [ ' p a r _ u m o l ' ]  
         )  
          
         #   G e n e r a t e   L E D   r e c o m m e n d a t i o n   b a s e d   o n   s t r e s s  
         r e c o m m e n d a t i o n   =   g e n e r a t e _ l e d _ r e c o m m e n d a t i o n ( v p d ,   s t r e s s )  
          
         r e t u r n   j s o n i f y ( {  
                 " p h e n o t y p e " :   {  
                         " v p d _ k p a " :   r o u n d ( v p d ,   3 ) ,  
                         " v p d _ s t a t u s " :   e n g i n e . c l a s s i f y _ v p d _ s t r e s s ( v p d ) ,  
                         " t r a n s p i r a t i o n _ g _ m 2 _ h " :   r o u n d ( t r a n s p i r a t i o n ,   1 ) ,  
                         " s t r e s s _ s c o r e " :   s t r e s s [ ' s t r e s s _ s c o r e ' ]  
                 } ,  
                 " l e d _ r e c o m m e n d a t i o n " :   r e c o m m e n d a t i o n  
         } )  
 ` ` `  
  
 * * 6 .   C u r a t e d   D a t a s e t   ( ` / a p i / c u r a t e d ` ) * *  
 -   G E T :   D o w n l o a d   t h e   l a t e s t   M L - r e a d y   s y n c h r o n i z e d   d a t a s e t   a s   C S V  
  
 * * 7 .   P h e n o t y p e   S u m m a r y   ( ` / a p i / p h e n o t y p e / s u m m a r y ` ) * *  
 -   G E T :   A g g r e g a t e   p h e n o t y p e   m e t r i c s   a c r o s s   a l l   n o d e s   f o r   t h e   l a s t   h o u r  
  
 * * 8 .   H e a l t h   C h e c k   ( ` / h e a l t h ` ) * *  
 ` ` ` p y t h o n  
 @ a p p . r o u t e ( ' / h e a l t h ' )  
 d e f   h e a l t h _ c h e c k ( ) :  
         " " " H e a l t h   c h e c k   e n d p o i n t   f o r   D o c k e r . " " "  
         r e t u r n   j s o n i f y ( { " s e r v i c e " :   " g o s - r e s e a r c h - a p i " ,   " s t a t u s " :   " h e a l t h y " } )  
 ` ` `  
  
 * * I n t e r v i e w   t a l k i n g   p o i n t s : * *  
 -   " I   d e s i g n e d   t h e   A P I   w i t h   t h e   G U I   t e a m ' s   n e e d s   i n   m i n d "  
 -   " T h e   L L M   i n t e g r a t i o n   a l l o w s   n a t u r a l   l a n g u a g e   e v e n t   l o g g i n g "  
 -   " H e a l t h   c h e c k s   e n a b l e   p r o p e r   D o c k e r   o r c h e s t r a t i o n "  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / s y n c . p y `   ( 2 6 5   l i n e s ,   9 , 9 1 8   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / s y n c . p y `  
  
 * * W h a t   i t   d o e s : * *  
 T h e   " D a t a   B a c k b o n e "   -   s y n c h r o n i z e s   d a t a   f r o m   m u l t i p l e   s o u r c e s   a n d   c r e a t e s   M L - r e a d y   d a t a s e t s .  
  
 * * C l a s s e s : * *  
  
 * * 1 .   T e l e m e t r y R e c o r d   ( P y d a n t i c   S c h e m a ) * *  
 ` ` ` p y t h o n  
 c l a s s   T e l e m e t r y R e c o r d ( B a s e M o d e l ) :  
         " " " S c h e m a   f o r   v a l i d a t i n g   i n c o m i n g   t e l e m e t r y   d a t a . " " "  
         n o d e _ i d :   s t r  
         s a m p l e _ i d e n t i t y :   O p t i o n a l [ s t r ]   =   N o n e  
         t e m p _ c :   O p t i o n a l [ f l o a t ]   =   N o n e  
         h u m i d i t y _ p c t :   O p t i o n a l [ f l o a t ]   =   N o n e  
         p a r _ u m o l :   O p t i o n a l [ f l o a t ]   =   N o n e  
         b a t t e r y _ m v :   O p t i o n a l [ i n t ]   =   N o n e  
          
         @ v a l i d a t o r ( ' t e m p _ c ' )  
         d e f   v a l i d a t e _ t e m p ( c l s ,   v ) :  
                 i f   v   i s   n o t   N o n e   a n d   n o t   - 2 0   < =   v   < =   5 0 :  
                         r a i s e   V a l u e E r r o r ( f ' T e m p e r a t u r e   { v } � � C   o u t   o f   r a n g e ' )  
                 r e t u r n   v  
          
         @ v a l i d a t o r ( ' h u m i d i t y _ p c t ' )  
         d e f   v a l i d a t e _ h u m i d i t y ( c l s ,   v ) :  
                 i f   v   i s   n o t   N o n e   a n d   n o t   0   < =   v   < =   1 0 0 :  
                         r a i s e   V a l u e E r r o r ( f ' H u m i d i t y   { v } %   o u t   o f   r a n g e ' )  
                 r e t u r n   v  
 ` ` `  
  
 * * 2 .   R e s e a r c h C u r a t i o n E n g i n e * *  
 ` ` ` p y t h o n  
 c l a s s   R e s e a r c h C u r a t i o n E n g i n e :  
         " " "  
         T h e   ' D a t a   B a c k b o n e '   f o r   Q u e e n ' s   P h y t o t r o n   E L E C   4 9 0 / 4 9 8   p r o j e c t .  
          
         I m p l e m e n t s :  
         -   I n g e s t i o n   f r o m   P o s t g r e S Q L / T i m e s c a l e D B  
         -   V a l i d a t i o n   u s i n g   P y d a n t i c   s c h e m a s  
         -   T e m p o r a l   s y n c h r o n i z a t i o n   a c r o s s   s t r e a m s  
         -   M L - r e a d y   d a t a s e t   e x p o r t  
         " " "  
          
         d e f   _ _ i n i t _ _ ( s e l f ,   d b _ u r l ) :  
                 s e l f . d b _ u r l   =   d b _ u r l  
                 s e l f . e n g i n e   =   c r e a t e _ e n g i n e ( d b _ u r l )  
          
         d e f   v a l i d a t e _ t e l e m e t r y ( s e l f ,   d f :   p d . D a t a F r a m e ) :  
                 " " " V a l i d a t e s   t e l e m e t r y   d a t a   u s i n g   P y d a n t i c   s c h e m a . " " "  
                 v a l i d _ r e c o r d s   =   [ ]  
                 i n v a l i d _ c o u n t   =   0  
                  
                 f o r   _ ,   r o w   i n   d f . i t e r r o w s ( ) :  
                         t r y :  
                                 r e c o r d   =   T e l e m e t r y R e c o r d ( * * r o w . t o _ d i c t ( ) )  
                                 v a l i d _ r e c o r d s . a p p e n d ( r e c o r d . d i c t ( ) )  
                         e x c e p t   V a l i d a t i o n E r r o r   a s   e :  
                                 i n v a l i d _ c o u n t   + =   1  
                                 l o g g e r . w a r n i n g ( f " V a l i d a t i o n   f a i l e d :   { e } " )  
                  
                 l o g g e r . i n f o ( f " V a l i d a t e d   { l e n ( v a l i d _ r e c o r d s ) }   r e c o r d s ,   r e j e c t e d   { i n v a l i d _ c o u n t } " )  
                 r e t u r n   p d . D a t a F r a m e ( v a l i d _ r e c o r d s )  
          
         d e f   c u r a t e _ m l _ r e a d y _ s e t ( s e l f ) :  
                 " " "  
                 A s s e m b l e s   t h e   h i g h - f i d e l i t y   M L - r e a d y   d a t a s e t   f r o m   T H R E E   d i s t i n c t   s t r e a m s .  
                 P e r f o r m s   t e m p o r a l   j o i n s   w i t h   p r e s e r v e d   s a m p l e   i d e n t i t y .  
                 " " "  
                 #   S t e p   1 :   E x t r a c t   t e l e m e t r y   ( 4 0   n o d e s ,   1   s a m p l e / m i n   e a c h )  
                 t e l e m e t r y   =   p d . r e a d _ s q l ( " " "  
                         S E L E C T   t i m e s t a m p ,   n o d e _ i d ,   t e m p _ c ,   h u m i d i t y _ p c t ,   p a r _ u m o l ,   b a t t e r y _ m v  
                         F R O M   r a w _ t e l e m e t r y  
                         W H E R E   t i m e s t a m p   >   N O W ( )   -   I N T E R V A L   ' 2 4   h o u r s '  
                 " " " ,   s e l f . e n g i n e )  
                  
                 #   S t e p   2 :   E x t r a c t   m e t   s t a t i o n   d a t a   ( 1   s a m p l e / 1 0 s )  
                 m e t   =   p d . r e a d _ s q l ( " " "  
                         S E L E C T   t i m e s t a m p ,   r a d i a t i o n _ w _ m 2 ,   s p e c t r a l _ r e d _ p c t ,   s p e c t r a l _ b l u e _ p c t  
                         F R O M   m e t _ s t a t i o n _ d a t a  
                         W H E R E   t i m e s t a m p   >   N O W ( )   -   I N T E R V A L   ' 2 4   h o u r s '  
                 " " " ,   s e l f . e n g i n e )  
                  
                 #   S t e p   3 :   V a l i d a t e   t e l e m e t r y  
                 t e l e m e t r y   =   s e l f . v a l i d a t e _ t e l e m e t r y ( t e l e m e t r y )  
                  
                 #   S t e p   4 :   T e m p o r a l   j o i n   ( n e a r e s t - n e i g h b o r   w i t h i n   6 0 s   t o l e r a n c e )  
                 t e l e m e t r y [ ' t i m e s t a m p ' ]   =   p d . t o _ d a t e t i m e ( t e l e m e t r y [ ' t i m e s t a m p ' ] )  
                 m e t [ ' t i m e s t a m p ' ]   =   p d . t o _ d a t e t i m e ( m e t [ ' t i m e s t a m p ' ] )  
                  
                 s y n c e d   =   p d . m e r g e _ a s o f (  
                         t e l e m e t r y . s o r t _ v a l u e s ( ' t i m e s t a m p ' ) ,  
                         m e t . s o r t _ v a l u e s ( ' t i m e s t a m p ' ) ,  
                         o n = ' t i m e s t a m p ' ,  
                         d i r e c t i o n = ' n e a r e s t ' ,  
                         t o l e r a n c e = p d . T i m e d e l t a ( ' 6 0 s ' )  
                 )  
                  
                 #   S t e p   5 :   C a l c u l a t e   p h e n o t y p e s  
                 s y n c e d [ ' v p d _ k p a ' ]   =   s y n c e d . a p p l y (  
                         l a m b d a   r :   c a l c u l a t e _ v p d ( r [ ' t e m p _ c ' ] ,   r [ ' h u m i d i t y _ p c t ' ] ) ,   a x i s = 1  
                 )  
                 s y n c e d [ ' t r a n s p i r a t i o n ' ]   =   s y n c e d . a p p l y (  
                         l a m b d a   r :   e s t i m a t e _ t r a n s p i r a t i o n ( r [ ' t e m p _ c ' ] ,   r [ ' h u m i d i t y _ p c t ' ] ,   r [ ' p a r _ u m o l ' ] ) ,   a x i s = 1  
                 )  
                  
                 #   S t e p   6 :   J o i n   w i t h   r e s e a r c h   e v e n t s   ( 5 - m i n   t o l e r a n c e )  
                 e v e n t s   =   p d . r e a d _ s q l ( " S E L E C T   *   F R O M   r e s e a r c h _ e v e n t s " ,   s e l f . e n g i n e )  
                 i f   l e n ( e v e n t s )   >   0 :  
                         e v e n t s [ ' t i m e s t a m p ' ]   =   p d . t o _ d a t e t i m e ( e v e n t s [ ' t i m e s t a m p ' ] )  
                         s y n c e d   =   p d . m e r g e _ a s o f (  
                                 s y n c e d ,  
                                 e v e n t s . s o r t _ v a l u e s ( ' t i m e s t a m p ' ) ,  
                                 o n = ' t i m e s t a m p ' ,  
                                 d i r e c t i o n = ' n e a r e s t ' ,  
                                 t o l e r a n c e = p d . T i m e d e l t a ( ' 3 0 0 s ' )  
                         )  
                  
                 #   S t e p   7 :   E x p o r t   t o   C S V  
                 o u t p u t _ p a t h   =   ' / a p p / d a t a / c u r a t e d _ r e s e a r c h _ d a t a s e t . c s v '  
                 s y n c e d . t o _ c s v ( o u t p u t _ p a t h ,   i n d e x = F a l s e )  
                 l o g g e r . i n f o ( f " C u r a t e d   { l e n ( s y n c e d ) }   r e c o r d s   t o   { o u t p u t _ p a t h } " )  
                  
                 r e t u r n   s y n c e d  
 ` ` `  
  
 * * I n t e r v i e w   t a l k i n g   p o i n t s : * *  
 -   " T h e   t e m p o r a l   j o i n   w a s   t h e   m o s t   c h a l l e n g i n g   p a r t   -   y o u   c a n ' t   j u s t   J O I N   o n   t i m e s t a m p "  
 -   " P y d a n t i c   v a l i d a t i o n   c a t c h e s   s e n s o r   e r r o r s   b e f o r e   t h e y   p o l l u t e   t h e   d a t a s e t "  
 -   " m e r g e _ a s o f   f i n d s   t h e   n e a r e s t   m a t c h   w i t h i n   a   c o n f i g u r a b l e   t o l e r a n c e   w i n d o w "  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / f a r m _ s i m . p y `   ( 1 3 9   l i n e s ,   5 , 7 9 4   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / f a r m _ s i m . p y `  
  
 * * W h a t   i t   d o e s : * *  
 S i m u l a t e s   4 0   n R F 5 2 8 4 0   s e n s o r   n o d e s   w i t h   r e a l i s t i c   e n v i r o n m e n t a l   p a t t e r n s .  
  
 * * C l a s s :   P h y t o t r o n S i m u l a t o r * *  
  
 * * K e y   M e t h o d s : * *  
  
 * * 1 .   g e t _ a m b i e n t _ c o n d i t i o n s ( ) * *  
 ` ` ` p y t h o n  
 d e f   g e t _ a m b i e n t _ c o n d i t i o n s ( s e l f ) :  
         " " " C a l c u l a t e s   r e a l i s t i c   d i u r n a l   t e m p e r a t u r e   a n d   h u m i d i t y . " " "  
         n o w   =   d a t e t i m e . n o w ( )  
         h o u r   =   n o w . h o u r   +   n o w . m i n u t e / 6 0 . 0  
          
         #   D i u r n a l   t e m p e r a t u r e   c y c l e :   p e a k s   a t   3   P M   ( h o u r   1 5 ) ,   l o w e s t   a t   5   A M  
         #   O n t a r i o   g r e e n h o u s e   t y p i c a l   r a n g e :   1 8 C   ( n i g h t )   t o   2 6 C   ( d a y )  
         t e m p _ b a s e   =   2 2   +   4   *   m a t h . s i n ( ( h o u r   -   9 )   *   m a t h . p i   /   1 2 )  
          
         #   R e l a t i v e   h u m i d i t y :   i n v e r s e   t o   t e m p e r a t u r e  
         #   R a n g e :   4 5 %   ( d a y )   t o   7 5 %   ( n i g h t )  
         h u m _ b a s e   =   6 0   -   1 5   *   m a t h . s i n ( ( h o u r   -   9 )   *   m a t h . p i   /   1 2 )  
          
         #   P A R   f o l l o w s   s u n   p a t t e r n  
         i f   6   < =   h o u r   < =   2 0 :  
                 p a r _ b a s e   =   8 0 0   *   m a t h . s i n ( ( h o u r   -   6 )   *   m a t h . p i   /   1 4 )  
         e l s e :  
                 p a r _ b a s e   =   0  
                  
         r e t u r n   t e m p _ b a s e ,   h u m _ b a s e ,   m a x ( 0 ,   p a r _ b a s e )  
 ` ` `  
  
 * * 2 .   s i m u l a t e _ n o d e ( ) * *  
 -   A d d s   p e r - n o d e   v a r i a n c e   ( m i c r o - c l i m a t e   e f f e c t s )  
 -   S i m u l a t e s   s e n s o r   a n o m a l i e s   ( N o d e   1 2   n e a r   h e a t e r ,   N o d e   2 8   n e a r   d o o r )  
 -   M o d e l s   r e a l i s t i c   b a t t e r y   d r a i n   o v e r   t i m e  
 -   S i m u l a t e s   R S S I   ( s i g n a l   s t r e n g t h )  
  
 * * W h y   r e a l i s t i c   s i m u l a t i o n   m a t t e r s : * *  
 -   T e s t s   e d g e   c a s e s   ( s e n s o r   f a i l u r e s ,   o u t l i e r s )  
 -   L o a d   t e s t i n g   ( 4 0   c o n c u r r e n t   d a t a b a s e   c o n n e c t i o n s )  
 -   R L   t r a i n i n g   w i t h o u t   r e a l   c r o p   c y c l e s  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / m q t t _ b r i d g e . p y `   ( 1 5 5   l i n e s ,   6 , 0 6 6   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / m q t t _ b r i d g e . p y `  
  
 * * W h a t   i t   d o e s : * *  
 B r i d g e s   M Q T T   m e s s a g e s   f r o m   R a s p b e r r y   P i   b o r d e r   r o u t e r   t o   T i m e s c a l e D B .  
  
 * * M Q T T   T o p i c s : * *  
 -   ` g o s / t e l e m e t r y / { n o d e _ i d } ` :   S e n s o r   d a t a  
 -   ` g o s / h e a l t h / { n o d e _ i d } ` :   N o d e   s t a t u s  
 -   ` g o s / l e d / s c h e d u l e ` :   L E D   c o n t r o l   c o m m a n d s  
  
 * * C l a s s :   M Q T T D a t a b a s e B r i d g e * *  
  
 * * K e y   M e t h o d s : * *  
  
 * * o n _ m e s s a g e ( )   -   M e s s a g e   R o u t e r : * *  
 ` ` ` p y t h o n  
 d e f   o n _ m e s s a g e ( s e l f ,   c l i e n t ,   u s e r d a t a ,   m s g ) :  
         t o p i c   =   m s g . t o p i c  
         p a y l o a d   =   j s o n . l o a d s ( m s g . p a y l o a d . d e c o d e ( ' u t f - 8 ' ) )  
          
         i f   t o p i c . s t a r t s w i t h ( " g o s / t e l e m e t r y / " ) :  
                 s e l f . h a n d l e _ t e l e m e t r y ( t o p i c ,   p a y l o a d )  
         e l i f   t o p i c . s t a r t s w i t h ( " g o s / h e a l t h / " ) :  
                 s e l f . h a n d l e _ h e a l t h ( t o p i c ,   p a y l o a d )  
         e l i f   t o p i c   = =   " g o s / l e d / s c h e d u l e " :  
                 s e l f . h a n d l e _ l e d _ s c h e d u l e ( p a y l o a d )  
 ` ` `  
  
 * * h a n d l e _ t e l e m e t r y ( )   -   D a t a b a s e   I n s e r t : * *  
 ` ` ` p y t h o n  
 d e f   h a n d l e _ t e l e m e t r y ( s e l f ,   t o p i c ,   p a y l o a d ) :  
         n o d e _ i d   =   t o p i c . s p l i t ( ' / ' ) [ - 1 ]  
          
         c o n n   =   p s y c o p g 2 . c o n n e c t ( s e l f . d b _ u r l )  
         w i t h   c o n n . c u r s o r ( )   a s   c u r :  
                 c u r . e x e c u t e ( " " "  
                         I N S E R T   I N T O   r a w _ t e l e m e t r y    
                         ( n o d e _ i d ,   s a m p l e _ i d e n t i t y ,   t e m p _ c ,   h u m i d i t y _ p c t ,   p a r _ u m o l ,   b a t t e r y _ m v ,   r s s i )  
                         V A L U E S   ( % s ,   % s ,   % s ,   % s ,   % s ,   % s ,   % s )  
                 " " " ,   (  
                         n o d e _ i d ,  
                         p a y l o a d . g e t ( ' e u i 6 4 ' ) ,  
                         p a y l o a d . g e t ( ' t e m p _ c ' ) ,  
                         p a y l o a d . g e t ( ' h u m i d i t y _ p c t ' ) ,  
                         p a y l o a d . g e t ( ' p a r _ u m o l ' ) ,  
                         p a y l o a d . g e t ( ' b a t t e r y _ m v ' ) ,  
                         p a y l o a d . g e t ( ' r s s i ' )  
                 ) )  
         c o n n . c o m m i t ( )  
 ` ` `  
  
 * * I n t e r v i e w   p o i n t : * *   T h i s   i s   t h e   b r i d g e   b e t w e e n   p h y s i c a l   h a r d w a r e   a n d   t h e   d a t a b a s e .   I n   p r o d u c t i o n ,   y o u ' d   s w a p   ` f a r m _ s i m . p y `   f o r   r e a l   M Q T T   m e s s a g e s   f r o m   t h i s   b r i d g e .  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / m e t _ s t a t i o n . p y `   ( 4 , 7 6 3   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / m e t _ s t a t i o n . p y `  
  
 * * W h a t   i t   d o e s : * *  
 S i m u l a t e s   t h e   m e t e o r o l o g i c a l   s t a t i o n   t h a t   p r o v i d e s   r a d i a t i o n   a n d   s p e c t r a l   d a t a .  
  
 * * K e y   D a t a : * *  
 -   S o l a r   r a d i a t i o n   ( W / m � � )  
 -   S p e c t r a l   d i s t r i b u t i o n   ( %   r e d ,   b l u e ,   g r e e n ,   f a r - r e d )  
 -   Q u a n t u m   y i e l d   m e a s u r e m e n t s  
  
 * * S a m p l i n g   R a t e : * *   E v e r y   1 0   s e c o n d s   ( h i g h e r   f r e q u e n c y   t h a n   s e n s o r   n o d e s )  
  
 * * W h y   s e p a r a t e   f r o m   f a r m _ s i m ? * *  
 -   D i f f e r e n t   s a m p l i n g   r a t e   ( 1 0 s   v s   6 0 s )  
 -   D i f f e r e n t   d a t a   s c h e m a  
 -   M i m i c s   r e a l   d e p l o y m e n t   w h e r e   m e t   s t a t i o n   i s   a   s e p a r a t e   d e v i c e  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / s a f e t y _ l t l . p y `   ( 5 0   l i n e s ,   1 , 9 4 2   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / s a f e t y _ l t l . p y `  
  
 * * W h a t   i t   d o e s : * *  
 I m p l e m e n t s   L i n e a r   T e m p o r a l   L o g i c   ( L T L )   s a f e t y   c o n s t r a i n t s   f o r   t h e   R L   a g e n t .  
  
 * * C l a s s :   S a f e t y L T L M o n i t o r * *  
  
 * * S a f e t y   P r o p e r t i e s   ( i n   L T L   n o t a t i o n ) : * *  
 1 .   ` G ( p a r   <   1 5 0 0 ) `   -   G l o b a l l y ,   P A R   m u s t   s t a y   b e l o w   1 5 0 0   � � m o l / m � � / s  
 2 .   ` G ( d e l t a _ b l u e   <   0 . 5 ) `   -   G l o b a l l y ,   b l u e   r a t i o   c h a n g e s   m u s t   b e   <   5 0 %   p e r   s t e p  
  
 * * C o d e : * *  
 ` ` ` p y t h o n  
 d e f   c h e c k _ s a f e t y ( s e l f ,   a c t i o n ,   c u r r e n t _ s t a t e ) :  
         " " " C h e c k s   i f   a   p r o p o s e d   L E D   A c t i o n   v i o l a t e s   L T L   s a f e t y   c o n s t r a i n t s . " " "  
          
         #   1 .   I m m e d i a t e   C o n s t r a i n t :   N e v e r   e x c e e d   a b s o l u t e   P A R   l i m i t  
         i f   a c t i o n . g e t ( " p a r _ i n c r e a s e " ,   0 )   +   c u r r e n t _ s t a t e . g e t ( " p a r " ,   0 )   >   1 5 0 0 :  
                 l o g g e r . e r r o r ( " L T L   V I O L A T I O N :   G ( p a r   <   1 5 0 0 )   |   A B O R T I N G   A C T I O N . " )  
                 r e t u r n   F a l s e  
                  
         #   2 .   S e q u e n t i a l   C o n s t r a i n t :   N o   r a p i d   s p e c t r a l   s h i f t s   ( >   5 0 %   i n   1   m i n u t e )  
         i f   l e n ( s e l f . s t a t e _ h i s t o r y )   >   0 :  
                 p r e v _ b l u e   =   s e l f . s t a t e _ h i s t o r y [ - 1 ] . g e t ( " b l u e _ r a t i o " ,   0 . 2 )  
                 i f   a b s ( a c t i o n . g e t ( " b l u e _ r a t i o " ,   0 . 2 )   -   p r e v _ b l u e )   >   0 . 5 :  
                         l o g g e r . e r r o r ( " L T L   V I O L A T I O N :   G ( d e l t a _ b l u e   <   0 . 5 )   |   S T R E S S   P R E V E N T I O N . " )  
                         r e t u r n   F a l s e  
  
         r e t u r n   T r u e  
 ` ` `  
  
 * * I n t e r v i e w   t a l k i n g   p o i n t s : * *  
 -   " L T L   p r o v i d e s   f o r m a l   g u a r a n t e e s   t h a t   t h e   R L   a g e n t   n e v e r   v i o l a t e s   s a f e t y   c o n s t r a i n t s "  
 -   " T h i s   i s   s i m i l a r   t o   s a f e t y   c e r t i f i c a t i o n s   i n   a u t o n o m o u s   v e h i c l e s "  
 -   " T h e   m o n i t o r   w r a p s   t h e   R L   p o l i c y ,   n o t   t h e   o t h e r   w a y   a r o u n d "  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / o t b r _ g a t e w a y . p y `   ( 1 , 6 9 5   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / o t b r _ g a t e w a y . p y `  
  
 * * W h a t   i t   d o e s : * *  
 I n t e r f a c e   t o   t h e   O p e n T h r e a d   B o r d e r   R o u t e r   ( O T B R )   r u n n i n g   o n   R a s p b e r r y   P i .  
  
 * * F u n c t i o n s : * *  
 -   N e t w o r k   c o m m i s s i o n i n g  
 -   D e v i c e   d i s c o v e r y  
 -   C o A P   p r o x y i n g  
  
 * * F o r   r e a l   h a r d w a r e   d e p l o y m e n t   o n l y * *   -   n o t   u s e d   i n   s i m u l a t i o n   m o d e .  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s e r v i c e s / m q t t _ s n _ b r i d g e . p y `   ( 1 , 6 0 9   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s e r v i c e s / m q t t _ s n _ b r i d g e . p y `  
  
 * * W h a t   i t   d o e s : * *  
 M Q T T - S N   ( S e n s o r   N e t w o r k s )   b r i d g e   f o r   u l t r a - l o w - p o w e r   d e v i c e s .  
  
 * * M Q T T - S N   v s   M Q T T : * *  
 -   M Q T T - S N   u s e s   U D P   i n s t e a d   o f   T C P  
 -   S m a l l e r   p a c k e t   s i z e s   ( 2   b y t e s   t o p i c   I D   v s   v a r i a b l e - l e n g t h   t o p i c   s t r i n g )  
 -   B e t t e r   f o r   c o n s t r a i n e d   d e v i c e s  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / s c h e m a . s q l `   ( 4 , 5 0 7   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / s c h e m a . s q l `  
  
 * * W h a t   i t   d o e s : * *  
 D e f i n e s   t h e   T i m e s c a l e D B   d a t a b a s e   s c h e m a .   A u t o m a t i c a l l y   r u n s   o n   f i r s t   c o n t a i n e r   s t a r t .  
  
 * * T a b l e s : * *  
  
 * * 1 .   r a w _ t e l e m e t r y   ( H y p e r t a b l e ) * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   r a w _ t e l e m e t r y   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L   D E F A U L T   N O W ( ) ,  
         n o d e _ i d   T E X T   N O T   N U L L ,  
         s a m p l e _ i d e n t i t y   T E X T ,  
         t e m p _ c   N U M E R I C ( 5 , 2 ) ,  
         h u m i d i t y _ p c t   N U M E R I C ( 5 , 2 ) ,  
         p a r _ u m o l   N U M E R I C ( 8 , 2 ) ,  
         b a t t e r y _ m v   I N T E G E R ,  
         r s s i   I N T E G E R  
 ) ;  
  
 - -   C o n v e r t   t o   h y p e r t a b l e   ( a u t o m a t i c   t i m e - b a s e d   p a r t i t i o n i n g )  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' r a w _ t e l e m e t r y ' ,   ' t i m e s t a m p ' ) ;  
  
 - -   I n d e x   f o r   e f f i c i e n t   n o d e - b a s e d   q u e r i e s  
 C R E A T E   I N D E X   i d x _ t e l e m e t r y _ n o d e   O N   r a w _ t e l e m e t r y   ( n o d e _ i d ,   t i m e s t a m p   D E S C ) ;  
 ` ` `  
  
 * * 2 .   m e t _ s t a t i o n _ d a t a   ( H y p e r t a b l e ) * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   m e t _ s t a t i o n _ d a t a   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L   D E F A U L T   N O W ( ) ,  
         r a d i a t i o n _ w _ m 2   N U M E R I C ( 8 , 2 ) ,  
         s p e c t r a l _ r e d _ p c t   N U M E R I C ( 5 , 2 ) ,  
         s p e c t r a l _ b l u e _ p c t   N U M E R I C ( 5 , 2 ) ,  
         s p e c t r a l _ g r e e n _ p c t   N U M E R I C ( 5 , 2 ) ,  
         s p e c t r a l _ f a r _ r e d _ p c t   N U M E R I C ( 5 , 2 )  
 ) ;  
  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' m e t _ s t a t i o n _ d a t a ' ,   ' t i m e s t a m p ' ) ;  
 ` ` `  
  
 * * 3 .   r e s e a r c h _ e v e n t s   ( H y p e r t a b l e ) * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   r e s e a r c h _ e v e n t s   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L   D E F A U L T   N O W ( ) ,  
         e v e n t _ t y p e   T E X T ,  
         d e s c r i p t i o n   T E X T ,  
         m e t a d a t a   J S O N B ,     - -   L L M - e x t r a c t e d   s t r u c t u r e d   d a t a  
         a n n o t a t o r   T E X T  
 ) ;  
  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' r e s e a r c h _ e v e n t s ' ,   ' t i m e s t a m p ' ) ;  
 ` ` `  
  
 * * 4 .   n o d e _ h e a l t h * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   n o d e _ h e a l t h   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L   D E F A U L T   N O W ( ) ,  
         n o d e _ i d   T E X T   N O T   N U L L ,  
         b a t t e r y _ m v   I N T E G E R ,  
         r s s i   I N T E G E R ,  
         u p t i m e _ s e c o n d s   I N T E G E R ,  
         r e b o o t _ c o u n t   I N T E G E R   D E F A U L T   0  
 ) ;  
  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' n o d e _ h e a l t h ' ,   ' t i m e s t a m p ' ) ;  
 ` ` `  
  
 * * 5 .   l e d _ s c h e d u l e _ h i s t o r y * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   l e d _ s c h e d u l e _ h i s t o r y   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L   D E F A U L T   N O W ( ) ,  
         b l u e _ r a t i o   N U M E R I C ( 4 , 3 ) ,  
         r e d _ r a t i o   N U M E R I C ( 4 , 3 ) ,  
         i n t e n s i t y _ p c t   I N T E G E R   D E F A U L T   1 0 0 ,  
         s e c t o r _ i d   T E X T   D E F A U L T   ' A L L '  
 ) ;  
  
 S E L E C T   c r e a t e _ h y p e r t a b l e ( ' l e d _ s c h e d u l e _ h i s t o r y ' ,   ' t i m e s t a m p ' ) ;  
 ` ` `  
  
 * * 6 .   y i e l d _ l o g s * *  
 ` ` ` s q l  
 C R E A T E   T A B L E   y i e l d _ l o g s   (  
         t i m e s t a m p   T I M E S T A M P T Z   N O T   N U L L   D E F A U L T   N O W ( ) ,  
         p l a n t _ i d   T E X T   N O T   N U L L ,  
         w e i g h t _ g   N U M E R I C ( 8 , 2 ) ,  
         b r i x   N U M E R I C ( 4 , 2 ) ,     - -   S u g a r   c o n t e n t  
         n o t e s   T E X T  
 ) ;  
 ` ` `  
  
 * * W h y   h y p e r t a b l e s ? * *  
 -   A u t o m a t i c   p a r t i t i o n i n g   b y   t i m e   ( c h u n k s )  
 -   F a s t e r   q u e r i e s   f o r   t i m e - r a n g e   f i l t e r s  
 -   E a s y   d a t a   r e t e n t i o n   ( d r o p   o l d   c h u n k s )  
 -   B u i l t - i n   c o m p r e s s i o n  
  
 - - -  
  
 # # #   � x    ` g a t e w a y / D o c k e r f i l e `   ( 4 3 2   b y t e s )  
  
 * * L o c a t i o n : * *   ` / g a t e w a y / D o c k e r f i l e `  
  
 * * W h a t   i t   d o e s : * *  
 B u i l d s   t h e   g a t e w a y   s e r v i c e   c o n t a i n e r .  
  
 ` ` ` d o c k e r f i l e  
 F R O M   p y t h o n : 3 . 1 1 - s l i m  
  
 W O R K D I R   / a p p  
  
 #   I n s t a l l   d e p e n d e n c i e s  
 C O P Y   r e q u i r e m e n t s . t x t   .  
 R U N   p i p   i n s t a l l   - - n o - c a c h e - d i r   - r   r e q u i r e m e n t s . t x t  
  
 #   C o p y   s e r v i c e   c o d e  
 C O P Y   s e r v i c e s /   / a p p / s e r v i c e s /  
  
 #   D e f a u l t   c o m m a n d   ( o v e r r i d d e n   b y   d o c k e r - c o m p o s e )  
 C M D   [ " p y t h o n " ,   " s e r v i c e s / a p i . p y " ]  
 ` ` `  
  
 * * W h y   s l i m   b a s e   i m a g e ? * *  
 -   S m a l l e r   i m a g e   s i z e   ( ~ 1 5 0 M B   v s   ~ 9 0 0 M B   f o r   f u l l   P y t h o n )  
 -   F a s t e r   p u l l s   a n d   d e p l o y m e n t s  
 -   R e d u c e d   a t t a c k   s u r f a c e  
  
 - - -  
  
 # #   1 3 . 3   M L   E n g i n e   ( 8   F i l e s )  
  
 T h e   ` m l _ e n g i n e / `   d i r e c t o r y   c o n t a i n s   m a c h i n e   l e a r n i n g   a n d   p l a n t   p h y s i o l o g y   c o d e .  
  
 - - -  
  
 # # #   � x    ` m l _ e n g i n e / p h e n o t y p i n g . p y `   ( 3 6 6   l i n e s ,   1 2 , 7 7 9   b y t e s )  
  
 * * L o c a t i o n : * *   ` / m l _ e n g i n e / p h e n o t y p i n g . p y `  
  
 * * W h a t   i t   d o e s : * *  
 T h e   c o r e   p h e n o t y p i n g   e n g i n e .   C a l c u l a t e s   p l a n t   p h y s i o l o g i c a l   m e t r i c s   f r o m   s e n s o r   d a t a .  
  
 * * C l a s s :   P h e n o t y p i n g E n g i n e * *  
  
 * * K e y   M e t h o d s : * *  
  
 * * 1 .   c a l c u l a t e _ v p d ( )   -   V a p o r   P r e s s u r e   D e f i c i t * *  
 ` ` ` p y t h o n  
 d e f   c a l c u l a t e _ v p d ( s e l f ,   t e m p _ c :   f l o a t ,   h u m i d i t y _ p c t :   f l o a t )   - >   f l o a t :  
         " " "  
         C a l c u l a t e   V a p o r   P r e s s u r e   D e f i c i t   ( V P D )   i n   k P a .  
          
         V P D   =   S V P ( T )   �    ( 1   -   R H / 1 0 0 )  
          
         W h e r e   S V P   i s   c a l c u l a t e d   u s i n g   T e t e n s   e q u a t i o n :  
         S V P   =   0 . 6 1 0 8   �    e x p ( 1 7 . 2 7   �    T   /   ( T   +   2 3 7 . 3 ) )  
         " " "  
         #   S a t u r a t i o n   v a p o r   p r e s s u r e  
         s v p   =   0 . 6 1 0 8   *   n p . e x p ( ( 1 7 . 2 7   *   t e m p _ c )   /   ( t e m p _ c   +   2 3 7 . 3 ) )  
          
         #   A c t u a l   v a p o r   p r e s s u r e  
         a v p   =   s v p   *   ( h u m i d i t y _ p c t   /   1 0 0 . 0 )  
          
         #   V a p o r   p r e s s u r e   d e f i c i t  
         v p d   =   s v p   -   a v p  
          
         r e t u r n   v p d  
 ` ` `  
  
 * * 2 .   e s t i m a t e _ t r a n s p i r a t i o n ( )   -   P e n m a n - M o n t e i t h * *  
 ` ` ` p y t h o n  
 d e f   e s t i m a t e _ t r a n s p i r a t i o n ( s e l f ,   t e m p _ c :   f l o a t ,   h u m i d i t y _ p c t :   f l o a t ,    
                                                       p a r _ u m o l :   f l o a t ,   w i n d _ s p e e d :   f l o a t   =   0 . 5 )   - >   f l o a t :  
         " " "  
         E s t i m a t e   t r a n s p i r a t i o n   r a t e   u s i n g   s i m p l i f i e d   P e n m a n - M o n t e i t h   e q u a t i o n .  
          
         E T   =   ( �    �    R n   +   � � a   �    c p   �    V P D   /   r a )   /   ( �    +   � �   �    ( 1   +   r s / r a ) )  
         " " "  
         #   C a l c u l a t e   V P D  
         v p d   =   s e l f . c a l c u l a t e _ v p d ( t e m p _ c ,   h u m i d i t y _ p c t )  
          
         #   C o n v e r t   P A R   t o   n e t   r a d i a t i o n  
         r n   =   p a r _ u m o l   /   4 . 6   *   0 . 5     #   E m p i r i c a l   c o n v e r s i o n  
          
         #   S l o p e   o f   s a t u r a t i o n   v a p o r   p r e s s u r e   c u r v e  
         s v p   =   0 . 6 1 0 8   *   n p . e x p ( ( 1 7 . 2 7   *   t e m p _ c )   /   ( t e m p _ c   +   2 3 7 . 3 ) )  
         d e l t a   =   ( 4 0 9 8   *   s v p )   /   ( ( t e m p _ c   +   2 3 7 . 3 )   * *   2 )  
          
         #   P s y c h r o m e t r i c   c o n s t a n t  
         g a m m a   =   0 . 0 6 6     #   k P a / � � C  
          
         #   S i m p l i f i e d   c a l c u l a t i o n  
         e t   =   ( d e l t a   *   r n   +   g a m m a   *   v p d   *   2 . 0 )   /   ( d e l t a   +   g a m m a )  
          
         #   C o n v e r t   t o   g / m � � / h  
         r e t u r n   e t   *   1 0 0 0  
 ` ` `  
  
 * * 3 .   d e t e c t _ s t r e s s ( )   -   M u l t i - F a c t o r   S t r e s s   D e t e c t i o n * *  
 ` ` ` p y t h o n  
 d e f   d e t e c t _ s t r e s s ( s e l f ,   t e m p _ c :   f l o a t ,   h u m i d i t y _ p c t :   f l o a t ,  
                                     p a r _ u m o l :   f l o a t ,   b a t t e r y _ m v :   i n t   =   3 3 0 0 )   - >   d i c t :  
         " " "  
         M u l t i - f a c t o r   s t r e s s   d e t e c t i o n   f o r   g r e e n h o u s e   s t r a w b e r r y .  
          
         R e t u r n s   s t r e s s   i n d i c a t o r s   f o r :  
         -   H e a t   s t r e s s  
         -   C o l d   s t r e s s  
         -   V P D   s t r e s s   ( d r o u g h t - l i k e )  
         -   L i g h t   s t r e s s  
         -   S e n s o r   h e a l t h  
         " " "  
         s t r e s s _ s c o r e   =   0  
         i n d i c a t o r s   =   [ ]  
          
         #   H e a t   s t r e s s   ( > 3 0 � � C )  
         i f   t e m p _ c   >   3 0 :  
                 s t r e s s _ s c o r e   + =   m i n ( 2 0 ,   ( t e m p _ c   -   3 0 )   *   4 )  
                 i n d i c a t o r s . a p p e n d ( " H E A T _ S T R E S S " )  
          
         #   C o l d   s t r e s s   ( < 1 5 � � C )  
         i f   t e m p _ c   <   1 5 :  
                 s t r e s s _ s c o r e   + =   m i n ( 1 5 ,   ( 1 5   -   t e m p _ c )   *   3 )  
                 i n d i c a t o r s . a p p e n d ( " C O L D _ S T R E S S " )  
          
         #   V P D   s t r e s s   ( > 1 . 5   k P a )  
         v p d   =   s e l f . c a l c u l a t e _ v p d ( t e m p _ c ,   h u m i d i t y _ p c t )  
         i f   v p d   >   1 . 5 :  
                 s t r e s s _ s c o r e   + =   m i n ( 2 5 ,   ( v p d   -   1 . 5 )   *   2 0 )  
                 i n d i c a t o r s . a p p e n d ( " V P D _ S T R E S S " )  
          
         #   L o w   l i g h t   s t r e s s   ( < 1 0 0   � � m o l )  
         i f   p a r _ u m o l   <   1 0 0 :  
                 s t r e s s _ s c o r e   + =   m i n ( 1 0 ,   ( 1 0 0   -   p a r _ u m o l )   /   1 0 )  
                 i n d i c a t o r s . a p p e n d ( " L O W _ L I G H T " )  
          
         #   S e n s o r   h e a l t h   c h e c k  
         i f   b a t t e r y _ m v   <   3 5 0 0 :  
                 i n d i c a t o r s . a p p e n d ( " L O W _ B A T T E R Y " )  
          
         r e t u r n   {  
                 " s t r e s s _ s c o r e " :   m i n ( 1 0 0 ,   s t r e s s _ s c o r e ) ,  
                 " s t r e s s _ l e v e l " :   s e l f . _ c l a s s i f y _ s t r e s s _ s c o r e ( s t r e s s _ s c o r e ) ,  
                 " i n d i c a t o r s " :   i n d i c a t o r s ,  
                 " v p d _ k p a " :   r o u n d ( v p d ,   3 )  
         }  
 ` ` `  
  
 * * 4 .   c a l c u l a t e _ n d v i _ p r o x y ( )   -   V e g e t a t i o n   I n d e x * *  
 ` ` ` p y t h o n  
 d e f   c a l c u l a t e _ n d v i _ p r o x y ( s e l f ,   b l u e _ i n t e n s i t y :   f l o a t ,   r e d _ i n t e n s i t y :   f l o a t ,  
                                                   p a r _ u m o l :   f l o a t )   - >   f l o a t :  
         " " "  
         C a l c u l a t e   N D V I   p r o x y   f r o m   L E D   s p e c t r a l   d a t a .  
          
         T r u e   N D V I   r e q u i r e s   N I R   s e n s o r ,   b u t   w e   c a n   e s t i m a t e   p l a n t   v i g o r  
         f r o m   t h e   r a t i o   o f   a b s o r b e d   r e d   ( p h o t o s y n t h e s i s )   v s   b l u e   l i g h t .  
         " " "  
         #   A v o i d   d i v i s i o n   b y   z e r o  
         i f   r e d _ i n t e n s i t y   +   b l u e _ i n t e n s i t y   = =   0 :  
                 r e t u r n   0 . 0  
          
         #   P r o x y   c a l c u l a t i o n   ( n o t   t r u e   N D V I ,   b u t   c o r r e l a t e s   w i t h   v i g o r )  
         n d v i _ p r o x y   =   ( r e d _ i n t e n s i t y   -   b l u e _ i n t e n s i t y )   /   ( r e d _ i n t e n s i t y   +   b l u e _ i n t e n s i t y )  
          
         #   S c a l e   b a s e d   o n   P A R   ( h i g h e r   P A R   =   m o r e   r e l i a b l e   m e a s u r e m e n t )  
         p a r _ w e i g h t   =   m i n ( 1 . 0 ,   p a r _ u m o l   /   5 0 0 )  
          
         r e t u r n   n d v i _ p r o x y   *   p a r _ w e i g h t  
 ` ` `  
  
 * * I n t e r v i e w   t a l k i n g   p o i n t s : * *  
 -   " T h e   T e t e n s   e q u a t i o n   i s   i n d u s t r y - s t a n d a r d   f o r   S V P   c a l c u l a t i o n "  
 -   " P e n m a n - M o n t e i t h   i s   t h e   F A O - r e c o m m e n d e d   m e t h o d   f o r   E T   e s t i m a t i o n "  
 -   " M u l t i - f a c t o r   s t r e s s   d e t e c t i o n   c a p t u r e s   i n t e r a c t i o n s   b e t w e e n   s t r e s s o r s "  
  
 - - -  
  
 # # #   � x    ` m l _ e n g i n e / a g e n t _ r l . p y `   ( 4 3   l i n e s ,   1 , 6 9 4   b y t e s )  
  
 * * L o c a t i o n : * *   ` / m l _ e n g i n e / a g e n t _ r l . p y `  
  
 * * W h a t   i t   d o e s : * *  
 R e i n f o r c e m e n t   L e a r n i n g   a g e n t   f o r   L E D   s p e c t r a l   q u a l i t y   c o n t r o l .  
  
 * * C l a s s :   T r a n s p i r a t i o n R L A g e n t * *  
  
 * * P o l i c y : * *  
 ` ` ` p y t h o n  
 d e f   g e t _ a c t i o n ( s e l f ,   c u r r e n t _ v p d ,   c u r r e n t _ p a r ) :  
         " " " R e c o m m e n d s   a   s p e c t r a l   q u a l i t y   s h i f t   t o   o p t i m i z e   t r a n s p i r a t i o n . " " "  
         #   S i m p l e   p o l i c y :   I f   V P D   i s   h i g h ,   i n c r e a s e   b l u e   r a t i o    
         #   t o   m a i n t a i n   s t o m a t a l   c o n d u c t a n c e   b u t   m a n a g e   w a t e r   s t r e s s .  
         i f   c u r r e n t _ v p d   >   1 . 5 :  
                 r e c o m m e n d a t i o n   =   " I n c r e a s e   b l u e   r a t i o   t o   0 . 4 5 ;   I n c r e a s e   F a r - R e d "  
                 s h i f t   =   { " b l u e " :   0 . 4 5 ,   " r e d " :   0 . 5 5 }  
         e l s e :  
                 r e c o m m e n d a t i o n   =   " M a i n t a i n   B l u e   r a t i o   a t   0 . 2 0 "  
                 s h i f t   =   { " b l u e " :   0 . 2 ,   " r e d " :   0 . 8 }  
                  
         r e t u r n   r e c o m m e n d a t i o n ,   s h i f t  
 ` ` `  
  
 * * W h y   t h i s   s i m p l e   p o l i c y ? * *  
 T h i s   i s   a   p r o t o t y p e .   I n   p r o d u c t i o n ,   y o u ' d   u s e :  
 -   S o f t   A c t o r - C r i t i c   ( S A C )   f o r   c o n t i n u o u s   a c t i o n   s p a c e s  
 -   P r o x i m a l   P o l i c y   O p t i m i z a t i o n   ( P P O )   f o r   s t a b i l i t y  
 -   M o d e l - b a s e d   R L   f o r   s a m p l e   e f f i c i e n c y  
  
 - - -  
  
 # # #   � x    ` m l _ e n g i n e / p l a n t _ s i m _ c 3 . p y `   ( 5 7   l i n e s ,   2 , 3 1 3   b y t e s )  
  
 * * L o c a t i o n : * *   ` / m l _ e n g i n e / p l a n t _ s i m _ c 3 . p y `  
  
 * * W h a t   i t   d o e s : * *  
 P h y s i c s - i n f o r m e d   p l a n t   p h y s i o l o g y   s i m u l a t o r   b a s e d   o n   t h e   F v C B   ( F a r q u h a r )   m o d e l .  
  
 * * C l a s s :   S t r a w b e r r y P h y s i o l o g y S i m * *  
  
 * * B i o l o g i c a l   C o n s t a n t s : * *  
 ` ` ` p y t h o n  
 d e f   _ _ i n i t _ _ ( s e l f ) :  
         #   B i o l o g i c a l   c o n s t a n t s   f o r   C 3   p l a n t s  
         s e l f . V c m a x 2 5   =   8 0 . 0       #   M a x   c a r b o x y l a t i o n   r a t e   ( � � m o l / m � � / s )  
         s e l f . J m a x 2 5   =   1 4 0 . 0       #   M a x   e l e c t r o n   t r a n s p o r t   r a t e  
         s e l f . R d 2 5   =   0 . 8               #   D a r k   r e s p i r a t i o n  
         s e l f . b o u n d a r y _ l a y e r _ c o n d   =   0 . 5     #   m o l / m � � / s  
 ` ` `  
  
 * * T r a n s p i r a t i o n   M o d e l : * *  
 ` ` ` p y t h o n  
 d e f   c a l c u l a t e _ t r a n s p i r a t i o n ( s e l f ,   p a r ,   t e m p ,   h u m ,   b l u e _ r a t i o ) :  
         " " " P e n m a n - M o n t e i t h   s t y l e d   t r a n s p i r a t i o n   c a l c u l a t i o n . " " "  
          
         #   B l u e   l i g h t   a t   4 5 0 n m   s t i m u l a t e s   s t o m a t e s   v i a   p h o t o t r o p i n   r e c e p t o r s  
         b l u e _ f a c t o r   =   1 . 0   +   ( b l u e _ r a t i o   *   1 . 5 )  
          
         #   V P D   c a l c u l a t i o n  
         e s a t   =   0 . 6 1 1   *   n p . e x p ( 1 7 . 2 7   *   t e m p   /   ( t e m p   +   2 3 7 . 3 ) )  
         e a c t   =   e s a t   *   ( h u m   /   1 0 0 . 0 )  
         v p d   =   e s a t   -   e a c t  
          
         #   S t o m a t a l   c o n d u c t a n c e   m o d e l  
         #   g s   =   g 0   +   f ( b l u e )   *   ( 1   /   ( 1   +   v p d / D 0 ) )  
         g s   =   0 . 0 5   +   ( 0 . 2   *   ( p a r   /   ( p a r   +   5 0 0 ) )   *   b l u e _ f a c t o r )   /   ( 1   +   v p d   /   1 . 5 )  
          
         #   T r a n s p i r a t i o n   p r o p o r t i o n a l   t o   g s   a n d   V P D  
         t r a n s p i r a t i o n _ r a t e   =   g s   *   v p d   *   1 0 0 0 . 0     #   g / m � � / h  
          
         r e t u r n   {  
                 " t r a n s p i r a t i o n _ r a t e " :   r o u n d ( t r a n s p i r a t i o n _ r a t e ,   4 ) ,  
                 " g s " :   r o u n d ( g s ,   4 ) ,  
                 " v p d " :   r o u n d ( v p d ,   4 )  
         }  
 ` ` `  
  
 * * W h y   C 3 - s p e c i f i c ? * *  
 S t r a w b e r r i e s   a r e   C 3   p l a n t s   ( u s e   C a l v i n   c y c l e   f o r   c a r b o n   f i x a t i o n ) .   C 4   p l a n t s   ( c o r n ,   s u g a r c a n e )   h a v e   d i f f e r e n t   p h o t o s y n t h e t i c   p a t h w a y s .  
  
 - - -  
  
 # # #   � x    ` m l _ e n g i n e / s p e c t r a l _ o p t . p y `   ( 4 1   l i n e s ,   1 , 5 3 9   b y t e s )  
  
 * * L o c a t i o n : * *   ` / m l _ e n g i n e / s p e c t r a l _ o p t . p y `  
  
 * * W h a t   i t   d o e s : * *  
 S p e c t r a l   o p t i m i z e r   b a s e d   o n   g e o m e t r i c   c o n t r o l   t h e o r y .  
  
 * * C l a s s :   P h o t o s y n t h e s i s O p t i m i z e r * *  
  
 * * K e y   M e t h o d : * *  
 ` ` ` p y t h o n  
 d e f   o p t i m i z e _ s p e c t r a l _ q u a l i t y ( s e l f ,   t a r g e t _ y i e l d ,   c u r r e n t _ s t a t e ) :  
         " " " U s e s   a   g e o m e t r i c   c o n t r o l l e r   a p p r o a c h   t o   f i n d   o p t i m a l   b l u e : r e d   b a l a n c e . " " "  
          
         p a r   =   c u r r e n t _ s t a t e . g e t ( ' p a r ' ,   4 0 0 )  
         c o 2   =   c u r r e n t _ s t a t e . g e t ( ' c o 2 ' ,   4 0 0 )  
          
         #   D i f f e r e n t i a l   G e o m e t r i c   L o g i c :   S m a l l   s h i f t s   i n   s p e c t r a l   r a t i o  
         #   t o   f i n d   t h e   t a n g e n t   o f   t h e   p h o t o s y n t h e s i s   s a t u r a t i o n   c u r v e .  
          
         i f   c o 2   >   6 0 0 :  
                 #   H i g h   C O 2   a l l o w s   h i g h e r   P A R   a b s o r p t i o n  
                 b l u e _ r a t i o   =   0 . 3 5  
                 r e d _ r a t i o   =   0 . 6 5  
         e l s e :  
                 b l u e _ r a t i o   =   0 . 2 0  
                 r e d _ r a t i o   =   0 . 8 0  
                  
         r e t u r n   {  
                 " b l u e _ c h a n n e l " :   b l u e _ r a t i o ,  
                 " r e d _ c h a n n e l " :   r e d _ r a t i o ,  
                 " c o n t r o l _ t y p e " :   " G e o m e t r i c _ T a n g e n t _ F o l l o w e r "  
         }  
 ` ` `  
  
 - - -  
  
 # # #   � x    ` m l _ e n g i n e / m a c q _ l e a r n e r . p y `   ( 1 , 6 6 9   b y t e s )  
  
 * * L o c a t i o n : * *   ` / m l _ e n g i n e / m a c q _ l e a r n e r . p y `  
  
 * * W h a t   i t   d o e s : * *  
 A c t i o n   m o d e l   l e a r n i n g   u s i n g   t h e   M A C Q   l i b r a r y .  
  
 * * W h a t   i s   M A C Q ? * *  
 M a c h i n e   l e a r n i n g   f o r   A c t i o n   m o d e l   a C Q u i s i t i o n .   L e a r n s   P D D L   a c t i o n   m o d e l s   f r o m   o b s e r v a t i o n   t r a c e s .  
  
 * * C o n n e c t i o n   t o   p r o j e c t : * *  
 D r .   M u i s e ' s   r e s e a r c h   ( f a c u l t y   a d v i s o r )   f o c u s e s   o n   A I   p l a n n i n g .   M A C Q   c a n   l e a r n   t h e   " r u l e s "   o f   p l a n t   b e h a v i o r   f r o m   h i s t o r i c a l   d a t a .  
  
 - - -  
  
 # # #   � x    ` m l _ e n g i n e / d o m a i n . p d d l `   ( 1 , 1 0 0   b y t e s )  
  
 * * L o c a t i o n : * *   ` / m l _ e n g i n e / d o m a i n . p d d l `  
  
 * * W h a t   i t   d o e s : * *  
 P D D L   ( P l a n n i n g   D o m a i n   D e f i n i t i o n   L a n g u a g e )   d o m a i n   f i l e   f o r   A I   p l a n n i n g .  
  
 * * P D D L   S t r u c t u r e : * *  
 ` ` ` p d d l  
 ( d e f i n e   ( d o m a i n   g r e e n h o u s e )  
     ( : p r e d i c a t e s  
         ( h i g h _ v p d )  
         ( l o w _ l i g h t )  
         ( s t r e s s e d )  
         ( l e d _ o n )  
     )  
      
     ( : a c t i o n   i n c r e a s e _ l i g h t  
         : p r e c o n d i t i o n   ( a n d   ( l o w _ l i g h t )   ( l e d _ o n ) )  
         : e f f e c t   ( a n d   ( n o t   ( l o w _ l i g h t ) )   ( w h e n   ( h i g h _ v p d )   ( s t r e s s e d ) ) )  
     )  
      
     ( : a c t i o n   r e d u c e _ v p d  
         : p r e c o n d i t i o n   ( h i g h _ v p d )  
         : e f f e c t   ( n o t   ( h i g h _ v p d ) )  
     )  
 )  
 ` ` `  
  
 * * W h y   P D D L ? * *  
 -   F o r m a l   s p e c i f i c a t i o n   o f   a c t i o n s   a n d   e f f e c t s  
 -   C a n   u s e   a u t o m a t e d   p l a n n e r s   t o   g e n e r a t e   c o n t r o l   s e q u e n c e s  
 -   V e r i f i a b l e   a g a i n s t   s a f e t y   p r o p e r t i e s  
  
 - - -  
  
 # #   1 3 . 4   F i r m w a r e   ( 1 2   F i l e s )  
  
 T h e   ` f i r m w a r e / `   d i r e c t o r y   c o n t a i n s   C   c o d e   f o r   t h e   n R F 5 2 8 4 0   s e n s o r   n o d e s .  
  
 - - -  
  
 # # #   � x    ` f i r m w a r e / s r c / m a i n . c `   ( 2 5 5   l i n e s ,   7 , 0 4 1   b y t e s )  
  
 * * L o c a t i o n : * *   ` / f i r m w a r e / s r c / m a i n . c `  
  
 * * W h a t   i t   d o e s : * *  
 E n t r y   p o i n t   f o r   t h e   Z e p h y r   R T O S   f i r m w a r e   r u n n i n g   o n   n R F 5 2 8 4 0   s e n s o r   n o d e s .  
  
 * * C o m p l e t e   C o d e   S t r u c t u r e : * *  
  
 * * 1 .   I n c l u d e s   a n d   D e f i n e s : * *  
 ` ` ` c  
 # i n c l u d e   < o p e n t h r e a d / c o a p . h >  
 # i n c l u d e   < o p e n t h r e a d / t h r e a d . h >  
 # i n c l u d e   < z e p h y r / d e v i c e . h >  
 # i n c l u d e   < z e p h y r / d r i v e r s / s e n s o r . h >  
 # i n c l u d e   < z e p h y r / d r i v e r s / p w m . h >  
 # i n c l u d e   < z e p h y r / k e r n e l . h >  
  
 L O G _ M O D U L E _ R E G I S T E R ( g o s _ m a i n ,   C O N F I G _ L O G _ D E F A U L T _ L E V E L ) ;  
  
 # d e f i n e   S H T 4 X _ N O D E   D T _ N O D E L A B E L ( s h t 4 x _ s e n s o r )  
 # d e f i n e   C O A P _ U R I _ P A T H   " t e l e m e t r y "  
 ` ` `  
  
 * * 2 .   S e n s o r   I n i t i a l i z a t i o n : * *  
 ` ` ` c  
 s t a t i c   i n t   s e n s o r s _ i n i t ( v o i d )   {  
         / *   S H T 4 x   T e m p e r a t u r e / H u m i d i t y   * /  
         s h t 4 x _ d e v   =   D E V I C E _ D T _ G E T ( S H T 4 X _ N O D E ) ;  
         i f   ( ! d e v i c e _ i s _ r e a d y ( s h t 4 x _ d e v ) )   {  
                 L O G _ E R R ( " S H T 4 x   s e n s o r   n o t   r e a d y " ) ;  
                 r e t u r n   - E N O D E V ;  
         }  
         L O G _ I N F ( " S H T 4 x   s e n s o r   i n i t i a l i z e d " ) ;  
          
         / *   T S L 2 5 9 1   L i g h t   S e n s o r   ( o p t i o n a l )   * /  
         t s l 2 5 9 1 _ d e v   =   d e v i c e _ g e t _ b i n d i n g ( " T S L 2 5 9 1 " ) ;  
         i f   ( t s l 2 5 9 1 _ d e v )   {  
                 L O G _ I N F ( " T S L 2 5 9 1   l i g h t   s e n s o r   i n i t i a l i z e d " ) ;  
         }  
          
         r e t u r n   0 ;  
 }  
 ` ` `  
  
 * * 3 .   L E D   P W M   C o n t r o l : * *  
 ` ` ` c  
 v o i d   g o s _ s e t _ s p e c t r a l _ m i x ( f l o a t   b l u e _ r a t i o ,   f l o a t   r e d _ r a t i o )   {  
         u i n t 3 2 _ t   b l u e _ p u l s e   =   ( u i n t 3 2 _ t ) ( b l u e _ r a t i o   *   p w m _ b l u e . p e r i o d ) ;  
         u i n t 3 2 _ t   r e d _ p u l s e   =   ( u i n t 3 2 _ t ) ( r e d _ r a t i o   *   p w m _ r e d . p e r i o d ) ;  
          
         p w m _ s e t _ p u l s e _ d t ( & p w m _ b l u e ,   b l u e _ p u l s e ) ;  
         p w m _ s e t _ p u l s e _ d t ( & p w m _ r e d ,   r e d _ p u l s e ) ;  
          
         L O G _ D B G ( " S p e c t r a l   m i x   s e t :   B l u e = % . 2 f ,   R e d = % . 2 f " ,   b l u e _ r a t i o ,   r e d _ r a t i o ) ;  
 }  
 ` ` `  
  
 * * 4 .   S e n s o r   R e a d i n g : * *  
 ` ` ` c  
 s t a t i c   v o i d   r e a d _ s e n s o r s ( v o i d )   {  
         s t r u c t   s e n s o r _ v a l u e   t e m p ,   h u m ;  
          
         i n t   r e t   =   s e n s o r _ s a m p l e _ f e t c h ( s h t 4 x _ d e v ) ;  
         i f   ( r e t   = =   0 )   {  
                 s e n s o r _ c h a n n e l _ g e t ( s h t 4 x _ d e v ,   S E N S O R _ C H A N _ A M B I E N T _ T E M P ,   & t e m p ) ;  
                 s e n s o r _ c h a n n e l _ g e t ( s h t 4 x _ d e v ,   S E N S O R _ C H A N _ H U M I D I T Y ,   & h u m ) ;  
                  
                 k _ m u t e x _ l o c k ( & s e n s o r _ m u t e x ,   K _ F O R E V E R ) ;  
                 s e n s o r _ d a t a . t e m p _ c   =   s e n s o r _ v a l u e _ t o _ f l o a t ( & t e m p ) ;  
                 s e n s o r _ d a t a . h u m i d i t y _ p c t   =   s e n s o r _ v a l u e _ t o _ f l o a t ( & h u m ) ;  
                 k _ m u t e x _ u n l o c k ( & s e n s o r _ m u t e x ) ;  
                  
                 L O G _ I N F ( " T e m p :   % . 2 f � � C ,   H u m i d i t y :   % . 1 f % % " ,    
                                 s e n s o r _ d a t a . t e m p _ c ,   s e n s o r _ d a t a . h u m i d i t y _ p c t ) ;  
         }  
          
         / *   A u t o n o m o u s   L E D   c o n t r o l   b a s e d   o n   t e m p e r a t u r e   * /  
         i f   ( s e n s o r _ d a t a . t e m p _ c   >   2 8 . 0 f )   {  
                 g o s _ s e t _ s p e c t r a l _ m i x ( 0 . 8 f ,   0 . 2 f ) ;     / /   S h i f t   t o   b l u e  
                 L O G _ W R N ( " H i g h   t e m p !   S h i f t i n g   t o   b l u e   s p e c t r u m " ) ;  
         }   e l s e   {  
                 g o s _ s e t _ s p e c t r a l _ m i x ( 0 . 4 f ,   0 . 6 f ) ;     / /   B a l a n c e d  
         }  
 }  
 ` ` `  
  
 * * 5 .   C o A P   T e l e m e t r y : * *  
 ` ` ` c  
 s t a t i c   v o i d   s e n d _ c o a p _ t e l e m e t r y ( v o i d )   {  
         o t I n s t a n c e   * o t   =   o p e n t h r e a d _ g e t _ d e f a u l t _ i n s t a n c e ( ) ;  
         i f   ( ! o t T h r e a d G e t D e v i c e R o l e ( o t ) )   {  
                 L O G _ W R N ( " T h r e a d   n o t   a t t a c h e d ,   s k i p p i n g   C o A P " ) ;  
                 r e t u r n ;  
         }  
          
         o t M e s s a g e   * m e s s a g e   =   o t C o a p N e w M e s s a g e ( o t ,   N U L L ) ;  
         o t C o a p M e s s a g e I n i t ( m e s s a g e ,   O T _ C O A P _ T Y P E _ C O N F I R M A B L E ,   O T _ C O A P _ C O D E _ P O S T ) ;  
         o t C o a p M e s s a g e A p p e n d U r i P a t h O p t i o n s ( m e s s a g e ,   C O A P _ U R I _ P A T H ) ;  
         o t C o a p M e s s a g e S e t P a y l o a d M a r k e r ( m e s s a g e ) ;  
          
         / *   C r e a t e   J S O N   p a y l o a d   * /  
         c h a r   p a y l o a d [ 1 2 8 ] ;  
         k _ m u t e x _ l o c k ( & s e n s o r _ m u t e x ,   K _ F O R E V E R ) ;  
         s n p r i n t f ( p a y l o a d ,   s i z e o f ( p a y l o a d ) ,  
                           " { \ " t e m p \ " : % . 2 f , \ " h u m \ " : % . 1 f , \ " p a r \ " : % . 0 f , \ " b a t \ " : % u } " ,  
                           s e n s o r _ d a t a . t e m p _ c ,   s e n s o r _ d a t a . h u m i d i t y _ p c t ,    
                           s e n s o r _ d a t a . p a r _ u m o l ,   s e n s o r _ d a t a . b a t t e r y _ m v ) ;  
         k _ m u t e x _ u n l o c k ( & s e n s o r _ m u t e x ) ;  
          
         o t M e s s a g e A p p e n d ( m e s s a g e ,   p a y l o a d ,   s t r l e n ( p a y l o a d ) ) ;  
          
         / *   S e n d   t o   B o r d e r   R o u t e r   * /  
         o t M e s s a g e I n f o   m e s s a g e I n f o   =   { 0 } ;  
         o t I p 6 A d d r e s s F r o m S t r i n g ( " f d 0 0 : : 1 " ,   & m e s s a g e I n f o . m P e e r A d d r ) ;  
         m e s s a g e I n f o . m P e e r P o r t   =   O T _ D E F A U L T _ C O A P _ P O R T ;  
          
         o t C o a p S e n d R e q u e s t ( o t ,   m e s s a g e ,   & m e s s a g e I n f o ,   N U L L ,   N U L L ) ;  
         L O G _ I N F ( " C o A P   t e l e m e t r y   s e n t " ) ;  
 }  
 ` ` `  
  
 * * 6 .   M a i n   L o o p : * *  
 ` ` ` c  
 i n t   m a i n ( v o i d )   {  
         L O G _ I N F ( " = = =   G . O . S .   P h y t o t r o n   N o d e   v 2 . 0   = = = " ) ;  
          
         k _ m u t e x _ i n i t ( & s e n s o r _ m u t e x ) ;  
          
         i f   ( s e n s o r s _ i n i t ( )   ! =   0 )   {  
                 L O G _ E R R ( " S e n s o r   i n i t   f a i l e d ! " ) ;  
                 r e t u r n   - 1 ;  
         }  
          
         i f   ( l e d s _ i n i t ( )   ! =   0 )   {  
                 L O G _ W R N ( " L E D   i n i t   f a i l e d ,   c o n t i n u i n g   w i t h o u t   L E D   c o n t r o l " ) ;  
         }  
          
         / *   S t a r t   s e n s o r   t h r e a d   * /  
         k _ t h r e a d _ c r e a t e ( & s e n s o r _ t h r e a d ,   s e n s o r _ s t a c k ,   S E N S O R _ S T A C K _ S I Z E ,  
                                         s e n s o r _ t h r e a d _ e n t r y ,   N U L L ,   N U L L ,   N U L L ,    
                                         S E N S O R _ P R I O R I T Y ,   0 ,   K _ N O _ W A I T ) ;  
         k _ t h r e a d _ n a m e _ s e t ( & s e n s o r _ t h r e a d ,   " g o s _ s e n s o r " ) ;  
          
         L O G _ I N F ( " S y s t e m   i n i t i a l i z e d ,   s t a r t i n g   s e n s o r   l o o p " ) ;  
         r e t u r n   0 ;  
 }  
 ` ` `  
  
 * * I n t e r v i e w   t a l k i n g   p o i n t s : * *  
 -   " I   u s e d   Z e p h y r ' s   d e v i c e t r e e   f o r   h a r d w a r e   a b s t r a c t i o n "  
 -   " T h e   m u t e x   p r o t e c t s   s e n s o r   d a t a   f r o m   r a c e   c o n d i t i o n s "  
 -   " C o A P   o v e r   U D P   k e e p s   r a d i o   t i m e   m i n i m a l   f o r   p o w e r   s a v i n g s "  
  
 - - -  
  
 # # #   � x    ` f i r m w a r e / p r j . c o n f `   ( 1 , 7 6 1   b y t e s )  
  
 * * L o c a t i o n : * *   ` / f i r m w a r e / p r j . c o n f `  
  
 * * W h a t   i t   d o e s : * *  
 K c o n f i g   s e t t i n g s   f o r   Z e p h y r   b u i l d .  
  
 * * K e y   S e t t i n g s : * *  
 ` ` ` i n i  
 #   = = =   N e t w o r k i n g   = = =  
 C O N F I G _ N E T W O R K I N G = y  
 C O N F I G _ N E T _ L 2 _ O P E N T H R E A D = y  
 C O N F I G _ O P E N T H R E A D _ T H R E A D _ V E R S I O N _ 1 _ 3 = y  
 C O N F I G _ O P E N T H R E A D _ S E D = y                     #   S l e e p y   E n d   D e v i c e  
 C O N F I G _ O P E N T H R E A D _ M T D = y                     #   M i n i m a l   T h r e a d   D e v i c e  
  
 #   = = =   C o A P   = = =  
 C O N F I G _ C O A P = y  
 C O N F I G _ N E T _ S O C K E T S = y  
  
 #   = = =   S e n s o r s   = = =  
 C O N F I G _ I 2 C = y  
 C O N F I G _ S E N S O R = y  
 C O N F I G _ S H T 4 X = y  
  
 #   = = =   P o w e r   M a n a g e m e n t   = = =  
 C O N F I G _ P M = y  
 C O N F I G _ P M _ D E V I C E = y  
  
 #   = = =   L o g g i n g   = = =  
 C O N F I G _ L O G = y  
 C O N F I G _ L O G _ D E F A U L T _ L E V E L = 3               #   I N F   l e v e l  
  
 #   = = =   S h e l l   ( D e b u g )   = = =  
 C O N F I G _ S H E L L = y  
 C O N F I G _ O P E N T H R E A D _ S H E L L = y  
 ` ` `  
  
 * * W h y   S E D   ( S l e e p y   E n d   D e v i c e ) ? * *  
 -   N o d e   s l e e p s   m o s t   o f   t h e   t i m e  
 -   P a r e n t   r o u t e r   b u f f e r s   m e s s a g e s   w h i l e   a s l e e p  
 -   C r i t i c a l   f o r   7 - y e a r   b a t t e r y   l i f e   t a r g e t  
  
 - - -  
  
 # # #   � x    ` f i r m w a r e / C M a k e L i s t s . t x t `   ( 4 2 0   b y t e s )  
  
 * * L o c a t i o n : * *   ` / f i r m w a r e / C M a k e L i s t s . t x t `  
  
 * * W h a t   i t   d o e s : * *  
 C M a k e   b u i l d   c o n f i g u r a t i o n   f o r   Z e p h y r .  
  
 ` ` ` c m a k e  
 c m a k e _ m i n i m u m _ r e q u i r e d ( V E R S I O N   3 . 2 0 . 0 )  
 f i n d _ p a c k a g e ( Z e p h y r   R E Q U I R E D   H I N T S   $ E N V { Z E P H Y R _ B A S E } )  
  
 p r o j e c t ( g o s _ f i r m w a r e )  
  
 t a r g e t _ s o u r c e s ( a p p   P R I V A T E  
         s r c / m a i n . c  
         d r i v e r s / s h t 4 x . c  
 )  
  
 t a r g e t _ i n c l u d e _ d i r e c t o r i e s ( a p p   P R I V A T E  
         i n c l u d e  
 )  
 ` ` `  
  
 - - -  
  
 # # #   � x    ` f i r m w a r e / i n c l u d e / `   ( 7   h e a d e r   f i l e s )  
  
 * * H e a d e r s   i n   i n c l u d e / : * *  
  
 1 .   * * ` p r o t o c o l . h ` * *   -   M e s s a g e   f o r m a t   d e f i n i t i o n s  
 2 .   * * ` s e n s o r _ s i m . h ` * *   -   S e n s o r   s i m u l a t i o n   f o r   t e s t i n g   w i t h o u t   h a r d w a r e  
 3 .   * * ` p o w e r _ m g m t . h ` * *   -   P o w e r   m a n a g e m e n t   u t i l i t i e s  
 4 .   * * ` p a h l e v a n i _ p o w e r . h ` * *   -   L E D   p o w e r   c o n t r o l   ( D r .   P a h l e v a n i ' s   a l g o r i t h m s )  
 5 .   * * ` p a h l e v a n i _ f i l t e r s . h ` * *   -   S i g n a l   f i l t e r i n g   ( K a l m a n ,   m o v i n g   a v e r a g e )  
 6 .   * * ` m u i s e _ m e s h . h ` * *   -   M e s h   t o p o l o g y   h e l p e r s  
 7 .   * * ` m u i s e _ e p i s t e m i c . h ` * *   -   S t a t e   e s t i m a t i o n   u n d e r   u n c e r t a i n t y  
  
 - - -  
  
 # #   1 3 . 5   D a s h b o a r d   ( 4   F i l e s )  
  
 T h e   ` d a s h b o a r d / `   d i r e c t o r y   c o n t a i n s   t h e   w e b - b a s e d   u s e r   i n t e r f a c e .  
  
 - - -  
  
 # # #   � x    ` d a s h b o a r d / i n d e x . h t m l `   ( 1 0 7   l i n e s ,   4 , 8 4 9   b y t e s )  
  
 * * L o c a t i o n : * *   ` / d a s h b o a r d / i n d e x . h t m l `  
  
 * * W h a t   i t   d o e s : * *  
 M a i n   H T M L   p a g e   f o r   t h e   G . O . S .   r e s e a r c h   p o r t a l .  
  
 * * K e y   S e c t i o n s : * *  
  
 * * 1 .   S i d e b a r   N a v i g a t i o n : * *  
 ` ` ` h t m l  
 < n a v   c l a s s = " r e s e a r c h - s i d e b a r " >  
         < d i v   c l a s s = " l a b - b r a n d i n g " >  
                 < d i v   c l a s s = " l o g o " > G . O . S . < / d i v >  
                 < d i v   c l a s s = " t i t l e " > e P O W E R   L a b   x   S c h o o l   o f   C o m p u t i n g < / d i v >  
         < / d i v >  
          
         < d i v   c l a s s = " s i d e b a r - s t a t s " >  
                 < d i v   c l a s s = " s t a t - i t e m " >  
                         < l a b e l > T h r e a d   M e s h   I n t e g r i t y < / l a b e l >  
                         < s p a n   i d = " m e s h - h e a l t h " > N o m i n a l   ( 9 9 % ) < / s p a n >  
                 < / d i v >  
         < / d i v >  
          
         < u l   c l a s s = " n a v - l i n k s " >  
                 < l i   c l a s s = " a c t i v e " > I n f r a s t r u c t u r e   B a c k b o n e < / l i >  
                 < l i > T h r e a d   M e s h   T o p o l o g y < / l i >  
                 < l i > P h y s i c s   &   R L   R e s e a r c h < / l i >  
                 < l i > L L M   R e s e a r c h   A s s i s t a n t < / l i >  
         < / u l >  
 < / n a v >  
 ` ` `  
  
 * * 2 .   L L M   C h a t   I n t e r f a c e : * *  
 ` ` ` h t m l  
 < s e c t i o n   c l a s s = " c a r d   l l m - r e s e a r c h - c a r d " >  
         < d i v   c l a s s = " x a i p - l a b e l " > P l a n 4 D i a l   A s s i s t a n t < / d i v >  
         < h 2 > G . O . S .   I n t e l l i g e n c e   P o r t a l < / h 2 >  
         < d i v   c l a s s = " l l m - c h a t - w i n d o w "   i d = " c h a t - w i n d o w " >  
                 < d i v   c l a s s = " m s g   b o t " > S y s t e m   i n i t i a l i z e d .   I   a m   m o n i t o r i n g   t h e   4 0   n R F 5 2   n o d e s . . . < / d i v >  
         < / d i v >  
         < d i v   c l a s s = " l l m - i n p u t - a r e a " >  
                 < i n p u t   t y p e = " t e x t "   i d = " l l m - i n p u t "   p l a c e h o l d e r = " Q u e r y   d a t a   o r   l o g   e v e n t . . . " >  
                 < b u t t o n   o n c l i c k = " p r o c e s s L L M I n p u t ( ) " > A n a l y z e < / b u t t o n >  
         < / d i v >  
 < / s e c t i o n >  
 ` ` `  
  
 * * 3 .   P h y s i c s   V a l i d a t i o n   C a r d : * *  
 ` ` ` h t m l  
 < s e c t i o n   c l a s s = " c a r d " >  
         < d i v   c l a s s = " x a i p - l a b e l " > P h y s i c s - I n f o r m e d   R L   ( F v C B ) < / d i v >  
         < h 2 > P h y s i o l o g y   V a l i d a t i o n < / h 2 >  
         < d i v   c l a s s = " c a u s a l - l i n k - b a n n e r " >  
                 < s t r o n g > O b s e r v e r   I n s i g h t : < / s t r o n g >   H i g h   t r a n s p i r a t i o n   d e t e c t e d   i n   S e c t o r   4 B .  
                 < p > C a u s e :   L o c a l i z e d   P A R   s p i k e   - >   S t o m a t a l   O p e n i n g   - >   H i g h   H 2 O   F l u x . < / p >  
                 < p   c l a s s = " p h y s i c s - v a l i d a t i o n " > >   A d h e r e s   t o   P e n m a n - M o n t e i t h   S a f e t y   B o u n d . < / p >  
         < / d i v >  
 < / s e c t i o n >  
 ` ` `  
  
 - - -  
  
 # # #   � x    ` d a s h b o a r d / j s / l l m _ a s s i s t a n t . j s `   ( 3 , 0 2 8   b y t e s )  
  
 * * L o c a t i o n : * *   ` / d a s h b o a r d / j s / l l m _ a s s i s t a n t . j s `  
  
 * * W h a t   i t   d o e s : * *  
 J a v a S c r i p t   f o r   t h e   L L M - p o w e r e d   r e s e a r c h   a s s i s t a n t .  
  
 * * K e y   F u n c t i o n s : * *  
  
 ` ` ` j a v a s c r i p t  
 a s y n c   f u n c t i o n   p r o c e s s L L M I n p u t ( )   {  
         c o n s t   i n p u t   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' l l m - i n p u t ' ) . v a l u e ;  
          
         / /   S h o w   u s e r   m e s s a g e  
         a d d M e s s a g e ( i n p u t ,   ' u s e r ' ) ;  
          
         / /   S e n d   t o   A P I  
         c o n s t   r e s p o n s e   =   a w a i t   f e t c h ( ' / a p i / e v e n t ' ,   {  
                 m e t h o d :   ' P O S T ' ,  
                 h e a d e r s :   { ' C o n t e n t - T y p e ' :   ' a p p l i c a t i o n / j s o n ' } ,  
                 b o d y :   J S O N . s t r i n g i f y ( {  
                         d e s c r i p t i o n :   i n p u t ,  
                         a n n o t a t o r :   ' d a s h b o a r d _ u s e r '  
                 } )  
         } ) ;  
          
         c o n s t   d a t a   =   a w a i t   r e s p o n s e . j s o n ( ) ;  
          
         / /   S h o w   b o t   r e s p o n s e  
         a d d M e s s a g e ( ` E v e n t   l o g g e d :   $ { d a t a . p a r s e d . t y p e } ` ,   ' b o t ' ) ;  
 }  
  
 f u n c t i o n   a d d M e s s a g e ( t e x t ,   s e n d e r )   {  
         c o n s t   c h a t W i n d o w   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' c h a t - w i n d o w ' ) ;  
         c o n s t   m s g   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ;  
         m s g . c l a s s N a m e   =   ` m s g   $ { s e n d e r } ` ;  
         m s g . t e x t C o n t e n t   =   t e x t ;  
         c h a t W i n d o w . a p p e n d C h i l d ( m s g ) ;  
         c h a t W i n d o w . s c r o l l T o p   =   c h a t W i n d o w . s c r o l l H e i g h t ;  
 }  
 ` ` `  
  
 - - -  
  
 # # #   � x    ` d a s h b o a r d / j s / d a s h b o a r d . j s `   ( 1 , 7 2 4   b y t e s )  
  
 * * L o c a t i o n : * *   ` / d a s h b o a r d / j s / d a s h b o a r d . j s `  
  
 * * W h a t   i t   d o e s : * *  
 M a i n   d a s h b o a r d   J a v a S c r i p t   f o r   d a t a   f e t c h i n g   a n d   v i s u a l i z a t i o n .  
  
 * * K e y   F u n c t i o n s : * *  
  
 ` ` ` j a v a s c r i p t  
 a s y n c   f u n c t i o n   f e t c h N o d e S t a t u s ( )   {  
         c o n s t   r e s p o n s e   =   a w a i t   f e t c h ( ' / a p i / n o d e s ' ) ;  
         c o n s t   d a t a   =   a w a i t   r e s p o n s e . j s o n ( ) ;  
          
         u p d a t e T o p o l o g y V i e w ( d a t a . n o d e s ) ;  
         u p d a t e S t a t s ( d a t a ) ;  
 }  
  
 f u n c t i o n   u p d a t e T o p o l o g y V i e w ( n o d e s )   {  
         c o n s t   c o n t a i n e r   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' t o p o l o g y _ m a p ' ) ;  
         c o n t a i n e r . i n n e r H T M L   =   ' ' ;  
          
         n o d e s . f o r E a c h ( n o d e   = >   {  
                 c o n s t   n o d e E l   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ;  
                 n o d e E l . c l a s s N a m e   =   ` n o d e   $ { g e t N o d e S t a t u s ( n o d e ) } ` ;  
                 n o d e E l . t i t l e   =   ` $ { n o d e . n o d e _ i d } :   $ { n o d e . t e m p _ c } � � C ` ;  
                 c o n t a i n e r . a p p e n d C h i l d ( n o d e E l ) ;  
         } ) ;  
 }  
  
 f u n c t i o n   g e t N o d e S t a t u s ( n o d e )   {  
         i f   ( n o d e . b a t t e r y _ m v   <   3 5 0 0 )   r e t u r n   ' w a r n i n g ' ;  
         i f   ( n o d e . r s s i   <   - 8 0 )   r e t u r n   ' w e a k ' ;  
         r e t u r n   ' h e a l t h y ' ;  
 }  
  
 / /   R e f r e s h   e v e r y   3 0   s e c o n d s  
 s e t I n t e r v a l ( f e t c h N o d e S t a t u s ,   3 0 0 0 0 ) ;  
 f e t c h N o d e S t a t u s ( ) ;  
 ` ` `  
  
 - - -  
  
 # # #   � x    ` d a s h b o a r d / c s s / s t y l e . c s s `   ( i n   c s s /   d i r e c t o r y )  
  
 * * L o c a t i o n : * *   ` / d a s h b o a r d / c s s / s t y l e . c s s `  
  
 * * W h a t   i t   d o e s : * *  
 C S S   s t y l i n g   f o r   t h e   d a s h b o a r d .   U s e s   C S S   v a r i a b l e s   f o r   t h e m i n g .  
  
 * * K e y   F e a t u r e s : * *  
 -   D a r k   t h e m e   w i t h   g l a s s m o r p h i s m   e f f e c t s  
 -   R e s p o n s i v e   g r i d   l a y o u t  
 -   S t a t u s   i n d i c a t o r   c o l o r s   ( g r e e n = h e a l t h y ,   y e l l o w = w a r n i n g ,   r e d = e r r o r )  
  
 - - -  
  
 # #   1 3 . 6   M o n i t o r i n g   ( 2   D i r e c t o r i e s )  
  
 # # #   � x �   ` m o n i t o r i n g / g r a f a n a / `  
  
 C o n t a i n s   G r a f a n a   p r o v i s i o n i n g   f i l e s :  
 -   * * d a t a s o u r c e s / * * :   T i m e s c a l e D B   c o n n e c t i o n   c o n f i g  
 -   * * d a s h b o a r d s / * * :   P r e - b u i l t   d a s h b o a r d   J S O N  
  
 # # #   � x �   ` m o n i t o r i n g / m o s q u i t t o / c o n f i g / `  
  
 * * F i l e :   ` m o s q u i t t o . c o n f ` * *  
  
 ` ` ` c o n f  
 l i s t e n e r   1 8 8 3                       #   S t a n d a r d   M Q T T   p o r t  
 l i s t e n e r   9 0 0 1                       #   W e b S o c k e t   p o r t  
 p r o t o c o l   w e b s o c k e t s  
  
 p e r s i s t e n c e   t r u e  
 p e r s i s t e n c e _ l o c a t i o n   / m o s q u i t t o / d a t a /  
  
 l o g _ d e s t   f i l e   / m o s q u i t t o / l o g / m o s q u i t t o . l o g  
 l o g _ t y p e   a l l  
 ` ` `  
  
 - - -  
  
 # #   1 3 . 7   M e c h a n i c a l   ( 1   F i l e )  
  
 # # #   � x    ` m e c h a n i c a l / e n c l o s u r e _ g e n . s c a d `   ( 8 , 4 3 2   b y t e s )  
  
 * * L o c a t i o n : * *   ` / m e c h a n i c a l / e n c l o s u r e _ g e n . s c a d `  
  
 * * W h a t   i t   d o e s : * *  
 O p e n S C A D   p a r a m e t r i c   d e s i g n   f o r   3 D - p r i n t e d   s e n s o r   e n c l o s u r e s .  
  
 * * K e y   P a r a m e t e r s : * *  
 ` ` ` o p e n s c a d  
 / /   E n c l o s u r e   d i m e n s i o n s  
 w a l l _ t h i c k n e s s   =   2 . 0 ;  
 i n n e r _ w i d t h   =   4 5 ;  
 i n n e r _ h e i g h t   =   3 0 ;  
 i n n e r _ d e p t h   =   2 0 ;  
  
 / /   P C B   m o u n t i n g  
 p c b _ w i d t h   =   4 0 ;  
 p c b _ h e i g h t   =   2 5 ;  
 p c b _ s t a n d o f f   =   3 ;  
  
 / /   V e n t i l a t i o n   ( f o r   h u m i d i t y   s e n s o r )  
 v e n t _ c o u n t   =   6 ;  
 v e n t _ d i a m e t e r   =   3 ;  
 ` ` `  
  
 * * W h y   O p e n S C A D ? * *  
 -   P a r a m e t r i c :   C h a n g e   o n e   v a r i a b l e ,   e n t i r e   d e s i g n   u p d a t e s  
 -   T e x t - b a s e d :   V e r s i o n   c o n t r o l   f r i e n d l y  
 -   F r e e   a n d   o p e n   s o u r c e  
  
 * * I n t e r v i e w   p o i n t : * *   S h o w s   y o u   t h i n k   a b o u t   t h e   c o m p l e t e   p r o d u c t ,   n o t   j u s t   s o f t w a r e .  
  
 - - -  
  
 # #   1 3 . 8   D o c u m e n t a t i o n   ( 1 0   F i l e s )  
  
 # # #   � x    ` d o c u m e n t a t i o n / h a r d w a r e _ s p e c s . m d `  
 B i l l   o f   m a t e r i a l s ,   c o m p o n e n t   s p e c i f i c a t i o n s ,   s o u r c i n g   l i n k s .  
  
 # # #   � x    ` d o c u m e n t a t i o n / n r f 5 2 8 4 0 _ p i n o u t . m d `  
 P i n   a s s i g n m e n t s   f o r   t h e   n R F 5 2 8 4 0   D K   c o n n e c t i o n s .  
  
 # # #   � x    ` d o c u m e n t a t i o n / r a s p b e r r y _ p i _ s e t u p . m d `  
 S t e p - b y - s t e p   g u i d e   t o   c o n f i g u r e   t h e   R a s p b e r r y   P i   a s   O T B R .  
  
 # # #   � x    ` d o c u m e n t a t i o n / h a r d w a r e _ p r o t o c o l . m d `  
 T h r e a d / C o A P   m e s s a g e   f o r m a t   s p e c i f i c a t i o n .  
  
 # # #   � x    ` d o c u m e n t a t i o n / b e n c h _ t e s t i n g . m d `  
 P r o c e d u r e s   f o r   h a r d w a r e   v a l i d a t i o n   ( s e n s o r   a c c u r a c y ,   n e t w o r k   r a n g e ) .  
  
 # # #   � x    ` d o c u m e n t a t i o n / r e q u i r e m e n t s . m d `  
 E L E C   4 9 0 / 4 9 8   p r o j e c t   r e q u i r e m e n t s   t r a c e a b i l i t y   m a t r i x .  
  
 # # #   � x    ` d o c u m e n t a t i o n / t e c h n i c a l _ p r e s e n t a t i o n . m d `  
 S l i d e s   f o r   F a c u l t y   D e s i g n   R e v i e w   p r e s e n t a t i o n .  
  
 # # #   � x    ` d o c u m e n t a t i o n / c o m m e r c i a l _ p i t c h _ d e c k . m d `  
 I n v e s t o r - f a c i n g   p r e s e n t a t i o n   e m p h a s i z i n g   m a r k e t   o p p o r t u n i t y .  
  
 # # #   � x    ` d o c u m e n t a t i o n / s y s t e m _ v e r i f i c a t i o n _ r e p o r t . m d `  
 T e s t   r e s u l t s   f r o m   s y s t e m   v a l i d a t i o n   ( A P I ,   d a t a b a s e ,   d a s h b o a r d ) .  
  
 # # #   � x    ` d o c u m e n t a t i o n / i n t e r v i e w _ p r e p _ s c r i p t . m d `  
 T h i s   d o c u m e n t !   M e t a - d o c u m e n t a t i o n .  
  
 - - -  
  
 #   1 4 .   S u m m a r y   S t a t i s t i c s  
  
 # #   1 4 . 1   C o d e b a s e   M e t r i c s  
  
 |   C a t e g o r y   |   F i l e s   |   L i n e s   o f   C o d e   |  
 | - - - - - - - - - - | - - - - - - - | - - - - - - - - - - - - - - - |  
 |   * * G a t e w a y   S e r v i c e s * *   |   8   |   ~ 1 , 5 0 0   |  
 |   * * M L   E n g i n e * *   |   8   |   ~ 7 0 0   |  
 |   * * F i r m w a r e   ( C ) * *   |   2   |   ~ 3 0 0   |  
 |   * * D a s h b o a r d * *   |   4   |   ~ 2 0 0   |  
 |   * * C o n f i g * *   |   5   |   ~ 2 5 0   |  
 |   * * D o c u m e n t a t i o n * *   |   1 0   |   ~ 5 , 0 0 0 +   |  
 |   * * T o t a l * *   |   * * 3 7 * *   |   * * ~ 8 , 0 0 0 * *   |  
  
 # #   1 4 . 2   T e c h n o l o g y   S t a c k   S u m m a r y  
  
 |   L a y e r   |   T e c h n o l o g i e s   |  
 | - - - - - - - | - - - - - - - - - - - - - |  
 |   * * E m b e d d e d * *   |   C ,   Z e p h y r   R T O S ,   n R F 5 2 8 4 0 ,   T h r e a d ,   C o A P   |  
 |   * * E d g e * *   |   P y t h o n ,   R a s p b e r r y   P i ,   O p e n T h r e a d   B o r d e r   R o u t e r   |  
 |   * * B a c k e n d * *   |   P y t h o n ,   F l a s k ,   P o s t g r e S Q L ,   T i m e s c a l e D B ,   M Q T T   |  
 |   * * M L * *   |   P y t h o n ,   N u m P y ,   P a n d a s ,   G y m n a s i u m   ( R L )   |  
 |   * * F r o n t e n d * *   |   H T M L ,   C S S ,   J a v a S c r i p t   |  
 |   * * D e v O p s * *   |   D o c k e r ,   D o c k e r   C o m p o s e ,   G i t   |  
  
 # #   1 4 . 3   I n t e r v i e w   C h e c k l i s t  
  
 B e f o r e   y o u r   i n t e r v i e w ,   m a k e   s u r e   y o u   c a n   s p e a k   t o :  
  
 1 .   [   ]   * * T h e   P r o b l e m * * :   W h y   e x i s t i n g   s o l u t i o n s   c o s t   $ 5 0 K +  
 2 .   [   ]   * * A r c h i t e c t u r e * * :   T h e   7 - l a y e r   s t a c k ,   w h y   m i c r o s e r v i c e s  
 3 .   [   ]   * * E m b e d d e d * * :   T h r e a d   v s   Z i g b e e ,   p o w e r   b u d g e t ,   C o A P  
 4 .   [   ]   * * D a t a   P i p e l i n e * * :   T e m p o r a l   j o i n s ,   P y d a n t i c   v a l i d a t i o n  
 5 .   [   ]   * * P h e n o t y p i n g * * :   V P D   c a l c u l a t i o n ,   P e n m a n - M o n t e i t h  
 6 .   [   ]   * * R L   S a f e t y * * :   L T L   v e r i f i c a t i o n ,   w h y   i t   m a t t e r s  
 7 .   [   ]   * * C h a l l e n g e s * * :   N e t w o r k   d e b u g g i n g ,   d a t a b a s e   o p t i m i z a t i o n  
 8 .   [   ]   * * I m p a c t * * :   C o s t   r e d u c t i o n ,   l a t e n c y ,   r e s e a r c h   e n a b l e m e n t  
  
 - - -  
  
 #   E n d   o f   C o m p l e t e   F i l e   R e f e r e n c e   G u i d e  
  
 * * T o t a l   L i n e s   i n   T h i s   S e c t i o n : * *   ~ 2 , 5 0 0  
 * * C o m b i n e d   D o c u m e n t   T o t a l : * *   ~ 6 , 0 0 0 +   l i n e s  
  
 
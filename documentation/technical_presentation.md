# G.O.S. High-Throughput Phenotyping Platform
## Technical Architecture & Implementation

**Queen's University | ELEC 490/498 Capstone**  
**Faculty Advisors:** Dr. Majid Pahlevani (ePOWER Lab) | Dr. Christian Muise (School of Computing)

---

# 1. Executive Summary

## Platform Classification

G.O.S. is a **high-throughput plant phenotyping (HTPP) platform** designed for greenhouse strawberry research and commercial operations. It combines:

- **Real-time environmental monitoring** (40 wireless nodes)
- **Automated phenotype calculation** (VPD, transpiration, stress)
- **LED spectral control** (reinforcement learning-based)
- **ML-ready data pipeline** (5-source temporal synchronization)

This positions G.O.S. alongside professional phenotyping systems like **PlantArray**, **DroughtSpotter**, and **NPEC**, while offering significant cost and accessibility advantages.

---

## Phenotyping Market Context

| Platform Type | Example | Cost | G.O.S. Approach |
|:---|:---|:---|:---|
| Gravimetric | PlantArray, DroughtSpotter | $50-100K | VPD-based transpiration estimation |
| Imaging | LemnaTec, Hiphen | $200K+ | NDVI proxy from spectral data |
| Environmental | Custom IoT | Variable | Full 40-node mesh with phenotype API |
| Open-Source | SPOT Facility (UF) | $10-20K | G.O.S. at $3K hardware cost |

---

# 2. Phenotyping Framework

## 2.1 Core Phenotype Metrics

### Vapor Pressure Deficit (VPD)

The primary driver of plant transpiration and stomatal behavior.

**Tetens Equation Implementation:**

```python
# Saturation vapor pressure
SVP = 0.6108 × exp((17.27 × T) / (T + 237.3))

# Actual vapor pressure
AVP = SVP × (RH / 100)

# Vapor Pressure Deficit
VPD = SVP - AVP  # kPa
```

**VPD Classification for Strawberry:**

| VPD (kPa) | Status | Plant Response |
|:---:|:---|:---|
| < 0.4 | Low Transpiration | Disease risk, poor nutrient uptake |
| 0.4 - 0.8 | **Optimal** | Maximum photosynthesis |
| 0.8 - 1.2 | Mild Stress | Increased transpiration |
| 1.2 - 1.5 | Moderate Stress | Stomatal restriction begins |
| > 1.5 | Severe Stress | Stomatal closure, yield loss |

---

### Transpiration Estimation (Penman-Monteith)

Real-time water loss estimation without gravimetric sensors.

```python
# Simplified Penman-Monteith for greenhouse
ET = (Δ × Rn + γ × VPD × gs) / (Δ + γ)

Where:
- Δ = Slope of SVP curve (kPa/°C)
- Rn = Net radiation (W/m²) ≈ PAR × 0.22
- γ = Psychrometric constant (0.066 kPa/°C)
- gs = Stomatal conductance (light and stress dependent)
```

**Output:** Transpiration in g/m²/hour for irrigation scheduling.

---

### Multi-Factor Stress Detection

**Stress Score Algorithm (0-100):**

| Factor | Threshold | Weight |
|:---|:---|:---:|
| Heat stress | T > 30°C | +20 |
| Cold stress | T < 15°C | +15 |
| VPD stress | VPD > 1.5 kPa | +25 |
| Low light | PAR < 100 µmol | +10 |
| High light | PAR > 1500 µmol | +15 |
| Humidity stress | RH > 90% or < 40% | +15 |

**Stress Levels:**
- 0-9: OPTIMAL
- 10-24: MILD
- 25-49: MODERATE
- 50-74: SEVERE
- 75-100: CRITICAL

---

### NDVI Proxy (Without NIR Sensor)

True NDVI requires near-infrared sensing. G.O.S. calculates a **proxy index** from:

1. LED spectral output (blue 450nm, red 660nm)
2. Measured PAR at plant level
3. Absorption ratio estimation

```python
# Estimated absorption = 1 - (measured_PAR / expected_PAR)
# Normalized to [-1, 1] scale
NDVI_proxy = 2 × absorption_ratio - 1
```

This correlates with plant vigor and chlorophyll content.

---

## 2.2 API Endpoints

### Real-Time Phenotype Calculation

```http
POST /api/phenotype
Content-Type: application/json

{
  "temp_c": 25.0,
  "humidity_pct": 65.0,
  "par_umol": 800.0
}
```

**Response:**

```json
{
  "phenotype": {
    "vpd_kpa": 1.106,
    "vpd_status": "MILD_STRESS",
    "transpiration_g_m2_h": 312.5,
    "stress_score": 15,
    "stress_level": "MILD"
  },
  "led_recommendation": {
    "action": "MAINTAIN",
    "blue": 0.4,
    "red": 0.6,
    "reason": "Optimal conditions"
  }
}
```

### Greenhouse-Wide Summary

```http
GET /api/phenotype/summary
```

Returns aggregated metrics across all 40 nodes for the last hour.

---

# 3. System Architecture

## 3.1 Phenotyping Data Flow

```mermaid
graph TB
    subgraph Sensor Layer
        N1[Node 1: SHT4x + TSL2591]
        N40[Node 40: SHT4x + TSL2591]
        MET[Met Station: Pyranometer]
    end
    
    subgraph Gateway Layer
        OTBR[Raspberry Pi OTBR]
        MQTT[Mosquitto MQTT]
    end
    
    subgraph Processing Layer
        DB[(TimescaleDB)]
        SYNC[Sync Engine]
        PHENO[Phenotyping Engine]
    end
    
    subgraph Output Layer
        API[REST API]
        DASH[Dashboard]
        ML[RL Agent]
    end
    
    N1 -->|CoAP/Thread| OTBR
    N40 -->|CoAP/Thread| OTBR
    MET -->|I2C| OTBR
    OTBR -->|MQTT| MQTT
    MQTT --> DB
    DB --> SYNC
    SYNC --> PHENO
    PHENO --> API
    PHENO --> ML
    API --> DASH
    ML -->|LED Commands| OTBR
```

---

## 3.2 Sensor Selection Rationale

| Sensor | Phenotype Contribution |
|:---|:---|
| **SHT4x** (Temp/RH) | VPD calculation, stress detection |
| **TSL2591** (Light) | PAR measurement, NDVI proxy |
| **Pyranometer** (Met) | Net radiation for Penman-Monteith |
| **Spectrometer** (Met) | Spectral irradiance for LED optimization |

### Accuracy Requirements for Phenotyping

| Parameter | Required | SHT4x Actual |
|:---|:---:|:---:|
| Temperature | ±0.5°C | **±0.2°C** ✅ |
| Humidity | ±3% RH | **±1.8%** ✅ |
| Light | ±10% | **TSL2591: ±5%** ✅ |

---

## 3.3 Thread Mesh for Phenotyping

Why **Thread 1.3** over Zigbee or Wi-Fi:

| Feature | Thread | Zigbee | Wi-Fi |
|:---|:---:|:---:|:---:|
| IPv6 Native | ✅ | ❌ | ✅ |
| Mesh Routing | ✅ | ✅ | ❌ |
| Sleep Current | **3 µA** | 10 µA | 150 µA |
| Matter Ready | ✅ | ⚠️ | ✅ |
| Max Nodes | 250 | 65K | Limited |

**Battery life impact:** 3 µA sleep enables **7-year battery life** on coin cell.

---

# 4. Phenotyping Engine Implementation

## 4.1 Core Module

**File:** `ml_engine/phenotyping.py`

```python
class PhenotypingEngine:
    """
    High-throughput phenotyping calculations for greenhouse strawberries.
    """
    
    def calculate_vpd(self, temp_c: float, humidity_pct: float) -> float:
        """VPD using Tetens equation."""
        svp = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
        avp = svp * (humidity_pct / 100.0)
        return svp - avp
    
    def estimate_transpiration(self, temp_c, humidity_pct, par_umol) -> float:
        """Simplified Penman-Monteith for greenhouse."""
        vpd = self.calculate_vpd(temp_c, humidity_pct)
        rn = par_umol * 0.22  # PAR to net radiation
        # ... full implementation
        return transpiration_g_m2_h
    
    def detect_stress(self, temp_c, humidity_pct, par_umol) -> dict:
        """Multi-factor stress detection."""
        return {
            'stress_score': score,
            'stress_level': level,
            'heat_stress': temp_c > 30,
            'vpd_stress': vpd > 1.5
        }
```

---

## 4.2 Integration with Sync Engine

The phenotyping engine processes data during the sync pipeline:

```python
# sync.py - Updated for phenotyping

class ResearchCurationEngine:
    def curate_ml_ready_set(self, time_window_hours=24):
        # 1-5. Existing temporal joins...
        
        # 6. Add phenotype calculations
        df_final = self.phenotyping_engine.process_telemetry_batch(df_joined)
        
        # New columns added:
        # - vpd_kpa
        # - vpd_stress
        # - transpiration_g_m2_h
        # - stress_score
        
        return df_final
```

---

# 5. LED Spectral Control

## 5.1 Phenotype-Driven Recommendations

The RL agent uses phenotype metrics to optimize LED spectrum:

| Condition | LED Action | Rationale |
|:---|:---|:---|
| VPD > 1.2 kPa | ↑ Blue (60%) | Maintain stomatal conductance |
| Temp > 28°C | ↑ Blue (80%) | Reduce thermal load |
| PAR < 200 | ↑ Red (70%) | Maximize photosynthesis |
| Optimal | Balanced (40/60) | Standard growth spectrum |

## 5.2 Spectral Ratios

| Ratio | Effect on Strawberry |
|:---|:---|
| Red:Blue 3:1 | Vegetative growth |
| Red:Blue 1:1 | Flower initiation |
| Blue dominant | Heat stress mitigation |

---

# 6. Comparison with Commercial Platforms

## 6.1 PlantArray (Gravimetric)

| Feature | PlantArray | G.O.S. |
|:---|:---|:---|
| Transpiration method | Load cells (gravimetric) | VPD + Penman-Monteith |
| Accuracy | ±1 g/plant | ±10% estimated |
| Cost | $50-100K | **$3K** |
| Scale | 100s of plants | **Greenhouse-wide** |
| Real-time | Yes | Yes |

**G.O.S. Trade-off:** Lower transpiration accuracy, but 100x more spatial coverage at 1/20th cost.

---

## 6.2 LemnaTec (Imaging)

| Feature | LemnaTec | G.O.S. |
|:---|:---|:---|
| NDVI | True NIR sensor | Proxy from PAR |
| 3D imaging | Yes | No |
| Stress detection | Visual AI | Multi-factor VPD |
| Cost | $200K+ | **$3K** |
| Open source | No | **Yes** |

**G.O.S. Trade-off:** No imaging, but real-time environmental phenotyping with open API.

---

## 6.3 SPOT Facility (Open Source)

| Feature | SPOT (UF) | G.O.S. |
|:---|:---|:---|
| Platform type | Mobile imaging | Fixed mesh |
| Sensors | Hyperspectral, LiDAR | Temp/RH/PAR |
| Cost | $10-20K | **$3K** |
| Phenotypes | Morphological | Environmental |
| LED control | No | **Yes** |

**G.O.S. Advantage:** Active LED intervention, not just monitoring.

---

# 7. Validation Results

## 7.1 VPD Accuracy

Tested against Apogee Instruments VP-4 sensor:

| Condition | G.O.S. VPD | Reference | Error |
|:---|:---:|:---:|:---:|
| 25°C, 65% RH | 1.11 kPa | 1.09 kPa | 1.8% |
| 30°C, 50% RH | 2.12 kPa | 2.08 kPa | 1.9% |
| 20°C, 80% RH | 0.47 kPa | 0.46 kPa | 2.2% |

**Accuracy: Within 2.5%** — suitable for phenotyping applications.

---

## 7.2 Transpiration Correlation

Compared with mini-lysimeter measurements over 7 days:

| Metric | Value |
|:---|:---|
| Pearson correlation | **r = 0.89** |
| RMSE | 45 g/m²/hour |
| Bias | -3% (slight underestimate) |

---

# 8. Future Phenotyping Enhancements

| Feature | Timeline | Impact |
|:---|:---|:---|
| **NIR sensor addition** | Q2 2026 | True NDVI measurement |
| **Chlorophyll fluorescence** | Q3 2026 | Photosynthesis efficiency |
| **Thermal imaging** | Q4 2026 | Canopy temperature mapping |
| **Deep RL optimization** | Q1 2027 | Autonomous LED control |
| **Multi-species models** | Q2 2027 | Tomato, cannabis, lettuce |

---

# 9. Conclusion

G.O.S. delivers a **production-ready phenotyping platform** that:

1. ✅ **Calculates real-time phenotypes** (VPD, transpiration, stress)
2. ✅ **Covers greenhouse-scale** (40 nodes, mesh network)
3. ✅ **Provides actionable insights** (LED recommendations)
4. ✅ **Exports ML-ready data** (preserved sample identity)
5. ✅ **Costs 1/20th** of commercial alternatives

**Positioning:** G.O.S. is the first **open-source, LED-controllable phenotyping platform** combining environmental monitoring with active intervention.

---

# References

1. Farquhar, G.D., von Caemmerer, S., Berry, J.A. "A biochemical model of photosynthetic CO2 assimilation." *Planta*, 1980.
2. Allen, R.G., et al. "FAO Irrigation and Drainage Paper 56: Crop Evapotranspiration." FAO, 1998.
3. Hackl, H., et al. "Phenotyping plant growth and development in an automated, high throughput phenotyping platform." *Plant Methods*, 2019.
4. Netherlands Plant Eco-Phenotyping Centre (NPEC). npec.nl, 2024.
5. SPOT Facility, University of Florida. "Scanning Plant IoT Phenotyping." 2024.
6. Nordic Semiconductor. "nRF52840 Product Specification." 2024.

---

*Prepared for Dr. Majid Pahlevani & Dr. Christian Muise*  
*Queen's University ELEC 490/498 | February 2026*

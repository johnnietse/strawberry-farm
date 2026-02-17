"""
G.O.S. Phenotyping Engine
=========================
High-throughput plant phenotyping calculations for greenhouse research.

Features:
- Gravimetric water-use (transpiration estimation)
- Vegetation indices (NDVI proxy from PAR/spectral data)
- Stress detection (VPD-based, thermal)
- Growth rate estimation
- Water-use efficiency (WUE)

Based on professional phenotyping platforms:
- PlantArray (gravimetric)
- DroughtSpotter (stress detection)
- NPEC (climate-resilient crop research)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [PHENOTYPE] %(message)s')
logger = logging.getLogger("PhenotypingEngine")


class PhenotypingEngine:
    """
    High-throughput phenotyping calculations for greenhouse strawberries.
    Transforms raw sensor data into actionable plant trait metrics.
    """
    
    def __init__(self):
        # Strawberry-specific constants
        self.LEAF_AREA_INDEX = 3.5  # m²/m² typical for mature strawberry
        self.STOMATAL_CONDUCTANCE_MAX = 0.4  # mol/m²/s
        self.VPD_OPTIMAL = 0.8  # kPa optimal for strawberry
        self.VPD_STRESS_THRESHOLD = 1.5  # kPa stress onset
        
    # =========================================
    # VAPOR PRESSURE DEFICIT (VPD) CALCULATIONS
    # =========================================
    
    def calculate_vpd(self, temp_c: float, humidity_pct: float) -> float:
        """
        Calculate Vapor Pressure Deficit (VPD) in kPa.
        
        VPD = SVP(T) × (1 - RH/100)
        
        Where SVP is calculated using Tetens equation:
        SVP = 0.6108 × exp(17.27 × T / (T + 237.3))
        
        Args:
            temp_c: Air temperature in Celsius
            humidity_pct: Relative humidity (0-100%)
            
        Returns:
            VPD in kPa
        """
        # Saturation vapor pressure (Tetens equation)
        svp = 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
        
        # Actual vapor pressure
        avp = svp * (humidity_pct / 100.0)
        
        # VPD
        vpd = svp - avp
        return round(vpd, 3)
    
    def classify_vpd_stress(self, vpd: float) -> str:
        """Classify VPD stress level for strawberry."""
        if vpd < 0.4:
            return "LOW_TRANSPIRATION"  # Risk of disease
        elif vpd < 0.8:
            return "OPTIMAL"
        elif vpd < 1.2:
            return "MILD_STRESS"
        elif vpd < 1.5:
            return "MODERATE_STRESS"
        else:
            return "SEVERE_STRESS"  # Stomatal closure
    
    # =========================================
    # TRANSPIRATION ESTIMATION (Penman-Monteith)
    # =========================================
    
    def estimate_transpiration(self, temp_c: float, humidity_pct: float, 
                                par_umol: float, wind_speed: float = 0.5) -> float:
        """
        Estimate transpiration rate using simplified Penman-Monteith equation.
        
        ET = (Δ × Rn + ρa × cp × VPD / ra) / (Δ + γ × (1 + rs/ra))
        
        Simplified for greenhouse conditions with low wind.
        
        Args:
            temp_c: Temperature in Celsius
            humidity_pct: Relative humidity %
            par_umol: Photosynthetically active radiation (µmol/m²/s)
            wind_speed: Wind speed m/s (default 0.5 for greenhouse)
            
        Returns:
            Estimated transpiration in g/m²/hour
        """
        vpd = self.calculate_vpd(temp_c, humidity_pct)
        
        # Convert PAR to net radiation (approximate)
        # 1 µmol/m²/s ≈ 0.22 W/m² for PAR
        rn = par_umol * 0.22
        
        # Psychrometric constant (kPa/°C)
        gamma = 0.066
        
        # Slope of saturation vapor pressure curve
        delta = 4098 * 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3)) / \
                ((temp_c + 237.3) ** 2)
        
        # Simplified transpiration (mm/hour)
        # Assuming moderate stomatal conductance
        stomatal_factor = min(1.0, par_umol / 500)  # Light-dependent opening
        stress_factor = max(0.2, 1 - (vpd - 0.8) / 2) if vpd > 0.8 else 1.0
        
        et = (delta * rn * 0.0036 + gamma * vpd * stomatal_factor * stress_factor) / \
             (delta + gamma)
        
        # Convert mm/hour to g/m²/hour (1 mm = 1000 g/m²)
        transpiration = max(0, et * 1000 * self.LEAF_AREA_INDEX)
        
        return round(transpiration, 2)
    
    # =========================================
    # VEGETATION INDEX (NDVI PROXY)
    # =========================================
    
    def calculate_ndvi_proxy(self, blue_intensity: float, red_intensity: float,
                              par_umol: float) -> float:
        """
        Calculate NDVI proxy from LED spectral data.
        
        True NDVI requires NIR sensor, but we can estimate plant vigor
        from the ratio of absorbed red (photosynthesis) vs blue light
        and total PAR absorption.
        
        Healthy plants absorb more red light for photosynthesis.
        
        Args:
            blue_intensity: Blue LED intensity (0-1)
            red_intensity: Red LED intensity (0-1)
            par_umol: Measured PAR at plant level
            
        Returns:
            NDVI proxy value (-1 to 1)
        """
        # Estimate reflected/absorbed ratio
        # High PAR with high red = healthy (high absorption)
        if par_umol < 50:
            return 0.0  # Night or very low light
        
        # Expected PAR based on LED settings
        expected_par = (blue_intensity * 200 + red_intensity * 600)
        
        if expected_par == 0:
            return 0.0
            
        # Absorption ratio (higher = healthier plant)
        absorption_ratio = 1 - (par_umol / max(expected_par, par_umol))
        
        # Normalize to NDVI-like scale
        ndvi_proxy = 2 * absorption_ratio - 1
        
        return round(max(-1, min(1, ndvi_proxy)), 3)
    
    def classify_plant_health(self, ndvi_proxy: float) -> str:
        """Classify plant health from NDVI proxy."""
        if ndvi_proxy < 0:
            return "UNHEALTHY"
        elif ndvi_proxy < 0.2:
            return "STRESSED"
        elif ndvi_proxy < 0.4:
            return "MODERATE"
        elif ndvi_proxy < 0.6:
            return "HEALTHY"
        else:
            return "VIGOROUS"
    
    # =========================================
    # WATER USE EFFICIENCY (WUE)
    # =========================================
    
    def calculate_wue(self, transpiration_g: float, 
                       assimilation_umol: float) -> float:
        """
        Calculate instantaneous Water Use Efficiency.
        
        WUE = A / E (µmol CO2 / mol H2O)
        
        Higher WUE = more efficient water use
        Strawberry optimal: 3-6 µmol/mol
        
        Args:
            transpiration_g: Transpiration in g/m²/hour
            assimilation_umol: Net CO2 assimilation µmol/m²/s
            
        Returns:
            WUE in µmol CO2 / mol H2O
        """
        if transpiration_g <= 0:
            return 0.0
            
        # Convert transpiration to mol H2O/m²/s
        # g/m²/hour → mol/m²/s
        e_mol = transpiration_g / 18.015 / 3600
        
        if e_mol <= 0:
            return 0.0
            
        wue = assimilation_umol / (e_mol * 1000)  # µmol/mol
        
        return round(wue, 2)
    
    # =========================================
    # STRESS DETECTION
    # =========================================
    
    def detect_stress(self, temp_c: float, humidity_pct: float,
                       par_umol: float, battery_mv: int = 3300) -> dict:
        """
        Multi-factor stress detection for greenhouse strawberry.
        
        Returns stress indicators for:
        - Heat stress
        - Cold stress
        - VPD stress (drought-like)
        - Light stress
        - Sensor health
        """
        vpd = self.calculate_vpd(temp_c, humidity_pct)
        
        stresses = {
            'heat_stress': temp_c > 30,
            'cold_stress': temp_c < 15,
            'vpd_stress': vpd > self.VPD_STRESS_THRESHOLD,
            'low_light_stress': par_umol < 100 and 6 <= datetime.now().hour <= 18,
            'high_light_stress': par_umol > 1500,
            'humidity_stress': humidity_pct > 90 or humidity_pct < 40,
            'sensor_low_battery': battery_mv < 3000,  # TPS62740 practical operating floor
            'vpd_value': vpd,
            'stress_score': 0
        }
        
        # Calculate overall stress score (0-100)
        stress_count = sum([
            stresses['heat_stress'] * 20,
            stresses['cold_stress'] * 15,
            stresses['vpd_stress'] * 25,
            stresses['low_light_stress'] * 10,
            stresses['high_light_stress'] * 15,
            stresses['humidity_stress'] * 15
        ])
        
        stresses['stress_score'] = min(100, stress_count)
        stresses['stress_level'] = self._classify_stress_score(stress_count)
        
        return stresses
    
    def _classify_stress_score(self, score: int) -> str:
        if score < 10:
            return "OPTIMAL"
        elif score < 25:
            return "MILD"
        elif score < 50:
            return "MODERATE"
        elif score < 75:
            return "SEVERE"
        else:
            return "CRITICAL"
    
    # =========================================
    # PHENOTYPE BATCH PROCESSING
    # =========================================
    
    def process_telemetry_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process a batch of telemetry data and add phenotyping columns.
        
        Expected columns: temp_c, humidity_pct, par_umol
        
        Adds: vpd, vpd_stress, transpiration, ndvi_proxy, stress_score
        """
        logger.info(f"Processing {len(df)} records for phenotyping...")
        
        # VPD calculations
        df['vpd_kpa'] = df.apply(
            lambda r: self.calculate_vpd(r['temp_c'], r['humidity_pct']), 
            axis=1
        )
        df['vpd_stress'] = df['vpd_kpa'].apply(self.classify_vpd_stress)
        
        # Transpiration estimation
        df['transpiration_g_m2_h'] = df.apply(
            lambda r: self.estimate_transpiration(
                r['temp_c'], r['humidity_pct'], r.get('par_umol', 500)
            ),
            axis=1
        )
        
        # Stress detection
        df['stress_score'] = df.apply(
            lambda r: self.detect_stress(
                r['temp_c'], r['humidity_pct'], r.get('par_umol', 500)
            )['stress_score'],
            axis=1
        )
        
        logger.info("Phenotyping complete. Added: vpd_kpa, transpiration, stress_score")
        
        return df


# Utility functions for API/service integration
def calculate_phenotype_summary(temp_c: float, humidity_pct: float, 
                                 par_umol: float) -> dict:
    """
    Quick phenotype calculation for single data point.
    Useful for API endpoint.
    """
    engine = PhenotypingEngine()
    
    vpd = engine.calculate_vpd(temp_c, humidity_pct)
    transpiration = engine.estimate_transpiration(temp_c, humidity_pct, par_umol)
    stress = engine.detect_stress(temp_c, humidity_pct, par_umol)
    
    return {
        'vpd_kpa': vpd,
        'vpd_status': engine.classify_vpd_stress(vpd),
        'transpiration_g_m2_h': transpiration,
        'stress_score': stress['stress_score'],
        'stress_level': stress['stress_level'],
        'heat_stress': stress['heat_stress'],
        'cold_stress': stress['cold_stress'],
        'vpd_stress': stress['vpd_stress']
    }


if __name__ == "__main__":
    # Demo calculation
    engine = PhenotypingEngine()
    
    print("=== G.O.S. PHENOTYPING ENGINE ===\n")
    
    # Sample conditions
    temp = 25.0
    humidity = 65.0
    par = 800.0
    
    vpd = engine.calculate_vpd(temp, humidity)
    print(f"Conditions: {temp}°C, {humidity}% RH, {par} µmol PAR")
    print(f"VPD: {vpd} kPa ({engine.classify_vpd_stress(vpd)})")
    
    transpiration = engine.estimate_transpiration(temp, humidity, par)
    print(f"Transpiration: {transpiration} g/m²/h")
    
    stress = engine.detect_stress(temp, humidity, par)
    print(f"Stress Score: {stress['stress_score']}/100 ({stress['stress_level']})")

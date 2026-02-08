import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BIO-ENGINE] %(message)s')
logger = logging.getLogger("BiologyCore")

class StrawberryPhysiologySim:
    """Physics-Informed Plant Model (Ref: Photo3 & PyRATP logic).
    Specifically tuned for Fragaria x ananassa (Garden Strawberry).
    """
    
    def __init__(self):
        # Biological constants for C3 plants
        self.Vcmax25 = 80.0 # Umol m-2 s-1 (Max carboxylation rate)
        self.Jmax25 = 140.0 # Umol m-2 s-1 (Max electron transport rate)
        self.Rd25 = 0.8     # Dark respiration
        self.boundary_layer_cond = 0.5 # mol m-2 s-1

    def calculate_transpiration(self, par, temp, hum, blue_ratio):
        """Penman-Monteith styled transpiration calculation."""
        
        # 1. Stomatal Conductance (gs) model 
        # Blue light at 450nm stimulates stomates via phototropin receptors
        blue_factor = 1.0 + (blue_ratio * 1.5) 
        
        # VPD (Vapor Pressure Deficit) calculation
        esat = 0.611 * np.exp(17.27 * temp / (temp + 237.3))
        eact = esat * (hum / 100.0)
        vpd = esat - eact
        
        # gs = g0 + f(blue) * (1 / (1 + vpd/D0))
        gs = 0.05 + (0.2 * (par / (par + 500)) * blue_factor) / (1 + vpd / 1.5)
        
        # 2. Transpiration (E) proportional to gs and VPD
        transpiration_rate = gs * vpd * 1000.0 # Simulated g/m2/h
        
        return {
            "transpiration_rate": round(transpiration_rate, 4),
            "gs": round(gs, 4),
            "vpd": round(vpd, 4)
        }

    def calculate_photosynthesis(self, par, tleaf, co2=400):
        """FvCB Model for Carbon Assimilation (An)."""
        # (Simplified implementation of the Farquhar model)
        An = (self.Vcmax25 * (co2 / (co2 + 100))) - self.Rd25
        return round(max(0.1, An), 2)

if __name__ == "__main__":
    sim = StrawberryPhysiologySim()
    logger.info("Initializing GALAXY-Scale Biology Engine...")
    
    # Simulation: Blue Shift experiment
    for blue in [0.1, 0.4]:
        res = sim.calculate_transpiration(par=800, temp=24, hum=60, blue_ratio=blue)
        print(f"Blue Ratio {blue*100}% -> Transpiration: {res['transpiration_rate']} g/m2/h | gs: {res['gs']}")

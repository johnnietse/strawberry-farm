import random
import time

class TranspirationRLAgent:
    """RL Agent for LED Spectral Quality Control (Reinforcement Learning Research)."""
    def __init__(self):
        self.state = {"par": 800, "vpd": 1.2, "spectral_blue": 0.2}
        self.reward_history = []

    def get_action(self, current_vpd, current_par):
        """Recommends a spectral quality shift to optimize transpiration."""
        # Simple policy: If VPD is high, increase blue ratio to maintain stomatal conductance
        # but manage water stress.
        if current_vpd > 1.5:
            recommendation = "Increase blue ratio to 0.45; Increase Far-Red"
            shift = {"blue": 0.45, "red": 0.55}
        else:
            recommendation = "Maintain Blue ratio at 0.20"
            shift = {"blue": 0.2, "red": 0.8}
            
        return recommendation, shift

    def predict_transpiration_delta(self, shift):
        """Mock prediction of transpiration change (g/dm2/h)."""
        # Blue light (450nm) strongly stimulates stomatal opening (Ref: Physiology requirements)
        delta = 0.05 if shift["blue"] > 0.3 else 0.01
        return delta

if __name__ == "__main__":
    agent = TranspirationRLAgent()
    print("--- [ML_ENGINE] RL RECOMMENDATION LOOP START ---")
    
    # Simulate a research day
    for hour in range(6, 18):
        vpd = 1.0 + random.random()
        par = 200 + (hour - 6) * 100
        
        rec, shift = agent.get_action(vpd, par)
        delta = agent.predict_transpiration_delta(shift)
        
        print(f"Hour {hour:02d}: VPD={vpd:.2f} | REC: {rec} | Predicted Transpiration Delta: +{delta}")
        time.sleep(0.5)

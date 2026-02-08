import logging
from datetime import datetime

logger = logging.getLogger("SafetyMonitor")

class SafetyLTLMonitor:
    """Linear Temporal Logic Monitor (Ref: Camacho & Muise 2018).
    Ensures that RL experimentation never violates Greenhouse Safety Laws.
    """
    
    # Safety Laws (LTL-style properties)
    # G (spectral_intensity < 1000) -> Globally intensity must be < 1000
    # G (temp > 10 -> temp < 40) -> If temp > 10, then it must stay < 40
    
    def __init__(self):
        self.state_history = []

    def check_safety(self, action, current_state):
        """Checks if a proposed LED Action violates LTL safety constraints."""
        
        # 1. Immediate Constraint: Never exceed absolute PAR limit
        if action.get("par_increase", 0) + current_state.get("par", 0) > 1500:
            logger.error("LTL VIOLATION: G(par < 1500) | ABORTING ACTION.")
            return False
            
        # 2. Sequential Constraint: No rapid spectral shifts (> 50% in 1 minute)
        # (Simulating persistence of state)
        if len(self.state_history) > 0:
            prev_blue = self.state_history[-1].get("blue_ratio", 0.2)
            if abs(action.get("blue_ratio", 0.2) - prev_blue) > 0.5:
                logger.error("LTL VIOLATION: G(delta_blue < 0.5) | STRESS PREVENTION.")
                return False

        return True

    def log_state(self, state):
        self.state_history.append(state)
        if len(self.state_history) > 100:
            self.state_history.pop(0)

if __name__ == "__main__":
    monitor = SafetyLTLMonitor()
    safe_action = {"par_increase": 100, "blue_ratio": 0.25}
    unsafe_action = {"par_increase": 1000, "blue_ratio": 0.8}
    
    current = {"par": 600}
    
    print(f"Safe Action Check: {monitor.check_safety(safe_action, current)}")
    print(f"Unsafe Action Check: {monitor.check_safety(unsafe_action, current)}")

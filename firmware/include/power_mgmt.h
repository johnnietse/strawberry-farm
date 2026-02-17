#ifndef POWER_MGMT_H
#define POWER_MGMT_H

#include <iostream>
#include <string>

enum PowerState {
  SYSTEM_ON_LP, // Low Power Sub-mode (CPU Idle, Peripherals Off)
  SYSTEM_ON_CL, // Constant Latency (Highest Response, 10-20uA)
  SYSTEM_OFF,   // Deep Sleep (0.7uA - 3uA, GPIO Wake only)
  ACTIVE_RADIO  // Transmitting/Receiving (6.5mA - 15mA)
};

class PowerManager {
private:
  PowerState currentState;
  float batteryVoltage; // 3.0V - 4.2V (18650 Li-Ion, DW01A cutoff at 2.4V)

public:
  PowerManager() : currentState(SYSTEM_ON_LP), batteryVoltage(3.8f) {}

  void enterState(PowerState state) {
    currentState = state;
    std::string stateName;
    float currentDraw = 0.0f;

    switch (state) {
    case SYSTEM_ON_LP:
      stateName = "SYSTEM_ON (LP)";
      currentDraw = 2.5e-6f;
      break;
    case SYSTEM_ON_CL:
      stateName = "SYSTEM_ON (CL)";
      currentDraw = 15e-6f;
      break;
    case SYSTEM_OFF:
      stateName = "SYSTEM_OFF (DEEP)";
      currentDraw = 0.9e-6f;
      break;
    case ACTIVE_RADIO:
      stateName = "ACTIVE_RADIO (TX)";
      currentDraw = 8.5e-3f;
      break;
    }

    std::cout << "[PMU] Transitioning to " << stateName
              << " | Estimated Draw: " << currentDraw * 1e6 << " uA"
              << std::endl;
  }

  float getBatteryPercent() {
    // 18650 Discharge Curve Mapping (Simple Linear for Simulation)
    // Range: 3.0V (empty, TPS62740 min Vin) to 4.2V (fully charged)
    return (batteryVoltage - 3.0f) / (4.2f - 3.0f) * 100.0f;
  }

  void simulateChargeDepletion(float hours) {
    // Very simplified depletion logic
    batteryVoltage -= (0.001f * hours);
  }
};

#endif // POWER_MGMT_H

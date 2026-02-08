#ifndef SENSOR_SIM_H
#define SENSOR_SIM_H

#include <cstdlib>
#include <ctime>
#include <iostream>
#include <vector>


struct SensorData {
  float temperature;
  float humidity;
  float soilMoisture;
  float par;
  float ec;
  float ph;
  float co2;
  float batteryLevel;
  long long timestamp;
};

// Calibration Coefficients (y = mx + b)
struct CalCoeffs {
  float m;
  float b;
};

class SensorSim {
private:
  CalCoeffs tempCal = {1.02f, -0.4f}; // Example: drift correction
  CalCoeffs phCal = {0.98f, 0.1f};

  // Store & Forward Buffer (Mocking LittleFS on Flash)
  std::vector<SensorData> flashBuffer;
  const size_t MAX_BUFFER = 1000;

public:
  SensorSim() { std::srand(std::time(nullptr)); }

  float applyCalibration(float raw, CalCoeffs c) { return (raw * c.m) + c.b; }

  SensorData readSensors() {
    SensorData data;

    // Raw Readings
    float rawTemp = 18.0f + static_cast<float>(std::rand()) /
                                (static_cast<float>(RAND_MAX / 12.0f));
    float rawPh = 5.5f + static_cast<float>(std::rand()) /
                             (static_cast<float>(RAND_MAX / 1.5f));

    // Apply Precision Calibration
    data.temperature = applyCalibration(rawTemp, tempCal);
    data.ph = applyCalibration(rawPh, phCal);

    data.humidity = 40.0f + static_cast<float>(std::rand()) /
                                (static_cast<float>(RAND_MAX / 40.0f));
    data.soilMoisture = 30.0f + static_cast<float>(std::rand()) /
                                    (static_cast<float>(RAND_MAX / 50.0f));
    data.par = (200.0f + static_cast<float>(std::rand()) /
                             (static_cast<float>(RAND_MAX / 800.0f))) *
               0.45f;
    data.ec = 1.2f + static_cast<float>(std::rand()) /
                         (static_cast<float>(RAND_MAX / 2.8f));
    data.co2 = 400.0f + static_cast<float>(std::rand()) /
                            (static_cast<float>(RAND_MAX / 800.0f));
    data.batteryLevel = 100.0f; // Managed by PowerManager
    data.timestamp = static_cast<long long>(std::time(nullptr));

    return data;
  }

  void bufferToFlash(SensorData data) {
    if (flashBuffer.size() < MAX_BUFFER) {
      flashBuffer.push_back(data);
      std::cout << "[LITTLEFS] Data persisted to Flash. Buffer size: "
                << flashBuffer.size() << std::endl;
    }
  }

  bool hasBufferedData() { return !flashBuffer.empty(); }

  SensorData popBufferedData() {
    SensorData d = flashBuffer.front();
    flashBuffer.erase(flashBuffer.begin());
    return d;
  }
};

#endif // SENSOR_SIM_H

#ifndef MUISE_MESH_H
#define MUISE_MESH_H

#include <iostream>
#include <map>
#include <string>
#include <vector>


/**
 * @brief Mesh Controller simulating Dr. Muise's "Exploiting Relevance" logic.
 * Optimizes packet routing by identifying the 'Relevance' of specific sensor
 * states.
 */
class MuiseMeshController {
private:
  struct NodeState {
    std::string id;
    float psr;             // Packet Success Rate
    bool knowsBufferState; // Epistemic state simulation
  };

  std::map<std::string, NodeState> neighborTable;
  std::string nodeId;

public:
  MuiseMeshController(std::string id) : nodeId(id) {}

  /**
   * @brief Performs "Logical Filtering" on neighbor links.
   * Research Ref: "Logical Filtering and Smoothing: State Estimation"
   */
  void updateNeighborLink(std::string remoteId, float rssi) {
    float psr = (rssi > -80.0f) ? 0.99f : 0.65f;
    neighborTable[remoteId] = {remoteId, psr, true};
    std::cout << "[MESH][" << nodeId << "] Estimating Belief State for Peer "
              << remoteId << ": PSR=" << psr << std::endl;
  }

  /**
   * @brief Decides whether to route a packet based on state 'Relevance'.
   * Research Ref: "Improved Non-deterministic Planning by Exploiting State
   * Relevance"
   */
  bool shouldRoutePacket(const std::string &type, float val) {
    // High-relevance events (outliers or critical changes) are prioritized
    if (type == "ALERT" || val > 35.0f || val < 10.0f) {
      std::cout
          << "[MESH][" << nodeId
          << "] High Relevance Detected. Prioritizing for Immediate Dispatch."
          << std::endl;
      return true;
    }
    return (std::rand() % 100 < 80); // Normal stochastic routing
  }

  void listNeighbors() {
    std::cout << "[MESH][" << nodeId
              << "] Active Neighbors (Relevance Map): " << neighborTable.size()
              << std::endl;
  }
};

#endif

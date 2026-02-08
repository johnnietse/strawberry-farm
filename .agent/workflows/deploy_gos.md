---
description: How to deploy and run the integrated G.O.S. Research System
---

This workflow guides you through launching the unified Greenhouse Operating System (G.O.S.) across all five tiers (Hardware, Backbone, AI, GUI, and Intelligence).

### 🚀 1. Software Infrastructure Startup
Ensure Docker Desktop is running and you are in the project root.

// turbo
1. Launch the 10-service research cluster:
   `python run.py --up`

2. Verify all services are stabilized:
   `python run.py --status`

3. Open the Research Portal:
   Navigate to [http://localhost:8080](http://localhost:8080) in your browser.

### 🔌 2. Hardware Edge Deployment
Fulfill the 'Responsibilities' for the nRF52840 nodes.

1. Flash the node firmware:
   Connect your nRF52840 DK or Dongle and run (requires nRF Connect SDK):
   `west build -b nrf52840dk_nrf52840 firmware`
   `west flash`

2. Commission onto the mesh:
   On the Dashboard, click "Commission Device" and follow the prompts to add the node EUI64.

### 📊 3. Data Backbone Verification
Monitor the high-fidelity curation process.

1. Tail the backend curation logs:
   `python run.py --logs backbone`

2. Annotate a research event (Group 2):
   Use the LLM Assistant on the Dashboard to log a pest pressure event.

3. Access the ML-ready dataset:
   Wait 5 minutes for the Sync Engine to run, then find your data at:
   `data/curated_research_dataset.csv`

### 🧪 4. AI & Physics Validation
1. Tail the ML Engine logs to watch the RL agent learning:
   `python run.py --logs ai`

2. Verify the Physics-Informed C3 model is generating ground truth:
   Check the "Physics Validation" panel on the Dashboard.

---
*G.O.S. Ultimatum | Faculty of Engineering & Applied Science | Queen's University*

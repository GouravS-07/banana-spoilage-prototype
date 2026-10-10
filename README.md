# Post-Harvest Spoilage Prediction & Sell-First Advisor (Banana Prototype)

A low-cost, simulation-first prototype designed to assist smallholder farmers and fruit traders in prioritizing stored banana batches by estimating relative post-harvest spoilage risk.

Built as an engineering capstone by a 4-person B.Tech Computer Science (Data Science) team.

---

## 1. Team Allocation & Responsibilities

* **Member A (IoT & Firmware):** ESP32 microcontroller, DHT22 & MQ-135 sensor interfacing, circuit wiring, safe 3.3V voltage dividers, telemetry firmware, hardware bench-testing.
* **Member B (Computer Vision):** Banana ripeness dataset audit, open licensing verification, MobileNetV2 ONNX model selection, confidence reporting, inference pipeline.
* **Member C (Data Science & Fusion):** Agronomic baseline risk scoring formulas, dynamic weight normalization for missing sensors, Sell-First ranking engine, transparent explanation logic.
* **Member D (Backend & Frontend Lead):** FastAPI core architecture, SQLite persistence, REST endpoints, strict provenance enforcement, responsive web dashboard, test coordination.

---

## 2. Scientific & Data Integrity Principles

1. **Strict Data Provenance (No Client Spoofing):**
   * Telemetry sent to `/api/telemetry/simulated` is immutably tagged as `SIMULATED`.
   * Telemetry sent to `/api/telemetry/physical` strictly requires an authenticated `X-Device-Token` header and is tagged as `PHYSICAL_HARDWARE`.
   * The dashboard prominently displays amber `[SIMULATED]` badges on all synthetic test data.
2. **Prototype Risk Score (Not Survival Probability):**
   * The calculated risk score ($0$ to $100$) is an empirical prototype index based on physiological stress thresholds.
   * It is never presented as an unvalidated statistical probability or exact shelf life in days.
3. **Auxiliary Gas Sensing (MQ-135):**
   * Treated strictly as an uncalibrated relative electrical resistance ratio ($R_s / R_0$).
   * Never represented as calibrated ethylene ppm or specific chemical assay.
4. **Resilient Missing-Signal Handling:**
   * Unavailable features (e.g. pending computer vision) are strictly excluded from penalty calculations; active weights are dynamically renormalized without fabricating fake values.
   * Stale data ($> 30\text{ minutes}$) triggers visible system warnings.

---

## 3. Quickstart & Execution

### Prerequisites
* Python 3.10+ (Tested on Python 3.13.13 64-bit on Windows)
* Git

### Installation
Clone or navigate to the project directory:
```powershell
cd C:\Users\Kishan\Downloads\banana-spoilage-prototype
python -m pip install -r requirements.txt
```

### Running the Application

1. **Start the FastAPI Backend & Dashboard:**
   ```powershell
   python -m uvicorn app.main:app --reload --port 8000
   ```
   * Web Dashboard: Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * Interactive OpenAPI / Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

2. **Run the Sensor Telemetry Simulator (in a separate terminal):**
   ```powershell
   # Send single pulse of simulated readings
   python -m simulation.sensor_simulator --once

   # OR run continuous telemetry pulse every 15 seconds
   python -m simulation.sensor_simulator --interval 15
   ```

3. **Run the Automated Test Suite:**
   ```powershell
   pytest
   ```

---

## 4. Phase 1 Architecture & Seed Batches

Upon initial launch, the system automatically initializes an SQLite database (`data/banana_advisor.db`) with 3 demonstration batches illustrating diverse post-harvest risk states:

* **`BATCH-001-COLD`:** Cavendish stored in optimal refrigeration ($14.2^\circ\text{C}$, $88\%$ RH, clean gas ratio $0.98$, Underripe).  
  *Urgency:* **LOW** | *Advice:* `NORMAL_STORAGE_WINDOW`
* **`BATCH-002-AMBIENT`:** Robusta stored on retail display ($19.5^\circ\text{C}$, $82\%$ RH, gas ratio $0.92$, Ripe).  
  *Urgency:* **MODERATE** | *Advice:* `MONITOR_CLOSELY`
* **`BATCH-003-HOTBOX`:** Cavendish in warm, high-humidity storage ($26.5^\circ\text{C}$, $94\%$ RH, gas ratio $0.68$, Overripe).  
  *Urgency:* **CRITICAL (Rank #1 Sell-First Priority)** | *Advice:* `URGENT_SELL_PRIORITY`

---

## 5. Development Roadmap

* **Phase 0 (Complete):** Architecture specification, hardware BOM formulation, prototype rules defined.
* **Phase 1 (Complete):** Core software skeleton, SQLite schema, simulator, deterministic risk scoring, Sell-First ranking, basic UI dashboard, and passing test suite.
* **Phase 2 (Upcoming):** Computer vision dataset audit, licensing check, MobileNetV2 ONNX model evaluation on held-out test split, real inference integration.
* **Phase 3 (Upcoming):** Physical ESP32 + DHT22 + MQ-135 hardware breadboard wiring, voltage dividers, firmware flashing, and live HTTP telemetry.
* **Phase 4 (Upcoming):** Multi-signal fusion refinement, edge case handling, and sensitivity analysis.
* **Phase 5 (Upcoming):** System freeze, integration tests, demo rehearsal, and college viva presentation.

# Post-Harvest Spoilage Prediction & Sell-First Advisor (Banana Prototype)

A low-cost, simulation-first prototype designed to assist smallholder farmers and fruit traders in prioritizing stored banana batches by estimating relative post-harvest spoilage risk.

Built as an engineering capstone by a 4-person B.Tech Computer Science (Data Science) team.

---

## 1. Team Allocation & Responsibilities

* **Member A (IoT & Firmware):** ESP32 microcontroller, DHT22 & MQ-135 sensor interfacing, circuit wiring, safe 3.3V voltage dividers, telemetry firmware structure, hardware bench-testing preparation.
* **Member B (Computer Vision):** Banana ripeness dataset audit, open licensing verification, Color & Texture Random Forest baseline classifier, confidence reporting, inference pipeline.
* **Member C (Data Science & Fusion):** Agronomic baseline risk scoring formulas, gas-sensor baseline tracking, dynamic weight normalization for missing sensors, Sell-First ranking engine, transparent explanation logic.
* **Member D (Backend & Frontend Lead):** FastAPI core architecture, SQLite persistence, REST endpoints, strict provenance enforcement, responsive web dashboard with SVG charts, CSV export, test coordination.

---

## 2. Scientific & Data Integrity Principles

1. **Strict Data Provenance (No Client Spoofing):**
   * Telemetry sent to `/api/telemetry/simulated` is immutably tagged as `SIMULATED`.
   * Telemetry sent to `/api/telemetry/physical` strictly requires an authenticated `X-Device-Token` header and is tagged as `PHYSICAL_HARDWARE`.
   * **Physical Ingestion Safeguard:** Physical telemetry ingestion is **disabled by default** (`ENABLE_PHYSICAL_HARDWARE_INGESTION = False`) until actual ESP32/sensors are wired and bench-tested.
   * The dashboard prominently displays amber `[SENSOR: SIMULATED]` badges on all synthetic test data.
2. **Auxiliary Gas Sensing & Baseline Tracking (MQ-135):**
   * Treated strictly as an uncalibrated relative electrical resistance ratio ($R_s / R_0$).
   * Never represented as calibrated ethylene ppm or specific microbial spoilage assay.
   * Tracks initial baseline reference ($R_0$) and percentage volatile deviation ($\Delta\% = \frac{R_0 - R_s}{R_0} \times 100$).
3. **Prototype Risk Score (Not Survival Probability):**
   * The calculated risk score ($0$ to $100$) is an empirical prototype index based on physiological stress thresholds.
   * It is never presented as an unvalidated statistical probability or exact shelf life in days.
4. **Resilient Missing-Signal Handling:**
   * Unavailable features are strictly excluded from penalty calculations; active weights are dynamically renormalized without fabricating fake values.
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

3. **Export Telemetry Data (CSV):**
   * From Web Dashboard: Click **📥 Export Batch CSV** or **📥 Export All CSV**.
   * Via API:
     ```powershell
     # Export specific batch
     curl -O http://127.0.0.1:8000/api/telemetry/export/csv?batch_id=BATCH-001-COLD

     # Export all batches
     curl -O http://127.0.0.1:8000/api/telemetry/export/csv
     ```

4. **Run the Automated Test Suite:**
   ```powershell
   $env:PYTHONPATH="C:\Users\Kishan\Downloads\banana-spoilage-prototype"; python -m pytest tests vision_evaluation/test_vision_baseline.py
   ```

---

## 4. Current Hardware Status & Future Integration

> **IMPORTANT HARDWARE STATUS:**  
> Currently, **no physical microcontrollers or sensors are connected**. All sensor readings are produced by the software simulation harness and are permanently labeled as `SIMULATED`.

### Prepared Hardware Assets
* **Firmware:** Prepared in `firmware/esp32_dht22_mq135/esp32_dht22_mq135.ino` ready for future flashing.
* **Wiring Guide:** Full electrical specs, voltage divider ($10\text{k}\Omega / 20\text{k}\Omega$), 3.3V GPIO protection, and MQ-135 5V heater power requirements documented in `firmware/hardware_wiring.md`.
* **Activation Procedure:**
  1. Assemble hardware breadboard according to `firmware/hardware_wiring.md`.
  2. Flash firmware to ESP32 DevKit V1 and configure Wi-Fi and server IP.
  3. Change `ENABLE_PHYSICAL_HARDWARE_INGESTION = True` in `app/config.py`.
  4. Perform bench tests with actual fruit.

---

## 5. Development Roadmap & Status

* **Phase 0 (Complete):** Architecture specification, hardware BOM formulation, prototype rules defined.
* **Phase 1 (Complete):** Core software skeleton, SQLite schema, simulator, deterministic risk scoring, Sell-First ranking, basic UI dashboard.
* **Phase 2 (Complete):** Computer vision dataset audit (CC BY 4.0), Color & Texture Random Forest baseline model trained and integrated with explicit provenance tags.
* **Phase 3 (Simulation Completed, Hardware Prepared):**
  - Full gas-sensor monitoring module and baseline tracking ($R_0$) implemented using simulated data only.
  - Interactive SVG historical graphs (Gas Ratio vs. Baseline & Climate Trends) integrated into dashboard.
  - Batch selection toolbar and RFC 4180 CSV export implemented.
  - ESP32 firmware and hardware wiring specifications prepared for future bench-testing.
  - Physical ingestion endpoint kept disabled until hardware is connected.
* **Phase 4 (Upcoming):** Multi-signal fusion refinement, edge case stress-testing, and sensitivity analysis.
* **Phase 5 (Upcoming):** Final system freeze, end-to-end rehearsal, and college viva presentation.

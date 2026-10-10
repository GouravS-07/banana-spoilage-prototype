"""
Sensor Simulator for Banana Spoilage & Sell-First Advisor.
Simulates time-series telemetry (Temperature, Humidity, Gas Resistance Ratio)
and transmits directly to the FastAPI /api/telemetry/simulated endpoint.
"""

import sys
import time
import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timezone
import httpx

PRESETS_FILE = Path(__file__).resolve().parent / "presets.json"

def load_presets():
    with open(PRESETS_FILE, "r") as f:
        return json.load(f)["scenarios"]

def generate_reading(scenario: dict) -> dict:
    temp = round(scenario["base_temp_c"] + random.uniform(-scenario["temp_jitter"], scenario["temp_jitter"]), 2)
    rh = round(scenario["base_rh_pct"] + random.uniform(-scenario["rh_jitter"], scenario["rh_jitter"]), 2)
    rh = max(0.0, min(100.0, rh))
    gas = round(scenario["base_gas_ratio"] + random.uniform(-scenario["gas_jitter"], scenario["gas_jitter"]), 3)
    gas = max(0.01, gas)
    weight = round(scenario["base_weight_kg"] + random.uniform(-0.02, 0.02), 2)

    return {
        "batch_id": scenario["batch_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": temp,
        "relative_humidity_pct": rh,
        "gas_resistance_raw": gas,
        "current_weight_kg": weight,
        "sensor_device_id": f"SIMULATOR_{scenario['batch_id']}",
    }

def send_readings(base_url: str, scenarios: list):
    endpoint = f"{base_url.rstrip('/')}/api/telemetry/simulated"
    with httpx.Client(timeout=10.0) as client:
        for sc in scenarios:
            payload = generate_reading(sc)
            try:
                resp = client.post(endpoint, json=payload)
                if resp.status_code == 201:
                    data = resp.json()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Transmitted simulated reading for {sc['batch_id']}: "
                          f"T={payload['temperature_c']}°C, RH={payload['relative_humidity_pct']}%, Gas={payload['gas_resistance_raw']} -> Stored ID {data['id']} (Provenance: {data['provenance']})")
                else:
                    print(f"[ERROR] Failed to send {sc['batch_id']}: HTTP {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"[ERROR] Could not connect to {endpoint}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Banana Telemetry Sensor Simulator")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="FastAPI Base URL")
    parser.add_argument("--once", action="store_true", help="Send a single batch of readings and exit")
    parser.add_argument("--interval", type=int, default=15, help="Seconds between telemetry pulses")
    args = parser.parse_args()

    scenarios = load_presets()
    print(f"Loaded {len(scenarios)} simulation scenarios from {PRESETS_FILE.name}.")
    print(f"Targeting: {args.url}/api/telemetry/simulated")

    if args.once:
        send_readings(args.url, scenarios)
        return

    print(f"Starting continuous telemetry pulse every {args.interval} seconds (Press Ctrl+C to stop)...")
    try:
        while True:
            send_readings(args.url, scenarios)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped by user.")

if __name__ == "__main__":
    main()

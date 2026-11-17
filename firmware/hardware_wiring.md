# ESP32 + DHT22 + MQ-135 Hardware Wiring & Integration Specification

> **HARDWARE STATUS NOTICE:**  
> This document specifies the future hardware setup. Currently, **no physical microcontrollers or sensors are connected**, and no physical wiring has been conducted. All current project telemetry runs strictly via the software simulation harness. Do not claim physical hardware integration has been tested until physical components arrive and complete the bench-testing steps below.

---

## 1. Itemized Component List

| Component | Quantity | Purpose | Operating Voltage |
|---|---|---|---|
| **ESP32 DevKit V1** (30-pin, CP2102) | 1 | Microcontroller with Wi-Fi, HTTP client, and 12-bit ADC | 5V via USB (Internal 3.3V logic) |
| **DHT22 / AM2302** | 1 | Digital Temperature ($ \pm 0.5^\circ\text{C} $) and Relative Humidity ($ \pm 2\text{--}5\% $) sensor | 3.3V DC |
| **MQ-135 Gas Sensor Module** | 1 | Metal-oxide ($\text{SnO}_2$) broad VOC / fermentation resistance sensor | **5.0V DC** (Internal heater draws $\approx 160\text{ mA}$) |
| **Resistor: $10\text{ k}\Omega$ 1/4W** | 2 | 1x DHT22 data pull-up; 1x top resistor ($R_1$) of voltage divider | - |
| **Resistor: $20\text{ k}\Omega$ 1/4W** | 1 | Bottom resistor ($R_2$) of voltage divider | - |
| **Breadboard & Jumper Wires** | 1 kit | Solderless prototyping connections | - |
| **External 5V 2A USB Adapter** | 1 | Dedicated clean power source for ESP32 VIN and MQ-135 heater | 5.0V DC |

---

## 2. Electrical Constraints & Safe Voltage Interfacing

### 2.1 Critical ESP32 3.3V Limit
* **ESP32 GPIO and ADC pins are strictly 3.3V maximum.** Exposing any ESP32 pin to 5V will burn the internal silicon or destroy the ADC channel.

### 2.2 MQ-135 Power & Voltage Divider
* **Heater Power:** The MQ-135 heater coil consumes $5.0\text{V} \pm 0.1\text{V}$ and draws $150\text{--}180\text{ mA}$ ($0.8\text{ W}$). The ESP32's onboard 3.3V LDO regulator cannot supply this current. The MQ-135 `VCC` pin **must be wired directly to the 5V `VIN` rail** powered by an external 5V 2A micro-USB adapter.
* **Resistive Voltage Divider on Analog Output ($A_{\text{OUT}}$):**
  When high concentrations of volatiles occur, the MQ-135 analog output swings up to ~4.5–5.0V. A voltage divider steps this down to $< 3.2\text{V}$:
  $$V_{\text{ADC}} = V_{\text{AOUT}} \times \frac{R_2}{R_1 + R_2} = 5.0\text{V} \times \frac{20\text{ k}\Omega}{10\text{ k}\Omega + 20\text{ k}\Omega} = 5.0\text{V} \times 0.667 = 3.33\text{V max}$$
* **ADC Channel Choice:**
  Connect the divider output to **`GPIO34` (ADC1 Channel 6)**.  
  *Never use ADC2 pins (`GPIO 0, 2, 4, 12, 13, 14, 15, 25, 26, 27`)* because ADC2 is shared with the ESP32 Wi-Fi module and cannot be read while Wi-Fi is active.

```
       MQ-135 Module                     ESP32 DevKit V1
   +-------------------+              +-------------------+
   | VCC               |<-------------| VIN (5V from USB) |
   | GND               |------+------>| GND               |
   |                   |      |       +-------------------+
   | AOUT (0 - 5.0V)   |      |
   +---------+---------+      |
             |                |
             | [10 kOhm, R1]  |
             +--------+       |
                      |       |
                      +-------+-----> GPIO34 (ADC1 input, 0-3.3V)
                      |       |
             +--------+       |
             | [20 kOhm, R2]  |
             |                |
             +----------------+ (Common Ground)
```

### 2.3 DHT22 Interfacing
* Connect DHT22 `Pin 1 (VCC)` to ESP32 **`3.3V`**.
* Connect DHT22 `Pin 4 (GND)` to ESP32 **`GND`**.
* Connect DHT22 `Pin 2 (DATA)` to ESP32 **`GPIO4`**.
* Place a $10\text{ k}\Omega$ pull-up resistor between DHT22 `Pin 2 (DATA)` and `3.3V`.

---

## 3. MQ-135 Calibration & Warm-Up Protocols

1. **New Sensor Burn-In Period (24–48 Hours):**  
   Fresh metal-oxide sensors have surface chemical moisture and organic film deposits. Before conducting real banana measurements, power the MQ-135 heater continuously for 24–48 hours in clean ambient air.
2. **Every-Power-Cycle Warm-Up (3–5 Minutes):**  
   Whenever the rig is powered on, the internal heater coil requires ~3 minutes to reach thermal equilibrium ($\sim 300^\circ\text{C}$). The firmware automatically tracks `bootTime` and flags readings during the first 180 seconds as warming up.
3. **Clean-Air Baseline ($R_0$):**  
   Measure sensor resistance $R_s$ in clean air at $20^\circ\text{C}, 65\%$ RH. Record $R_0 = R_s / 3.6$. This value is entered into the firmware constant `MQ_R0_CLEAN_AIR`.
4. **Metric Integrity:**  
   The system outputs the normalized ratio $R_s / R_0$. This is treated strictly as a **relative Volatile Organic Compounds (VOC) indicator**, never as certified ethylene parts-per-million (ppm).

---

## 4. Step-by-Step Instructions for Future Physical Integration

When the physical hardware is received:

1. **Bench Assembly:**  
   Assemble the circuit on a solderless breadboard according to the diagram above. Double-check that $5\text{V}$ never connects directly to GPIO pins.
2. **Firmware Installation:**  
   Open `firmware/esp32_dht22_mq135/esp32_dht22_mq135.ino` in Arduino IDE. Install libraries:
   - `DHT sensor library` by Adafruit
   - `ArduinoJson` by Benoit Blanchon (v6+)
3. **Network Configuration:**  
   In the `.ino` file, configure `WIFI_SSID`, `WIFI_PASSWORD`, and the IP address of the laptop running the FastAPI backend (`SERVER_ENDPOINT`).
4. **Flash & Serial Check:**  
   Connect ESP32 via micro-USB, select board "ESP32 Dev Module", and flash the code. Open Serial Monitor at `115200 baud` to verify DHT22 and ADC readings.
5. **Enable Server Physical Ingestion:**  
   In `app/config.py`, change:
   ```python
   ENABLE_PHYSICAL_HARDWARE_INGESTION: bool = True
   ```
6. **Verify Server Telemetry:**  
   Observe FastAPI terminal logs for incoming `POST /api/telemetry/physical` requests with HTTP 201 responses and verify that readings are tagged as `provenance="PHYSICAL_HARDWARE"`.

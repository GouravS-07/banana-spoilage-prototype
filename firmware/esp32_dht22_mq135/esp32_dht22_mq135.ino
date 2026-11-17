/*******************************************************************************
 * POST-HARVEST BANANA SPOILAGE ADVISOR - ESP32 TELEMETRY FIRMWARE TEMPLATE
 * Target Microcontroller: ESP32 DevKit V1 (30-pin / 38-pin, ESP-WROOM-32)
 * Sensors: DHT22 (AM2302) Temperature/Humidity + MQ-135 Gas Sensor (Air Quality/VOC)
 *
 * IMPORTANT SCIENTIFIC & HARDWARE INTEGRITY DISCLAIMER:
 * ----------------------------------------------------
 * 1. This firmware is PREPARED AS A REFERENCE STRUCTURE FOR FUTURE HARDWARE USE.
 * 2. Physical hardware is NOT currently connected to the development environment.
 *    This code has NOT been flashed or bench-tested on physical hardware yet.
 * 3. Never represent this template as "hardware-tested" until physical sensors
 *    are wired, calibrated, and validated with actual fruit.
 * 4. The server-side physical ingestion endpoint (/api/telemetry/physical) remains
 *    DISABLED by default until physical bench tests are completed.
 *******************************************************************************/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>  // Install via Arduino Library Manager: ArduinoJson by Benoit Blanchon (v6+)
#include <DHT.h>          // Install via Arduino Library Manager: DHT sensor library by Adafruit

// =============================================================================
// CONFIGURATION: WIFI & SERVER CREDENTIALS (TO BE CONFIGURED DURING BENCH TEST)
// =============================================================================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Server endpoint on local laptop running FastAPI backend
const char* SERVER_ENDPOINT = "http://192.168.1.100:8000/api/telemetry/physical";

// Hardware authentication token matching RegisteredDevice in database
const char* DEVICE_TOKEN = "dev-esp32-secret-token-123";
const char* DEVICE_ID    = "ESP32-DEV-RIG1";
const char* BATCH_ID     = "BATCH-001-COLD";  // Target batch under active monitoring

// Telemetry transmission interval (e.g., every 30 seconds)
const unsigned long TRANSMISSION_INTERVAL_MS = 30000;
unsigned long lastTransmissionTime = 0;

// =============================================================================
// PIN DEFINITIONS & ELECTRICAL SPECIFICATIONS
// =============================================================================
// DHT22 Digital Data Pin (requires 10k pull-up to 3.3V)
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// MQ-135 Analog Out connected via voltage divider to ESP32 ADC1
// NOTE: Use ADC1 channel (GPIO 32-39). Do NOT use ADC2 (GPIO 0, 2, 4, 12-15, 25-27)
// because ADC2 is shared with Wi-Fi and cannot be read when Wi-Fi is transmitting!
#define MQ135_PIN 34

// Resistive voltage divider scaling factors (10k resistor and 20k resistor)
// MQ-135 analog output (0 - 5.0V) -> Divider -> ESP32 GPIO34 (0 - 3.3V max)
const float VOLTAGE_DIVIDER_RATIO = (10000.0 + 20000.0) / 20000.0; // 1.5x scaling
const float ESP32_VREF            = 3.30;   // Measured 3.3V rail voltage
const float MQ_RL_KOHMS           = 10.0;   // Onboard load resistor on MQ-135 board (typical: 10k or 20k)
const float MQ_R0_CLEAN_AIR       = 76.63;  // Clean-air baseline resistance R0 (determined during 48h calibration)

// MQ-135 heater warm-up tracking (requires 3 minutes after boot before stable readings)
const unsigned long WARMUP_DURATION_MS = 180000; // 3 minutes
unsigned long bootTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  bootTime = millis();

  Serial.println("\n========================================================");
  Serial.println("🍌 Banana Spoilage Prototype - ESP32 Telemetry Client");
  Serial.println("STATUS: Reference template for future physical deployment");
  Serial.println("========================================================");

  // Initialize DHT22
  dht.begin();
  Serial.println("[SETUP] DHT22 sensor initialized on GPIO4.");

  // Configure ADC for MQ-135
  analogReadResolution(12); // 12-bit ADC: 0 - 4095
  analogSetPinAttenuation(MQ135_PIN, ADC_11db); // Full range: ~0 - 3.3V
  Serial.println("[SETUP] ADC configured on GPIO34 (12-bit, 11dB attenuation).");

  // Connect to Wi-Fi
  connectWiFi();
}

void loop() {
  // Maintain Wi-Fi connection
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  unsigned long currentMillis = millis();
  if (currentMillis - lastTransmissionTime >= TRANSMISSION_INTERVAL_MS) {
    lastTransmissionTime = currentMillis;
    transmitTelemetry();
  }
}

void connectWiFi() {
  Serial.print("[WIFI] Connecting to: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected! Local IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WIFI] Connection failed. Will retry on next cycle.");
  }
}

void transmitTelemetry() {
  // 1. Read DHT22
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature(); // Celsius

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("[ERROR] Failed to read from DHT22 sensor!");
    return;
  }

  // 2. Read MQ-135 and compute relative resistance ratio (Rs / R0)
  int rawADC = analogRead(MQ135_PIN);
  float vOutADC = (rawADC / 4095.0) * ESP32_VREF;
  float vSensorOut = vOutADC * VOLTAGE_DIVIDER_RATIO;
  
  // Guard against near-zero voltages
  vSensorOut = constrain(vSensorOut, 0.05, 4.95);
  
  // Calculate sensor surface resistance Rs = RL * (Vcc - Vout) / Vout
  float rsKohms = MQ_RL_KOHMS * (5.0 - vSensorOut) / vSensorOut;
  // Calculate normalized resistance ratio Rs / R0 (relative VOC trend indicator)
  float gasRatio = rsKohms / MQ_R0_CLEAN_AIR;
  gasRatio = constrain(gasRatio, 0.01, 2.0);

  // Check warm-up state
  bool isWarmedUp = (millis() - bootTime) >= WARMUP_DURATION_MS;
  if (!isWarmedUp) {
    Serial.println("[NOTICE] MQ-135 heater in 3-minute stabilization warm-up window.");
  }

  Serial.printf("[TELEMETRY] Temp: %.2f °C | Humidity: %.2f %% | Gas Ratio (Rs/R0): %.3f\n",
                temperature, humidity, gasRatio);

  // 3. Assemble JSON Payload
  StaticJsonDocument<256> doc;
  doc["batch_id"] = BATCH_ID;
  doc["temperature_c"] = round(temperature * 100.0) / 100.0;
  doc["relative_humidity_pct"] = round(humidity * 100.0) / 100.0;
  doc["gas_resistance_raw"] = round(gasRatio * 1000.0) / 1000.0;
  doc["sensor_device_id"] = DEVICE_ID;

  String jsonString;
  serializeJson(doc, jsonString);

  // 4. Send HTTP POST to FastAPI backend
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", DEVICE_TOKEN);

    int httpResponseCode = http.POST(jsonString);
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.printf("[HTTP] POST Result: %d -> %s\n", httpResponseCode, response.c_str());
    } else {
      Serial.printf("[HTTP] POST Failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  }
}

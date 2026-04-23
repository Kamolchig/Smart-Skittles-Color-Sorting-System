/*
 * Smart Skittles Color Sorting System — Arduino Firmware
 * =========================================================
 * Reads color from a TCS34725 sensor and sends JSON over serial.
 *
 * Hardware:
 *   - Arduino Uno / Mega / Nano
 *   - Adafruit TCS34725 color sensor (I2C: SDA→A4, SCL→A5)
 *   - Servo motor on pin 9 (sorting gate)
 *
 * Library dependencies (install via Library Manager):
 *   - Adafruit_TCS34725
 *   - ArduinoJson  (v6+)
 *   - Servo
 *
 * Serial output format (JSON, one line per detection):
 *   {"color":"red","confidence":0.94,"sensor_id":"TCS34725","timestamp":"0"}
 *
 * CSV format is also supported (uncomment CSV block below):
 *   red,0.94,TCS34725
 */

#include <Wire.h>
#include <Adafruit_TCS34725.h>
#include <ArduinoJson.h>
#include <Servo.h>

// ── Configuration ────────────────────────────────────────────────────────────
#define BAUD_RATE      9600
#define SAMPLE_DELAY   500    // ms between readings
#define SERVO_PIN      9

// Servo positions for each colour lane (adjust to your machine)
#define POS_RED        30
#define POS_ORANGE     60
#define POS_YELLOW     90
#define POS_GREEN     120
#define POS_BLUE      150
#define POS_PURPLE    170
#define POS_UNKNOWN    90   // centre / reject

// ── Globals ───────────────────────────────────────────────────────────────────
Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_50MS,
                                           TCS34725_GAIN_4X);
Servo gateServo;

unsigned long sampleCount = 0;

// ── Colour classification ─────────────────────────────────────────────────────
struct ColorResult {
  const char* name;
  float       confidence;
};

ColorResult classifyColor(float r, float g, float b) {
  // Normalise
  float total = r + g + b;
  if (total < 10) return {"unknown", 0.30};
  float rn = r / total;
  float gn = g / total;
  float bn = b / total;

  // Simple heuristic thresholds — tune for your specific candies
  if      (rn > 0.55 && gn < 0.28)             return {"red",    0.85 + rn * 0.12};
  else if (rn > 0.48 && gn > 0.28 && bn < 0.20) return {"orange", 0.80 + rn * 0.10};
  else if (rn > 0.38 && gn > 0.38 && bn < 0.22) return {"yellow", 0.82 + gn * 0.10};
  else if (gn > 0.45 && rn < 0.32)              return {"green",  0.83 + gn * 0.10};
  else if (bn > 0.42 && rn < 0.32)              return {"blue",   0.84 + bn * 0.10};
  else if (rn > 0.30 && bn > 0.38 && gn < 0.28) return {"purple", 0.80 + bn * 0.10};
  else                                           return {"unknown", 0.40};
}

// ── Servo gate ────────────────────────────────────────────────────────────────
void sortCandy(const char* color) {
  int pos = POS_UNKNOWN;
  if      (strcmp(color, "red")    == 0) pos = POS_RED;
  else if (strcmp(color, "orange") == 0) pos = POS_ORANGE;
  else if (strcmp(color, "yellow") == 0) pos = POS_YELLOW;
  else if (strcmp(color, "green")  == 0) pos = POS_GREEN;
  else if (strcmp(color, "blue")   == 0) pos = POS_BLUE;
  else if (strcmp(color, "purple") == 0) pos = POS_PURPLE;

  gateServo.write(pos);
  delay(600);                // allow candy to fall through
  gateServo.write(90);       // return to centre
}

// ── JSON output ───────────────────────────────────────────────────────────────
void sendJSON(const char* color, float confidence, unsigned long ts) {
  StaticJsonDocument<128> doc;
  doc["color"]      = color;
  doc["confidence"] = round(confidence * 100) / 100.0;
  doc["sensor_id"]  = "TCS34725";
  doc["timestamp"]  = ts;    // millis() as surrogate; use RTC for real timestamps
  serializeJson(doc, Serial);
  Serial.println();
}

/* -- CSV alternative (uncomment to use instead of JSON) ----------------
void sendCSV(const char* color, float confidence) {
  Serial.print(color);
  Serial.print(",");
  Serial.print(confidence, 2);
  Serial.print(",TCS34725");
  Serial.println();
}
-----------------------------------------------------------------------*/

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial);

  gateServo.attach(SERVO_PIN);
  gateServo.write(90);

  if (!tcs.begin()) {
    Serial.println("{\"error\":\"TCS34725 not found — check wiring\"}");
    while (1) delay(1000);
  }

  Serial.println("{\"event\":\"boot\",\"sensor_id\":\"TCS34725\",\"status\":\"ready\"}");
}

// ── Main loop ─────────────────────────────────────────────────────────────────
void loop() {
  uint16_t r_raw, g_raw, b_raw, c_raw;
  tcs.getRawData(&r_raw, &g_raw, &b_raw, &c_raw);

  // Lux / colour temp (informational)
  float lux   = tcs.calculateLux(r_raw, g_raw, b_raw);

  // Cast to float for classification
  float r = (float)r_raw;
  float g = (float)g_raw;
  float b = (float)b_raw;

  ColorResult result = classifyColor(r, g, b);

  // Clamp confidence
  float conf = result.confidence;
  if (conf > 0.99) conf = 0.99;
  if (conf < 0.10) conf = 0.10;

  // Send detection
  sendJSON(result.name, conf, millis());

  // Physically sort the candy
  sortCandy(result.name);

  sampleCount++;
  delay(SAMPLE_DELAY);
}

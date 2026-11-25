// GemXpert wearable - ESP32 + MPU6050 -> Bluetooth Low Energy (single file, no extra libraries)
//
// Wiring:  MPU6050 VCC -> 3V3, GND -> GND, SCL -> GPIO 22, SDA -> GPIO 21
// Board:   Tools > Board > "ESP32 Dev Module"
//
// 1. Upload. Open the Serial Monitor (115200) and keep the sensor still for 2 seconds while it calibrates.
// 2. Open the GemXpert site in Chrome or Edge -> Wearable Device -> Connect wearable -> pick "GemXpert-Ring" -> Pair.
// 3. Rotate the sensor: the ring (and the hand) rotate with it. Tap it: next gemstone. Double tap: next metal.
//
// BLE protocol (the site's src/wearable/ble.ts reads the same):
//   service  9a1f0001-6c3b-4e8a-b1d2-47e5c0a1f001
//   IMU      9a1f0002-...  notify 50x/s, 20 bytes = 10 x int16 little-endian:
//            qw qx qy qz (x32767) | gx gy gz (deg/s x10) | ax ay az (g x1000), quaternion relative to the "straight" pose
//   Gesture  9a1f0003-...  notify, 1 byte: 1 = tap, 2 = double tap
//   Command  9a1f0004-...  write,  1 byte: 1 = recentre (current pose becomes straight)

#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>

#define DEVICE_NAME   "GemXpert-Ring"
#define SERVICE_UUID  "9a1f0001-6c3b-4e8a-b1d2-47e5c0a1f001"
#define IMU_UUID      "9a1f0002-6c3b-4e8a-b1d2-47e5c0a1f001"
#define GESTURE_UUID  "9a1f0003-6c3b-4e8a-b1d2-47e5c0a1f001"
#define CMD_UUID      "9a1f0004-6c3b-4e8a-b1d2-47e5c0a1f001"

const int PIN_SDA = 21;
const int PIN_SCL = 22;
const int PIN_LED = 2;            // on-board LED: blinking = waiting for the site, solid = connected
const float TAP_G = 2.0f;         // how hard a tap must be (g above gravity); raise if taps trigger by themselves

uint8_t mpuAddr = 0x68;
float ax, ay, az, gx, gy, gz;     // accel in g, gyro in deg/s
float bias[3] = {0, 0, 0};
float q0 = 1, q1 = 0, q2 = 0, q3 = 0;   // current orientation
float r0 = 1, r1 = 0, r2 = 0, r3 = 0;   // "straight" pose (set when the site connects or presses Recentre)
float oq[4] = {1, 0, 0, 0};             // orientation relative to the straight pose
float yaw, pitch, roll;

BLEServer* server = nullptr;
BLECharacteristic* imuChar = nullptr;
BLECharacteristic* gestureChar = nullptr;
volatile bool bleConnected = false, restartAdvertising = false, recentreNow = false;

uint32_t lastSampleUs = 0, lastSendMs = 0, lastPrintMs = 0, lastTapMs = 0, pendingTapMs = 0;
bool tapPending = false;

// ---------------- MPU6050 ----------------
void writeReg(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(mpuAddr); Wire.write(reg); Wire.write(val); Wire.endTransmission();
}

bool readMpu() {
  Wire.beginTransmission(mpuAddr);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(mpuAddr, (uint8_t)14) != 14) return false;
  int16_t v[7];
  for (int i = 0; i < 7; i++) { uint8_t hi = Wire.read(), lo = Wire.read(); v[i] = (int16_t)((hi << 8) | lo); }
  ax = v[0] / 4096.0f; ay = v[1] / 4096.0f; az = v[2] / 4096.0f;                               // +-8 g
  gx = v[4] / 32.8f - bias[0]; gy = v[5] / 32.8f - bias[1]; gz = v[6] / 32.8f - bias[2];         // +-1000 deg/s
  return true;
}

bool found(uint8_t addr) { Wire.beginTransmission(addr); return Wire.endTransmission() == 0; }

void startMpu() {
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);
  while (true) {
    if (found(0x68)) { mpuAddr = 0x68; break; }
    if (found(0x69)) { mpuAddr = 0x69; break; }
    Serial.println("MPU6050 NOT FOUND - check wires: VCC->3V3, GND->GND, SCL->22, SDA->21");
    delay(1000);
  }
  writeReg(0x6B, 0x80); delay(100);   // reset
  writeReg(0x6B, 0x01); delay(50);    // wake up
  writeReg(0x1A, 0x03);               // low-pass filter ~44 Hz
  writeReg(0x1B, 0x10);               // gyro +-1000 deg/s
  writeReg(0x1C, 0x10);               // accel +-8 g
  delay(50);
  Serial.println("MPU6050 found");

  Serial.println("Calibrating gyro - keep the sensor still...");
  float s[3] = {0, 0, 0};
  for (int i = 0; i < 400; i++) {
    readMpu();
    s[0] += gx; s[1] += gy; s[2] += gz;
    digitalWrite(PIN_LED, (i / 20) % 2);
    delay(5);
  }
  for (int k = 0; k < 3; k++) bias[k] = s[k] / 400;
  readMpu();

  // start from the accelerometer's tilt so the orientation is right immediately
  float rl = atan2f(ay, az), pt = atan2f(-ax, sqrtf(ay * ay + az * az));
  float cr = cosf(rl / 2), sr = sinf(rl / 2), cp = cosf(pt / 2), sp = sinf(pt / 2);
  q0 = cr * cp; q1 = sr * cp; q2 = cr * sp; q3 = -sr * sp;
  r0 = q0; r1 = q1; r2 = q2; r3 = q3;
  Serial.println("Gyro calibrated");
}

// ---------------- orientation (Mahony filter: gyro + gravity) ----------------
void updateOrientation(float dt) {
  float g1 = gx * 0.0174533f, g2 = gy * 0.0174533f, g3 = gz * 0.0174533f;
  float n = sqrtf(ax * ax + ay * ay + az * az);
  if (n > 0.85f && n < 1.15f) {                 // use gravity only when not shaking / tapping
    float a1 = ax / n, a2 = ay / n, a3 = az / n;
    float vx = 2 * (q1 * q3 - q0 * q2), vy = 2 * (q0 * q1 + q2 * q3), vz = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3;
    g1 += a2 * vz - a3 * vy; g2 += a3 * vx - a1 * vz; g3 += a1 * vy - a2 * vx;
  }
  g1 *= 0.5f * dt; g2 *= 0.5f * dt; g3 *= 0.5f * dt;
  float a = q0, b = q1, c = q2;
  q0 += -b * g1 - c * g2 - q3 * g3;
  q1 +=  a * g1 + c * g3 - q3 * g2;
  q2 +=  a * g2 - b * g3 + q3 * g1;
  q3 +=  a * g3 + b * g2 - c * g1;
  n = sqrtf(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
  q0 /= n; q1 /= n; q2 /= n; q3 /= n;

  // relative to the straight pose: conj(r) * q
  oq[0] =  r0 * q0 + r1 * q1 + r2 * q2 + r3 * q3;
  oq[1] =  r0 * q1 - r1 * q0 - r2 * q3 + r3 * q2;
  oq[2] =  r0 * q2 + r1 * q3 - r2 * q0 - r3 * q1;
  oq[3] =  r0 * q3 - r1 * q2 + r2 * q1 - r3 * q0;
  float w = oq[0], x = oq[1], y = oq[2], z = oq[3];
  roll  = atan2f(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)) * 57.2958f;
  pitch = asinf(constrain(2 * (w * y - z * x), -1.0f, 1.0f)) * 57.2958f;
  yaw   = atan2f(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)) * 57.2958f;
}

// ---------------- taps ----------------
void sendGesture(uint8_t code, const char* name) {
  Serial.printf("Gesture: %s\n", name);
  if (!bleConnected) return;
  gestureChar->setValue(&code, 1);
  gestureChar->notify();
}

void detectTaps(uint32_t now) {
  float spike = fabsf(sqrtf(ax * ax + ay * ay + az * az) - 1.0f);
  if (spike > TAP_G && now - lastTapMs > 120) {
    lastTapMs = now;
    if (tapPending && now - pendingTapMs < 350) { tapPending = false; sendGesture(2, "double tap"); }
    else { tapPending = true; pendingTapMs = now; }
  }
  if (tapPending && now - pendingTapMs >= 350) { tapPending = false; sendGesture(1, "tap"); }
}

// ---------------- BLE ----------------
class ServerEvents : public BLEServerCallbacks {
  void onConnect(BLEServer*) override { bleConnected = true; recentreNow = true; Serial.println("Site connected"); }
  void onDisconnect(BLEServer*) override { bleConnected = false; restartAdvertising = true; Serial.println("Site disconnected"); }
};

class CommandEvents : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* c) override {
    auto v = c->getValue();
    if (v.length() > 0 && (uint8_t)v[0] == 1) recentreNow = true;
  }
};

int16_t pack(float v, float scale) { return (int16_t)constrain(lroundf(v * scale), -32767L, 32767L); }

void sendImu() {
  int16_t p[10] = {
    pack(oq[0], 32767), pack(oq[1], 32767), pack(oq[2], 32767), pack(oq[3], 32767),
    pack(gx, 10), pack(gy, 10), pack(gz, 10),
    pack(ax, 1000), pack(ay, 1000), pack(az, 1000),
  };
  imuChar->setValue((uint8_t*)p, sizeof p);   // ESP32 is little-endian, as the site expects
  imuChar->notify();
}

void startBle() {
  BLEDevice::init(DEVICE_NAME);
  server = BLEDevice::createServer();
  server->setCallbacks(new ServerEvents());
  BLEService* svc = server->createService(SERVICE_UUID);

  imuChar = svc->createCharacteristic(IMU_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  imuChar->addDescriptor(new BLE2902());
  gestureChar = svc->createCharacteristic(GESTURE_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  gestureChar->addDescriptor(new BLE2902());
  BLECharacteristic* cmd = svc->createCharacteristic(CMD_UUID, BLECharacteristic::PROPERTY_WRITE);
  cmd->setCallbacks(new CommandEvents());
  svc->start();

  BLEAdvertising* adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();
  Serial.println("Bluetooth ready: in the GemXpert site press Connect wearable and pick \"" DEVICE_NAME "\"");
}

// ---------------- setup / loop ----------------
void setup() {
  Serial.begin(115200);
  delay(300);
  pinMode(PIN_LED, OUTPUT);
  Serial.println("\n=== GemXpert wearable (Bluetooth) ===");
  startMpu();
  startBle();
  lastSampleUs = micros();
}

void loop() {
  uint32_t nowUs = micros(), now = millis();

  if (nowUs - lastSampleUs >= 5000) {          // 200 Hz
    float dt = (nowUs - lastSampleUs) / 1e6f;
    lastSampleUs = nowUs;
    if (dt > 0.05f) dt = 0.05f;
    if (readMpu()) { updateOrientation(dt); detectTaps(now); }
  }

  if (recentreNow) { recentreNow = false; r0 = q0; r1 = q1; r2 = q2; r3 = q3; }

  if (bleConnected && now - lastSendMs >= 20) {   // 50 packets per second
    lastSendMs = now;
    sendImu();
  }

  if (restartAdvertising) {                       // let the site reconnect after a drop
    restartAdvertising = false;
    delay(200);
    BLEDevice::startAdvertising();
  }

  digitalWrite(PIN_LED, bleConnected ? HIGH : (now / 500) % 2);

  if (now - lastPrintMs >= 3000) {
    lastPrintMs = now;
    Serial.printf("Bluetooth %s | yaw %.0f  pitch %.0f  roll %.0f\n",
                  bleConnected ? "connected" : "waiting for the site", yaw, pitch, roll);
  }
}

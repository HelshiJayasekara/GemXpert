# GemXpert wearable firmware (ESP32 + MPU6050)

One-file Arduino sketch: `GemXpertWearable/GemXpertWearable.ino`. Wire VCC→3V3, GND→GND, SCL→GPIO 22, SDA→GPIO 21, upload
with board **ESP32 Dev Module**, then press **Connect wearable** on the site's Wearable Device screen (Chrome or Edge).
It talks Bluetooth Low Energy; no WiFi and no extra libraries.

Full steps: [Documentation/Hardware/ESP32_WEARABLE_SETUP.md](../../Documentation/Hardware/ESP32_WEARABLE_SETUP.md)

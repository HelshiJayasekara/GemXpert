# ESP32 + MPU6050 wearable over Bluetooth

Rotate the sensor and the ring (and the hand it's on) rotates with it in the GemXpert site. Tap the sensor for the next
gemstone, double tap for the next metal. Firmware: [`Firmware/ESP32/GemXpertWearable/GemXpertWearable.ino`](../../Firmware/ESP32/GemXpertWearable/GemXpertWearable.ino)
(one file, no extra libraries, no WiFi).

## 1. Wiring

| MPU6050 | ESP32 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SCL | GPIO 22 |
| SDA | GPIO 21 |

Leave XDA, XCL, AD0 and INT unconnected. Solder the MPU6050's header pins: pins just pushed through the holes make a loose contact.

## 2. Flash

1. Arduino IDE → open `GemXpertWearable.ino`.
2. Tools ▸ Board ▸ **ESP32 Dev Module**, pick the COM port, **Upload**. If it hangs at `Connecting...`, hold **BOOT** on the ESP32.
3. Serial Monitor at **115200**, press **EN/RST**, keep the sensor **still for 2 s**. It prints `Bluetooth ready`.

No library to install: Bluetooth support is built into the ESP32 board package.

## 3. Connect from the site

1. Open the site (local: `npm run dev` in `Web/` → http://localhost:5173, or the deployed site) in **Chrome or Edge**.
2. **Wearable Device** → **Connect wearable** → pick **GemXpert-Ring** in the browser's list → **Pair**.
3. The header shows *Wearable: connected* and the ESP32's blue LED stays on. Press **On hand** under the stage, then rotate the sensor.

The pose at the moment you connect counts as "straight"; **Recentre** resets it any time.

### Browser support (Web Bluetooth)

| Works | Doesn't work |
|---|---|
| Chrome and Edge on Windows 10/11, macOS, Android, ChromeOS | Firefox, Safari, any browser on iPhone/iPad (use the Bluefy app there) |

Web Bluetooth only runs on `https://` sites or `localhost`, so it works on the Vercel deployment and in `npm run dev`, but not
from a plain `http://192.168.x.x` address.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `MPU6050 NOT FOUND` repeating | Check the 4 wires and the solder; try VCC on VIN (5V) instead of 3V3 |
| GemXpert-Ring isn't in the browser's list | ESP32 not running the new firmware, or already connected to another tab/device. Reset the ESP32 |
| "Bluetooth is switched off" on the site | Turn Bluetooth on in Windows settings, reload the page |
| Ring slowly turns by itself | Gyro drift (the MPU6050 has no compass). Press Recentre, or reset the ESP32 while it lies still |
| Taps trigger by themselves / not at all | Change `TAP_G` at the top of the sketch (default 2.0 g) |
| Disconnects when you walk away | Bluetooth range is about 5-10 m; the site reconnects by itself when you come back |

## Bluetooth protocol

Service `9a1f0001-6c3b-4e8a-b1d2-47e5c0a1f001`. Characteristics share the same UUID with `0002`, `0003`, `0004` in the first group:

| Characteristic | Type | Data |
|---|---|---|
| IMU `9a1f0002-…` | notify, 50/s | 20 bytes, 10 × int16 little-endian: `qw qx qy qz` (×32767), `gx gy gz` (°/s ×10), `ax ay az` (g ×1000) |
| Gesture `9a1f0003-…` | notify | 1 byte: `1` tap, `2` double tap |
| Command `9a1f0004-…` | write | 1 byte: `1` recentre |

The quaternion is relative to the "straight" pose, in sensor axes (X and Y as printed on the board, Z up out of the chip).
The site converts it to three.js axes in [`Web/src/wearable/live.ts`](../../Web/src/wearable/live.ts). Twenty bytes fit Bluetooth's
default packet size, so no MTU negotiation is needed.

# Hardware Tests Still Outstanding

No VR headset or ESP32 device is available on the development machine. Everything below has
a simulation fallback but **has not been verified on real hardware**. Do not report these as tested.

| ID | Area | Test on real hardware | Fallback used today |
|---|---|---|---|
| HW-1 | Headset (Quest 3/3S) | Build an Android APK with OpenXR + Meta Quest feature group, install over USB, confirm `Run mode: VR headset` and 72/90 Hz | Desktop mode + XR Device Simulator |
| HW-2 | Comfort | Panel distance/height, text legibility, no discomfort when walking or snap-turning | Values chosen from common VR UI guidance (1–2 m, slightly below eye level, ≥ 2.5 cm text) |
| HW-3 | Controllers | Ray select, grip and teleport on Quest Touch controllers | Simulator controllers |
| HW-4 | Hand tracking (Phase 4) | XR Hands joints drive the virtual hand. Ring stays on the ring finger during fast motion | Simulated hand |
| HW-5 | ESP32 BLE on Quest (Phase 5) | Quest app can scan, connect and subscribe to the custom GATT service | Mock transport + macOS UDP bridge |
| HW-6 | IMU (Phase 5) | MPU6050 orientation drift, calibration, gesture thresholds | Mock sensor simulator |
| HW-7 | Performance (Phase 6) | Quest GPU/CPU frame timing in OVR Metrics, with the showroom + jewellery visible | Editor profiler only |

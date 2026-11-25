// GemXpert wearable over Bluetooth Low Energy (Web Bluetooth). Firmware: Firmware/ESP32/GemXpertWearable.
//
// GATT service 9a1f0001-…:
//   IMU      9a1f0002 notify, 20 bytes, 10 x int16 little-endian:
//            qw qx qy qz (x 32767) · gx gy gz (deg/s x 10) · ax ay az (g x 1000); quaternion relative to the recentred pose
//   Gesture  9a1f0003 notify, 1 byte: 1 = tap, 2 = double tap
//   Command  9a1f0004 write,  1 byte: 1 = recentre (current pose becomes straight)
import { useApp } from "../lib/store";
import { eulerFromSensor, live, sensorToThree } from "./live";

export const BLE_SERVICE = "9a1f0001-6c3b-4e8a-b1d2-47e5c0a1f001";
const IMU_CHAR = "9a1f0002-6c3b-4e8a-b1d2-47e5c0a1f001";
const GESTURE_CHAR = "9a1f0003-6c3b-4e8a-b1d2-47e5c0a1f001";
const CMD_CHAR = "9a1f0004-6c3b-4e8a-b1d2-47e5c0a1f001";

let device: BluetoothDevice | null = null;
let cmdChar: BluetoothRemoteGATTCharacteristic | null = null;
let wanted = false;                         // false after the user presses Disconnect

export const bleSupported = () => typeof navigator !== "undefined" && !!navigator.bluetooth;

export async function bleAvailable(): Promise<boolean> {
  if (!bleSupported()) return false;
  try { return await navigator.bluetooth.getAvailability(); } catch { return true; }
}

function onImu(ev: Event) {
  const v = (ev.target as BluetoothRemoteGATTCharacteristic).value;
  if (!v || v.byteLength < 20) return;
  const i = (k: number) => v.getInt16(k * 2, true);
  const w = i(0) / 32767, x = i(1) / 32767, y = i(2) / 32767, z = i(3) / 32767;
  live.q = sensorToThree(w, x, y, z);
  live.e = eulerFromSensor(w, x, y, z);
  live.g = [i(4) / 10, i(5) / 10, i(6) / 10];
  live.a = [i(7) / 1000, i(8) / 1000, i(9) / 1000];
  live.packets++;
}

function onGesture(ev: Event) {
  const v = (ev.target as BluetoothRemoteGATTCharacteristic).value;
  const code = v?.getUint8(0);
  if (code === 1) useApp.getState().gesture("tap");
  else if (code === 2) useApp.getState().gesture("double");
}

async function attach(d: BluetoothDevice) {
  const server = await d.gatt!.connect();
  const svc = await server.getPrimaryService(BLE_SERVICE);
  const imu = await svc.getCharacteristic(IMU_CHAR);
  const gest = await svc.getCharacteristic(GESTURE_CHAR);
  cmdChar = await svc.getCharacteristic(CMD_CHAR);
  imu.addEventListener("characteristicvaluechanged", onImu);
  gest.addEventListener("characteristicvaluechanged", onGesture);
  await imu.startNotifications();
  await gest.startNotifications();
  await recentre();   // the pose at connect time is "straight"
}

async function onDisconnected() {
  const app = useApp.getState();
  live.q = null; cmdChar = null;
  if (!wanted || !device) { app.setWear({ mode: "off", status: "idle", deviceName: null }); return; }
  app.setWear({ status: "reconnecting" });
  app.showToast("Wearable disconnected. Reconnecting...");
  for (let attempt = 0; wanted && device && attempt < 20; attempt++) {
    try {
      await attach(device);
      app.setWear({ status: "live" });
      app.showToast("Wearable reconnected.");
      return;
    } catch {
      await new Promise((r) => setTimeout(r, Math.min(1000 * (attempt + 1), 5000)));
    }
  }
  if (wanted) { app.setWear({ mode: "off", status: "idle", deviceName: null }); app.showToast("Couldn't reconnect. Press Connect to try again."); }
}

/** Must be called from a click (the browser shows its device picker). */
export async function connectBle(): Promise<void> {
  const app = useApp.getState();
  if (!bleSupported()) {
    app.showToast("This browser has no Bluetooth support. Use Chrome or Edge on Windows, Mac, Android or ChromeOS.");
    return;
  }
  let picked: BluetoothDevice;
  try {
    picked = await navigator.bluetooth.requestDevice({
      filters: [{ services: [BLE_SERVICE] }, { namePrefix: "GemXpert" }],
      optionalServices: [BLE_SERVICE],
    });
  } catch (e) {
    if ((e as DOMException)?.name !== "NotFoundError") app.showToast("Bluetooth isn't available. Check that it's switched on.");
    return;   // NotFoundError = the user closed the picker
  }
  if (device && device !== picked) disconnectBle();
  device = picked;
  wanted = true;
  device.addEventListener("gattserverdisconnected", onDisconnected);
  app.setWear({ mode: "ble", status: "connecting", deviceName: device.name || "GemXpert wearable" });
  try {
    await attach(device);
    app.setWear({ status: "live" });
    app.showToast("Wearable connected. Rotate it to turn the ring.");
  } catch (e) {
    console.error(e);
    wanted = false;
    device.removeEventListener("gattserverdisconnected", onDisconnected);
    try { device.gatt?.disconnect(); } catch { /* already gone */ }
    device = null;
    app.setWear({ mode: "off", status: "idle", deviceName: null });
    app.showToast("Couldn't connect. Is the GemXpert firmware running on the ESP32? Try again.");
  }
}

export function disconnectBle() {
  wanted = false;
  live.q = null;
  if (device) {
    device.removeEventListener("gattserverdisconnected", onDisconnected);
    try { device.gatt?.disconnect(); } catch { /* already gone */ }
  }
  device = null; cmdChar = null;
  useApp.getState().setWear({ mode: "off", status: "idle", deviceName: null });
}

export async function recentre() {
  if (!cmdChar) return;
  try { await cmdChar.writeValueWithResponse(new Uint8Array([1])); } catch (e) { console.warn("recentre failed", e); }
}

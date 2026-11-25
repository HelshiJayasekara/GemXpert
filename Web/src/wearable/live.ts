// High-rate wearable data, kept outside React state (50 updates a second). The 3D stage and the readout read it directly.
import * as THREE from "three";

export const live = {
  q: null as THREE.Quaternion | null,   // orientation in three.js axes, relative to the recentred pose
  e: [0, 0, 0] as number[],             // yaw, pitch, roll (degrees)
  g: [0, 0, 0] as number[],             // gyro, deg/s
  a: [0, 0, 1] as number[],             // accelerometer, g
  packets: 0,                           // count, for the packets/s readout
};

// Simulator (no hardware): natural wrist movement or manual sliders.
export const sim = { auto: true, yaw: 0, pitch: 0, roll: 0 };

/** Sensor quaternion (w,x,y,z; X right, Y forward, Z up) -> three.js (X right, Y up, Z towards the viewer). */
export function sensorToThree(w: number, x: number, y: number, z: number) {
  return new THREE.Quaternion(x, z, -y, w).normalize();
}

/** Yaw / pitch / roll (degrees, ZYX) from a sensor-frame quaternion. */
export function eulerFromSensor(w: number, x: number, y: number, z: number): number[] {
  const R = 180 / Math.PI;
  const roll = Math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)) * R;
  const pitch = Math.asin(Math.max(-1, Math.min(1, 2 * (w * y - z * x)))) * R;
  const yaw = Math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)) * R;
  return [yaw, pitch, roll];
}

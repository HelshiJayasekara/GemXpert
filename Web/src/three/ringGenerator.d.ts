import type * as THREE from "three";
import type { RingSpec } from "../lib/catalog";

export declare const GEN: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  build(spec: RingSpec, cuts: Record<string, any>, roundGeo: THREE.BufferGeometry): { root: THREE.Group; info: { accentStones: number; accentSizeMm?: number } };
};

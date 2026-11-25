// JavaScript port of Blender/Scripts/gx_rings.py (+ cut outlines from gx_gems.py). Moved verbatim from the original page.
// @ts-nocheck
import * as THREE from "three";

export const GEN = (() => {
  const TAU = Math.PI * 2;
  const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const unit = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
  const linspace = (a, b, n) => Array.from({ length: n }, (_, i) => (n === 1 ? a : a + ((b - a) * i) / (n - 1)));

  // --- girdle outlines, normalised to width 1 and length = aspect, centred on their bounding box
  class Outline {
    constructor(fn, aspect, samples = 720) {
      this.fn = fn; this.aspect = aspect;
      const lo = [Infinity, Infinity], hi = [-Infinity, -Infinity];
      for (let i = 0; i < samples; i++) {
        const p = fn((TAU * i) / samples);
        lo[0] = Math.min(lo[0], p[0]); lo[1] = Math.min(lo[1], p[1]); hi[0] = Math.max(hi[0], p[0]); hi[1] = Math.max(hi[1], p[1]);
      }
      this.c = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2];
      this.s = [1 / (hi[0] - lo[0]), aspect / (hi[1] - lo[1])];
    }
    point(t) { const p = this.fn(t); return [(p[0] - this.c[0]) * this.s[0], (p[1] - this.c[1]) * this.s[1]]; }
    normal(t, h = 1e-4) {
      const p = this.point(t), a = this.point(t + h), b = this.point(t - h);
      let n = [a[1] - b[1], -(a[0] - b[0])];
      if (Math.hypot(n[0], n[1]) < 1e-12) n = p.slice();
      const l = Math.hypot(n[0], n[1]);
      n = [n[0] / l, n[1] / l];
      return n[0] * p[0] + n[1] * p[1] >= 0 ? n : [-n[0], -n[1]];
    }
  }
  const circle = (t) => [Math.cos(t), Math.sin(t)];
  const superellipse = (e) => (t) => { const c = Math.cos(t), s = Math.sin(t), p = 2 / e; return [Math.sign(c) * Math.abs(c) ** p, Math.sign(s) * Math.abs(s) ** p]; };
  const teardrop = (t) => [Math.sin(t) * Math.abs(Math.sin(t / 2)), -Math.cos(t)];
  const chamfered = (w, l, c) => { const W = w / 2, L = l / 2; return [[W, -L + c], [W, L - c], [W - c, L], [-W + c, L], [-W, L - c], [-W, -L + c], [-W + c, -L], [W - c, -L]]; };
  const polygonFn = (poly) => (t) => {
    const d = [Math.cos(t), Math.sin(t)];
    let best = null;
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i], b = poly[(i + 1) % poly.length], e = [b[0] - a[0], b[1] - a[1]];
      const det = d[0] * -e[1] - -e[0] * d[1];
      if (Math.abs(det) < 1e-12) continue;
      const r = (a[0] * -e[1] - -e[0] * a[1]) / det, u = (d[0] * a[1] - d[1] * a[0]) / det;
      if (r > 0 && u >= -1e-9 && u <= 1 + 1e-9 && (best === null || r < best)) best = r;
    }
    return [d[0] * best, d[1] * best];
  };
  const FACTORY = {
    round: () => new Outline(circle, 1), oval: () => new Outline(circle, 8 / 6), cushion: () => new Outline(superellipse(3.4), 1),
    pear: () => new Outline(teardrop, 1.5), emerald: () => new Outline(polygonFn(chamfered(1, 1.4, 0.15)), 1.4),
    princess: () => new Outline(polygonFn(chamfered(1, 1, 0.03)), 1),
  };
  const outlines = {};
  const outline = (cut) => outlines[cut] || (outlines[cut] = FACTORY[cut]());

  class GemSpec {
    constructor(cut, L, W, cuts) {
      const info = cuts[cut];
      this.cut = cut; this.length = L; this.width = W;
      this.depth = W * info.depth_ratio; this.crown = this.depth * info.crown_fraction; this.pavilion = this.depth * info.pavilion_fraction;
      this.o = outline(cut); this.sx = W; this.sy = L / this.o.aspect;
    }
    scaled(p, n) {
      const nn = [n[0] / this.sx, n[1] / this.sy], l = Math.hypot(nn[0], nn[1]);
      return [[p[0] * this.sx, p[1] * this.sy], [nn[0] / l, nn[1] / l]];
    }
    at(azDeg) {
      const target = (azDeg * Math.PI) / 180;
      let bestT = 0, bestD = Infinity;
      for (let i = 0; i < 720; i++) {
        const t = (TAU * i) / 720, p = this.o.point(t);
        const d = Math.abs(((((Math.atan2(p[1], p[0]) - target + Math.PI) % TAU) + TAU) % TAU) - Math.PI);
        if (d < bestD) { bestD = d; bestT = t; }
      }
      return this.scaled(this.o.point(bestT), this.o.normal(bestT));
    }
    loop(n = 96) {
      const pts = [], nrm = [];
      for (let i = 0; i < n; i++) { const t = (TAU * i) / n; const [p, q] = this.scaled(this.o.point(t), this.o.normal(t)); pts.push(p); nrm.push(q); }
      return [pts, nrm];
    }
  }

  // --- mesh building: closed parts are oriented outward by signed volume, then merged
  class MB {
    constructor() { this.v = []; this.f = []; }
    add(part) {
      let vol = 0;
      for (const f of part.f) for (let k = 1; k + 1 < f.length; k++) vol += dot(part.v[f[0]], cross(part.v[f[k]], part.v[f[k + 1]]));
      const base = this.v.length;
      for (const p of part.v) this.v.push(p);
      for (const f of part.f) this.f.push((vol < 0 ? f.slice().reverse() : f).map((i) => i + base));
      return this;
    }
    geometry() {
      const pos = new Float32Array(this.v.length * 3);
      this.v.forEach((p, i) => { pos[i * 3] = p[0] * 0.001; pos[i * 3 + 1] = p[2] * 0.001; pos[i * 3 + 2] = -p[1] * 0.001; });
      const idx = [];
      for (const f of this.f) for (let k = 1; k + 1 < f.length; k++) idx.push(f[0], f[k], f[k + 1]);
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      return g;
    }
  }
  const gltfPos = (p) => new THREE.Vector3(p[0] * 0.001, p[2] * 0.001, -p[1] * 0.001);

  function catmull(points, n = 8) {
    const p = points, last = p.length - 1;
    const ext = [sub(mul(p[0], 2), p[1]), ...p, sub(mul(p[last], 2), p[last - 1])];
    const out = [];
    for (let i = 1; i < ext.length - 2; i++) {
      const [p0, p1, p2, p3] = [ext[i - 1], ext[i], ext[i + 1], ext[i + 2]];
      for (let s = 0; s < n; s++) {
        const t = s / n, t2 = t * t, t3 = t2 * t;
        out.push([0, 1, 2].map((k) => 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)));
      }
    }
    out.push(p[last].slice());
    return out;
  }
  function frames(path, closed) {
    const n = path.length, T = [], N = [];
    for (let i = 0; i < n; i++) {
      const a = closed || i > 0 ? path[(i - 1 + n) % n] : path[i];
      const b = closed || i < n - 1 ? path[(i + 1) % n] : path[i];
      T.push(unit(sub(b, a)));
    }
    const ref = Math.abs(T[0][2]) < 0.9 ? [0, 0, 1] : [1, 0, 0];
    N[0] = unit(cross(cross(T[0], ref), T[0]));
    for (let i = 0; i < n - 1; i++) {
      const v1 = sub(path[i + 1], path[i]), c1 = dot(v1, v1);
      if (c1 < 1e-18) { N[i + 1] = N[i]; continue; }
      const rl = sub(N[i], mul(v1, (2 / c1) * dot(v1, N[i]))), tl = sub(T[i], mul(v1, (2 / c1) * dot(v1, T[i])));
      const v2 = sub(T[i + 1], tl), c2 = dot(v2, v2);
      N[i + 1] = unit(c2 > 1e-18 ? sub(rl, mul(v2, (2 / c2) * dot(v2, rl))) : rl);
    }
    return [T, N, T.map((t, i) => cross(t, N[i]))];
  }
  function tube(path, radii, seg = 12, closed = false, caps = true) {
    const n = path.length, R = typeof radii === "number" ? Array(n).fill(radii) : radii;
    const [, N, B] = frames(path, closed), v = [], f = [];
    for (let i = 0; i < n; i++) for (let s = 0; s < seg; s++) {
      const a = (TAU * s) / seg;
      v.push(add(path[i], add(mul(N[i], R[i] * Math.cos(a)), mul(B[i], R[i] * Math.sin(a)))));
    }
    for (let i = 0; i < (closed ? n : n - 1); i++) {
      const j = (i + 1) % n;
      for (let s = 0; s < seg; s++) { const s2 = (s + 1) % seg; f.push([i * seg + s, i * seg + s2, j * seg + s2, j * seg + s]); }
    }
    if (caps && !closed) {
      v.push(path[0].slice());
      let c = v.length - 1;
      for (let s = 0; s < seg; s++) f.push([c, (s + 1) % seg, s]);
      v.push(path[n - 1].slice());
      c = v.length - 1;
      const st = (n - 1) * seg;
      for (let s = 0; s < seg; s++) f.push([c, st + s, st + ((s + 1) % seg)]);
    }
    return { v, f };
  }
  function sphere(c, r, u = 12, vv = 8) {
    const v = [add(c, [0, 0, r])], f = [];
    for (let i = 1; i < vv; i++) {
      const th = (Math.PI * i) / vv;
      for (let j = 0; j < u; j++) { const ph = (TAU * j) / u; v.push(add(c, mul([Math.sin(th) * Math.cos(ph), Math.sin(th) * Math.sin(ph), Math.cos(th)], r))); }
    }
    v.push(add(c, [0, 0, -r]));
    for (let j = 0; j < u; j++) f.push([0, 1 + j, 1 + ((j + 1) % u)]);
    for (let i = 0; i < vv - 2; i++) for (let j = 0; j < u; j++) { const a = 1 + i * u + j, b = 1 + i * u + ((j + 1) % u); f.push([a, a + u, b + u, b]); }
    const last = v.length - 1, base = 1 + (vv - 2) * u;
    for (let j = 0; j < u; j++) f.push([last, base + ((j + 1) % u), base + j]);
    return { v, f };
  }
  function sweepClosed(pts, nrm, profile) {
    const m = pts.length, k = profile.length, v = [], f = [];
    for (let i = 0; i < m; i++) for (const [off, z] of profile) v.push([pts[i][0] + nrm[i][0] * off, pts[i][1] + nrm[i][1] * off, z]);
    for (let i = 0; i < m; i++) for (let j = 0; j < k; j++) {
      const i2 = (i + 1) % m, j2 = (j + 1) % k;
      f.push([i * k + j, i2 * k + j, i2 * k + j2, i * k + j2]);
    }
    return { v, f };
  }

  // --- parts (see gx_rings.py for the design notes)
  function band(innerD, width, thick, segs = 128, prof = 22, exponent = 3.2) {
    const r0 = innerD / 2, e = 2 / exponent, v = [], f = [];
    for (let i = 0; i < segs; i++) {
      const phi = (TAU * i) / segs, top = ((1 + Math.cos(phi)) / 2) ** 2;
      const w = width * (0.9 + 0.25 * top), th = thick * (0.9 + 0.22 * top);
      for (let j = 0; j < prof; j++) {
        const s = (TAU * j) / prof, c = Math.cos(s), sn = Math.sin(s);
        const u = (w / 2) * Math.sign(c) * Math.abs(c) ** e, r = r0 + th / 2 + (th / 2) * Math.sign(sn) * Math.abs(sn) ** e;
        v.push([r * Math.sin(phi), u, r * Math.cos(phi)]);
      }
    }
    for (let i = 0; i < segs; i++) for (let j = 0; j < prof; j++) {
      const i2 = (i + 1) % segs, j2 = (j + 1) % prof;
      f.push([i * prof + j, i2 * prof + j, i2 * prof + j2, i * prof + j2]);
    }
    return { v, f, top: r0 + thick * 1.12 };
  }
  function prongHead(spec, azimuths, baseZ, prongR = 0.45, tipLean = 0.3) {
    const mb = new MB();
    for (const az of azimuths) {
      const [p, n] = spec.at(az), rad = Math.hypot(p[0], p[1]), u = [p[0] / rad, p[1] / rad], k = Math.min(1.2, rad * 0.25);
      const path = catmull([
        [u[0] * k, u[1] * k, baseZ],
        [p[0] * 0.5, p[1] * 0.5, -spec.pavilion * 0.88],
        [p[0] * 0.86 + n[0] * prongR * 0.9, p[1] * 0.86 + n[1] * prongR * 0.9, -spec.pavilion * 0.42],
        [p[0] + n[0] * prongR * 0.75, p[1] + n[1] * prongR * 0.75, 0],
        [p[0] - u[0] * tipLean + n[0] * prongR * 0.2, p[1] - u[1] * tipLean + n[1] * prongR * 0.2, spec.crown * 0.55 + prongR * 0.35],
      ], 8);
      mb.add(tube(path, linspace(prongR * 1.15, prongR * 0.92, path.length), 12));
      mb.add(sphere(path[path.length - 1], prongR, 14, 10));
    }
    const [pts, nrm] = spec.loop(96);
    for (const [df, sc, push, r] of [[0.42, 0.86, prongR * 0.9, prongR * 0.72], [0.86, 0.5, 0, prongR * 0.62]]) {
      mb.add(tube(pts.map((p, i) => [p[0] * sc + nrm[i][0] * push, p[1] * sc + nrm[i][1] * push, -spec.pavilion * df]), r, 10, true));
    }
    return mb;
  }
  function halo(spec, baseZ, accentSize, cuts, gap = 0.14, clearance = 0.35) {
    const [pts, nrm] = spec.loop(240), off = clearance + accentSize / 2;
    const path = pts.map((p, i) => [p[0] + nrm[i][0] * off, p[1] + nrm[i][1] * off]);
    const seg = path.map((p, i) => { const q = path[(i + 1) % path.length]; return Math.hypot(q[0] - p[0], q[1] - p[1]); });
    const per = seg.reduce((a, b) => a + b, 0), count = Math.floor(per / (accentSize + gap));
    const cum = [0];
    for (const s of seg) cum.push(cum[cum.length - 1] + s);
    const at = (d) => {
      d = ((d % per) + per) % per;
      let k = 0;
      while (k < seg.length - 1 && cum[k + 1] <= d) k++;
      const f = (d - cum[k]) / Math.max(seg[k], 1e-9), a = path[k], b = path[(k + 1) % path.length], na = nrm[k], nb = nrm[(k + 1) % nrm.length];
      const nn = [na[0] * (1 - f) + nb[0] * f, na[1] * (1 - f) + nb[1] * f], l = Math.hypot(nn[0], nn[1]);
      return [[a[0] * (1 - f) + b[0] * f, a[1] * (1 - f) + b[1] * f], [nn[0] / l, nn[1] / l]];
    };
    const accent = new GemSpec("round", accentSize, accentSize, cuts), zAcc = -0.3, step = per / count;
    const centres = Array.from({ length: count }, (_, i) => at(i * step)[0]);
    const mb = new MB(), half = accentSize / 2 + 0.22, bottom = zAcc - accent.pavilion - 0.15, top = zAcc - 0.06;
    mb.add(sweepClosed(pts, nrm, [[off - half, bottom + 0.1], [off - half + 0.1, bottom], [off + half - 0.1, bottom], [off + half, bottom + 0.1], [off + half, top], [off - half, top]]));
    for (let i = 0; i < count; i++) {
      const [c, n] = at((i + 0.5) * step);
      for (const side of [-1, 1]) mb.add(sphere([c[0] + n[0] * side * (accentSize / 2 + 0.02), c[1] + n[1] * side * (accentSize / 2 + 0.02), zAcc + 0.08], 0.2, 8, 6));
    }
    for (const az of [45, 135, 225, 315]) {
      const [p, n] = spec.at(az), rad = Math.hypot(p[0], p[1]);
      const start = [p[0] + n[0] * off, p[1] + n[1] * off, bottom + 0.05], end = [(p[0] / rad) * 1.4, (p[1] / rad) * 1.4, baseZ];
      const mid = [(start[0] + end[0]) / 2 + n[0] * 0.5, (start[1] + end[1]) / 2 + n[1] * 0.5, (start[2] + end[2]) / 2];
      mb.add(tube(catmull([start, mid, end], 8), linspace(0.42, 0.55, 17), 10));
    }
    return { mb, centres, zAcc, accent };
  }
  function bezelCup(spec, baseZ) {
    const [pts, nrm] = spec.loop(160), mb = new MB();
    mb.add(sweepClosed(pts, nrm, [[0.05, -1.35], [0.05, 0.22], [-0.12, 0.33], [0.15, 0.46], [0.75, 0.3], [0.8, -1.45], [0.45, -1.95], [-0.25, -1.95]]));
    for (let az = 0; az < 360; az += 60) {
      const [p, n] = spec.at(az + 30), rad = Math.hypot(p[0], p[1]);
      const start = [p[0] + n[0] * 0.2, p[1] + n[1] * 0.2, -1.85], end = [(p[0] / rad) * 1.2, (p[1] / rad) * 1.2, baseZ];
      mb.add(tube(catmull([start, add(mul(add(start, end), 0.5), [0, 0, -0.2]), end], 8), linspace(0.5, 0.6, 17), 10));
    }
    return mb;
  }
  function cathedralArches(spec, mountZ, innerR, thick) {
    const mb = new MB(), rIn = innerR + thick * 0.55;
    for (const side of [-1, 1]) {
      const [p] = spec.at(side > 0 ? 0 : 180);
      for (const y of [-1, 1]) {
        const phi = (36 * Math.PI / 180) * side;
        const start = [rIn * Math.sin(phi), y * 0.6, rIn * Math.cos(phi)];
        const rise = [rIn * 1.08 * Math.sin(phi * 0.82), y * 0.6, rIn * 1.08 * Math.cos(phi * 0.82)];
        const end = [p[0] * 0.72, y * 0.5, mountZ - spec.pavilion * 0.45];
        const crest = [(rise[0] + end[0]) * 0.5 + side * 0.85, y * 0.56, (rise[2] + end[2]) * 0.5 + 0.55];
        const path = catmull([start, rise, crest, end], 10);
        mb.add(tube(path, linspace(0.52, 0.34, path.length), 14));
      }
    }
    return mb;
  }

  const HEAD = { low: 0.45, medium: 1.0, high: 1.6 };
  const PRONGS = { 4: [45, 135, 225, 315], 6: [0, 60, 120, 180, 240, 300], 8: [22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5] };
  const PLACEHOLDER = new THREE.MeshStandardMaterial();
  const mesh = (name, mb) => { const m = new THREE.Mesh(mb.geometry(), PLACEHOLDER); m.name = name; return m; };

  /** Builds a ring setting (no centre stone) from a ring spec. `roundGeo` is the unit round-cut geometry for accents. */
  function build(spec, cuts, roundGeo) {
    const root = new THREE.Group();
    root.name = "Ring_Custom";
    const innerD = spec.innerDiameterMm || 17.3;
    const b = band(innerD, spec.bandWidthMm, spec.bandThicknessMm);
    root.add(mesh("Band", new MB().add(b)));
    const st = spec.stone, center = new GemSpec(st.shapeId, st.lengthMm, st.widthMm, cuts);
    const mountZ = b.top + (HEAD[spec.headHeight] ?? 1.0) + center.pavilion, baseZ = b.top - mountZ - 0.35;
    const mount = new THREE.Group();
    mount.name = "GemMount_Center";
    mount.position.copy(gltfPos([0, 0, mountZ]));
    root.add(mount);
    const info = { accentStones: 0, accentSizeMm: 0 };
    if (spec.style === "bezel") {
      mount.add(mesh("Bezel", bezelCup(center, baseZ)));
    } else if (spec.style === "halo") {
      mount.add(mesh("Head_Center", prongHead(center, PRONGS[4], baseZ, 0.36, 0.25)));
      const a = spec.halo?.accentSizeMm ?? 1.3, h = halo(center, baseZ, a, cuts);
      mount.add(mesh("Halo_Frame", h.mb));
      h.centres.forEach((c, i) => {
        const g = new THREE.Mesh(roundGeo, PLACEHOLDER);
        g.name = `Accent_${String(i).padStart(2, "0")}`;
        g.scale.set(a, h.accent.depth, a);
        g.position.copy(gltfPos([c[0], c[1], h.zAcc]));
        mount.add(g);
      });
      Object.assign(info, { accentStones: h.centres.length, accentSizeMm: a });
    } else {
      const az = PRONGS[spec.prongs] || PRONGS[4];
      mount.add(mesh("Head_Center", prongHead(center, az, baseZ, az.length === 4 ? 0.45 : 0.4)));
      if (spec.style === "three_stone") {
        const size = spec.sideStones?.sizeMm ?? 4, side = new GemSpec("round", size, size, cuts);
        for (const [id, sign] of [["SideL", 1], ["SideR", -1]]) {
          const x = sign * (center.width / 2 + size / 2 + 1.1), tilt = 14 * sign, z = mountZ - 1.2;
          const sm = new THREE.Group();
          sm.name = `GemMount_${id}`;
          sm.position.copy(gltfPos([x, 0, z]));
          sm.rotation.z = (-tilt * Math.PI) / 180;   // Blender Ry(+a) == glTF Rz(-a)
          const bandBelow = Math.sqrt(Math.max(b.top ** 2 - (Math.abs(x) * 0.85) ** 2, 0)) - 0.4;
          sm.add(mesh(`Head_${id}`, prongHead(side, PRONGS[4], -(z - bandBelow) / Math.cos((14 * Math.PI) / 180), 0.33, 0.18)));
          root.add(sm);
        }
      }
      if (spec.cathedral) root.add(mesh("Cathedral", cathedralArches(center, mountZ, innerD / 2, spec.bandThicknessMm)));
    }
    return { root, info };
  }

  return { build, GemSpec };
})();

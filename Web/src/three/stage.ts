// The 3D display stand: ring + gemstone + optional hand, driven by the app store and the wearable.
// Units: millimetres. Ring local axes (glTF): +Y = towards the stone, +Z = along the finger.
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { CATEGORIES, GEM_FILES, byId, categoryOf, pieceFile, type Category, type Gemstone, type RingDef } from "../lib/catalog";
import { designView, useApp } from "../lib/store";
import { live, sim } from "../wearable/live";
import { GEN } from "./ringGenerator.js";

const HOME = { pos: new THREE.Vector3(40, 26, 72), target: new THREE.Vector3(0, 2, 0) };
// Rough size of each display relative to the ring stand (camera distances, top/side views).
const SCALE: Record<Category, number> = { ring: 1, pendant: 2.4, necklace: 4.6, bracelet: 3.1, earring: 1.8 };

export class Stage {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(28, 1, 1, 4000);
  private controls: OrbitControls;
  private loader = new GLTFLoader();
  private stand = new THREE.Group();        // ring stand (stays still while the ring turns)
  private pivot = new THREE.Group();        // wearable orientation is applied here
  private key: THREE.SpotLight;
  private displayCat: Category | null = null;
  private anchorZ = 0;                      // bail position on the length axis: the head scales about it
  private handHolder = new THREE.Group();
  private handLoad: Promise<void> | null = null;
  private handView = { pos: new THREE.Vector3(70, 190, -170), target: new THREE.Vector3(0, 0, -40) };

  private ringCache: Record<string, THREE.Group> = {};
  private gemGeo: Record<string, THREE.BufferGeometry> = {};
  private ringRoot: THREE.Object3D | null = null;
  private headScaler: THREE.Group | null = null;
  private centerGem: THREE.Mesh | null = null;
  private twins: { scaler: THREE.Group; gem: THREE.Mesh }[] = [];   // the second earring of a pair follows the centre stone
  private drops: { node: THREE.Object3D; z0: number }[] = [];        // chain drops (Drop_*): they ride on the bottom of the head, unscaled
  private accentGemMats: Record<string, THREE.MeshPhysicalMaterial> = {};
  private lastHome: { pos: THREE.Vector3; target: THREE.Vector3 } | null = null;                     // where the camera last framed a piece   // coloured accents, e.g. pink pave
  private loose = new THREE.Group();        // Gemstone Gallery: one loose stone on a small gem tray (millimetres)
  private looseInner = new THREE.Group();   // holds the stone, scaled like a ring root (m -> mm)
  private looseTray: THREE.Mesh;            // light felt pad: gives a transparent stone something to refract, so it shows its colour
  private looseGem: THREE.Mesh | null = null;
  private looseMat = Stage.makeGem();
  private looseOn = false;
  private looseShape: string | null = null;
  private metalMat = new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 1, roughness: 0.08, envMapIntensity: 1.25 });
  private gemMat = Stage.makeGem();
  private accentMat = Stage.makeGem();

  private loadedRingId: string | null = null;
  private loadedRingVersion = -1;
  private loadedShapeId: string | null = null;
  private syncing = false;
  private syncAgain = false;
  private tween: { p0: THREE.Vector3; t0: THREE.Vector3; p1: THREE.Vector3; t1: THREE.Vector3; start: number; ms: number } | null = null;
  private clock = new THREE.Clock();
  private raf = 0;
  private unsub: () => void;
  private resizeObs: ResizeObserver;

  constructor(private canvas: HTMLCanvasElement) {
    const r = (this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }));
    r.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    r.toneMapping = THREE.AgXToneMapping;
    r.toneMappingExposure = 1.15;
    this.scene.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.03).texture;

    this.camera.position.copy(HOME.pos);
    const c = (this.controls = new OrbitControls(this.camera, canvas));
    c.target.copy(HOME.target);
    c.enableDamping = true;
    c.minDistance = 16;
    c.maxDistance = 420;
    c.autoRotate = true;
    c.autoRotateSpeed = 0.9;
    c.addEventListener("start", () => this.setAutoRotate(false));

    const key = (this.key = new THREE.SpotLight(0xffe2bd, 3.2, 0, Math.PI / 7, 0.6, 0));
    key.position.set(20, 160, 60);
    this.scene.add(key, key.target, new THREE.HemisphereLight(0xfff1dd, 0x120e10, 0.35));

    // Display stand: black lacquer plinth, gold rim, burgundy velvet cushion.
    const lacquer = new THREE.MeshPhysicalMaterial({ color: 0x0b0b0d, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08 });
    const goldTrim = new THREE.MeshStandardMaterial({ color: 0xc9a45c, metalness: 1, roughness: 0.22 });
    const velvet = new THREE.MeshStandardMaterial({ color: 0x1f070e, roughness: 1 });
    const plinth = new THREE.Mesh(new THREE.CylinderGeometry(26, 28, 10, 72), lacquer);
    plinth.position.y = -16.4;
    const rim = new THREE.Mesh(new THREE.TorusGeometry(26, 0.5, 12, 96), goldTrim);
    rim.rotation.x = Math.PI / 2; rim.position.y = -11.4;
    const cushion = new THREE.Mesh(new THREE.CylinderGeometry(14, 14.6, 1.2, 64), velvet);
    cushion.position.y = -10.8;
    this.stand.add(plinth, rim, cushion);
    this.scene.add(this.stand, this.pivot);
    this.loose.visible = false;
    this.looseInner.scale.setScalar(1000);
    this.looseTray = new THREE.Mesh(new THREE.CylinderGeometry(1, 1.03, 1, 96),
      new THREE.MeshPhysicalMaterial({ color: 0xb9b4ab, roughness: 0.85, sheen: 0.4, sheenColor: 0xffffff }));
    this.loose.add(this.looseInner, this.looseTray);
    this.pivot.add(this.loose);
    this.handHolder.visible = false;
    this.handHolder.matrixAutoUpdate = false;
    this.pivot.add(this.handHolder);

    this.accentMat.ior = 2.333;
    this.accentMat.dispersion = 3;

    this.resizeObs = new ResizeObserver(() => this.resize());
    this.resizeObs.observe(canvas);
    this.resize();

    this.unsub = useApp.subscribe((s, prev) => {
      if (s.design !== prev.design || s.ringVersion !== prev.ringVersion || s.draftRing !== prev.draftRing || s.cat !== prev.cat) this.queueSync();
      if (s.autoRotate !== prev.autoRotate) this.controls.autoRotate = s.autoRotate;
      if (s.view !== prev.view || s.gallery !== prev.gallery) this.syncLoose().catch((e) => console.error(e));
      if (s.wear.mode !== "off" && prev.wear.mode === "off") this.setAutoRotate(false);   // the wearable drives the ring now
    });
    this.queueSync();
    this.syncLoose().catch((e) => console.error(e));
    this.tick();
    if (import.meta.env.DEV) (window as unknown as { __gxStage: Stage }).__gxStage = this;   // debugging in npm run dev
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.unsub();
    this.resizeObs.disconnect();
    this.controls.dispose();
    this.renderer.dispose();
  }

  private static makeGem() {
    return new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0, roughness: 0, transmission: 1, thickness: 0.0008,
      ior: 1.77, specularIntensity: 1, envMapIntensity: 1.6, flatShading: true });
  }

  private accentGemMat(gemId: string) {
    if (!this.accentGemMats[gemId]) {
      const mat = Stage.makeGem(), g = useApp.getState().cat?.gemstones.find((x) => x.id === gemId);
      if (g) { this.styleGem(mat, g); mat.attenuationDistance = 0.9; }   // small stones: a shorter path for the same depth of colour
      this.accentGemMats[gemId] = mat;
    }
    return this.accentGemMats[gemId];
  }

  private styleGem(mat: THREE.MeshPhysicalMaterial, g: Gemstone) {
    const c = new THREE.Color(g.colorHex), isClear = g.id === "diamond";
    mat.color.copy(isClear ? new THREE.Color(0xffffff) : c.clone().lerp(new THREE.Color(0xffffff), 0.45));
    mat.attenuationColor.copy(isClear ? new THREE.Color(0xffffff) : c);
    mat.attenuationDistance = isClear ? Infinity : 3.6;
    mat.ior = Math.min(g.refractiveIndex, 2.333);   // three.js caps IOR at 2.333 (diamond is 2.42)
    mat.dispersion = isClear ? 3.5 : Math.min(3, g.dispersion * 45);   // fire follows the mineral: corundum 0.8, zircon 1.8, quartz 0.6
    mat.needsUpdate = true;
  }

  // ------------------------------------------------------------------ loading
  private async loadGemGeometry(shapeId: string) {
    if (this.gemGeo[shapeId]) return this.gemGeo[shapeId];
    const gltf = await this.loader.loadAsync(`/models/${GEM_FILES[shapeId]}.glb`);
    let geo: THREE.BufferGeometry | null = null;
    gltf.scene.traverse((o) => { if ((o as THREE.Mesh).isMesh && !geo) geo = (o as THREE.Mesh).geometry; });
    this.gemGeo[shapeId] = geo!;
    return geo!;
  }

  private async loadRing() {
    const s = useApp.getState(), v = designView(s)!;
    const r = v.ring;
    let root: THREE.Object3D;
    if (r.custom && r.spec) {
      const built = GEN.build(r.spec, s.meta!.gemCuts, await this.loadGemGeometry("round"));
      useApp.setState({ customInfo: { ...useApp.getState().customInfo, [r.id]: built.info } });
      root = built.root;
    } else {
      const file = pieceFile(r);   // custom necklaces and bracelets share their base piece's model
      if (!this.ringCache[file]) this.ringCache[file] = (await this.loader.loadAsync(`/models/${file}.glb`)).scene;
      root = this.ringCache[file].clone(true);
    }
    if (this.ringRoot) this.pivot.remove(this.ringRoot);
    this.ringRoot = root;
    root.scale.setScalar(1000);   // rings are in metres (GLB and generator alike); the stage works in millimetres
    const metalPrefixes = r.metalRendererPrefixes, accentPrefixes = r.accentStoneRendererPrefixes || [];
    const accentGems = r.accentGems || {};
    root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const coloured = Object.keys(accentGems).find((p) => m.name.startsWith(p));
      if (coloured) m.material = accentGems[coloured] === "center" ? this.gemMat : this.accentGemMat(accentGems[coloured]);
      else if (accentPrefixes.some((p) => m.name.startsWith(p))) m.material = this.accentMat;
      else if (metalPrefixes.some((p) => m.name.startsWith(p))) m.material = this.metalMat;
    });
    // Wrap the centre head so it can follow the stone's footprint (the stone itself is a sibling).
    // A pendant bail (Attach_*) stays where it is on the chain; the head scales about it instead.
    // A chain drop (Drop_*) is not scaled either: it moves so it stays on the bottom of the head.
    this.drops = [];
    const wrapHead = (mount: THREE.Object3D) => {
      const scaler = new THREE.Group();
      scaler.name = "HeadScaler";
      [...mount.children].filter((c) => !c.name.startsWith("Attach_") && !c.name.startsWith("Drop_")).forEach((c) => scaler.add(c));
      mount.children.filter((c) => c.name.startsWith("Drop_")).forEach((node) => this.drops.push({ node, z0: node.position.z }));
      mount.add(scaler);
      return scaler;
    };
    const mount = root.getObjectByName("GemMount_Center")!;
    this.headScaler = wrapHead(mount);
    this.anchorZ = mount.getObjectByName("Attach_Bail")?.position.z ?? 0;
    const gemGeo = await this.loadGemGeometry(v.d.shapeId);
    this.centerGem = new THREE.Mesh(gemGeo, this.gemMat);
    this.centerGem.name = "CenterGem";
    mount.add(this.centerGem);
    // Earring pairs: GemMount_Pair carries the same head and takes the same stone.
    this.twins = [];
    const pair = root.getObjectByName("GemMount_Pair");
    if (pair) {
      const gem = new THREE.Mesh(gemGeo, this.gemMat);
      gem.name = "PairGem";
      this.twins.push({ scaler: wrapHead(pair), gem });
      pair.add(gem);
    }
    for (const m of r.mounts.filter((x) => x.role === "side" && x.fixedShapeId)) {
      const node = root.getObjectByName(`GemMount_${m.id}`);
      if (!node) continue;
      const g = new THREE.Mesh(await this.loadGemGeometry(m.fixedShapeId!), this.accentMat);
      const L = m.fixedLengthMm!;
      g.scale.set(L, L * v.depthRatio(m.fixedShapeId!), L);
      node.add(g);
    }
    this.pivot.add(root);
    this.applyDisplay(r);
  }

  private queueSync() {
    if (this.syncing) { this.syncAgain = true; return; }
    this.syncing = true;
    this.sync()
      .then(() => useApp.setState({ stageReady: true, stageError: null }))
      .catch((e) => { console.error(e); useApp.setState({ stageError: "The 3D models could not be loaded. Reload to try again." }); })
      .finally(() => { this.syncing = false; if (this.syncAgain) { this.syncAgain = false; this.queueSync(); } });
  }

  private async sync() {
    const s = useApp.getState(), v = designView(s);
    if (!v) return;
    if (this.loadedRingId !== v.d.ringId || this.loadedRingVersion !== s.ringVersion || !this.centerGem) {
      await this.loadRing();
      this.loadedRingId = v.d.ringId; this.loadedRingVersion = s.ringVersion; this.loadedShapeId = v.d.shapeId;
    }
    if (this.loadedShapeId !== v.d.shapeId) {
      this.centerGem!.geometry = await this.loadGemGeometry(v.d.shapeId);
      this.twins.forEach((t) => { t.gem.geometry = this.centerGem!.geometry; });
      this.loadedShapeId = v.d.shapeId;
    }
    const cur = designView(useApp.getState())!;   // the design may have moved on while models loaded
    this.metalMat.color.set(cur.metal.colorHex);
    this.metalMat.roughness = Math.max(0.04, (1 - cur.metal.smoothness) * 0.6);
    this.styleGem(this.gemMat, cur.gem);
    const head = cur.headDefaults(), kz = cur.d.lengthMm / head.L, shift = this.anchorZ * (1 - kz);
    this.headScaler!.scale.set(cur.d.widthMm / head.W, 1, kz);
    this.headScaler!.position.set(0, 0, shift);
    this.centerGem!.scale.set(cur.d.widthMm, cur.depthMm, cur.d.lengthMm);
    this.centerGem!.position.set(cur.d.seat.x * 0.001, cur.d.seat.y * 0.001, cur.d.seat.z * 0.001 + shift);
    for (const dr of this.drops) dr.node.position.z = this.anchorZ + (dr.z0 - this.anchorZ) * kz;
    for (const t of this.twins) {   // mirror twin: side-to-side seat offset flips
      t.scaler.scale.copy(this.headScaler!.scale); t.scaler.position.copy(this.headScaler!.position);
      t.gem.scale.copy(this.centerGem!.scale);
      t.gem.position.set(-cur.d.seat.x * 0.001, cur.d.seat.y * 0.001, cur.d.seat.z * 0.001 + shift);
    }
    this.gemMat.emissive.set(cur.fit().status === "bad" ? 0x5a0d0d : 0x000000);
  }

  // ------------------------------------------------------------------ displays
  private home(cat: Category = this.displayCat || "ring") {
    if (this.looseOn) {                                            // the loose stone, from above and in front
      const g = useApp.getState().gallery, d = 5.6 * Math.max(g.lengthMm, g.widthMm) + 12;
      return { pos: new THREE.Vector3(0.36, 0.62, 0.7).normalize().multiplyScalar(d), target: new THREE.Vector3(0, 0, 0) };
    }
    if (cat === "ring") return HOME;
    if (cat === "bracelet") return { pos: new THREE.Vector3(205, 58, 158), target: new THREE.Vector3(0, -6, 0) };
    if (cat === "necklace") return { pos: new THREE.Vector3(130, 95, 520), target: new THREE.Vector3(0, -5, 8) };      // the whole necklace
    if (cat === "earring") {                                       // the pair, front three-quarter; drops hang lower, so frame them too
      let cy = 5, k = 1;
      if (this.ringRoot) {
        this.ringRoot.updateWorldMatrix(true, true);
        const box = new THREE.Box3().setFromObject(this.ringRoot);
        cy = (box.min.y + box.max.y) / 2 + 2; k = Math.max(1, (box.max.y - box.min.y) / 24);
      }
      return { pos: new THREE.Vector3(46 * k, 26 * k + cy - 5, 138 * k), target: new THREE.Vector3(0, cy, 0) };
    }
    // Pendant: the stone and bail with the chain rising either side of it.
    // A big pendant (the starburst) is framed from further back.
    let k = 1;
    const mount = this.centerGem?.parent;
    if (mount) { mount.updateWorldMatrix(true, true); const sz = new THREE.Box3().setFromObject(mount).getSize(new THREE.Vector3()); k = Math.max(1, Math.max(sz.x, sz.y) / 20); }
    const target = this.centerGem ? this.centerGem.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 9 * Math.sqrt(k), 0)) : new THREE.Vector3(0, -33, 50);
    return { pos: target.clone().add(new THREE.Vector3(62, 26, 175).multiplyScalar(k)), target };
  }

  /** Rings sit on the stand; every other piece is shown on its own. Frames the piece when the jewellery type changes. */
  private applyDisplay(r: RingDef) {
    const cat = categoryOf(r), onFinger = useApp.getState().onFinger;
    if (onFinger && cat !== "ring") { this.handHolder.visible = false; useApp.setState({ onFinger: false }); }
    const finger = useApp.getState().onFinger;
    this.stand.visible = cat === "ring" && !finger && !this.looseOn;
    if (this.ringRoot) this.ringRoot.visible = !this.looseOn;
    if (cat === this.displayCat) {                                 // same type: reframe only if this piece sits elsewhere (a drop pair, a big pendant)
      const h = this.home(cat);
      const moved = this.lastHome && (h.target.distanceTo(this.lastHome.target) > 4 || h.pos.distanceTo(this.lastHome.pos) > 25);
      if (!finger && !this.looseOn && moved) { this.lastHome = h; this.flyTo(h.pos, h.target); }
      return;
    }
    this.displayCat = cat;
    const k = SCALE[cat];
    this.controls.minDistance = 16 * Math.min(k, 2);
    this.controls.maxDistance = 420 * Math.max(k / 1.6, 1);
    const big = cat !== "ring";
    const [kx, ky, kz] = cat === "bracelet" ? [40, 320, 170] : cat === "earring" ? [60, 170, 230] : big ? [70, 260, 430] : [20, 160, 60];
    const neck = cat === "pendant" || cat === "necklace";       // modelled where they would hang at the neck
    this.key.position.set(kx, ky, kz);
    this.key.target.position.set(0, neck ? -30 : 0, neck ? 40 : 0);
    this.key.angle = big ? Math.PI / 6 : Math.PI / 7;
    this.key.intensity = cat === "bracelet" ? 2.3 : cat === "earring" ? 2.6 : big ? 2.4 : 3.2;
    if (!finger && !this.looseOn) { const h = this.home(cat); this.lastHome = h; this.flyTo(h.pos, h.target); }
  }

  // ------------------------------------------------------------------ gemstone gallery
  /** Shows the Gallery's loose stone while that screen is open, and puts the design back on display afterwards. */
  private async syncLoose() {
    const s = useApp.getState(), on = s.view === "gallery";
    if (on && s.cat && s.meta) {
      const g = s.gallery, gem = byId(s.cat.gemstones, g.gemId), shape = byId(s.cat.shapes, g.shapeId);
      if (!gem || !shape) return;
      if (this.looseShape !== g.shapeId) {
        const geo = await this.loadGemGeometry(g.shapeId);
        if (!this.looseGem) { this.looseGem = new THREE.Mesh(geo, this.looseMat); this.looseGem.name = "LooseGem"; this.looseInner.add(this.looseGem); }
        else this.looseGem.geometry = geo;
        this.looseShape = g.shapeId;
      }
      this.styleGem(this.looseMat, gem);
      const depth = g.widthMm * (s.meta.gemCuts?.[g.shapeId]?.depth_ratio ?? shape.depthRatio);
      this.looseGem!.scale.set(g.widthMm, depth, g.lengthMm);
      const crown = s.meta.gemCuts?.[g.shapeId]?.crown_fraction ?? 0.27;
      this.looseGem!.position.set(0, depth * (0.5 - crown) * 0.001, 0);   // centre the whole stone (crown + pavilion) on the orbit point
      const r = 0.85 * Math.max(g.lengthMm, g.widthMm) + 1.2;               // tray just under the culet, a little wider than the stone
      this.looseTray.scale.set(r, 0.8, r);
      // Coloured stones need light behind them to show their colour; a colourless stone needs a dark pad to show its facets.
      const pad = this.looseTray.material as THREE.MeshPhysicalMaterial, clear = g.gemId === "diamond";
      pad.color.set(clear ? 0x2c2b2a : 0xb9b4ab);
      pad.sheen = clear ? 0 : 0.4;
      this.looseTray.position.y = -depth / 2 - 0.45;
    }
    if (on === this.looseOn) return;
    this.looseOn = on;
    this.loose.visible = on;
    const finger = s.onFinger, cat = this.displayCat || "ring";
    if (this.ringRoot) this.ringRoot.visible = !on;
    this.stand.visible = cat === "ring" && !finger && !on;
    this.handHolder.visible = finger && !on;
    if (on) {
      this.controls.minDistance = 6; this.controls.maxDistance = 160;
      this.key.position.set(20, 160, 60); this.key.target.position.set(0, 0, 0);
      this.key.angle = Math.PI / 7; this.key.intensity = 3.2;
      const h = this.home(); this.setAutoRotate(true); this.flyTo(h.pos, h.target);
    } else {
      this.displayCat = null;                                      // re-frame whatever is on display
      const v = designView(s);
      if (v && this.ringRoot) this.applyDisplay(v.ring);
      if (finger) this.flyTo(this.handView.pos, this.handView.target);
    }
  }

  // ------------------------------------------------------------------ hand
  /** Loads the hand and fits it so the ring (at the origin, stone up) sits on the ring finger's base segment. */
  private ensureHand() {
    if (this.handLoad) return this.handLoad;
    this.handLoad = (async () => {
      const gltf = await this.loader.loadAsync("/models/Hand_Left.glb");
      const hand = gltf.scene;
      const skin = new THREE.MeshPhysicalMaterial({ color: 0xc9937a, roughness: 0.5, sheen: 0.6, sheenColor: 0xffb9a0,
        sheenRoughness: 0.55, clearcoat: 0.05, clearcoatRoughness: 0.5, envMapIntensity: 0.9, side: THREE.DoubleSide });
      const meshes: THREE.Mesh[] = [];
      hand.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh) { m.material = skin; m.frustumCulled = false; meshes.push(m); }
      });
      hand.updateMatrixWorld(true);
      const P = (n: string) => hand.getObjectByName(n)!.getWorldPosition(new THREE.Vector3());
      const knuckle = P("ring-finger-phalanx-proximal"), middle = P("ring-finger-phalanx-intermediate");
      const along = middle.clone().sub(knuckle).normalize();
      // Back of the hand: the palm normal from the knuckle line and the finger direction, flipped to the side the thumb isn't on.
      const across = P("index-finger-phalanx-proximal").sub(P("pinky-finger-phalanx-proximal")).normalize();
      let up = new THREE.Vector3().crossVectors(along, across).normalize();
      const thumbSide = P("thumb-tip").sub(knuckle);
      if (up.dot(thumbSide) > 0) up.negate();
      up = up.sub(along.clone().multiplyScalar(up.dot(along))).normalize();
      const side = new THREE.Vector3().crossVectors(up, along).normalize();

      // Measure the finger where the ring sits: rays outward from the bone line, centroid + average radius.
      let center = knuckle.clone().lerp(middle, 0.38);
      const ray = new THREE.Raycaster();
      const hits: THREE.Vector3[] = [];
      for (let k = 0; k < 12; k++) {
        const a = (k / 12) * Math.PI * 2;
        const d = side.clone().multiplyScalar(Math.cos(a)).add(up.clone().multiplyScalar(Math.sin(a))).normalize();
        ray.set(center, d);
        ray.far = 0.04;
        const hit = ray.intersectObjects(meshes, false)[0];
        if (hit) hits.push(hit.point);
      }
      let radius = 0.0084;
      if (hits.length >= 8) {
        center = hits.reduce((acc, p) => acc.add(p), new THREE.Vector3()).multiplyScalar(1 / hits.length);
        radius = hits.reduce((acc, p) => acc + p.clone().sub(center).projectOnPlane(along).length(), 0) / hits.length;
      }
      skin.side = THREE.FrontSide;
      // Scale so the finger fills the 17.3 mm ring (radius 8.65 mm) with a little room.
      const ringInnerR = (designView(useApp.getState())?.ring.innerDiameterMm ?? 17.3) / 2;
      const scale = THREE.MathUtils.clamp((ringInnerR - 0.25) / radius, 700, 1400);
      const frame = new THREE.Matrix4().makeBasis(side, up, along).setPosition(center);
      this.handHolder.matrix.copy(new THREE.Matrix4().makeScale(scale, scale, scale).multiply(frame.invert()));
      this.handHolder.matrixWorldNeedsUpdate = true;
      this.handHolder.add(hand);

      // Camera for the hand view: above the back of the hand, looking from the wrist towards the fingertips.
      this.handHolder.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(hand);
      const size = box.getSize(new THREE.Vector3()).length();
      const mid = box.getCenter(new THREE.Vector3());
      const target = new THREE.Vector3(0, 0, 0).lerp(mid, 0.3);
      this.handView = { target, pos: target.clone().add(new THREE.Vector3(0.16 * size, 0.62 * size, -0.45 * size)) };
    })();
    this.handLoad.catch(() => { this.handLoad = null; });
    return this.handLoad;
  }

  async setFinger(on: boolean) {
    const cat = this.displayCat || "ring";
    if (on && this.looseOn) { useApp.getState().showToast("The Gemstone Gallery shows loose stones. Choose a ring to see it on the hand."); return; }
    if (on && cat !== "ring") {
      useApp.getState().showToast(`The hand is for rings; ${CATEGORIES.find((c) => c.id === cat)!.plural.toLowerCase()} are shown on their own.`);
      return;
    }
    if (on) {
      try { await this.ensureHand(); }
      catch (e) { console.error(e); useApp.getState().showToast("The hand model could not be loaded."); return; }
    }
    this.handHolder.visible = on;
    this.stand.visible = !on;
    this.setAutoRotate(false);
    const h = this.home();
    this.flyTo(on ? this.handView.pos : h.pos, on ? this.handView.target : h.target);
    useApp.setState({ onFinger: on });
    useApp.getState().showToast(on ? "On a left ring finger, ring size 17.3 mm. Rotate the wearable to turn your hand." : "Back on the display stand.");
  }

  // ------------------------------------------------------------------ camera
  private resize() {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }
  private flyTo(pos: THREE.Vector3, target: THREE.Vector3, ms = 700) {
    this.tween = { p0: this.camera.position.clone(), t0: this.controls.target.clone(), p1: pos.clone(), t1: target.clone(), start: performance.now(), ms };
  }
  setAutoRotate(on: boolean) { this.controls.autoRotate = on; useApp.setState({ autoRotate: on }); }
  zoom(f: number) {
    const d = this.camera.position.clone().sub(this.controls.target).multiplyScalar(f);
    this.flyTo(this.controls.target.clone().add(d), this.controls.target, 300);
  }
  resetView() {
    if (useApp.getState().onFinger) { this.setAutoRotate(false); this.flyTo(this.handView.pos, this.handView.target); return; }
    const h = this.home();
    this.setAutoRotate(true); this.flyTo(h.pos, h.target);
  }
  closeUp() {
    if (this.looseOn) { const h = this.home(); this.setAutoRotate(false); this.flyTo(h.pos.clone().multiplyScalar(0.6), h.target); return; }
    if (!this.centerGem) return;
    this.setAutoRotate(false);
    const p = this.centerGem.getWorldPosition(new THREE.Vector3());
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(this.centerGem.getWorldQuaternion(new THREE.Quaternion()));   // out of the table
    this.flyTo(p.clone().add(up.multiplyScalar(14)).add(new THREE.Vector3(9, 0, 13)), p);
  }
  topView() {
    const k = this.looseOn ? 0.45 : SCALE[this.displayCat || "ring"], t = this.home().target;
    this.setAutoRotate(false); this.flyTo(t.clone().add(new THREE.Vector3(0, 70 * k, 0.01)), t.clone().add(new THREE.Vector3(0, 8, 0)));
  }
  sideView() {
    const k = this.looseOn ? 0.45 : SCALE[this.displayCat || "ring"], t = this.home().target;
    this.setAutoRotate(false); this.flyTo(t.clone().add(new THREE.Vector3(70 * k, 6, 0)), t.clone().add(new THREE.Vector3(0, 2, 0)));
  }

  // ------------------------------------------------------------------ frame loop
  private tick = () => {
    const dt = Math.min(this.clock.getDelta(), 0.05), t = this.clock.elapsedTime;
    if (this.tween) {
      const k = Math.min((performance.now() - this.tween.start) / this.tween.ms, 1), e = 1 - Math.pow(1 - k, 3);
      this.camera.position.lerpVectors(this.tween.p0, this.tween.p1, e);
      this.controls.target.lerpVectors(this.tween.t0, this.tween.t1, e);
      if (k >= 1) this.tween = null;
    }
    const mode = useApp.getState().wear.mode;
    if (mode === "ble" && live.q) {
      this.pivot.quaternion.slerp(live.q, 1 - Math.exp(-20 * dt));
    } else if (mode === "sim") {
      const prev = [sim.yaw, sim.pitch, sim.roll];
      if (sim.auto) { sim.yaw = 28 * Math.sin(t * 0.45); sim.pitch = 14 * Math.sin(t * 0.33 + 1); sim.roll = 22 * Math.sin(t * 0.27 + 2); }
      const D = THREE.MathUtils.degToRad;
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(D(sim.pitch), D(sim.yaw), D(sim.roll), "YXZ"));
      this.pivot.quaternion.slerp(q, 1 - Math.exp(-8 * dt));
      live.e = [sim.yaw, sim.pitch, sim.roll];
      live.g = [sim.pitch - prev[1], sim.yaw - prev[0], sim.roll - prev[2]].map((x) => x / Math.max(dt, 1e-3));
      const g = new THREE.Vector3(0, 1, 0).applyQuaternion(this.pivot.quaternion.clone().invert());
      live.a = [g.x, g.y, g.z];
      live.packets++;
    } else {
      this.pivot.quaternion.slerp(new THREE.Quaternion(), 1 - Math.exp(-6 * dt));
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.raf = requestAnimationFrame(this.tick);
  };
}

let current: Stage | null = null;
export const getStage = () => current;
export const setStage = (s: Stage | null) => { current = s; };

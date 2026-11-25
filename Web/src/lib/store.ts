// App state (zustand). Screens read from it; the 3D stage subscribes to it and follows the design.
import { create } from "zustand";
import type { Catalog, Category, Design, Meta, RingDef } from "./catalog";
import { DesignView, byId, categoryOf, loadCatalog } from "./catalog";

export type ViewId = "welcome" | "how-it-works" | "showroom" | "rings" | "gemstones" | "customise" | "inspect" | "summary"
  | "saved" | "wearable" | "photo" | "photo-piece" | "gallery";
export const VIEW_TITLES: Record<ViewId, string> = {
  welcome: "Welcome", "how-it-works": "How It Works", showroom: "The Showroom", rings: "Jewellery Designs", gemstones: "Gemstones",
  customise: "Customise", inspect: "Inspect", summary: "Design Summary", saved: "Saved Designs", wearable: "Wearable Device",
  photo: "From a Photo", "photo-piece": "From a Photo", gallery: "Gemstone Gallery",
};
const isView = (v: string): v is ViewId => v in VIEW_TITLES;

export interface WearState {
  mode: "off" | "sim" | "ble";
  status: "idle" | "connecting" | "live" | "reconnecting";
  deviceName: string | null;
}
export interface SavedDesign { name: string; savedAt: string; design: Design }
/** The loose stone shown in the Gemstone Gallery (separate from the design on display). */
export interface GalleryStone { gemId: string; shapeId: string; lengthMm: number; widthMm: number }

const CUSTOM_KEY = "gemxpert.customRings.v1";
const SAVE_KEY = "gemxpert.savedDesigns.v1";
const readLS = <T,>(key: string, fallback: T): T => {
  try { const v = JSON.parse(localStorage.getItem(key) || "null"); return v ?? fallback; } catch { return fallback; }
};
const writeLS = (key: string, v: unknown) => { try { localStorage.setItem(key, JSON.stringify(v)); } catch { /* private mode */ } };

interface AppState {
  cat: Catalog | null; meta: Meta | null; loadError: string | null;
  customRings: RingDef[]; draftRing: RingDef | null;
  customInfo: Record<string, { accentStones: number; accentSizeMm?: number }>;
  design: Design;
  gallery: GalleryStone;
  keepStone: boolean;             // set by the Gallery: settings chosen on Jewellery Designs keep that stone until you leave it
  category: Category;             // the jewellery type being browsed (follows the piece on the stand)
  ringVersion: number;            // bump to force the stage to rebuild the ring (custom draft edits)
  compare: Design[];
  saved: SavedDesign[];
  view: ViewId; history: ViewId[];
  toast: { msg: string; key: number } | null;
  onFinger: boolean; autoRotate: boolean; stageReady: boolean; stageError: string | null;
  wear: WearState;

  init(): Promise<void>;
  go(view: ViewId): void; back(): void; home(): void; syncFromHash(): void;
  showToast(msg: string): void;
  patchDesign(p: Partial<Design>): void;
  selectRing(id: string, announce?: boolean): void;
  setCategory(c: Category): void;
  setShape(id: string): void;
  restore(d: Design): void;
  addCompare(d?: Design): void;
  saveDesign(name: string): void; deleteSaved(i: number): void;
  setDraft(def: RingDef | null): void;
  addCustomRing(def: RingDef): void; removeCustomRing(id: string): void;
  setWear(p: Partial<WearState>): void;
  setGallery(p: Partial<GalleryStone>): void;
  gesture(kind: string): void;
}

export const useApp = create<AppState>()((set, get) => ({
  cat: null, meta: null, loadError: null,
  customRings: [], draftRing: null, customInfo: {},
  design: { ringId: "solitaire", gemId: "diamond", shapeId: "round", lengthMm: 6.5, widthMm: 6.5, seat: { x: 0, y: 0, z: 0 }, metalId: "yellow_gold" },
  gallery: { gemId: "blue_sapphire", shapeId: "oval", lengthMm: 8.0, widthMm: 6.0 }, keepStone: false,   // opens on a coloured stone
  category: "ring", ringVersion: 0, compare: [], saved: [],
  view: "welcome", history: [], toast: null,
  onFinger: false, autoRotate: true, stageReady: false, stageError: null,
  wear: { mode: "off", status: "idle", deviceName: null },

  async init() {
    try {
      const { cat, meta } = await loadCatalog();
      const customRings = readLS<RingDef[]>(CUSTOM_KEY, []).filter((r) => r && r.custom && (r.spec || r.pieceSpec));
      const saved = readLS<SavedDesign[]>(SAVE_KEY, []);
      set({ cat, meta, customRings, saved: Array.isArray(saved) ? saved : [] });
      get().selectRing("solitaire");
      // Every visit opens on the front page (Start Experience), even from a link to an inner page.
      if (location.hash && location.hash !== "#welcome") history.replaceState(null, "", location.pathname + location.search);
    } catch (e) {
      console.error(e);
      set({ loadError: "GemXpert couldn't load its catalogue. Reload the page to try again." });
    }
  },

  go(view) {
    const { view: cur, history } = get();
    if (view === cur) return;
    if (get().keepStone && view !== "rings") set({ keepStone: false });
    set({ history: [...history, cur], view });
    location.hash = view;
  },
  back() {
    if (get().keepStone) set({ keepStone: false });
    const h = [...get().history];
    const v = h.pop();
    if (!v) return;
    set({ history: h, view: v });
    location.hash = v;
  },
  home() { set({ history: [], view: "showroom", keepStone: false }); location.hash = "showroom"; },
  syncFromHash() {
    const v = location.hash.slice(1);
    const view = isView(v) ? v : "welcome";
    if (view !== get().view) set({ view });
  },

  showToast(msg) { set({ toast: { msg, key: Date.now() } }); },

  patchDesign(p) { set({ design: { ...get().design, ...p } }); },

  selectRing(id, announce = false) {
    const s = get();
    const r = allRings(s).find((x) => x.id === id);
    if (!r || !s.cat) return;
    const shape = byId(s.cat.shapes, r.defaultShapeId)!;
    const stone = r.custom ? (r.spec || r.pieceSpec)?.stone : undefined;
    const design: Design = {
      ringId: r.id, metalId: r.defaultMetalId, gemId: r.defaultGemstoneId, shapeId: r.defaultShapeId,
      lengthMm: stone ? stone.lengthMm : shape.defaultLengthMm,
      widthMm: stone ? stone.widthMm : shape.defaultWidthMm,
      seat: { x: 0, y: 0, z: 0 },
    };
    if (s.keepStone) {   // a stone picked in the Gemstone Gallery follows into the setting (the fit check flags it if it can't)
      const { gemId, shapeId, lengthMm, widthMm } = s.design;
      Object.assign(design, { gemId, shapeId, lengthMm, widthMm });
    }
    set({ design, category: categoryOf(r), ringVersion: s.ringVersion + 1 });
    if (announce) {
      const v = designView(get())!;
      get().showToast(`${r.displayName} with ${v.gem.displayName} ${v.shape.displayName.toLowerCase()} in ${v.metal.displayName}.`);
    }
  },

  setCategory(c) {
    const s = get();
    if (categoryOf(designView(s)!.ring) === c) { set({ category: c }); return; }
    const first = allRings(s).find((r) => categoryOf(r) === c);
    if (first) get().selectRing(first.id, true);
  },

  setShape(id) {
    const s = get(), shape = byId(s.cat!.shapes, id)!;
    get().patchDesign({ shapeId: id, lengthMm: shape.defaultLengthMm, widthMm: shape.defaultWidthMm, seat: { x: 0, y: 0, z: 0 } });
  },

  restore(d) { set({ design: { ...d, seat: { ...d.seat } } }); },

  addCompare(d) {
    const compare = [...get().compare, d || { ...get().design, seat: { ...get().design.seat } }].slice(-4);
    set({ compare });
    get().showToast(`Added to compare (${compare.length}/4).`);
  },

  saveDesign(name) {
    const saved = [{ name: name.trim() || "Untitled design", savedAt: new Date().toISOString(), design: { ...get().design } }, ...get().saved];
    set({ saved }); writeLS(SAVE_KEY, saved);
    get().showToast("Design saved.");
  },
  deleteSaved(i) { const saved = get().saved.filter((_, k) => k !== i); set({ saved }); writeLS(SAVE_KEY, saved); },

  setDraft(def) { set({ draftRing: def }); },
  addCustomRing(def) { const customRings = [...get().customRings, def]; set({ customRings, draftRing: null }); writeLS(CUSTOM_KEY, customRings); },
  removeCustomRing(id) {
    const customRings = get().customRings.filter((r) => r.id !== id);
    set({ customRings }); writeLS(CUSTOM_KEY, customRings);
    if (get().design.ringId === id) {   // fall back to the first catalogue piece of the same type
      const c = get().category;
      get().selectRing((get().cat!.rings.find((r) => categoryOf(r) === c) || get().cat!.rings[0]).id);
    }
  },

  setWear(p) { set({ wear: { ...get().wear, ...p } }); },
  setGallery(p) { set({ gallery: { ...get().gallery, ...p } }); },

  gesture(kind) {
    const s = get();
    if (s.wear.mode === "off") { s.showToast("Connect the wearable first."); return; }
    const cat = s.cat!;
    const cycle = (list: string[], cur: string) => list[(list.indexOf(cur) + 1) % list.length];
    if (kind === "tap") {
      s.patchDesign({ gemId: cycle(cat.gemstones.map((g) => g.id), s.design.gemId) });
      s.showToast(`Tap: ${designView(get())!.gem.displayName}`);
    } else if (kind === "double") {
      s.patchDesign({ metalId: cycle(cat.metals.map((m) => m.id), s.design.metalId) });
      s.showToast(`Double tap: ${designView(get())!.metal.displayName}`);
    } else if (kind === "swipe") {
      const list = [...cat.rings, ...s.customRings].filter((r) => categoryOf(r) === s.category);
      const keep = { gemId: s.design.gemId, metalId: s.design.metalId };
      s.selectRing(cycle(list.map((r) => r.id), s.design.ringId));
      s.patchDesign(keep);
      s.showToast(`Swipe: ${designView(get())!.ring.displayName}`);
    }
  },
}));

export function allRings(s: Pick<AppState, "cat" | "customRings" | "draftRing">): RingDef[] {
  return s.cat ? [...s.cat.rings, ...s.customRings, ...(s.draftRing ? [s.draftRing] : [])] : [];
}
export function designView(s: Pick<AppState, "cat" | "meta" | "customRings" | "draftRing" | "design">): DesignView | null {
  return s.cat && s.meta ? new DesignView(s.cat, s.meta, allRings(s), s.design) : null;
}
/** Hook: the derived design view, re-rendering when any of its inputs change. */
export function useDesignView(): DesignView {
  const cat = useApp((s) => s.cat), meta = useApp((s) => s.meta), customRings = useApp((s) => s.customRings);
  const draftRing = useApp((s) => s.draftRing), design = useApp((s) => s.design);
  return designView({ cat, meta, customRings, draftRing, design })!;
}

window.addEventListener("hashchange", () => useApp.getState().syncFromHash());

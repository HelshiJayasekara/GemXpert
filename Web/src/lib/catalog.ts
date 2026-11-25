// Catalogue types, loading and the design rules (fit check, carat estimate). Same rules as the Unity GemstoneFitManager.

export interface Vec3 { x: number; y: number; z: number }
export interface Mount {
  id: string; role: "center" | "side";
  supportedShapes: string[];
  minLengthMm: number; maxLengthMm: number; minWidthMm: number; maxWidthMm: number; maxDepthMm: number;
  adjustRangeMm: Vec3;
  fixedGemstoneId?: string; fixedShapeId?: string; fixedLengthMm?: number;
}
export interface RingSpec {
  specVersion: number; name: string; style: "solitaire" | "halo" | "three_stone" | "bezel";
  prongs: number; cathedral: boolean; headHeight: "low" | "medium" | "high"; innerDiameterMm: number;
  bandWidthMm: number; bandThicknessMm: number;
  stone: { gemId: string; shapeId: string; lengthMm: number; widthMm: number };
  metalId: string; halo: { accentSizeMm: number }; sideStones: { sizeMm: number };
}
export interface RingDef {
  id: string; displayName: string; settingStyle: string; description: string;
  innerDiameterMm: number; bandWidthMm: number; bandThicknessMm: number;
  defaultMetalId: string; defaultGemstoneId: string; defaultShapeId: string;
  metalRendererPrefixes: string[]; accentStoneRendererPrefixes?: string[];
  mounts: Mount[];
  custom?: boolean; spec?: RingSpec; source?: "photo" | "manual"; photo?: string | null;
}
export interface Gemstone {
  id: string; displayName: string; mineral: string; description: string; colorHex: string;
  refractiveIndex: number; dispersion: number; hardnessMohs: number;
}
export interface Shape {
  id: string; displayName: string; defaultLengthMm: number; defaultWidthMm: number; depthRatio: number;
  lockAspect: boolean; minLengthMm: number; maxLengthMm: number;
}
export interface Metal { id: string; displayName: string; colorHex: string; smoothness: number; description: string }
export interface Catalog { rings: RingDef[]; gemstones: Gemstone[]; shapes: Shape[]; metals: Metal[] }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Meta = { gemCuts: Record<string, any>; rings: Record<string, any> };

export interface Design {
  ringId: string; gemId: string; shapeId: string; lengthMm: number; widthMm: number; seat: Vec3; metalId: string;
}
export interface Fit { status: "ok" | "warn" | "bad"; title: string; reasons: string[] }

export const RING_FILES: Record<string, string> = {
  solitaire: "Ring_Solitaire", halo: "Ring_Halo", three_stone: "Ring_ThreeStone", prong: "Ring_Prong", bezel: "Ring_Bezel",
};
export const GEM_FILES: Record<string, string> = {
  round: "Gem_Round", oval: "Gem_Oval", cushion: "Gem_Cushion", pear: "Gem_Pear", emerald: "Gem_EmeraldCut", princess: "Gem_Princess",
};
// Specific gravity for carat estimates (diamond formulas scaled by SG / 3.52).
const SG: Record<string, number> = { blue_sapphire: 4.0, ruby: 4.0, yellow_sapphire: 4.0, emerald: 2.72, diamond: 3.52 };
// Standard jeweller's weight-estimation factors (diamond, mm -> ct).
const CARAT_K: Record<string, number> = { round: 0.0061, oval: 0.0062, cushion: 0.0081, pear: 0.006, emerald: 0.0092, princess: 0.0083 };

export async function loadCatalog(): Promise<{ cat: Catalog; meta: Meta }> {
  const get = async (p: string) => {
    const r = await fetch(p);
    if (!r.ok) throw new Error(`${p}: HTTP ${r.status}`);
    return r.json();
  };
  const [rings, gemstones, shapes, metals, meta] = await Promise.all(
    ["rings", "gemstones", "shapes", "metals", "asset_metadata"].map((n) => get(`/data/${n}.json`)));
  return { cat: { rings: rings.items, gemstones: gemstones.items, shapes: shapes.items, metals: metals.items }, meta };
}

export const byId = <T extends { id: string }>(list: T[], id: string): T | undefined => list.find((x) => x.id === id);
export const listJoin = (a: string[]) => (a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]);

/** Everything derived from the catalogue + current design, in one place for screens and the 3D stage. */
export class DesignView {
  constructor(public cat: Catalog, public meta: Meta, public rings: RingDef[], public d: Design) {}
  get ring(): RingDef { return this.rings.find((r) => r.id === this.d.ringId) || this.cat.rings[0]; }
  get gem(): Gemstone { return byId(this.cat.gemstones, this.d.gemId)!; }
  get shape(): Shape { return byId(this.cat.shapes, this.d.shapeId)!; }
  get metal(): Metal { return byId(this.cat.metals, this.d.metalId)!; }
  get centerMount(): Mount { return this.ring.mounts.find((m) => m.role === "center")!; }
  shapeDef(id: string) { return byId(this.cat.shapes, id)!; }
  depthRatio(shapeId: string): number { return this.meta.gemCuts?.[shapeId]?.depth_ratio ?? this.shapeDef(shapeId).depthRatio; }
  get depthMm() { return this.d.widthMm * this.depthRatio(this.d.shapeId); }
  get carat() {
    const { lengthMm: L, widthMm: W, shapeId, gemId } = this.d, D = this.depthMm, k = CARAT_K[shapeId];
    const base = shapeId === "round" || shapeId === "oval" ? ((L + W) / 2) ** 2 * D * k : L * W * D * k;
    return base * (SG[gemId] / 3.52);
  }
  headDefaults(r: RingDef = this.ring): { L: number; W: number } {
    if (r.custom && r.spec) return { L: r.spec.stone.lengthMm, W: r.spec.stone.widthMm };
    const c = this.meta.rings[r.id].mounts.Center;
    return { L: c.headDefaultLengthMm, W: c.headDefaultWidthMm };
  }
  fit(): Fit {
    const r = this.ring, m = this.centerMount, s = this.shape, g = this.gem;
    const L = this.d.lengthMm, W = this.d.widthMm, D = this.depthMm;
    if (!m.supportedShapes.includes(s.id)) {
      const names = m.supportedShapes.map((id) => this.shapeDef(id).displayName.toLowerCase());
      return { status: "bad", title: "Does not fit this setting", reasons: [`The ${r.displayName} setting holds ${listJoin(names)} stones only.`] };
    }
    const reasons: string[] = [];
    if (L < m.minLengthMm) reasons.push(`Too short: ${L.toFixed(1)} mm (needs at least ${m.minLengthMm} mm).`);
    if (L > m.maxLengthMm) reasons.push(`Too long: ${L.toFixed(1)} mm (the head takes up to ${m.maxLengthMm} mm).`);
    if (W < m.minWidthMm) reasons.push(`Too narrow: ${W.toFixed(1)} mm (needs at least ${m.minWidthMm} mm).`);
    if (W > m.maxWidthMm) reasons.push(`Too wide: ${W.toFixed(1)} mm (the head takes up to ${m.maxWidthMm} mm).`);
    if (D > m.maxDepthMm) reasons.push(`Too deep: ${D.toFixed(2)} mm total depth (maximum ${m.maxDepthMm} mm).`);
    if (reasons.length) return { status: "bad", title: "Does not fit this setting", reasons };
    const near: string[] = [], margin = 0.25;
    if (L - m.minLengthMm < margin || m.maxLengthMm - L < margin) near.push("Length is at the edge of what the head can hold.");
    if (W - m.minWidthMm < margin || m.maxWidthMm - W < margin) near.push("Width is at the edge of what the head can hold.");
    if (m.maxDepthMm - D < margin) near.push("Pavilion sits very close to the band.");
    if (g.hardnessMohs < 8 && (r.id === "solitaire" || r.id === "prong"))
      near.push(`${g.displayName} (${g.hardnessMohs} Mohs) is softer than corundum; a bezel or halo protects it better.`);
    if (near.length) return { status: "warn", title: "Fits, with a note", reasons: near };
    return { status: "ok", title: "Fits the setting", reasons: [] };
  }
  describe(d: Design) {
    const r = this.rings.find((x) => x.id === d.ringId) || { displayName: "Removed custom design" };
    const g = byId(this.cat.gemstones, d.gemId)!, s = byId(this.cat.shapes, d.shapeId)!, m = byId(this.cat.metals, d.metalId)!;
    return { title: `${r.displayName} · ${g.displayName}`, detail: `${s.displayName} ${d.lengthMm.toFixed(1)}×${d.widthMm.toFixed(1)} mm · ${m.displayName}`, color: g.colorHex };
  }
}

export const SHAPE_ICONS: Record<string, string> = {
  round: '<circle cx="17" cy="17" r="13"/><polygon points="17,7 26,17 17,27 8,17"/>',
  oval: '<ellipse cx="17" cy="17" rx="10" ry="14"/><polygon points="17,6 24,17 17,28 10,17"/>',
  cushion: '<rect x="4" y="4" width="26" height="26" rx="9"/><rect x="11" y="11" width="12" height="12" rx="3"/>',
  pear: '<path d="M17 31 C9 23 7 18 7 13 a10 10 0 0 1 20 0 c0 5 -2 10 -10 18z"/><polygon points="17,8 23,15 17,24 11,15"/>',
  emerald: '<polygon points="11,3 23,3 28,8 28,26 23,31 11,31 6,26 6,8"/><polygon points="13,9 21,9 22,10 22,24 21,25 13,25 12,24 12,10"/>',
  princess: '<rect x="5" y="5" width="24" height="24"/><path d="M5 5 L29 29 M29 5 L5 29"/>',
};
export const RING_ICON = "data:image/svg+xml," + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 92 74"><rect width="92" height="74" fill="#0d0c0f"/><circle cx="46" cy="44" r="17" fill="none" stroke="#C9A45C" stroke-width="3"/><path d="M38 27 L46 15 L54 27 Z" fill="none" stroke="#E6C983" stroke-width="2"/></svg>');

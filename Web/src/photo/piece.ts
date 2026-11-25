// "Design from a photo" for pendants, necklaces and bracelets. These pieces are Blender models, not a parametric generator,
// so the photo picks the closest catalogue piece and supplies the centre stone (gem, cut, size) and the metal.
import type { Catalog, Category, PieceSpec, RingDef } from "../lib/catalog";
import { CATEGORIES, PIECE_NOUN, byId, categoryOf } from "../lib/catalog";

const round1 = (v: number) => Math.round(v * 10) / 10;
const clampNum = (v: unknown, lo: number, hi: number, d: number) => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : d;
};

/** Catalogue pieces of one jewellery type that a photo design can build on. */
export const basesFor = (cat: Catalog, category: Category) => cat.rings.filter((r) => !r.custom && categoryOf(r) === category);
const centre = (r: RingDef) => r.mounts.find((m) => m.role === "center")!;

export function defaultPieceSpec(cat: Catalog, category: Category): PieceSpec {
  const base = basesFor(cat, category)[0], shape = byId(cat.shapes, base.defaultShapeId)!;
  return {
    specVersion: 1, category, name: `My ${PIECE_NOUN[category]}`, baseId: base.id, metalId: base.defaultMetalId,
    stone: { gemId: base.defaultGemstoneId, shapeId: base.defaultShapeId, lengthMm: shape.defaultLengthMm, widthMm: shape.defaultWidthMm },
  };
}

/** Clamps whatever came back (from Claude or the form) to what the chosen piece's centre head can hold. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizePieceSpec(cat: Catalog, category: Category, raw: any): PieceSpec {
  const d = defaultPieceSpec(cat, category), r = raw || {}, st = r.stone || {};
  const base = basesFor(cat, category).find((b) => b.id === r.baseId) || byId(cat.rings, d.baseId)!;
  const m = centre(base);
  const shapeId = m.supportedShapes.includes(st.shapeId) ? st.shapeId : m.supportedShapes.includes(d.stone.shapeId) ? d.stone.shapeId : base.defaultShapeId;
  const shape = byId(cat.shapes, shapeId)!;
  const lo = Math.max(shape.minLengthMm, m.minLengthMm), hi = Math.min(shape.maxLengthMm, m.maxLengthMm);
  let L = clampNum(st.lengthMm, lo, hi, Math.min(hi, Math.max(lo, shape.defaultLengthMm)));
  let W = clampNum(st.widthMm, m.minWidthMm, m.maxWidthMm, Math.min(m.maxWidthMm, Math.max(m.minWidthMm, shape.defaultWidthMm)));
  if (shape.lockAspect) { L = Math.min(L, m.maxWidthMm); W = L; }
  else if (W > L) [L, W] = [W, L];
  return {
    specVersion: 1, category, baseId: base.id,
    name: String(r.name || d.name).replace(/\s+/g, " ").trim().slice(0, 60) || d.name,
    stone: { gemId: cat.gemstones.some((g) => g.id === st.gemId) ? st.gemId : base.defaultGemstoneId, shapeId, lengthMm: round1(L), widthMm: round1(W) },
    metalId: cat.metals.some((x) => x.id === r.metalId) ? r.metalId : base.defaultMetalId,
  };
}

/** A custom piece: the base piece's definition (same model, mounts and accents) with the photo's stone, metal and name. */
export function makePieceDef(cat: Catalog, spec: PieceSpec, id: string,
  extra: { source?: "photo" | "manual"; photo?: string | null; description?: string } = {}): RingDef {
  const base = byId(cat.rings, spec.baseId)!;
  return {
    ...JSON.parse(JSON.stringify(base)), id, custom: true, baseId: base.id, pieceSpec: JSON.parse(JSON.stringify(spec)),
    source: extra.source || "manual", photo: extra.photo || null, displayName: spec.name,
    description: extra.description || `${extra.source === "photo" ? "Rebuilt from your photo" : "Designed by hand"} on the ${base.displayName} setting.`,
    defaultMetalId: spec.metalId, defaultGemstoneId: spec.stone.gemId, defaultShapeId: spec.stone.shapeId,
  };
}

export function piecePrompt(cat: Catalog, category: Category): string {
  const noun = PIECE_NOUN[category];
  const bases = basesFor(cat, category).map((b) => {
    const m = centre(b);
    return `- ${b.id}: ${b.displayName}. ${b.settingStyle}. ${b.description} Centre stone cuts: ${m.supportedShapes.join(", ")}; ${m.minLengthMm}-${m.maxLengthMm} mm long.`;
  }).join("\n");
  const gems = cat.gemstones.map((g) => `${g.id} (${g.displayName}, colour ${g.colorHex})`).join("; ");
  const cuts = cat.shapes.map((s) => `${s.id} (${s.displayName})`).join("; ");
  const metals = cat.metals.map((m) => `${m.id} (${m.displayName})`).join("; ");
  const scale = {
    ring: "",
    pendant: "If the photo has no scale reference, assume the chain is about 1.2 mm wide and the bail about 3 mm, and estimate the stone relative to them (a typical pendant stone is 5-9 mm).",
    necklace: "If the photo has no scale reference, assume a fine necklace chain is about 1.5 mm wide and estimate the centre stone relative to it (a typical centre drop is 5-9 mm).",
    bracelet: "If the photo has no scale reference, assume a bracelet is about 60 mm across inside and estimate the centre stone relative to it (a typical centre stone is 5-7 mm).",
    earring: "Describe ONE earring of the pair (both get the same stone). If the photo has no scale reference, assume an earring post or hook wire is about 0.8 mm thick and estimate the stone relative to it (a typical earring stone is 4-8 mm).",
  }[category];
  return [
    `You are helping a jewellery app rebuild a ${noun} from a customer's photo. The app has these settings for ${CATEGORIES.find((c) => c.id === category)!.plural.toLowerCase()}:`,
    bases,
    "",
    `Pick the setting closest to the ${noun} in the photo, then describe its centre stone and metal using ONLY the options below. Choose the closest option when unsure.`,
    "",
    "Reply with only one JSON object of this shape:",
    `{"matches": true, "name": "short descriptive name, at most 6 words", "baseId": string, "stone": {"gemId": string, "shapeId": string, "lengthMm": number, "widthMm": number}, "metalId": string, "confidence": "high" | "medium" | "low", "observations": [string], "notMatched": [string]}`,
    "",
    `baseId options: ${basesFor(cat, category).map((b) => b.id).join(", ")}.`,
    `gemId options: ${gems}.`,
    `shapeId options: ${cuts}.`,
    `metalId options: ${metals}.`,
    "stone is the main (largest or centre) stone. If there is no single centre stone, describe the most prominent one.",
    `All sizes are millimetres. ${scale} lengthMm must be >= widthMm.`,
    `observations: up to 5 short facts you used, e.g. "bezel-set stones spaced along the chain". notMatched: features of this ${noun} that the chosen setting does not have, e.g. "box chain", "two strands", "milgrain edge", "pearls"; empty if none.`,
    `If the image does not show a ${noun}, reply {"matches": false, "reason": "what the image shows"}.`,
  ].join("\n");
}

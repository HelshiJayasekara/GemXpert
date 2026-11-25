// Ring specs for "design from a photo": defaults, clamping to what the generator can build, and custom ring definitions.
import type { Catalog, Meta, RingDef, RingSpec } from "../lib/catalog";
import { byId } from "../lib/catalog";

const round1 = (v: number) => Math.round(v * 10) / 10;
const clampNum = (v: unknown, lo: number, hi: number, d: number) => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : d;
};
export const STYLE_TEXT: Record<RingSpec["style"], string> = { solitaire: "Solitaire", halo: "Halo", three_stone: "Three-stone", bezel: "Bezel" };

export function defaultSpec(): RingSpec {
  return {
    specVersion: 1, name: "My ring", style: "solitaire", prongs: 4, cathedral: false, headHeight: "medium", innerDiameterMm: 17.3,
    bandWidthMm: 2.0, bandThicknessMm: 1.7, stone: { gemId: "diamond", shapeId: "round", lengthMm: 6.5, widthMm: 6.5 },
    metalId: "yellow_gold", halo: { accentSizeMm: 1.3 }, sideStones: { sizeMm: 4.0 },
  };
}

/** Clamps whatever came back (from Claude or the form) to what the generator can build. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeSpec(cat: Catalog, raw: any): RingSpec {
  const d = defaultSpec(), r = raw || {}, st = r.stone || {};
  const style = (["solitaire", "halo", "three_stone", "bezel"].includes(r.style) ? r.style : d.style) as RingSpec["style"];
  const shapeId = cat.shapes.some((s) => s.id === st.shapeId) ? st.shapeId : d.stone.shapeId;
  const shape = byId(cat.shapes, shapeId)!;
  let L = clampNum(st.lengthMm, shape.minLengthMm, shape.maxLengthMm, shape.defaultLengthMm);
  let W = clampNum(st.widthMm, 3, 10, shape.defaultWidthMm);
  if (shape.lockAspect) W = L;
  else if (W > L) [L, W] = [W, L];
  return {
    specVersion: 1,
    name: String(r.name || d.name).replace(/\s+/g, " ").trim().slice(0, 60) || d.name,
    style,
    prongs: [4, 6, 8].includes(Number(r.prongs)) ? Number(r.prongs) : 4,
    cathedral: !!r.cathedral && (style === "solitaire" || style === "three_stone"),
    headHeight: ["low", "medium", "high"].includes(r.headHeight) ? r.headHeight : style === "bezel" ? "low" : "medium",
    innerDiameterMm: 17.3,
    bandWidthMm: round1(clampNum(r.bandWidthMm, 1.6, 3.5, d.bandWidthMm)),
    bandThicknessMm: round1(clampNum(r.bandThicknessMm, 1.5, 2.4, d.bandThicknessMm)),
    stone: { gemId: cat.gemstones.some((g) => g.id === st.gemId) ? st.gemId : d.stone.gemId, shapeId, lengthMm: round1(L), widthMm: round1(W) },
    metalId: cat.metals.some((m) => m.id === r.metalId) ? r.metalId : d.metalId,
    halo: { accentSizeMm: round1(clampNum(r.halo?.accentSizeMm, 1.0, 1.8, 1.3)) },
    sideStones: { sizeMm: round1(clampNum(r.sideStones?.sizeMm, 3.0, 5.0, 4.0)) },
  };
}

/** A custom ring definition shaped like a rings.json entry, so fit checks, customising and saving all work. */
export function makeRingDef(cat: Catalog, meta: Meta, spec: RingSpec, id: string,
  extra: { source?: "photo" | "manual"; photo?: string | null; description?: string } = {}): RingDef {
  const st = spec.stone, shape = byId(cat.shapes, st.shapeId)!;
  const depth = st.widthMm * (meta.gemCuts?.[st.shapeId]?.depth_ratio ?? shape.depthRatio);
  const style = {
    solitaire: `${spec.prongs}-prong solitaire${spec.cathedral ? " with cathedral shoulders" : ""}`,
    halo: "Halo with pave accent stones",
    three_stone: `Three-stone, ${spec.prongs}-prong centre${spec.cathedral ? ", cathedral shoulders" : ""}`,
    bezel: "Full bezel",
  }[spec.style];
  const mounts: RingDef["mounts"] = [{
    id: "Center", role: "center", supportedShapes: cat.shapes.map((s) => s.id),
    minLengthMm: round1(Math.max(shape.minLengthMm, st.lengthMm - 1.5)), maxLengthMm: round1(Math.min(shape.maxLengthMm, st.lengthMm + 1.5)),
    minWidthMm: round1(Math.max(3, st.widthMm - 1.2)), maxWidthMm: round1(st.widthMm + 1.2),
    maxDepthMm: Math.round((depth + 0.9) * 100) / 100,
    adjustRangeMm: spec.style === "bezel" ? { x: 0, y: 0.2, z: 0 } : { x: 0.3, y: 0.5, z: 0.3 },
  }];
  if (spec.style === "three_stone") {
    for (const sid of ["SideL", "SideR"]) {
      const s = spec.sideStones.sizeMm;
      mounts.push({ id: sid, role: "side", supportedShapes: ["round"], minLengthMm: s, maxLengthMm: s, minWidthMm: s, maxWidthMm: s,
        maxDepthMm: s, adjustRangeMm: { x: 0, y: 0, z: 0 }, fixedGemstoneId: "diamond", fixedShapeId: "round", fixedLengthMm: s });
    }
  }
  return {
    id, custom: true, spec: JSON.parse(JSON.stringify(spec)), source: extra.source || "manual", photo: extra.photo || null,
    displayName: spec.name, settingStyle: style,
    description: extra.description || (extra.source === "photo" ? "Rebuilt from your photo." : "Designed by hand."),
    innerDiameterMm: spec.innerDiameterMm, bandWidthMm: spec.bandWidthMm, bandThicknessMm: spec.bandThicknessMm,
    defaultMetalId: spec.metalId, defaultGemstoneId: st.gemId, defaultShapeId: st.shapeId,
    metalRendererPrefixes: ["Band", "Head", "Prong", "Halo", "Gallery", "Bezel", "Cathedral"], accentStoneRendererPrefixes: ["Accent"], mounts,
  };
}

export function photoPrompt(cat: Catalog): string {
  const gems = cat.gemstones.map((g) => `${g.id} (${g.displayName}, colour ${g.colorHex})`).join("; ");
  const cuts = cat.shapes.map((s) => `${s.id} (${s.displayName})`).join("; ");
  const metals = cat.metals.map((m) => `${m.id} (${m.displayName})`).join("; ");
  return [
    "You are helping a jewellery app rebuild a ring from a customer's photo with a parametric 3D ring generator.",
    "Look at the attached photo and describe the ring using ONLY the options below. Choose the closest option when unsure.",
    "",
    "Reply with only one JSON object of this shape:",
    '{"isRing": true, "name": "short descriptive name, at most 6 words", "style": "solitaire" | "halo" | "three_stone" | "bezel", "prongs": 4 | 6 | 8, "cathedral": true | false, "headHeight": "low" | "medium" | "high", "bandWidthMm": number, "bandThicknessMm": number, "stone": {"gemId": string, "shapeId": string, "lengthMm": number, "widthMm": number}, "metalId": string, "halo": {"accentSizeMm": number}, "sideStones": {"sizeMm": number}, "confidence": "high" | "medium" | "low", "observations": [string], "notMatched": [string]}',
    "",
    `gemId options: ${gems}.`,
    `shapeId options: ${cuts}.`,
    `metalId options: ${metals}.`,
    "style: solitaire = one centre stone held by prongs; halo = centre stone surrounded by a ring of small stones; three_stone = a centre stone with one smaller stone on each side; bezel = a metal rim around the whole stone.",
    "prongs = claws holding the centre stone (ignored for halo and bezel). cathedral = arched shoulders rising from the band up to the head. headHeight = how high the stone sits above the band.",
    "All sizes are millimetres. If the photo has no scale reference, assume the band is about 2 mm wide and estimate the stone relative to it (a typical centre stone is 5-9 mm). lengthMm must be >= widthMm.",
    'observations: up to 5 short facts you used, e.g. "six round-tipped prongs". notMatched: design features these options cannot express, e.g. "twisted band", "milgrain edge", "pave stones along the band"; empty if none.',
    'If the image does not show a ring, reply {"isRing": false, "reason": "what the image shows"}.',
  ].join("\n");
}

export function specForExport(spec: RingSpec, fromPhoto: boolean) {
  return JSON.stringify({ ...spec, id: "custom-" + (spec.name || "ring").toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    source: fromPhoto ? "photo" : "manual" }, null, 2);
}

import { useEffect, useRef, useState } from "react";
import { RING_ICON, byId, type RingSpec } from "../lib/catalog";
import { useApp } from "../lib/store";
import { ANALYSIS_ERRORS, AnalysisError, analyse, makeThumb, photoStatus } from "../photo/analyse";
import { STYLE_TEXT, defaultSpec, makeRingDef, normalizeSpec, photoPrompt, specForExport } from "../photo/spec";
import { ConfirmRow } from "../ui";

// Kept across visits to the screen (module state, like the original page).
const photo = {
  file: null as File | null, url: null as string | null, thumb: null as string | null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result: null as any, spec: null as RingSpec | null, message: "", kind: "" as "" | "ok" | "bad",
};
let statusPromise: ReturnType<typeof photoStatus> | null = null;

export function Photo() {
  const cat = useApp((s) => s.cat)!, meta = useApp((s) => s.meta)!, customRings = useApp((s) => s.customRings);
  const ringId = useApp((s) => s.design.ringId);
  const app = useApp.getState();
  const [, rerender] = useState(0);
  const refresh = () => rerender((n) => n + 1);
  const [avail, setAvail] = useState<{ available: boolean; reason: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<string | null>(null);
  const [specText, setSpecText] = useState<string | null>(null);
  const ctl = useRef<AbortController | null>(null);
  const draftTimer = useRef<number | undefined>(undefined);

  if (!photo.spec) photo.spec = normalizeSpec(cat, defaultSpec());
  const s = photo.spec, prongStyle = s.style === "solitaire" || s.style === "three_stone";
  const shape = byId(cat.shapes, s.stone.shapeId)!;

  useEffect(() => { (statusPromise ??= photoStatus()).then(setAvail); }, []);

  const previewDraft = (source?: "photo" | "manual") => {
    const def = makeRingDef(cat, meta, photo.spec!, "custom-draft", { source: source || (photo.result ? "photo" : "manual"), photo: photo.thumb });
    app.setDraft(def);
    app.selectRing(def.id);
  };

  const update = (next: RingSpec) => {
    const cutChanged = next.stone.shapeId !== photo.spec!.stone.shapeId;
    if (cutChanged) { const sd = byId(cat.shapes, next.stone.shapeId)!; next.stone.lengthMm = sd.defaultLengthMm; next.stone.widthMm = sd.defaultWidthMm; }
    photo.spec = normalizeSpec(cat, next);
    refresh();
    if (useApp.getState().design.ringId === "custom-draft") {
      clearTimeout(draftTimer.current);
      draftTimer.current = window.setTimeout(() => previewDraft(), 220);
    }
  };
  const set = (p: Partial<RingSpec>) => update({ ...s, ...p, stone: { ...s.stone }, halo: { ...s.halo }, sideStones: { ...s.sideStones } });
  const setStone = (p: Partial<RingSpec["stone"]>) => update({ ...s, stone: { ...s.stone, ...p } });

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    if (photo.url) URL.revokeObjectURL(photo.url);
    photo.file = file; photo.url = URL.createObjectURL(file); photo.thumb = await makeThumb(file);
    photo.result = null; photo.message = ""; photo.kind = "";
    refresh();
  };

  const run = async () => {
    if (!photo.file) return;
    setBusy(true);
    photo.message = "Reading the design... this usually takes 10-40 seconds."; photo.kind = "";
    ctl.current = new AbortController();
    try {
      const raw = await analyse(photo.file, photoPrompt(cat), ctl.current.signal);
      if (!raw || raw.isRing === false) {
        photo.result = null;
        photo.message = `This photo doesn't seem to show a ring${raw?.reason ? `: ${raw.reason}` : "."} Try a clear photo of a single ring.`;
        photo.kind = "bad";
      } else {
        photo.result = raw;
        photo.spec = normalizeSpec(cat, raw);
        photo.message = "Design read from your photo. Check the details below, adjust anything, then save it.";
        photo.kind = "ok";
        previewDraft("photo");
      }
    } catch (e) {
      const code = e instanceof AnalysisError ? e.code : "server_error";
      if (code === "cancelled") { photo.message = "Stopped."; photo.kind = ""; }
      else { photo.message = ANALYSIS_ERRORS[code] || "Something went wrong while reading the photo. Try again."; photo.kind = "bad"; }
    } finally {
      ctl.current = null; setBusy(false);
    }
  };

  const save = () => {
    const def = makeRingDef(cat, meta, photo.spec!, "custom-" + Date.now().toString(36), {
      source: photo.result ? "photo" : "manual", photo: photo.thumb,
      description: photo.result?.observations?.length ? `Rebuilt from your photo: ${photo.result.observations.slice(0, 3).join("; ")}.` : undefined,
    });
    app.addCustomRing(def);
    app.selectRing(def.id);
    app.showToast(`Saved "${def.displayName}" to your designs.`);
  };

  const copySpec = async () => {
    const text = specForExport(photo.spec!, !!photo.result);
    try { await navigator.clipboard.writeText(text); app.showToast("Spec copied. Save it as a .json file for build_custom.py."); }
    catch { setSpecText(text); }
  };
  const downloadSpec = () => {
    const name = (photo.spec!.name || "ring").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "ring";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([specForExport(photo.spec!, !!photo.result)], { type: "application/json" }));
    a.download = `gemxpert_${name}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };

  const SLIDER_SET = {
    len: (x: number) => setStone({ lengthMm: x }), wid: (x: number) => setStone({ widthMm: x }),
    bandW: (x: number) => set({ bandWidthMm: x }), bandT: (x: number) => set({ bandThicknessMm: x }),
    accent: (x: number) => set({ halo: { accentSizeMm: x } }), side: (x: number) => set({ sideStones: { sizeMm: x } }),
  };
  type SliderRow = [keyof typeof SLIDER_SET, string, number, number, number];
  const sliders: SliderRow[] = [
    ["len", "Stone length", s.stone.lengthMm, shape.minLengthMm, shape.maxLengthMm],
    ["wid", "Stone width", s.stone.widthMm, 3, 10],
    ["bandW", "Band width", s.bandWidthMm, 1.6, 3.5],
    ["bandT", "Band thickness", s.bandThicknessMm, 1.5, 2.4],
    ...(s.style === "halo" ? [["accent", "Halo stone size", s.halo.accentSizeMm, 1.0, 1.8] as SliderRow] : []),
    ...(s.style === "three_stone" ? [["side", "Side stone size", s.sideStones.sizeMm, 3, 5] as SliderRow] : []),
  ];

  return (
    <>
      <p className="lede">Upload a photo of a ring. Claude reads the setting, prongs, stone, metal and band, and GemXpert rebuilds it as a 3D ring you can customise like any other.</p>
      <label className="drop">
        {photo.url ? <img src={photo.url} alt="Your ring photo" />
          : <span>Choose a ring photo<br /><small>JPEG, PNG or WebP · a clear, well-lit photo of one ring works best</small></span>}
        <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" className="sr-only" onChange={(e) => onFile(e.target.files?.[0])} />
      </label>
      <div className="row">
        <button className="btn primary" style={{ flex: 1 }} disabled={!photo.file || busy || avail?.available !== true} onClick={run}>{busy ? "Analysing..." : "Analyse photo"}</button>
        {busy && <button className="btn" onClick={() => ctl.current?.abort()}>Stop</button>}
      </div>
      {avail === null && <p className="note">Checking whether photo analysis is available...</p>}
      {avail?.available === false && <p className="note">{avail.reason} You can still build the design by hand below.</p>}
      {photo.message && <div className={`fitbox ${photo.kind}`} role="status"><b>{photo.message}</b></div>}
      {photo.result && (
        <div className="findings">
          <span className="eyebrow">What Claude saw · confidence {photo.result.confidence || "unknown"}</span>
          <ul>{(photo.result.observations || []).slice(0, 5).map((o: string) => <li key={o}>{o}</li>)}</ul>
          {(photo.result.notMatched || []).length > 0 && <>
            <span className="eyebrow">Can't be reproduced yet</span>
            <ul className="warn">{photo.result.notMatched.slice(0, 5).map((o: string) => <li key={o}>{o}</li>)}</ul>
          </>}
        </div>
      )}

      <h2 className="section">Design</h2>
      <div className="form">
        <label>Name<input type="text" maxLength={60} value={s.name} onChange={(e) => set({ name: e.target.value })} /></label>
        <label>Setting<select value={s.style} onChange={(e) => set({ style: e.target.value as RingSpec["style"] })}>
          {Object.entries(STYLE_TEXT).map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select></label>
        <label>Prongs<select value={s.prongs} disabled={!prongStyle} onChange={(e) => set({ prongs: Number(e.target.value) })}>
          {[4, 6, 8].map((n) => <option key={n} value={n}>{n} prongs</option>)}</select></label>
        <label>Stone height<select value={s.headHeight} onChange={(e) => set({ headHeight: e.target.value as RingSpec["headHeight"] })}>
          {[["low", "Low"], ["medium", "Medium"], ["high", "High"]].map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select></label>
        <label className="check"><input type="checkbox" checked={s.cathedral} disabled={!prongStyle} onChange={(e) => set({ cathedral: e.target.checked })} /> Cathedral shoulders</label>
        <label>Gemstone<select value={s.stone.gemId} onChange={(e) => setStone({ gemId: e.target.value })}>
          {cat.gemstones.map((g) => <option key={g.id} value={g.id}>{g.displayName}</option>)}</select></label>
        <label>Cut<select value={s.stone.shapeId} onChange={(e) => setStone({ shapeId: e.target.value })}>
          {cat.shapes.map((c) => <option key={c.id} value={c.id}>{c.displayName}</option>)}</select></label>
        <label>Metal<select value={s.metalId} onChange={(e) => set({ metalId: e.target.value })}>
          {cat.metals.map((m) => <option key={m.id} value={m.id}>{m.displayName}</option>)}</select></label>
      </div>
      {sliders.map(([id, label, value, lo, hi]) => (
        <div className="field" key={id}>
          <div className="field-top"><label htmlFor={`f-${id}`}>{label}</label><span className="val">{value.toFixed(1)} mm</span></div>
          <input type="range" id={`f-${id}`} min={lo} max={hi} step={0.1} value={value} disabled={id === "wid" && shape.lockAspect}
            onChange={(e) => SLIDER_SET[id](Number(e.target.value))} />
        </div>
      ))}
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => previewDraft()}>Show on the stand</button>
        <button className="btn primary" style={{ flex: 1 }} onClick={save}>Save to my designs</button>
      </div>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={downloadSpec}>Download spec for Blender</button>
        <button className="btn" style={{ flex: 1 }} onClick={copySpec}>Copy spec (JSON)</button>
      </div>
      {specText && <pre className="packet">{specText}</pre>}
      <p className="note">The spec builds the same ring in Blender for the Unity app: <code>build_custom.py -- spec.json</code>.</p>

      <h2 className="section">Your designs</h2>
      <div className="saved">
        {!customRings.length && <div className="empty">Designs you save here appear in Ring Designs too.</div>}
        {customRings.map((r) => (
          <div key={r.id} className="saved-item">
            <div className="row" style={{ alignItems: "center", flexWrap: "nowrap" }}>
              <img src={r.photo || RING_ICON} alt="" style={{ width: 56, height: 46, objectFit: "cover", borderRadius: 8 }} />
              <div style={{ minWidth: 0 }}><b>{r.displayName}</b>{r.id === ringId && <span className="hint"> · on the stand</span>}<br />
                <small>{r.settingStyle} · {byId(cat.gemstones, r.defaultGemstoneId)?.displayName}</small></div>
            </div>
            {confirm === r.id
              ? <ConfirmRow question="Remove this design?" yes="Remove" onYes={() => { app.removeCustomRing(r.id); setConfirm(null); }} onNo={() => setConfirm(null)} />
              : <div className="row">
                  <button className="btn" style={{ flex: 1 }} onClick={() => app.selectRing(r.id, true)}>Show</button>
                  <button className="btn" style={{ flex: 1 }} onClick={() => setConfirm(r.id)}>Remove</button>
                </div>}
          </div>
        ))}
      </div>
    </>
  );
}

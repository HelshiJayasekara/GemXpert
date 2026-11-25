import { useEffect, useRef, useState } from "react";
import { CATEGORIES, PIECE_NOUN, byId, pieceFile, type Category, type PieceSpec } from "../lib/catalog";
import { useApp } from "../lib/store";
import { ANALYSIS_ERRORS, AnalysisError, analyse, makeThumb, photoStatus } from "../photo/analyse";
import { basesFor, defaultPieceSpec, makePieceDef, normalizePieceSpec, piecePrompt } from "../photo/piece";
import { ConfirmRow } from "../ui";

// One photo session per jewellery type, kept across visits to the screen.
type Session = {
  file: File | null; url: string | null; thumb: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result: any; spec: PieceSpec | null; message: string; kind: "" | "ok" | "bad";
};
const sessions: Partial<Record<Category, Session>> = {};
let statusPromise: ReturnType<typeof photoStatus> | null = null;

/** "Design from a photo" for pendants, necklaces and bracelets (rings have their own screen, Photo.tsx). */
export function PhotoPiece() {
  const cat = useApp((s) => s.cat)!, category = useApp((s) => s.category), customRings = useApp((s) => s.customRings);
  const ringId = useApp((s) => s.design.ringId);
  const app = useApp.getState();
  const kind: Category = category === "ring" ? "necklace" : category;
  const noun = PIECE_NOUN[kind], info = CATEGORIES.find((c) => c.id === kind)!;
  const photo = (sessions[kind] ??= { file: null, url: null, thumb: null, result: null, spec: null, message: "", kind: "" });
  const [, rerender] = useState(0);
  const refresh = () => rerender((n) => n + 1);
  const [avail, setAvail] = useState<{ available: boolean; reason: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<string | null>(null);
  const ctl = useRef<AbortController | null>(null);
  const draftTimer = useRef<number | undefined>(undefined);

  if (!photo.spec) photo.spec = defaultPieceSpec(cat, kind);
  const s = photo.spec, base = byId(cat.rings, s.baseId)!, m = base.mounts.find((x) => x.role === "center")!;
  const shape = byId(cat.shapes, s.stone.shapeId)!;
  const lenLo = Math.max(shape.minLengthMm, m.minLengthMm), lenHi = Math.min(shape.maxLengthMm, m.maxLengthMm);

  useEffect(() => { (statusPromise ??= photoStatus()).then(setAvail); }, []);
  useEffect(() => { if (kind !== category) app.setCategory(kind); }, [kind, category, app]);   // opened by link: show a necklace

  const previewDraft = (source?: "photo" | "manual") => {
    const def = makePieceDef(cat, photo.spec!, "custom-draft", { source: source || (photo.result ? "photo" : "manual"), photo: photo.thumb });
    app.setDraft(def);
    app.selectRing(def.id);
  };

  const update = (next: PieceSpec) => {
    if (next.stone.shapeId !== photo.spec!.stone.shapeId) {
      const sd = byId(cat.shapes, next.stone.shapeId)!;
      next.stone.lengthMm = sd.defaultLengthMm; next.stone.widthMm = sd.defaultWidthMm;
    }
    photo.spec = normalizePieceSpec(cat, kind, next);
    refresh();
    if (useApp.getState().design.ringId === "custom-draft") {
      clearTimeout(draftTimer.current);
      draftTimer.current = window.setTimeout(() => previewDraft(), 220);
    }
  };
  const set = (p: Partial<PieceSpec>) => update({ ...s, ...p, stone: { ...s.stone } });
  const setStone = (p: Partial<PieceSpec["stone"]>) => update({ ...s, stone: { ...s.stone, ...p } });

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
    refresh();
    ctl.current = new AbortController();
    try {
      const raw = await analyse(photo.file, piecePrompt(cat, kind), ctl.current.signal);
      if (!raw || raw.matches === false) {
        photo.result = null;
        photo.message = `This photo doesn't seem to show a ${noun}${raw?.reason ? `: ${raw.reason}` : "."} Try a clear photo of a single ${noun}.`;
        photo.kind = "bad";
      } else {
        photo.result = raw;
        photo.spec = normalizePieceSpec(cat, kind, raw);
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
    const def = makePieceDef(cat, photo.spec!, "custom-" + Date.now().toString(36), {
      source: photo.result ? "photo" : "manual", photo: photo.thumb,
      description: photo.result?.observations?.length ? `Rebuilt from your photo: ${photo.result.observations.slice(0, 3).join("; ")}.` : undefined,
    });
    app.addCustomRing(def);
    app.selectRing(def.id);
    app.showToast(`Saved "${def.displayName}" to your designs.`);
  };

  const mine = customRings.filter((r) => r.pieceSpec?.category === kind);

  return (
    <>
      <p className="lede">Upload a photo of a {noun}. Claude reads its style, centre stone and metal, and GemXpert rebuilds it on the closest GemXpert {info.label.toLowerCase()} setting, ready to customise like any other.</p>
      <label className="drop">
        {photo.url ? <img src={photo.url} alt="Your photo" />
          : <span>Choose a photo of a {noun}<br /><small>JPEG, PNG or WebP · a clear, well-lit photo of one {noun} works best</small></span>}
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
            <span className="eyebrow">Not on the {base.displayName} setting</span>
            <ul className="warn">{photo.result.notMatched.slice(0, 5).map((o: string) => <li key={o}>{o}</li>)}</ul>
          </>}
        </div>
      )}

      <h2 className="section">Design</h2>
      <div className="form">
        <label>Name<input type="text" maxLength={60} value={s.name} onChange={(e) => set({ name: e.target.value })} /></label>
        <label>Setting<select value={s.baseId} onChange={(e) => set({ baseId: e.target.value })}>
          {basesFor(cat, kind).map((b) => <option key={b.id} value={b.id}>{b.displayName}</option>)}</select></label>
        <label>Gemstone<select value={s.stone.gemId} onChange={(e) => setStone({ gemId: e.target.value })}>
          {cat.gemstones.map((g) => <option key={g.id} value={g.id}>{g.displayName}</option>)}</select></label>
        <label>Cut<select value={s.stone.shapeId} onChange={(e) => setStone({ shapeId: e.target.value })}>
          {cat.shapes.filter((c) => m.supportedShapes.includes(c.id)).map((c) => <option key={c.id} value={c.id}>{c.displayName}</option>)}</select></label>
        <label>Metal<select value={s.metalId} onChange={(e) => set({ metalId: e.target.value })}>
          {cat.metals.map((x) => <option key={x.id} value={x.id}>{x.displayName}</option>)}</select></label>
      </div>
      <p className="note">{base.settingStyle}. {base.description}</p>
      <div className="field">
        <div className="field-top"><label htmlFor="pp-len">Stone length</label><span className="val">{s.stone.lengthMm.toFixed(1)} mm</span></div>
        <input type="range" id="pp-len" min={lenLo} max={lenHi} step={0.1} value={s.stone.lengthMm}
          onChange={(e) => { const x = Number(e.target.value); setStone(shape.lockAspect ? { lengthMm: x, widthMm: x } : { lengthMm: x }); }} />
      </div>
      <div className="field">
        <div className="field-top"><label htmlFor="pp-wid">Stone width</label><span className="val">{s.stone.widthMm.toFixed(1)} mm</span></div>
        <input type="range" id="pp-wid" min={m.minWidthMm} max={m.maxWidthMm} step={0.1} value={s.stone.widthMm} disabled={shape.lockAspect}
          onChange={(e) => setStone({ widthMm: Number(e.target.value) })} />
      </div>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => previewDraft()}>Show on the display</button>
        <button className="btn primary" style={{ flex: 1 }} onClick={save}>Save to my designs</button>
      </div>

      <h2 className="section">Your {info.plural.toLowerCase()}</h2>
      <div className="saved">
        {!mine.length && <div className="empty">{info.plural} you save here appear in Jewellery Designs too.</div>}
        {mine.map((r) => (
          <div key={r.id} className="saved-item">
            <div className="row" style={{ alignItems: "center", flexWrap: "nowrap" }}>
              <img src={r.photo || `/renders/${pieceFile(r)}.png`} alt="" style={{ width: 56, height: 46, objectFit: "cover", borderRadius: 8 }} />
              <div style={{ minWidth: 0 }}><b>{r.displayName}</b>{r.id === ringId && <span className="hint"> · on display</span>}<br />
                <small>{byId(cat.rings, r.baseId!)?.displayName} · {byId(cat.gemstones, r.defaultGemstoneId)?.displayName}</small></div>
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

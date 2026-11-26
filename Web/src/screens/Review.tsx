import { useState } from "react";
import { CATEGORIES, PIECE_NOUN, baseOf, categoryOf } from "../lib/catalog";
import { useApp, useDesignView } from "../lib/store";
import { getStage } from "../three/stage";
import { ConfirmRow, FitBox, GoButton, Swatch } from "../ui";

export function Inspect() {
  const v = useDesignView(), compare = useApp((s) => s.compare), onFinger = useApp((s) => s.onFinger);
  const { addCompare, restore } = useApp.getState();
  const current = JSON.stringify(v.d);
  return (
    <>
      <p className="lede">Drag to turn the {PIECE_NOUN[categoryOf(v.ring)]}, scroll to zoom, or use the controls under the stage. The GemXpert wearable can turn it for you.</p>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.closeUp()}>Close-up stone</button>
        {categoryOf(v.ring) === "ring" && <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.setFinger(!onFinger)}>{onFinger ? "Back to stand" : "Show on hand"}</button>}
      </div>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.topView()}>Top view</button>
        <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.sideView()}>Side profile</button>
        <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.resetView()}>Reset view</button>
      </div>
      <h2 className="section">Compare designs</h2>
      <div className="compare">
        {!compare.length && <div className="empty" style={{ width: "100%" }}>Add up to four designs, then tap one to switch the stand to it. Try the same setting with two different stones.</div>}
        {compare.map((d, i) => {
          const info = v.describe(d);
          return (
            <button key={i} className={`cmp${JSON.stringify(d) === current ? " active" : ""}`} onClick={() => restore(d)}>
              <Swatch hex={info.color} /><span><b>{info.title}</b><br /><span className="hint">{info.detail}</span></span>
            </button>
          );
        })}
      </div>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => addCompare()}>Add current design</button>
        <GoButton to="summary" primary style={{ flex: 1 }}>Design summary</GoButton>
      </div>
    </>
  );
}

export function Summary() {
  const v = useDesignView(), r = v.ring, g = v.gem, s = v.shape, m = v.metal, f = v.fit(), cm = v.centerMount, d = v.d;
  const customInfo = useApp((st) => st.customInfo), meta = useApp((st) => st.meta)!;
  const extras = r.custom && r.spec ? customInfo[r.id] || { accentStones: 0 } : meta.rings[baseOf(r)];
  const side = r.mounts.find((x) => x.role === "side");
  const [name, setName] = useState(`${g.displayName} ${r.displayName}`);
  const save = () => { useApp.getState().saveDesign(name); useApp.getState().go("saved"); };
  return (
    <>
      <FitBox v={v} />
      <dl className="spec">
        <dt>{CATEGORIES.find((c) => c.id === categoryOf(r))!.label} design</dt><dd>{r.displayName}</dd>
        <dt>Setting</dt><dd>{r.settingStyle}</dd>
        <dt>Gemstone</dt><dd>{g.displayName} ({g.mineral})</dd>
        <dt>Cut</dt><dd>{s.displayName}</dd>
        <dt>Dimensions</dt><dd className="mono">{d.lengthMm.toFixed(1)} × {d.widthMm.toFixed(1)} × {v.depthMm.toFixed(2)} mm</dd>
        <dt>Est. weight</dt><dd className="mono">≈ {v.carat.toFixed(2)} ct{categoryOf(r) === "earring" ? ` each · ≈ ${(v.carat * 2).toFixed(2)} ct the pair` : ""}</dd>
        {categoryOf(r) === "earring" && <><dt>Pair</dt><dd>Two matched {g.displayName.toLowerCase()} stones, one in each earring</dd></>}
        <dt>Seat offset</dt><dd className="mono">height {d.seat.y.toFixed(2)} mm · side {d.seat.x.toFixed(2)} mm</dd>
        <dt>Metal</dt><dd>{m.displayName}</dd>
        {categoryOf(r) === "ring" && <><dt>Ring size</dt><dd className="mono">{r.innerDiameterMm} mm inner diameter</dd></>}
        {r.chainLengthMm && <><dt>Length</dt><dd className="mono">{r.chainLengthMm} mm ({(r.chainLengthMm / 25.4).toFixed(0)} in)</dd></>}
        {r.innerWidthMm && <><dt>Inside size</dt><dd className="mono">{r.innerWidthMm} × {r.innerHeightMm} mm</dd></>}
        {side && <><dt>Side stones</dt><dd className="mono">2 × round diamond-style {side.fixedLengthMm} mm</dd></>}
        {extras?.accentStones > 0 && <><dt>{["halo", "pendant_halo", "earring_halo"].includes(baseOf(r)) || (r.custom && r.spec) ? "Halo" : "Accent stones"}</dt><dd className="mono">{extras.accentStones}{extras.accentSizeMm ? ` × ${extras.accentSizeMm} mm` : " graduated"} accent stones</dd></>}
        {r.baseId && <><dt>Based on</dt><dd>{v.cat.rings.find((x) => x.id === r.baseId)?.displayName ?? r.baseId}</dd></>}
        {r.custom && <><dt>Origin</dt><dd>{r.source === "photo" ? "Rebuilt from your photo" : "Designed by hand"}</dd></>}
        <dt>Head accepts</dt><dd className="mono">{cm.minLengthMm}-{cm.maxLengthMm} × {cm.minWidthMm}-{cm.maxWidthMm} mm</dd>
      </dl>
      <div className="field">
        <label htmlFor="dname">Design name</label>
        <input id="dname" type="text" className="text-in" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <button className="btn primary block" disabled={f.status === "bad"} onClick={save}>Save design</button>
      {f.status === "bad" && <p className="note">This stone does not fit the setting yet. Adjust it in Customise before saving.</p>}
    </>
  );
}

export function Saved() {
  const v = useDesignView(), saved = useApp((s) => s.saved);
  const [confirm, setConfirm] = useState<number | null>(null);
  const app = useApp.getState();
  if (!saved.length) {
    return (
      <>
        <div className="empty">No saved designs yet. Build one, then use <b>Save design</b> on the Design Summary.</div>
        <GoButton to="summary" primary block>Go to Design Summary</GoButton>
      </>
    );
  }
  return (
    <>
      <div className="saved">
        {saved.map((item, i) => {
          const info = v.describe(item.design);
          return (
            <div key={item.savedAt + i} className="saved-item">
              <div><b>{item.name}</b><br /><small>{info.title} · {info.detail}</small><br /><small>Saved {new Date(item.savedAt).toLocaleString()}</small></div>
              {confirm === i
                ? <ConfirmRow question="Delete this design?" yes="Delete" onYes={() => { app.deleteSaved(i); setConfirm(null); }} onNo={() => setConfirm(null)} />
                : <div className="row">
                    <button className="btn" style={{ flex: 1 }} onClick={() => { app.restore(item.design); app.showToast("Design restored."); app.go("summary"); }}>Restore</button>
                    <button className="btn" style={{ flex: 1 }} onClick={() => { app.addCompare(item.design); app.go("inspect"); }}>Compare</button>
                    <button className="btn" style={{ flex: 1 }} onClick={() => setConfirm(i)}>Delete</button>
                  </div>}
            </div>
          );
        })}
      </div>
      <p className="note">Saved designs stay in this browser on this device.</p>
    </>
  );
}

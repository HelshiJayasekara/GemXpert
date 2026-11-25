import { RING_FILES, RING_ICON, SHAPE_ICONS, listJoin } from "../lib/catalog";
import { useApp, useDesignView } from "../lib/store";
import { FitBox, GoButton, Slider, Swatch, cssVars, rangeTrack } from "../ui";

export function Rings() {
  const cat = useApp((s) => s.cat)!, customRings = useApp((s) => s.customRings), ringId = useApp((s) => s.design.ringId);
  const select = useApp((s) => s.selectRing);
  return (
    <>
      <p className="lede">Five catalogue settings plus any you have designed from a photo. Selecting a design loads its stone and metal.</p>
      <GoButton to="photo" block>Design a ring from a photo</GoButton>
      <div className="cards">
        {[...cat.rings, ...customRings].map((r) => {
          const m = r.mounts.find((x) => x.role === "center")!;
          const img = r.custom ? r.photo || RING_ICON : `/renders/${RING_FILES[r.id]}.png`;
          return (
            <button key={r.id} className="card" aria-pressed={r.id === ringId} onClick={() => select(r.id, true)}>
              <img src={img} alt={r.displayName} loading="lazy" />
              <div>
                <b>{r.displayName}</b><span className="meta">{r.settingStyle}</span>
                <p>{r.description}</p>
                <p className="hint">Centre stone {m.minLengthMm}-{m.maxLengthMm} mm long · {m.supportedShapes.length} cuts</p>
              </div>
            </button>
          );
        })}
      </div>
      <GoButton to="gemstones" primary block>Choose the gemstone</GoButton>
    </>
  );
}

export function Gems() {
  const v = useDesignView(), cat = v.cat, m = v.centerMount;
  const patch = useApp((s) => s.patchDesign), setShape = useApp((s) => s.setShape);
  const unsupported = cat.shapes.filter((s) => !m.supportedShapes.includes(s.id)).map((s) => s.displayName.toLowerCase());
  return (
    <>
      <h2 className="section">Gemstone</h2>
      <div className="gems">
        {cat.gemstones.map((g) => (
          <button key={g.id} className="gem" aria-pressed={g.id === v.d.gemId} onClick={() => patch({ gemId: g.id })}>
            <Swatch hex={g.colorHex} />
            <span><b>{g.displayName}</b><small>{g.mineral} · {g.hardnessMohs} Mohs</small></span>
            <span className="num">RI {g.refractiveIndex.toFixed(2)}</span>
          </button>
        ))}
      </div>
      <h2 className="section">Cut</h2>
      <div className="shapes">
        {cat.shapes.map((s) => {
          const ok = m.supportedShapes.includes(s.id);
          return (
            <button key={s.id} className="shape" aria-pressed={s.id === v.d.shapeId} disabled={!ok}
              title={ok ? s.displayName : `Not available in the ${v.ring.displayName} setting`} onClick={() => setShape(s.id)}>
              <svg viewBox="0 0 34 34" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true" dangerouslySetInnerHTML={{ __html: SHAPE_ICONS[s.id] }} />
              {s.displayName}
            </button>
          );
        })}
      </div>
      {unsupported.length > 0 && <p className="note">The {v.ring.displayName} head cannot hold {listJoin(unsupported)} stones, so those cuts are unavailable.</p>}
      <p className="note">{v.gem.description}</p>
      <GoButton to="customise" primary block>Customise size &amp; metal</GoButton>
    </>
  );
}

export function Customise() {
  const v = useDesignView(), m = v.centerMount, s = v.shape, d = v.d;
  const patch = useApp((st) => st.patchDesign), addCompare = useApp((st) => st.addCompare);
  const wMin = 3, wMax = 10;
  return (
    <>
      <FitBox v={v} />
      <h2 className="section">Stone dimensions</h2>
      <Slider id="len" label="Length" value={d.lengthMm} min={s.minLengthMm} max={s.maxLengthMm} step={0.1}
        style={rangeTrack(s.minLengthMm, s.maxLengthMm, m.minLengthMm, m.maxLengthMm)}
        onChange={(x) => patch(s.lockAspect ? { lengthMm: x, widthMm: x } : { lengthMm: x })}
        hint={`Cut range ${s.minLengthMm}-${s.maxLengthMm} mm · setting holds ${m.minLengthMm}-${m.maxLengthMm} mm`} />
      <Slider id="wid" label="Width" value={d.widthMm} min={wMin} max={wMax} step={0.1} disabled={s.lockAspect}
        style={rangeTrack(wMin, wMax, m.minWidthMm, m.maxWidthMm)} onChange={(x) => patch({ widthMm: x })}
        hint={s.lockAspect ? `${s.displayName} stones are as wide as they are long` : `Setting holds ${m.minWidthMm}-${m.maxWidthMm} mm`} />
      <dl className="spec">
        <dt>Total depth</dt><dd className="mono">{v.depthMm.toFixed(2)} mm (max {m.maxDepthMm} mm)</dd>
        <dt>Estimated weight</dt><dd className="mono">≈ {v.carat.toFixed(2)} ct</dd>
      </dl>
      <h2 className="section">Seat position in the head</h2>
      <Slider id="seatY" label="Height" value={d.seat.y} min={-m.adjustRangeMm.y} max={m.adjustRangeMm.y} step={0.05} digits={2} signed
        disabled={!m.adjustRangeMm.y} onChange={(y) => patch({ seat: { ...d.seat, y } })} />
      <Slider id="seatX" label="Side to side" value={d.seat.x} min={-m.adjustRangeMm.x} max={m.adjustRangeMm.x} step={0.05} digits={2} signed
        disabled={!m.adjustRangeMm.x} onChange={(x) => patch({ seat: { ...d.seat, x } })}
        hint={m.adjustRangeMm.x ? `Adjustable by up to ±${m.adjustRangeMm.x} mm in this head` : "A bezel holds the stone exactly centred"} />
      <h2 className="section">Metal</h2>
      <div className="metals">
        {v.cat.metals.map((mt) => (
          <button key={mt.id} className="metal" aria-pressed={mt.id === d.metalId} onClick={() => patch({ metalId: mt.id })}>
            <i style={cssVars({ "--m": mt.colorHex })} />{mt.displayName.replace("18K ", "")}
          </button>
        ))}
      </div>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => addCompare()}>Add to compare</button>
        <GoButton to="inspect" primary style={{ flex: 1 }}>Inspect</GoButton>
      </div>
    </>
  );
}

import { SHAPE_ICONS, byId, estimateCarat, specificGravity } from "../lib/catalog";
import { useApp } from "../lib/store";
import { getStage } from "../three/stage";
import { Slider, Swatch } from "../ui";

/** Gemstone Gallery: every stone and cut as a loose 3D gem, with its mineral and cut facts. */
export function Gallery() {
  const cat = useApp((s) => s.cat)!, meta = useApp((s) => s.meta)!, g = useApp((s) => s.gallery);
  const app = useApp.getState();
  const gem = byId(cat.gemstones, g.gemId)!, shape = byId(cat.shapes, g.shapeId)!, cut = meta.gemCuts?.[g.shapeId] || {};
  const depthRatio: number = cut.depth_ratio ?? shape.depthRatio;
  const depth = g.widthMm * depthRatio, carat = estimateCarat(g.shapeId, g.gemId, g.lengthMm, g.widthMm, depth);
  const setShape = (id: string) => {
    const s = byId(cat.shapes, id)!;
    app.setGallery({ shapeId: id, lengthMm: s.defaultLengthMm, widthMm: s.defaultWidthMm });
  };
  const useInDesign = () => {
    app.patchDesign({ gemId: g.gemId, shapeId: g.shapeId, lengthMm: g.lengthMm, widthMm: g.widthMm, seat: { x: 0, y: 0, z: 0 } });
    useApp.setState({ keepStone: true });
    app.showToast(`${gem.displayName} ${shape.displayName.toLowerCase()} ${g.lengthMm.toFixed(1)} × ${g.widthMm.toFixed(1)} mm loaded. Pick a setting: any that can't hold it will say why.`);
    app.go("rings");
  };
  return (
    <>
      <p className="lede">Every GemXpert gemstone in every cut, as a loose 3D stone. Pick a stone and a cut, set the size, then drag to turn it and watch the facets catch the light.</p>

      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.topView()}>Table view</button>
        <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.sideView()}>Side profile</button>
        <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.resetView()}>Spin</button>
      </div>

      <h2 className="section">{gem.displayName} · {shape.displayName}</h2>
      <dl className="spec">
        <dt>Mineral</dt><dd>{gem.mineral}</dd>
        <dt>Colour</dt><dd className="mono"><Swatch hex={gem.colorHex} /> {gem.colorHex}</dd>
        <dt>Hardness</dt><dd className="mono">{gem.hardnessMohs} Mohs</dd>
        <dt>Refractive index</dt><dd className="mono">{gem.refractiveIndex.toFixed(2)}</dd>
        <dt>Dispersion (fire)</dt><dd className="mono">{gem.dispersion.toFixed(3)}</dd>
        <dt>Density</dt><dd className="mono">{specificGravity(g.gemId).toFixed(2)} g/cm³</dd>
        <dt>Cut</dt><dd>{shape.displayName}{cut.facets ? `, ${cut.facets} facets` : ""}</dd>
        <dt>Proportions</dt><dd className="mono">depth {(depthRatio * 100).toFixed(0)}% of width{cut.crown_fraction ? ` · crown ${(cut.crown_fraction * 100).toFixed(0)}% / pavilion ${(cut.pavilion_fraction * 100).toFixed(0)}%` : ""}</dd>
        <dt>Dimensions</dt><dd className="mono">{g.lengthMm.toFixed(1)} × {g.widthMm.toFixed(1)} × {depth.toFixed(2)} mm</dd>
        <dt>Est. weight</dt><dd className="mono">≈ {carat.toFixed(2)} ct</dd>
      </dl>
      <p className="note">{gem.description}</p>

      <h2 className="section">Gemstone</h2>
      <div className="gems">
        {cat.gemstones.map((x) => (
          <button key={x.id} className="gem" aria-pressed={x.id === g.gemId} onClick={() => app.setGallery({ gemId: x.id })}>
            <Swatch hex={x.colorHex} />
            <span><b>{x.displayName}</b><small>{x.mineral} · {x.hardnessMohs} Mohs</small></span>
            <span className="num">RI {x.refractiveIndex.toFixed(2)}</span>
          </button>
        ))}
      </div>

      <h2 className="section">Cut</h2>
      <div className="shapes">
        {cat.shapes.map((s) => (
          <button key={s.id} className="shape" aria-pressed={s.id === g.shapeId} title={s.displayName} onClick={() => setShape(s.id)}>
            <svg viewBox="0 0 34 34" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true" dangerouslySetInnerHTML={{ __html: SHAPE_ICONS[s.id] }} />
            {s.displayName}
          </button>
        ))}
      </div>

      <h2 className="section">Size</h2>
      <Slider id="g-len" label="Length" value={g.lengthMm} min={shape.minLengthMm} max={shape.maxLengthMm} step={0.1}
        onChange={(x) => app.setGallery(shape.lockAspect ? { lengthMm: x, widthMm: x } : { lengthMm: x, widthMm: Math.min(g.widthMm, x) })}
        hint={`${shape.displayName} stones from ${shape.minLengthMm} to ${shape.maxLengthMm} mm`} />
      <Slider id="g-wid" label="Width" value={g.widthMm} min={3} max={Math.min(10, g.lengthMm)} step={0.1} disabled={shape.lockAspect}
        onChange={(x) => app.setGallery({ widthMm: x })}
        hint={shape.lockAspect ? `${shape.displayName} stones are as wide as they are long` : "No wider than the stone is long"} />

      <button className="btn primary block" onClick={useInDesign}>Set this stone in a design</button>
    </>
  );
}

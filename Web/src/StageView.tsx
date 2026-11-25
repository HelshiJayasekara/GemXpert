import { useEffect, useRef, useState } from "react";
import { byId, estimateCarat } from "./lib/catalog";
import { useApp, useDesignView } from "./lib/store";
import { Stage, getStage, setStage } from "./three/stage";

export function StageView() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cat = useApp((s) => s.cat);
  const stageReady = useApp((s) => s.stageReady), stageError = useApp((s) => s.stageError), loadError = useApp((s) => s.loadError);
  const autoRotate = useApp((s) => s.autoRotate), onFinger = useApp((s) => s.onFinger), category = useApp((s) => s.category);
  const gallery = useApp((s) => s.view === "gallery");

  useEffect(() => {
    if (!cat || !canvas.current) return;
    const stage = new Stage(canvas.current);
    setStage(stage);
    return () => { stage.dispose(); setStage(null); };
  }, [cat]);

  return (
    <section className="stage" aria-label="3D display stand">
      <canvas ref={canvas} id="view" />
      {cat && (gallery ? <LooseHud /> : <Hud />)}
      <div className="toolbar" role="toolbar" aria-label="Inspection">
        <button className="tool" aria-pressed={autoRotate} onClick={() => getStage()?.setAutoRotate(!autoRotate)}>Auto-rotate</button>
        <button className="tool" aria-label="Zoom in" onClick={() => getStage()?.zoom(0.75)}>Zoom +</button>
        <button className="tool" aria-label="Zoom out" onClick={() => getStage()?.zoom(1.33)}>Zoom -</button>
        <button className="tool" onClick={() => getStage()?.closeUp()}>Close-up stone</button>
        <button className="tool" aria-pressed={onFinger} disabled={category !== "ring" || gallery}
          title={gallery ? "Loose stones are shown on their own" : category === "ring" ? "Put the ring on a hand" : "Rings only: other pieces are shown on their own"}
          onClick={() => getStage()?.setFinger(!onFinger)}>On hand</button>
        <button className="tool" onClick={() => getStage()?.resetView()}>Reset view</button>
      </div>
      <Toast />
      <div className={`loading${stageReady && !stageError ? " done" : ""}`}>
        {loadError || stageError || "Preparing the showroom..."}
      </div>
    </section>
  );
}

function Hud() {
  const v = useDesignView();
  if (!v) return null;
  const f = v.fit();
  return (
    <div className="hud">
      <div className="caption">
        <div className="caption-title">{v.ring.displayName}</div>
        <div className="caption-spec">
          {v.gem.displayName} · {v.shape.displayName} {v.d.lengthMm.toFixed(1)} × {v.d.widthMm.toFixed(1)} × {v.depthMm.toFixed(2)} mm · {v.metal.displayName}
        </div>
      </div>
      <div className={`fit ${f.status}`} role="status">
        {f.status === "bad" ? `Does not fit: ${f.reasons[0].split(":")[0].replace(/\.$/, "")}` : f.title}
      </div>
    </div>
  );
}

/** Caption for the Gemstone Gallery's loose stone (no setting, so no fit badge). */
function LooseHud() {
  const cat = useApp((s) => s.cat)!, meta = useApp((s) => s.meta)!, g = useApp((s) => s.gallery);
  const gem = byId(cat.gemstones, g.gemId)!, shape = byId(cat.shapes, g.shapeId)!;
  const depth = g.widthMm * (meta.gemCuts?.[g.shapeId]?.depth_ratio ?? shape.depthRatio);
  return (
    <div className="hud">
      <div className="caption">
        <div className="caption-title">Loose {gem.displayName}</div>
        <div className="caption-spec">
          {shape.displayName} {g.lengthMm.toFixed(1)} × {g.widthMm.toFixed(1)} × {depth.toFixed(2)} mm · ≈ {estimateCarat(g.shapeId, g.gemId, g.lengthMm, g.widthMm, depth).toFixed(2)} ct
        </div>
      </div>
    </div>
  );
}

function Toast() {
  const toast = useApp((s) => s.toast);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!toast) return;
    setShown(true);
    const t = setTimeout(() => setShown(false), 2600);
    return () => clearTimeout(t);
  }, [toast]);
  return <div className={`toast${shown ? " show" : ""}`} aria-live="polite">{toast?.msg}</div>;
}

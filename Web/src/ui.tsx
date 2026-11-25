// Small shared UI pieces.
import type { CSSProperties, ReactNode } from "react";
import { Color } from "three";
import type { DesignView } from "./lib/catalog";
import { useApp, type ViewId } from "./lib/store";

export const cssVars = (vars: Record<string, string>) => vars as CSSProperties;

export function swatchStyle(hex: string): CSSProperties {
  const c = new Color(hex);
  const lite = c.clone().lerp(new Color(0xffffff), 0.55), dark = c.clone().multiplyScalar(0.45);
  return cssVars({ "--c1": hex, "--c2": `#${lite.getHexString()}`, "--c3": `#${dark.getHexString()}` });
}

export function Swatch({ hex }: { hex: string }) {
  return <span className="swatch" style={swatchStyle(hex)} />;
}

export function GoButton({ to, primary, block, children, style }: { to: ViewId; primary?: boolean; block?: boolean; children: ReactNode; style?: CSSProperties }) {
  const go = useApp((s) => s.go);
  return <button className={`btn${primary ? " primary" : ""}${block ? " block" : ""}`} style={style} onClick={() => go(to)}>{children}</button>;
}

export function FitBox({ v }: { v: DesignView }) {
  const f = v.fit();
  return (
    <div className={`fitbox ${f.status}`}>
      <b>{f.title}</b>
      <ul>
        {f.reasons.length
          ? f.reasons.map((r) => <li key={r}>{r}</li>)
          : <li>{v.gem.displayName} {v.shape.displayName.toLowerCase()} sits correctly in the {v.ring.displayName} head.</li>}
      </ul>
    </div>
  );
}

export function rangeTrack(min: number, max: number, okMin: number, okMax: number): CSSProperties {
  const a = ((okMin - min) / (max - min)) * 100, b = ((okMax - min) / (max - min)) * 100;
  return cssVars({ "--track": `linear-gradient(90deg, #4a2a2a 0%, #4a2a2a ${a}%, #2f4a3a ${a}%, #2f4a3a ${b}%, #4a2a2a ${b}%, #4a2a2a 100%)` });
}

export function Slider({ id, label, value, min, max, step, onChange, disabled, hint, unit = "mm", digits = 1, signed, style }: {
  id: string; label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void;
  disabled?: boolean; hint?: ReactNode; unit?: string; digits?: number; signed?: boolean; style?: CSSProperties;
}) {
  return (
    <div className="field">
      <div className="field-top">
        <label htmlFor={id}>{label}</label>
        <span className="val">{signed && value >= 0 ? "+" : ""}{value.toFixed(digits)} {unit}</span>
      </div>
      <input type="range" id={id} min={min} max={max} step={step} value={value} disabled={disabled} style={style}
        onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <span className="hint">{hint}</span>}
    </div>
  );
}

/** Two-step confirm for destructive buttons (Delete / Remove). */
export function ConfirmRow({ question, yes, onYes, onNo }: { question: string; yes: string; onYes: () => void; onNo: () => void }) {
  return (
    <div className="row">
      <span style={{ flex: 1, alignSelf: "center" }}>{question}</span>
      <button className="btn" onClick={onYes}>{yes}</button>
      <button className="btn" onClick={onNo}>Keep</button>
    </div>
  );
}

import { useApp, useDesignView } from "../lib/store";
import { GoButton } from "../ui";

export function Welcome() {
  return (
    <div className="stack welcome">
      <span className="eyebrow">Welcome to</span>
      <div className="mark">GEMXPERT</div>
      <div className="tag">Immersive Gemstone &amp; Jewellery Studio</div>
      <div className="rule" />
      <p className="lede">Choose a ring design, fit a gemstone into its setting, adjust the cut, size and metal, then see it on a hand and turn it with the GemXpert wearable.</p>
      <GoButton to="showroom" primary block>Start experience</GoButton>
      <div className="row" style={{ width: "100%" }}>
        <GoButton to="how-it-works" style={{ flex: 1 }}>How it works</GoButton>
        <GoButton to="wearable" style={{ flex: 1 }}>Wearable device</GoButton>
      </div>
    </div>
  );
}

export function How() {
  return (
    <>
      <ol className="steps">
        <li><div><b>Choose a setting</b><span>Solitaire, halo, three-stone, six-prong cathedral or bezel, or rebuild one from a photo.</span></div></li>
        <li><div><b>Fit a gemstone</b><span>Blue sapphire, ruby, emerald, yellow sapphire or a diamond-style stone in six cuts. Each setting accepts only the cuts and sizes its head can hold, and tells you why when a stone does not fit.</span></div></li>
        <li><div><b>Make it yours</b><span>Set the length and width in millimetres, nudge the stone's seat, and choose yellow, white or rose gold, or silver.</span></div></li>
        <li><div><b>See it on a hand</b><span>Put the ring on a hand, connect the GemXpert wearable over Bluetooth and turn your own hand to turn it. Compare designs and save your favourites.</span></div></li>
      </ol>
      <h2 className="section">Controls</h2>
      <div className="keys">
        <kbd>Drag</kbd><span>Rotate the view</span>
        <kbd>Scroll / pinch</kbd><span>Zoom</span>
        <kbd>Right-drag</kbd><span>Pan</span>
      </div>
      <h2 className="section">The wearable</h2>
      <p className="lede">An ESP32 with an MPU6050 motion sensor, worn on the finger. It sends its orientation over Bluetooth: tap it for the next gemstone, double tap for the next metal. Works in Chrome or Edge on Windows, Mac, Android and ChromeOS.</p>
      <p className="note">Hand model: WebXR Input Profiles generic hand, W3C Software and Document License.</p>
      <GoButton to="showroom" primary block>Enter the showroom</GoButton>
    </>
  );
}

export function Showroom() {
  const v = useDesignView(), saved = useApp((s) => s.saved), wear = useApp((s) => s.wear), go = useApp((s) => s.go);
  const f = v.fit();
  const tiles: [Parameters<typeof go>[0], string, string][] = [
    ["rings", "Ring Designs", v.ring.displayName],
    ["photo", "From a Photo", "Upload a ring photo and rebuild it in 3D"],
    ["gemstones", "Gemstones", `${v.gem.displayName}, ${v.shape.displayName}`],
    ["customise", "Customise", `${v.d.lengthMm.toFixed(1)} × ${v.d.widthMm.toFixed(1)} mm · ${v.metal.displayName}`],
    ["inspect", "Inspect", "Close-up, on a hand and compare"],
    ["summary", "Design Summary", f.status === "bad" ? "Fix the fit before saving" : "Review and save"],
    ["saved", "Saved Designs", `${saved.length} saved`],
    ["wearable", "Wearable Device", wear.status === "live" ? (wear.mode === "ble" ? "Connected" : "Simulated") : "Not connected"],
  ];
  return (
    <>
      <p className="lede">Your current design is on the stand. Start with a setting, or go straight to the stone.</p>
      <div className="tiles">
        {tiles.map(([to, title, sub]) => (
          <button key={to} className="tile" onClick={() => go(to)}><b>{title}</b><span>{sub}</span></button>
        ))}
      </div>
    </>
  );
}

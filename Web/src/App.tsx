import { useApp } from "./lib/store";
import { Panel } from "./Panel";
import { StageView } from "./StageView";

export default function App() {
  const wear = useApp((s) => s.wear);
  const label = wear.status === "live" ? `Wearable: ${wear.mode === "ble" ? "connected" : "simulated"}`
    : wear.status === "connecting" ? "Wearable: connecting..." : wear.status === "reconnecting" ? "Wearable: reconnecting..." : "Wearable: not connected";
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">GEMXPERT</span>
          <span className="brand-sub">Immersive Gemstone &amp; Jewellery Studio</span>
        </div>
        <div className="chips">
          <span className="chip">by 4axismedia</span>
          <button className="chip chip-btn" onClick={() => useApp.getState().go("wearable")}>
            <span className={`dot${wear.status === "live" ? " on" : ""}`} />{label}
          </button>
        </div>
      </header>
      <main className="layout">
        <StageView />
        <Panel />
      </main>
    </div>
  );
}

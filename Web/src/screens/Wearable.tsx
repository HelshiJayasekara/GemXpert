import { useEffect, useState } from "react";
import { useApp } from "../lib/store";
import { getStage } from "../three/stage";
import { bleAvailable, bleSupported, connectBle, disconnectBle, recentre } from "../wearable/ble";
import { live, sim } from "../wearable/live";

/** Re-renders a few times a second with the latest sensor values. */
function useLiveReadout(active: boolean) {
  const [, setTick] = useState(0);
  const [rate, setRate] = useState(0);
  useEffect(() => {
    if (!active) return;
    let last = live.packets, lastT = performance.now();
    const fast = setInterval(() => setTick((t) => t + 1), 120);
    const slow = setInterval(() => {
      const now = performance.now();
      setRate(Math.round(((live.packets - last) * 1000) / (now - lastT)));
      last = live.packets; lastT = now;
    }, 1000);
    return () => { clearInterval(fast); clearInterval(slow); };
  }, [active]);
  return rate;
}

export function Wearable() {
  const wear = useApp((s) => s.wear), onFinger = useApp((s) => s.onFinger);
  const app = useApp.getState();
  const [btOn, setBtOn] = useState<boolean | null>(null);
  const [auto, setAuto] = useState(sim.auto);
  const [roll, setRoll] = useState(sim.roll), [pitch, setPitch] = useState(sim.pitch);
  useEffect(() => { bleAvailable().then(setBtOn); }, []);
  const active = wear.mode !== "off";
  const rate = useLiveReadout(active);
  const ble = wear.mode === "ble", simOn = wear.mode === "sim";
  const busy = wear.status === "connecting" || wear.status === "reconnecting";

  const startSim = () => {
    if (ble) disconnectBle();
    app.setWear({ mode: "sim", status: "live", deviceName: "Simulator" });
    getStage()?.setAutoRotate(false);
  };
  const stopSim = () => app.setWear({ mode: "off", status: "idle", deviceName: null });

  return (
    <>
      <h2 className="section" style={{ marginTop: 0 }}>GemXpert wearable (Bluetooth)</h2>
      {!bleSupported() ? (
        <div className="fitbox warn"><b>This browser can't use Bluetooth.</b>
          <ul><li>Open this page in Chrome or Edge on Windows, Mac, Android or ChromeOS.</li>
              <li>iPhone and iPad browsers don't support Web Bluetooth (the Bluefy app does).</li></ul></div>
      ) : btOn === false ? (
        <div className="fitbox warn"><b>Bluetooth is switched off or missing on this computer.</b><ul><li>Turn Bluetooth on, then reload the page.</li></ul></div>
      ) : null}
      <div className="row">
        {ble || busy
          ? <button className="btn" style={{ flex: 1 }} onClick={() => disconnectBle()}>Disconnect</button>
          : <button className="btn primary" style={{ flex: 1 }} disabled={!bleSupported()} onClick={() => connectBle()}>Connect wearable</button>}
      </div>
      <p className="note" style={{ marginTop: 0 }}>
        {wear.status === "live" && ble ? `Connected to ${wear.deviceName}. Rotate it and the ring follows. Recentre makes the current pose straight.`
          : wear.status === "connecting" ? "Connecting..." : wear.status === "reconnecting" ? "Connection lost, reconnecting..."
          : "Power the ESP32, press Connect wearable, pick GemXpert-Ring in the list and press Pair."}
      </p>

      <div className="device">
        <div className="device-top">
          <div><b>{ble ? wear.deviceName : simOn ? "Simulated wearable" : "No device connected"}</b><br />
            <small className="hint">{ble ? "ESP32 + MPU6050 · Bluetooth LE" : simOn ? "No hardware needed" : "Connect above, or try the simulator"}</small></div>
          <span className={`sim-badge${ble ? " live" : ""}`}>{ble ? "Live" : "Simulated"}</span>
        </div>
        <div className="row">
          {ble
            ? <button className="btn" style={{ flex: 1 }} onClick={() => { recentre(); app.showToast("Recentred: the current pose is now straight."); }}>Recentre</button>
            : <button className="btn" style={{ flex: 1 }} onClick={simOn ? stopSim : startSim}>{simOn ? "Stop simulator" : "Simulate instead"}</button>}
          <button className="btn" style={{ flex: 1 }} onClick={() => getStage()?.setFinger(!onFinger)}>{onFinger ? "Back to stand" : "Show on hand"}</button>
        </div>
        <div className="readout">
          <span /><span>X</span><span>Y</span><span>Z</span>
          <span>Gyro °/s</span>{[0, 1, 2].map((k) => <span key={k}>{active ? live.g[k].toFixed(1) : "-"}</span>)}
          <span>Accel g</span>{[0, 1, 2].map((k) => <span key={k}>{active ? live.a[k].toFixed(2) : "-"}</span>)}
          <span>Yaw/P/R °</span>{[0, 1, 2].map((k) => <span key={k}>{active ? live.e[k].toFixed(1) : "-"}</span>)}
        </div>
        <div className="hint">{active ? `${rate} updates/s` : "Not streaming"}</div>
      </div>

      {simOn && (
        <>
          <h2 className="section">Simulated hand motion</h2>
          <label className="row" style={{ alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={auto} onChange={(e) => { sim.auto = e.target.checked; setAuto(e.target.checked); }} /> Natural wrist movement
          </label>
          <div className="field"><div className="field-top"><label htmlFor="sRoll">Roll</label><span className="val">{roll.toFixed(0)}°</span></div>
            <input type="range" id="sRoll" min={-60} max={60} step={1} value={roll} disabled={auto} onChange={(e) => { sim.roll = +e.target.value; setRoll(sim.roll); }} /></div>
          <div className="field"><div className="field-top"><label htmlFor="sPitch">Pitch</label><span className="val">{pitch.toFixed(0)}°</span></div>
            <input type="range" id="sPitch" min={-45} max={45} step={1} value={pitch} disabled={auto} onChange={(e) => { sim.pitch = +e.target.value; setPitch(sim.pitch); }} /></div>
        </>
      )}

      <h2 className="section">Gestures</h2>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={() => app.gesture("tap")}>Tap</button>
        <button className="btn" style={{ flex: 1 }} onClick={() => app.gesture("double")}>Double tap</button>
        <button className="btn" style={{ flex: 1 }} onClick={() => app.gesture("swipe")}>Swipe</button>
      </div>
      <p className="note">On the wearable: tap the sensor for the next gemstone, double tap for the next metal. The buttons do the same here.</p>
    </>
  );
}

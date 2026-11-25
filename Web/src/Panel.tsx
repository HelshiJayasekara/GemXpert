import { useEffect, useRef } from "react";
import { VIEW_TITLES, useApp, type ViewId } from "./lib/store";
import { How, Showroom, Welcome } from "./screens/Basic";
import { Customise, Gems, Rings } from "./screens/Design";
import { Inspect, Saved, Summary } from "./screens/Review";
import { Photo } from "./screens/Photo";
import { Wearable } from "./screens/Wearable";

const SCREENS: Record<ViewId, () => React.JSX.Element> = {
  welcome: Welcome, "how-it-works": How, showroom: Showroom, rings: Rings, gemstones: Gems, customise: Customise,
  inspect: Inspect, summary: Summary, saved: Saved, wearable: Wearable, photo: Photo,
};

export function Panel() {
  const view = useApp((s) => s.view), history = useApp((s) => s.history), cat = useApp((s) => s.cat);
  const wear = useApp((s) => s.wear);
  const body = useRef<HTMLDivElement>(null);
  useEffect(() => { body.current?.scrollTo(0, 0); }, [view]);
  const Screen = SCREENS[view];
  return (
    <aside className="panel" aria-label="GemXpert panel">
      <div className="panel-head">
        <button className="quiet" style={{ justifySelf: "start" }} hidden={!history.length} onClick={() => useApp.getState().back()}>&lsaquo; Back</button>
        <h1>{VIEW_TITLES[view]}</h1>
        <button className="quiet" style={{ justifySelf: "end" }} hidden={view === "showroom" || view === "welcome"} onClick={() => useApp.getState().home()}>Showroom</button>
      </div>
      <div className="panel-body" ref={body}>
        {cat ? <Screen /> : <div className="empty">Loading the catalogue...</div>}
      </div>
      <div className="panel-foot">
        <strong>GEMXPERT</strong>
        <span>{wear.status === "live" ? (wear.mode === "ble" ? `Wearable: ${wear.deviceName}` : "Wearable simulated") : "gemxpert.4axismedia.com"}</span>
      </div>
    </aside>
  );
}

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { useApp } from "./lib/store";
import "./styles.css";

useApp.getState().init();
createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);

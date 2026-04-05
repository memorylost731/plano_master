import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import CookieConsent from "./components/CookieConsent";
import { PlannerStateProvider } from "./state/plannerState";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("Root element #root not found");

// cache-bust assets so changes appear immediately
const bust = Date.now();
const html = document.documentElement;

// Keep your current images as-is
const base = import.meta.env.BASE_URL || "/";
html.style.setProperty("--plano-bg-landing", `url("${base}assets/background.png?v=${bust}")`);
html.style.setProperty("--plano-bg-2d", `url("${base}assets/background.png?v=${bust}")`);
html.style.setProperty("--plano-bg-3d", `url("${base}assets/3d_canvas.png?v=${bust}")`);

createRoot(rootEl).render(
  <StrictMode>
    <div className="plano-liquid">
      <PlannerStateProvider>
        <App />
        <CookieConsent />
      </PlannerStateProvider>
    </div>
  </StrictMode>
);

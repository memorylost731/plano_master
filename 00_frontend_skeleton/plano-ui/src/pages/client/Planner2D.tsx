import { useNavigate } from "react-router-dom";
import { FolderOpen, Save, Download, RefreshCcw, Hand, Rotate3D } from "lucide-react";

export default function Planner2D() {
  const navigate = useNavigate();

  return (
    <div className="planner2d-bg fixed inset-0 text-zinc-900">
      {/* React-Planner 2D canvas will live here later */}
      <div className="absolute inset-0" />

      {/* TOP BAR */}
      <div className="pointer-events-none absolute left-0 right-0 top-0 flex justify-center p-4">
        <div className="pointer-events-auto glass-panel flex w-full max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">Project: Demo Apartment · Mode: 2D</div>
            <div className="truncate text-xs text-zinc-700">
              2D editing (React-Planner). Switch to 3D for services.
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate("/planner/3d")}
              className="plano-glass-btn px-4 py-2 text-sm font-semibold"
            >
              3D
            </button>

            <button type="button" className="plano-glass-btn h-10 w-10 grid place-items-center" title="Load">
              <FolderOpen className="h-5 w-5" />
            </button>

            <button type="button" className="plano-glass-btn h-10 w-10 grid place-items-center" title="Save">
              <Save className="h-5 w-5" />
            </button>

            <button type="button" className="plano-glass-btn h-10 w-10 grid place-items-center" title="Export">
              <Download className="h-5 w-5" />
            </button>

            <button type="button" className="plano-glass-btn h-10 w-10 grid place-items-center" title="Reset">
              <RefreshCcw className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT NAVIGATION MENU (Pan + Orbit) */}
      <div className="pointer-events-none absolute right-4 top-28">
        <div className="pointer-events-auto glass-panel w-[200px] p-3 space-y-2">
          <div className="text-[11px] font-semibold text-zinc-800 px-1">NAVIGATION</div>

          <button type="button" className="plano-dock-item w-full flex items-center gap-2 px-3 py-2 text-sm">
            <Rotate3D className="h-4 w-4" />
            Orbit / Rotate
          </button>

          <button type="button" className="plano-dock-item w-full flex items-center gap-2 px-3 py-2 text-sm">
            <Hand className="h-4 w-4" />
            Pan
          </button>
        </div>
      </div>
    </div>
  );
}

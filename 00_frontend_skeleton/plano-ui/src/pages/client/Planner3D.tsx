import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  Bolt,
  Wrench,
  Paintbrush,
  Grid3X3,
  Layers,
  Boxes,
  MoreHorizontal,
  FolderOpen,
  Save,
  FileText,
  Download,
  RefreshCcw,
} from "lucide-react";

import {
  MAIN_SERVICES,
  SUBSERVICES,
  usePlannerState,
  type MainService,
} from "../../state/plannerState";

const ICONS: Record<MainService, LucideIcon> = {
  electricity: Bolt,
  plumbing: Wrench,
  painting: Paintbrush,
  flooring: Grid3X3,
  plastering: Layers,
  boards: Boxes,
  other: MoreHorizontal,
};

export default function Planner3D() {
  const navigate = useNavigate();
  const {
    activeMain,
    setActiveMain,
    selected,
    toggleSub,
    hasAnySelection,
    selectedCount,
    clearAll,
  } = usePlannerState();

  const subs = SUBSERVICES[activeMain];

  return (
    <div className="planner3d-bg fixed inset-0 text-zinc-900">
      {/* React-Planner 3D canvas will live here later */}
      <div className="absolute inset-0" />

      {/* HEADER */}
      <div className="pointer-events-none absolute left-0 right-0 top-0 flex justify-center p-3">
        <div className="pointer-events-auto glass-panel w-full max-w-6xl px-4 py-2">
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="flex items-center gap-2 font-semibold"
              title="PlanO"
            >
              <span className="text-base">PlanO</span>
            </button>

            {/* MAIN SERVICES (no wrapping — horizontal scroll instead) */}
            <div className="flex-1 overflow-x-auto">
              <div className="flex items-center gap-2 justify-center min-w-max px-1">
                {MAIN_SERVICES.map((s) => {
                  const Icon = ICONS[s.key];
                  const isActive = activeMain === s.key;

                  return (
                    <button
                      key={s.key}
                      type="button"
                      onClick={() => setActiveMain(s.key)}
                      className={`plano-dock-item flex items-center gap-2 px-3 py-2 text-sm ${
                        isActive ? "ring-2 ring-white/70" : ""
                      }`}
                      title={s.label}
                    >
                      <Icon className="h-4 w-4" />
                      <span className="hidden sm:inline">{s.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ACTIONS */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => navigate("/planner/2d")}
                className="plano-glass-btn px-4 py-2 text-sm font-semibold"
              >
                2D
              </button>

              <button className="plano-glass-btn h-10 w-10 grid place-items-center" title="Load">
                <FolderOpen className="h-5 w-5" />
              </button>
              <button className="plano-glass-btn h-10 w-10 grid place-items-center" title="Save">
                <Save className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={() => navigate("/estimate")}
                disabled={!hasAnySelection}
                className={`plano-glass-btn h-10 w-10 grid place-items-center ${
                  hasAnySelection ? "" : "opacity-40 cursor-not-allowed"
                }`}
                title="Estimate"
              >
                <FileText className="h-5 w-5" />
              </button>

              <button className="plano-glass-btn h-10 w-10 grid place-items-center" title="Export">
                <Download className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={() => clearAll()}
                className="plano-glass-btn h-10 w-10 grid place-items-center"
                title="Reset selections"
              >
                <RefreshCcw className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="mt-2 text-xs text-zinc-700">
            Selected items: <span className="font-semibold">{selectedCount}</span>
          </div>
        </div>
      </div>

      {/* LEFT SUBSERVICES — moved down + clean header */}
      <div className="pointer-events-none absolute left-4 top-36">
        <div className="pointer-events-auto w-[300px] glass-panel overflow-hidden">
          <div className="px-4 py-3 border-b border-white/20">
            <div className="text-[11px] font-semibold text-zinc-900">
              {MAIN_SERVICES.find((x) => x.key === activeMain)?.label.toUpperCase()} SUB-SERVICES
            </div>
            <div className="text-[11px] text-zinc-700">
              Click to toggle. Selected are highlighted.
            </div>
          </div>

          <div className="p-3 space-y-2 max-h-[62vh] overflow-auto">
            {subs.map((sub) => {
              const isActive = selected[activeMain].has(sub);
              return (
                <button
                  key={sub}
                  type="button"
                  onClick={() => toggleSub(activeMain, sub)}
                  className={`plano-dock-item w-full px-3 py-2 text-sm text-left ${
                    isActive ? "ring-2 ring-white/70" : ""
                  }`}
                  title={sub}
                >
                  {sub}
                </button>
              );
            })}

            {hasAnySelection && (
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => navigate("/estimate")}
                  className="plano-glass-btn w-full px-3 py-2 text-sm font-semibold"
                >
                  Proceed to Estimate
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

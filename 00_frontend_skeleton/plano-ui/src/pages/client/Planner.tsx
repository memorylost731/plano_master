import { useMemo, useRef, useState, useCallback } from "react";
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
  FilePlus,
  FolderOpen,
  Save,
  Plus,
  Undo2,
  Settings,
  PersonStanding,
  FileText,
} from "lucide-react";

import PlannerFrame, { type PlannerApi } from "../../components/planner/PlannerFrame";

import {
  MAIN_SERVICES,
  SUBSERVICES,
  usePlannerState,
  type MainService,
} from "../../state/plannerState";

type ViewMode = "2D" | "3D";

const ICONS: Record<MainService, LucideIcon> = {
  electricity: Bolt,
  plumbing: Wrench,
  painting: Paintbrush,
  flooring: Grid3X3,
  plastering: Layers,
  boards: Boxes,
  other: MoreHorizontal,
};

export default function Planner() {
  const navigate = useNavigate();

  const apiRef = useRef<PlannerApi | null>(null);
  const didInitRef = useRef(false);

  const [viewMode, setViewMode] = useState<ViewMode>("2D");
  const [engineMode, setEngineMode] = useState<string>("");

  const {
    activeMain,
    setActiveMain,
    selected,
    toggleSub,
    hasAnySelection,
    selectedCount: _selectedCount,
    clearAll,
  } = usePlannerState();

  const subs = useMemo(() => SUBSERVICES[activeMain], [activeMain]);

  const handleApi = useCallback((api: PlannerApi) => {
    apiRef.current = api;
    if (!didInitRef.current) {
      didInitRef.current = true;
      api.cmd("VIEW_2D");
      api.cmd("SELECT_TOOL_EDIT");
      setViewMode("2D");
    }
  }, []);

  const go2D = useCallback(() => {
    setViewMode("2D");
    apiRef.current?.cmd("VIEW_2D");
    apiRef.current?.cmd("SELECT_TOOL_EDIT");
  }, []);

  const go3D = useCallback(() => {
    setViewMode("3D");
    apiRef.current?.cmd("VIEW_3D");
  }, []);

  const isCatalogOpen = engineMode === "MODE_VIEWING_CATALOG";

  return (
    <div className={`${viewMode === "2D" ? "planner2d-bg" : "planner3d-bg"} fixed inset-0 text-zinc-900`}>
      <PlannerFrame onApi={handleApi} onModeChange={setEngineMode} />

      {/* TOP BAR (FULL WIDTH – NO SLIDER, NO WRAP) */}
      <div className="pointer-events-none absolute left-0 right-0 top-0 z-50 flex justify-center p-2">
        <div className="pointer-events-auto glass-panel w-[calc(100vw-24px)] px-4 py-1">
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="flex items-center gap-2 font-semibold"
            >
              <span className="text-base">PlanO</span>
            </button>

            {/* SERVICES (3D only) — NO WRAP, NO SCROLLBAR */}
            {viewMode === "3D" ? (
              <div className="flex-1 min-w-0 overflow-hidden">
                <div className="flex items-center gap-2 justify-center px-1">
                  {MAIN_SERVICES.map((s) => {
                    const Icon = ICONS[s.key];
                    const isActive = activeMain === s.key;
                    return (
                      <button
                        key={s.key}
                        type="button"
                        onClick={() => setActiveMain(s.key)}
                        className={`plano-dock-item flex items-center gap-2 px-2 py-1 text-xs ${
                          isActive ? "ring-2 ring-white/70" : ""
                        }`}
                        title={s.label}
                      >
                        <Icon className="h-4 w-4" />
                        <span className="hidden lg:inline">{s.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="flex-1" />
            )}

            {/* ACTIONS */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => apiRef.current?.cmd("NEW_PROJECT")}
                className="plano-glass-btn h-10 w-10 grid place-items-center"
                title="New project"
              >
                <FilePlus className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={() => apiRef.current?.saveProjectDownload()}
                className="plano-glass-btn h-10 w-10 grid place-items-center"
                title="Save project"
              >
                <Save className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={() => apiRef.current?.loadProjectPicker()}
                className="plano-glass-btn h-10 w-10 grid place-items-center"
                title="Load project (JSON/PDF/Image via Raster)"
              >
                <FolderOpen className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={() => apiRef.current?.cmd("OPEN_CATALOG")}
                className="plano-glass-btn h-10 w-10 grid place-items-center"
                title="Open catalog"
              >
                <Plus className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={go3D}
                className={`plano-glass-btn px-4 py-2 text-sm font-semibold ${
                  viewMode === "3D" ? "ring-2 ring-white/70" : ""
                }`}
                title="3D View"
              >
                3D
              </button>

              <button
                type="button"
                onClick={go2D}
                className={`plano-glass-btn px-4 py-2 text-sm font-semibold ${
                  viewMode === "2D" ? "ring-2 ring-white/70" : ""
                }`}
                title="2D View"
              >
                2D
              </button>

              <button
                type="button"
                onClick={() => viewMode === "3D" && apiRef.current?.cmd("VIEW_3D_FIRST_PERSON")}
                className={`plano-glass-btn h-10 w-10 grid place-items-center ${
                  viewMode === "3D" ? "" : "opacity-40 cursor-not-allowed"
                }`}
                title="3D First Person (3D only)"
                disabled={viewMode !== "3D"}
              >
                <PersonStanding className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={() => apiRef.current?.cmd("UNDO")}
                className="plano-glass-btn h-10 w-10 grid place-items-center"
                title="Undo"
              >
                <Undo2 className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={() => apiRef.current?.cmd("OPEN_PROJECT_CONFIGURATOR")}
                className="plano-glass-btn h-10 w-10 grid place-items-center"
                title="Configure project"
              >
                <Settings className="h-5 w-5" />
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
            </div>
          </div>
        </div>
      </div>

      {/* LEFT SUBSERVICES only in 3D (HIDDEN while catalog is open) */}
      {viewMode === "3D" && !isCatalogOpen && (
        <div className="pointer-events-none absolute left-4 top-36 z-50">
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

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => {
                    clearAll();
                    apiRef.current?.cmd("UNSELECT_ALL");
                  }}
                  className="plano-glass-btn w-full px-3 py-2 text-sm font-semibold"
                >
                  Reset selections
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* IMPORTANT: removed the PlanO right NAV overlay entirely */}
    </div>
  );
}

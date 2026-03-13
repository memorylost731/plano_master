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
  FileText,
} from "lucide-react";

import PlannerFrame, {
  type PlannerApi,
  type CatalogServiceSelectedPayload,
} from "../../components/planner/PlannerFrame";

import {
  MAIN_SERVICES,
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
    hasAnySelection,
    selectedCount: _selectedCount,
    clearAll,
    toggleSurface,
    applyAreaService,
    activeAreaSubService,
    setActiveAreaSubService,
    activeAreaMaterialKey,
    setActiveAreaMaterialKey,
    activeAreaMaterialLabel,
    setActiveAreaMaterialLabel,
    activeAreaMaterialColor,
    setActiveAreaMaterialColor,
  } = usePlannerState();

  const handleApi = useCallback((api: PlannerApi) => {
    apiRef.current = api;

    if (!didInitRef.current) {
      didInitRef.current = true;
      api.cmd("VIEW_2D");
      api.cmd("SELECT_TOOL_EDIT");
      setViewMode("2D");
    }
  }, []);

  const handleCatalogServiceSelected = useCallback(
    (payload: CatalogServiceSelectedPayload) => {
      if (payload.mainService === "painting") {
        setActiveMain("painting");
        setActiveAreaSubService(payload.subService);
        setActiveAreaMaterialKey(payload.materialKey);
        setActiveAreaMaterialLabel(payload.materialLabel);
        setActiveAreaMaterialColor(payload.color || null);
        setViewMode("3D");
        apiRef.current?.cmd("VIEW_3D");
        console.log("Selected catalog material:", payload);
      }
    },
    [
      setActiveMain,
      setActiveAreaSubService,
      setActiveAreaMaterialKey,
      setActiveAreaMaterialLabel,
      setActiveAreaMaterialColor,
    ]
  );

  const handleSurfaceSelected = useCallback(
    (payload: any) => {
      const surfaceId = payload?.surfaceId;
      if (!surfaceId) return;

      console.log("PlanO received surface:", surfaceId);

      if (
        activeAreaSubService &&
        activeAreaMaterialKey &&
        (activeMain === "painting" ||
          activeMain === "flooring" ||
          activeMain === "plastering" ||
          activeMain === "boards")
      ) {
        console.log("Applying service/material:", {
          service: activeMain,
          subService: activeAreaSubService,
          materialKey: activeAreaMaterialKey,
          materialLabel: activeAreaMaterialLabel,
          color: activeAreaMaterialColor,
          surfaceId,
        });

        toggleSurface(surfaceId);
        applyAreaService(activeMain);
      } else {
        toggleSurface(surfaceId);
      }
    },
    [
      toggleSurface,
      applyAreaService,
      activeMain,
      activeAreaSubService,
      activeAreaMaterialKey,
      activeAreaMaterialLabel,
      activeAreaMaterialColor,
    ]
  );

  const go2D = useCallback(() => {
    setViewMode("2D");
    apiRef.current?.cmd("VIEW_2D");
    apiRef.current?.cmd("SELECT_TOOL_EDIT");
  }, []);

  const go3D = useCallback(() => {
    setViewMode("3D");
    apiRef.current?.cmd("VIEW_3D");
  }, []);

  const openServiceCatalog = useCallback((service: MainService) => {
    setActiveMain(service);
    apiRef.current?.cmd("OPEN_CATALOG");

    setTimeout(() => {
      apiRef.current?.cmd("CHANGE_CATALOG_PAGE", {
        newPage: `plano_${service}`,
        oldPage: "root",
      });
    }, 50);
  }, [setActiveMain]);

  const isCatalogOpen = engineMode === "MODE_VIEWING_CATALOG";

  const statusText = useMemo(() => {
    if (!activeAreaSubService || !activeAreaMaterialLabel) return null;
    return `${activeAreaSubService} → ${activeAreaMaterialLabel}`;
  }, [activeAreaSubService, activeAreaMaterialLabel]);

  return (
    <div
      className={`${
        viewMode === "2D" ? "planner2d-bg" : "planner3d-bg"
      } fixed inset-0 text-zinc-900`}
    >
      <PlannerFrame
        onApi={handleApi}
        onModeChange={setEngineMode}
        onSurfaceSelected={handleSurfaceSelected}
        onCatalogServiceSelected={handleCatalogServiceSelected}
      />

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

            {viewMode === "3D" && !isCatalogOpen ? (
              <div className="flex-1 min-w-0 overflow-hidden">
                <div className="flex items-center gap-2 justify-center px-1">
                  {MAIN_SERVICES.map((s) => {
                    const Icon = ICONS[s.key];
                    const isActive = activeMain === s.key;

                    return (
                      <button
                        key={s.key}
                        type="button"
                        onClick={() => openServiceCatalog(s.key)}
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

            {!isCatalogOpen && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => apiRef.current?.cmd("NEW_PROJECT")}
                  className="plano-glass-btn h-10 w-10 grid place-items-center"
                >
                  <FilePlus className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={() => apiRef.current?.saveProjectDownload()}
                  className="plano-glass-btn h-10 w-10 grid place-items-center"
                >
                  <Save className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={() => apiRef.current?.loadProjectPicker()}
                  className="plano-glass-btn h-10 w-10 grid place-items-center"
                >
                  <FolderOpen className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={() => apiRef.current?.cmd("OPEN_CATALOG")}
                  className="plano-glass-btn h-10 w-10 grid place-items-center"
                >
                  <Plus className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={go3D}
                  className={`plano-glass-btn px-4 py-2 text-sm ${
                    viewMode === "3D" ? "ring-2 ring-white/70" : ""
                  }`}
                >
                  3D
                </button>

                <button
                  type="button"
                  onClick={go2D}
                  className={`plano-glass-btn px-4 py-2 text-sm ${
                    viewMode === "2D" ? "ring-2 ring-white/70" : ""
                  }`}
                >
                  2D
                </button>

                <button
                  type="button"
                  onClick={() => apiRef.current?.cmd("UNDO")}
                  className="plano-glass-btn h-10 w-10 grid place-items-center"
                >
                  <Undo2 className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={() => apiRef.current?.cmd("OPEN_PROJECT_CONFIGURATOR")}
                  className="plano-glass-btn h-10 w-10 grid place-items-center"
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
                >
                  <FileText className="h-5 w-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {!isCatalogOpen && statusText ? (
        <div className="absolute left-4 top-20 z-40 rounded-xl bg-white/95 px-4 py-3 shadow-lg">
          <div className="text-sm font-semibold">Selected service</div>
          <div className="text-sm">{statusText}</div>
        </div>
      ) : null}
    </div>
  );
}
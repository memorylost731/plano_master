import { useMemo, useRef, useState, useCallback, useEffect } from "react";
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
  type SurfaceSelectedPayload,
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

const SCENE_BACKUP_KEY = "plano_scene_backup";

export default function Planner() {
  const navigate = useNavigate();

  const apiRef = useRef<PlannerApi | null>(null);
  const didInitRef = useRef(false);
  const pendingEstimateNavRef = useRef(false);
  const restoreAttemptedRef = useRef(false);

  const [viewMode, setViewMode] = useState<ViewMode>("2D");
  const [engineMode, setEngineMode] = useState<string>("");

  const selectedSurfacesRef = useRef<Set<string>>(new Set());

  const {
    activeMain,
    setActiveMain,
    committedLedger,
    commitCurrentService,
    selectedSurfaces,
    surfaceGeoMap,
    selectedSurfaceTotalM2,
    areaServiceDraft,
    toggleSurface,
    clearSelectedSurfaces,
    restoreFromLedgerEntry,
    liveSurfaceGeo,
    setLiveSurfaceGeo,
    applyAreaService,
    removeSurfaceFromAreaService,
    activeAreaSubService,
    setActiveAreaSubService,
    activeAreaMaterialKey,
    setActiveAreaMaterialKey,
    activeAreaMaterialLabel,
    setActiveAreaMaterialLabel,
    activeAreaMaterialColor,
    setActiveAreaMaterialColor,
  } = usePlannerState();

  selectedSurfacesRef.current = selectedSurfaces;

  const handleApi = useCallback((api: PlannerApi) => {
    apiRef.current = api;

    if (!didInitRef.current) {
      didInitRef.current = true;
      api.cmd("VIEW_2D");
      api.cmd("SELECT_TOOL_EDIT");
      setViewMode("2D");
    }
  }, []);

  useEffect(() => {
    const handleSceneSaved = (e: Event) => {
      const customEvent = e as CustomEvent<any>;
      const scene = customEvent.detail;

      if (!scene) return;

      sessionStorage.setItem(SCENE_BACKUP_KEY, JSON.stringify(scene));

      if (pendingEstimateNavRef.current) {
        pendingEstimateNavRef.current = false;
        navigate("/estimate");
      }
    };

    window.addEventListener("PLANO_SCENE_SAVED", handleSceneSaved as EventListener);

    return () => {
      window.removeEventListener("PLANO_SCENE_SAVED", handleSceneSaved as EventListener);
    };
  }, [navigate]);

  useEffect(() => {
    if (restoreAttemptedRef.current) return;
    if (!apiRef.current) return;
    if (!engineMode) return;

    const storedScene = sessionStorage.getItem(SCENE_BACKUP_KEY);
    if (!storedScene) {
      restoreAttemptedRef.current = true;
      return;
    }

    try {
      const scene = JSON.parse(storedScene);
      apiRef.current.cmd("LOAD_PROJECT_JSON", { scene });
      sessionStorage.removeItem(SCENE_BACKUP_KEY);
    } catch (error) {
      console.error("Failed to restore saved planner scene", error);
      sessionStorage.removeItem(SCENE_BACKUP_KEY);
    } finally {
      restoreAttemptedRef.current = true;
    }
  }, [engineMode]);

  const handleCatalogServiceSelected = useCallback(
    (payload: CatalogServiceSelectedPayload) => {
      const areaServices: MainService[] = [
        "painting",
        "flooring",
        "plastering",
        "boards",
      ];

      if (areaServices.includes(payload.mainService as MainService)) {
        const nextMain = payload.mainService as MainService;

        setActiveMain(nextMain);
        setActiveAreaSubService(payload.subService);
        setActiveAreaMaterialKey(payload.materialKey);
        setActiveAreaMaterialLabel(payload.materialLabel);
        setActiveAreaMaterialColor(payload.color || null);

        const existingEntry = committedLedger.find(
          (entry) =>
            entry.service === nextMain &&
            entry.subService === payload.subService &&
            entry.materialKey === payload.materialKey
        );

        if (existingEntry) {
          restoreFromLedgerEntry(existingEntry);

          setViewMode("3D");
          apiRef.current?.cmd("VIEW_3D");

          const surfaceIds = Array.from(existingEntry.surfaces.keys());

          setTimeout(() => {
            apiRef.current?.cmd("RESTORE_SURFACE_HIGHLIGHTS", { surfaceIds });
          }, 120);
        } else {
          clearSelectedSurfaces();

          setViewMode("3D");
          apiRef.current?.cmd("VIEW_3D");

          setTimeout(() => {
            apiRef.current?.cmd("RESTORE_SURFACE_HIGHLIGHTS", { surfaceIds: [] });
          }, 120);
        }
      }
    },
    [
      committedLedger,
      restoreFromLedgerEntry,
      clearSelectedSurfaces,
      setActiveMain,
      setActiveAreaSubService,
      setActiveAreaMaterialKey,
      setActiveAreaMaterialLabel,
      setActiveAreaMaterialColor,
    ]
  );

  const handleSurfaceSelected = useCallback(
    (payload: SurfaceSelectedPayload) => {
      const surfaceId = payload?.surfaceId;
      if (!surfaceId) return;

      setLiveSurfaceGeo({
        surfaceId,
        wallId: payload.wallId,
        surfaceType: payload.surfaceType,
        lengthM: payload.lengthM ?? null,
        heightM: payload.heightM ?? null,
        areaM2: payload.areaM2 ?? null,
      });

      const geo = {
        wallId: payload.wallId,
        surfaceType: payload.surfaceType,
        lengthM: payload.lengthM ?? null,
        heightM: payload.heightM ?? null,
        areaM2: payload.areaM2 ?? null,
      };

      const isAreaService =
        !!activeAreaSubService &&
        !!activeAreaMaterialKey &&
        (activeMain === "painting" ||
          activeMain === "flooring" ||
          activeMain === "plastering" ||
          activeMain === "boards");

      if (isAreaService) {
        const wasSelected = selectedSurfacesRef.current.has(surfaceId);

        toggleSurface(surfaceId, geo);

        const next = new Set(selectedSurfacesRef.current);

        if (wasSelected) {
          next.delete(surfaceId);
          selectedSurfacesRef.current = next;
          removeSurfaceFromAreaService(activeMain, surfaceId);
        } else {
          next.add(surfaceId);
          selectedSurfacesRef.current = next;
          applyAreaService(activeMain, surfaceId);
        }
      } else {
        toggleSurface(surfaceId, geo);
      }
    },
    [
      toggleSurface,
      applyAreaService,
      removeSurfaceFromAreaService,
      activeMain,
      activeAreaSubService,
      activeAreaMaterialKey,
      setLiveSurfaceGeo,
    ]
  );

  const handleSurfacesCleared = useCallback(() => {
    clearSelectedSurfaces();
    selectedSurfacesRef.current = new Set();
  }, [clearSelectedSurfaces]);

  const go2D = useCallback(() => {
    setViewMode("2D");
    apiRef.current?.cmd("VIEW_2D");
    apiRef.current?.cmd("SELECT_TOOL_EDIT");
  }, []);

  const go3D = useCallback(() => {
    setViewMode("3D");
    apiRef.current?.cmd("VIEW_3D");
  }, []);

  const openServiceCatalog = useCallback(
    (service: MainService) => {
      setActiveMain(service);
      apiRef.current?.cmd("OPEN_CATALOG");

      setTimeout(() => {
        apiRef.current?.cmd("CHANGE_CATALOG_PAGE", {
          newPage: `plano_${service}`,
          oldPage: "root",
        });
      }, 50);
    },
    [setActiveMain]
  );

  const isCatalogOpen = engineMode === "MODE_VIEWING_CATALOG";

  const currentServiceDraftCount = useMemo(() => {
    if (
      activeMain === "painting" ||
      activeMain === "flooring" ||
      activeMain === "plastering" ||
      activeMain === "boards"
    ) {
      return areaServiceDraft[activeMain].size;
    }
    return 0;
  }, [activeMain, areaServiceDraft]);

  const canCompleteService = useMemo(() => {
    const isAreaService =
      activeMain === "painting" ||
      activeMain === "flooring" ||
      activeMain === "plastering" ||
      activeMain === "boards";

    return (
      isAreaService &&
      !!activeAreaSubService &&
      !!activeAreaMaterialKey &&
      !!activeAreaMaterialLabel &&
      selectedSurfaces.size > 0 &&
      surfaceGeoMap.size > 0
    );
  }, [
    activeMain,
    activeAreaSubService,
    activeAreaMaterialKey,
    activeAreaMaterialLabel,
    selectedSurfaces,
    surfaceGeoMap,
  ]);

  const statusBox = useMemo(() => {
    if (!activeAreaSubService || !activeAreaMaterialLabel) return null;

    return {
      service: activeMain,
      subService: activeAreaSubService,
      material: activeAreaMaterialLabel,
      draftFaces: currentServiceDraftCount,
      liveFaces: selectedSurfaces.size,
    };
  }, [
    activeMain,
    activeAreaSubService,
    activeAreaMaterialLabel,
    currentServiceDraftCount,
    selectedSurfaces,
  ]);

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
        onSurfacesCleared={handleSurfacesCleared}
        onCatalogServiceSelected={handleCatalogServiceSelected}
      />

      <div className="pointer-events-none absolute left-0 right-0 top-0 z-50 flex justify-center p-2">
        <div className="pointer-events-auto glass-panel w-[calc(100vw-24px)] px-4 py-1">
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => {
                apiRef.current?.cmd("REQUEST_SCENE_JSON");
              }}
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
                  onClick={() =>
                    apiRef.current?.cmd("OPEN_PROJECT_CONFIGURATOR")
                  }
                  className="plano-glass-btn h-10 w-10 grid place-items-center"
                >
                  <Settings className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    pendingEstimateNavRef.current = true;
                    apiRef.current?.cmd("REQUEST_SCENE_JSON");
                  }}
                  disabled={committedLedger.length === 0}
                  className={`plano-glass-btn h-10 w-10 grid place-items-center ${
                    committedLedger.length > 0 ? "" : "opacity-40 cursor-not-allowed"
                  }`}
                >
                  <FileText className="h-5 w-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {!isCatalogOpen && liveSurfaceGeo ? (
        <div className="absolute left-4 top-20 z-40 rounded-xl bg-white/95 px-4 py-3 shadow-lg min-w-[220px]">
          <div className="text-sm font-semibold">PlanO selection</div>

          <div className="text-sm mt-1">Wall: {liveSurfaceGeo.wallId}</div>
          <div className="text-sm">Face: {liveSurfaceGeo.surfaceType}</div>
          <div className="text-sm">
            Length: {liveSurfaceGeo.lengthM ?? "-"} m
          </div>
          <div className="text-sm">
            Height: {liveSurfaceGeo.heightM ?? "-"} m
          </div>
          <div className="text-sm font-semibold">
            Area: {liveSurfaceGeo.areaM2 ?? "-"} m²
          </div>

          <div className="text-sm mt-2">
            Selected: {surfaceGeoMap.size} faces
          </div>
          <div className="text-sm font-semibold">
            Total: {selectedSurfaceTotalM2} m²
          </div>

          {statusBox && (
            <>
              <div className="text-sm mt-2">Service: {statusBox.service}</div>
              <div className="text-sm">Mode: {statusBox.subService}</div>
              <div className="text-sm">Material: {statusBox.material}</div>
              <div className="text-sm mt-2">
                Draft faces: {statusBox.draftFaces}
              </div>
              <div className="text-sm">
                Live clicked faces: {statusBox.liveFaces}
              </div>

              <button
                type="button"
                onClick={commitCurrentService}
                disabled={!canCompleteService}
                className={`mt-3 w-full rounded-lg px-3 py-2 text-sm font-semibold ${
                  canCompleteService
                    ? "bg-zinc-900 text-white"
                    : "bg-zinc-300 text-zinc-500 cursor-not-allowed"
                }`}
              >
                Complete Service
              </button>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
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
import ServicePanel from "../../components/planner/ServicePanel";

import {
  MAIN_SERVICES,
  usePlannerState,
  type MainService,
  type AreaService,
} from "../../state/plannerState";
import {
  AREA_SERVICE_CONFIG,
  type MaterialOption,
  type SubServiceGroup,
} from "../../config/areaServiceConfig";

type ViewMode = "2D" | "3D";

type SurfaceAppearance = {
  color: string | null;
  textureUri: string | null;
  dimensions: { w: number; h: number } | null;
};

type ActiveAreaMaterialSelection = {
  materialKey: string;
  materialLabel: string;
  subService: string;
  color: string | null;
  textureUri: string | null;
  dimensions: { w: number; h: number } | null;
};

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

function isAreaService(service: MainService): service is AreaService {
  return (
    service === "painting" ||
    service === "flooring" ||
    service === "plastering" ||
    service === "boards"
  );
}

export default function Planner() {
  const navigate = useNavigate();

  const apiRef = useRef<PlannerApi | null>(null);
  const didInitRef = useRef(false);
  const pendingEstimateNavRef = useRef(false);
  const restoreAttemptedRef = useRef(false);
  const lastPushedSurfaceColorsRef = useRef<Record<string, SurfaceAppearance>>({});

  const [viewMode, setViewMode] = useState<ViewMode>("2D");
  const [engineMode, setEngineMode] = useState<string>("");
  const [materialStripService, setMaterialStripService] = useState<AreaService | null>(null);
  const [openSubGroup, setOpenSubGroup] = useState<string | null>(null);

  const selectedSurfacesRef = useRef<Set<string>>(new Set());

  const {
    activeMain,
    setActiveMain,
    committedLedger,
    commitCurrentService,
    selectedSurfaces,
    surfaceGeoMap,
    selectedSurfaceTotalM2,
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
    setActiveAreaMaterialColor,
    setActiveAreaMaterialTextureUri,
    setActiveAreaMaterialDimensions,
  } = usePlannerState();

  selectedSurfacesRef.current = selectedSurfaces;

  const buildCommittedSurfaceAppearanceMap = useCallback(() => {
    const map: Record<string, SurfaceAppearance> = {};

    committedLedger.forEach((entry) => {
      entry.surfaces.forEach((_geo, surfaceId) => {
        map[surfaceId] = {
          color: entry.color,
          textureUri: entry.textureUri,
          dimensions: entry.dimensions,
        };
      });
    });

    return map;
  }, [committedLedger]);

  const pushCommittedSurfaceColors = useCallback(
    (forceFull: boolean = false) => {
      const nextMap = buildCommittedSurfaceAppearanceMap();
      const prevMap = lastPushedSurfaceColorsRef.current;

      const payload: Record<string, SurfaceAppearance | null> = {};

      if (forceFull) {
        Object.entries(nextMap).forEach(([surfaceId, appearance]) => {
          payload[surfaceId] = appearance;
        });
      } else {
        const allSurfaceIds = new Set([
          ...Object.keys(prevMap),
          ...Object.keys(nextMap),
        ]);

        allSurfaceIds.forEach((surfaceId) => {
          payload[surfaceId] =
            Object.prototype.hasOwnProperty.call(nextMap, surfaceId)
              ? nextMap[surfaceId]
              : null;
        });
      }

      apiRef.current?.cmd("APPLY_SURFACE_COLORS", { surfaces: payload });
      lastPushedSurfaceColorsRef.current = nextMap;
    },
    [buildCommittedSurfaceAppearanceMap]
  );

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
    if (!apiRef.current) return;
    pushCommittedSurfaceColors(false);
  }, [committedLedger, pushCommittedSurfaceColors]);

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

      setTimeout(() => {
        pushCommittedSurfaceColors(true);
      }, 220);
    } catch (error) {
      console.error("Failed to restore saved planner scene", error);
      sessionStorage.removeItem(SCENE_BACKUP_KEY);
    } finally {
      restoreAttemptedRef.current = true;
    }
  }, [engineMode, pushCommittedSurfaceColors]);

  useEffect(() => {
    setOpenSubGroup(null);
  }, [materialStripService]);

  const restoreHighlights = useCallback((surfaceIds: string[]) => {
    setTimeout(() => {
      apiRef.current?.cmd("RESTORE_SURFACE_HIGHLIGHTS", { surfaceIds });
    }, 120);
  }, []);

  const activateAreaMaterial = useCallback(
    (service: AreaService, option: ActiveAreaMaterialSelection) => {
      setActiveMain(service);
      setActiveAreaSubService(option.subService);
      setActiveAreaMaterialKey(option.materialKey);
      setActiveAreaMaterialLabel(option.materialLabel);
      setActiveAreaMaterialColor(option.color);
      setActiveAreaMaterialTextureUri(option.textureUri);
      setActiveAreaMaterialDimensions(option.dimensions);

      const existingEntry = committedLedger.find(
        (entry) =>
          entry.service === service &&
          entry.subService === option.subService &&
          entry.materialKey === option.materialKey
      );

      if (existingEntry) {
        restoreFromLedgerEntry(existingEntry);
        setViewMode("3D");
        apiRef.current?.cmd("VIEW_3D");
        restoreHighlights(Array.from(existingEntry.surfaces.keys()));

        setTimeout(() => {
          pushCommittedSurfaceColors(true);
        }, 180);
      } else {
        clearSelectedSurfaces();
        setViewMode("3D");
        apiRef.current?.cmd("VIEW_3D");
        restoreHighlights([]);

        setTimeout(() => {
          pushCommittedSurfaceColors(true);
        }, 180);
      }
    },
    [
      committedLedger,
      restoreFromLedgerEntry,
      clearSelectedSurfaces,
      restoreHighlights,
      pushCommittedSurfaceColors,
      setActiveMain,
      setActiveAreaSubService,
      setActiveAreaMaterialKey,
      setActiveAreaMaterialLabel,
      setActiveAreaMaterialColor,
      setActiveAreaMaterialTextureUri,
      setActiveAreaMaterialDimensions,
    ]
  );

  const handleCatalogServiceSelected = useCallback(
    (payload: CatalogServiceSelectedPayload) => {
      const main = payload.mainService as MainService;
      if (!isAreaService(main)) return;

      setMaterialStripService(main);
      setOpenSubGroup(null);

      activateAreaMaterial(main, {
        materialKey: payload.materialKey,
        materialLabel: payload.materialLabel,
        subService: payload.subService,
        color: payload.color || null,
        textureUri: null,
        dimensions: null,
      });
    },
    [activateAreaMaterial]
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

      const areaModeActive =
        !!activeAreaSubService &&
        !!activeAreaMaterialKey &&
        isAreaService(activeMain);

      if (areaModeActive) {
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

  const handleCommitCurrentService = useCallback(() => {
    commitCurrentService();
  }, [commitCurrentService]);

  const go2D = useCallback(() => {
    setViewMode("2D");
    setMaterialStripService(null);
    setOpenSubGroup(null);
    apiRef.current?.cmd("VIEW_2D");
    apiRef.current?.cmd("SELECT_TOOL_EDIT");
  }, []);

  const go3D = useCallback(() => {
    setViewMode("3D");
    apiRef.current?.cmd("VIEW_3D");

    setTimeout(() => {
      pushCommittedSurfaceColors(true);
    }, 180);
  }, [pushCommittedSurfaceColors]);

  const openServiceEntry = useCallback(
    (service: MainService) => {
      if (!isAreaService(service)) {
        setMaterialStripService(null);
        setOpenSubGroup(null);
        setActiveMain(service);
        apiRef.current?.cmd("OPEN_CATALOG");

        setTimeout(() => {
          apiRef.current?.cmd("CHANGE_CATALOG_PAGE", {
            newPage: `plano_${service}`,
            oldPage: "root",
          });
        }, 50);
        return;
      }

      setActiveMain(service);
      setMaterialStripService(service);
      setViewMode("3D");
      apiRef.current?.cmd("VIEW_3D");

      const serviceEntries = committedLedger.filter((entry) => entry.service === service);

      setTimeout(() => {
        pushCommittedSurfaceColors(true);
      }, 180);

      if (serviceEntries.length === 1) {
        const entry = serviceEntries[0];
        activateAreaMaterial(service, {
          materialKey: entry.materialKey,
          materialLabel: entry.materialLabel,
          subService: entry.subService,
          color: entry.color,
          textureUri: entry.textureUri,
          dimensions: entry.dimensions,
        });
      } else if (serviceEntries.length === 0) {
        clearSelectedSurfaces();
        restoreHighlights([]);
      }
    },
    [
      committedLedger,
      activateAreaMaterial,
      clearSelectedSurfaces,
      restoreHighlights,
      pushCommittedSurfaceColors,
      setActiveMain,
    ]
  );

  const handleGroupClick = useCallback(
    (service: AreaService, group: SubServiceGroup) => {
      if (group.materials.length === 0) return;

      if (group.variant === "immediate") {
        const material = group.materials[0];
        setOpenSubGroup(null);

        activateAreaMaterial(service, {
          materialKey: material.materialKey,
          materialLabel: material.materialLabel,
          subService: group.groupKey,
          color: material.color,
          textureUri: material.textureUri || null,
          dimensions: material.dimensions || null,
        });
        return;
      }

      setOpenSubGroup((prev) => (prev === group.groupKey ? null : group.groupKey));
    },
    [activateAreaMaterial]
  );

  const handleMaterialClick = useCallback(
    (service: AreaService, group: SubServiceGroup, material: MaterialOption) => {
      setOpenSubGroup(null);

      activateAreaMaterial(service, {
        materialKey: material.materialKey,
        materialLabel: material.materialLabel,
        subService: group.groupKey,
        color: material.color,
        textureUri: material.textureUri || null,
        dimensions: material.dimensions || null,
      });
    },
    [activateAreaMaterial]
  );

  const handleEntryClick = useCallback(
    (entry: {
      materialKey: string;
      materialLabel: string;
      subService: string;
      color: string | null;
      textureUri: string | null;
      dimensions: { w: number; h: number } | null;
    }) => {
      if (!materialStripService) return;

      activateAreaMaterial(materialStripService, {
        materialKey: entry.materialKey,
        materialLabel: entry.materialLabel,
        subService: entry.subService,
        color: entry.color,
        textureUri: entry.textureUri,
        dimensions: entry.dimensions,
      });
    },
    [activateAreaMaterial, materialStripService]
  );

  const isCatalogOpen = engineMode === "MODE_VIEWING_CATALOG";

  const canCompleteService = useMemo(() => {
    return (
      isAreaService(activeMain) &&
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

  const activeServiceGroups = useMemo(() => {
    if (!materialStripService) return [];
    return AREA_SERVICE_CONFIG[materialStripService] || [];
  }, [materialStripService]);

  const activeServiceEntries = useMemo(() => {
    if (!materialStripService) return [];
    return committedLedger.filter((entry) => entry.service === materialStripService);
  }, [committedLedger, materialStripService]);

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
                        onClick={() => openServiceEntry(s.key)}
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
                  title="Open full catalog"
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

      {materialStripService && viewMode === "3D" && !isCatalogOpen && (
        <ServicePanel
          service={materialStripService}
          groups={activeServiceGroups}
          openSubGroup={openSubGroup}
          activeSubService={activeAreaSubService}
          activeMaterialKey={activeAreaMaterialKey}
          committedEntries={activeServiceEntries}
          selectedCount={surfaceGeoMap.size}
          totalM2={selectedSurfaceTotalM2}
          canComplete={canCompleteService}
          onGroupClick={handleGroupClick}
          onMaterialClick={handleMaterialClick}
          onComplete={handleCommitCurrentService}
          onEntryClick={handleEntryClick}
        />
      )}

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
        </div>
      ) : null}
    </div>
  );
}
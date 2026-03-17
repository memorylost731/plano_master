import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type MainService =
  | "electricity"
  | "plumbing"
  | "painting"
  | "flooring"
  | "plastering"
  | "boards"
  | "other";

export const MAIN_SERVICES: Array<{ key: MainService; label: string }> = [
  { key: "electricity", label: "Electricity" },
  { key: "plumbing", label: "Plumbing" },
  { key: "painting", label: "Painting" },
  { key: "flooring", label: "Flooring" },
  { key: "plastering", label: "Plastering" },
  { key: "boards", label: "Boards" },
  { key: "other", label: "Other" },
];

export const SUBSERVICES: Record<MainService, string[]> = {
  electricity: [
    "Switches & plugs",
    "Overlaps with plumbing",
    "Oven",
    "Hob",
    "Fridge freezer",
    "Microwave",
    "AC",
  ],
  plumbing: [
    "Floor drain",
    "Shower cubical",
    "Bathroom sink",
    "Mixers",
    "Kitchen sink",
    "Water heater",
    "Washing machine",
    "Dishwasher",
    "Tap for water",
  ],
  painting: ["Internal paint", "External paint"],
  flooring: [
    "Ceramic tiles 60×60",
    "Ceramic tiles 120×60",
    "Ceramic tiles custom",
    "Laminate",
    "Microcement",
    "Polished concrete",
    "Parquet",
  ],
  plastering: [
    "Internal (monacote+finittura)",
    "Internal (microcement)",
    "External (GR1000)",
    "External (silicato)",
    "Stone restoration",
  ],
  boards: ["Flat ceiling", "L-shape bulkhead", "U-shape bulkhead", "Custom shapes"],
  other: ["To be defined", "Custom request", "Special works"],
};

export type AreaService = "painting" | "flooring" | "plastering" | "boards";

type AreaServiceDraft = {
  painting: Set<string>;
  flooring: Set<string>;
  plastering: Set<string>;
  boards: Set<string>;
};

type LiveSurfaceGeo = {
  surfaceId: string;
  wallId: string;
  surfaceType: "front" | "back" | "floor";
  lengthM: number | null;
  heightM: number | null;
  areaM2: number | null;
} | null;

export type SurfaceGeoEntry = {
  wallId: string;
  surfaceType: "front" | "back" | "floor";
  lengthM: number | null;
  heightM: number | null;
  areaM2: number | null;
};

export type CommittedServiceEntry = {
  ledgerId: string;
  service: AreaService;
  subService: string;
  materialKey: string;
  materialLabel: string;
  color: string | null;
  surfaces: Map<string, SurfaceGeoEntry>;
  totalM2: number;
};

type State = {
  activeMain: MainService;
  setActiveMain: (s: MainService) => void;

  selected: Record<MainService, Set<string>>;
  toggleSub: (main: MainService, sub: string) => void;
  clearAll: () => void;

  hasAnySelection: boolean;
  selectedCount: number;

  selectedSurfaces: Set<string>;
  surfaceGeoMap: Map<string, SurfaceGeoEntry>;
  selectedSurfaceTotalM2: number;
  toggleSurface: (surfaceId: string, geo?: SurfaceGeoEntry) => void;
  clearSelectedSurfaces: () => void;
  restoreFromLedgerEntry: (entry: CommittedServiceEntry) => void;

  liveSurfaceGeo: LiveSurfaceGeo;
  setLiveSurfaceGeo: (value: LiveSurfaceGeo) => void;

  areaServiceDraft: AreaServiceDraft;
  applyAreaService: (service: AreaService, surfaceId: string) => void;
  removeSurfaceFromAreaService: (service: AreaService, surfaceId: string) => void;

  activeAreaSubService: string | null;
  setActiveAreaSubService: (value: string | null) => void;
  activeAreaMaterialKey: string | null;
  setActiveAreaMaterialKey: (value: string | null) => void;
  activeAreaMaterialLabel: string | null;
  setActiveAreaMaterialLabel: (value: string | null) => void;
  activeAreaMaterialColor: string | null;
  setActiveAreaMaterialColor: (value: string | null) => void;

  committedLedger: CommittedServiceEntry[];
  commitCurrentService: () => void;
  projectTotalM2: number;
};

const KEY = "plano:plannerSelections:v1";
const Ctx = createContext<State | null>(null);

function load(): { activeMain: MainService; selected: Record<MainService, string[]> } | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;

    const activeMain = (parsed.activeMain as MainService) || "electricity";
    const sel = (parsed.selected as Record<string, string[]>) || {};

    const out: Record<MainService, string[]> = {
      electricity: sel.electricity || [],
      plumbing: sel.plumbing || [],
      painting: sel.painting || [],
      flooring: sel.flooring || [],
      plastering: sel.plastering || [],
      boards: sel.boards || [],
      other: sel.other || [],
    };

    return { activeMain, selected: out };
  } catch {
    return null;
  }
}

function save(activeMain: MainService, selected: Record<MainService, Set<string>>) {
  const payload = {
    activeMain,
    selected: {
      electricity: Array.from(selected.electricity),
      plumbing: Array.from(selected.plumbing),
      painting: Array.from(selected.painting),
      flooring: Array.from(selected.flooring),
      plastering: Array.from(selected.plastering),
      boards: Array.from(selected.boards),
      other: Array.from(selected.other),
    },
  };

  localStorage.setItem(KEY, JSON.stringify(payload));
}

export function PlannerStateProvider({ children }: { children: React.ReactNode }) {
  const initial = load();

  const [activeMain, setActiveMain] = useState<MainService>(initial?.activeMain || "electricity");

  const [selected, setSelected] = useState<Record<MainService, Set<string>>>(() => ({
    electricity: new Set(initial?.selected.electricity || []),
    plumbing: new Set(initial?.selected.plumbing || []),
    painting: new Set(initial?.selected.painting || []),
    flooring: new Set(initial?.selected.flooring || []),
    plastering: new Set(initial?.selected.plastering || []),
    boards: new Set(initial?.selected.boards || []),
    other: new Set(initial?.selected.other || []),
  }));

  const [selectedSurfaces, setSelectedSurfaces] = useState<Set<string>>(new Set());
  const [surfaceGeoMap, setSurfaceGeoMap] = useState<Map<string, SurfaceGeoEntry>>(new Map());
  const [liveSurfaceGeo, setLiveSurfaceGeo] = useState<LiveSurfaceGeo>(null);

  const [areaServiceDraft, setAreaServiceDraft] = useState<AreaServiceDraft>({
    painting: new Set(),
    flooring: new Set(),
    plastering: new Set(),
    boards: new Set(),
  });

  const [activeAreaSubService, setActiveAreaSubService] = useState<string | null>(null);
  const [activeAreaMaterialKey, setActiveAreaMaterialKey] = useState<string | null>(null);
  const [activeAreaMaterialLabel, setActiveAreaMaterialLabel] = useState<string | null>(null);
  const [activeAreaMaterialColor, setActiveAreaMaterialColor] = useState<string | null>(null);

  const [committedLedger, setCommittedLedger] = useState<CommittedServiceEntry[]>([]);

  const toggleSurface = (surfaceId: string, geo?: SurfaceGeoEntry) => {
    setSelectedSurfaces((prev) => {
      const next = new Set(prev);
      if (next.has(surfaceId)) next.delete(surfaceId);
      else next.add(surfaceId);
      return next;
    });

    setSurfaceGeoMap((prev) => {
      const next = new Map(prev);
      if (next.has(surfaceId)) next.delete(surfaceId);
      else if (geo) next.set(surfaceId, geo);
      return next;
    });
  };

  const clearSelectedSurfaces = () => {
    setSelectedSurfaces(new Set());
    setSurfaceGeoMap(new Map());
    setLiveSurfaceGeo(null);
  };

  const restoreFromLedgerEntry = (entry: CommittedServiceEntry) => {
    setSelectedSurfaces(new Set(entry.surfaces.keys()));
    setSurfaceGeoMap(new Map(entry.surfaces));
    setLiveSurfaceGeo(null);
  };

  const applyAreaService = (service: AreaService, surfaceId: string) => {
    setAreaServiceDraft((prev) => {
      const next: AreaServiceDraft = {
        painting: new Set(prev.painting),
        flooring: new Set(prev.flooring),
        plastering: new Set(prev.plastering),
        boards: new Set(prev.boards),
      };

      next[service].add(surfaceId);
      return next;
    });
  };

  const removeSurfaceFromAreaService = (service: AreaService, surfaceId: string) => {
    setAreaServiceDraft((prev) => {
      const next: AreaServiceDraft = {
        painting: new Set(prev.painting),
        flooring: new Set(prev.flooring),
        plastering: new Set(prev.plastering),
        boards: new Set(prev.boards),
      };

      next[service].delete(surfaceId);
      return next;
    });
  };

  const commitCurrentService = () => {
    const isAreaService =
      activeMain === "painting" ||
      activeMain === "flooring" ||
      activeMain === "plastering" ||
      activeMain === "boards";

    if (!isAreaService) return;
    if (!activeAreaSubService || !activeAreaMaterialKey || !activeAreaMaterialLabel) return;
    if (surfaceGeoMap.size === 0) return;

    const committedSurfaces = new Map(surfaceGeoMap);

    let totalM2 = 0;
    committedSurfaces.forEach((entry) => {
      if (entry.areaM2 !== null) totalM2 += entry.areaM2;
    });
    totalM2 = Math.round(totalM2 * 100) / 100;

    setCommittedLedger((prev) => {
      const existingIndex = prev.findIndex(
        (entry) =>
          entry.service === activeMain &&
          entry.subService === activeAreaSubService &&
          entry.materialKey === activeAreaMaterialKey
      );

      const nextEntry: CommittedServiceEntry = {
        ledgerId: existingIndex >= 0 ? prev[existingIndex].ledgerId : crypto.randomUUID(),
        service: activeMain,
        subService: activeAreaSubService,
        materialKey: activeAreaMaterialKey,
        materialLabel: activeAreaMaterialLabel,
        color: activeAreaMaterialColor,
        surfaces: committedSurfaces,
        totalM2,
      };

      if (existingIndex >= 0) {
        return prev.map((entry, index) => (index === existingIndex ? nextEntry : entry));
      }

      return [...prev, nextEntry];
    });

    clearSelectedSurfaces();
    setActiveAreaSubService(null);
    setActiveAreaMaterialKey(null);
    setActiveAreaMaterialLabel(null);
    setActiveAreaMaterialColor(null);
  };

  useEffect(() => {
    save(activeMain, selected);
  }, [activeMain, selected]);

  const toggleSub = (main: MainService, sub: string) => {
    setSelected((prev) => {
      const next: Record<MainService, Set<string>> = {
        electricity: new Set(prev.electricity),
        plumbing: new Set(prev.plumbing),
        painting: new Set(prev.painting),
        flooring: new Set(prev.flooring),
        plastering: new Set(prev.plastering),
        boards: new Set(prev.boards),
        other: new Set(prev.other),
      };

      if (next[main].has(sub)) next[main].delete(sub);
      else next[main].add(sub);

      return next;
    });
  };

  const clearAll = () => {
    setSelected({
      electricity: new Set(),
      plumbing: new Set(),
      painting: new Set(),
      flooring: new Set(),
      plastering: new Set(),
      boards: new Set(),
      other: new Set(),
    });

    clearSelectedSurfaces();
  };

  const selectedCount = useMemo(() => {
    return (
      selected.electricity.size +
      selected.plumbing.size +
      selected.painting.size +
      selected.flooring.size +
      selected.plastering.size +
      selected.boards.size +
      selected.other.size
    );
  }, [selected]);

  const selectedSurfaceTotalM2 = useMemo(() => {
    let sum = 0;
    surfaceGeoMap.forEach((entry) => {
      if (entry.areaM2 !== null) sum += entry.areaM2;
    });
    return Math.round(sum * 100) / 100;
  }, [surfaceGeoMap]);

  const projectTotalM2 = useMemo(() => {
    const total = committedLedger.reduce((sum, entry) => sum + entry.totalM2, 0);
    return Math.round(total * 100) / 100;
  }, [committedLedger]);

  const hasAnySelection = selectedCount > 0;

  const value: State = {
    activeMain,
    setActiveMain,
    selected,
    toggleSub,
    clearAll,
    hasAnySelection,
    selectedCount,
    selectedSurfaces,
    surfaceGeoMap,
    selectedSurfaceTotalM2,
    toggleSurface,
    clearSelectedSurfaces,
    restoreFromLedgerEntry,
    liveSurfaceGeo,
    setLiveSurfaceGeo,
    areaServiceDraft,
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
    committedLedger,
    commitCurrentService,
    projectTotalM2,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePlannerState() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePlannerState must be used inside PlannerStateProvider");
  return ctx;
}
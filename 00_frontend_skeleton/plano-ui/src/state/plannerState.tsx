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

type AreaService = "painting" | "flooring" | "plastering" | "boards";

type AreaServiceDraft = {
  painting: Set<string>;
  flooring: Set<string>;
  plastering: Set<string>;
  boards: Set<string>;
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
  toggleSurface: (surfaceId: string) => void;
  clearSelectedSurfaces: () => void;

  areaServiceDraft: AreaServiceDraft;
  applyAreaService: (service: AreaService) => void;
  removeSurfaceFromAreaService: (service: AreaService, surfaceId: string) => void;

  activeAreaSubService: string | null;
  setActiveAreaSubService: (value: string | null) => void;
  activeAreaMaterialKey: string | null;
  setActiveAreaMaterialKey: (value: string | null) => void;
  activeAreaMaterialLabel: string | null;
  setActiveAreaMaterialLabel: (value: string | null) => void;
  activeAreaMaterialColor: string | null;
  setActiveAreaMaterialColor: (value: string | null) => void;
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

  const toggleSurface = (surfaceId: string) => {
    setSelectedSurfaces((prev) => {
      const next = new Set(prev);

      if (next.has(surfaceId)) {
        next.delete(surfaceId);
      } else {
        next.add(surfaceId);
      }

      console.log("Selected surfaces:", Array.from(next));

      return next;
    });
  };

  const clearSelectedSurfaces = () => {
    setSelectedSurfaces(new Set());
  };

  const applyAreaService = (service: AreaService) => {
    setAreaServiceDraft((prev) => {
      const next: AreaServiceDraft = {
        painting: new Set(prev.painting),
        flooring: new Set(prev.flooring),
        plastering: new Set(prev.plastering),
        boards: new Set(prev.boards),
      };

      selectedSurfaces.forEach((surfaceId) => {
        next[service].add(surfaceId);
      });

      console.log("Area service draft:", {
        service,
        surfaces: Array.from(next[service]),
        subService: activeAreaSubService,
        materialKey: activeAreaMaterialKey,
        materialLabel: activeAreaMaterialLabel,
        color: activeAreaMaterialColor,
      });

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
    toggleSurface,
    clearSelectedSurfaces,
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
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePlannerState() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePlannerState must be used inside PlannerStateProvider");
  return ctx;
}
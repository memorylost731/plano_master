import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";

/* ── Building selection from GeoSelect map ── */
export interface SelectedBuilding {
  osmId: string;
  osmType: "way" | "relation" | "node";
  name?: string;
  buildingType?: string;
  levels?: string;
  height?: string;
  address?: string;
  material?: string;
  lat: number;
  lng: number;
  properties: Record<string, unknown>;
}

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

type State = {
  activeMain: MainService;
  setActiveMain: (s: MainService) => void;

  selected: Record<MainService, Set<string>>;
  toggleSub: (main: MainService, sub: string) => void;
  clearAll: () => void;

  hasAnySelection: boolean;
  selectedCount: number;

  /* Building from GeoSelect map */
  selectedBuilding: SelectedBuilding | null;
  setSelectedBuilding: (b: SelectedBuilding | null) => void;
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

/** ✅ This name must match your main.tsx import */
export function PlannerStateProvider({ children }: { children: React.ReactNode }) {
  const initial = load();

  const [selectedBuilding, setSelectedBuilding] = useState<SelectedBuilding | null>(null);
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

  const stableSetSelectedBuilding = useCallback((b: SelectedBuilding | null) => {
    setSelectedBuilding(b);
  }, []);

  const value: State = {
    activeMain,
    setActiveMain,
    selected,
    toggleSub,
    clearAll,
    hasAnySelection,
    selectedCount,
    selectedBuilding,
    setSelectedBuilding: stableSetSelectedBuilding,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/** ✅ This name must match Planner3D.tsx import */
export function usePlannerState() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePlannerState must be used inside PlannerStateProvider");
  return ctx;
}

import { useState, useCallback } from "react";
import { Building2, Layers, Sun, Moon, Map } from "lucide-react";
import type { Map as MaplibreMap } from "maplibre-gl";

export type MapStyle = "liberty" | "bright" | "dark";

const STYLE_URLS: Record<MapStyle, string> = {
  liberty: "https://tiles.openfreemap.org/styles/liberty",
  bright: "https://tiles.openfreemap.org/styles/bright",
  dark: "https://tiles.openfreemap.org/styles/dark",
};

const STYLE_META: Array<{ key: MapStyle; label: string; icon: React.ReactNode }> = [
  { key: "liberty", label: "Liberty", icon: <Map className="h-3.5 w-3.5" /> },
  { key: "bright", label: "Bright", icon: <Sun className="h-3.5 w-3.5" /> },
  { key: "dark", label: "Dark", icon: <Moon className="h-3.5 w-3.5" /> },
];

interface MapControlsProps {
  map: MaplibreMap | null;
  buildings3D: boolean;
  onToggleBuildings: (on: boolean) => void;
  currentStyle: MapStyle;
  onChangeStyle: (style: MapStyle) => void;
}

export { STYLE_URLS };

export default function MapControls({
  buildings3D,
  onToggleBuildings,
  currentStyle,
  onChangeStyle,
}: MapControlsProps) {
  const [expanded, setExpanded] = useState(false);

  const handleToggleBuildings = useCallback(() => {
    onToggleBuildings(!buildings3D);
  }, [buildings3D, onToggleBuildings]);

  return (
    <div className="absolute bottom-6 left-4 z-20 flex flex-col gap-2">
      {/* 3D buildings toggle */}
      <button
        onClick={handleToggleBuildings}
        className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium shadow-lg backdrop-blur-xl transition-all ${
          buildings3D
            ? "bg-blue-600 text-white border border-blue-500"
            : "bg-white/90 text-zinc-700 border border-white/30 hover:bg-white"
        }`}
        aria-label={buildings3D ? "Disable 3D buildings" : "Enable 3D buildings"}
        aria-pressed={buildings3D}
      >
        <Building2 className="h-4 w-4" />
        <span className="hidden sm:inline">3D Buildings</span>
      </button>

      {/* Style switcher */}
      <div className="relative">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/90 px-3 py-2.5 text-xs font-medium text-zinc-700 shadow-lg backdrop-blur-xl hover:bg-white transition-all"
          aria-label="Change map style"
          aria-expanded={expanded}
        >
          <Layers className="h-4 w-4" />
          <span className="hidden sm:inline">Style</span>
        </button>

        {expanded && (
          <div className="absolute bottom-full left-0 mb-2 flex flex-col gap-1 rounded-xl border border-white/30 bg-white/95 p-1.5 shadow-xl backdrop-blur-xl">
            {STYLE_META.map((s) => (
              <button
                key={s.key}
                onClick={() => {
                  onChangeStyle(s.key);
                  setExpanded(false);
                }}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors whitespace-nowrap ${
                  currentStyle === s.key
                    ? "bg-blue-50 text-blue-700"
                    : "text-zinc-600 hover:bg-zinc-50"
                }`}
              >
                {s.icon}
                {s.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

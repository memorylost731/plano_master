import { useState, useRef, useEffect, useCallback } from "react";
import { MapPin, Globe, ChevronDown } from "lucide-react";
import type { Map as MaplibreMap } from "maplibre-gl";
import {
  PLANO_CITIES,
  DEFAULT_CITY,
  getCitiesByIsland,
  type PlanOCity,
} from "../../config/cities.ts";

interface CitySelectorProps {
  map: MaplibreMap | null;
  /** Override the initial/default city (e.g. "sliema" for TSCM) */
  defaultCityId?: string;
  /** Use dark theme variant (for TSCM page) */
  dark?: boolean;
  /** Additional CSS classes for the outer wrapper (use for positioning) */
  className?: string;
}

export default function CitySelector({
  map,
  defaultCityId,
  dark = false,
  className = "",
}: CitySelectorProps) {
  const initialCity =
    (defaultCityId
      ? PLANO_CITIES.find((c) => c.id === defaultCityId)
      : undefined) || DEFAULT_CITY;

  const [currentCity, setCurrentCity] = useState<PlanOCity>(initialCity);
  const [expanded, setExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const grouped = getCitiesByIsland();
  const islandOrder: Array<"Malta" | "Gozo"> = ["Malta", "Gozo"];

  const handleSelect = useCallback(
    (city: PlanOCity) => {
      if (!city.active) return;
      setCurrentCity(city);
      setExpanded(false);

      if (map) {
        map.flyTo({
          center: city.center,
          zoom: city.zoom,
          pitch: city.pitch,
          bearing: city.bearing,
          duration: 2000,
          essential: true,
        });
      }
    },
    [map],
  );

  /* Close dropdown on outside click */
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setExpanded(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  /* ── Style tokens based on dark/light mode ── */
  const btnBase = dark
    ? "border-zinc-700/50 bg-black/70 text-zinc-200 hover:bg-black/90"
    : "border-white/30 bg-white/90 text-zinc-700 hover:bg-white";

  const panelBase = dark
    ? "border-zinc-700/50 bg-zinc-900/95"
    : "border-white/30 bg-white/95";

  const groupLabelCls = dark ? "text-zinc-500" : "text-zinc-400";

  const itemBase = dark
    ? "text-zinc-300 hover:bg-zinc-800/80"
    : "text-zinc-700 hover:bg-blue-50/80";

  const itemActiveCls = dark
    ? "bg-blue-600/20 text-blue-300"
    : "bg-blue-50 text-blue-700";

  const comingSoonCls = dark
    ? "text-zinc-600 cursor-not-allowed"
    : "text-zinc-400 cursor-not-allowed";

  return (
    <div ref={containerRef} className={`absolute z-20 ${className}`}>
      {/* Compact trigger button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 text-xs font-medium shadow-lg backdrop-blur-xl transition-all ${btnBase}`}
        aria-label="Select city"
        aria-expanded={expanded}
        aria-haspopup="listbox"
      >
        <Globe className="h-4 w-4 shrink-0" />
        <span>{currentCity.name}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`}
        />
      </button>

      {/* Expanded city list */}
      {expanded && (
        <div
          role="listbox"
          aria-label="City selection"
          className={`absolute bottom-full left-0 mb-2 w-56 max-h-80 overflow-y-auto rounded-xl border p-2 shadow-xl backdrop-blur-xl ${panelBase}`}
        >
          {islandOrder.map((island) => {
            const cities = grouped[island];
            if (!cities?.length) return null;

            return (
              <div key={island} className="mb-1 last:mb-0">
                {/* Island header */}
                <div
                  className={`flex items-center gap-2 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider ${groupLabelCls}`}
                >
                  <span>{island}</span>
                </div>

                {/* Cities */}
                {cities.map((city) => {
                  const isSelected = city.id === currentCity.id;
                  const isActive = city.active;

                  return (
                    <button
                      key={city.id}
                      role="option"
                      aria-selected={isSelected}
                      aria-disabled={!isActive}
                      onClick={() => handleSelect(city)}
                      disabled={!isActive}
                      className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                        !isActive
                          ? comingSoonCls
                          : isSelected
                            ? itemActiveCls
                            : itemBase
                      }`}
                    >
                      <MapPin
                        className={`h-3 w-3 shrink-0 ${
                          !isActive
                            ? "opacity-30"
                            : isSelected
                              ? ""
                              : "opacity-60"
                        }`}
                      />
                      <span className="truncate">{city.name}</span>
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

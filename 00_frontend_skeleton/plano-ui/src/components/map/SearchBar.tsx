import { useState, useRef, useCallback, useEffect } from "react";
import { Search, X, MapPin, Globe, Building2, Loader2 } from "lucide-react";
import type { Map as MaplibreMap } from "maplibre-gl";

interface NominatimResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  type: string;
  class: string;
  addresstype: string;
  boundingbox: [string, string, string, string];
  osm_type: string;
  osm_id: number;
}

interface SearchBarProps {
  map: MaplibreMap | null;
}

function getZoomForType(result: NominatimResult): number {
  const type = result.addresstype || result.type;
  if (["country", "continent"].includes(type)) return 5;
  if (["state", "region", "province"].includes(type)) return 7;
  if (["county", "district"].includes(type)) return 9;
  if (["city", "town", "municipality", "village"].includes(type)) return 13;
  if (["suburb", "neighbourhood", "quarter"].includes(type)) return 15;
  if (["building", "house", "amenity", "shop"].includes(type)) return 18;
  if (["road", "street"].includes(type)) return 16;
  return 14;
}

function getIcon(result: NominatimResult) {
  const type = result.addresstype || result.type;
  if (["country", "continent", "state", "region"].includes(type)) {
    return <Globe className="h-4 w-4 shrink-0 text-zinc-400" />;
  }
  if (["building", "house", "amenity", "shop"].includes(type)) {
    return <Building2 className="h-4 w-4 shrink-0 text-zinc-400" />;
  }
  return <MapPin className="h-4 w-4 shrink-0 text-zinc-400" />;
}

export default function SearchBar({ map }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<NominatimResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    setLoading(true);
    try {
      const url = new URL("https://nominatim.openstreetmap.org/search");
      url.searchParams.set("q", q);
      url.searchParams.set("format", "json");
      url.searchParams.set("limit", "8");
      url.searchParams.set("addressdetails", "1");

      const res = await fetch(url.toString(), {
        headers: { "Accept-Language": "en" },
      });
      if (!res.ok) return;
      const data: NominatimResult[] = await res.json();
      setResults(data);
      setIsOpen(data.length > 0);
    } catch {
      /* network error — silently ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInput = useCallback(
    (value: string) => {
      setQuery(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => search(value), 300);
    },
    [search],
  );

  const handleSelect = useCallback(
    (result: NominatimResult) => {
      if (!map) return;
      const zoom = getZoomForType(result);
      map.flyTo({
        center: [parseFloat(result.lon), parseFloat(result.lat)],
        zoom,
        pitch: zoom >= 15 ? 60 : zoom >= 10 ? 45 : 0,
        bearing: 0,
        duration: 2000,
        essential: true,
      });
      setQuery(result.display_name.split(",")[0]);
      setIsOpen(false);
    },
    [map],
  );

  const handleClear = useCallback(() => {
    setQuery("");
    setResults([]);
    setIsOpen(false);
  }, []);

  /* Close dropdown on outside click */
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={containerRef} className="absolute top-4 left-4 right-4 z-30 sm:left-auto sm:right-4 sm:w-96">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400 pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleInput(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder="Search city, country, or address..."
          aria-label="Search location"
          aria-expanded={isOpen}
          aria-autocomplete="list"
          role="combobox"
          className="w-full rounded-xl border border-white/30 bg-white/90 py-3 pl-10 pr-10 text-sm shadow-lg backdrop-blur-xl outline-none placeholder:text-zinc-400 focus:ring-2 focus:ring-blue-500/40"
        />
        {loading && (
          <Loader2 className="absolute right-10 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-zinc-400" />
        )}
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-0.5 text-zinc-400 hover:text-zinc-600"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {isOpen && results.length > 0 && (
        <ul
          role="listbox"
          className="mt-1 max-h-72 overflow-y-auto rounded-xl border border-white/30 bg-white/95 shadow-xl backdrop-blur-xl"
        >
          {results.map((r) => (
            <li key={r.place_id}>
              <button
                role="option"
                onClick={() => handleSelect(r)}
                className="flex w-full items-start gap-3 px-4 py-3 text-left text-sm hover:bg-blue-50/80 transition-colors"
              >
                {getIcon(r)}
                <div className="min-w-0">
                  <div className="font-medium text-zinc-900 truncate">
                    {r.display_name.split(",")[0]}
                  </div>
                  <div className="text-xs text-zinc-500 truncate">
                    {r.display_name.split(",").slice(1).join(",").trim()}
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

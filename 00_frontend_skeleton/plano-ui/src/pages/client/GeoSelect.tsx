import { useRef, useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { MapPin, Home, Building2, Wrench } from "lucide-react";

/* ── Geo data (Ogi's location/pricing model) ── */

const GEO_DATA: Record<string, { cities: string[]; center: [number, number]; zoom: number }> = {
  Malta: {
    cities: ["Valletta", "Sliema", "St Julian's", "Birkirkara", "Mosta", "Gzira", "San Gwann", "Msida"],
    center: [14.5146, 35.8989],
    zoom: 14,
  },
  Bulgaria: {
    cities: ["Sofia", "Plovdiv", "Varna", "Burgas", "Stara Zagora", "Ruse", "Pleven"],
    center: [23.3219, 42.6977],
    zoom: 12,
  },
};

const CITY_COORDS: Record<string, [number, number]> = {
  // Malta
  Valletta: [14.5146, 35.8989],
  Sliema: [14.5020, 35.9116],
  "St Julian's": [14.4905, 35.9186],
  Birkirkara: [14.4615, 35.8969],
  Mosta: [14.4261, 35.9092],
  Gzira: [14.4946, 35.9060],
  "San Gwann": [14.4752, 35.9048],
  Msida: [14.4880, 35.8961],
  // Bulgaria
  Sofia: [23.3219, 42.6977],
  Plovdiv: [24.7489, 42.1354],
  Varna: [27.9147, 43.2141],
  Burgas: [27.4626, 42.5048],
  "Stara Zagora": [25.6255, 42.4258],
  Ruse: [25.9657, 43.8486],
  Pleven: [24.6167, 43.4170],
};

type ServiceType = "refurbishing" | "new" | "individual";

/* ================================================================
   MapBackground — lazy loaded, failure-tolerant
   ================================================================ */

function MapBackground({
  country,
  city,
}: {
  country: string;
  city: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    let map: any;
    let cancelled = false;

    (async () => {
      try {
        const mod = await import("maplibre-gl");
        const maplibregl = mod.default;
        // CSS import may fail in production (already bundled) — ignore
        try { await import("maplibre-gl/dist/maplibre-gl.css"); } catch { /* ok */ }

        if (cancelled || !containerRef.current) return;

        // Ensure container has dimensions
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) {
          console.warn("[PlanO] Map container has zero dimensions, skipping map");
          return;
        }

        map = new maplibregl.Map({
          container: containerRef.current,
          style: "https://tiles.openfreemap.org/styles/liberty",
          center: [14.5146, 35.8989],
          zoom: 16,
          pitch: 60,
          bearing: -20,
          maxPitch: 85,
          attributionControl: {},
        });

        map.addControl(
          new maplibregl.NavigationControl({ visualizePitch: true }),
          "top-left",
        );
        map.addControl(new maplibregl.ScaleControl({ maxWidth: 150, unit: "metric" }), "bottom-right");

        map.on("style.load", () => {
          // Add 3D buildings
          const style = map.getStyle();
          if (!style?.sources) return;
          const sourceId = Object.keys(style.sources).find(
            (id) => style.sources[id].type === "vector",
          );
          if (!sourceId) return;

          const layers = style.layers || [];
          let labelLayerId: string | undefined;
          for (const layer of layers) {
            if (layer.type === "symbol" && (layer as any)["source-layer"]) {
              labelLayerId = layer.id;
              break;
            }
          }

          map.addLayer(
            {
              id: "building-3d",
              source: sourceId,
              "source-layer": "building",
              type: "fill-extrusion",
              minzoom: 14,
              paint: {
                "fill-extrusion-color": [
                  "interpolate", ["linear"],
                  ["coalesce", ["get", "render_height"], ["get", "height"], 10],
                  0, "#e8edf3", 10, "#c5cfe0", 20, "#8ea4c2",
                  40, "#5a7ba8", 80, "#3d5a80", 150, "#1b3a5c",
                ],
                "fill-extrusion-height": ["coalesce", ["get", "render_height"], ["get", "height"], 10],
                "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
                "fill-extrusion-opacity": 0.85,
              },
            },
            labelLayerId,
          );
        });

        map.on("load", () => {
          if (!cancelled) mapRef.current = map;
        });

        map.on("error", () => {
          if (!cancelled) setFailed(true);
        });
      } catch (err) {
        console.error("[PlanO] Map failed to load:", err);
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
      if (map) {
        try { map.remove(); } catch { /* ignore */ }
      }
      mapRef.current = null;
    };
  }, []);

  // Fly on country/city change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    try {
      if (city && CITY_COORDS[city]) {
        map.flyTo({ center: CITY_COORDS[city], zoom: 16, pitch: 60, bearing: -20, duration: 2000 });
      } else if (country && GEO_DATA[country]) {
        const geo = GEO_DATA[country];
        map.flyTo({ center: geo.center, zoom: geo.zoom, pitch: geo.zoom >= 14 ? 60 : 30, bearing: -20, duration: 2000 });
      }
    } catch { /* ignore flyTo errors */ }
  }, [country, city]);

  if (failed) return null;

  return <div ref={containerRef} className="absolute inset-0 w-full h-full" />;
}

/* ================================================================
   GeoSelect — Form-first, map as background enhancement
   ================================================================ */

export default function GeoSelect() {
  const navigate = useNavigate();

  const countries = useMemo(() => Object.keys(GEO_DATA), []);
  const [country, setCountry] = useState("Malta");
  const cities = country ? GEO_DATA[country]?.cities ?? [] : [];
  const [city, setCity] = useState("");
  const [serviceType, setServiceType] = useState<ServiceType>("refurbishing");
  const [mapSupported, setMapSupported] = useState(true);

  // Check WebGL support on mount
  useEffect(() => {
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (!gl) setMapSupported(false);
    } catch {
      setMapSupported(false);
    }
  }, []);

  const canContinue =
    country.length > 0 &&
    (cities.length === 0 || city.length > 0) &&
    !!serviceType;

  function handleContinue() {
    navigate("/planner");
  }

  return (
    <div className="fixed inset-0 w-screen h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-slate-200">
      {/* Map background (lazy, optional) */}
      {mapSupported && (
        <MapBackground country={country} city={city} />
      )}

      {/* PlanO branding — always visible */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-2">
        <div className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/90 px-4 py-2.5 shadow-lg backdrop-blur-xl">
          <svg
            className="h-5 w-5 text-zinc-900"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            <polyline points="9,22 9,12 15,12 15,22" />
          </svg>
          <span className="text-sm font-bold text-zinc-900 tracking-tight">PlanO</span>
        </div>
      </div>

      {/* Form panel — ALWAYS visible, z-30 */}
      <div className="absolute bottom-6 right-4 z-30 w-[340px] sm:w-[380px]">
        <div className="rounded-2xl border border-zinc-200 bg-white shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="border-b border-zinc-100 px-5 py-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-zinc-600" />
              <span className="text-sm font-semibold text-zinc-900">Location & Service</span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">
              {mapSupported ? "Select or click a building on the map" : "Select your location and service type"}
            </p>
          </div>

          {/* Location selectors */}
          <div className="px-5 py-4 space-y-3">
            <div className="grid gap-3 grid-cols-2">
              <label className="space-y-1">
                <div className="text-xs font-medium text-zinc-600">Country</div>
                <select
                  value={country}
                  onChange={(e) => { setCountry(e.target.value); setCity(""); }}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm"
                >
                  <option value="">Select...</option>
                  {countries.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <div className="text-xs font-medium text-zinc-600">City</div>
                <select
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  disabled={!country || cities.length === 0}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-sm disabled:opacity-50"
                >
                  <option value="">{cities.length ? "Select..." : "N/A"}</option>
                  {cities.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>
            </div>

            {/* Service type */}
            <div className="space-y-1.5">
              <div className="text-xs font-medium text-zinc-600">Service type</div>
              <div className="grid grid-cols-3 gap-2">
                {([
                  { key: "refurbishing" as ServiceType, label: "Refurbish", icon: <Home className="h-3.5 w-3.5" /> },
                  { key: "new" as ServiceType, label: "New build", icon: <Building2 className="h-3.5 w-3.5" /> },
                  { key: "individual" as ServiceType, label: "Single", icon: <Wrench className="h-3.5 w-3.5" /> },
                ]).map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setServiceType(opt.key)}
                    className={`flex flex-col items-center gap-1 rounded-xl border px-2 py-2.5 text-xs font-medium transition-all ${
                      serviceType === opt.key
                        ? "border-zinc-900 bg-zinc-900 text-white shadow-md"
                        : "border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50"
                    }`}
                  >
                    {opt.icon}
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Continue button */}
          <div className="border-t border-zinc-100 px-5 py-3">
            <button
              disabled={!canContinue}
              onClick={handleContinue}
              className="w-full rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Continue to Planner
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

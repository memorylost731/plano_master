import { useRef, useEffect, useState, useCallback, useMemo } from "react";
import { createRoot } from "react-dom/client";
import { useNavigate, BrowserRouter } from "react-router-dom";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapPin, Home, Building2, Wrench } from "lucide-react";

import SearchBar from "../../components/map/SearchBar";
import BuildingPopup from "../../components/map/BuildingPopup";
import MapControls, {
  STYLE_URLS,
  type MapStyle,
} from "../../components/map/MapControls";
import { PlannerStateProvider } from "../../state/plannerState";
import type { SelectedBuilding } from "../../types/building";

/* ── Geo data (Ogi's location/pricing model) ── */

const GEO_DATA: Record<string, { cities: string[]; center: [number, number]; zoom: number }> = {
  Malta: {
    cities: ["Valletta", "Sliema", "St Julian's", "Birkirkara", "Mosta"],
    center: [14.5146, 35.8989],
    zoom: 14,
  },
  Italy: {
    cities: ["Rome", "Milan", "Turin", "Naples"],
    center: [12.4964, 41.9028],
    zoom: 12,
  },
  UK: {
    cities: ["London", "Manchester", "Birmingham"],
    center: [-0.1276, 51.5074],
    zoom: 12,
  },
};

const CITY_COORDS: Record<string, [number, number]> = {
  Valletta: [14.5146, 35.8989],
  Sliema: [14.5020, 35.9116],
  "St Julian's": [14.4905, 35.9186],
  Birkirkara: [14.4615, 35.8969],
  Mosta: [14.4261, 35.9092],
  Rome: [12.4964, 41.9028],
  Milan: [9.1900, 45.4642],
  Turin: [7.6869, 45.0703],
  Naples: [14.2681, 40.8518],
  London: [-0.1276, 51.5074],
  Manchester: [-2.2426, 53.4808],
  Birmingham: [-1.8904, 52.4862],
};

type ServiceType = "refurbishing" | "new" | "individual";

/* ── Map constants ── */

const INITIAL_CENTER: [number, number] = [14.5146, 35.8989];
const INITIAL_ZOOM = 16;
const INITIAL_PITCH = 60;
const INITIAL_BEARING = -20;

const BUILDING_SOURCE_LAYER = "building";
const HIGHLIGHT_LAYER_ID = "building-3d-highlight";
const BUILDINGS_LAYER_ID = "building-3d";

/* ── Helpers ── */

function buildAddress(props: Record<string, unknown>): string {
  const parts: string[] = [];
  const street = props["addr:street"] as string | undefined;
  const number = props["addr:housenumber"] as string | undefined;
  const city = props["addr:city"] as string | undefined;
  const postcode = props["addr:postcode"] as string | undefined;
  if (number) parts.push(number);
  if (street) parts.push(street);
  if (city) parts.push(city);
  if (postcode) parts.push(postcode);
  return parts.join(", ");
}

function featureToBuilding(
  feature: maplibregl.MapGeoJSONFeature,
  lngLat: maplibregl.LngLat,
): SelectedBuilding {
  const p = feature.properties as Record<string, unknown>;
  return {
    osmId: String(feature.id ?? p["osm_id"] ?? p["id"] ?? "unknown"),
    osmType: (p["osm_type"] as "way" | "relation") || "way",
    name: (p["name"] as string) || undefined,
    buildingType: (p["building"] as string) || (p["type"] as string) || undefined,
    levels: (p["building:levels"] as string) || (p["levels"] as string) || undefined,
    height: (p["height"] as string) || (p["render_height"] as string) || undefined,
    address: buildAddress(p) || undefined,
    material: (p["building:material"] as string) || undefined,
    lat: lngLat.lat,
    lng: lngLat.lng,
    properties: p,
  };
}

/* ── 3D building layers ── */

function add3DBuildingLayers(map: maplibregl.Map) {
  const style = map.getStyle();
  if (!style?.sources) return;

  const sourceId = Object.keys(style.sources).find((id) => {
    const src = style.sources[id];
    return src.type === "vector";
  });
  if (!sourceId) return;

  if (map.getLayer(BUILDINGS_LAYER_ID)) map.removeLayer(BUILDINGS_LAYER_ID);
  if (map.getLayer(HIGHLIGHT_LAYER_ID)) map.removeLayer(HIGHLIGHT_LAYER_ID);

  const layers = style.layers || [];
  let labelLayerId: string | undefined;
  for (const layer of layers) {
    if (layer.type === "symbol" && (layer as Record<string, unknown>)["source-layer"]) {
      labelLayerId = layer.id;
      break;
    }
  }

  map.addLayer(
    {
      id: BUILDINGS_LAYER_ID,
      source: sourceId,
      "source-layer": BUILDING_SOURCE_LAYER,
      type: "fill-extrusion",
      minzoom: 14,
      filter: ["all", ["!=", "hide_3d", true]],
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

  map.addLayer(
    {
      id: HIGHLIGHT_LAYER_ID,
      source: sourceId,
      "source-layer": BUILDING_SOURCE_LAYER,
      type: "fill-extrusion",
      minzoom: 14,
      filter: ["==", ["id"], ""],
      paint: {
        "fill-extrusion-color": "#3b82f6",
        "fill-extrusion-height": ["coalesce", ["get", "render_height"], ["get", "height"], 10],
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        "fill-extrusion-opacity": 0.9,
      },
    },
    labelLayerId,
  );
}

function addSkyLayer(map: maplibregl.Map) {
  if (map.getLayer("sky")) return;
  map.addLayer({
    id: "sky",
    type: "sky" as unknown as "background",
    paint: {
      "sky-type": "atmosphere",
      "sky-atmosphere-sun": [0, 0],
      "sky-atmosphere-sun-intensity": 15,
    } as unknown as maplibregl.BackgroundLayerSpecification["paint"],
  });
}

/* ================================================================
   GeoSelect — Ogi's form + 3D map
   ================================================================ */

export default function GeoSelect() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  const [mapReady, setMapReady] = useState(false);
  const [buildings3D, setBuildings3D] = useState(true);
  const [currentStyle, setCurrentStyle] = useState<MapStyle>("liberty");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | number | null>(null);

  /* ── Ogi's form state ── */
  const countries = useMemo(() => Object.keys(GEO_DATA), []);
  const [country, setCountry] = useState("Malta");
  const cities = country ? GEO_DATA[country]?.cities ?? [] : [];
  const [city, setCity] = useState("");
  const [serviceType, setServiceType] = useState<ServiceType>("refurbishing");

  const canContinue =
    country.length > 0 &&
    (cities.length === 0 || city.length > 0) &&
    !!serviceType;

  function handleContinue() {
    if (serviceType === "individual") {
      navigate("/planner");
    } else {
      navigate("/planner");
    }
  }

  /* ── Fly map when country/city changes ── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    if (city && CITY_COORDS[city]) {
      map.flyTo({
        center: CITY_COORDS[city],
        zoom: 16,
        pitch: 60,
        bearing: -20,
        duration: 2000,
        essential: true,
      });
    } else if (country && GEO_DATA[country]) {
      const geo = GEO_DATA[country];
      map.flyTo({
        center: geo.center,
        zoom: geo.zoom,
        pitch: geo.zoom >= 14 ? 60 : 30,
        bearing: -20,
        duration: 2000,
        essential: true,
      });
    }
  }, [country, city, mapReady]);

  /* ── Initialize map ── */
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URLS[currentStyle],
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      pitch: INITIAL_PITCH,
      bearing: INITIAL_BEARING,
      maxPitch: 85,
      attributionControl: {},
    });

    map.addControl(
      new maplibregl.NavigationControl({ visualizePitch: true, showCompass: true, showZoom: true }),
      "top-left",
    );
    map.addControl(
      new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: true }),
      "top-left",
    );
    map.addControl(new maplibregl.FullscreenControl(), "top-left");
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 150, unit: "metric" }), "bottom-right");

    map.on("style.load", () => {
      if (buildings3D) add3DBuildingLayers(map);
      addSkyLayer(map);
    });

    map.on("load", () => {
      mapRef.current = map;
      setMapReady(true);
    });

    return () => {
      mapRef.current = null;
      setMapReady(false);
      map.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Building click ── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      if (!map.getLayer(BUILDINGS_LAYER_ID)) return;

      const features = map.queryRenderedFeatures(e.point, { layers: [BUILDINGS_LAYER_ID] });

      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }

      if (!features.length) {
        if (map.getLayer(HIGHLIGHT_LAYER_ID)) {
          map.setFilter(HIGHLIGHT_LAYER_ID, ["==", ["id"], ""]);
        }
        setSelectedFeatureId(null);
        return;
      }

      const feature = features[0];
      const building = featureToBuilding(feature, e.lngLat);

      const fid = feature.id;
      if (fid != null && map.getLayer(HIGHLIGHT_LAYER_ID)) {
        map.setFilter(HIGHLIGHT_LAYER_ID, ["==", ["id"], fid]);
        setSelectedFeatureId(fid);
      }

      const popupNode = document.createElement("div");
      const root = createRoot(popupNode);
      root.render(
        <BrowserRouter>
          <PlannerStateProvider>
            <BuildingPopup
              building={building}
              onClose={() => {
                popup.remove();
                if (map.getLayer(HIGHLIGHT_LAYER_ID)) {
                  map.setFilter(HIGHLIGHT_LAYER_ID, ["==", ["id"], ""]);
                }
                setSelectedFeatureId(null);
              }}
            />
          </PlannerStateProvider>
        </BrowserRouter>,
      );

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        maxWidth: "none",
        offset: 10,
        className: "plano-map-popup",
      })
        .setLngLat(e.lngLat)
        .setDOMContent(popupNode)
        .addTo(map);

      popupRef.current = popup;
    };

    map.on("click", handleClick);

    const handleMouseEnter = () => { map.getCanvas().style.cursor = "pointer"; };
    const handleMouseLeave = () => { map.getCanvas().style.cursor = ""; };

    if (map.getLayer(BUILDINGS_LAYER_ID)) {
      map.on("mouseenter", BUILDINGS_LAYER_ID, handleMouseEnter);
      map.on("mouseleave", BUILDINGS_LAYER_ID, handleMouseLeave);
    }

    return () => {
      map.off("click", handleClick);
      if (map.getLayer(BUILDINGS_LAYER_ID)) {
        map.off("mouseenter", BUILDINGS_LAYER_ID, handleMouseEnter);
        map.off("mouseleave", BUILDINGS_LAYER_ID, handleMouseLeave);
      }
    };
  }, [mapReady, selectedFeatureId]);

  /* ── Toggle 3D buildings ── */
  const handleToggleBuildings = useCallback((on: boolean) => {
    setBuildings3D(on);
    const map = mapRef.current;
    if (!map) return;
    if (on) {
      if (!map.getLayer(BUILDINGS_LAYER_ID)) add3DBuildingLayers(map);
    } else {
      if (map.getLayer(BUILDINGS_LAYER_ID)) map.removeLayer(BUILDINGS_LAYER_ID);
      if (map.getLayer(HIGHLIGHT_LAYER_ID)) map.removeLayer(HIGHLIGHT_LAYER_ID);
    }
  }, []);

  /* ── Style change ── */
  const handleStyleChange = useCallback((style: MapStyle) => {
    setCurrentStyle(style);
    mapRef.current?.setStyle(STYLE_URLS[style]);
  }, []);

  return (
    <div className="fixed inset-0 w-screen h-screen">
      {/* 3D Map (full background) */}
      <div ref={containerRef} className="absolute inset-0 w-full h-full" />

      {/* Search bar */}
      <SearchBar map={mapReady ? mapRef.current : null} />

      {/* Map controls */}
      <MapControls
        map={mapReady ? mapRef.current : null}
        buildings3D={buildings3D}
        onToggleBuildings={handleToggleBuildings}
        currentStyle={currentStyle}
        onChangeStyle={handleStyleChange}
      />

      {/* PlanO branding */}
      <div className="absolute top-4 left-4 z-20 hidden sm:flex items-center gap-2">
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

      {/* ── Ogi's form panel (glass overlay, bottom-right) ── */}
      <div className="absolute bottom-6 right-4 z-30 w-[340px] sm:w-[380px]">
        <div className="rounded-2xl border border-white/30 bg-white/90 shadow-2xl backdrop-blur-xl overflow-hidden">
          {/* Header */}
          <div className="border-b border-zinc-100 px-5 py-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-zinc-600" />
              <span className="text-sm font-semibold text-zinc-900">Location & Service</span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">
              Select or click a building on the map
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

      {/* Loading state */}
      {!mapReady && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-zinc-900">
          <div className="flex flex-col items-center gap-4">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-400 border-t-transparent" />
            <p className="text-sm text-zinc-400 font-medium">Loading map...</p>
          </div>
        </div>
      )}
    </div>
  );
}

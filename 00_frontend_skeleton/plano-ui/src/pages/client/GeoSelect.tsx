import { useRef, useEffect, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import SearchBar from "../../components/map/SearchBar.tsx";
import BuildingPopup from "../../components/map/BuildingPopup.tsx";
import MapControls, {
  STYLE_URLS,
  type MapStyle,
} from "../../components/map/MapControls.tsx";
import { PlannerStateProvider, type SelectedBuilding } from "../../state/plannerState.tsx";

/* ── Constants ── */
const INITIAL_CENTER: [number, number] = [14.5146, 35.8989]; // Valletta, Malta
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

/* ── Add 3D building layers ── */
function add3DBuildingLayers(map: maplibregl.Map) {
  /* Find the source that contains building data.
     OpenFreeMap uses "openmaptiles" as the source ID. */
  const style = map.getStyle();
  if (!style?.sources) return;

  const sourceId = Object.keys(style.sources).find((id) => {
    const src = style.sources[id];
    return src.type === "vector";
  });
  if (!sourceId) return;

  /* Remove existing layers if present (style change) */
  if (map.getLayer(BUILDINGS_LAYER_ID)) map.removeLayer(BUILDINGS_LAYER_ID);
  if (map.getLayer(HIGHLIGHT_LAYER_ID)) map.removeLayer(HIGHLIGHT_LAYER_ID);

  /* Find the first symbol layer to insert buildings below labels */
  const layers = style.layers || [];
  let labelLayerId: string | undefined;
  for (const layer of layers) {
    if (layer.type === "symbol" && (layer as Record<string, unknown>)["source-layer"]) {
      labelLayerId = layer.id;
      break;
    }
  }

  /* Main 3D building extrusions */
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
          "interpolate",
          ["linear"],
          ["coalesce", ["get", "render_height"], ["get", "height"], 10],
          0,
          "#e8edf3",
          10,
          "#c5cfe0",
          20,
          "#8ea4c2",
          40,
          "#5a7ba8",
          80,
          "#3d5a80",
          150,
          "#1b3a5c",
        ],
        "fill-extrusion-height": [
          "coalesce",
          ["get", "render_height"],
          ["get", "height"],
          10,
        ],
        "fill-extrusion-base": [
          "coalesce",
          ["get", "render_min_height"],
          0,
        ],
        "fill-extrusion-opacity": 0.85,
      },
    },
    labelLayerId,
  );

  /* Highlight layer for selected building */
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
        "fill-extrusion-height": [
          "coalesce",
          ["get", "render_height"],
          ["get", "height"],
          10,
        ],
        "fill-extrusion-base": [
          "coalesce",
          ["get", "render_min_height"],
          0,
        ],
        "fill-extrusion-opacity": 0.9,
      },
    },
    labelLayerId,
  );
}

/* ── Add sky layer ── */
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
   GeoSelect Component
   ================================================================ */
export default function GeoSelect() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  const [mapReady, setMapReady] = useState(false);
  const [buildings3D, setBuildings3D] = useState(true);
  const [currentStyle, setCurrentStyle] = useState<MapStyle>("liberty");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | number | null>(null);

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

    /* Navigation controls */
    map.addControl(
      new maplibregl.NavigationControl({
        visualizePitch: true,
        showCompass: true,
        showZoom: true,
      }),
      "top-left",
    );

    /* Geolocate control */
    map.addControl(
      new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
      }),
      "top-left",
    );

    /* Fullscreen control */
    map.addControl(new maplibregl.FullscreenControl(), "top-left");

    /* Scale bar */
    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 150, unit: "metric" }),
      "bottom-right",
    );

    map.on("style.load", () => {
      if (buildings3D) {
        add3DBuildingLayers(map);
      }
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
    // Only run on mount — style changes handled separately
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Building click handler ── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      if (!map.getLayer(BUILDINGS_LAYER_ID)) return;

      const features = map.queryRenderedFeatures(e.point, {
        layers: [BUILDINGS_LAYER_ID],
      });

      /* Close existing popup */
      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }

      if (!features.length) {
        /* Clear highlight */
        if (map.getLayer(HIGHLIGHT_LAYER_ID)) {
          map.setFilter(HIGHLIGHT_LAYER_ID, ["==", ["id"], ""]);
        }
        setSelectedFeatureId(null);
        return;
      }

      const feature = features[0];
      const building = featureToBuilding(feature, e.lngLat);

      /* Highlight */
      const fid = feature.id;
      if (fid != null && map.getLayer(HIGHLIGHT_LAYER_ID)) {
        map.setFilter(HIGHLIGHT_LAYER_ID, ["==", ["id"], fid]);
        setSelectedFeatureId(fid);
      }

      /* Popup */
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

    /* Cursor change on hover */
    const handleMouseEnter = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
    };

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
  const handleToggleBuildings = useCallback(
    (on: boolean) => {
      setBuildings3D(on);
      const map = mapRef.current;
      if (!map) return;

      if (on) {
        if (!map.getLayer(BUILDINGS_LAYER_ID)) {
          add3DBuildingLayers(map);
        }
      } else {
        if (map.getLayer(BUILDINGS_LAYER_ID)) map.removeLayer(BUILDINGS_LAYER_ID);
        if (map.getLayer(HIGHLIGHT_LAYER_ID)) map.removeLayer(HIGHLIGHT_LAYER_ID);
      }
    },
    [],
  );

  /* ── Style change ── */
  const handleStyleChange = useCallback(
    (style: MapStyle) => {
      setCurrentStyle(style);
      const map = mapRef.current;
      if (!map) return;

      map.setStyle(STYLE_URLS[style]);
      /* style.load event will re-add building layers automatically */
    },
    [],
  );

  return (
    <div className="fixed inset-0 w-screen h-screen">
      {/* Map container */}
      <div ref={containerRef} className="absolute inset-0 w-full h-full" />

      {/* Search bar overlay */}
      <SearchBar map={mapReady ? mapRef.current : null} />

      {/* Map controls overlay */}
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

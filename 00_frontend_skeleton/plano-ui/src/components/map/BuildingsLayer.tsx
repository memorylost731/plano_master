import { useEffect, useRef, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import maplibregl from "maplibre-gl";
import type { Map as MaplibreMap } from "maplibre-gl";
import {
  Building2,
  Layers,
  Ruler,
  MapPin,
  Palette,
  Radio,
  Shield,
  Loader2,
  X,
  Hash,
} from "lucide-react";
import { getCityById, type PlanOCity } from "../../config/cities.ts";

/* ── Constants ── */
const SOURCE_ID = "plano-buildings";
const LAYER_ID = "plano-buildings-3d";
const BASE_LAYER_ID = "building-3d"; // the OpenFreeMap base layer

/* ── Types for enriched GeoJSON properties ── */
interface EnrichedBuildingProps {
  osm_id?: string | number;
  name?: string;
  "addr:street"?: string;
  "addr:housenumber"?: string;
  "addr:city"?: string;
  material?: string;
  material_confidence?: number;
  height?: number;
  min_height?: number;
  levels?: number;
  color?: string;
  rf_attenuation_2_4ghz?: number;
  rf_class?: string;
  building?: string;
  [key: string]: unknown;
}

interface BuildingsLayerProps {
  map: MaplibreMap | null;
  visible: boolean;
  cityId: string;
}

/* ── Enriched Building Popup ── */
function EnrichedBuildingPopup({
  props,
  onClose,
}: {
  props: EnrichedBuildingProps;
  onClose: () => void;
}) {
  const name =
    props.name ||
    [props["addr:housenumber"], props["addr:street"], props["addr:city"]]
      .filter(Boolean)
      .join(", ") ||
    "Building";

  const materialLabel = props.material
    ? props.material.replace(/_/g, " ")
    : "Unknown";

  const confidencePct =
    props.material_confidence != null
      ? `${Math.round(props.material_confidence * 100)}%`
      : null;

  const rfAtten =
    props.rf_attenuation_2_4ghz != null
      ? `${props.rf_attenuation_2_4ghz} dB`
      : null;

  const rfClass = props.rf_class || null;

  const rows: Array<{
    icon: React.ReactNode;
    label: string;
    value: string;
    accent?: string;
  }> = [];

  if (props.building) {
    rows.push({
      icon: <Building2 className="h-3.5 w-3.5" />,
      label: "Type",
      value: props.building.replace(/_/g, " "),
    });
  }

  rows.push({
    icon: <Palette className="h-3.5 w-3.5" />,
    label: "Material",
    value: confidencePct
      ? `${materialLabel} (${confidencePct})`
      : materialLabel,
  });

  if (props.height != null) {
    rows.push({
      icon: <Ruler className="h-3.5 w-3.5" />,
      label: "Height",
      value: `${props.height} m`,
    });
  }

  if (props.levels != null) {
    rows.push({
      icon: <Layers className="h-3.5 w-3.5" />,
      label: "Levels",
      value: String(props.levels),
    });
  }

  if (rfAtten) {
    rows.push({
      icon: <Radio className="h-3.5 w-3.5" />,
      label: "RF 2.4 GHz",
      value: rfAtten,
      accent: "text-amber-600",
    });
  }

  if (rfClass) {
    rows.push({
      icon: <Shield className="h-3.5 w-3.5" />,
      label: "RF Class",
      value: rfClass,
      accent: rfClassAccent(rfClass),
    });
  }

  if (props.osm_id) {
    rows.push({
      icon: <Hash className="h-3.5 w-3.5" />,
      label: "OSM ID",
      value: String(props.osm_id),
    });
  }

  return (
    <div className="w-80 rounded-xl border border-white/30 bg-white/95 shadow-2xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="h-3 w-3 rounded-full shrink-0 border border-white/50 shadow-sm"
            style={{ backgroundColor: props.color || "#94a3b8" }}
          />
          <h3 className="text-sm font-semibold text-zinc-900 truncate">
            {name}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors shrink-0 ml-2"
          aria-label="Close popup"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Properties */}
      <div className="px-4 py-3 space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-2 text-xs">
            <span className="text-zinc-400">{row.icon}</span>
            <span className="font-medium text-zinc-500 w-[4.5rem] shrink-0">
              {row.label}
            </span>
            <span
              className={`truncate capitalize font-medium ${row.accent || "text-zinc-900"}`}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>

      {/* TSCM badge */}
      {rfClass && (
        <div className="mx-4 mb-3 rounded-lg bg-zinc-50 border border-zinc-100 px-3 py-2">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
            <Shield className="h-3 w-3" />
            TSCM RF Attenuation Profile
          </div>
          <div className="mt-1 flex items-center gap-3">
            <RfBar value={props.rf_attenuation_2_4ghz ?? 0} />
            <span className="text-[10px] font-mono text-zinc-500">
              {rfAtten || "N/A"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── RF attenuation bar ── */
function RfBar({ value }: { value: number }) {
  // Scale: 0-40 dB range typical for building materials
  const pct = Math.min(100, Math.max(0, (value / 40) * 100));
  const color =
    value < 5
      ? "bg-green-400"
      : value < 15
        ? "bg-yellow-400"
        : value < 25
          ? "bg-orange-400"
          : "bg-red-400";

  return (
    <div className="flex-1 h-1.5 rounded-full bg-zinc-200 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/* ── RF class color accent ── */
function rfClassAccent(rfClass: string): string {
  switch (rfClass.toLowerCase()) {
    case "transparent":
    case "low":
      return "text-green-600";
    case "moderate":
      return "text-yellow-600";
    case "high":
      return "text-orange-600";
    case "very_high":
    case "opaque":
      return "text-red-600";
    default:
      return "text-zinc-700";
  }
}

/* ================================================================
   BuildingsLayer — Renderless component for enriched GeoJSON
   ================================================================ */
export default function BuildingsLayer({
  map,
  visible,
  cityId,
}: BuildingsLayerProps) {
  const [loading, setLoading] = useState(false);
  const [featureCount, setFeatureCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const layerAddedRef = useRef(false);

  /* ── Fetch buildings GeoJSON for a city ── */
  const fetchBuildings = useCallback(
    async (city: PlanOCity, signal: AbortSignal) => {
      const [south, west, north, east] = city.bbox;
      const url = `/api/raster/buildings?south=${south}&west=${west}&north=${north}&east=${east}`;

      const res = await fetch(url, { signal });
      if (!res.ok) {
        throw new Error(`API returned ${res.status}: ${res.statusText}`);
      }

      const geojson = await res.json();
      return geojson as GeoJSON.FeatureCollection;
    },
    [],
  );

  /* ── Ensure source and layer exist on the map ── */
  const ensureLayer = useCallback(
    (m: MaplibreMap) => {
      if (layerAddedRef.current && m.getSource(SOURCE_ID)) return;

      // Add empty source if not present
      if (!m.getSource(SOURCE_ID)) {
        m.addSource(SOURCE_ID, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
      }

      // Remove existing layer if present (e.g. after style change)
      if (m.getLayer(LAYER_ID)) {
        m.removeLayer(LAYER_ID);
      }

      // Find insertion point: above the base building layer, below labels
      const style = m.getStyle();
      const layers = style?.layers || [];
      let beforeId: string | undefined;

      // Try to insert above the base building-3d layer
      const baseIdx = layers.findIndex((l) => l.id === BASE_LAYER_ID);
      if (baseIdx >= 0 && baseIdx + 1 < layers.length) {
        beforeId = layers[baseIdx + 1].id;
      } else {
        // Fallback: insert below the first symbol layer
        for (const layer of layers) {
          if (
            layer.type === "symbol" &&
            (layer as Record<string, unknown>)["source-layer"]
          ) {
            beforeId = layer.id;
            break;
          }
        }
      }

      m.addLayer(
        {
          id: LAYER_ID,
          source: SOURCE_ID,
          type: "fill-extrusion",
          minzoom: 13,
          paint: {
            "fill-extrusion-color": [
              "coalesce",
              ["get", "color"],
              "#94a3b8", // slate-400 fallback
            ],
            "fill-extrusion-height": [
              "coalesce",
              ["get", "height"],
              10,
            ],
            "fill-extrusion-base": [
              "coalesce",
              ["get", "min_height"],
              0,
            ],
            "fill-extrusion-opacity": 0.9,
          },
        },
        beforeId,
      );

      layerAddedRef.current = true;
    },
    [],
  );

  /* ── Update source data ── */
  const updateData = useCallback(
    (m: MaplibreMap, geojson: GeoJSON.FeatureCollection) => {
      const src = m.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      if (src) {
        src.setData(geojson);
      }
    },
    [],
  );

  /* ── Main effect: load data when cityId or map changes ── */
  useEffect(() => {
    if (!map || !visible) return;

    const city = getCityById(cityId);
    if (!city) {
      setError(`Unknown city: ${cityId}`);
      return;
    }

    // Cancel previous fetch
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setFeatureCount(null);

    // Ensure layer exists (may need to re-add after style change)
    const addLayerAndFetch = () => {
      ensureLayer(map);

      fetchBuildings(city, controller.signal)
        .then((geojson) => {
          if (controller.signal.aborted) return;
          updateData(map, geojson);
          setFeatureCount(geojson.features.length);
          setLoading(false);
        })
        .catch((err) => {
          if (controller.signal.aborted) return;
          if (err instanceof DOMException && err.name === "AbortError") return;
          console.error("[BuildingsLayer] fetch error:", err);
          setError(err.message || "Failed to load buildings");
          setLoading(false);
        });
    };

    // If the map style is loaded, add immediately; otherwise wait
    if (map.isStyleLoaded()) {
      addLayerAndFetch();
    } else {
      const onStyleLoad = () => {
        addLayerAndFetch();
      };
      map.once("style.load", onStyleLoad);
      return () => {
        map.off("style.load", onStyleLoad);
        controller.abort();
      };
    }

    return () => {
      controller.abort();
    };
  }, [map, visible, cityId, ensureLayer, fetchBuildings, updateData]);

  /* ── Re-add layer after style changes ── */
  useEffect(() => {
    if (!map) return;

    const onStyleLoad = () => {
      layerAddedRef.current = false;
      // The main effect will handle re-adding the layer on the next render,
      // but we need to trigger it for style-only changes (same city)
      if (visible) {
        const city = getCityById(cityId);
        if (!city) return;

        ensureLayer(map);

        // Re-fetch to repopulate
        const controller = new AbortController();
        abortRef.current = controller;
        setLoading(true);

        fetchBuildings(city, controller.signal)
          .then((geojson) => {
            if (controller.signal.aborted) return;
            updateData(map, geojson);
            setFeatureCount(geojson.features.length);
            setLoading(false);
          })
          .catch((err) => {
            if (controller.signal.aborted) return;
            if (err instanceof DOMException && err.name === "AbortError") return;
            setError(err.message || "Failed to load buildings");
            setLoading(false);
          });
      }
    };

    map.on("style.load", onStyleLoad);
    return () => {
      map.off("style.load", onStyleLoad);
    };
  }, [map, visible, cityId, ensureLayer, fetchBuildings, updateData]);

  /* ── Click handler for enriched buildings ── */
  useEffect(() => {
    if (!map || !visible) return;

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      if (!map.getLayer(LAYER_ID)) return;

      const features = map.queryRenderedFeatures(e.point, {
        layers: [LAYER_ID],
      });

      // Close existing popup
      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }

      if (!features.length) return;

      // Prevent the base building click from also firing
      e.originalEvent.stopPropagation();

      const feature = features[0];
      const props = feature.properties as EnrichedBuildingProps;

      const popupNode = document.createElement("div");
      const root = createRoot(popupNode);

      const closePopup = () => {
        popup.remove();
        popupRef.current = null;
      };

      root.render(<EnrichedBuildingPopup props={props} onClose={closePopup} />);

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

    const handleMouseEnter = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("click", LAYER_ID, handleClick);
    map.on("mouseenter", LAYER_ID, handleMouseEnter);
    map.on("mouseleave", LAYER_ID, handleMouseLeave);

    return () => {
      map.off("click", LAYER_ID, handleClick);
      map.off("mouseenter", LAYER_ID, handleMouseEnter);
      map.off("mouseleave", LAYER_ID, handleMouseLeave);
    };
  }, [map, visible]);

  /* ── Visibility toggle ── */
  useEffect(() => {
    if (!map || !map.getLayer(LAYER_ID)) return;
    map.setLayoutProperty(
      LAYER_ID,
      "visibility",
      visible ? "visible" : "none",
    );
  }, [map, visible]);

  /* ── Cleanup on unmount ── */
  useEffect(() => {
    return () => {
      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }
      if (abortRef.current) {
        abortRef.current.abort();
      }

      // Defensive removal — map may already be gone
      try {
        if (map) {
          if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID);
          if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
        }
      } catch {
        // Map was already removed
      }
      layerAddedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Status indicator (loading/error/count) ── */
  if (!visible) return null;

  return (
    <div className="absolute bottom-6 right-4 z-20">
      {loading && (
        <div className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-xs font-medium text-zinc-600 shadow-lg backdrop-blur-xl">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />
          <span>Loading buildings...</span>
        </div>
      )}

      {!loading && error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200/50 bg-red-50/90 px-3 py-2 text-xs font-medium text-red-600 shadow-lg backdrop-blur-xl">
          <X className="h-3.5 w-3.5" />
          <span className="truncate max-w-48">{error}</span>
        </div>
      )}

      {!loading && !error && featureCount != null && (
        <div className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-xs font-medium text-zinc-600 shadow-lg backdrop-blur-xl">
          <Building2 className="h-3.5 w-3.5 text-emerald-500" />
          <span>
            {featureCount.toLocaleString()} enriched building
            {featureCount !== 1 ? "s" : ""}
          </span>
        </div>
      )}
    </div>
  );
}

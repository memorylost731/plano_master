import { useEffect, useRef, useState, useCallback } from "react";
import type { Map as MaplibreMap } from "maplibre-gl";
import type { TscmEmitter } from "./TscmPanel.tsx";

/* ── Types ── */
interface TscmReading {
  lat: number;
  lng: number;
  rssi: number;
  emitter_type: string;
  threat_level: string;
}

interface FloorPlan {
  id: number;
  name: string;
  image_path: string;
  lat_nw: number;
  lng_nw: number;
  lat_se: number;
  lng_se: number;
  floor_level: number;
}

interface TscmHeatmapLayerProps {
  map: MaplibreMap | null;
  visible: boolean;
  showFloorPlans?: boolean;
  selectedEmitter?: TscmEmitter | null;
  threatFilters?: string[];
}

const THREAT_MARKER_COLORS: Record<string, string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
  BENIGN: "#71717a",
};

const EMITTER_SOURCE = "tscm-emitters";
const EMITTER_CIRCLES_LAYER = "tscm-emitter-circles";
const EMITTER_LABELS_LAYER = "tscm-emitter-labels";
const HEATMAP_SOURCE = "tscm-heatmap";
const HEATMAP_LAYER = "tscm-heatmap-layer";
const SELECTED_SOURCE = "tscm-selected";
const SELECTED_LAYER = "tscm-selected-pulse";

export default function TscmHeatmapLayer({
  map,
  visible,
  showFloorPlans = true,
  selectedEmitter,
  threatFilters = [],
}: TscmHeatmapLayerProps) {
  const [emitters, setEmitters] = useState<TscmEmitter[]>([]);
  const [floorPlans, setFloorPlans] = useState<FloorPlan[]>([]);
  const loadedPlansRef = useRef<Set<number>>(new Set());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ── Fetch data ── */
  const loadData = useCallback(async () => {
    try {
      const [emRes, planRes] = await Promise.all([
        fetch("/api/tscm/emitters").then((r) => r.json()),
        fetch("/api/tscm/plans").then((r) => r.json()),
      ]);
      setEmitters(emRes);
      setFloorPlans(planRes);
    } catch {
      /* TSCM backend unavailable */
    }
  }, []);

  useEffect(() => {
    if (!visible) return;
    loadData();
    intervalRef.current = setInterval(loadData, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [visible, loadData]);

  /* ── Add/update map layers ── */
  useEffect(() => {
    if (!map || !visible) return;

    const geoEmitters = emitters.filter((e) => e.lat && e.lng);

    /* Filter by threat level if any */
    const filtered =
      threatFilters.length > 0
        ? geoEmitters.filter((e) => threatFilters.includes(e.threat_level))
        : geoEmitters;

    /* ── Emitter markers as GeoJSON ── */
    const emitterGeoJSON: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: filtered.map((e) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [e.lng!, e.lat!],
        },
        properties: {
          id: e.id,
          name: e.name || e.address,
          address: e.address,
          type: e.emitter_type,
          threat: e.threat_level,
          rssi: e.avg_rssi || -80,
          color: THREAT_MARKER_COLORS[e.threat_level] || "#71717a",
          radius: Math.max(4, Math.min(12, (e.avg_rssi || -80 + 100) / 5)),
        },
      })),
    };

    /* ── Heatmap data (all readings weighted by RSSI) ── */
    const heatGeoJSON: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: filtered.map((e) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [e.lng!, e.lat!],
        },
        properties: {
          weight: Math.max(
            0.1,
            (e.avg_rssi || -80 + 100) / 100 *
              (e.threat_level === "CRITICAL"
                ? 3
                : e.threat_level === "HIGH"
                  ? 2
                  : 1),
          ),
        },
      })),
    };

    /* ── Update or create sources/layers ── */
    if (map.getSource(EMITTER_SOURCE)) {
      (map.getSource(EMITTER_SOURCE) as maplibregl.GeoJSONSource).setData(
        emitterGeoJSON,
      );
    } else {
      map.addSource(EMITTER_SOURCE, {
        type: "geojson",
        data: emitterGeoJSON,
      });

      map.addLayer({
        id: EMITTER_CIRCLES_LAYER,
        type: "circle",
        source: EMITTER_SOURCE,
        paint: {
          "circle-radius": ["get", "radius"],
          "circle-color": ["get", "color"],
          "circle-opacity": 0.8,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#000",
          "circle-stroke-opacity": 0.4,
        },
      });

      map.addLayer({
        id: EMITTER_LABELS_LAYER,
        type: "symbol",
        source: EMITTER_SOURCE,
        layout: {
          "text-field": ["get", "name"],
          "text-size": 10,
          "text-offset": [0, 1.5],
          "text-anchor": "top",
          "text-optional": true,
        },
        paint: {
          "text-color": "#e4e4e7",
          "text-halo-color": "#000",
          "text-halo-width": 1,
        },
        minzoom: 17,
      });
    }

    if (map.getSource(HEATMAP_SOURCE)) {
      (map.getSource(HEATMAP_SOURCE) as maplibregl.GeoJSONSource).setData(
        heatGeoJSON,
      );
    } else {
      map.addSource(HEATMAP_SOURCE, {
        type: "geojson",
        data: heatGeoJSON,
      });

      map.addLayer(
        {
          id: HEATMAP_LAYER,
          type: "heatmap",
          source: HEATMAP_SOURCE,
          paint: {
            "heatmap-weight": ["get", "weight"],
            "heatmap-intensity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10,
              0.5,
              18,
              2,
            ],
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(0,0,0,0)",
              0.2,
              "rgba(0,80,255,0.3)",
              0.4,
              "rgba(0,200,255,0.4)",
              0.6,
              "rgba(255,255,0,0.5)",
              0.8,
              "rgba(255,140,0,0.6)",
              1,
              "rgba(255,0,0,0.7)",
            ],
            "heatmap-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10,
              15,
              18,
              30,
            ],
            "heatmap-opacity": 0.6,
          },
        },
        EMITTER_CIRCLES_LAYER,
      );
    }

    /* ── Selected emitter highlight ── */
    if (selectedEmitter?.lat && selectedEmitter?.lng) {
      const selectedGeoJSON: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [selectedEmitter.lng, selectedEmitter.lat],
            },
            properties: {},
          },
        ],
      };

      if (map.getSource(SELECTED_SOURCE)) {
        (map.getSource(SELECTED_SOURCE) as maplibregl.GeoJSONSource).setData(
          selectedGeoJSON,
        );
      } else {
        map.addSource(SELECTED_SOURCE, {
          type: "geojson",
          data: selectedGeoJSON,
        });

        map.addLayer({
          id: SELECTED_LAYER,
          type: "circle",
          source: SELECTED_SOURCE,
          paint: {
            "circle-radius": 20,
            "circle-color": "transparent",
            "circle-stroke-width": 3,
            "circle-stroke-color": "#fff",
            "circle-stroke-opacity": 0.9,
          },
        });
      }
    }

    return () => {
      /* cleanup on unmount */
    };
  }, [map, visible, emitters, threatFilters, selectedEmitter]);

  /* ── Floor plan overlays ── */
  useEffect(() => {
    if (!map || !visible || !showFloorPlans) return;

    floorPlans.forEach((plan) => {
      if (loadedPlansRef.current.has(plan.id)) return;

      const sourceId = `tscm-plan-${plan.id}`;
      if (map.getSource(sourceId)) return;

      map.addSource(sourceId, {
        type: "image",
        url: `/api/tscm/plan-image/${plan.id}`,
        coordinates: [
          [plan.lng_nw, plan.lat_nw],
          [plan.lng_se, plan.lat_nw],
          [plan.lng_se, plan.lat_se],
          [plan.lng_nw, plan.lat_se],
        ],
      });

      map.addLayer(
        {
          id: `tscm-plan-layer-${plan.id}`,
          type: "raster",
          source: sourceId,
          paint: {
            "raster-opacity": 0.7,
            "raster-fade-duration": 0,
          },
        },
        HEATMAP_LAYER,
      );

      loadedPlansRef.current.add(plan.id);
    });
  }, [map, visible, showFloorPlans, floorPlans]);

  /* ── Hide layers when not visible ── */
  useEffect(() => {
    if (!map) return;

    const layerIds = [
      EMITTER_CIRCLES_LAYER,
      EMITTER_LABELS_LAYER,
      HEATMAP_LAYER,
      SELECTED_LAYER,
    ];

    layerIds.forEach((id) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    });

    floorPlans.forEach((plan) => {
      const layerId = `tscm-plan-layer-${plan.id}`;
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
      }
    });
  }, [map, visible, floorPlans]);

  return null;
}

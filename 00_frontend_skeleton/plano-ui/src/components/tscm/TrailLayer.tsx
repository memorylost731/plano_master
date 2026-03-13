/**
 * TrailLayer -- Renders animated emitter movement polylines on MapLibre
 *
 * For each emitter with >1 position in the current time window, draws:
 *   - A polyline connecting positions in chronological order
 *   - Color coded by threat level
 *   - Line width proportional to average RSSI
 *   - An arrow marker at the latest (head) position
 *   - Animated growing effect during playback
 */

import { useEffect, useRef } from "react";
import type { Map as MaplibreMap } from "maplibre-gl";
import type { TscmEmitter4D } from "../../types/tscm";
import { THREAT_COLORS } from "../../types/tscm";

const TRAIL_SOURCE = "tscm-trails";
const TRAIL_LAYER = "tscm-trail-lines";
const TRAIL_HEADS_SOURCE = "tscm-trail-heads";
const TRAIL_HEADS_LAYER = "tscm-trail-heads-circles";
const MAX_TRAILS = 50; // performance cap

interface TrailLayerProps {
  map: MaplibreMap | null;
  visible: boolean;
  emitters: TscmEmitter4D[];
  playing: boolean;
}

export default function TrailLayer({
  map,
  visible,
  emitters,
  playing,
}: TrailLayerProps) {
  const addedRef = useRef(false);

  useEffect(() => {
    if (!map || !visible) return;

    /* ── Filter to emitters with movement (>1 position) ── */
    const mobile = emitters
      .filter((e) => e.positions && e.positions.length > 1)
      .sort((a, b) => {
        // Prioritize: CRITICAL > HIGH > most positions
        const threatOrder: Record<string, number> = {
          CRITICAL: 0,
          HIGH: 1,
          MEDIUM: 2,
          LOW: 3,
          BENIGN: 4,
        };
        const ta = threatOrder[a.threat_level] ?? 5;
        const tb = threatOrder[b.threat_level] ?? 5;
        if (ta !== tb) return ta - tb;
        return b.positions.length - a.positions.length;
      })
      .slice(0, MAX_TRAILS);

    /* ── Build GeoJSON for trail lines ── */
    const trailGeoJSON: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: mobile.map((e) => ({
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: e.positions.map((p) => [p.lng, p.lat]),
        },
        properties: {
          id: e.id,
          name: e.name || e.address,
          threat: e.threat_level,
          color: THREAT_COLORS[e.threat_level] || "#71717a",
          width: Math.max(
            2,
            Math.min(
              6,
              (Math.abs(e.avg_rssi || 80) - 40) / 10,
            ),
          ),
          point_count: e.positions.length,
        },
      })),
    };

    /* ── Build GeoJSON for trail head markers (latest position) ── */
    const headsGeoJSON: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: mobile.map((e) => {
        const latest = e.positions[e.positions.length - 1];
        return {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [latest.lng, latest.lat],
          },
          properties: {
            id: e.id,
            name: e.name || e.address,
            color: THREAT_COLORS[e.threat_level] || "#71717a",
            rssi: latest.rssi,
          },
        };
      }),
    };

    /* ── Update or create trail source/layer ── */
    if (map.getSource(TRAIL_SOURCE)) {
      (map.getSource(TRAIL_SOURCE) as maplibregl.GeoJSONSource).setData(
        trailGeoJSON,
      );
    } else {
      map.addSource(TRAIL_SOURCE, {
        type: "geojson",
        data: trailGeoJSON,
      });

      map.addLayer({
        id: TRAIL_LAYER,
        type: "line",
        source: TRAIL_SOURCE,
        paint: {
          "line-color": ["get", "color"],
          "line-width": ["get", "width"],
          "line-opacity": 0.7,
          "line-dasharray": playing ? [2, 1] : [1, 0],
        },
        layout: {
          "line-cap": "round",
          "line-join": "round",
        },
      });

      addedRef.current = true;
    }

    /* ── Update or create head markers ── */
    if (map.getSource(TRAIL_HEADS_SOURCE)) {
      (
        map.getSource(TRAIL_HEADS_SOURCE) as maplibregl.GeoJSONSource
      ).setData(headsGeoJSON);
    } else {
      map.addSource(TRAIL_HEADS_SOURCE, {
        type: "geojson",
        data: headsGeoJSON,
      });

      map.addLayer({
        id: TRAIL_HEADS_LAYER,
        type: "circle",
        source: TRAIL_HEADS_SOURCE,
        paint: {
          "circle-radius": 5,
          "circle-color": ["get", "color"],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#000",
          "circle-opacity": 0.9,
        },
      });
    }

    /* ── Toggle dash animation during playback ── */
    if (map.getLayer(TRAIL_LAYER)) {
      map.setPaintProperty(
        TRAIL_LAYER,
        "line-dasharray",
        playing ? [2, 1] : [1, 0],
      );
    }
  }, [map, visible, emitters, playing]);

  /* ── Visibility toggle ── */
  useEffect(() => {
    if (!map) return;

    const layers = [TRAIL_LAYER, TRAIL_HEADS_LAYER];
    layers.forEach((id) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    });
  }, [map, visible]);

  /* ── Cleanup on unmount ── */
  useEffect(() => {
    return () => {
      if (!map) return;
      [TRAIL_LAYER, TRAIL_HEADS_LAYER].forEach((id) => {
        if (map.getLayer(id)) map.removeLayer(id);
      });
      [TRAIL_SOURCE, TRAIL_HEADS_SOURCE].forEach((id) => {
        if (map.getSource(id)) map.removeSource(id);
      });
    };
  }, [map]);

  return null; // renderless -- manipulates map directly
}

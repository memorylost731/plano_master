import { useRef, useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import SearchBar from "../../components/map/SearchBar.tsx";
import MapControls, {
  STYLE_URLS,
  type MapStyle,
} from "../../components/map/MapControls.tsx";
import CitySelector from "../../components/map/CitySelector.tsx";
import TscmPanel, {
  type TscmEmitter,
} from "../../components/tscm/TscmPanel.tsx";
import TscmHeatmapLayer from "../../components/tscm/TscmHeatmapLayer.tsx";
import TimeSlider from "../../components/tscm/TimeSlider.tsx";
import TrailLayer from "../../components/tscm/TrailLayer.tsx";
import { useTscm4D } from "../../hooks/useTscm4D.ts";
import { Building2, Shield, Radio, Layers, Eye, EyeOff, Clock } from "lucide-react";

/* ── Constants ── */
const INITIAL_CENTER: [number, number] = [14.5039, 35.9130]; // 42 Stella Maris, Sliema
const INITIAL_ZOOM = 19; // high zoom for floor plan detail
const INITIAL_PITCH = 55;
const INITIAL_BEARING = -15;

const BUILDING_SOURCE_LAYER = "building";
const BUILDINGS_LAYER_ID = "tscm-building-3d";

/* ── Add 3D building layers (translucent for TSCM overlay) ── */
function add3DBuildingLayers(map: maplibregl.Map) {
  const style = map.getStyle();
  if (!style?.sources) return;

  const sourceId = Object.keys(style.sources).find((id) => {
    const src = style.sources[id];
    return src.type === "vector";
  });
  if (!sourceId) return;

  if (map.getLayer(BUILDINGS_LAYER_ID)) map.removeLayer(BUILDINGS_LAYER_ID);

  const layers = style.layers || [];
  let labelLayerId: string | undefined;
  for (const layer of layers) {
    if (
      layer.type === "symbol" &&
      (layer as Record<string, unknown>)["source-layer"]
    ) {
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
          "interpolate",
          ["linear"],
          ["coalesce", ["get", "render_height"], ["get", "height"], 10],
          0,
          "#1a1a2e",
          10,
          "#16213e",
          20,
          "#0f3460",
          40,
          "#1a1a3e",
          80,
          "#0d1b2a",
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
        "fill-extrusion-opacity": 0.6,
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
      "sky-atmosphere-sun": [0, 80],
      "sky-atmosphere-sun-intensity": 5,
    } as unknown as maplibregl.BackgroundLayerSpecification["paint"],
  });
}

/* ================================================================
   TSCM Page Component — Full-screen counter-surveillance map
   ================================================================ */
export default function Tscm() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [mapReady, setMapReady] = useState(false);
  const [currentStyle, setCurrentStyle] = useState<MapStyle>("dark");
  const [buildings3D, setBuildings3D] = useState(true);
  const [heatmapVisible, setHeatmapVisible] = useState(true);
  const [trailsVisible, setTrailsVisible] = useState(true);
  const [timelineVisible, setTimelineVisible] = useState(true);
  const [selectedEmitter, setSelectedEmitter] = useState<TscmEmitter | null>(
    null,
  );
  const [threatFilters, setThreatFilters] = useState<string[]>([]);

  /* ── 4D timeline hook ── */
  const {
    meta,
    snapshot,
    loading: timelineLoading,
    playback,
    seekTo,
    togglePlay,
    setSpeed,
    setWindowSize,
  } = useTscm4D();

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
      new maplibregl.NavigationControl({
        visualizePitch: true,
        showCompass: true,
        showZoom: true,
      }),
      "top-left",
    );

    map.addControl(
      new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
      }),
      "top-left",
    );

    map.addControl(new maplibregl.FullscreenControl(), "top-left");

    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 150, unit: "metric" }),
      "bottom-right",
    );

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

  /* ── Emitter click → fly to ── */
  const handleEmitterSelect = useCallback(
    (emitter: TscmEmitter) => {
      setSelectedEmitter(emitter);
      if (mapRef.current && emitter.lat && emitter.lng) {
        mapRef.current.flyTo({
          center: [emitter.lng, emitter.lat],
          zoom: 19,
          pitch: 60,
          duration: 1500,
        });
      }
    },
    [],
  );

  /* ── Toggle handlers ── */
  const handleToggleBuildings = useCallback(
    (on: boolean) => {
      setBuildings3D(on);
      const map = mapRef.current;
      if (!map) return;
      if (on) {
        if (!map.getLayer(BUILDINGS_LAYER_ID)) add3DBuildingLayers(map);
      } else {
        if (map.getLayer(BUILDINGS_LAYER_ID)) map.removeLayer(BUILDINGS_LAYER_ID);
      }
    },
    [],
  );

  const handleStyleChange = useCallback((style: MapStyle) => {
    setCurrentStyle(style);
    mapRef.current?.setStyle(STYLE_URLS[style]);
  }, []);

  return (
    <div className="fixed inset-0 w-screen h-screen bg-zinc-950">
      {/* Map container */}
      <div ref={containerRef} className="absolute inset-0 w-full h-full" />

      {/* TSCM Heatmap overlay (invisible component, manipulates map layers) */}
      <TscmHeatmapLayer
        map={mapReady ? mapRef.current : null}
        visible={heatmapVisible}
        selectedEmitter={selectedEmitter}
        threatFilters={threatFilters}
      />

      {/* 4D Movement trails */}
      <TrailLayer
        map={mapReady ? mapRef.current : null}
        visible={trailsVisible}
        emitters={snapshot?.emitters || []}
        playing={playback.playing}
      />

      {/* Search bar overlay */}
      <SearchBar map={mapReady ? mapRef.current : null} />

      {/* Map controls (bottom-left) */}
      <MapControls
        map={mapReady ? mapRef.current : null}
        buildings3D={buildings3D}
        onToggleBuildings={handleToggleBuildings}
        currentStyle={currentStyle}
        onChangeStyle={handleStyleChange}
      />

      {/* City selector (dark variant, default to Sliema) */}
      <CitySelector
        map={mapReady ? mapRef.current : null}
        defaultCityId="sliema"
        dark
        className="bottom-6 left-40"
      />

      {/* Top-left branding + nav */}
      <div className="absolute top-4 left-4 z-20 hidden sm:flex items-center gap-2">
        <div className="flex items-center gap-3 rounded-xl border border-red-500/30 bg-black/80 px-4 py-2.5 shadow-lg backdrop-blur-xl">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-red-400" />
            <span className="text-sm font-bold text-zinc-100 tracking-tight">
              PlanO
            </span>
            <span className="text-[10px] font-mono text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">
              TSCM
            </span>
          </div>
          <div className="h-4 w-px bg-zinc-700" />
          <Link
            to="/"
            className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <Building2 className="h-3 w-3" />
            Map
          </Link>
          <Link
            to="/planner"
            className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <Layers className="h-3 w-3" />
            Planner
          </Link>
        </div>
      </div>

      {/* Layer toggles */}
      <div className="absolute top-4 right-[340px] z-20 flex flex-col gap-2">
        <button
          onClick={() => setHeatmapVisible(!heatmapVisible)}
          className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium shadow-lg backdrop-blur-xl transition-all ${
            heatmapVisible
              ? "bg-red-600/30 text-red-300 border border-red-500/40"
              : "bg-black/70 text-zinc-500 border border-zinc-700/50 hover:text-zinc-300"
          }`}
          title={heatmapVisible ? "Hide heatmap" : "Show heatmap"}
        >
          {heatmapVisible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
          <Radio className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => setTrailsVisible(!trailsVisible)}
          className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium shadow-lg backdrop-blur-xl transition-all ${
            trailsVisible
              ? "bg-orange-600/30 text-orange-300 border border-orange-500/40"
              : "bg-black/70 text-zinc-500 border border-zinc-700/50 hover:text-zinc-300"
          }`}
          title={trailsVisible ? "Hide trails" : "Show trails"}
        >
          {trailsVisible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
          <Layers className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => setTimelineVisible(!timelineVisible)}
          className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium shadow-lg backdrop-blur-xl transition-all ${
            timelineVisible
              ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
              : "bg-black/70 text-zinc-500 border border-zinc-700/50 hover:text-zinc-300"
          }`}
          title={timelineVisible ? "Hide timeline" : "Show timeline"}
        >
          {timelineVisible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
          <Clock className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* TSCM control panel (right side) */}
      <div className="absolute top-4 right-4 z-20">
        <TscmPanel
          onEmitterSelect={handleEmitterSelect}
          onThreatFilterChange={setThreatFilters}
        />
      </div>

      {/* 4D Timeline controls (bottom) */}
      {timelineVisible && (
        <TimeSlider
          meta={meta}
          playback={playback}
          loading={timelineLoading}
          onSeek={seekTo}
          onTogglePlay={togglePlay}
          onSetSpeed={setSpeed}
          onSetWindowSize={setWindowSize}
          activeEmitters={snapshot?.stats.active_emitters}
          maxThreat={snapshot?.stats.max_threat}
        />
      )}

      {/* Loading state */}
      {!mapReady && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-zinc-950">
          <div className="flex flex-col items-center gap-4">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-red-400 border-t-transparent" />
            <p className="text-sm text-zinc-400 font-medium">
              Initializing TSCM overlay...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

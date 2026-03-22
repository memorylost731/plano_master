/**
 * TSCM 4D Mapping System -- Shared TypeScript Types
 *
 * Used by: TimeSlider, TrailLayer, TscmHeatmapLayer, useTscm4D hook
 */

/* ── Core emitter (matches existing TscmPanel.tsx interface) ── */
export interface TscmEmitter {
  id: number;
  address: string;
  name: string | null;
  emitter_type: "ble" | "wifi" | "rf";
  manufacturer?: string;
  threat_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "BENIGN";
  first_seen: string;
  last_seen: string;
  detect_count: number;
  avg_rssi: number;
  max_rssi: number;
  whitelisted: number;
  metadata?: Record<string, unknown>;
  lat?: number;
  lng?: number;
}

/* ── 4D position point ── */
export interface EmitterPosition {
  lat: number;
  lng: number;
  rssi: number;
  ts: string;
  floor?: number;
}

/* ── 4D-enriched emitter (emitter + its positions in a time window) ── */
export interface TscmEmitter4D extends TscmEmitter {
  positions: EmitterPosition[];
  trail_color: string;
}

/* ── Heatmap grid point ── */
export interface HeatmapPoint {
  lat: number;
  lng: number;
  weight: number;
  ts: string;
}

/* ── Time range ── */
export interface TimeRange {
  t0: string; // ISO timestamp
  t1: string;
}

/* ── Snapshot stats ── */
export interface SnapshotStats {
  active_emitters: number;
  new_this_window: number;
  disappeared: number;
  max_threat: string;
}

/* ── Full 4D snapshot response ── */
export interface TscmSnapshot {
  time_range: TimeRange;
  emitters: TscmEmitter4D[];
  heatmap_grid: HeatmapPoint[];
  stats: SnapshotStats;
}

/* ── Time range metadata (for slider bounds) ── */
export interface TimeRangeMeta {
  first_reading: string;
  last_reading: string;
  total_days: number;
  reading_count: number;
  density: Array<{ date: string; count: number }>;
}

/* ── Playback state ── */
export interface PlaybackState {
  playing: boolean;
  speed: number; // 0.5, 1, 2, 4, 8
  currentTime: string; // ISO -- the playhead position
  windowSize: number; // seconds -- how wide the visible window is
}

/* ── Trail data for a single emitter ── */
export interface EmitterTrail {
  emitter_id: number;
  address: string;
  trail: EmitterPosition[];
  mobility: string;
  distance_total_m: number;
  time_span_hours: number;
}

/* ── Threat level color mapping ── */
export const THREAT_COLORS: Record<string, string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
  BENIGN: "#71717a",
};

/* ── Window size presets (seconds) ── */
export const WINDOW_PRESETS = [
  { label: "1h", seconds: 3600 },
  { label: "6h", seconds: 21600 },
  { label: "1d", seconds: 86400 },
  { label: "1w", seconds: 604800 },
  { label: "1mo", seconds: 2592000 },
] as const;

/* ── Speed presets ── */
export const SPEED_PRESETS = [0.5, 1, 2, 4, 8] as const;

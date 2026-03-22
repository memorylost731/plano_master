import { useState, useEffect, useCallback } from "react";
import {
  Radio,
  Wifi,
  Bluetooth,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Activity,
  Eye,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Search,
  X,
  Zap,
  Users,
} from "lucide-react";

/* ── Types ── */
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

export interface TscmStats {
  total_emitters: number;
  ble: number;
  wifi: number;
  readings: number;
  critical: number;
  high: number;
  plans: number;
  sweeps: number;
  tomo_pts: number;
}

export interface PresenceReading {
  timestamp: string;
  motion_level: "absent" | "present_still" | "active";
  confidence: number;
  breathing_rate_bpm?: number;
  node_id?: number;
}

/* ── Threat colors ── */
const THREAT_COLORS: Record<string, string> = {
  CRITICAL: "text-red-500 bg-red-500/10 border-red-500/30",
  HIGH: "text-orange-500 bg-orange-500/10 border-orange-500/30",
  MEDIUM: "text-yellow-500 bg-yellow-500/10 border-yellow-500/30",
  LOW: "text-green-500 bg-green-500/10 border-green-500/30",
  BENIGN: "text-zinc-400 bg-zinc-500/10 border-zinc-500/30",
};

const THREAT_DOTS: Record<string, string> = {
  CRITICAL: "bg-red-500",
  HIGH: "bg-orange-500",
  MEDIUM: "bg-yellow-500",
  LOW: "bg-green-500",
  BENIGN: "bg-zinc-400",
};

/* ── API helpers ── */
async function fetchStats(): Promise<TscmStats> {
  const res = await fetch("/api/tscm/stats");
  return res.json();
}

async function fetchEmitters(
  type?: string,
  threat?: string,
): Promise<TscmEmitter[]> {
  const params = new URLSearchParams();
  if (type && type !== "all") params.set("type", type);
  if (threat && threat !== "all") params.set("threat", threat);
  const qs = params.toString();
  const res = await fetch(`/api/tscm/emitters${qs ? `?${qs}` : ""}`);
  return res.json();
}

async function fetchPresence(): Promise<{ readings: PresenceReading[] }> {
  const res = await fetch("/api/tscm/densepose/presence?minutes=5");
  return res.json();
}

async function triggerScan(
  type: "ble" | "wifi" | "sweep",
): Promise<{ found?: number; status?: string }> {
  const endpoint =
    type === "sweep" ? "/api/tscm/sweep" : `/api/tscm/scan/${type}`;
  const res = await fetch(endpoint, { method: "POST" });
  return res.json();
}

/* ── Component ── */
interface TscmPanelProps {
  onEmitterSelect?: (emitter: TscmEmitter) => void;
  onThreatFilterChange?: (threats: string[]) => void;
  collapsed?: boolean;
}

export default function TscmPanel({
  onEmitterSelect,
  onThreatFilterChange,
  collapsed: initialCollapsed = false,
}: TscmPanelProps) {
  const [stats, setStats] = useState<TscmStats | null>(null);
  const [emitters, setEmitters] = useState<TscmEmitter[]>([]);
  const [presence, setPresence] = useState<PresenceReading[]>([]);
  const [scanning, setScanning] = useState(false);
  const [typeFilter, setTypeFilter] = useState("all");
  const [threatFilter, setThreatFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [expandedSection, setExpandedSection] = useState<string>("threats");

  /* ── Data loading ── */
  const refresh = useCallback(async () => {
    try {
      const [s, e, p] = await Promise.all([
        fetchStats(),
        fetchEmitters(typeFilter, threatFilter),
        fetchPresence().catch(() => ({ readings: [] })),
      ]);
      setStats(s);
      setEmitters(e);
      setPresence(p.readings || []);
    } catch {
      /* TSCM backend unavailable */
    }
  }, [typeFilter, threatFilter]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    if (onThreatFilterChange) {
      onThreatFilterChange(
        threatFilter === "all" ? [] : [threatFilter],
      );
    }
  }, [threatFilter, onThreatFilterChange]);

  /* ── Scan handler ── */
  const handleScan = async (type: "ble" | "wifi" | "sweep") => {
    setScanning(true);
    try {
      await triggerScan(type);
      await refresh();
    } finally {
      setScanning(false);
    }
  };

  /* ── Filtered emitters ── */
  const filtered = emitters.filter((e) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (e.name?.toLowerCase().includes(q)) ||
      e.address.toLowerCase().includes(q) ||
      (e.manufacturer?.toLowerCase().includes(q))
    );
  });

  const criticals = filtered.filter((e) => e.threat_level === "CRITICAL");
  const highs = filtered.filter((e) => e.threat_level === "HIGH");
  const mediums = filtered.filter((e) => e.threat_level === "MEDIUM");
  const lows = filtered.filter(
    (e) => e.threat_level === "LOW" || e.threat_level === "BENIGN",
  );

  /* ── Presence summary ── */
  const latestPresence = presence.length > 0 ? presence[0] : null;

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-black/80 px-3 py-2.5 text-xs font-medium text-red-400 shadow-lg backdrop-blur-xl hover:bg-black/90 transition-all"
        title="TSCM Counter-Surveillance"
      >
        <ShieldAlert className="h-4 w-4" />
        <span className="hidden sm:inline">TSCM</span>
        {stats && stats.critical > 0 && (
          <span className="ml-1 rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
            {stats.critical}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="flex flex-col w-80 max-h-[calc(100vh-120px)] rounded-xl border border-zinc-700/50 bg-zinc-900/95 shadow-2xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-700/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-red-400" />
          <h3 className="text-sm font-bold text-zinc-100">TSCM</h3>
          {stats && (
            <span className="text-[10px] text-zinc-500 font-mono">
              {stats.total_emitters} devices
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => refresh()}
            className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setCollapsed(true)}
            className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
            title="Collapse"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-4 gap-px border-b border-zinc-700/50 bg-zinc-800/50">
          <div className="flex flex-col items-center py-2">
            <span className="text-xs font-bold text-zinc-100">
              {stats.total_emitters}
            </span>
            <span className="text-[9px] text-zinc-500">Total</span>
          </div>
          <div className="flex flex-col items-center py-2">
            <span className="text-xs font-bold text-blue-400">
              {stats.ble}
            </span>
            <span className="text-[9px] text-zinc-500">BLE</span>
          </div>
          <div className="flex flex-col items-center py-2">
            <span className="text-xs font-bold text-cyan-400">
              {stats.wifi}
            </span>
            <span className="text-[9px] text-zinc-500">WiFi</span>
          </div>
          <div className="flex flex-col items-center py-2">
            <span
              className={`text-xs font-bold ${stats.critical > 0 ? "text-red-400" : "text-green-400"}`}
            >
              {stats.critical + stats.high}
            </span>
            <span className="text-[9px] text-zinc-500">Threats</span>
          </div>
        </div>
      )}

      {/* Scan controls */}
      <div className="flex gap-1.5 border-b border-zinc-700/50 px-3 py-2">
        <button
          onClick={() => handleScan("ble")}
          disabled={scanning}
          className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-blue-600/20 border border-blue-500/30 px-2 py-1.5 text-[10px] font-medium text-blue-400 hover:bg-blue-600/30 disabled:opacity-50 transition-colors"
        >
          <Bluetooth className="h-3 w-3" />
          BLE
        </button>
        <button
          onClick={() => handleScan("wifi")}
          disabled={scanning}
          className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-cyan-600/20 border border-cyan-500/30 px-2 py-1.5 text-[10px] font-medium text-cyan-400 hover:bg-cyan-600/30 disabled:opacity-50 transition-colors"
        >
          <Wifi className="h-3 w-3" />
          WiFi
        </button>
        <button
          onClick={() => handleScan("sweep")}
          disabled={scanning}
          className="flex-1 flex items-center justify-center gap-1 rounded-lg bg-red-600/20 border border-red-500/30 px-2 py-1.5 text-[10px] font-medium text-red-400 hover:bg-red-600/30 disabled:opacity-50 transition-colors"
        >
          <Zap className="h-3 w-3" />
          Sweep
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-1.5 border-b border-zinc-700/50 px-3 py-2">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="flex-1 rounded-lg bg-zinc-800 border border-zinc-700 px-2 py-1 text-[10px] text-zinc-300 outline-none"
        >
          <option value="all">All types</option>
          <option value="ble">BLE</option>
          <option value="wifi">WiFi</option>
        </select>
        <select
          value={threatFilter}
          onChange={(e) => setThreatFilter(e.target.value)}
          className="flex-1 rounded-lg bg-zinc-800 border border-zinc-700 px-2 py-1 text-[10px] text-zinc-300 outline-none"
        >
          <option value="all">All threats</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>

      {/* Search */}
      <div className="relative border-b border-zinc-700/50 px-3 py-2">
        <Search className="absolute left-5 top-1/2 -translate-y-1/2 h-3 w-3 text-zinc-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search device name or MAC..."
          className="w-full rounded-lg bg-zinc-800 border border-zinc-700 pl-7 pr-2 py-1.5 text-[10px] text-zinc-300 placeholder-zinc-600 outline-none focus:border-zinc-500"
        />
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {/* Presence section */}
        {latestPresence && (
          <div className="border-b border-zinc-700/50 px-3 py-2">
            <button
              onClick={() =>
                setExpandedSection(
                  expandedSection === "presence" ? "" : "presence",
                )
              }
              className="flex w-full items-center justify-between text-xs"
            >
              <div className="flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5 text-purple-400" />
                <span className="font-medium text-zinc-300">Presence</span>
              </div>
              {expandedSection === "presence" ? (
                <ChevronUp className="h-3 w-3 text-zinc-500" />
              ) : (
                <ChevronDown className="h-3 w-3 text-zinc-500" />
              )}
            </button>
            {expandedSection === "presence" && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center gap-2 text-[10px]">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      latestPresence.motion_level === "active"
                        ? "bg-green-500 animate-pulse"
                        : latestPresence.motion_level === "present_still"
                          ? "bg-yellow-500"
                          : "bg-zinc-600"
                    }`}
                  />
                  <span className="text-zinc-400">Motion:</span>
                  <span className="text-zinc-200 capitalize">
                    {latestPresence.motion_level.replace("_", " ")}
                  </span>
                  <span className="text-zinc-500">
                    ({(latestPresence.confidence * 100).toFixed(0)}%)
                  </span>
                </div>
                {latestPresence.breathing_rate_bpm && (
                  <div className="flex items-center gap-2 text-[10px]">
                    <Activity className="h-2.5 w-2.5 text-pink-400" />
                    <span className="text-zinc-400">Breathing:</span>
                    <span className="text-zinc-200">
                      {latestPresence.breathing_rate_bpm} bpm
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Threats section */}
        <div className="px-3 py-2">
          <button
            onClick={() =>
              setExpandedSection(
                expandedSection === "threats" ? "" : "threats",
              )
            }
            className="flex w-full items-center justify-between text-xs"
          >
            <div className="flex items-center gap-1.5">
              <ShieldAlert className="h-3.5 w-3.5 text-red-400" />
              <span className="font-medium text-zinc-300">
                Threats ({criticals.length + highs.length})
              </span>
            </div>
            {expandedSection === "threats" ? (
              <ChevronUp className="h-3 w-3 text-zinc-500" />
            ) : (
              <ChevronDown className="h-3 w-3 text-zinc-500" />
            )}
          </button>
          {expandedSection === "threats" && (
            <div className="mt-2 space-y-1">
              {criticals.length === 0 && highs.length === 0 && (
                <div className="flex items-center gap-1.5 py-2 text-[10px] text-zinc-500">
                  <ShieldCheck className="h-3 w-3 text-green-500" />
                  No critical or high threats detected
                </div>
              )}
              {[...criticals, ...highs].slice(0, 20).map((e) => (
                <EmitterRow
                  key={e.id}
                  emitter={e}
                  onClick={() => onEmitterSelect?.(e)}
                />
              ))}
            </div>
          )}
        </div>

        {/* All devices section */}
        <div className="border-t border-zinc-700/50 px-3 py-2">
          <button
            onClick={() =>
              setExpandedSection(
                expandedSection === "devices" ? "" : "devices",
              )
            }
            className="flex w-full items-center justify-between text-xs"
          >
            <div className="flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5 text-zinc-400" />
              <span className="font-medium text-zinc-300">
                All Devices ({filtered.length})
              </span>
            </div>
            {expandedSection === "devices" ? (
              <ChevronUp className="h-3 w-3 text-zinc-500" />
            ) : (
              <ChevronDown className="h-3 w-3 text-zinc-500" />
            )}
          </button>
          {expandedSection === "devices" && (
            <div className="mt-2 space-y-1 max-h-60 overflow-y-auto">
              {filtered.slice(0, 50).map((e) => (
                <EmitterRow
                  key={e.id}
                  emitter={e}
                  onClick={() => onEmitterSelect?.(e)}
                />
              ))}
              {filtered.length > 50 && (
                <p className="text-[9px] text-zinc-600 text-center py-1">
                  ... and {filtered.length - 50} more
                </p>
              )}
            </div>
          )}
        </div>

        {/* Readings info */}
        {stats && (
          <div className="border-t border-zinc-700/50 px-3 py-2">
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div className="flex items-center gap-1.5">
                <Eye className="h-3 w-3 text-zinc-500" />
                <span className="text-zinc-500">Readings:</span>
                <span className="text-zinc-300 font-mono">
                  {stats.readings.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Activity className="h-3 w-3 text-zinc-500" />
                <span className="text-zinc-500">Tomo:</span>
                <span className="text-zinc-300 font-mono">
                  {stats.tomo_pts.toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Emitter Row sub-component ── */
function EmitterRow({
  emitter,
  onClick,
}: {
  emitter: TscmEmitter;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-zinc-800/80 transition-colors group"
    >
      <span
        className={`h-1.5 w-1.5 rounded-full shrink-0 ${THREAT_DOTS[emitter.threat_level]}`}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          {emitter.emitter_type === "ble" ? (
            <Bluetooth className="h-2.5 w-2.5 text-blue-400 shrink-0" />
          ) : (
            <Wifi className="h-2.5 w-2.5 text-cyan-400 shrink-0" />
          )}
          <span className="text-[10px] text-zinc-200 truncate">
            {emitter.name || emitter.address}
          </span>
        </div>
        <div className="flex items-center gap-2 text-[9px] text-zinc-500">
          <span className="font-mono">{emitter.address}</span>
          <span>{emitter.avg_rssi?.toFixed(0)} dBm</span>
        </div>
      </div>
      <span
        className={`shrink-0 rounded px-1.5 py-0.5 text-[8px] font-bold border ${THREAT_COLORS[emitter.threat_level]}`}
      >
        {emitter.threat_level}
      </span>
    </button>
  );
}

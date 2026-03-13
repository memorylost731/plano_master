/**
 * TimeSlider -- 4D time scrubber with playback controls for TSCM map
 *
 * Renders at bottom of screen:
 *   [|<<] [<] [play/pause] [>] [>>|]  [speed: 2x]  [window: 1d]
 *   [===========================|thumb|================================]
 *   [sparkline density chart behind the track]
 *   [current time display]
 */

import { useCallback, useMemo } from "react";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronsLeft,
  ChevronsRight,
  Clock,
  Activity,
  Loader2,
} from "lucide-react";
import type { TimeRangeMeta, PlaybackState } from "../../types/tscm";
import { WINDOW_PRESETS, SPEED_PRESETS } from "../../types/tscm";

interface TimeSliderProps {
  meta: TimeRangeMeta | null;
  playback: PlaybackState;
  loading: boolean;
  onSeek: (isoTime: string) => void;
  onTogglePlay: () => void;
  onSetSpeed: (speed: number) => void;
  onSetWindowSize: (seconds: number) => void;
  activeEmitters?: number;
  maxThreat?: string;
}

function isoToMs(iso: string): number {
  return new Date(iso).getTime();
}

function msToIso(ms: number): string {
  return new Date(ms).toISOString();
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatDateShort(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export default function TimeSlider({
  meta,
  playback,
  loading,
  onSeek,
  onTogglePlay,
  onSetSpeed,
  onSetWindowSize,
  activeEmitters,
  maxThreat,
}: TimeSliderProps) {
  if (!meta) return null;

  const startMs = isoToMs(meta.first_reading);
  const endMs = isoToMs(meta.last_reading);
  const rangeMs = endMs - startMs;
  const currentMs = isoToMs(playback.currentTime);

  /* ── Slider position as 0..1 fraction ── */
  const fraction = rangeMs > 0 ? (currentMs - startMs) / rangeMs : 0;
  const pct = Math.max(0, Math.min(100, fraction * 100));

  /* ── Sparkline: normalize density to max ── */
  const maxDensity = useMemo(
    () => Math.max(1, ...meta.density.map((d) => d.count)),
    [meta.density],
  );

  /* ── Handle slider input ── */
  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseFloat(e.target.value);
      const newMs = startMs + (val / 1000) * rangeMs;
      onSeek(msToIso(newMs));
    },
    [startMs, rangeMs, onSeek],
  );

  /* ── Jump forward/backward by window size ── */
  const jumpBy = useCallback(
    (direction: number) => {
      const jumpMs = playback.windowSize * 1000 * direction;
      const newMs = Math.max(startMs, Math.min(endMs, currentMs + jumpMs));
      onSeek(msToIso(newMs));
    },
    [currentMs, playback.windowSize, startMs, endMs, onSeek],
  );

  /* ── Jump to start/end ── */
  const jumpToStart = useCallback(
    () => onSeek(meta.first_reading),
    [meta.first_reading, onSeek],
  );
  const jumpToEnd = useCallback(
    () => onSeek(meta.last_reading),
    [meta.last_reading, onSeek],
  );

  /* ── Current window size preset label ── */
  const windowLabel =
    WINDOW_PRESETS.find((p) => p.seconds === playback.windowSize)?.label ||
    `${Math.round(playback.windowSize / 3600)}h`;

  return (
    <div className="absolute bottom-4 left-4 right-4 z-30">
      <div className="rounded-xl border border-zinc-700/60 bg-zinc-900/95 shadow-2xl backdrop-blur-xl overflow-hidden">
        {/* Top row: time display + stats */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800/60">
          <div className="flex items-center gap-3">
            <Clock className="h-3.5 w-3.5 text-zinc-500" />
            <span className="text-xs font-mono text-zinc-200">
              {formatDateTime(playback.currentTime)}
            </span>
            {loading && (
              <Loader2 className="h-3 w-3 text-zinc-500 animate-spin" />
            )}
          </div>
          <div className="flex items-center gap-4 text-[10px] text-zinc-500">
            {activeEmitters !== undefined && (
              <span>
                <Activity className="inline h-3 w-3 mr-1" />
                {activeEmitters} active
              </span>
            )}
            {maxThreat && maxThreat !== "BENIGN" && (
              <span
                className={
                  maxThreat === "CRITICAL"
                    ? "text-red-400"
                    : maxThreat === "HIGH"
                      ? "text-orange-400"
                      : "text-yellow-400"
                }
              >
                {maxThreat}
              </span>
            )}
            <span className="text-zinc-600">
              {formatDateShort(meta.first_reading)} -{" "}
              {formatDateShort(meta.last_reading)} ({meta.total_days}d)
            </span>
          </div>
        </div>

        {/* Sparkline + slider row */}
        <div className="relative px-4 pt-3 pb-1">
          {/* Sparkline behind slider */}
          <div className="absolute inset-x-4 top-3 h-6 flex items-end gap-px opacity-30">
            {meta.density.map((d, i) => (
              <div
                key={i}
                className="flex-1 bg-blue-500/50 rounded-t-sm min-w-[1px]"
                style={{
                  height: `${(d.count / maxDensity) * 100}%`,
                  minHeight: d.count > 0 ? "1px" : "0",
                }}
                title={`${d.date}: ${d.count} readings`}
              />
            ))}
          </div>

          {/* Range slider */}
          <input
            type="range"
            min={0}
            max={1000}
            value={Math.round(fraction * 1000)}
            onChange={handleSliderChange}
            className="relative z-10 w-full h-6 appearance-none bg-transparent cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-6
              [&::-webkit-slider-thumb]:rounded-sm [&::-webkit-slider-thumb]:bg-red-500 [&::-webkit-slider-thumb]:border
              [&::-webkit-slider-thumb]:border-red-400 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-grab
              [&::-webkit-slider-runnable-track]:h-0.5 [&::-webkit-slider-runnable-track]:rounded
              [&::-webkit-slider-runnable-track]:bg-zinc-700"
          />

          {/* Window indicator (shows the visible time window width) */}
          <div
            className="absolute top-3 h-6 bg-red-500/10 border-x border-red-500/30 pointer-events-none z-[5]"
            style={{
              left: `${Math.max(0, pct - (playback.windowSize / (rangeMs / 1000)) * 50)}%`,
              width: `${Math.min(100, (playback.windowSize / (rangeMs / 1000)) * 100)}%`,
              marginLeft: "1rem",
              marginRight: "1rem",
            }}
          />
        </div>

        {/* Controls row */}
        <div className="flex items-center justify-between px-4 py-2">
          {/* Playback controls */}
          <div className="flex items-center gap-1">
            <button
              onClick={jumpToStart}
              className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
              title="Jump to start"
            >
              <SkipBack className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => jumpBy(-1)}
              className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
              title={`Back ${windowLabel}`}
            >
              <ChevronsLeft className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={onTogglePlay}
              className={`rounded-lg p-2 transition-colors ${
                playback.playing
                  ? "bg-red-600/30 text-red-400 hover:bg-red-600/40"
                  : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
              title={playback.playing ? "Pause" : "Play"}
            >
              {playback.playing ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </button>
            <button
              onClick={() => jumpBy(1)}
              className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
              title={`Forward ${windowLabel}`}
            >
              <ChevronsRight className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={jumpToEnd}
              className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
              title="Jump to latest"
            >
              <SkipForward className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Speed selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-zinc-600 mr-1">Speed</span>
            {SPEED_PRESETS.map((s) => (
              <button
                key={s}
                onClick={() => onSetSpeed(s)}
                className={`rounded px-1.5 py-0.5 text-[10px] font-mono transition-colors ${
                  playback.speed === s
                    ? "bg-red-600/30 text-red-400 border border-red-500/40"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          {/* Window size selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-zinc-600 mr-1">Window</span>
            {WINDOW_PRESETS.map((p) => (
              <button
                key={p.seconds}
                onClick={() => onSetWindowSize(p.seconds)}
                className={`rounded px-1.5 py-0.5 text-[10px] font-mono transition-colors ${
                  playback.windowSize === p.seconds
                    ? "bg-blue-600/30 text-blue-400 border border-blue-500/40"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

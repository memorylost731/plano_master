/**
 * useTscm4D -- React hook for 4D TSCM timeline state management
 *
 * Manages: time range bounds, playback state, snapshot fetching, debounced scrub
 */

import { useState, useEffect, useRef, useCallback } from "react";
import type {
  TimeRangeMeta,
  TscmSnapshot,
  PlaybackState,
  EmitterTrail,
  TimeRange,
} from "../types/tscm";

const BASE_URL = "/api/tscm/4d";
const FETCH_INTERVAL_MS = 500; // polling interval during playback
const SCRUB_DEBOUNCE_MS = 300; // debounce on slider drag

interface UseTscm4DReturn {
  /** Available time range metadata (for slider bounds + sparkline) */
  meta: TimeRangeMeta | null;
  /** Current snapshot for the active time window */
  snapshot: TscmSnapshot | null;
  /** Loading state */
  loading: boolean;
  /** Playback controls */
  playback: PlaybackState;
  /** Set current time (ISO string) -- used by slider scrub */
  seekTo: (isoTime: string) => void;
  /** Toggle play/pause */
  togglePlay: () => void;
  /** Set playback speed */
  setSpeed: (speed: number) => void;
  /** Set window size (seconds) */
  setWindowSize: (seconds: number) => void;
  /** Fetch trail for a specific emitter */
  fetchTrail: (emitterId: number) => Promise<EmitterTrail | null>;
  /** Current time window being displayed */
  currentWindow: TimeRange | null;
  /** Error message if any */
  error: string | null;
}

function isoToMs(iso: string): number {
  return new Date(iso).getTime();
}

function msToIso(ms: number): string {
  return new Date(ms).toISOString();
}

export function useTscm4D(): UseTscm4DReturn {
  const [meta, setMeta] = useState<TimeRangeMeta | null>(null);
  const [snapshot, setSnapshot] = useState<TscmSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playback, setPlayback] = useState<PlaybackState>({
    playing: false,
    speed: 1,
    currentTime: new Date().toISOString(),
    windowSize: 86400, // 1 day default
  });

  const playbackRef = useRef(playback);
  playbackRef.current = playback;

  const metaRef = useRef(meta);
  metaRef.current = meta;

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const playInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastFetchTime = useRef<string>("");

  /* ── Fetch time range metadata on mount ── */
  useEffect(() => {
    async function loadMeta() {
      try {
        const res = await fetch(`${BASE_URL}/time-range`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: TimeRangeMeta = await res.json();
        setMeta(data);
        // Initialize playhead to latest reading
        setPlayback((prev) => ({
          ...prev,
          currentTime: data.last_reading,
        }));
      } catch (e) {
        setError(`Failed to load time range: ${e}`);
      }
    }
    loadMeta();
  }, []);

  /* ── Compute current window from playhead ── */
  const currentWindow: TimeRange | null = meta
    ? {
        t0: msToIso(
          isoToMs(playback.currentTime) - (playback.windowSize * 1000) / 2,
        ),
        t1: msToIso(
          isoToMs(playback.currentTime) + (playback.windowSize * 1000) / 2,
        ),
      }
    : null;

  /* ── Fetch snapshot for current window ── */
  const fetchSnapshot = useCallback(
    async (window: TimeRange) => {
      const key = `${window.t0}|${window.t1}`;
      if (key === lastFetchTime.current) return; // skip duplicate
      lastFetchTime.current = key;

      setLoading(true);
      try {
        const params = new URLSearchParams({
          t0: window.t0,
          t1: window.t1,
          resolution: "medium",
        });
        const res = await fetch(`${BASE_URL}/snapshot?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: TscmSnapshot = await res.json();
        setSnapshot(data);
        setError(null);
      } catch (e) {
        setError(`Snapshot fetch failed: ${e}`);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  /* ── Debounced fetch on window change ── */
  useEffect(() => {
    if (!currentWindow) return;

    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      fetchSnapshot(currentWindow);
    }, playback.playing ? 0 : SCRUB_DEBOUNCE_MS);

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [currentWindow?.t0, currentWindow?.t1, fetchSnapshot, playback.playing]);

  /* ── Playback timer ── */
  useEffect(() => {
    if (playInterval.current) {
      clearInterval(playInterval.current);
      playInterval.current = null;
    }

    if (!playback.playing || !meta) return;

    const startMs = isoToMs(meta.first_reading);
    const endMs = isoToMs(meta.last_reading);

    playInterval.current = setInterval(() => {
      setPlayback((prev) => {
        // Advance by speed * interval in "data time"
        // At speed=1, 500ms real = 500ms data time
        // At speed=8, 500ms real = 4000ms data time
        // For 119-day range, speed=1 would take 119 days to play.
        // Scale: at speed=1, 1 real second = 1 hour of data time
        const advanceMs = prev.speed * FETCH_INTERVAL_MS * 7200; // 1 real sec = 1 hour data
        const newMs = isoToMs(prev.currentTime) + advanceMs;

        if (newMs >= endMs) {
          // Reached end -- stop playback
          return { ...prev, playing: false, currentTime: msToIso(endMs) };
        }

        return { ...prev, currentTime: msToIso(Math.max(startMs, newMs)) };
      });
    }, FETCH_INTERVAL_MS);

    return () => {
      if (playInterval.current) clearInterval(playInterval.current);
    };
  }, [playback.playing, playback.speed, meta]);

  /* ── Public API ── */
  const seekTo = useCallback((isoTime: string) => {
    setPlayback((prev) => ({ ...prev, currentTime: isoTime }));
  }, []);

  const togglePlay = useCallback(() => {
    setPlayback((prev) => ({ ...prev, playing: !prev.playing }));
  }, []);

  const setSpeed = useCallback((speed: number) => {
    setPlayback((prev) => ({ ...prev, speed }));
  }, []);

  const setWindowSize = useCallback((seconds: number) => {
    setPlayback((prev) => ({ ...prev, windowSize: seconds }));
  }, []);

  const fetchTrail = useCallback(
    async (emitterId: number): Promise<EmitterTrail | null> => {
      if (!currentWindow) return null;
      try {
        const params = new URLSearchParams({
          t0: currentWindow.t0,
          t1: currentWindow.t1,
        });
        const res = await fetch(
          `${BASE_URL}/trail/${emitterId}?${params}`,
        );
        if (!res.ok) return null;
        return await res.json();
      } catch {
        return null;
      }
    },
    [currentWindow],
  );

  return {
    meta,
    snapshot,
    loading,
    playback,
    seekTo,
    togglePlay,
    setSpeed,
    setWindowSize,
    fetchTrail,
    currentWindow,
    error,
  };
}

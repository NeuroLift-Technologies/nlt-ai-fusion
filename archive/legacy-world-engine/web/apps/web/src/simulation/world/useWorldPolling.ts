"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  Position,
  SimDetail,
  SimSummary,
  SpeedChangeResponse,
  TimeSpeedLabel,
  WorldState,
} from "./types";

// ---------------------------------------------------------------------------
// Base URL resolution
//
// The deployed frontend talks to the FastAPI backend.  The env var may be
// shipped with a trailing ``/api`` or ``/api/v1`` (or a bare origin), so we
// normalise to an origin and always append ``/api/world``.
// ---------------------------------------------------------------------------
function resolveWorldOrigin(): string {
  const raw =
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE_URL) ||
    "http://localhost:8000";

  let url = raw.replace(/\/+$/, "");
  url = url.replace(/\/(api\/v\d+|api|v\d+)$/i, "");
  return url.replace(/\/+$/, "");
}

export const WORLD_BASE_URL = `${resolveWorldOrigin()}/api/world`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${WORLD_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = "";
    try {
      detail = await response.text();
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const worldApi = {
  /** Poll this to get the live world snapshot. */
  getWorldState: () => request<WorldState>("/state"),
  /** Flip the simulation time speed. ``label`` must be one of realtime|fast|ultra|hyper. */
  setTimeSpeed: (speed: TimeSpeedLabel | string) =>
    request<SpeedChangeResponse>("/time/speed", {
      method: "POST",
      body: JSON.stringify({ speed }),
    }),
  /** Detailed state for a single Sim (matched by entity id or agent id). */
  getSimDetail: (simId: string) =>
    request<SimDetail>(`/sims/${encodeURIComponent(simId)}`),
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface WorldPolling {
  state: WorldState | null;
  loading: boolean;
  error: string | null;
  paused: boolean;
  pause: () => void;
  resume: () => void;
  togglePause: () => void;
  refetch: () => Promise<void>;
}

const DEFAULT_POLL_MS = 1000;

export function useWorldPolling(pollIntervalMs = DEFAULT_POLL_MS): WorldPolling {
  const [state, setState] = useState<WorldState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState<boolean>(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stoppedRef = useRef(true);

  const fetchState = useCallback(async () => {
    try {
      const next = await worldApi.getWorldState();
      setState(next);
      setError(null);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void fetchState();
  }, [fetchState]);

  // Polling loop
  useEffect(() => {
    if (paused) {
      return;
    }
    stoppedRef.current = false;
    void fetchState();
    timerRef.current = setInterval(() => {
      if (stoppedRef.current) return;
      void fetchState();
    }, pollIntervalMs);
    return () => {
      stoppedRef.current = true;
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [paused, pollIntervalMs, fetchState]);

  const pause = useCallback(() => setPaused(true), []);
  const resume = useCallback(() => setPaused(false), []);
  const togglePause = useCallback(() => setPaused((p) => !p), []);

  return {
    state,
    loading,
    error,
    paused,
    pause,
    resume,
    togglePause,
    refetch: fetchState,
  };
}

// ---------------------------------------------------------------------------
// Helpers shared with the view layer
// ---------------------------------------------------------------------------

export function simColor(simId: string): string {
  let hash = 0;
  for (let i = 0; i < simId.length; i++) {
    hash = (hash * 31 + simId.charCodeAt(i)) | 0;
  }
  const h = Math.abs(hash) % 360;
  return `hsl(${h}, 70%, 48%)`;
}

export function simPosition(sim: SimSummary): Position {
  return sim.position ?? { x: 0, y: 0, z: 0 };
}

export function minimumNeed(needs: Record<string, number> | undefined): number {
  if (!needs || Object.keys(needs).length === 0) return 100;
  return Math.min(...Object.values(needs));
}

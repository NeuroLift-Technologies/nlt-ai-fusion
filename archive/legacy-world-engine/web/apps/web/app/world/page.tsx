"use client";

import { useEffect, useState } from "react";
import { RefreshCw, WifiOff } from "lucide-react";

import { Button } from "@/components/ui/button";

import { useWorldPolling, worldApi } from "../../src/simulation/world/useWorldPolling";
import WorldView from "../../src/simulation/world/WorldView";
import TimeControls from "../../src/simulation/world/TimeControls";
import SimInspector from "../../src/simulation/world/SimInspector";
import type { SimDetail, SimSummary } from "../../src/simulation/world/types";

export default function WorldPage() {
  const { state, loading, error, paused, togglePause, refetch } = useWorldPolling();
  const [selectedSim, setSelectedSim] = useState<SimSummary | null>(null);
  const [detail, setDetail] = useState<SimDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Fetch detailed state for the selected Sim.
  useEffect(() => {
    if (!selectedSim) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    worldApi
      .getSimDetail(selectedSim.sim_id)
      .then((d) => {
        if (!cancelled) {
          setDetail(d);
          setDetailLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDetailLoading(false);
          setDetailError(
            err instanceof Error ? err.message : "Could not load Sim details",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedSim]);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sims World</h1>
          <p className="text-sm text-muted-foreground">
            Live 2D top-down simulation of the house. Sims move around, fulfill
            needs, and follow their schedules in real time.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {error && (
            <span className="inline-flex items-center gap-1.5 text-xs text-destructive">
              <WifiOff className="h-3.5 w-3.5" />
              {error}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={() => void refetch()}>
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="ml-1.5">Refresh</span>
          </Button>
        </div>
      </header>

      {state && (
        <TimeControls time={state.time} paused={paused} onTogglePause={togglePause} />
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-2">
          <div className="relative h-[640px] w-full min-h-[420px] rounded-lg border border-border bg-card">
            <WorldView
              state={state}
              selectedSimId={selectedSim ? selectedSim.sim_id : null}
              onSelectSim={setSelectedSim}
              onDeselect={() => setSelectedSim(null)}
            />
            {loading && !state && (
              <div className="absolute inset-0 flex items-center justify-center bg-card/60 text-sm text-muted-foreground">
                Connecting to the simulation…
              </div>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Keyboard: arrow keys move the cursor (Shift + arrow moves 5 cells),
            Enter selects the nearest Sim, Escape deselects.
          </p>
        </div>
        {detailError && (
          <p className="text-xs text-destructive" role="alert">
            Failed to load Sim details: {detailError}
          </p>
        )}
        <SimInspector
          sim={detail}
          loading={detailLoading}
          onClear={() => setSelectedSim(null)}
        />
      </div>
    </div>
  );
}

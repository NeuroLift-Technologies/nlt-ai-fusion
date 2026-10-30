"use client";

import { useState, type MouseEvent } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Pause, Play, Sun, Moon } from "lucide-react";

import { worldApi } from "./useWorldPolling";
import type { TimeSpeedLabel, TimeState } from "./types";

interface TimeControlsProps {
  time: TimeState;
  paused: boolean;
  onTogglePause: () => void;
}

// Button → backend speed label. "100x" maps to "hyper" which the backend
// accepts once TimeManager + router support it; otherwise it degrades
// gracefully (see error handling below).
const SPEED_OPTIONS: { label: string; value: TimeSpeedLabel }[] = [
  { label: "1x", value: "realtime" },
  { label: "5x", value: "fast" },
  { label: "20x", value: "ultra" },
  { label: "100x", value: "hyper" },
];

function formatTime(hour: number, minute: number): string {
  const period = hour < 12 ? "AM" : "PM";
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  const mm = minute.toString().padStart(2, "0");
  return `${h12}:${mm} ${period}`;
}

export default function TimeControls({
  time,
  paused,
  onTogglePause,
}: TimeControlsProps) {
  const { toast } = useToast();
  const [pending, setPending] = useState<TimeSpeedLabel | null>(null);

  async function handleSpeed(value: TimeSpeedLabel, e: MouseEvent<HTMLButtonElement>) {
    e.preventDefault();
    setPending(value);
    try {
      const res = await worldApi.setTimeSpeed(value);
      toast({
        title: "Speed changed",
        description: `${res.new_label} (${res.new_speed}×) is active`,
        duration: 1500,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not change speed";
      toast({
        title: "Speed change failed",
        description: message,
        duration: 3000,
      });
    } finally {
      setPending(null);
    }
  }

  const activeLabel = pending ?? (time.speed_label as TimeSpeedLabel);

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <div
        aria-label={time.is_daytime ? "Day" : "Night"}
        className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-sm"
      >
        {time.is_daytime ? (
          <Sun className="h-4 w-4 text-amber-400" />
        ) : (
          <Moon className="h-4 w-4 text-slate-400" />
        )}
        <span className="font-medium">Day {time.day}</span>
        <span className="text-muted-foreground" aria-hidden="true">
          •
        </span>
        <span className="tabular-nums">{formatTime(time.hour, time.minute)}</span>
      </div>

      <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-card p-1 text-sm">
        {SPEED_OPTIONS.map((opt) => {
          const active = activeLabel === opt.value;
          return (
            <Button
              key={opt.value}
              variant={active ? "default" : "outline"}
              size="sm"
              disabled={pending !== null}
              className={
                active
                  ? "bg-brand-600 text-brand-50 hover:bg-brand-700"
                  : "border-border text-muted-foreground hover:bg-accent"
              }
              onClick={(e) => handleSpeed(opt.value, e)}
            >
              {opt.label}
            </Button>
          );
        })}
      </div>

      <Button
        variant={paused ? "default" : "outline"}
        size="sm"
        onClick={onTogglePause}
        className={
          paused
            ? "bg-brand-600 text-brand-50 hover:bg-brand-700"
            : "border-border text-muted-foreground hover:bg-accent"
        }
      >
        {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
        <span className="ml-1.5">{paused ? "Resume" : "Pause"}</span>
      </Button>

      {time.speed_multiplier !== undefined && (
        <span className="text-xs text-muted-foreground tabular-nums">
          {time.speed_multiplier}×
        </span>
      )}
    </div>
  );
}

"use client";

import { X, MapPin, Heart, Users, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

import type { Position, Relationship, SimDetail } from "./types";

interface SimInspectorProps {
  sim: SimDetail | null;
  loading: boolean;
  onClear: () => void;
}

function needColor(value: number): string {
  if (value < 30) return "bg-red-500";
  if (value < 55) return "bg-amber-400";
  return "bg-emerald-500";
}

function NeedBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground capitalize">{label}</span>
        <span className="font-mono tabular-nums">{Math.round(value)}/100</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", needColor(pct))}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function RelationshipRow({ rel }: { rel: Relationship }) {
  const scoreBar = (value: number, label: string) => (
    <div className="inline-flex items-center gap-1 text-xs">
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-mono tabular-nums">{Math.round(value)}</span>
    </div>
  );
  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
      <div>
        <div className="font-medium">{rel.other_sim_name ?? rel.other_sim_id}</div>
        <div className="text-xs text-muted-foreground">
          {rel.interaction_count} interaction{rel.interaction_count === 1 ? "" : "s"}
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs">
        {scoreBar(rel.friendship, "Friendship")}
        {scoreBar(rel.romance, "Romance")}
        {scoreBar(rel.familiarity, "Familiarity")}
      </div>
    </div>
  );
}

function positionLabel(pos: Position): string {
  return `(${pos.x}, ${pos.y})`;
}

export default function SimInspector({ sim, loading, onClear }: SimInspectorProps) {
  if (!sim) {
    return (
      <Card className="h-full">
        <CardContent className="flex h-full flex-col items-center justify-center gap-3 py-8 text-center">
          <Users className="h-10 w-10 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            Click on a Sim in the world view to inspect their needs, mood,
            schedule, and relationships.
          </p>
        </CardContent>
      </Card>
    );
  }

  const needEntries = Object.entries(sim.needs).sort((a, b) => a[1] - b[1]);
  const moodLabel = sim.mood;
  const activeSchedule = sim.schedule?.weekend ? "weekend" : "workday";

  const entries = sim.schedule?.[
    sim.schedule.weekend ? "weekend_schedule" : "workday_schedule"
  ]?.entries ?? [];

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="relative pb-3">
        <CardTitle className="text-xl">{sim.name}</CardTitle>
        <CardDescription>
          <span className="inline-flex items-center gap-1.5">
            <MapPin className="h-3 w-3" />
            {sim.room} · {positionLabel(sim.position)}
          </span>
        </CardDescription>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Close inspector"
          className="absolute top-3 right-3 h-6 w-6"
          onClick={onClear}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto space-y-5">
        {/* Activity + mood */}
        <div className="flex items-center justify-between rounded-lg border border-border bg-card/50 p-3">
          <div>
            <div className="text-xs text-muted-foreground">Activity</div>
            <div className="font-medium">{sim.current_activity}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Mood</div>
            <Badge
              variant={
                moodLabel === "happy" || moodLabel === "content"
                  ? "default"
                  : moodLabel === "uncomfortable"
                    ? "secondary"
                    : "destructive"
              }
            >
              {moodLabel}
            </Badge>
          </div>
        </div>

        {/* Needs meters */}
        <div>
          <div className="mb-2 text-xs font-semibold text-muted-foreground">
            Needs (lowest first)
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {needEntries.map(([key, value]) => (
              <NeedBar key={key} label={key} value={value} />
            ))}
          </div>
        </div>

        {/* Schedule */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span>{activeSchedule} schedule</span>
          </div>
          <div className="space-y-1.5">
            {entries.map((entry, i) => {
              const isCurrent = entry.activity === sim.current_activity;
              const range =
                entry.start_hour === entry.end_hour
                  ? "all day"
                  : `${String(entry.start_hour).padStart(2, "0")}:00–${String(entry.end_hour).padStart(2, "0")}:00`;
              return (
                <div
                  key={`${entry.activity}-${i}`}
                  className={cn(
                    "flex items-center justify-between rounded-md border border-border px-3 py-1.5 text-sm",
                    isCurrent
                      ? "bg-brand-50 dark:bg-brand-900/20 border-brand-600"
                      : "bg-card",
                  )}
                >
                  <span className="font-medium">{entry.activity}</span>
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {range}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Relationships */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            <Heart className="h-3.5 w-3.5" />
            <span>Relationships ({sim.relationships.length})</span>
          </div>
          {sim.relationships.length === 0 ? (
            <p className="text-sm text-muted-foreground">No relationships yet.</p>
          ) : (
            <div className="divide-y divide-border rounded-md border border-border">
              {sim.relationships.map((rel, i) => (
                <RelationshipRow key={`${rel.other_sim_id}-${i}`} rel={rel} />
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

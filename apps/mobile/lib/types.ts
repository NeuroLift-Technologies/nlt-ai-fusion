/**
 * API types for the mobile screens. Mirrors apps/web/lib/types.ts; keep the two in step.
 */

export type AvatarType = "stay_alert" | "task_kickstart";

export type AideType = "stay_alert_aide" | "task_kickstart_aide";

export type SessionStatus = "pending" | "running" | "completed" | "aborted" | "failed";

export type ScenarioType = "workplace" | "personal" | "social";

export interface AvatarSummary {
  id: string;
  type: AvatarType;
  display_name: string;
  description: string;
  traits: string[];
}

export interface AideSummary {
  id: string;
  type: AideType;
  display_name: string;
  description: string;
  expertise: string[];
}

export interface ScenarioConfig {
  type: ScenarioType;
  difficulty: number;
  /** Optional in a request: the API defaults it to "" (apps/api/schemas/models.py). */
  description?: string;
}

export interface SessionSummary {
  session_id: string;
  status: SessionStatus;
  avatar_type: AvatarType;
  aide_type: AideType;
  created_at: string;
}

export interface ScenarioResult {
  scenario_index: number;
  scenario_type: string;
  attempts: number;
  successes: number;
  success_rate: number;
  coaching_events: number;
  peak_burnout_risk: number;
  completed: boolean;
}

export interface SessionResult {
  session_id: string;
  status: SessionStatus;
  avatar_type: AvatarType;
  aide_type: AideType;
  scenario_results: ScenarioResult[];
  overall_success_rate: number;
  final_independence_level: number;
  peak_burnout_risk: number;
  fusion_ready: boolean;
  duration_seconds: number;
  error: string | null;
}

export interface SessionCreatePayload {
  avatar_type: AvatarType;
  aide_type: AideType;
  scenarios: ScenarioConfig[];
  max_attempts_per_scenario?: number;
  max_coaching_per_attempt?: number;
  independence_target?: number;
}

export interface Position {
  x: number;
  y: number;
  z: number;
}

export interface TimeState {
  day: number;
  hour: number;
  minute: number;
  is_daytime: boolean;
  total_minutes_elapsed: number;
  speed_multiplier: number;
  speed_label: string;
}

export type SimState =
  | "initializing"
  | "running"
  | "paused"
  | "completed"
  | "error";

export interface WorldConfig {
  grid_width: number;
  grid_height: number;
  seconds_per_tick: number;
  time_speed_multiplier: number;
}

export interface SimSummary {
  sim_id: string;
  name: string;
  position: Position;
  room: string;
  current_activity: string;
  needs_summary: Record<string, number>;
}

export interface Furniture {
  entity_id: string;
  furniture_type: string;
  position: Position;
  affordances: string[];
  in_use_by: string | null;
}

export interface Room {
  name: string;
  furniture: Furniture[];
  occupants: string[];
}

export interface EntitySummary {
  entity_id: string;
  position: Position | null;
  components: string[];
}

export interface WorldState {
  simulation_id: string;
  tick_count: number;
  state: string;
  config: WorldConfig;
  time: TimeState;
  rooms: Room[];
  sims: SimSummary[];
  entities: EntitySummary[];
}

export interface Relationship {
  other_sim_id: string;
  other_sim_name: string | null;
  friendship: number;
  romance: number;
  familiarity: number;
  interaction_count: number;
}

export interface ScheduleEntry {
  activity: string;
  start_hour: number;
  end_hour: number;
  required_furniture: string | null;
  required_room: string | null;
  need_fulfilled: string | null;
}

export interface SimSchedule {
  workday_schedule: { entries: ScheduleEntry[] };
  weekend_schedule: { entries: ScheduleEntry[] };
  current_activity: string | null;
  weekend: boolean;
}

export interface SimDetail {
  sim_id: string;
  name: string;
  position: Position;
  room: string;
  current_activity: string;
  needs: Record<string, number>;
  mood: string;
  weekend: boolean;
  relationships: Relationship[];
  schedule: SimSchedule;
}

export interface SpeedChangeResponse {
  previous_speed: number;
  previous_label: string;
  new_speed: number;
  new_label: string;
}

export type TimeSpeedLabel = "realtime" | "fast" | "ultra" | "hyper";

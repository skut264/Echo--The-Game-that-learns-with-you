export interface LoginResponse {
  token: string;
  player_id: number;
  username: string;
}

export interface GameStartResponse {
  session_id: number;
  level: number;
  sequence_length: number;
  difficulty: number;
  current_rule: string;
  color_theme: string;
}

export interface Coaching {
  hint: string | null;
  text: string | null;
  source: string;
}

export interface LayerUpdate {
  disabled?: boolean;
  speed_multiplier?: number;
  feedback_boost?: boolean;
  time_multiplier?: number;
}

export interface AttemptResponse {
  state: string;
  action: string;
  difficulty: number;
  level: number;
  sequence_length: number;
  consecutive_wins: number;
  consecutive_losses: number;
  color_theme: string;
  layer_updates: Record<string, LayerUpdate>;
  coaching: Coaching;
  new_rule?: string;
  dashboard: DashboardSnapshot;
}

export interface DashboardSnapshot {
  level: number;
  sequence_length: number;
  difficulty: number;
  state: string;
  consecutive_wins: number;
  total_attempts: number;
  correct_attempts: number;
  win_rate: number;
  recovery_streak: number;
}

export interface GameEndResponse {
  session_id: number;
  is_flow_session: boolean;
  final_level: number;
  total_attempts: number;
  correct_attempts: number;
  win_rate: number;
  final_difficulty: number;
}

export interface PlayerStats {
  total_attempts: number;
  correct_attempts: number;
  win_rate: number;
  avg_time_per_note_ms: number;
  avg_difficulty: number;
  total_sessions: number;
  flow_sessions: number;
  avg_session_difficulty: number;
}

export interface SessionSummary {
  id: number;
  started_at: string;
  ended_at: string | null;
  level_at_start: number;
  level_at_end: number;
  total_attempts: number;
  correct_attempts: number;
  is_flow_session: number;
  avg_difficulty: number;
}
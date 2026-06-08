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

// ── Puzzle System Types ──

export type PuzzleType = 'pattern_recall' | 'psychology_question' | 'motion_tracking' | 'spatial_golden';

export interface FibNote {
  index: number;
  x: number;
  y: number;
  size: number;
  rotation: number;
  color: string;
  shape: 'circle' | 'hexagon' | 'diamond' | 'star';
}

export interface MotionObject {
  index: number;
  start_x: number;
  start_y: number;
  end_x: number;
  end_y: number;
  travel_time_ms: number;
  color: string;
  size: number;
}

export interface GoldenShape {
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  color: string;
  is_correct: boolean;
  shape: string;
}

export interface PatternPuzzleData {
  puzzle_type: 'pattern_recall';
  notes: FibNote[];
  canvas_width: number;
  canvas_height: number;
  display_timings: number[];
  fib_spiral_visible: boolean;
  background_spiral: { arms: number; growth: number; opacity: number } | null;
}

export interface MotionPuzzleData {
  puzzle_type: 'motion_tracking';
  objects: MotionObject[];
  canvas_width: number;
  canvas_height: number;
  fib_spiral_visible: boolean;
  background_spiral: { arms: number; growth: number; opacity: number } | null;
}

export interface SpatialPuzzleData {
  puzzle_type: 'spatial_golden';
  shapes: GoldenShape[];
  canvas_width: number;
  canvas_height: number;
  correct_index: number;
  fib_spiral_visible: boolean;
}

export interface PsychOption {
  text: string;
  weight: number;
  reason: string;
}

export interface PsychQuestionData {
  puzzle_type: 'psychology_question';
  question: string;
  options: PsychOption[];
  correct_index: number;
  explanation: string;
  max_time_ms: number;
}

export type PuzzleData = PatternPuzzleData | MotionPuzzleData | SpatialPuzzleData | PsychQuestionData;

export interface PuzzleGenerateResponse {
  puzzle_id: number;
  puzzle_type: PuzzleType;
  puzzle_data: PuzzleData;
  fib_spiral_visible: boolean;
  background_spiral: { arms: number; growth: number; opacity: number } | null;
}

export interface LLMPredictResponse {
  will_fail: boolean;
  confidence: number;
  reasoning: string;
}

export interface PuzzleSwitchResponse {
  puzzle_id: number;
  puzzle_type: PuzzleType;
  puzzle_data: PuzzleData;
  fib_spiral_visible: boolean;
}

export interface MetricsSnapshotResponse {
  snapshot_id: number;
}
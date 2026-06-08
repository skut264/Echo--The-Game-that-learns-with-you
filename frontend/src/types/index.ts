export interface LoginResponse {
  token: string;
  player_id: number;
  username: string;
}

// ── Dynamic Puzzle Types ──

export interface FibonacciPoint {
  x: number;
  y: number;
  radius: number;
  angle_deg: number;
  fib_n: number;
  opacity: number;
}

export interface GoldenRectangle {
  x: number;
  y: number;
  w: number;
  h: number;
  rotation_deg: number;
}

export interface FibonacciData {
  points: FibonacciPoint[];
  rects: GoldenRectangle[];
  phi: number;
}

export interface CanvasLayout {
  w: number;
  h: number;
  puzzle_area: { x: number; y: number; w: number; h: number };
  hint_area: { x: number; y: number; w: number; h: number };
  feedback_area: { x: number; y: number; w: number; h: number };
}

export interface PuzzleOption {
  text: string;
  weight: number;
}

export type PuzzleType = string;

export interface PuzzleGenerateResponse {
  puzzle_id: number;
  puzzle_type: string;
  puzzle_data: PuzzleData;
  fib_spiral_visible: boolean;
  background_spiral: any;
}

export interface PuzzleData {
  puzzle_id: string;
  puzzle_type: string;
  prompt: string;
  options: PuzzleOption[] | null;
  time_limit_ms: number;
  metadata: Record<string, any>;
  answer_positions: Array<{ x: number; y: number }>;
  fibonacci_data: FibonacciData;
  canvas_layout: CanvasLayout;
}

export interface GameStartResponse {
  session_id: number;
  level: number;
  difficulty: number;
  sequence_length: number;
  current_rule: string;
  color_theme: string;
  puzzle?: PuzzleData;
  dashboard?: DashboardSnapshot;
}

export interface Coaching {
  hint: string | null;
  source: string;
}

export interface FailureAnalysis {
  trend: string;
  speed_delta_ms: number;
  first_time_to_fail_ms: number;
  second_time_to_fail_ms: number;
}

export interface LlmPrediction {
  prediction: boolean;
  confidence: number;
  reasoning: string;
}

export interface AttemptResponse {
  state: string;
  color_theme: string;
  coaching: { hint: string | null; source: string; text?: string | null };
  failure_analysis: FailureAnalysis | null;
  prediction: LlmPrediction | null;
  predicted_will_fail: boolean | null;
  puzzle_action: string;
  puzzle_should_rotate: boolean;
  should_regenerate: boolean;
  fibonacci_data: FibonacciData | null;
  canvas_layout: CanvasLayout | null;
  new_puzzle: PuzzleData | null;
  dashboard: DashboardSnapshot;
  // Legacy fields (v1 compat)
  level?: number;
  difficulty?: number;
  sequence_length?: number;
  consecutive_wins?: number;
  consecutive_losses?: number;
  new_rule?: string | null;
}

export interface GameEndResponse {
  session_id: number;
  is_flow_session: boolean;
  total_puzzles: number;
  correct_puzzles: number;
  win_rate: number;
  streak: number;
}

export interface DashboardSnapshot {
  total_attempts: number;
  correct_attempts: number;
  win_rate: number;
  state: string;
  streak: number;
  recovery_streak: number;
  avg_decision_time_ms: number;
  avg_hesitation_ms: number;
  recent_window_accuracy: number;
  hesitation_score: number;
  current_puzzle_type: string | null;
}

export interface PlayerStats {
  total_puzzles: number;
  correct_puzzles: number;
  win_rate: number;
  avg_time_ms: number;
  avg_decision_ms: number;
  total_sessions: number;
  flow_sessions: number;
  avg_session_difficulty: number;
  total_predictions: number;
  prediction_accuracy: number;
  puzzle_type_breakdown: Array<{ puzzle_type: string; count: number; correct: number }>;
  recent_accuracy: number;
  recent_avg_decision_ms: number;
  total_rotations: number;
}

export interface SessionSummary {
  id: number;
  started_at: string;
  ended_at: string | null;
  total_puzzles: number;
  correct_puzzles: number;
  is_flow_session: number;
  avg_difficulty: number;
}

export interface PuzzleRecord {
  id: number;
  puzzle_id: string;
  puzzle_type: string;
  prompt: string;
  is_correct: number;
  time_visible_ms: number;
  decision_time_ms: number;
  puzzle_attempt_count: number;
  shown_at: string;
}

export interface PredictionRecord {
  id: number;
  puzzle_id: string;
  predicted_fail: number;
  confidence: number;
  reasoning: string;
  actually_failed: number | null;
  created_at: string;
}

export interface RotationRecord {
  id: number;
  old_puzzle_type: string;
  failures_before_rotate: number;
  trend_json: string;
  predicted_will_fail: string;
  new_puzzle_type: string;
  rotated_at: string;
}

export interface PuzzleTypeConfig {
  type: string;
  label: string;
  icon: string;
  color: string;
}

export const PUZZLE_TYPE_CONFIGS: Record<string, PuzzleTypeConfig> = {
  pattern_recognition: { type: 'pattern_recognition', label: 'Pattern Recognition', icon: '\u2B1A', color: '#00d4ff' },
  psychology_question: { type: 'psychology_question', label: 'Psychology', icon: '\uD83E\uDDE0', color: '#b388ff' },
  spatial_logic: { type: 'spatial_logic', label: 'Spatial Logic', icon: '\u2B22', color: '#ffd700' },
  sequence_memory: { type: 'sequence_memory', label: 'Sequence', icon: '\u25CB', color: '#2ecc71' },
  timing_challenge: { type: 'timing_challenge', label: 'Timing', icon: '\u23F1', color: '#e94560' },
};

export const PUZZLE_TYPE_COLORS: Record<string, string> = {
  pattern_recognition: '#00d4ff',
  psychology_question: '#b388ff',
  spatial_logic: '#ffd700',
  sequence_memory: '#2ecc71',
  timing_challenge: '#e94560',
};
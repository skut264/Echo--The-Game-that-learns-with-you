import type { PuzzleData, GameStartResponse, GameEndResponse, PlayerStats, SessionSummary, PuzzleRecord, PredictionRecord, RotationRecord, PuzzleOption, LoginResponse, AttemptResponse, DashboardSnapshot } from '../types';

const API = import.meta.env.VITE_API_URL || '';

function getToken(): string | null {
  return localStorage.getItem('echo_token');
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// Auth
export const authApi = {
  login: (username: string, password: string) =>
    request<LoginResponse>('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  register: (username: string, email: string, password: string) =>
    request<LoginResponse>('/api/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password }),
    }),
};

// Game
export const gameApi = {
  start: () =>
    request<GameStartResponse>('/api/game/start', { method: 'POST' }),
  attempt: (data: {
    puzzle_id: string;
    puzzle_type: string;
    prompt?: string;
    correct_answer?: string;
    is_correct: boolean;
    decision_time_ms?: number;
    time_visible_ms?: number;
    input_latency_ms?: number;
    option_selected?: string;
    hovered_options?: string[];
    hover_durations_ms?: number[];
    puzzle_attempt_count?: number;
    canvas_positions?: Array<{ x: number; y: number }>;
  }) =>
    request<AttemptResponse>('/api/game/attempt', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  end: () =>
    request<GameEndResponse>('/api/game/end', { method: 'POST' }),
  state: () =>
    request<{ dashboard: DashboardSnapshot; current_puzzle: PuzzleData | null }>('/api/game/state'),
  regenPuzzle: () =>
    request<{ puzzle: PuzzleData }>('/api/regen-puzzle'),
};

// Puzzle generation
export const puzzleApi = {
  generate: (puzzleType?: string, sessionId?: number) =>
    request<{ puzzle_id: number; puzzle_type: string; puzzle_data: PuzzleData; fib_spiral_visible: boolean }>(
      '/api/puzzle/generate',
      {
        method: 'POST',
        body: JSON.stringify({ puzzle_type: puzzleType, session_id: sessionId }),
      },
    ),
  psychologyQuestion: () =>
    request<{
      puzzle_type: string;
      question: string;
      options: PuzzleOption[];
      correct_index: number;
      explanation: string;
      max_time_ms: number;
    }>('/api/puzzle/psychology-question', { method: 'POST' }),
  psychologyAnswer: (selectedIndex: number, timeTakenMs: number) =>
    request<{ is_correct: boolean; weight_applied: number }>('/api/puzzle/psychology-answer', {
      method: 'POST',
      body: JSON.stringify({ selected_index: selectedIndex, time_taken_ms: timeTakenMs }),
    }),
  predictFailure: () =>
    request<{ will_fail: boolean; confidence: number; reasoning: string }>('/api/puzzle/llm-predict', {
      method: 'POST',
    }),
  switchPuzzle: () =>
    request<{ puzzle_id: number; puzzle_type: string; puzzle_data: PuzzleData; fib_spiral_visible: boolean }>(
      '/api/puzzle/switch',
      { method: 'POST' },
    ),
};

// Metrics
export const metricsApi = {
  snapshot: (data: { avg_time_per_note_ms?: number; puzzle_type?: string }) =>
    request<{ snapshot_id: number }>('/api/metrics/snapshot', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  history: (limit = 10) =>
    request<{ snapshots: any[] }>(`/api/metrics/history?limit=${limit}`),
};

// Dashboard
export const dashboardApi = {
  stats: () =>
    request<PlayerStats>('/api/dashboard/stats'),
  sessions: (limit = 20) =>
    request<SessionSummary[]>(`/api/dashboard/sessions?limit=${limit}`),
  puzzles: (limit = 20) =>
    request<{ puzzles: PuzzleRecord[] }>(`/api/dashboard/puzzles?limit=${limit}`),
  predictions: (limit = 20) =>
    request<{ predictions: PredictionRecord[] }>(`/api/dashboard/predictions?limit=${limit}`),
  rotations: (limit = 20) =>
    request<{ rotations: RotationRecord[] }>(`/api/dashboard/rotations?limit=${limit}`),
};
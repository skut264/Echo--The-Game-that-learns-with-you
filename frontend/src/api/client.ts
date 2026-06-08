import type {
  LoginResponse,
  GameStartResponse,
  AttemptResponse,
  GameEndResponse,
  PlayerStats,
  SessionSummary,
  PuzzleGenerateResponse,
  LLMPredictResponse,
  PuzzleSwitchResponse,
  PsychQuestionData,
  MetricsSnapshotResponse,
} from '../types';

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
    sequence_length: number;
    is_correct: boolean;
    time_per_note_ms?: number;
    input_latency_ms?: number;
    error_type?: string;
  }) =>
    request<AttemptResponse>('/api/game/attempt', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  end: () =>
    request<GameEndResponse>('/api/game/end', { method: 'POST' }),
  state: () =>
    request<AttemptResponse['dashboard']>('/api/game/state'),
};

// Dashboard
export const dashboardApi = {
  stats: () =>
    request<PlayerStats>('/api/dashboard/stats'),
  sessions: (limit = 20) =>
    request<SessionSummary[]>(`/api/dashboard/sessions?limit=${limit}`),
};

// Puzzle System
export const puzzleApi = {
  generate: (puzzleType?: string) =>
    request<PuzzleGenerateResponse>('/api/puzzle/generate', {
      method: 'POST',
      body: JSON.stringify({ puzzle_type: puzzleType || null }),
    }),
  psychologyQuestion: () =>
    request<PsychQuestionData>('/api/puzzle/psychology-question', {
      method: 'POST',
    }),
  psychologyAnswer: (selectedIndex: number, timeTakenMs: number) =>
    request<{ is_correct: boolean; weight_applied: number }>('/api/puzzle/psychology-answer', {
      method: 'POST',
      body: JSON.stringify({ selected_index: selectedIndex, time_taken_ms: timeTakenMs }),
    }),
  predictFailure: () =>
    request<LLMPredictResponse>('/api/puzzle/llm-predict', {
      method: 'POST',
    }),
  switchPuzzle: () =>
    request<PuzzleSwitchResponse>('/api/puzzle/switch', {
      method: 'POST',
    }),
};

// Metrics
export const metricsApi = {
  snapshot: (data: {
    avg_time_per_note_ms?: number;
    variance_time_per_note?: number;
    error_rate_rolling?: number;
    reaction_time_improvement?: number;
    fatigue_score?: number;
    puzzle_type?: string;
  }) =>
    request<MetricsSnapshotResponse>('/api/metrics/snapshot', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  history: (limit = 10) =>
    request<{ snapshots: any[] }>(`/api/metrics/history?limit=${limit}`),
};
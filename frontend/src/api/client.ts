import type {
  LoginResponse,
  GameStartResponse,
  AttemptResponse,
  GameEndResponse,
  PlayerStats,
  SessionSummary,
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
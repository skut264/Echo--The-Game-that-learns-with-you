import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardApi } from '../api/client';
import type { PlayerStats, SessionSummary } from '../types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<PlayerStats | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [s, sess] = await Promise.all([
          dashboardApi.stats(),
          dashboardApi.sessions(20),
        ]);
        setStats(s);
        setSessions(sess);
      } catch (e: any) {
        setError(e.message || 'Failed to load dashboard');
        if (e.message?.includes('401') || e.message?.includes('Not authenticated')) {
          navigate('/login');
        }
      }
    })();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('echo_token');
    localStorage.removeItem('echo_username');
    navigate('/login');
  };

  const winRate = stats?.win_rate ?? 0;
  const winRatePct = Math.round(winRate * 100);

  // Chart data
  const chartData = sessions.slice().reverse().map((s, _i) => ({
    name: `S${s.id}`,
    difficulty: s.avg_difficulty,
    accuracy: s.total_attempts > 0 ? Math.round((s.correct_attempts / s.total_attempts) * 100) : 0,
    attempts: s.total_attempts,
    flow: s.is_flow_session,
  }));

  const username = localStorage.getItem('echo_username') || 'Player';

  return (
    <div style={{ minHeight: '100vh', background: '#1a1a2e', padding: '20px', color: '#e0e0e0', fontFamily: "'Inter', sans-serif" }}>
      {/* Header */}
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div>
            <span style={{ fontSize: 24, fontWeight: 700, color: '#e94560' }}>Echo</span>
            <span style={{ fontSize: 14, color: '#8892b0', marginLeft: 12 }}>Dashboard — {username}</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => navigate('/game')} style={{ padding: '8px 16px', background: '#16213e', border: '1px solid #3b3b4f', borderRadius: 6, color: '#e0e0e0', cursor: 'pointer' }}>
              Play
            </button>
            <button onClick={handleLogout} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid #e94560', borderRadius: 6, color: '#e94560', cursor: 'pointer' }}>
              Logout
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: 12, background: 'rgba(233,69,96,0.1)', border: '1px solid #e94560', borderRadius: 8, marginBottom: 16, color: '#e94560' }}>
            {error}
          </div>
        )}

        {/* Stats cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 24 }}>
          <div style={{ background: '#16213e', borderRadius: 12, padding: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: '#8892b0', marginBottom: 8 }}>WIN RATE</div>
            {/* Circular gauge */}
            <svg width="100" height="100" viewBox="0 0 100 100" style={{ margin: '0 auto' }}>
              <circle cx="50" cy="50" r="42" fill="none" stroke="#3b3b4f" strokeWidth="8" />
              <circle
                cx="50" cy="50" r="42" fill="none"
                stroke={winRate > 0.6 ? '#2ecc71' : winRate > 0.3 ? '#ffd700' : '#e94560'}
                strokeWidth="8"
                strokeDasharray={`${winRatePct * 2.64} 264`}
                strokeLinecap="round"
                transform="rotate(-90 50 50)"
              />
              <text x="50" y="55" textAnchor="middle" fill="#e0e0e0" fontSize="22" fontWeight="700">
                {winRatePct}%
              </text>
            </svg>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, color: '#8892b0', marginBottom: 8 }}>TOTAL ATTEMPTS</div>
            <div style={{ fontSize: 36, fontWeight: 700 }}>{stats?.total_attempts ?? 0}</div>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, color: '#8892b0', marginBottom: 8 }}>FLOW SESSIONS</div>
            <div style={{ fontSize: 36, fontWeight: 700, color: '#e94560' }}>{stats?.flow_sessions ?? 0}</div>
            <div style={{ fontSize: 12, color: '#8892b0', marginTop: 4 }}>
              of {stats?.total_sessions ?? 0} total
            </div>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, color: '#8892b0', marginBottom: 8 }}>AVG DIFFICULTY</div>
            <div style={{ fontSize: 36, fontWeight: 700 }}>{stats?.avg_difficulty.toFixed(2) ?? '1.00'}x</div>
          </div>
        </div>

        {/* Difficulty/Accuracy chart */}
        <div style={{ background: '#16213e', borderRadius: 12, padding: 20, marginBottom: 24 }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Session Performance</div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3b3b4f" />
                <XAxis dataKey="name" stroke="#8892b0" fontSize={12} />
                <YAxis stroke="#8892b0" fontSize={12} />
                <Tooltip
                  contentStyle={{ background: '#1a1a2e', border: '1px solid #3b3b4f', borderRadius: 8 }}
                  labelStyle={{ color: '#e0e0e0' }}
                />
                <Line type="monotone" dataKey="difficulty" stroke="#e94560" strokeWidth={2} name="Difficulty" dot={{ fill: '#e94560' }} />
                <Line type="monotone" dataKey="accuracy" stroke="#2ecc71" strokeWidth={2} name="Accuracy %" dot={{ fill: '#2ecc71' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#8892b0' }}>
              No session data yet. Play a game first!
            </div>
          )}
        </div>

        {/* Recent sessions table */}
        <div style={{ background: '#16213e', borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Recent Sessions</div>
          {sessions.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #3b3b4f' }}>
                    <th style={{ padding: '8px 12px', textAlign: 'left', color: '#8892b0' }}>Session</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', color: '#8892b0' }}>Level</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', color: '#8892b0' }}>Attempts</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', color: '#8892b0' }}>Correct</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', color: '#8892b0' }}>Accuracy</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', color: '#8892b0' }}>Flow</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => (
                    <tr key={s.id} style={{ borderBottom: '1px solid #2b2d42' }}>
                      <td style={{ padding: '8px 12px' }}>#{s.id}</td>
                      <td style={{ padding: '8px 12px' }}>{s.level_at_start} → {s.level_at_end}</td>
                      <td style={{ padding: '8px 12px' }}>{s.total_attempts}</td>
                      <td style={{ padding: '8px 12px' }}>{s.correct_attempts}</td>
                      <td style={{ padding: '8px 12px' }}>
                        {s.total_attempts > 0 ? Math.round((s.correct_attempts / s.total_attempts) * 100) : 0}%
                      </td>
                      <td style={{ padding: '8px 12px' }}>
                        {s.is_flow_session ? <span style={{ color: '#e94560' }}>✦</span> : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#8892b0' }}>
              No sessions yet. Play a game first!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
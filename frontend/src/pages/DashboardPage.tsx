import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardApi } from '../api/client';
import type { PlayerStats, SessionSummary, PuzzleRecord, PredictionRecord, RotationRecord } from '../types';
import { PUZZLE_TYPE_COLORS } from '../types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<PlayerStats | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [puzzlesList, setPuzzlesList] = useState<PuzzleRecord[]>([]);
  const [predictions, setPredictions] = useState<PredictionRecord[]>([]);
  const [rotations, setRotations] = useState<RotationRecord[]>([]);
  const [activeTab, setActiveTab] = useState<'overview'|'puzzles'|'predictions'|'rotations'>('overview');
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [s, sess, p, pred, rot] = await Promise.all([
          dashboardApi.stats(),
          dashboardApi.sessions(20),
          dashboardApi.puzzles(20),
          dashboardApi.predictions(20),
          dashboardApi.rotations(20),
        ]);
        setStats(s);
        setSessions(sess);
        setPuzzlesList(p.puzzles);
        setPredictions(pred.predictions);
        setRotations(rot.rotations);
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
  const predAccuracy = stats?.prediction_accuracy ?? 0;

  // Chart data
  const chartData = sessions.slice().reverse().map((s) => ({
    name: `S${s.id}`,
    accuracy: s.total_puzzles > 0 ? Math.round((s.correct_puzzles / s.total_puzzles) * 100) : 0,
    attempts: s.total_puzzles,
    flow: s.is_flow_session,
  }));

  // Puzzle type breakdown
  const typeData = stats?.puzzle_type_breakdown?.map((t) => ({
    name: t.puzzle_type,
    count: t.count,
    accuracy: t.count > 0 ? Math.round((t.correct / t.count) * 100) : 0,
    fill: PUZZLE_TYPE_COLORS[t.puzzle_type] || '#666',
  })) || [];

  const username = localStorage.getItem('echo_username') || 'Player';

  const tabStyle = (tab: string) => ({
    padding: '8px 16px',
    background: activeTab === tab ? '#16213e' : 'transparent',
    border: activeTab === tab ? '1px solid #e94560' : '1px solid #3b3b4f',
    borderRadius: 6,
    color: activeTab === tab ? '#e94560' : '#8892b0',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: activeTab === tab ? 600 : 400,
  } as const);

  return (
    <div style={{ minHeight: '100vh', background: '#1a1a2e', padding: '20px', color: '#e0e0e0', fontFamily: "'Inter', sans-serif" }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <span style={{ fontSize: 24, fontWeight: 700, color: '#e94560' }}>Echo</span>
            <span style={{ fontSize: 14, color: '#8892b0', marginLeft: 12 }}>Dashboard — {username}</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => navigate('/game')} style={{ padding: '8px 16px', background: '#e94560', border: 'none', borderRadius: 6, color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>
              Play
            </button>
            <button onClick={handleLogout} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid #e94560', borderRadius: 6, color: '#e94560', cursor: 'pointer', fontSize: 13 }}>
              Logout
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: 12, background: 'rgba(233,69,96,0.1)', border: '1px solid #e94560', borderRadius: 8, marginBottom: 16, color: '#e94560', fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Stats cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 16 }}>
          {/* Win rate gauge */}
          <div style={{ background: '#16213e', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#8892b0', marginBottom: 8 }}>WIN RATE</div>
            <svg width="80" height="80" viewBox="0 0 100 100" style={{ margin: '0 auto' }}>
              <circle cx="50" cy="50" r="42" fill="none" stroke="#3b3b4f" strokeWidth="8" />
              <circle
                cx="50" cy="50" r="42" fill="none"
                stroke={winRate > 0.6 ? '#2ecc71' : winRate > 0.3 ? '#ffd700' : '#e94560'}
                strokeWidth="8"
                strokeDasharray={`${winRatePct * 2.64} 264`}
                strokeLinecap="round"
                transform="rotate(-90 50 50)"
              />
              <text x="50" y="55" textAnchor="middle" fill="#e0e0e0" fontSize="20" fontWeight="700">{winRatePct}%</text>
            </svg>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 11, color: '#8892b0', marginBottom: 4 }}>TOTAL PUZZLES</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>{stats?.total_puzzles ?? 0}</div>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 11, color: '#8892b0', marginBottom: 4 }}>CORRECT</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: '#2ecc71' }}>{stats?.correct_puzzles ?? 0}</div>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 11, color: '#8892b0', marginBottom: 4 }}>AVG DECISION</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{(stats?.avg_decision_ms ?? 0).toFixed(0)}ms</div>
            <div style={{ fontSize: 10, color: '#8892b0' }}>time to answer</div>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 11, color: '#8892b0', marginBottom: 4 }}>PREDICTION</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: predAccuracy > 0.6 ? '#2ecc71' : '#ffd700' }}>
              {(predAccuracy * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: 10, color: '#8892b0' }}>AI accuracy</div>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 11, color: '#8892b0', marginBottom: 4 }}>FLOW</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: '#e94560' }}>{stats?.flow_sessions ?? 0}</div>
            <div style={{ fontSize: 10, color: '#8892b0' }}>of {stats?.total_sessions ?? 0} sessions</div>
          </div>

          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 11, color: '#8892b0', marginBottom: 4 }}>ROTATIONS</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: '#b388ff' }}>{stats?.total_rotations ?? 0}</div>
            <div style={{ fontSize: 10, color: '#8892b0' }}>puzzle changes</div>
          </div>
        </div>

        {/* Tab navigation */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button onClick={() => setActiveTab('overview')} style={tabStyle('overview')}>Overview</button>
          <button onClick={() => setActiveTab('puzzles')} style={tabStyle('puzzles')}>Puzzles</button>
          <button onClick={() => setActiveTab('predictions')} style={tabStyle('predictions')}>Predictions</button>
          <button onClick={() => setActiveTab('rotations')} style={tabStyle('rotations')}>Rotations</button>
        </div>

        {/* Tab content */}
        {activeTab === 'overview' && (
          <>
            {/* Session performance chart */}
            <div style={{ background: '#16213e', borderRadius: 12, padding: 16, marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Session Performance</div>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#3b3b4f" />
                    <XAxis dataKey="name" stroke="#8892b0" fontSize={11} />
                    <YAxis stroke="#8892b0" fontSize={11} />
                    <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #3b3b4f', borderRadius: 8, fontSize: 12 }} />
                    <Line type="monotone" dataKey="accuracy" stroke="#2ecc71" strokeWidth={2} name="Accuracy %" dot={{ fill: '#2ecc71', r: 3 }} />
                    <Line type="monotone" dataKey="attempts" stroke="#e94560" strokeWidth={2} name="Puzzles" dot={{ fill: '#e94560', r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: 30, color: '#8892b0', fontSize: 13 }}>
                  No session data yet. Play a game first!
                </div>
              )}
            </div>

            {/* Puzzle type breakdown */}
            {typeData.length > 0 && (
              <div style={{ background: '#16213e', borderRadius: 12, padding: 16, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Puzzle Type Breakdown</div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={typeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#3b3b4f" />
                    <XAxis dataKey="name" stroke="#8892b0" fontSize={10} />
                    <YAxis stroke="#8892b0" fontSize={11} />
                    <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #3b3b4f', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="count" name="Count" radius={[4, 4, 0, 0]}>
                      {typeData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Recent sessions table */}
            <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Recent Sessions</div>
              {sessions.length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #3b3b4f' }}>
                        <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Session</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Puzzles</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Correct</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Accuracy</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Flow</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map((s) => (
                        <tr key={s.id} style={{ borderBottom: '1px solid #2b2d42' }}>
                          <td style={{ padding: '6px 10px' }}>#{s.id}</td>
                          <td style={{ padding: '6px 10px' }}>{s.total_puzzles}</td>
                          <td style={{ padding: '6px 10px' }}>{s.correct_puzzles}</td>
                          <td style={{ padding: '6px 10px' }}>
                            {s.total_puzzles > 0 ? Math.round((s.correct_puzzles / s.total_puzzles) * 100) : 0}%
                          </td>
                          <td style={{ padding: '6px 10px' }}>
                            {s.is_flow_session ? <span style={{ color: '#e94560', fontSize: 16 }}>✦</span> : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: 30, color: '#8892b0', fontSize: 13 }}>
                  No sessions yet. Play a game first!
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'puzzles' && (
          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Puzzle History</div>
            {puzzlesList.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #3b3b4f' }}>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Type</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Result</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Time</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Decision</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Attempt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {puzzlesList.map((p) => (
                      <tr key={p.id} style={{ borderBottom: '1px solid #2b2d42' }}>
                        <td style={{ padding: '6px 10px' }}>
                          <span style={{ color: PUZZLE_TYPE_COLORS[p.puzzle_type] || '#8892b0' }}>
                            {p.puzzle_type}
                          </span>
                        </td>
                        <td style={{ padding: '6px 10px', color: p.is_correct ? '#2ecc71' : '#e94560' }}>
                          {p.is_correct ? 'Correct' : 'Wrong'}
                        </td>
                        <td style={{ padding: '6px 10px' }}>{(p.time_visible_ms / 1000).toFixed(1)}s</td>
                        <td style={{ padding: '6px 10px' }}>{p.decision_time_ms?.toFixed(0)}ms</td>
                        <td style={{ padding: '6px 10px' }}>#{p.puzzle_attempt_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 30, color: '#8892b0', fontSize: 13 }}>
                No puzzles yet. Play a game first!
              </div>
            )}
          </div>
        )}

        {activeTab === 'predictions' && (
          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>AI Prediction Log</div>
            {predictions.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #3b3b4f' }}>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Puzzle</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Prediction</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Confidence</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Actual Result</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Reasoning</th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((p) => (
                      <tr key={p.id} style={{ borderBottom: '1px solid #2b2d42' }}>
                        <td style={{ padding: '6px 10px', fontSize: 10, color: '#8892b0' }}>
                          {p.puzzle_id.slice(0, 16)}...
                        </td>
                        <td style={{ padding: '6px 10px', color: p.predicted_fail ? '#e94560' : '#2ecc71' }}>
                          {p.predicted_fail ? 'Will Fail' : 'May Pass'}
                        </td>
                        <td style={{ padding: '6px 10px' }}>{(p.confidence * 100).toFixed(0)}%</td>
                        <td style={{ padding: '6px 10px', color: p.actually_failed === null ? '#8892b0' : p.actually_failed ? '#e94560' : '#2ecc71' }}>
                          {p.actually_failed === null ? '—' : p.actually_failed ? 'Failed' : 'Passed'}
                        </td>
                        <td style={{ padding: '6px 10px', fontSize: 10, color: '#8892b0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {p.reasoning}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 30, color: '#8892b0', fontSize: 13 }}>
                No predictions yet. The AI will start predicting after you fail a few puzzles.
              </div>
            )}
          </div>
        )}

        {activeTab === 'rotations' && (
          <div style={{ background: '#16213e', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Puzzle Rotation Log</div>
            {rotations.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #3b3b4f' }}>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Old Type</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Failures</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Prediction</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>New Type</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left', color: '#8892b0' }}>Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rotations.map((r) => (
                      <tr key={r.id} style={{ borderBottom: '1px solid #2b2d42' }}>
                        <td style={{ padding: '6px 10px', color: PUZZLE_TYPE_COLORS[r.old_puzzle_type] || '#8892b0' }}>
                          {r.old_puzzle_type}
                        </td>
                        <td style={{ padding: '6px 10px' }}>{r.failures_before_rotate}</td>
                        <td style={{ padding: '6px 10px', color: r.predicted_will_fail === 'True' ? '#e94560' : '#2ecc71', fontSize: 11 }}>
                          {r.predicted_will_fail === 'True' ? 'Fail predicted' :
                           r.predicted_will_fail === 'False' ? 'May pass' : 'Unknown'}
                        </td>
                        <td style={{ padding: '6px 10px', color: PUZZLE_TYPE_COLORS[r.new_puzzle_type] || '#8892b0' }}>
                          {r.new_puzzle_type}
                        </td>
                        <td style={{ padding: '6px 10px', fontSize: 10, color: '#8892b0', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {r.trend_json?.slice(0, 40)}...
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 30, color: '#8892b0', fontSize: 13 }}>
                No rotations yet. The system rotates puzzles after repeated failures.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
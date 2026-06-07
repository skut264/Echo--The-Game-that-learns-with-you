import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { gameApi } from '../api/client';
import type { GameStartResponse, AttemptResponse } from '../types';

const noteColors = ['#e94560', '#0f3460', '#533483', '#ffd700', '#2ecc71', '#3498db'];

interface SequenceNote {
  row: number;
  col: number;
  color: string;
}

function genSequence(len: number): SequenceNote[] {
  const notes: SequenceNote[] = [];
  for (let i = 0; i < len; i++) {
    notes.push({
      row: Math.floor(Math.random() * 3),
      col: Math.floor(Math.random() * 3),
      color: noteColors[Math.floor(Math.random() * noteColors.length)],
    });
  }
  return notes;
}

function playBeep(freq: number) {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.15);
  } catch (e) {}
}

const hexStyle: React.CSSProperties = {
  width: 80,
  height: 92,
  clipPath: 'polygon(50% 0%, 95% 25%, 95% 75%, 50% 100%, 5% 75%, 5% 25%)',
  cursor: 'pointer',
  transition: 'all 0.15s ease',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 10,
  color: '#fff',
};

export default function GamePage() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<'loading' | 'displaying' | 'input' | 'coaching'>('loading');
  const [sequence, setSequence] = useState<SequenceNote[]>([]);
  const [displayIdx, setDisplayIdx] = useState(-1);
  const [inputIdx, setInputIdx] = useState(0);
  const [level, setLevel] = useState(1);
  const [seqLen, setSeqLen] = useState(3);
  const [difficulty, setDifficulty] = useState(1.0);
  const [consecutiveWins, setConsecutiveWins] = useState(0);
  const [consecutiveLosses, setConsecutiveLosses] = useState(0);
  const [playerState, setPlayerState] = useState('stable');
  const [bgColor, setBgColor] = useState('#1a1a2e');
  const [coachingText, setCoachingText] = useState<string | null>(null);
  const [newRule, setNewRule] = useState<string | null>(null);
  const [flashCorrect, setFlashCorrect] = useState(false);
  const [flashWrong, setFlashWrong] = useState(false);
  const [timerPct, setTimerPct] = useState(100);
  const timerRef = useRef<number>(0);
  const [startInfo, setStartInfo] = useState<GameStartResponse | null>(null);
  void startInfo;

  // Start game
  useEffect(() => {
    (async () => {
      try {
        const res = await gameApi.start();
        setStartInfo(res);
        setLevel(res.level);
        setSeqLen(res.sequence_length);
        setDifficulty(res.difficulty);
        setBgColor(res.color_theme);
        const seq = genSequence(res.sequence_length);
        setSequence(seq);
        setPhase('displaying');
      } catch (e) {
        console.error('Start failed:', e);
      }
    })();
  }, []);

  // Display sequence
  useEffect(() => {
    if (phase !== 'displaying' || sequence.length === 0) return;
    let i = 0;
    const interval = setInterval(() => {
      if (i >= sequence.length) {
        clearInterval(interval);
        setDisplayIdx(-1);
        setTimeout(() => {
          setPhase('input');
          setInputIdx(0);
        }, 400);
        return;
      }
      setDisplayIdx(i);
      playBeep(440 + i * 80);
      i++;
    }, Math.max(300, 600 / difficulty));
    return () => clearInterval(interval);
  }, [phase, sequence, difficulty]);

  // Timer during input phase
  useEffect(() => {
    if (phase !== 'input') {
      setTimerPct(100);
      return;
    }
    const duration = Math.max(3000, seqLen * 1500 / difficulty);
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const pct = Math.max(0, 100 - (elapsed / duration) * 100);
      setTimerPct(pct);
      if (pct <= 0) {
        // Timeout = wrong
        handleAttempt(false, 'timing');
        return;
      }
      timerRef.current = requestAnimationFrame(tick);
    };
    timerRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(timerRef.current);
  }, [phase]);

  const handleAttempt = async (isCorrect: boolean, errorType?: string) => {
    try {
      const res = await gameApi.attempt({
        sequence_length: seqLen,
        is_correct: isCorrect,
        input_latency_ms: 0,
        error_type: errorType,
      });
      processResponse(res);
    } catch (e) {
      console.error('Attempt failed:', e);
    }
  };

  const processResponse = (res: AttemptResponse) => {
    setLevel(res.level);
    setDifficulty(res.difficulty);
    setConsecutiveWins(res.consecutive_wins);
    setConsecutiveLosses(res.consecutive_losses);
    setPlayerState(res.state);
    setBgColor(res.color_theme);
    setCoachingText(res.coaching.text || null);

    if (res.new_rule) {
      setNewRule(res.new_rule);
      setTimeout(() => setNewRule(null), 3000);
    }

    if (res.sequence_length !== seqLen) {
      setSeqLen(res.sequence_length);
    }

    // Start next round
    setTimeout(() => {
      const newSeq = genSequence(res.sequence_length);
      setSequence(newSeq);
      setInputIdx(0);
      setCoachingText(null);
      setFlashCorrect(false);
      setFlashWrong(false);
      setPhase('displaying');
    }, 800);
  };

  const handleTileClick = (row: number, col: number) => {
    if (phase !== 'input' || inputIdx >= sequence.length) return;

    const expected = sequence[inputIdx];
    if (row === expected.row && col === expected.col) {
      playBeep(523 + inputIdx * 80);
      if (inputIdx === sequence.length - 1) {
        // Complete!
        setFlashCorrect(true);
        setPhase('coaching');
        handleAttempt(true);
      } else {
        setInputIdx((i) => i + 1);
      }
    } else {
      // Wrong
      playBeep(200);
      setFlashWrong(true);
      setPhase('coaching');
      handleAttempt(false, 'position');
    }
  };

  const handleEndGame = async () => {
    try {
      localStorage.removeItem('echo_token');
      localStorage.removeItem('echo_username');
      navigate('/login');
    } catch (e) {}
  };

  const renderTile = (row: number, col: number) => {
    const isDisplayNote = displayIdx >= 0 && sequence[displayIdx]?.row === row && sequence[displayIdx]?.col === col;
    const isInputNote = inputIdx < sequence.length && sequence[inputIdx]?.row === row && sequence[inputIdx]?.col === col;

    let tileBg = '#16213e';
    if (isDisplayNote) {
      tileBg = sequence[displayIdx]?.color || '#e94560';
    }
    if (flashCorrect && isInputNote) {
      tileBg = '#2ecc71';
    }
    if (flashWrong && isInputNote) {
      tileBg = '#e94560';
    }

    const isHighlighted = isDisplayNote || (flashCorrect && isInputNote) || (flashWrong && isInputNote);

    return (
      <div
        key={`${row}-${col}`}
        onClick={() => handleTileClick(row, col)}
        style={{
          ...hexStyle,
          background: tileBg,
          boxShadow: isHighlighted
            ? `0 0 ${flashCorrect ? '20px' : '15px'} ${tileBg}`
            : 'none',
          transform: isHighlighted ? 'scale(1.1)' : 'scale(1)',
          opacity: phase === 'input' ? 1 : isHighlighted ? 1 : 0.6,
        }}
      />
    );
  };

  const username = localStorage.getItem('echo_username') || 'Player';

  return (
    <div
      style={{
        minHeight: '100vh',
        background: bgColor,
        transition: 'background 0.5s ease',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '20px',
        color: '#e0e0e0',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Top bar */}
      <div style={{ width: '100%', maxWidth: '600px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#e94560' }}>Echo</span>
          <span style={{ fontSize: 12, color: '#8892b0', marginLeft: 8 }}>{username}</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => navigate('/dashboard')} style={{ padding: '6px 14px', background: '#16213e', border: '1px solid #3b3b4f', borderRadius: 6, color: '#e0e0e0', fontSize: 13, cursor: 'pointer' }}>
            Dashboard
          </button>
          <button onClick={handleEndGame} style={{ padding: '6px 14px', background: 'transparent', border: '1px solid #e94560', borderRadius: 6, color: '#e94560', fontSize: 13, cursor: 'pointer' }}>
            Logout
          </button>
        </div>
      </div>

      {/* New rule reveal */}
      {newRule && (
        <div style={{
          position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          background: 'rgba(255,215,0,0.1)', border: '2px solid #ffd700',
          borderRadius: 16, padding: '24px 40px', textAlign: 'center', zIndex: 100,
          backdropFilter: 'blur(8px)', animation: 'fadeIn 0.5s ease',
        }}>
          <div style={{ color: '#ffd700', fontSize: 14, marginBottom: 4 }}>NEW RULE UNLOCKED</div>
          <div style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>{newRule}</div>
        </div>
      )}

      {/* HUD */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: '#8892b0' }}>LEVEL</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{level}</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: '#8892b0' }}>DIFFICULTY</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{difficulty.toFixed(2)}x</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: '#8892b0' }}>STREAK</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: consecutiveWins >= 3 ? '#ffd700' : '#e94560' }}>
            {consecutiveWins > 0 ? `🔥${consecutiveWins}` : consecutiveLosses > 0 ? `💀${consecutiveLosses}` : '—'}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: '#8892b0' }}>STATE</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: playerState === 'struggle' ? '#8892b0' : playerState === 'skill_gap' ? '#a0a0b0' : '#2ecc71' }}>
            {playerState}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: '#8892b0' }}>SEQUENCE</div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{seqLen} notes</div>
        </div>
      </div>

      {/* Phase indicator */}
      <div style={{ fontSize: 13, color: '#8892b0', marginBottom: 20, letterSpacing: 1 }}>
        {phase === 'displaying' ? 'WATCH THE SEQUENCE' : phase === 'input' ? 'YOUR TURN' : phase === 'coaching' ? '—' : 'LOADING'}
      </div>

      {/* Timer bar */}
      {phase === 'input' && (
        <div style={{ width: '300px', height: 4, background: '#3b3b4f', borderRadius: 2, marginBottom: 20 }}>
          <div
            className="timer-bar"
            style={{
              width: `${timerPct}%`,
              height: '100%',
              background: timerPct > 50 ? '#2ecc71' : timerPct > 25 ? '#ffd700' : '#e94560',
              borderRadius: 2,
              transition: 'width 0.05s linear',
            }}
          />
        </div>
      )}

      {/* Hexagonal grid */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0 }}>
        {[0, 1, 2].map((row) => (
          <div
            key={row}
            style={{
              display: 'flex',
              gap: 8,
              marginLeft: row % 2 === 1 ? 44 : 0,
              marginBottom: -24,
            }}
          >
            {[0, 1, 2].map((col) => renderTile(row, col))}
          </div>
        ))}
      </div>

      {/* Coaching text */}
      {coachingText && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: 32,
            padding: '14px 24px',
            background: 'rgba(232,213,183,0.1)',
            border: '1px solid #e8d5b7',
            borderRadius: 12,
            color: '#e8d5b7',
            fontSize: 15,
            textAlign: 'center',
            maxWidth: 400,
          }}
        >
          {coachingText}
        </div>
      )}
    </div>
  );
}
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { gameApi } from '../api/client';
import type { PuzzleData, FibonacciData, DashboardSnapshot, PuzzleOption } from '../types';
import { PUZZLE_TYPE_COLORS } from '../types';

const PHI = 1.618033988749895;

// ── Canvas rendering helpers ──

function drawFibonacciSpiral(
  ctx: CanvasRenderingContext2D,
  fib: FibonacciData,
  time: number,
  _canvasW: number,
  _canvasH: number
) {
  // Draw golden rectangles with rotation animation
  fib.rects.forEach((r) => {
    ctx.save();
    ctx.translate(r.x, r.y);
    ctx.rotate((r.rotation_deg * Math.PI) / 180 + time * 0.0001);
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.strokeRect(-r.w / 2, -r.h / 2, r.w, r.h);
    ctx.restore();
  });

  // Draw spiral points with gentle pulse
  fib.points.forEach((p, i) => {
    const pulse = Math.sin(time * 0.002 + i * 0.5) * 0.3 + 0.7;
    const opacity = p.opacity * pulse;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.radius * 0.08, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(0, 212, 255, ${opacity * 0.5})`;
    ctx.fill();
    ctx.strokeStyle = `rgba(0, 212, 255, ${opacity * 0.3})`;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Fibonacci number label
    ctx.fillStyle = `rgba(0, 212, 255, ${opacity * 0.4})`;
    ctx.font = '10px monospace';
    ctx.fillText(`φ${p.fib_n}`, p.x + 8, p.y - 4);
  });
}

function drawGoldenAngleGrid(ctx: CanvasRenderingContext2D, canvasW: number, canvasH: number, time: number) {
  const count = 12;
  const goldenAngle = 137.508;
  const maxR = Math.min(canvasW, canvasH) * 0.35;
  const cx = canvasW / 2;
  const cy = canvasH / 2 + 20;

  for (let i = 1; i <= count; i++) {
    const angle = (goldenAngle * i) % 360;
    const rad = (angle * Math.PI) / 180 + time * 0.0003;
    const r = (i / count) * maxR;
    const x = cx + Math.cos(rad) * r;
    const y = cy + Math.sin(rad) * r;

    ctx.beginPath();
    ctx.arc(x, y, 3 + Math.sin(time * 0.003 + i) * 1.5, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(46, 204, 113, ${0.15 + (i / count) * 0.2})`;
    ctx.fill();
  }
}

// ── Component ──

export default function GamePage() {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [puzzle, setPuzzle] = useState<PuzzleData | null>(null);
  const [dashboard, setDashboard] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [puzzleAction, setPuzzleAction] = useState<string>('');
  const [coaching, setCoaching] = useState<string | null>(null);
  const [hintTimer, setHintTimer] = useState<number>(0);

  // Puzzle attempt tracking
  const attemptCountRef = useRef(0);
  const puzzleShowTimeRef = useRef(0);
  const puzzleStartTimeRef = useRef(0);
  const hoveredOptionsRef = useRef<string[]>([]);
  const hoverDurationsRef = useRef<number[]>([]);
  const hoverStartRef = useRef<Record<string, number>>({});
  const animFrameRef = useRef<number>(0);

  const [puzzleAttemptCount, setPuzzleAttemptCount] = useState(1);
  const [isAnswered, setIsAnswered] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [result, setResult] = useState<'correct'|'wrong'|null>(null);
  const [timeLeft, setTimeLeft] = useState(100);
  const [showPrediction, setShowPrediction] = useState<any>(null);

  // Helper to get auth state
  const username = localStorage.getItem('echo_username') || 'Player';
  const token = localStorage.getItem('echo_token');

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    startNewGame();
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  // Canvas animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let running = true;
    const startTime = Date.now();

    const draw = () => {
      if (!running) return;
      const time = Date.now() - startTime;
      const w = canvas.width;
      const h = canvas.height;

      ctx.clearRect(0, 0, w, h);

      // Dark background
      ctx.fillStyle = '#1a1a2e';
      ctx.fillRect(0, 0, w, h);

      // Animated golden angle grid (always on)
      drawGoldenAngleGrid(ctx, w, h, time);

      // Fibonacci decorations if available
      if (puzzle?.fibonacci_data) {
        drawFibonacciSpiral(ctx, puzzle.fibonacci_data, time, w, h);
      }

      // Draw canvas layout areas (subtle guides)
      const layout = puzzle?.canvas_layout;
      if (layout) {
        // Puzzle area
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.lineWidth = 1;
        ctx.strokeRect(layout.puzzle_area.x, layout.puzzle_area.y, layout.puzzle_area.w, layout.puzzle_area.h);

        // Hint area
        if (coaching) {
          ctx.fillStyle = 'rgba(255, 215, 0, 0.08)';
          ctx.fillRect(layout.hint_area.x, layout.hint_area.y, layout.hint_area.w, layout.hint_area.h);
        }
      }

      animFrameRef.current = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      running = false;
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [puzzle, coaching]);

  // Timer countdown
  useEffect(() => {
    if (!puzzle || isAnswered) return;
    puzzleShowTimeRef.current = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - puzzleShowTimeRef.current;
      const pct = Math.max(0, 100 - (elapsed / puzzle.time_limit_ms) * 100);
      setTimeLeft(pct);
      if (pct <= 0) {
        // Time's up — auto-fail
        handleOptionSelect(null);
        clearInterval(interval);
      }
    }, 100);
    return () => clearInterval(interval);
  }, [puzzle, isAnswered]);

  // Hint timer — show hint after 5s of no answer
  useEffect(() => {
    if (!puzzle || isAnswered) return;
    const t = setTimeout(() => setHintTimer(1), 5000);
    return () => clearTimeout(t);
  }, [puzzle, isAnswered]);

  async function startNewGame() {
    setLoading(true);
    setPuzzleAction('');
    setCoaching(null);
    setHintTimer(0);
    attemptCountRef.current = 0;
    setPuzzleAttemptCount(1);
    setIsAnswered(false);
    setSelectedOption(null);
    setResult(null);
    setShowPrediction(null);
    setTimeLeft(100);

    try {
      const data = await gameApi.start();
      setPuzzle(data.puzzle ?? null);
      setDashboard(data.dashboard ?? null);
      setPuzzleAction('New Challenge');
    } catch (e: any) {
      if (e.message?.includes('401')) navigate('/login');
      setPuzzleAction('Error starting game');
    } finally {
      setLoading(false);
    }
  }

  async function handleOptionSelect(optionText: string | null) {
    if (isAnswered) return;
    setIsAnswered(true);
    setSelectedOption(optionText);

    const timeVisible = Date.now() - (puzzleShowTimeRef.current || Date.now());
    const decisionTime = Date.now() - (puzzleStartTimeRef.current || puzzleShowTimeRef.current);

    // Determine if correct
    let isCorrect = false;
    if (optionText && puzzle?.options) {
      const correctOption = puzzle.options.find((o: PuzzleOption) => o.weight >= 90);
      if (correctOption && optionText === correctOption.text) isCorrect = true;
    }

    setResult(isCorrect ? 'correct' : 'wrong');

    try {
      const resp = await gameApi.attempt({
        puzzle_id: puzzle?.puzzle_id || '',
        puzzle_type: puzzle?.puzzle_type || '',
        prompt: puzzle?.prompt,
        correct_answer: puzzle?.options?.find((o: PuzzleOption) => o.weight >= 90)?.text,
        is_correct: isCorrect,
        decision_time_ms: decisionTime,
        time_visible_ms: timeVisible,
        option_selected: optionText ? optionText : undefined,
        hovered_options: hoveredOptionsRef.current,
        hover_durations_ms: hoverDurationsRef.current,
        puzzle_attempt_count: puzzleAttemptCount,
      });

      setDashboard(resp.dashboard);

      if (resp.coaching?.hint) {
        setCoaching(resp.coaching.hint);
      }

      // Handle prediction display
      if (resp.prediction) {
        setShowPrediction({
          willFail: resp.predicted_will_fail,
          confidence: resp.prediction.confidence,
          reasoning: resp.prediction.reasoning,
        });
      }

      // Handle new puzzle
      if (resp.new_puzzle) {
        setPuzzle(resp.new_puzzle);
        setPuzzleAttemptCount(1);
        setIsAnswered(false);
        setSelectedOption(null);
        setResult(null);
        setCoaching(null);
        setHintTimer(0);
        setTimeLeft(100);
        hoveredOptionsRef.current = [];
        hoverDurationsRef.current = [];

        if (resp.puzzle_action === 'rotate') {
          setPuzzleAction('Puzzle rotated — too many failures');
        } else if (resp.should_regenerate) {
          setPuzzleAction('AI predicted you\'d fail — new puzzle generated');
        } else {
          setPuzzleAction('Correct! Next challenge');
        }
      } else {
        // Stay on same puzzle, increment attempt count
        setPuzzleAttemptCount((c) => c + 1);
        if (!isCorrect) {
          // Brief delay then allow retry
          setTimeout(() => {
            setIsAnswered(false);
            setSelectedOption(null);
            setResult(null);
            setTimeLeft(100);
            setCoaching(null);
          }, isCorrect ? 1500 : 2000);
        } else {
          // Correct but no new puzzle — should generate
          setTimeout(() => {
            setIsAnswered(false);
            setSelectedOption(null);
            setResult(null);
            setTimeLeft(100);
            setCoaching(null);
          }, 1500);
        }
      }
    } catch (e: any) {
      setPuzzleAction(`Error: ${e.message}`);
    }
  }

  function handleHoverStart(optionText: string) {
    hoverStartRef.current[optionText] = Date.now();
  }

  function handleHoverEnd(optionText: string) {
    const start = hoverStartRef.current[optionText];
    if (start) {
      const duration = Date.now() - start;
      hoveredOptionsRef.current.push(optionText);
      hoverDurationsRef.current.push(duration);
      delete hoverStartRef.current[optionText];
    }
  }

  // ── Render ──

  return (
    <div style={{ minHeight: '100vh', background: '#1a1a2e', color: '#e0e0e0', fontFamily: "'Inter', sans-serif", display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Top bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px', background: '#16213e', borderBottom: '1px solid #3b3b4f', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#e94560' }}>Echo</span>
          <span style={{ fontSize: 12, color: '#8892b0' }}>{username}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {dashboard && (
            <span style={{ fontSize: 12, color: '#8892b0' }}>
              Streak: <strong style={{ color: dashboard.streak >= 5 ? '#e94560' : '#2ecc71' }}>{dashboard.streak}</strong>
              {' | '}Rate: <strong>{(dashboard.win_rate * 100).toFixed(0)}%</strong>
            </span>
          )}
          <button onClick={() => { gameApi.end(); navigate('/dashboard'); }} style={{ padding: '6px 12px', background: 'transparent', border: '1px solid #3b3b4f', borderRadius: 6, color: '#8892b0', fontSize: 12, cursor: 'pointer' }}>
            End
          </button>
        </div>
      </div>

      {/* Main canvas area */}
      <div style={{ position: 'relative', flex: 1 }}>
        <canvas ref={canvasRef} width={800} height={600} style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} />

        {/* Puzzle overlay — positioned using golden ratio */}
        {puzzle && !loading && (
          <div style={{
            position: 'absolute',
            top: puzzle.canvas_layout?.puzzle_area?.y || 50,
            left: puzzle.canvas_layout?.puzzle_area?.x || 50,
            width: puzzle.canvas_layout?.puzzle_area?.w || 700,
            height: puzzle.canvas_layout?.puzzle_area?.h || 400,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'flex-start',
            padding: '20px 30px',
            pointerEvents: 'auto',
          }}>
            {/* Puzzle type badge */}
            <div style={{
              marginBottom: 12,
              padding: '4px 12px',
              background: (PUZZLE_TYPE_COLORS[puzzle.puzzle_type] || '#666') + '22',
              border: `1px solid ${PUZZLE_TYPE_COLORS[puzzle.puzzle_type] || '#666'}`,
              borderRadius: 12,
              color: PUZZLE_TYPE_COLORS[puzzle.puzzle_type] || '#666',
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: 1,
              textTransform: 'uppercase',
            }}>
              {puzzle.puzzle_type === 'psychology_question' ? 'Mind Game' :
               puzzle.puzzle_type === 'pattern_recognition' ? 'Pattern' :
               puzzle.puzzle_type === 'spatial_logic' ? 'Spatial' :
               puzzle.puzzle_type === 'sequence_memory' ? 'Memory' :
               puzzle.puzzle_type === 'timing_challenge' ? 'Timing' : puzzle.puzzle_type}
            </div>

            {/* Prompt */}
            <div style={{
              fontSize: puzzle.prompt.length > 120 ? 14 : 16,
              fontWeight: 400,
              textAlign: 'center',
              lineHeight: 1.5,
              color: '#e0e0e0',
              marginBottom: 20,
              maxWidth: '90%',
              minHeight: 40,
            }}>
              {puzzle.prompt}
            </div>

            {/* Timer bar */}
            <div style={{ width: '80%', height: 4, background: '#3b3b4f', borderRadius: 2, marginBottom: 16 }}>
              <div style={{
                width: `${timeLeft}%`,
                height: 4,
                background: timeLeft > 50 ? '#2ecc71' : timeLeft > 25 ? '#ffd700' : '#e94560',
                borderRadius: 2,
                transition: 'width 0.1s linear',
              }} />
            </div>

            {/* Options — distributed using golden ratio positions */}
            {puzzle.options && puzzle.options.length > 0 && (
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 12,
                justifyContent: 'center',
                width: '100%',
                marginTop: 8,
              }}>
                {puzzle.options.map((opt, i) => {
                  const isSelected = selectedOption === opt.text;
                  const opacity = isAnswered ? (isSelected ? 1 : 0.5) : 1;

                  // Weighted psychology question styling
                  const isHighWeight = opt.weight >= 70;
                  const isMidWeight = opt.weight >= 30 && opt.weight < 70;

                  return (
                    <button
                      key={i}
                      disabled={isAnswered}
                      onMouseEnter={() => handleHoverStart(opt.text)}
                      onMouseLeave={() => handleHoverEnd(opt.text)}
                      onClick={() => !isAnswered && handleOptionSelect(opt.text)}
                      style={{
                        flex: puzzle.puzzle_type === 'psychology_question' ? '0 1 48%' : '0 1 30%',
                        minWidth: puzzle.puzzle_type === 'psychology_question' ? 200 : 150,
                        maxWidth: '80%',
                        padding: '14px 20px',
                        background: isAnswered
                          ? (isSelected && result === 'correct' ? 'rgba(46, 204, 113, 0.2)' :
                             isSelected && result === 'wrong' ? 'rgba(233, 69, 96, 0.2)' :
                             'rgba(22, 33, 62, 0.8)')
                          : (isHighWeight ? 'rgba(0, 212, 255, 0.08)' :
                             isMidWeight ? 'rgba(22, 33, 62, 0.8)' :
                             'rgba(22, 33, 62, 0.6)'),
                        border: `1px solid ${
                          isAnswered && isSelected && result === 'correct' ? '#2ecc71' :
                          isAnswered && isSelected && result === 'wrong' ? '#e94560' :
                          isHighWeight ? 'rgba(0, 212, 255, 0.3)' :
                          puzzle.puzzle_type === 'psychology_question' ? `rgba(179, 136, 255, ${opacity * 0.4})` :
                          'rgba(59, 59, 79, 0.5)'
                        }`,
                        borderRadius: 8,
                        color: isAnswered && isSelected && result === 'correct' ? '#2ecc71' :
                               isAnswered && isSelected && result === 'wrong' ? '#e94560' :
                               '#e0e0e0',
                        fontSize: 13,
                        cursor: isAnswered ? 'default' : 'pointer',
                        transition: 'all 0.2s',
                        textAlign: 'left',
                        lineHeight: 1.4,
                        opacity: opacity,
                        position: 'relative',
                      }}
                    >
                      {/* Weight indicator for psychology questions */}
                      {puzzle.puzzle_type === 'psychology_question' && (
                        <span style={{
                          position: 'absolute',
                          top: 4,
                          right: 8,
                          fontSize: 10,
                          color: isHighWeight ? 'rgba(0, 212, 255, 0.5)' :
                                 isMidWeight ? 'rgba(179, 136, 255, 0.4)' :
                                 'rgba(233, 69, 96, 0.4)',
                        }}>
                          {opt.weight}%
                        </span>
                      )}
                      {opt.text}
                    </button>
                  );
                })}
              </div>
            )}

            {/* No options — free form answer */}
            {(!puzzle.options || puzzle.options.length === 0) && (
              <div style={{ marginTop: 20, color: '#8892b0', fontSize: 14 }}>
                Think carefully and select your answer below
              </div>
            )}

            {/* Puzzle action announcement */}
            {puzzleAction && (
              <div style={{
                marginTop: 16,
                padding: '6px 16px',
                background: puzzleAction.includes('Correct') ? 'rgba(46, 204, 113, 0.15)' :
                           puzzleAction.includes('rotate') || puzzleAction.includes('predicted') ?
                           'rgba(179, 136, 255, 0.15)' : 'rgba(233, 69, 96, 0.1)',
                border: `1px solid ${
                  puzzleAction.includes('Correct') ? '#2ecc71' :
                  puzzleAction.includes('rotate') || puzzleAction.includes('predicted') ? '#b388ff' :
                  '#e94560'
                }`,
                borderRadius: 6,
                color: puzzleAction.includes('Correct') ? '#2ecc71' :
                       puzzleAction.includes('rotate') || puzzleAction.includes('predicted') ? '#b388ff' :
                       '#e94560',
                fontSize: 12,
                textAlign: 'center',
                maxWidth: '90%',
              }}>
                {puzzleAction}
              </div>
            )}

            {/* Prediction display */}
            {showPrediction && (
              <div style={{
                marginTop: 8,
                padding: '6px 12px',
                background: showPrediction.willFail ? 'rgba(233, 69, 96, 0.1)' : 'rgba(46, 204, 113, 0.1)',
                border: `1px solid ${showPrediction.willFail ? '#e94560' : '#2ecc71'}`,
                borderRadius: 6,
                fontSize: 11,
                color: showPrediction.willFail ? '#e94560' : '#2ecc71',
                textAlign: 'center',
                maxWidth: '90%',
              }}>
                AI Prediction: {showPrediction.willFail ? 'Will fail again' : 'May improve'} ({(showPrediction.confidence * 100).toFixed(0)}% confidence)
                <br />
                <span style={{ fontSize: 10, color: '#8892b0' }}>{showPrediction.reasoning}</span>
              </div>
            )}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 18, color: '#e94560', marginBottom: 8 }}>Generating challenge...</div>
            <div style={{ fontSize: 12, color: '#8892b0' }}>Using LLM for unique puzzle creation</div>
          </div>
        )}

        {/* Coaching hint — positioned in hint area */}
        {(coaching || hintTimer > 0) && (
          <div style={{
            position: 'absolute',
            top: puzzle?.canvas_layout?.hint_area?.y || 480,
            left: puzzle?.canvas_layout?.hint_area?.x || 50,
            width: puzzle?.canvas_layout?.hint_area?.w || 700,
            padding: '10px 20px',
            background: 'rgba(255, 215, 0, 0.08)',
            borderTop: '1px solid rgba(255, 215, 0, 0.2)',
            fontSize: 13,
            color: '#ffd700',
            textAlign: 'center',
            pointerEvents: 'auto',
            animation: 'fadeIn 0.3s ease',
            zIndex: 5,
          }}>
            {coaching || (hintTimer > 0 && !isAnswered ? 'Take your time. Look for the hidden pattern.' : '')}
          </div>
        )}

        {/* Fibonacci sequence indicators floating */}
        {puzzle && !loading && (
          <div style={{
            position: 'absolute',
            bottom: 10,
            right: 16,
            fontSize: 10,
            color: 'rgba(0, 212, 255, 0.3)',
            fontFamily: 'monospace',
          }}>
            φ = {PHI.toFixed(6)}
          </div>
        )}
      </div>
    </div>
  );
}
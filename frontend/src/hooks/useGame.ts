import { useState, useCallback } from 'react';
import { gameApi } from '../api/client';
import type { AttemptResponse } from '../types';

type GamePhase = 'idle' | 'started' | 'displaying' | 'input' | 'coaching' | 'finished';

interface SequenceNote {
  row: number;
  col: number;
  color: string;
  index: number;
}

const NOTE_COLORS = ['#e94560', '#0f3460', '#533483', '#ffd700', '#2ecc71', '#3498db'];

export function useGame() {
  const [phase, setPhase] = useState<GamePhase>('idle');
  const [sequence, setSequence] = useState<SequenceNote[]>([]);
  const [playerInput, setPlayerInput] = useState<number>(0);
  const [displayIndex, setDisplayIndex] = useState(-1);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [level, setLevel] = useState(1);
  const [difficulty, setDifficulty] = useState(1.0);
  const [consecutiveWins, setConsecutiveWins] = useState(0);
  const [state, setState] = useState('stable');
  const [colorTheme, setColorTheme] = useState('#1a1a2e');
  const [coachingText, setCoachingText] = useState<string | null>(null);
  const [newRule, setNewRule] = useState<string | null>(null);
  const [lastAttemptResponse, setLastAttemptResponse] = useState<AttemptResponse | null>(null);
  const [lastCorrect, setLastCorrect] = useState<boolean | null>(null);
  const [showWinStreak, setShowWinStreak] = useState(false);

  const generateSequence = useCallback((length: number) => {
    const notes: SequenceNote[] = [];
    for (let i = 0; i < length; i++) {
      notes.push({
        row: Math.floor(Math.random() * 3),
        col: Math.floor(Math.random() * 3),
        color: NOTE_COLORS[Math.floor(Math.random() * NOTE_COLORS.length)],
        index: i,
      });
    }
    return notes;
  }, []);

  const startGame = useCallback(async () => {
    try {
      const res = await gameApi.start();
      setSessionId(res.session_id);
      setLevel(res.level);
      setDifficulty(res.difficulty);
      setColorTheme(res.color_theme);
      setState('stable');
      setConsecutiveWins(0);
      setCoachingText(null);
      setNewRule(null);
      setLastCorrect(null);
      setShowWinStreak(false);

      const seq = generateSequence(res.sequence_length);
      setSequence(seq);
      setPlayerInput(0);
      setPhase('displaying');
      return res;
    } catch (e) {
      console.error('Failed to start game:', e);
      throw e;
    }
  }, [generateSequence]);

  const displaySequence = useCallback(async () => {
    // Animate through each note
    const seq = sequence;
    for (let i = 0; i < seq.length; i++) {
      setDisplayIndex(i);
      await new Promise((r) => setTimeout(r, 600 / difficulty));
    }
    setDisplayIndex(-1);
    await new Promise((r) => setTimeout(r, 300));
    setPhase('input');
  }, [sequence, difficulty]);

  const playNote = async (row: number, col: number) => {
    if (phase !== 'input') return;

    const currentNote = sequence[playerInput];
    const isCorrect = currentNote.row === row && currentNote.col === col;
    const timePerNote = 0; // Could track this properly

    if (!isCorrect) {
      setLastCorrect(false);

      // Determine error type
      let errorType = 'position';
      if (playerInput > 0 && playerInput < sequence.length - 1) {
        errorType = 'timing';
      }

      try {
        const res = await gameApi.attempt({
          sequence_length: sequence.length,
          is_correct: false,
          time_per_note_ms: timePerNote,
          error_type: errorType,
        });

        setLevel(res.level);
        setDifficulty(res.difficulty);
        setConsecutiveWins(0);
        setColorTheme(res.color_theme);
        setState(res.state);
        setLastAttemptResponse(res);
        setCoachingText(res.coaching.text || null);

        if (res.new_rule) {
          setNewRule(res.new_rule);
        }

        // Show the correct note briefly
        setDisplayIndex(playerInput);
        await new Promise((r) => setTimeout(r, 800));
        setDisplayIndex(-1);
        setCoachingText(null);
        setLastCorrect(null);

        // Restart display with possible new sequence length
        if (res.sequence_length !== sequence.length) {
          const newSeq = generateSequence(res.sequence_length);
          setSequence(newSeq);
        }
        setPlayerInput(0);
        setPhase('displaying');
      } catch (e) {
        console.error('Failed to send attempt:', e);
      }
      return;
    }

    // Correct so far
    if (playerInput === sequence.length - 1) {
      // Completed the sequence!
      setLastCorrect(true);

      try {
        const res = await gameApi.attempt({
          sequence_length: sequence.length,
          is_correct: true,
          time_per_note_ms: timePerNote,
        });

        setLevel(res.level);
        setDifficulty(res.difficulty);
        setConsecutiveWins(res.consecutive_wins);
        setColorTheme(res.color_theme);
        setState(res.state);
        setLastAttemptResponse(res);

        if (res.coaching.text) {
          setCoachingText(res.coaching.text);
        }
        if (res.new_rule) {
          setNewRule(res.new_rule);
        }

        if (res.consecutive_wins >= 3) {
          setShowWinStreak(true);
          setTimeout(() => setShowWinStreak(false), 1500);
        }

        // Generate next sequence
        await new Promise((r) => setTimeout(r, 500));
        setLastCorrect(null);
        setCoachingText(null);
        setNewRule(null);

        const newSeq = generateSequence(res.sequence_length);
        setSequence(newSeq);
        setPlayerInput(0);
        setPhase('displaying');
      } catch (e) {
        console.error('Failed to send attempt:', e);
      }
    } else {
      setPlayerInput((p) => p + 1);
    }
  };

  const endGame = async () => {
    try {
      const res = await gameApi.end();
      setPhase('finished');
      return res;
    } catch (e) {
      console.error('Failed to end game:', e);
    }
  };

  return {
    phase,
    sequence,
    playerInput,
    displayIndex,
    sessionId,
    level,
    difficulty,
    consecutiveWins,
    state,
    colorTheme,
    coachingText,
    newRule,
    lastCorrect,
    lastAttemptResponse,
    showWinStreak,
    startGame,
    displaySequence,
    playNote,
    endGame,
    setPhase,
  };
}
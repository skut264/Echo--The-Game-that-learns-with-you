import { useState, useCallback, useRef } from 'react';
import { gameApi, puzzleApi, metricsApi } from '../api/client';
import type { PuzzleData } from '../types';

export type GamePhase =
  | 'loading'
  | 'generating'
  | 'displaying'
  | 'input'
  | 'coaching'
  | 'psych_question'
  | 'finished';

export interface GameState {
  phase: GamePhase;
  puzzleType: string | null;
  puzzleData: PuzzleData | null;
  sessionId: number | null;
  level: number;
  difficulty: number;
  failCount: number;
  totalFails: number;
  coachingText: string | null;
  bgColor: string;
  playerState: string;
  attemptCount: number;
  psychCorrect: number;
  psychTotal: number;
  lastAttemptStart: number;
}

export function useGame() {
  const [state, setState] = useState<GameState>({
    phase: 'loading',
    puzzleType: null,
    puzzleData: null,
    sessionId: null,
    level: 1,
    difficulty: 1.0,
    failCount: 0,
    totalFails: 0,
    coachingText: null,
    bgColor: '#1a1a2e',
    playerState: 'stable',
    attemptCount: 0,
    psychCorrect: 0,
    psychTotal: 0,
    lastAttemptStart: 0,
  });

  const stateRef = useRef(state);
  stateRef.current = state;

  const update = useCallback((patch: Partial<GameState>) => {
    setState((s) => ({ ...s, ...patch }));
  }, []);

  const recordMetricSnapshot = useCallback(async () => {
    const s = stateRef.current;
    try {
      await metricsApi.snapshot({
        avg_time_per_note_ms: 0,
        puzzle_type: s.puzzleType || undefined,
      });
    } catch (_) {}
  }, []);

  const generateNextPuzzle = useCallback(async () => {
    update({ phase: 'generating', coachingText: null });
    try {
      const s = stateRef.current;
      const res = await puzzleApi.generate(s.puzzleType || undefined);
      update({
        puzzleType: res.puzzle_type,
        puzzleData: res.puzzle_data,
        phase: res.puzzle_type === 'psychology_question' ? 'psych_question' : 'displaying',
        lastAttemptStart: Date.now(),
      });
    } catch (e) {
      console.error('Generate puzzle failed:', e);
    }
  }, [update]);

  const startGame = useCallback(async () => {
    update({ phase: 'loading' });
    try {
      const res = await gameApi.start();
      update({
        sessionId: res.session_id,
        level: res.level || 1,
        difficulty: res.difficulty || 1.0,
        bgColor: res.color_theme || '#1a1a2e',
        phase: 'generating',
        failCount: 0,
        totalFails: 0,
        attemptCount: 0,
      });
      await generateNextPuzzle();
    } catch (e) {
      console.error('Start game failed:', e);
    }
  }, [update, generateNextPuzzle]);

  const handleAttempt = useCallback(
    async (isCorrect: boolean, _errorType?: string) => {
      const s = stateRef.current;
      const decisionTime = Date.now() - (s.lastAttemptStart || Date.now());
      try {
        const res = await gameApi.attempt({
          puzzle_id: s.puzzleData?.puzzle_id || '',
          puzzle_type: s.puzzleType || '',
          prompt: s.puzzleData?.prompt,
          is_correct: isCorrect,
          decision_time_ms: decisionTime,
        });
        update({
          playerState: res.state || 'stable',
          bgColor: res.color_theme || '#1a1a2e',
          coachingText: res.coaching?.hint || null,
          attemptCount: s.attemptCount + 1,
        });

        if (!isCorrect) {
          const newFailCount = s.failCount + 1;
          update({ failCount: newFailCount });
          if (newFailCount >= 3) {
            try {
              await puzzleApi.switchPuzzle();
              update({ failCount: 0 });
            } catch (_) {}
          }
        } else {
          update({ failCount: 0 });
        }

        if ((s.attemptCount + 1) % 5 === 0) {
          recordMetricSnapshot();
        }

        setTimeout(() => generateNextPuzzle(), isCorrect ? 600 : 2000);
      } catch (e) {
        console.error('Attempt failed:', e);
      }
    },
    [update, generateNextPuzzle, recordMetricSnapshot],
  );

  const handleCorrect = useCallback(
    async (_timeMs: number) => handleAttempt(true),
    [handleAttempt],
  );

  const handleWrong = useCallback(
    async (errorType: string, _timeMs: number) => handleAttempt(false, errorType),
    [handleAttempt],
  );

  const handlePsychAnswer = useCallback(
    async (selectedIndex: number, timeMs: number) => {
      const s = stateRef.current;
      try {
        const res = await puzzleApi.psychologyAnswer(selectedIndex, timeMs);
        update({
          psychTotal: s.psychTotal + 1,
          psychCorrect: s.psychCorrect + (res.is_correct ? 1 : 0),
          coachingText: res.is_correct
            ? 'Correct! Your analytical mind prevailed.'
            : 'Interesting choice. The weight of your answer affects your difficulty.',
        });
        setTimeout(() => generateNextPuzzle(), 2000);
      } catch (e) {
        console.error('Psych answer failed:', e);
      }
    },
    [update, generateNextPuzzle],
  );

  const endGame = useCallback(async () => {
    try {
      await gameApi.end();
      update({ phase: 'finished' });
    } catch (e) {
      console.error('End game failed:', e);
    }
  }, [update]);

  return {
    state,
    startGame,
    handleCorrect,
    handleWrong,
    handlePsychAnswer,
    endGame,
    generateNextPuzzle,
  };
}
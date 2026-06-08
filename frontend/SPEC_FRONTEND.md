# Echo Game Frontend — Canvas Overhaul

## What to build

Replace the DOM-based 3x3 hex grid game with a full-viewport HTML5 Canvas game that supports multiple dynamic puzzle types with fibonacci/golden ratio layout.

## Files to modify

### 1. `src/App.tsx` — No changes needed (routing stays the same)

### 2. `src/game_constants.ts` — Already written. Read this file first for PHI, golden spiral helpers, fibTiming, NOTE_COLORS.

### 3. `src/api/client.ts` — Already updated with puzzleApi and metricsApi.

### 4. `src/types/index.ts` — Already updated with PuzzleData types.

### 5. `src/hooks/useGame.ts` — Must be rewritten.

### 6. `src/pages/GamePage.tsx` — COMPLETE REWRITE. This is the main file.

### 7. `src/pages/DashboardPage.tsx` — Minor updates for new metrics.

## GamePage.tsx Requirements

### Canvas Setup
- Create a full-viewport `<canvas>` element (100vw x 100vh)
- Resize handler on window resize
- requestAnimationFrame render loop
- Draw decorative fibonacci spiral background (subtle, low opacity lines)
- All puzzle elements rendered on canvas using 2D context

### Game Flow State Machine
```
  loading -> generating -> displaying -> input -> (correct -> generating | wrong -> coaching -> generating)
  also: psychology_question -> (answer -> generating)
```

### Puzzle Type: pattern_recall
- Notes positioned using goldenSpiralPoint() from game_constants.ts
- Display phase: animate notes appearing one by one with golden spiral reveal
- Each note appears at its (x,y) with a scale-in animation (0 -> 1)
- Play beep sound via Web Audio API per note
- Input phase: player clicks/taps canvas. Check if tap (x,y) is near any note (use distance to find closest note)
- If closest match has correct index -> correct. Wrong index or miss -> wrong.
- Fix click registration: use pointerdown/pointerup with debounce (150ms), check pointer position relative to canvas bounding rect

### Puzzle Type: motion_tracking
- Animated objects moving from start position to end position
- Each object follows a straight line with easing (ease-in-out)
- Player must tap objects in the correct order (index order)
- Object is "collected" when tapped near it (50px radius)
- Display phase plays all motions. Input phase: objects idle at their end position, player taps in sequence.

### Puzzle Type: spatial_golden
- Render multiple golden rectangles on canvas
- One has correct phi proportions, others have distorted ratios
- Player taps the one they think is the golden ratio rectangle
- Correct = green flash. Wrong = red flash + coaching.

### Puzzle Type: psychology_question
- Render question text at golden ratio horizontal position (38.2% from top)
- Render 3 options below, each as clickable text blocks
- Use canvas fillText with word wrapping
- Player clicks one option -> call /api/puzzle/psychology-answer -> show explanation overlay

### Puzzle Adaptation Logic (in useGame.ts)
- Track puzzle fail count per puzzle type
- After 2 fails on same puzzle:
  1. Measure time_to_fail for each attempt
  2. Calculate speed_change = (time2 - time1) / time1
  3. Call /api/puzzle/llm-predict
  4. If will_fail=true -> generate new puzzle (call /api/puzzle/generate with different type)
- After 3 fails total -> force switch via /api/puzzle/switch
- Call /api/metrics/snapshot every 5 attempts

### HUD (drawn on canvas, not DOM)
- Top bar: Level, Difficulty, PuzzleType, Streak — text drawn at canvas top (golden ratio positions)
- Timer bar: horizontal bar at golden ratio division (38.2% from top), width shrinks over time
- Coaching hint text: drawn at bottom of canvas (61.8% position) with golden color
- New rule reveal: flash overlay text in center

### Fibonacci Integration
- Background decorative: draw 3 fibonacci spiral arms at very low opacity
- Note positions: golden spiral curve
- Timing between notes: fibTiming() from game_constants.ts
- HUD font sizes: scale by phi (e.g. 14px, 22px, 36px)
- Color palette from NOTE_COLORS / BG_COLORS

### Click Fix
- Use pointer events (not click events)
- Debounce 150ms between clicks
- Track pointer position via canvas.getBoundingClientRect()
- Add passive: true to prevent scroll interference on mobile
- On canvas, detect element hits by distance calculation (not DOM hit testing)

### Sound
- Web Audio API: short sine wave beeps
- Frequencies: 440 + index * 80 for notes
- Wrong: 200Hz low tone
- Correct: 880Hz high tone
- Use AudioContext singleton (reuse, don't recreate)

## useGame.ts Hook

State machine:
```
  phase: 'loading' | 'generating' | 'displaying' | 'input' | 'coaching' | 'psych_question' | 'finished'
  puzzleType: PuzzleType
  puzzleData: PuzzleData
  failCount: number
  timeToFail1: number | null
  timeToFail2: number | null
  totalFails: number
```
Key functions:
- startGame() -> calls /api/game/start -> /api/puzzle/generate
- handleCorrect() / handleWrong(errorType, timeToFailMs)
- checkPuzzleSwitch() — after 2 fails, call LLM predict, optionally switch
- recordMetricSnapshot() — every 5 attempts
- handlePsychAnswer(selectedIndex, timeTaken)

## Dashboard Updates

Just add a "Puzzle Type History" section showing which puzzle types the player encountered, and a "Psychology Accuracy" stat if available.

## Testing

After building, run `npm run build` to verify no TypeScript errors.

Start coding now. Read game_constants.ts first. Build GamePage.tsx as a single file with all canvas rendering inline. Keep it clean but don't split into subcomponents — this is complex enough that a single well-organized file is better for the AI to manage.
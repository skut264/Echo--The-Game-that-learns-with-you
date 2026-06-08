# Echo Game Overhaul — Dynamic Puzzle Engine + LLM-driven Adaptation

## Core Problems to Fix

1. **Canvas underutilized** — game is a tiny 3x3 grid in a big canvas. Use full canvas with fibonacci/golden ratio positioning.
2. **Same puzzle every time** — only pattern recall. Need dynamic puzzle types.
3. **Mouse clicks not registering** — tile click handler race conditions. Use pointer events, debounce.
4. **Hints too fast / overlapping** — coaching display timing and positioning.
5. **No failure prediction** — track metrics, use LLM to predict, regenerate puzzle.

---

## Puzzle Types (all dynamically generated)

### Type 1: Pattern Sequence Recall (existing, improved)
- Fibonacci-spiral layout on full canvas (not 3x3 grid)
- Notes positioned along golden spiral curve
- Random position, size, rotation per note

### Type 2: Psychology Mind-Bending Question
- A text question with 3 options
- Each option has a weight score (1-10) that affects difficulty
- Options are psychological traps (cognitive biases)
- Player taps the one they believe
- Correct = faster recovery; Wrong = harder next round
- Examples: "A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?" → options: 5¢ (correct), 10¢ (intuitive trap), 15¢

### Type 3: Fibonacci Motion Pattern
- Objects moving in fibonacci spiral paths
- Player must tap in the correct golden-ratio sequence
- Objects shrink/grow following golden ratio
- Timing based on phi (1.618)

### Type 4: Spatial Golden Ratio Puzzle
- Shapes arranged in golden rectangle
- Player must identify the irregular shape among phi-proportioned ones
- Rotation, scale, and position follow fibonacci sequence

---

## Puzzle Selection Algorithm

1. On game start: randomly choose from available puzzle types
2. Track per-type performance across attempts
3. If player fails 2 consecutive times on same puzzle:
   - Analyze: time_to_fail_1 vs time_to_fail_2
   - Did they get faster (panic) or slower (giving up)?
   - Feed metrics to LLM: "Will this player fail this puzzle type on attempt 3?"
   - If LLM says YES or uncertainty > 50% → generate new puzzle
   - If fails 3rd time → force-switch to different puzzle type
4. LLM generates puzzle description → backend builds puzzle data
5. Store generation history for training

---

## Canvas Layout (Fibonacci/Golden Ratio)

- Canvas uses full viewport
- Elements positioned on golden spiral curve
- Spiral center at (canvas_width * 0.382, canvas_height * 0.382) — golden ratio point
- Element i position: angle = i * 137.508° (golden angle), radius = phi^i * base_radius
- Size follows: base_size * (1 / phi^i)
- Opacity/color transitions follow fib sequence
- Hint text appears at golden ratio division points (top/left 38.2%)

---

## Backend Changes

### New Endpoints

```
POST /api/puzzle/generate
  Body: { puzzle_type, difficulty, player_context }
  Returns: { puzzle_id, puzzle_data (type-specific), fibonacci_params }

POST /api/puzzle/llm-predict
  Body: { player_id, puzzle_type, attempt_count, metrics_history }
  Returns: { will_fail: bool, confidence: float, reasoning: str }

POST /api/puzzle/switch
  Body: { player_id, current_puzzle_id, fail_count }
  Returns: { new_puzzle_type, puzzle_data }

POST /api/puzzle/psychology-question
  Returns: { question, options: [{text, weight}], correct_index, explanation }
```

### New DB Tables

```sql
-- Puzzle generation log
CREATE TABLE puzzle_generations (
  id INTEGER PRIMARY KEY,
  session_id INTEGER REFERENCES sessions,
  puzzle_type TEXT,
  puzzle_data TEXT (JSON),
  generation_params TEXT (JSON),
  created_at TEXT
);

-- Puzzle attempt analysis
CREATE TABLE puzzle_analyses (
  id INTEGER PRIMARY KEY,
  attempt_id INTEGER REFERENCES attempts,
  puzzle_type TEXT,
  time_to_fail_ms REAL,
  prev_time_to_fail_ms REAL DEFAULT NULL,
  speed_change REAL, -- positive = got faster, negative = slower
  llm_prediction INTEGER,
  llm_confidence REAL,
  llm_reasoning TEXT,
  switched_puzzle INTEGER DEFAULT 0
);

-- Psychology question log
CREATE TABLE psych_questions (
  id INTEGER PRIMARY KEY,
  session_id INTEGER REFERENCES sessions,
  question TEXT,
  options TEXT (JSON),
  selected_index INTEGER,
  correct_index INTEGER,
  weight_chosen REAL,
  is_correct INTEGER
);

-- Player metric snapshots (for training)
CREATE TABLE player_metrics_snapshots (
  id INTEGER PRIMARY KEY,
  player_id INTEGER REFERENCES players,
  session_id INTEGER REFERENCES sessions,
  snapshot_at TEXT,
  avg_time_per_note_ms REAL,
  variance_time_per_note REAL,
  error_rate_rolling REAL, -- last 10
  reaction_time_improvement REAL, -- positive = getting faster
  fatigue_score REAL, -- based on time decay
  puzzle_type TEXT,
  llm_generated_puzzle INTEGER DEFAULT 0
);
```

### Training Data Collection
- Every 5 attempts: snapshot player metrics row
- Collect {puzzle_type, difficulty, player_reaction_time, error_rate, llm_prediction, outcome}
- Store for batch training against qwen2.5:3b
- API endpoint: POST /api/training/record for real-time feedback

---

## Frontend Changes

### Canvas-based Rendering (HTML5 Canvas)
- Replace DOM-based 3x3 hex grid with full-viewport canvas
- Draw fibonacci spiral background (subtle, decorative)
- For pattern puzzles: notes positioned on golden spiral
- For psych questions: text rendered at golden ratio positions
- For motion puzzles: animated objects following fib paths
- Touch/pointer events with debounce (fixes click registration)
- requestAnimationFrame loop for animations

### Puzzle States
- `displaying` — animate puzzle elements in (fib spiral reveal)
- `input` — player interacts with puzzle on canvas
- `coaching` — show coaching overlay
- `psych-question` — show question with options (overlay on canvas)
- `transition` — between puzzles (golden ratio fade)

### HUD Overlay on Canvas
- Semi-transparent top bar
- Level, Difficulty, Streak, PuzzleType
- Timer bar along golden ratio horizontal division (38.2% from top)

---

## Fibonacci Integration Everywhere

- Puzzle element positioning: golden spiral
- Timing intervals: 600ms / difficulty * phi^x
- Animation durations: phi * base
- Color transitions: golden ratio palette
- Sizing: divide by phi each layer
- Background decorative fibonacci spiral
- Button/UI element placement at golden ratio grid lines

---

## Files to Create/Modify

### New Backend Files
- `backend/puzzle_generator.py` — LLM-driven puzzle generation engine
- `backend/canvas_renderer.py` — puzzle data → canvas render instructions (JSON)
- `backend/training_collector.py` — metric snapshot collection + training data export

### Modified Backend Files
- `backend/main.py` — new endpoints for puzzle gen, LLM prediction, training
- `backend/models.py` — new tables, new query functions
- `backend/config.py` — fibonacci/physics constants, puzzle type registry
- `backend/engine.py` — multi-puzzle aware engine

### Frontend Files (via The Coder)
- `frontend/src/pages/GamePage.tsx` — full rewrite for canvas rendering
- `frontend/src/hooks/useGame.ts` — multi-puzzle state machine
- `frontend/src/types/index.ts` — new types
- `frontend/src/api/client.ts` — new endpoints
- `frontend/src/pages/DashboardPage.tsx` — expanded metrics
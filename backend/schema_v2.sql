-- Echo v2 Schema Migration
-- New tables for dynamic puzzles, challenges, and enhanced metrics

-- Puzzle definitions (generated dynamically per puzzle shown)
CREATE TABLE IF NOT EXISTS puzzles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    puzzle_type TEXT NOT NULL,        -- 'pattern_sequence', 'psychology_question', 'spatial_logic', 'timing_challenge'
    puzzle_data TEXT NOT NULL,         -- JSON: the puzzle definition (params, options, sequence, etc.)
    shown_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    shown_count INTEGER DEFAULT 1,    -- how many times this puzzle was shown
    is_active INTEGER DEFAULT 1,
    is_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    was_skipped INTEGER DEFAULT 0,
    generated_by TEXT DEFAULT 'template' -- 'template' or 'llm'
);

-- Individual attempts per puzzle (vs per game session)
CREATE TABLE IF NOT EXISTS puzzle_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    puzzle_id INTEGER NOT NULL REFERENCES puzzles(id),
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    attempt_number INTEGER NOT NULL,   -- 1st, 2nd, 3rd attempt at this puzzle
    is_correct INTEGER NOT NULL,
    time_taken_ms REAL,                -- how long before they answered/clicked
    hesitation_ms REAL,                -- time between sequence end and first click
    input_latency_ms REAL,
    error_type TEXT,
    chosen_option INTEGER,             -- for multiple choice challenges
    metrics JSON,                      -- extensible metrics payload
    attempted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Challenge questions bank
CREATE TABLE IF NOT EXISTS challenge_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_type TEXT NOT NULL,       -- 'psychology', 'logic', 'perception', 'memory'
    question_text TEXT NOT NULL,
    options JSON NOT NULL,             -- [{"text": "...", "weight": 0.3, "explanation": "..."}, ...]
    correct_answer INTEGER NOT NULL,   -- index of correct option
    difficulty REAL DEFAULT 1.0,
    category TEXT,
    times_used INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Player metrics table (per-session enhanced metrics)
CREATE TABLE IF NOT EXISTS player_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id),
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    avg_reaction_time_ms REAL,
    reaction_time_trend REAL,          -- positive = slowing down, negative = speeding up
    hesitation_score REAL,             -- avg time between sequence display and first input
    speed_variance REAL,               -- variance in response speeds
    fatigue_index REAL,                -- based on time-between-attempts increasing trend
    accuracy_trend REAL,               -- sliding window accuracy change
    puzzle_switches INTEGER DEFAULT 0, -- how many times puzzles were switched
    flow_score REAL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Fail prediction log
CREATE TABLE IF NOT EXISTS fail_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id),
    puzzle_id INTEGER NOT NULL REFERENCES puzzles(id),
    prediction BOOLEAN NOT NULL,       -- true = predicted fail
    confidence REAL,                   -- 0.0 - 1.0
    features_used TEXT,                -- JSON of what features the prediction used
    actual_outcome BOOLEAN,            -- did they actually fail?
    triggered_puzzle_switch INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_puzzles_session ON puzzles(session_id);
CREATE INDEX IF NOT EXISTS idx_puzzle_attempts_puzzle ON puzzle_attempts(puzzle_id);
CREATE INDEX IF NOT EXISTS idx_puzzle_attempts_player ON puzzle_attempts(player_id);
CREATE INDEX IF NOT EXISTS idx_fail_predictions_player ON fail_predictions(player_id);
CREATE INDEX IF NOT EXISTS idx_player_metrics_session ON player_metrics(session_id);
-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    audience TEXT DEFAULT 'client',
    deck_type TEXT DEFAULT 'strategic',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Uploaded files
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    file_size INTEGER,
    content_type TEXT,
    extracted_text TEXT,
    extracted_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Chat sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    current_stage INTEGER DEFAULT 1,
    stage_data TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    stage INTEGER,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Storylines
CREATE TABLE IF NOT EXISTS storylines (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    central_question TEXT,
    situation TEXT,
    complication TEXT,
    resolution TEXT,
    key_recommendation TEXT,
    desired_decision TEXT,
    supporting_arguments TEXT DEFAULT '[]',
    evidence TEXT DEFAULT '[]',
    issue_tree TEXT DEFAULT '{}',
    pyramid TEXT DEFAULT '{}',
    mece_template TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Slides
CREATE TABLE IF NOT EXISTS slides (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    slide_type TEXT NOT NULL,
    action_title TEXT NOT NULL,
    content_json TEXT NOT NULL DEFAULT '{}',
    is_appendix INTEGER DEFAULT 0,
    preview_image TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Generated decks
CREATE TABLE IF NOT EXISTS decks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filepath TEXT NOT NULL,
    filename TEXT NOT NULL,
    validation_score INTEGER,
    validation_report TEXT,
    generated_at TEXT DEFAULT (datetime('now'))
);

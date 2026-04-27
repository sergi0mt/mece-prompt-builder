ALTER TABLE projects ADD COLUMN engagement_type TEXT DEFAULT NULL;

CREATE TABLE IF NOT EXISTS research_state (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE,
    research_plan TEXT DEFAULT '{}',
    research_brief TEXT DEFAULT '{}',
    sources TEXT DEFAULT '[]',
    data_gaps TEXT DEFAULT '[]',
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS deliverables (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    format_type TEXT NOT NULL,
    filepath TEXT,
    filename TEXT,
    status TEXT DEFAULT 'pending',
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

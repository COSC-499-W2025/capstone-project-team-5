CREATE TABLE Project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    is_collaborative BOOLEAN NOT NULL DEFAULT 0,
    start_date DATE,
    end_date DATE,
    language TEXT, -- Primary programming language
    framework TEXT, -- Primary framework used
    importance_rank INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Artifact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    path TEXT NOT NULL, -- File path
    type TEXT NOT NULL, -- e.g., code, document, design, media
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE CASCADE
);

CREATE TABLE Contribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    artifact_id INTEGER,
    activity_type TEXT NOT NULL, -- e.g., code, test, design, document
    date DATE,
    description TEXT,
    FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES Artifact(id) ON DELETE SET NULL
);

CREATE TABLE Skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- many-to-many relationship between Project and Skill
CREATE TABLE ProjectSkill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES Skill(id) ON DELETE CASCADE
);


-- Consolidated generated items table used for portfolio/resume entries.
-- The `kind` column distinguishes logical item types (e.g. 'portfolio',
-- 'resume'). Using a single table simplifies querying and allows a
-- single retriever implementation to filter by kind.
CREATE TABLE IF NOT EXISTS GeneratedItem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL, -- JSON-serialized content
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_generateditem_kind ON GeneratedItem(kind);
CREATE INDEX IF NOT EXISTS idx_generateditem_project ON GeneratedItem(project_id);
CREATE INDEX IF NOT EXISTS idx_generateditem_created_at ON GeneratedItem(created_at);